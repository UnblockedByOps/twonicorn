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
import sys
import os
import logging
import optparse
import ConfigParser
import re
import subprocess
import git
import requests
from requests.auth import HTTPBasicAuth

try:
    import pysvn
except ImportError:
    # pysvn is not friendly, no pip or easy_install option.
    # If import fails, we don't have svn support.
    pass

# requests is chatty
logging.getLogger("requests").setLevel(logging.WARNING)


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


class tSvn:

    def __init__(self, url=None):
        self.url = url

        # Set up our client object
        try:
            self.client = pysvn.Client()
            self.client.callback_ssl_server_trust_prompt = (
                self.ssl_server_trust_prompt)
            self.client.callback_get_login = self.get_login
        except NameError:
            logging.error('pysn module is absent, no svn support')


    def ssl_server_trust_prompt(self, trust_dict):
        # we know what we're connecting to, no need to validate
        return (True, 0, True)

    def get_login(self, realm, username, may_save):
        # we know what we're connecting to, no need to validate
        # FIXME: read from conf
        return (True, "hudson", "hudson", False)

    def cmp_revision_svn(self, revision=None, db_rev=None, env=None):

        check_url = self.url + "/" + env + "/"

        logging.info('Comparing revision: %s with db revision: %s '
                     'for url: %s'
                     % (revision[:8],
                        db_rev,
                        check_url))

        result = self.client.diff_summarize(check_url,
                                            revision1=pysvn.Revision(
                                                pysvn.opt_revision_kind.number,
                                                db_rev),
                                            url_or_path2=check_url,
                                            revision2=pysvn.Revision(
                                                pysvn.opt_revision_kind.number,
                                                revision),
                                            recurse=True,
                                            ignore_ancestry=False)

        logging.debug('Result is: %s' % (result))

        if result:
            logging.info('Change detected between revision: %s and db '
                         'revision: %s for env: %s'
                         % (revision[:8],
                            db_rev,
                            env))
            return env
        else:
            logging.info('No change detected between revision: %s and db '
                         'revision: %s for env: %s'
                         % (revision[:8],
                            db_rev,
                            env))


class tGit:

    def __init__(self, url=None):
        self.url = url

        # Need this because our cert is lame
        os.environ['GIT_SSL_NO_VERIFY'] = 'true'

    def cmp_revision_git(self, revision=None, db_rev=None, env=None):

        # This is basically replicating this:
        # git diff --name-only cc2cd 16357 conf/prd
        logging.info('Comparing revision: %s with db '
                     'revision: %s for env: %s'
                     % (revision[:8],
                        db_rev,
                        env))
        test_dir = "conf/" + env

        if (os.path.isdir(test_dir)):
            repo = git.Repo(test_dir)
            commits_list = repo.commit(db_rev)
            env_match = "^" + env + "/"
            logging.debug('REGEX string is : %s' % env_match)

            found = False
            for x in commits_list.diff(revision):
                logging.debug('ex is: %s' % (x))
                if x.a_blob is not None and re.match(env_match, x.a_blob.path):
                    logging.debug('XA: %s ENV: %s' % (x.a_blob, env))
                    logging.info('Change detected between revision: %s and '
                                 'db revision: %s for env: %s'
                                 % (revision[:8],
                                    db_rev,
                                    env))
                    found = True
                    return env
                elif x.b_blob is not None and re.match(env_match,
                                                       x.b_blob.path):
                    logging.debug('XB: %s ENV: %s' % (x.b_blob, env))
                    logging.info('Change detected between revision: %s and '
                                 'db revision: %s for env: %s'
                                 % (revision[:8],
                                    db_rev,
                                    env))
                    found = True
                    return env

            # Have to check this condition outside the loop or we will get a
            # log line for every file that changed between two revisions,
            # regardless of what environment the files are in.
            if not found:
                logging.info('No change detected between revision: %s and '
                             'db revision: %s for env: %s'
                             % (revision[:8],
                                db_rev,
                                env))

        else:
            logging.info('Skipping due to no directory in '
                         'git repository for env : %s'
                         % env)



def api_submit(request, user=None, password=None):

    # Fetch the list of deploys for the application
    # This becomes the api call
    api_url = (api_protocol
               + '://'
               + api_host
               + request)

    if user:
        logging.info('Submitting data to API: %s' % api_url)
        r = requests.put(api_url, verify=verify_ssl_cert, auth=HTTPBasicAuth(user, password))
    else:
        logging.info('Requesting data from API: %s' % api_url)
        r = requests.get(api_url, verify=verify_ssl_cert)

    if r.status_code == requests.codes.ok:

        logging.debug('Response data: %s' % r.json())
        return r.json()

    elif r.status_code == requests.codes.conflict:

        logging.info('Artifact location/revision combination '
                     'is not unique. Nothing to do.')

        logging.info('twoni-plete')
        print ""
        sys.exit(0)

    else:

        logging.error('There was an error querying the API: '
                      'http_status_code=%s,reason=%s,request=%s'
                      % (r.status_code, r.reason, api_url))
        logging.info('twoni-plete')
        print ""
        sys.exit(2)


def insert_artifact(repo_id, location, revision, branch):

    logging.info('Inserting artifact into twonicorn...')

    request = ('/api/artifact?'
               + 'repo_id='
               + repo_id
               + '&location='
               + location
               + '&revision='
               + revision
               + '&branch='
               + branch)
               
    results = api_submit(request, api_user, api_pass)
    artifact_id = results[0]['artifact_id']
    artifact_id = str(artifact_id)

    return artifact_id


def assign_artifact(deploy_id, artifact_id, env, user):

    logging.info('Assigning artifact_id: %s to env: %s'
                 % (artifact_id, env))

    request = ('/api/artifact_assignment?'
               + 'deploy_id='
               + deploy_id
               + '&artifact_id='
               + artifact_id
               + '&env='
               + env
               + '&updated_by='
               + user)

    results = api_submit(request, api_user, api_pass)
    artifact_assignment_id = results[0]['artifact_assignment_id']
    artifact_assignment_id = str(artifact_assignment_id)

    logging.info('New artifact assignment created: %s'
                 % artifact_assignment_id)

    return artifact_assignment_id


def get_artifact_type(deploy_id):

    logging.info('Retrieving artifact type from twonicorn...')

    request = ('/api/artifact_types?'
               + 'deploy_id='
               + deploy_id)

    # what type are we? For confs we have to compare
    response = api_submit(request)
    artifact_type = response[0]['artifact_type']

    logging.debug('Artifact type: %s' % artifact_type)

    return artifact_type


def get_envs():

    request = '/api/envs'

    logging.info('Retrieving environment list from the API...')
    response = api_submit(request)

    return response


def get_latest_conf_details(deploy_id, env, loc):

    revision = None
    repo_type = None
    download_url = None

    # For prod, we want to compare against the latest revision in init.
    if env == 'prd':
        get_state = 'init'
    else:
        get_state = 'current'

    logging.info('Retrieving latest revision from the API for env: %s' % env)

    request = ('/api/deploy?'
               + 'id='
               + deploy_id
               + '&loc='
               + loc
               + '&env='
               + env
               + '&lifecycle='
               + get_state)

    response = api_submit(request)
    try:
        revision = response[0]['revision']
        repo_type = response[0]['repo_type']
        download_url = response[0]['download_url']
    except:
        pass

    logging.debug('Latest revision for env: %s is: %s' % (env, revision))

    return revision, repo_type, download_url


def find_conf_assign_envs(deploy_id, revision, loc):

    # Get the last revision from every env
    assign_envs = []

    envs = get_envs()
    env_names = []
    for e in envs:
        env_names.append(e['name'])

    for env in env_names:

        db_revision, repo_type, download_url = get_latest_conf_details(deploy_id, env, loc)

        # Compare the latst revision in the db to see if files changed
        # for each env if they changed, create an artifact assignment
        # for that env. In dev/qat it is made active, in prod it's
        # made init
        if db_revision:
            logging.debug('Revision for %s '
                          'is: %s'
                          % (env,
                             db_revision))
            if repo_type == 'svn':
                # Set up svn object
                t_svn = tSvn(download_url)
                compare = t_svn.cmp_revision_svn(
                    revision,
                    db_revision,
                    env)
                if compare:
                    assign_envs.append(compare)
            elif repo_type == 'git':
                # set up git object
                t_git = tGit(download_url)
                compare = t_git.cmp_revision_git(
                    revision,
                    db_revision,
                    env)
                if compare:
                    logging.debug('Staging update for: %s' % compare)
                    assign_envs.append(compare)
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
            assign_envs.append(env)

    return assign_envs


def assign_conf_to_envs(deploy_id, artifact_id, assign_envs, user):

    assignments = []

    for assign in assign_envs:

        artifact_assignment_id = assign_artifact(deploy_id,
                                                 artifact_id,
                                                 assign,
                                                 user)
        assignments.append(assign)

        if assign == 'prd':
            promote_url = (api_protocol
                           + '://'
                           + api_host
                           + '/promote?deploy_id='
                           + deploy_id
                           + '&artifact_id='
                           + artifact_id
                           + '&to_env=prd&commit=false')

            logging.info('Promote to prod url: %s' % promote_url)

    return assignments


def main(argv):

    parser = optparse.OptionParser(
        description='Deploy configs and artifacts automagically.')
    parser.add_option('--branch',
                      '-b',
                      action='store',
                      type='string',
                      dest='branch',
                      help='The branch/tag this artifact was built from',
                      default='None')
    parser.add_option('--deploy-id',
                      '-d',
                      action='store',
                      type='string',
                      dest='deploy_id',
                      help='[REQUIRED] Deployment ID in twonicorn DB',
                      default=None)
    parser.add_option('--environment',
                      '-e',
                      action='store',
                      type='string',
                      dest='environment',
                      help='[REQUIRED] Environment to'
                      'assign artifact to in twonicorn DB',
                      default='dev')
    parser.add_option('--repo-id',
                      '-p',
                      action='store',
                      type='string',
                      dest='repo_id',
                      help='[REQUIRED] Repo ID in twonicorn DB',
                      default=None)
    parser.add_option('--revision',
                      '-r',
                      action='store',
                      type='string',
                      dest='revision',
                      help='[REQUIRED] Revision. Only required for configs',
                      default='NULL')
    parser.add_option('--location',
                      '-l',
                      action='store',
                      type='string',
                      dest='location',
                      help='[REQUIRED] Location of artifact in repo',
                      default=None)
    parser.add_option('--user',
                      '-u',
                      action='store',
                      type='string',
                      dest='user',
                      help='[REQUIRED] The user name that will be stored in'
                      'the db as having updated the record.',
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
                      default='/app/secrets/twonicorn.conf')
    parser.add_option('--verbose',
                      '-v',
                      action='store_true',
                      dest='verbose',
                      help='Log debug messages to the log file',
                      default=None)

    (options, args) = parser.parse_args()

    # Make sure we have required options
    required = ['deploy_id',
                'environment',
                'repo_id',
                'revision',
                'location',
                'user']
    for r in required:
        if not options.__dict__[r]:
            print >> sys.stderr, \
                "\nERROR - Required option is missing: %s\n" % r
            parser.print_help()
            sys.exit(2)

    # Prevent from running this script for the prod env
    env_match = "^dev$|^qat$"
    if not re.match(env_match, options.environment):
        print >> sys.stderr, "\nERROR - --environment can only be dev or qat\n"
        sys.exit(2)

    t_facts = tFacter()

    # Facts
    ct_loc = t_facts.get_fact('ct_loc')

    # Parse the config
    config = ConfigParser.ConfigParser()
    config.read(options.config_file)
    secrets_config = ConfigParser.ConfigParser()
    secrets_config.read(options.secrets_config_file)
    log_file = config.get('inject', 'log.file')
    # Globalizing these. Otherwise will be passing them all over the
    # place for no reason.
    global api_host
    global api_user
    global api_pass
    global api_protocol
    global verify_ssl_cert
    api_host = config.get('main', 'tcw.host')
    api_user = config.get('main', 'tcw.api_user')
    api_protocol = config.get('main', 'tcw.api_protocol')
    verify_ssl_cert = config.get('main', 'tcw.verify_ssl_cert')
    api_pass = secrets_config.get('main', 'tcw.api_pass')

    if options.verbose:
        log_level = logging.DEBUG
    else:
        # log_level = logging.INFO
        log_level = logging.INFO

    # Set up logging to file
    logging.basicConfig(level=log_level,
                        format='%(asctime)s %(levelname)-8s- %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        filename=log_file,
                        filemode='a')

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(levelname)-8s- %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

    # Do stuff
    logging.info('Twonicorn START')
    if options.verbose:
        logging.info('Debug messages are being written to the log file : %s'
                     % log_file)
    logging.info('Using twonicorn API : %s'
                 % api_host)

    # Insert the artifact
    artifact_id = insert_artifact(options.repo_id,
                                  options.location,
                                  options.revision,
                                  options.branch)

    artifact_type = get_artifact_type(options.deploy_id)

    if artifact_type == 'conf':

        # figure out what envs we need to make assignments for
        assign_envs = find_conf_assign_envs(options.deploy_id, options.revision, ct_loc)

        # assign confs to all the envs we found
        if assign_envs:
            assignments = assign_conf_to_envs(options.deploy_id, artifact_id, assign_envs, options.user)
            logging.info('Artifact assignments made for the following envronments: %s' % assignments)
        else:
            logging.info('No assignments to be made for any environment')

    else:

        # No need to prepare, just go.
        artifact_assignment_id = assign_artifact(options.deploy_id,
                                                 artifact_id,
                                                 options.environment,
                                                 options.user)

        if options.environment == 'qat':
            promote_url = (api_protocol
                           + '://'
                           + api_host
                           + '/promote?deploy_id='
                           + options.deploy_id
                           + '&artifact_id='
                           + artifact_id
                           + '&to_env=prd&commit=false')
    
            logging.info('Promote to prod url: %s' % promote_url)

    logging.info('Twonicorn END')
    print ""

if __name__ == '__main__':
    main(sys.argv[1:])
