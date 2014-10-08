import os
import sys
import subprocess
import logging
import shutil
import zipfile
import datetime
import ast
from twonicornweb.lib.tfacter import tFacter
import datetime
import logging
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import func
from sqlalchemy.sql import label
from sqlalchemy import distinct
from sqlalchemy import or_
from sqlalchemy import desc
from twonicornweb.models import (
    DBSession,
    Application,
    Deploy,
    Artifact,
    ArtifactAssignment,
    ArtifactNote,
    Lifecycle,
    Env,
    Repo,
    RepoType,
    ArtifactType,
    RepoUrl,
    )
log = logging.getLogger(__name__)


class Core:

    def __init__(self):

        # Need this to print the right promote urls in the dev environment
        t_facts = tFacter()
        # Facts
        ct_class = t_facts.get_fact('ct_class')
        if ct_class == 'tdb':
            self.tcw_host = 'twonicorn.dev.ctgrd.com'
        else:
            self.tcw_host = 'twonicorn.ctgrd.com'

    # INJECT functions
    def env_to_id(self, env_name):

        envs = DBSession.query(Env)
        envs = envs.filter(Env.name == '%s' % env_name).first()

        return envs.env_id

    def insert_artifact(self):

        logging.info('Inserting new artifact into database: %s'
                     % self.location)

        sql = ("""
            INSERT INTO artifacts
                        (REPO_ID,LOCATION,REVISION,VALID)
                 VALUES ('%s','%s','%s','1')
        """ % (self.repo_id, self.location, self.revision))
        results = self.db_i.update_db(sql)
        self.artifact_id = str(results)

        logging.info('Artifact ID: %s' % self.artifact_id)

    def get_artifact_type(self):

        # what type are we? For confs we have to compare
        sql = ("""
            SELECT at.name as artifact_type
              FROM deploys d
                   JOIN artifact_types at USING (artifact_type_id)
             WHERE deploy_id='%s'
        """ % (self.deploy_id))
        results = self.db_so.query_db(sql)
        self.artifact_type = str(results[0])

        logging.info('Artifact type: %s' % self.artifact_type)

    def assign_artifact_package(self):

        # Automatically insert into dev or qat and make it current.
        # Prod requires promotion.
        sql = ("""
            INSERT INTO artifact_assignments
                        (DEPLOY_ID,ENV_ID,LIFECYCLE_ID,ARTIFACT_ID,USER)
                 VALUES ('%s','%s','2','%s','%s' )
        """ % (self.deploy_id, self.env_id, self.artifact_id, self.user))
        self.artifact_assignment_id = self.db_i.update_db(sql)

        if self.env_id == '2':
            promote_url = ('https://'
                           + self.tcw_host
                           + '/promote?deploy_id='
                           + self.deploy_id
                           + '&artifact_id='
                           + self.artifact_id
                           + '&to_env=prd&commit=false')
            logging.info('Promote to prod url: %s' % promote_url)

    def assign_artifact_conf(self):

        self.get_conf_url()

        # figure out what envs we need to make assignments for
        self.find_conf_assign_envs()

        # assign confs to all the envs we found
        if self.assign_envs:
            self.assign_conf_to_envs()
        else:
            logging.info('No assignments to be made for any environment')

    def get_conf_url(self):

        # First construct the correct url for the artifact we just inserted.
        sql = ("""
           SELECT u.url url,
                  a.location,
                  rt.name repo_type
             FROM artifacts a
                  JOIN repos r USING (repo_id)
                  JOIN repo_types rt USING (repo_type_id)
                  JOIN repo_urls u USING (repo_id)
            WHERE artifact_id=%s
                  AND u.ct_loc='%s'
        """ % (self.artifact_id, self.ct_loc))

        results = self.db_so.query_db(sql)
        self.artifact_url = results[0] + results[1]
        self.repo_type = results[2]

        logging.info('Artifact url: %s' % self.artifact_url)

    def find_conf_assign_envs(self):
        """
        Compare the latest revision in the db to see if files changed
        for each env if they changed, create an artifact assignment
        for that env. In dev/qat it is made current, in prd it's
        made init
        These two revs represent a change to prd only.
        >>> latest_conf_revs = ['234827']
        >>> revision = 234798
        >>> t_svn = tSvn('https://svn.prod.cs/repository/operations/twonicorn/twonicorn-test-war-svn-conf')
        >>> t_svn.cmp_revision_svn(revision, latest_conf_revs[0], 'prd')
        prd
        >>> t_svn.cmp_revision_svn(revision, latest_conf_revs[0], 'dev')
        None
        """
        # Get the last revision from every env
        self.assign_envs = []
        envs = ['dev', 'qat', 'prd']
        for env in envs:

            self.get_latest_conf_revs(env)

            if self.latest_conf_revs:
                logging.debug('Revision for %s '
                              'is: %s'
                              % (env,
                                 self.latest_conf_revs[0]))
                if self.repo_type == 'svn':
                    # Set up svn object
                    self.t_svn = tSvn(self.artifact_url)
                    compare = self.t_svn.cmp_revision_svn(
                        self.revision,
                        self.latest_conf_revs[0],
                        env)
                    if compare:
                        self.assign_envs.append(compare)
                elif self.repo_type == 'git':
                    # set up git object
                    self.t_git = tGit(self.artifact_url)
                    compare = self.t_git.cmp_revision_git(
                        self.revision,
                        self.latest_conf_revs[0],
                        env)
                    if compare:
                        logging.debug('Staging update for: %s' % compare)
                        self.assign_envs.append(compare)
                else:
                    logging.info('Only supporting svn and git '
                                 'repo types so far')
                    logging.info('twoni-plete')
                    print ""
                    sys.exit(0)

            else:
                logging.info('No assignments found in the DB for env: %s. '
                             'Creating new assignments.'
                             % env)
                self.assign_envs.append(env)

    def get_latest_conf_revs(self, env=None):

        # For prod, we want to compare against the latest revision in init.
        if env == 'prd':
            get_state = 'init'
        else:
            get_state = 'current'

        sql = ("""
           SELECT a.revision
             FROM deploys d
                  JOIN artifact_assignments aa USING (deploy_id)
                  JOIN envs e USING (env_id)
                  JOIN lifecycles l USING (lifecycle_id)
                  JOIN artifacts a USING (artifact_id)
            WHERE deploy_id=%s
                  AND l.name='%s'
                  AND e.name='%s'
                  AND a.valid=1
            ORDER BY aa.created DESC LIMIT 1
        """ % (self.deploy_id, get_state, env))

        self.latest_conf_revs = self.db_so.query_db(sql)

    def assign_conf_to_envs(self):

        for assign in self.assign_envs:
            # Dev and qat go live immediately, prd goes to init
            if assign == 'prd':
                lifecycle = '1'
            else:
                lifecycle = '2'

            # FIXME
            env_dict = {'dev': '1', 'qat': '2', 'prd': '3'}

            sql = ("""
                INSERT INTO artifact_assignments
                    (DEPLOY_ID,ENV_ID,LIFECYCLE_ID,ARTIFACT_ID,USER)
                VALUES ('%s','%s','%s','%s','%s' )
            """ % (self.deploy_id,
                   env_dict[assign],
                   lifecycle,
                   self.artifact_id,
                   self.user
                   ))
            self.artifact_assignment_id = self.db_i.update_db(sql)
            logging.info('New artifact assignment created for %s: %s'
                         % (assign,
                            self.artifact_assignment_id))
            # Print the promote url if it's prd
            if assign == 'prd':
                promote_url = ('https://'
                               + self.tcw_host
                               + '/promote?deploy_id='
                               + self.deploy_id
                               + '&artifact_id='
                               + self.artifact_id
                               + '&to_env=prd&commit=false')

                logging.info('Promote to prod url: %s' % promote_url)

    def inject(self,
               environment=None,
               repo_id=None,
               location=None,
               revision=None,
               deploy_id=None,
               user=None,
               ct_loc=None):
        self.env = environment
        self.repo_id = repo_id
        self.location = location
        self.revision = revision
        self.deploy_id = deploy_id
        self.user = user
        self.ct_loc = ct_loc

        self.env_id = self.env_to_id(environment)

        self.insert_artifact()

        self.get_artifact_type()

        if self.artifact_type == 'war':

            logging.info('Assigning new artifact ID to %s: %s'
                         % (self.env,
                            self.artifact_id))
            self.assign_artifact_package()
            logging.info('New artifact assignment created: %s'
                         % self.artifact_assignment_id)

        elif self.artifact_type == 'conf':

            self.assign_artifact_conf()

    # DEPLOY functions
    def get_application_deploys(self, application_id):
        q = DBSession.query(Deploy)
        deploy = q.filter(Deploy.application_id == '%s' % application_id).one()
        return deploy


    def get_artifact_details(self, deploy_data, limit=None):

        self.artifact_deployments = {}
        self.todo_dict = {}
        self.todo_list = []

        for deploy in deploy_data:
            #print deploy.deploy_id
            #print deploy.application_id
            #print deploy.artifact_type_id
            #print deploy.deploy_path
            #print deploy.created

            dep = DBSession.query(Deploy, ArtifactAssignment).\
                            filter(Deploy.deploy_id == '%s' % deploy.deploy_id).\
                            filter(Lifecycle.name == 'current').\
                            filter(Env.name == 'dev').\
                            filter(Artifact.valid == 1).\
                            filter(RepoUrl.ct_loc == 'lax1').\
                            order_by(desc(ArtifactAssignment.created)).\
                            first()

            print "SHIT: ", dep[0].artifact_id

            #print type(dep)
            print "DEEEPLOOOYYY: ", dep


#                sql = ("""
#                    SELECT d.application_id,
#                        d.deploy_id,
#                        aa.artifact_id,
#                        aa.artifact_assignment_id,
#                        aaa.application_name,
#                        aa.created,
#                        d.deploy_path,
#                        u.url url,
#                        a.location,
#                        a.revision,
#                        a.branch,
#                        at.name artifact_type,
#                        rt.name repo_type,
#                        r.name repo
#                    FROM deploys d
#                        JOIN applications aaa USING (application_id)
#                        JOIN artifact_assignments aa USING (deploy_id)
#                        JOIN envs e USING (env_id)
#                        JOIN lifecycles l USING (lifecycle_id)
#                        JOIN artifacts a USING (artifact_id)
#                        JOIN artifact_types at USING (artifact_type_id)
#                        JOIN repos r USING (repo_id)
#                        JOIN repo_types rt USING (repo_type_id)
#                        JOIN repo_urls u USING (repo_id)
#                    WHERE deploy_id=%s
#                        AND l.name='current'
#                        AND e.name='%s'
#                        AND a.valid=1
#                        AND u.ct_loc='%s'
#                    ORDER BY aa.created DESC %s
#                """ % (deploy_id, self.ct_env, self.ct_loc, lim))
#
#            deployment_data = self.db_sa.query_db(sql)
#
#            if not deployment_data:
#                deployment_data = [(str(deploy_id),
#                                    "No Data",
#                                    "No Data",
#                                    "No Data",
#                                    "No Data",
#                                    "No Data",
#                                    "No Data",
#                                    "No Data",
#                                    "No Data",
#                                    "No Data",
#                                    "No Data",
#                                    "No Data",
#                                    "No Data",
#                                    "No Data")]
#
#            logging.debug('Deployment Data: %s' % deployment_data)
#
#            for index in range(len(deployment_data)):
#
#                # Store all the info for the deployment for use in a minute.
#                (application_id,
#                 deploy_id,
#                 artifact_id,
#                 artifact_assignment_id,
#                 application_name,
#                 created,
#                 deploy_path,
#                 url,
#                 location,
#                 revision,
#                 branch,
#                 artifact_type,
#                 repo_type,
#                 repo) = deployment_data[index]
#
#                dict = {
#                    'application_id': application_id,
#                    'deploy_id': deploy_id,
#                    'artifact_id': artifact_id,
#                    'artifact_assignment_id': artifact_assignment_id,
#                    'application_name': application_name,
#                    'created': created,
#                    'deploy_path': deploy_path,
#                    'url': url,
#                    'location': location,
#                    'url_location': url + location,
#                    'suffix': location.split('/',)[-1],
#                    'revision': revision,
#                    'branch': branch,
#                    'artifact_type': artifact_type,
#                    'repo_type': repo_type,
#                    'repo': repo,
#                    'env': self.ct_env
#                }
#
#                if limit:
#                    self.todo_dict[deploy_id] = dict
#                else:
#                    self.todo_list.append(dict)
#
#                logging.debug('deploy_id=%s,,artifact_id=%s,'
#                              'artifact_assignment_id=%s,application_name=%s,'
#                              'deploy_path=%s,url=%s,location=%s,'
#                              'url_location=%s,revision=%s,branch=%s,'
#                              'artifact_type=%s,repo_type=%s,repo=%s'
#                              % (deploy_id,
#                                 artifact_id,
#                                 artifact_assignment_id,
#                                 application_name,
#                                 deploy_path,
#                                 url,
#                                 location,
#                                 url + location,
#                                 revision,
#                                 branch,
#                                 artifact_type,
#                                 repo_type,
#                                 repo))
#
#            # Add all the artifact assignement ids to a list to compare
#            # with the manifest.
#            self.artifact_deployments[deploy_id] = (
#                artifact_assignment_id)

    def check_manifest(self):

        self.deploys_todo = []
        logging.debug('Comparing versions in manifest file : %s'
                      % self.manifest_file)
        if not os.path.isfile(self.manifest_file):
            logging.info('Manifest file %s does not exist, creating'
                         % self.manifest_file)
            open(self.manifest_file, 'a').close()
            logging.info('Manifest file %s created. Installing the current '
                         'version of all artifacts.'
                         % self.manifest_file)
            # Nothing is installed, need to do everything
            self.deploys_todo = self.artifact_deployments.keys()
        elif os.stat(self.manifest_file)[6] == 0:
            logging.warn('Manifest file %s is empty. Installing the current '
                         'version of all artifacts.'
                         % self.manifest_file)
            # state is unknown, need to do everything
            self.deploys_todo = self.artifact_deployments.keys()
        else:
            # read the last line
            self.fileHandle = open(self.manifest_file, "r")
            self.lineList = self.fileHandle.readlines()
            self.fileHandle.close()
            self.last_line = self.lineList[-1]
            (self.inst_date,
             self.inst_time,
             self.inst_deploys) = self.last_line.split(' ', 2)
            # convert the string to a dict for comparison.
            self.inst_deploys = ast.literal_eval(self.inst_deploys)
            logging.debug('Installed deployment:assignments: %s'
                          % self.inst_deploys)
            logging.debug('DB deployment:assignments: %s'
                          % self.artifact_deployments)

            # First see if they're the same. If they are, great, if not, we
            # have work to do.
            if cmp(self.artifact_deployments, self.inst_deploys) == 0:
                logging.info('Installed deployment:assignments '
                             'match the DB. Nothing to do.')
            else:
                logging.info('Installed deployment:assignments do not match '
                             'the DB. Checking to see what we need to do...')
                # first check if all the keys we want to install are there
                for self.key in self.artifact_deployments.keys():
                    if self.key in self.inst_deploys:
                        logging.debug('Deploy %s is in the manifest.'
                                      % self.key)
                        # check the value to make sure it's the same
                        if (self.artifact_deployments[self.key] ==
                           self.inst_deploys[self.key]):
                            logging.debug('Artifact assignment is the same '
                                          'for deploy id %s in both sources.'
                                          % self.key)
                        else:
                            # add the deploy to the list of things to do.
                            logging.debug('Artifact assignment is different '
                                          'for deploy id %s. Adding to list of'
                                          ' deploys to install.'
                                          % self.key)
                            self.deploys_todo.append(self.key)
                    else:
                        # add the deploy to the list of things to do.
                        logging.debug('Deploy id %s is missing from the '
                                      'manifest. Adding to list of deploys '
                                      'to install.'
                                      % self.key)
                        self.deploys_todo.append(self.key)

            if self.deploys_todo:
                logging.info('We are going to upgrade the following '
                             'deploys : %s'
                             % self.deploys_todo)

    def clean_dir(self, tmp_dir=None):
        # Clean the tmp dir first
        if (os.path.isdir(tmp_dir)):
            logging.debug('Removing tmp dir : %s' % tmp_dir)
            shutil.rmtree(tmp_dir)

    def dl_artifact_http(self, tmp_dir=None, location=None, revision=None):

        logging.info('Downloading revision: %s artifact: %s'
                     % (revision,
                        location))
        logging.debug('Downloading to dir: %s' % tmp_dir)
        subprocess.check_call(["wget",
                               "-q",
                               "--no-check-certificate",
                               "--directory-prefix=" + tmp_dir + '/',
                               location])

    def download_artifacts(self):

        # download everything first
        for t in self.deploys_todo:
            # Set our vars
            deploy_id = self.todo_dict[t]['deploy_id']
            artifact_assignment_id = (
                self.todo_dict[t]['artifact_assignment_id'])
            deploy_path = self.todo_dict[t]['deploy_path']
            url = self.todo_dict[t]['url']
            location = self.todo_dict[t]['location']
            url_location = self.todo_dict[t]['url_location']
            revision = self.todo_dict[t]['revision']
            artifact_type = self.todo_dict[t]['artifact_type']
            repo_type = self.todo_dict[t]['repo_type']

            logging.debug('deploy_id=%s,artifact_assignment_id=%s,'
                          'deploy_path=%s,url=%s,location=%s,url_location=%s,'
                          'revision=%s,artifact_type=%s,repo_type=%s'
                          % (deploy_id,
                             artifact_assignment_id,
                             deploy_path,
                             url,
                             location,
                             url_location,
                             revision,
                             artifact_type,
                             repo_type))

            deploy_id = str(deploy_id)
            # Add the deploy id to the tmp dir
            tmp_dir_id = self.tmp_dir + '/' + deploy_id
            # Clean the deploy dir first
            self.clean_dir(tmp_dir_id)

            # download artifacts
            if artifact_type == 'war':
                logging.debug('artifact_type is war.')
                if repo_type == 'http':
                    self.dl_artifact_http(tmp_dir_id, url_location, revision)
            elif artifact_type == 'conf':
                logging.debug('artifact_type is conf')
                if repo_type == 'svn':
                    # Append ct_env so that source and detination are
                    # env scpecific
                    url_location = url_location + '/' + self.ct_env
                    tmp_dir_id = tmp_dir_id + '/' + self.ct_env
                    t_svn = tSvn(url_location)
                    t_svn.dl_artifact_svn_conf(tmp_dir_id,
                                               url_location,
                                               revision)
                elif repo_type == 'git':
                    t_git = tGit(url_location)
                    t_git.dl_artifact_git_conf(tmp_dir_id,
                                               url_location,
                                               revision)
            elif artifact_type == 'jar':
                logging.debug('artifact_type is jar. coming soon.')

    def unzip(self, source_filename=None, dest_dir=None):
        zipper = zipfile.ZipFile(source_filename)
        zipper.extractall(dest_dir)

    def sync_artifact_war(self, tmp_dir_id, deploy_path, artifact_file):
        tmp_artifact_path_current = tmp_dir_id + '/current'
        # explode the war
        logging.debug('Expanding artifact : %s in %s'
                      % (artifact_file,
                         tmp_artifact_path_current))
        self.unzip(tmp_dir_id + '/' + artifact_file, tmp_artifact_path_current)

        # rsync it
        logging.debug('Rsyncing %s to %s'
                      % (tmp_artifact_path_current,
                         deploy_path))
        # TODO: need to ensure no trailing / ?
        subprocess.check_call(["rsync",
                               "-ra",
                               "--delete",
                               tmp_artifact_path_current,
                               deploy_path])

    def sync_artifact_conf(self, tmp_dir_id=None, deploy_path=None):
        logging.debug('Rsyncing %s to %s' % (tmp_dir_id, deploy_path))
        subprocess.check_call(["rsync", "-ra", tmp_dir_id + '/', deploy_path])

    def sync_artifacts(self):

        # sync artifacts next
        for s in self.deploys_todo:
            # Set our vars
            deploy_id = self.todo_dict[s]['deploy_id']
            artifact_assignment_id = (
                self.todo_dict[s]['artifact_assignment_id'])
            deploy_path = self.todo_dict[s]['deploy_path']
            url_location = self.todo_dict[s]['url_location']
            revision = self.todo_dict[s]['revision']
            artifact_type = self.todo_dict[s]['artifact_type']
            repo_type = self.todo_dict[s]['repo_type']
            items = url_location.rsplit('/', 1)
            artifact_file = items[1]

            logging.info('Syncing deployment to %s' % deploy_path)
            logging.debug('deploy_id=%s,artifact_assignment_id=%s,'
                          'deploy_path=%s,url_location=%s,revision=%s,'
                          'artifact_type=%s,repo_type=%s'
                          % (deploy_id,
                             artifact_assignment_id,
                             deploy_path,
                             url_location,
                             revision,
                             artifact_type,
                             repo_type))

            deploy_id = str(deploy_id)
            # Add the deploy id to the tmp dir
            tmp_dir_id = self.tmp_dir + '/' + deploy_id

            # do the sync artifacts
            if artifact_type == 'war':
                logging.debug('artifact_type is war.')
                self.sync_artifact_war(tmp_dir_id, deploy_path, artifact_file)
            elif artifact_type == 'conf':
                logging.debug('artifact_type is conf.')
                tmp_dir_id = tmp_dir_id + '/' + self.ct_env
                self.sync_artifact_conf(tmp_dir_id, deploy_path)
            elif artifact_type == 'jar':
                logging.debug('artifact_type is jar. Coming soon.')

    def update_manifest(self):
        # update the manifest with everything we just installed from the db.
        logging.debug('Updating the manifest file')

        date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        string = date + " " + str(self.artifact_deployments) + "\n"

        with open(self.manifest_file, "a") as myfile:
            myfile.write(string)

        logging.debug('Updated manifest file %s with application '
                      'assignments: %s'
                      % (self.manifest_file,
                         str(self.artifact_deployments)))

    def deploy(self,
               application_id=None,
               ct_env=None,
               ct_loc=None,
               manifest_file=None,
               tmp_dir=None):

        self.application_id = application_id
        self.ct_env = ct_env
        self.ct_loc = ct_loc
        self.manifest_file = manifest_file
        self.tmp_dir = tmp_dir

        self.get_application_deploys()

        self.check_manifest()

        # We know what we have to do, so let's go
        if self.deploys_todo:
            self.download_artifacts()
            self.sync_artifacts()
            # update the manifest with everything from the db.
            self.update_manifest()

    # PROMOTE functions
    def insert_promotion(self):

        sql = ("""
            INSERT INTO artifact_assignments
                (DEPLOY_ID,ENV_ID,LIFECYCLE_ID,ARTIFACT_ID,USER)
            SELECT '%s', env_id, '%s','%s','%s'
            FROM envs
            WHERE name  = '%s'
            """ % (self.deploy_id,
                   self.state,
                   self.artifact_id,
                   self.user,
                   self.env))

        logging.info('Assigning artifact...')
        artifact_assignment_id = self.db_i.update_db(sql)
        logging.info('New artifact assignment created: %s'
                     % artifact_assignment_id)

    def get_promotion_details(self, deploy_id, artifact_id):

        self.todo_dict = {}
        self.todo_list = []

        sql = ("""
            SELECT d.application_id,
                d.deploy_id,
                a.artifact_id,
                aaa.application_name,
                d.deploy_path,
                a.created,
                u.url url,
                a.location,
                a.revision,
                a.branch,
                at.name artifact_type,
                rt.name repo_type,
                r.name repo
            FROM deploys d
                JOIN applications aaa USING (application_id)
                JOIN artifact_assignments aa USING (deploy_id)
                JOIN envs e USING (env_id)
                JOIN lifecycles l USING (lifecycle_id)
                JOIN artifacts a USING (artifact_id)
                JOIN artifact_types at USING (artifact_type_id)
                JOIN repos r USING (repo_id)
                JOIN repo_types rt USING (repo_type_id)
                JOIN repo_urls u USING (repo_id)
            WHERE deploy_id=%s
                AND a.artifact_id='%s'
                AND u.ct_loc='lax1' LIMIT 1
        """ % (deploy_id, artifact_id))

        deployment_data = self.db_sa.query_db(sql)

        if not deployment_data:
            deployment_data = [(str(deploy_id),
                                "No Data",
                                "No Data",
                                "No Data",
                                "No Data",
                                "No Data",
                                "No Data",
                                "No Data",
                                "No Data",
                                "No Data",
                                "No Data",
                                "No Data",
                                "No Data",
                                "No Data")]

        logging.debug('Deployment Data: %s' % deployment_data)

        for index in range(len(deployment_data)):

            # Store all the info for the deployment for use in a minute.
            (application_id,
             deploy_id,
             artifact_id,
             application_name,
             deploy_path,
             created,
             url,
             location,
             revision,
             branch,
             artifact_type,
             repo_type,
             repo) = deployment_data[index]

            dict = {
                'application_id': application_id,
                'deploy_id': deploy_id,
                'artifact_id': artifact_id,
                'application_name': application_name,
                'deploy_path': deploy_path,
                'created': created,
                'url': url,
                'location': location,
                'url_location': url + location,
                'suffix': location.split('/',)[-1],
                'revision': revision,
                'branch': branch,
                'artifact_type': artifact_type,
                'repo_type': repo_type,
                'repo': repo,
            }

            self.todo_list.append(dict)

    def promote(self,
                deploy_id=None,
                artifact_id=None,
                env=None,
                state=None,
                user=None):
        self.deploy_id = deploy_id
        self.artifact_id = artifact_id
        self.env = env
        self.state = state
        self.user = user

        self.insert_promotion()

    # UI functions
    def list_applications(self):

        try:
            apps = DBSession.query(Applications)
            return apps
        except DBAPIError, e:
            log.debug(str(e))
            raise


    def list_deploys(self, env, application_id=None):

        self.ct_env = env
        # We hard code lax1 as the location so all the urls will be relevant
        # in the office/vpn
        self.ct_loc = 'lax1'

        deploys = self.get_application_deploys(application_id)

        self.get_artifact_details(deploys, limit='True')

        return self.todo_dict

    def list_app_details_by_deploy(self, deploy_id=None):

        sql = ("""
            SELECT application_id,nodegroup
            FROM applications
            WHERE application_id=(SELECT application_id
                                  FROM deploys
                                  WHERE deploy_id='%s')
            """ % (deploy_id))

        details = self.db_so.query_db(sql)

        return details

    def list_history(self, env=None, deploy_id=None):

        self.ct_env = env
        # We hard code lax1 as the location so all the urls will be relevant
        # in the office/vpn
        self.ct_loc = 'lax1'

        self.get_artifact_details(deploy_id)

        return self.todo_list

    def list_promotion(self, deploy_id, artifact_id):

        # hardcoded for now, need to pass in
        self.ct_env = 'prd'

        self.ct_loc = 'lax1'
        deploy_data = [(deploy_id, artifact_id)]

        self.get_artifact_details(deploy_data, limit='True')

        return self.todo_dict

if __name__ == '__main__':
    import doctest
    doctest.testmod()
