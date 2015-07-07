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
from pyramid.view import view_config
import logging
import re
import requests
import time
from twonicornweb.views import (
    site_layout,
    get_user,
    )
from twonicornweb.views.cp_application import (
    create_application,
    )
from twonicornweb.models import (
    DBSession,
    ArtifactType,
    JenkinsInstance,
    )

log = logging.getLogger(__name__)

class UserInput(object):

    def __init__(self, 
                 project_type = None,
                 project_name = None,
                 code_review = None,
                 auto_tag = None,
                 job_server = None,
                 job_prefix = None,
                 git_code_repo = None,
                 git_conf_repo = None,
                 job_review_name = None,
                 job_code_name = None,
                 job_conf_name = None,
                 job_abs = None,
                 job_abs_name = None,
                 dir_app = None,
                 dir_conf = None):
        self.project_type = project_type
        self.project_name = project_name
        self.code_review = code_review
        self.auto_tag = auto_tag
        self.job_server = job_server
        self.job_prefix = job_prefix
        self.git_code_repo = git_code_repo
        self.git_conf_repo = git_conf_repo
        self.job_review_name = job_review_name
        self.job_code_name = job_code_name
        self.job_conf_name = job_conf_name
        self.job_abs = job_abs
        self.job_abs_name = job_abs_name
        self.dir_app = dir_app
        self.dir_conf = dir_conf


def format_user_input(request, ui):

    ui.project_type = request.POST['project_type']
    ui.project_name = request.POST['project_name']
    ui.code_review = request.POST['code_review']
    ui.job_server = request.POST['job_server']
    ui.job_prefix = request.POST['job_prefix'].upper()
    try:
        ui.job_abs = request.POST['job_abs']
    except:
        pass
    try:
        ui.auto_tag = request.POST['auto_tag']
        ui.code_review = None
    except:
        pass

    # Convert camel case, spaces and dashes to underscore for job naming and dir creation.
    a = re.compile('((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))')
    convert = a.sub(r'_\1', ui.project_name).lower()
    convert = convert.replace(" ","_")
    convert = convert.replace("-","_")

    if ui.project_type == 'war':
        log.info("self service project type is war")

        ui.dir_app = '/app/tomcat/webapp'
        ui.dir_conf = '/app/tomcat/conf'

    if ui.project_type == 'jar':
        log.info("self service project type is jar")

        ui.dir_app = '/app/{0}/lib'.format(convert)
        ui.dir_conf = '/app/{0}/conf'.format(convert)

    if ui.project_type == 'python':
        log.info("self service project type is python")

        ui.dir_app = '/app/{0}/venv'.format(convert)
        ui.dir_conf = '/app/{0}/conf'.format(convert)

    if ui.project_type == 'tar':
        log.info("self service project type is tar")

        ui.dir_app = '/app/{0}'.format(convert)
        ui.dir_conf = '/app/{0}/conf'.format(convert)

    # space to dash
    ui.git_repo_name = ui.project_name.replace(" ","-")
    # Camel case to dash
    b = re.compile('((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))')
    ui.git_repo_name = b.sub(r'-\1', ui.git_repo_name).lower()

    ui.git_code_repo = 'ssh://$USER@gerrit.ctgrd.com:29418/{0}'.format(ui.git_repo_name)
    ui.git_conf_repo = 'ssh://$USER@gerrit.ctgrd.com:29418/{0}-conf'.format(ui.git_repo_name)
    ui.job_ci_name = 'https://ci-{0}.prod.cs/{1}_{2}'.format(ui.job_server, ui.job_prefix, ui.git_repo_name.capitalize())

    if ui.code_review == 'true' and not ui.auto_tag:
        ui.job_review_name = ui.job_ci_name + '_Build-review'
    ui.job_code_name = ui.job_ci_name + '_Build-artifact'
    ui.job_conf_name = ui.job_ci_name + '_Build-conf'

    if ui.job_abs:
        ui.job_abs_name = 'https://abs-{0}.prod.cs/{1}_{2}_Run'.format(ui.job_server, ui.job_prefix, ui.git_repo_name.capitalize())

    return ui


def jenkins_get(url):

    # Hardcode for now
    verify_ssl = False

    logging.info('Requesting data from jenkins: %s' % url)
    r = requests.get(url, verify=verify_ssl)

    if r.status_code == requests.codes.ok:
        logging.info('Response data: %s' % r.json())
        return r

    else:

        logging.info('There was an error querying Jenkins: '
                      'http_status_code=%s,reason=%s,request=%s'
                      % (r.status_code, r.reason, url))
        return None


def check_all_resources(repo_name, *jobs):
    """Make sure that jenkins jobs and git repos don't already exist
       before beginning"""
    if check_git_repo(repo_name):
        if check_jenkins_jobs(*jobs):
            return True
    return None


def check_git_repo(repo_name):
    """Check and make sure that the code and conf repos don't
       already exist in gerrit"""

    # FIXME: Make the gerrit server configurable
    r = requests.get('https://qat.gerrit.ctgrd.com/projects/{0}'.format(repo_name), verify=False)
    if  r.status_code == 404:
        log.info("repo {0} does not exist, continuing".format(repo_name))
        r = requests.get('https://qat.gerrit.ctgrd.com/projects/{0}-conf'.format(repo_name), verify=False)
        if  r.status_code == 404:
            log.info("repo {0}-conf does not exist, continuing".format(repo_name))
            return True
        else:
            log.info("repo {0}-conf already exists, aborting".format(repo_name))
    else:
        log.info("repo {0} already exists, aborting".format(repo_name))

    return None


def check_jenkins_jobs(jobs):
    """Make sure that jenkins jobs don't already exist before beginning"""
    # Hardcode for now
    verify_ssl = False

    for j in jobs:
        logging.info('Verifying job does not already exist: %s' % j)
        r = requests.get(j, verify=verify_ssl)
        if r.status_code == requests.codes.ok:
            logging.error('Jenkins job: %s already exists, aborting.' % j)
            return None

    return True


def get_last_build(job):
    """get the last build number of a jenkins job"""

    r = requests.get('{0}/lastBuild/api/json'.format(job))
    last = r.json()
    log.info('Last build id is: {0}'.format(last['number']))
    return last['number']


def check_create_git_repo(git_job, git_repo_name, last_id):
    """Make sure the jenkins job completed successfully"""

    check_id = last_id + 1
    final_id = check_id + 4
    while (check_id < final_id): 
        count = 0
        # Try each id for 30 seconds
        while (count < 5): 
            log.info('Checking iteration {0} of Job: {1}/{2}'.format(count, git_job, check_id))
            # Start with the build id we got passed plus one, go up from there
            r = requests.get('{0}/{1}/api/json'.format(git_job, check_id), verify=False)
            if r.status_code == 200:
                last = r.json()
                log.info('Checking description: {0} against project name: {1} for SUCCESS'.format(last['description'], git_repo_name))
                if last['description'] == git_repo_name and last['result'] == 'SUCCESS':
                    log.info('Found successful git creation job for: {0}'.format(git_repo_name))
                    return True
            count = count + 1
            time.sleep(5)

        check_id = check_id + 1

    log.error('Unable to find successful git creation job for: {0}'.format(git_repo_name))


def create_git_repo(ui, git_job, git_token):

    # Get the last id of the jenkins job to start. 
    last_id = get_last_build(git_job)

    log.info("Creating git repos for {0}".format(ui.git_repo_name))
    
    code_review = 'No-code-review'
    if ui.code_review == 'true':
        code_review = 'Code-review'
    
    payload = {'token': git_token,
               'PROJECT_TYPE': code_review,
               'PROJECT_NAME': ui.git_repo_name,
               'PROJECT_DESCRIPTION': '{0} created by SELF_SERVICE'.format(ui.project_name),
               'CREATE_CONFIG_REPO': 'true',
               'cause': 'ss_{0}'.format(ui.git_repo_name)
    }
    try:
        log.info('Triggering git repo creation job: {0}/buildWithParameters params: {1}'.format(git_job, payload))
        r = requests.get('{0}/buildWithParameters'.format(git_job), params=payload)
    except Exception, e:
        log.error("Failed to trigger git repo creation: {0}".format(e))
        return None
    
    if r.status_code == 200:
        # check to make sure the job succeeded
        log.info("Checking for job success")

        if check_create_git_repo(git_job, ui.git_repo_name, int(last_id)):
            log.info("Git repo creation job finished successfully")
            return True
        else:
            log.erro("Failed to create git repos.")

def get_deploy_ids(host, uri):

    try:
        url = 'http://{0}{1}'.format(host, uri)
        log.info("Querying application: {0}".format(url))
        l = requests.get(url)
        j = l.json()
        deploy_ids = {j[0]['artifact_type']: j[0]['deploy_id'], j[1]['artifact_type']: j[1]['deploy_id']}
        return deploy_ids

    except Exception, e:
        log.error("Failed to retrieve deploy ids: {0}".format(e))
        return None


@view_config(route_name='ss', permission='view', renderer='twonicornweb:templates/ss.pt')
def view_ss(request):

    page_title = 'Self Service'
    subtitle = 'Add an application'
    user = get_user(request)

    params = {'mode': None,
              'confirm': None,
              'processed': None,
             }
    for p in params:
        try:
            params[p] = request.params[p]
        except:
            pass

    mode = params['mode']
    confirm = params['confirm']
    processed = params['processed']
    ui = UserInput()

    # Build some lists of choices
    q = DBSession.query(ArtifactType)
    q = q.filter(ArtifactType.name != 'conf')
    artifact_types = q.all()

    q = DBSession.query(JenkinsInstance)
    jenkins_instances = q.all()


    if 'form.edit' in request.POST:
         log.info("Editing self service")

         ui = format_user_input(request, ui)

    if 'form.preprocess' in request.POST:
         log.info("Pre-processing self service")

         ui = format_user_input(request, ui)

         log.info('doing stuff: mode=%s,updated_by=%s'
                  % (mode,
                     user['login']))

         confirm = 'true'

    if 'form.confirm' in request.POST:
         log.info("Processing self service request")
         try:
             ui = format_user_input(request, ui)

             log.info("Creating twonicorn application")
             ca = {'application_name': ui.project_name,
                   'nodegroup': 'SELF_SERVICE',
                   'artifact_types': [ui.project_type, 'conf'],
                   'deploy_paths': [ui.dir_app, ui.dir_conf],
                   'package_names': [ui.project_name, ''],
                   'day_start': '1',
                   'day_end': '4',
                   'hour_start': '8',
                   'minute_start': '0',
                   'hour_end': '17',
                   'minute_end': '0',
                   'updated_by': user['login'],
                   'ss': True
             }

             app = create_application(**ca)
             if app.status_code == 201:
                 log.info("Successfully created application: {0}".format(app.location))

                 # Set up the list of jobs to check
                 jobs = [ui.job_code_name, ui.job_conf_name]
                 if ui.code_review == 'true' and not ui.auto_tag:
                     jobs.append(ui.job_review_name)

                 if check_all_resources(ui.git_repo_name, jobs):
                     if create_git_repo(ui, request.registry.settings['ss.git_job'], request.registry.settings['ss.git_token']):

                         deploy_ids = get_deploy_ids(request.host, app.location)
                         if deploy_ids:
                             print "DEPLOY_IDS: ", deploy_ids
                             print "DEPLOY_ID conf: ", deploy_ids['conf']

                             
                             log.info("Creating jenkins jobs")

                         processed = 'true'

         except Exception, e:
             log.error("Failed to complete self service: {0}".format(e))

    return {'layout': site_layout(),
            'page_title': page_title,
            'user': user,
            'subtitle': subtitle,
            'mode': mode,
            'confirm': confirm,
            'processed': processed,
            'ui': ui,
            'artifact_types': artifact_types,
            'jenkins_instances': jenkins_instances,
           }
