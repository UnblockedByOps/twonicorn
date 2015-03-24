#!/usr/bin/python
#
#  Copyright 2015 CityGrid Media, LLC
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
import os
import sys
import subprocess
import logging
import optparse
import ConfigParser
import json
import urllib2
import git
import shutil
import zipfile
import tarfile
import datetime
import ast
import re

try:
    import pysvn
except ImportError:
    # pysvn is not friendly, no pip or easy_install option.
    # If import fails, we don't have svn support.
    pass


class tSvn:

    def __init__(self, url=None):
        self.url = url

        # Set up our client object
        try:
            self.client = pysvn.Client()
            self.client.callback_ssl_server_trust_prompt = (
                self.ssl_server_trust_prompt)
            self.client.set_default_username(svn_user)
            self.client.set_default_password(svn_pass)
        except NameError:
            logging.error('pysn module is absent, no svn support')

    def ssl_server_trust_prompt(self, trust_dict):
        # we know what we're connecting to, no need to validate
        return (True, 0, True)

    def dl_artifact_svn_conf(self, tmp_dir=None, location=None, revision=None):

        logging.info('Downloading revision: %s '
                     'artifact: %s'
                     % (revision,
                        location))
        logging.debug('Downloading to dir: %s' % tmp_dir)

        if revision == 'HEAD':
            # export the config
            self.client.export(location,
                               tmp_dir,
                               force=True,
                               revision=pysvn.Revision(
                                   pysvn.opt_revision_kind.head))
        else:
            # export the config
            self.client.export(location,
                               tmp_dir,
                               force=True,
                               revision=pysvn.Revision(
                                   pysvn.opt_revision_kind.number, revision))


class tFacter:

    def __init__(self):
        # need this for ct_*
        os.environ["FACTERLIB"] = "/var/lib/puppet/lib/facter:/app/twonicorn/conf/facter"
        p = subprocess.Popen(['facter'], stdout=subprocess.PIPE)
        p.wait()
        self.facts = p.stdout.readlines()
        # strip removes the trailing \n
        self.facts = dict(k.split(' => ') for k in
                          [s.strip() for s in self.facts if ' => ' in s])

    def get_fact(self, fact):

        return self.facts[fact]


class tGit:

    def __init__(self, url=None):
        self.url = url

        # Need this because our cert is lame
        os.environ['GIT_SSL_NO_VERIFY'] = 'true'

    def dl_artifact_git_conf(self, tmp_dir, location, revision):

        logging.info('Downloading revision: %s '
                     'artifact: %s'
                     % (revision, location))
        # check out the repo
        repo = git.Repo.clone_from(location, tmp_dir)
        # reset HEAD to the revision we want
        repo.head.reference = revision
        repo.head.reset(index=True, working_tree=True)


def get_application_deploys(tcw_host, application_id, ct_env, ct_loc):

    # Fetch the list of deploys for the application
    # This becomes the api call
    api_url = (api_protocol
               + '://'
               + tcw_host
               + '/api/application?'
               + 'id='
               + application_id
               + '&env='
               + ct_env
               + '&loc='
               + ct_loc
               + '&lifecycle=current')

    logging.info('Requesting data from api: %s' % api_url)

    response = urllib2.urlopen(api_url)
    deployment_data = json.load(response)

    if not deployment_data:
        logging.error('No deployment data found for '
                      'application_id: %s. Aborting!'
                      % application_id)
        logging.info('twoni-plete')
        print ""
        sys.exit(2)

    logging.debug('Deployment Data: %s' % deployment_data)

    deployments = {}

    for index in range(len(deployment_data)):
        deployment = deployment_data[index]

        deployments[deployment['deploy_id']] = {
            'deploy_id': deployment['deploy_id'],
            'package_name': deployment['package_name'],
            'artifact_assignment_id': deployment['artifact_assignment_id'],
            'deploy_path': deployment['deploy_path'],
            'download_url': deployment['download_url'],
            'revision': deployment['revision'],
            'artifact_type': deployment['artifact_type'],
            'repo_type': deployment['repo_type'],
            'repo_name': deployment['repo_name']
        }

        logging.debug('deploy_id=%s,artifact_assignment_id=%s,'
                      'deploy_path=%s,download_url=%s,'
                      'revision=%s,artifact_type=%s,repo_type=%s,repo_name=%s'
                      % (deployment['deploy_id'],
                         deployment['artifact_assignment_id'],
                         deployment['deploy_path'],
                         deployment['download_url'],
                         deployment['revision'],
                         deployment['artifact_type'],
                         deployment['repo_type'],
                         deployment['repo_name']))

    return deployments


def parse_db_deployments(deployments):

    db_deployments = {}
    for key in deployments.keys():
        db_deployments[key] = (
            deployments[key]['artifact_assignment_id'])

    return db_deployments


def check_manifest(deployments, manifest_file):

    deploys_todo = []
    logging.debug('Comparing versions in manifest file : %s'
                  % manifest_file)
    if not os.path.isfile(manifest_file):
        logging.info('Manifest file %s does not exist, creating'
                     % manifest_file)
        open(manifest_file, 'a').close()
        logging.info('Manifest file %s created. Installing the current '
                     'version of all artifacts.'
                     % manifest_file)
        # Nothing is installed, need to do everything
        deploys_todo = deployments.keys()
    elif os.stat(manifest_file)[6] == 0:
        logging.warn('Manifest file %s is empty. Installing the current '
                     'version of all artifacts.'
                     % manifest_file)
        # state is unknown, need to do everything
        deploys_todo = deployments.keys()
    else:
        # read the last line
        fileHandle = open(manifest_file, "r")
        lineList = fileHandle.readlines()
        fileHandle.close()
        last_line = lineList[-1]
        (inst_date,
         inst_time,
         inst_deploys) = last_line.split(' ', 2)
        # convert the string to a dict for comparison.
        inst_deploys = ast.literal_eval(inst_deploys)
        logging.debug('Installed deployment:assignments: %s'
                      % inst_deploys)

        db_deployments = parse_db_deployments(deployments)

        logging.debug('DB deployment:assignments: %s'
                      % db_deployments)

        # Check to see if we have to do anything
        logging.info('Checking to see what we need to do...')
        # first check if all the keys we want to install are there
        for key in deployments.keys():
            if key in inst_deploys:
                logging.debug('Deploy %s is in the manifest.'
                              % key)
                # check the value to make sure it's the same
                if (deployments[key]['artifact_assignment_id'] ==
                   inst_deploys[key]):
                    logging.debug('Artifact assignment is the same '
                                  'for deploy id %s in both sources.'
                                  % key)
                else:
                    # add the deploy to the list of things to do.
                    logging.debug('Artifact assignment is different '
                                  'for deploy id %s. Adding to list of'
                                  ' deploys to install.'
                                  % key)
                    deploys_todo.append(key)
            else:
                # add the deploy to the list of things to do.
                logging.debug('Deploy id %s is missing from the '
                              'manifest. Adding to list of deploys '
                              'to install.'
                              % key)
                deploys_todo.append(key)

        if deploys_todo:
            logging.info('We are going to upgrade the following '
                         'deploys : %s'
                         % deploys_todo)
        else:
            logging.info('Installed deployment:assignments '
                         'match the DB. Nothing to do.')

    return deploys_todo


def clean_dir(tmp_dir=None):
    # Clean the tmp dir first
    if (os.path.isdir(tmp_dir)):
        logging.debug('Removing tmp dir : %s' % tmp_dir)
        shutil.rmtree(tmp_dir)


def dl_artifact_http(tmp_dir=None, download_url=None, revision=None):

    logging.info('Downloading revision: %s artifact: %s'
                 % (revision,
                    download_url))
    artifact = download_url.rsplit('/', 1)
    artifact = artifact[1]

    if not os.path.exists(tmp_dir):
        logging.debug('Creating dir: %s' % tmp_dir)
        os.makedirs(tmp_dir)

    logging.debug('Downloading to dir: %s' % tmp_dir)
    if verify_ssl:
        subprocess.check_call(["curl",
                               "-s",
                               "--cacert",
                               ca_bundle_file,
                               "-o",
                               tmp_dir + '/' + artifact,
                               download_url])
    else:
        logging.warn('ssl cert check disabled for download URL: %s' % download_url)
        subprocess.check_call(["curl",
                               "-s",
                               "-k",
                               "-o",
                               tmp_dir + '/' + artifact,
                               download_url])


def get_py_version(location, package_name):
    version = re.sub(package_name + '-', '', location)
    version = re.sub('.tar.gz', '', version)
    return version


def install_py_package(pip, payload):
    logging.info('Installing package: %s' % payload)
    logging.info('Install command: %s install --pre -U %s' % (pip, payload))
    subprocess.check_call([pip,
                           "install",
                           "--pre",
                           "-U",
                           payload])
    logging.info('The following packages are installed:')
    subprocess.check_call([pip,
                           "freeze"])


def create_py_virtualenv(deploy_path):
    logging.info('Creating Virtualenv: %s' % deploy_path)
    subprocess.check_call(['virtualenv',
                           deploy_path])


def download_artifacts(deployments, deploys_todo, tmp_dir, ct_env):

    # download everything first
    for t in deploys_todo:
        # Set our vars
        deploy_id = deployments[t]['deploy_id']
        package_name = deployments[t]['package_name']
        artifact_assignment_id = (
            deployments[t]['artifact_assignment_id'])
        deploy_path = deployments[t]['deploy_path']
        download_url = deployments[t]['download_url']
        revision = deployments[t]['revision']
        artifact_type = deployments[t]['artifact_type']
        repo_type = deployments[t]['repo_type']

        logging.debug('deploy_id=%s,artifact_assignment_id=%s,'
                      'deploy_path=%s,download_url=%s,'
                      'revision=%s,artifact_type=%s,repo_type=%s'
                      % (deploy_id,
                         artifact_assignment_id,
                         deploy_path,
                         download_url,
                         revision,
                         artifact_type,
                         repo_type))

        deploy_id = str(deploy_id)
        # Add the deploy id to the tmp dir
        tmp_dir_id = tmp_dir + '/' + deploy_id
        # Clean the deploy dir first
        clean_dir(tmp_dir_id)

        # download artifacts
        if artifact_type == 'war' or artifact_type == 'tar' or artifact_type == 'jar':
            logging.debug('artifact_type is %s.' % artifact_type)
            if repo_type == 'http':
                dl_artifact_http(tmp_dir_id, download_url, revision)
                if artifact_type == 'jar':
                    # Rename the jar
                    artifact = download_url.rsplit('/', 1)
                    artifact = artifact[1]
                    logging.info('Renaming %s file %s to %s' % (artifact_type, tmp_dir_id + '/' + artifact, tmp_dir_id + '/' + package_name))
                    subprocess.check_call(['mv',
                               tmp_dir_id + '/' + artifact,
                               tmp_dir_id + '/' + package_name])
        elif artifact_type == 'conf':
            logging.debug('artifact_type is conf')
            if repo_type == 'svn':
                # Append ct_env so that source and detination are
                # env scpecific
                download_url = download_url + '/' + ct_env
                tmp_dir_id = tmp_dir_id + '/' + ct_env
                t_svn = tSvn(download_url)
                t_svn.dl_artifact_svn_conf(tmp_dir_id,
                                           download_url,
                                           revision)
            elif repo_type == 'git':
                t_git = tGit(download_url)
                t_git.dl_artifact_git_conf(tmp_dir_id,
                                           download_url,
                                           revision)
        elif artifact_type == 'python':

            artifact = download_url.rsplit('/', 1)
            logging.info('Package Name is: %s' % package_name)
            logging.info('Artifact is: %s' % artifact[1])
            version = get_py_version(artifact[1], package_name)
            logging.info('Version is: %s' % version)
 
            pip = deploy_path + '/bin/pip'
            payload = package_name + '==' + version

            if os.path.isfile(pip):
                install_py_package(pip, payload)
            else:
                create_py_virtualenv(deploy_path)
                install_py_package(pip, payload)


def unzip(source_filename=None, dest_dir=None):
    zipper = zipfile.ZipFile(source_filename)
    zipper.extractall(dest_dir)


def untar(source_filename=None, dest_dir=None):
    tar_file = tarfile.open(source_filename, 'r:gz')
    tar_file.extractall(dest_dir)


def sync_artifact_war(tmp_dir_id, deploy_path, artifact_file):
    tmp_artifact_path_current = tmp_dir_id + '/current'
    # explode the war
    logging.debug('Expanding artifact : %s in %s'
                  % (artifact_file,
                     tmp_artifact_path_current))
    unzip(tmp_dir_id + '/' + artifact_file, tmp_artifact_path_current)

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


def sync_artifact_tar(tmp_dir_id, deploy_path, artifact_file):
    # explode the tar
    tmp_artifact_path_current = tmp_dir_id + '/current'
    logging.debug('Expanding artifact : %s in %s'
                  % (artifact_file,
                     tmp_artifact_path_current))
    untar(tmp_dir_id + '/' + artifact_file, tmp_artifact_path_current)

    # FIXME: needs checking for files vs. dirs
    dirs = os.listdir(tmp_artifact_path_current)

    # rsync it
    for d in dirs:
        logging.debug('Rsyncing %s to %s'
                      % (tmp_artifact_path_current + '/' + d,
                         deploy_path))
        subprocess.check_call(["rsync",
                               "-ra",
                               "--delete",
                               tmp_artifact_path_current + '/' + d,
                               deploy_path])


def sync_artifact_jar(tmp_dir_id, deploy_path, artifact_file):
    # rsync it
    logging.debug('Rsyncing %s to %s'
                  % (tmp_dir_id,
                     deploy_path))
    subprocess.check_call(["rsync",
                           "-ra",
                           "--delete",
                           tmp_dir_id + '/',
                           deploy_path])


def sync_artifact_conf(tmp_dir_id=None, deploy_path=None):
    logging.debug('Rsyncing %s to %s' % (tmp_dir_id, deploy_path))
    subprocess.check_call(["rsync", "-ra", tmp_dir_id + '/', deploy_path])


def sync_artifacts(deployments, deploys_todo, tmp_dir, ct_env):

    # sync artifacts next
    for s in deploys_todo:
        # Set our vars
        deploy_id = deployments[s]['deploy_id']
        artifact_assignment_id = (
            deployments[s]['artifact_assignment_id'])
        deploy_path = deployments[s]['deploy_path']
        revision = deployments[s]['revision']
        artifact_type = deployments[s]['artifact_type']
        repo_type = deployments[s]['repo_type']
        download_url = deployments[s]['download_url']
        items = download_url.rsplit('/', 1)
        artifact_file = items[1]

        logging.info('Syncing deployment to %s' % deploy_path)
        logging.debug('deploy_id=%s,artifact_assignment_id=%s,'
                      'deploy_path=%s,revision=%s,'
                      'artifact_type=%s,repo_type=%s,'
                      'artifact_file=%s'
                      % (deploy_id,
                         artifact_assignment_id,
                         deploy_path,
                         revision,
                         artifact_type,
                         repo_type,
                         artifact_file))

        deploy_id = str(deploy_id)
        # Add the deploy id to the tmp dir
        tmp_dir_id = tmp_dir + '/' + deploy_id

        # do the sync artifacts
        if artifact_type == 'war':
            logging.debug('artifact_type is war.')
            sync_artifact_war(tmp_dir_id, deploy_path, artifact_file)
        elif artifact_type == 'tar':
            logging.debug('artifact_type is tar.')
            sync_artifact_tar(tmp_dir_id, deploy_path, artifact_file)
        elif artifact_type == 'jar':
            logging.debug('artifact_type is jar.')
            sync_artifact_jar(tmp_dir_id, deploy_path, artifact_file)
        elif artifact_type == 'conf':
            logging.debug('artifact_type is conf.')
            tmp_dir_id = tmp_dir_id + '/' + ct_env
            sync_artifact_conf(tmp_dir_id, deploy_path)


def update_manifest(deployments, manifest_file):
    # update the manifest with everything we just installed from the db.
    logging.debug('Updating the manifest file')

    db_deployments = parse_db_deployments(deployments)

    date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    string = date + " " + str(db_deployments) + "\n"

    with open(manifest_file, "a") as myfile:
        myfile.write(string)

    logging.debug('Updated manifest file %s with application '
                  'assignments: %s'
                  % (manifest_file,
                     str(db_deployments)))


def main(argv):

    parser = optparse.OptionParser(
        description='Deploy configs and artifacts automagically.')
    parser.add_option('--app-id',
                      '-i',
                      action='store',
                      type='string',
                      dest='application_id',
                      help='Application ID in twonicorn DB',
                      default=None)
    parser.add_option('--config',
                      '-c',
                      action='store',
                      type='string',
                      dest='config_file',
                      help='Config file to use.',
                      default='/app/twonicorn/conf/twonicorn.conf')
    parser.add_option('--secrets',
                      '-s',
                      action='store',
                      type='string',
                      dest='secrets_config_file',
                      help='Secret config file to use.',
                      default='/app/secrets/twonicorn-deploy.conf')
    parser.add_option('--verbose',
                      '-v',
                      action='store_true',
                      dest='verbose',
                      help='Log debug messages to the log file',
                      default=None)

    (options, args) = parser.parse_args()

    # Make sure we have required options
    required = ['application_id']
    for r in required:
        if not options.__dict__[r]:
            print >> sys.stderr, \
                "\nERROR - Required option is missing: %s\n" % r
            parser.print_help()
            sys.exit(2)

    # Load facts
    t_facts = tFacter()
    ct_env = t_facts.get_fact('ct_env')
    ct_loc = t_facts.get_fact('ct_loc')

    # Get the config
    config = ConfigParser.ConfigParser()
    config.read(options.config_file)
    secrets_config = ConfigParser.ConfigParser()
    secrets_config.read(options.secrets_config_file)
    # Globalizing these. Otherwise will be passing them all over the
    # place for no reason.
    global verify_ssl
    global ca_bundle_file
    global api_protocol
    global svn_user
    global svn_pass
    api_protocol = config.get('main', 'tcw.api_protocol')
    verify_ssl = bool(config.get('deploy', 'verify_ssl'))
    ca_bundle_file = config.get('deploy', 'ca_bundle_file')
    svn_user = config.get('main', 'tcw.svn_user')
    svn_pass = secrets_config.get('main', 'tcw.svn_pass')

    tcw_host = config.get('main', 'tcw.host')
    manifest_dir = config.get('main', 'manifest.dir')
    tmp_dir = config.get('main', 'tmp.dir')
    log_file = config.get('deploy', 'log.file')
    application_id = options.application_id

    manifest_file = manifest_dir + '/application_' \
        + options.application_id + '.txt'

    if options.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    # Set up logging to file
    logging.basicConfig(level=log_level,
                        format='%(asctime)s %(levelname)-8s- %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        filename=log_file,
                        filemode='a')

    console = logging.StreamHandler()
    console.setLevel(log_level)
    formatter = logging.Formatter('%(levelname)-8s- %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

    logging.info('Twonicorn START')
    if options.verbose:
        logging.info('Debug messages are being written to the log file : %s'
                     % log_file)
    logging.info('Getting deployment information from twonicorn api : %s'
                 % tcw_host)

    # Do all the things
    deployments = get_application_deploys(tcw_host, application_id, ct_env, ct_loc)
    deploys_todo = check_manifest(deployments, manifest_file)

    # We know what we have to do, so let's go
    if deploys_todo:
        download_artifacts(deployments, deploys_todo, tmp_dir, ct_env)
        sync_artifacts(deployments, deploys_todo, tmp_dir, ct_env)
        # update the manifest with everything from the db.
        update_manifest(deployments, manifest_file)

    logging.info('Twonicorn END')
    print ""

if __name__ == '__main__':
    main(sys.argv[1:])
