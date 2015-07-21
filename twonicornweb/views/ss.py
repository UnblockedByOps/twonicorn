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
from pyramid.httpexceptions import HTTPInternalServerError
import logging
import re
import requests
from requests.auth import HTTPBasicAuth
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
    JenkinsTemplate,
    )

log = logging.getLogger(__name__)

class UserInput(object):

    def __init__(self, 
                 project_type = None,
                 project_name = None,
                 nodegroup = 'SELF_SERVICE',
                 code_review = None,
                 autosnap = None,
                 job_server = None,
                 job_prefix = None,
                 git_repo_name = None,
                 git_code_repo = None,
                 git_code_repo_url = None,
                 git_conf_repo = None,
                 git_conf_repo_url = None,
                 job_review_name = None,
                 job_autosnap_name = None,
                 job_code_name = None,
                 job_conf_name = None,
                 job_rolling_restart_name = None,
                 job_review_url = None,
                 job_autosnap_url = None,
                 job_code_url = None,
                 job_conf_url = None,
                 job_rolling_restart_url = None,
                 job_ci_base_url = None,
                 job_abs = None,
                 job_abs_name = None,
                 job_abs_base_url = None,
                 job_abs_url = None,
                 deploy_id_code = None,
                 deploy_id_conf = None,
                 dir_app = None,
                 dir_conf = None,
                 app_id = None,
                 app_url = None,
                 ct_class = None):
        self.project_type = project_type
        self.project_name = project_name
        self.nodegroup = nodegroup
        self.code_review = code_review
        self.autosnap = autosnap
        self.job_server = job_server
        self.job_prefix = job_prefix
        self.git_repo_name = git_repo_name
        self.git_code_repo = git_code_repo
        self.git_code_repo_url = git_code_repo_url
        self.git_conf_repo = git_conf_repo
        self.git_conf_repo_url = git_conf_repo_url
        self.job_review_name = job_review_name
        self.job_autosnap_name = job_autosnap_name
        self.job_code_name = job_code_name
        self.job_conf_name = job_conf_name
        self.job_rolling_restart_name = job_rolling_restart_name
        self.job_review_url = job_review_url
        self.job_autosnap_url = job_autosnap_url
        self.job_code_url = job_code_url
        self.job_conf_url = job_conf_url
        self.job_rolling_restart_url = job_rolling_restart_url
        self.job_ci_base_url = job_ci_base_url
        self.job_abs = job_abs
        self.job_abs_name = job_abs_name
        self.job_abs_base_url = job_abs_base_url
        self.job_abs_url = job_abs_url
        self.deploy_id_code = deploy_id_code
        self.deploy_id_conf = deploy_id_conf
        self.dir_app = dir_app
        self.dir_conf = dir_conf
        self.app_id = app_id
        self.app_url = app_url
        self.ct_class = ct_class


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
        ui.autosnap = request.POST['autosnap']
        ui.code_review = None
    except:
        pass
    try:
        ui.ct_class = request.POST['ct_class']
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

    ui.git_code_repo = 'ssh://$USER@{0}:29418/{1}'.format(gerrit_server, ui.git_repo_name)
    ui.git_code_repo_url = 'https://{0}/git/gitweb.cgi?p={1}.git'.format(gerrit_server, ui.git_repo_name)
    ui.git_conf_repo = 'ssh://$USER@{0}:29418/{1}-conf'.format(gerrit_server, ui.git_repo_name)
    ui.git_conf_repo_url = 'https://{0}/git/gitweb.cgi?p={1}-conf.git'.format(gerrit_server, ui.git_repo_name)
    ui.job_ci_base_url = 'https://ci-{0}.prod.cs/'.format(ui.job_server)

    job_base_name = '{0}_{1}'.format(ui.job_prefix, ui.git_repo_name.capitalize())

    ui.job_code_name = job_base_name + '_Build-artifact'
    ui.job_code_url = '{0}job/{1}'.format(ui.job_ci_base_url, ui.job_code_name)
    ui.job_conf_name = job_base_name + '_Build-conf'
    ui.job_conf_url = '{0}job/{1}'.format(ui.job_ci_base_url, ui.job_conf_name)

    if ui.project_type == 'war':
        ui.job_rolling_restart_name = job_base_name + '_Rolling-restart'
        ui.job_rolling_restart_url = '{0}job/{1}'.format(ui.job_ci_base_url, ui.job_rolling_restart_name)

    if ui.autosnap:
        ui.job_autosnap_name = job_base_name + '_Build-release'
        ui.job_autosnap_url = '{0}job/{1}'.format(ui.job_ci_base_url, ui.job_autosnap_name)
    if ui.code_review == 'true' and not ui.autosnap:
        ui.job_review_name = job_base_name + '_Build-review'
        ui.job_review_url = '{0}job/{1}'.format(ui.job_ci_base_url, ui.job_review_name)
    if ui.job_abs:
        ui.job_abs_base_url = 'https://abs-{0}.dev.cs/'.format(ui.job_server)
        ui.job_abs_name = '{0}_{1}_Run'.format(ui.job_prefix, ui.git_repo_name.capitalize())
        ui.job_abs_url = '{0}job/{1}'.format(ui.job_abs_base_url, ui.job_abs_name)

    return ui


def check_all_resources(repo_name, jobs):
    """Make sure that jenkins jobs and git repos don't already exist
       before beginning"""
    if check_git_repo(repo_name):
        try:
            check_jenkins_jobs(jobs)
            return True
        except Exception, e:
            log.error("Job validation failure: {0}".format(e))
            raise

    return None


def check_git_repo(repo_name):
    """Check and make sure that the code and conf repos don't
       already exist in gerrit"""

    r = requests.get('https://{0}/projects/{1}'.format(gerrit_server, repo_name), verify=False)
    if  r.status_code == 404:
        log.info("repo {0} does not exist, continuing".format(repo_name))
        r = requests.get('https://{0}/projects/{1}-conf'.format(gerrit_server, repo_name), verify=False)
        if  r.status_code == 404:
            log.info("repo {0}-conf does not exist, continuing".format(repo_name))
            return True
        else:
            msg = "repo {0}-conf already exists, please choose a unique name".format(repo_name)
            log.error(msg)
            raise Exception(msg)
    else:
        msg = "repo {0} already exists, please choose a unique name".format(repo_name)
        log.error(msg)
        raise Exception(msg)

    return None


def check_jenkins_jobs(jobs):
    """Make sure that jenkins jobs don't already exist before beginning"""

    for j in jobs:
        log.info('Verifying job does not already exist: %s' % j)
        r = requests.get(j, verify=False)
        if r.status_code == requests.codes.ok:
            msg = 'Jenkins job: {0} already exists, please choose a unique name.'.format(j)
            log.error(msg)
            raise Exception(msg)
        else:
            log.info('Jenkins job: %s does not already exist, continuing.' % j)

    return True


def get_last_build(job):
    """get the last build number of a jenkins job"""

    log.info('Retrieving last build id')

    try:
        r = requests.get('{0}/lastBuild/api/json'.format(job), verify=False)
        last = r.json()
        if r.status_code == 200:
            log.info('Last build id is: {0}'.format(last['number']))
            return last['number']
        else:
            msg = 'There was an error querying Jenkins: http_status_code=%s,reason=%s,request=%s' % (r.status_code, r.reason, url)
            log.info(msg)
            raise Exception(msg)
    except:
        msg = 'Unable to find last build id for job: {0}'.format(job)
        log.error(msg)
        raise Exception(msg)


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

    msg = 'Unable to find successful git creation job for: {0}'.format(git_repo_name)
    log.error(msg)
    raise Exception(msg)


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
               'PROJECT_DESCRIPTION': 'SELF_SERVICE created [0]'.format(ui.project_name),
               'CREATE_CONFIG_REPO': 'true',
               'cause': 'ss_{0}'.format(ui.git_repo_name)
    }
    try:
        log.info('Triggering git repo creation job: {0}/buildWithParameters params: {1}'.format(git_job, payload))
        r = requests.get('{0}/buildWithParameters'.format(git_job), params=payload, verify=False)
    except Exception, e:
        log.error("Failed to trigger git repo creation: {0}".format(e))
        raise
    
    if r.status_code == 200:
        # check to make sure the job succeeded
        log.info("Checking for job success")

        if check_create_git_repo(git_job, ui.git_repo_name, int(last_id)):
            log.info("Git repo creation job finished successfully")
            return True
        else:
            log.erro("Failed to create git repos.")


def populate_git_conf_repo(ui, git_job, git_token):

    git_conf_project = "{0}-conf".format(ui.git_repo_name)
    file_suffix = 'properties'
    if ui.project_type == 'python':
        file_suffix = 'ini'

    log.info("Populating git conf repo for {0}".format(git_conf_project))

    payload = {'token': git_token,
               'PROJECT': git_conf_project,
               'PROPERTIES_FILE': '{0}.{1}'.format(ui.git_repo_name,file_suffix),
               'cause': 'ss_{0}'.format(git_conf_project)
    }
    try:
        log.info('Triggering git conf repo population job: {0}/buildWithParameters params: {1}'.format(git_job, payload))
        r = requests.get('{0}/buildWithParameters'.format(git_job), params=payload, verify=False)
    except Exception, e:
        log.error("Failed to trigger git repo creation: {0}".format(e))
        raise

    # FIXME: not sureif we care to validate it succeeds. It's not tragic.
    if r.status_code == 200:
        log.info("Git repo population job triggered successfully")
        return True
    else:
        log.erro("Failed to trigger git repo population.")


def get_deploy_ids(host, uri):

    try:
        url = 'http://{0}{1}'.format(host, uri)
        log.info("Querying application: {0}".format(url))
        l = requests.get(url, verify=False)
        j = l.json()
        deploy_ids = {j[0]['artifact_type']: j[0]['deploy_id'], j[1]['artifact_type']: j[1]['deploy_id']}
        return deploy_ids

    except Exception, e:
        log.error("Failed to retrieve deploy ids: {0}".format(e))
        raise

def jenkins_get(url):

    url = url + 'config.xml'

    log.info('Requesting data from jenkins: %s' % url)
    r = requests.get(url, verify=False)

    if r.status_code == requests.codes.ok:
        log.info('Response data: %s' % r.status_code)
        return r

    else:

        log.info('There was an error querying Jenkins: '
                      'http_status_code=%s,reason=%s,request=%s'
                      % (r.status_code, r.reason, url))
        return None


def jenkins_post(url, config_xml):

    try:

        log.info('Posting data to jenkins: %s' % url)
        headers = {'Content-Type': 'text/xml'}
        auth = HTTPBasicAuth(jenkins_user, jenkins_pass)
        r = requests.post(url, verify=False, headers=headers, auth=auth, data=config_xml)
    
        if r.status_code == requests.codes.ok:
            log.info('Success: %s' % r.status_code)
            return r
        else:
            msg = 'There was an error posting to Jenkins: http_status_code={0}s,reason={1},request={2}'.format(r.status_code, r.reason, url)
            log.error(msg)
            raise Exception(msg)

    except Exception, e:
        msg = 'Failed to create jenkins conf job: {0}'.format(e)
        log.error(msg)
        raise Exception(msg)


def get_jenkins_template_url(job_type):
    log.info("Retrieving jenkins tempalte job from DB for job type: {0}".format(job_type))
    try:
        q = DBSession.query(JenkinsTemplate)
        q = q.filter(JenkinsTemplate.job_type == job_type)
        job = q.one()
        log.info("Tempalte job is: {0}".format(job.job_url))
        return job.job_url
    except Exception, e:
        msg = 'Failed to retrieve conf template from db: {0}'.format(e)
        log.error(msg)
        raise Exception(msg)

def jenkins_sub_values(**kwargs):

    try:

        url = kwargs.get('url', None)
        project_name = str(kwargs.get('project_name', None))
        git_repo_name = str(kwargs.get('git_repo_name', None))
        app_id = str(kwargs.get('app_id', None))
        deploy_id = str(kwargs.get('deploy_id', None))
        ct_class = str(kwargs.get('ct_class', None))
        rolling_restart_job = str(kwargs.get('rolling_restart_job', None))

        r = jenkins_get(url)

        log.info('Substituting values into template: {0}'.format(url))

        config_xml = r.content.replace('__CHANGE_ME_PACKAGE_NAME__', project_name)
        config_xml = config_xml.replace('__CHANGE_ME_GIT_REPO_NAME__', git_repo_name)
        config_xml = config_xml.replace('__CHANGE_ME_APP_ID__', app_id)
        config_xml = config_xml.replace('__CHANGE_ME_DEPLOY_ID__', deploy_id)
        config_xml = config_xml.replace('__CHANGE_ME_CT_CLASS__', ct_class)
        config_xml = config_xml.replace('__CHANGE_ME_ROLLING_RESTART_JOB__', rolling_restart_job)
        config_xml = config_xml.replace('<disabled>true</disabled>', '<disabled>false</disabled>')

        return config_xml

    except Exception, e:
        msg = 'Failed jenkins template substitution {0}: {1}'.format(url, e)
        log.error(msg)
        raise Exception(msg)


def create_jenkins_jobs(ui):

    log.info("Creating jenkins jobs")

    try:
        url = get_jenkins_template_url('conf')
        config_xml = jenkins_sub_values(url=url, project_name=ui.project_name, git_repo_name=ui.git_repo_name + '-conf', deploy_id=ui.deploy_id_conf)
        url = '{0}createItem?name={1}'.format(ui.job_ci_base_url, ui.job_conf_name)
        jenkins_post(url, config_xml)

        if ui.code_review == 'true' and not ui.autosnap:
            log.info("Creating code review job: {0}".format(ui.job_review_url))

            url = get_jenkins_template_url('{0}_build_review'.format(ui.project_type))
            config_xml = jenkins_sub_values(url=url, project_name=ui.project_name, git_repo_name=ui.git_repo_name)
            url = '{0}createItem?name={1}'.format(ui.job_ci_base_url, ui.job_review_name)
            jenkins_post(url, config_xml)

        if ui.autosnap:
            log.info("Creating autosnap release job: {0} for deploy id: {1}".format(ui.job_autosnap_url, ui.deploy_id_code))

            url = get_jenkins_template_url('{0}_build_autosnap_release'.format(ui.project_type))
            config_xml = jenkins_sub_values(url=url, project_name=ui.project_name, git_repo_name=ui.git_repo_name, deploy_id=ui.deploy_id_code, rolling_restart_job=ui.job_rolling_restart_name)
            url = '{0}createItem?name={1}'.format(ui.job_ci_base_url, ui.job_autosnap_name)
            jenkins_post(url, config_xml)


            log.info("Creating code autosnap build job: {0} for deploy id: {1}".format(ui.job_code_url, ui.deploy_id_code))
            url = get_jenkins_template_url('{0}_build_autosnap'.format(ui.project_type))
        else:
            log.info("Creating code build job: {0} for deploy id: {1}".format(ui.job_code_url, ui.deploy_id_code))
            url = get_jenkins_template_url('{0}_build'.format(ui.project_type))

        # The main build job
        config_xml = jenkins_sub_values(url=url, project_name=ui.project_name, git_repo_name=ui.git_repo_name, deploy_id=ui.deploy_id_code, rolling_restart_job=ui.job_rolling_restart_name)
        url = '{0}createItem?name={1}'.format(ui.job_ci_base_url, ui.job_code_name)
        jenkins_post(url, config_xml)

        # wars need the rolling restart job
        if ui.project_type == 'war':
            url = get_jenkins_template_url('{0}_rolling_restart'.format(ui.project_type))
            config_xml = jenkins_sub_values(url=url, ct_class=ui.ct_class, rolling_restart_job=ui.job_rolling_restart_name)
            url = '{0}createItem?name={1}'.format(ui.job_ci_base_url, ui.job_rolling_restart_name)
            jenkins_post(url, config_xml)

        if ui.job_abs:
            log.info('Creating skeleton jenkins abs job')
            url = get_jenkins_template_url('abs')
            config_xml = jenkins_sub_values(url=url, app_id=ui.app_id)
            url = '{0}createItem?name={1}'.format(ui.job_abs_base_url, ui.job_abs_name)
            jenkins_post(url, config_xml)

        return True

    except Exception, e:
        msg = 'Failed to create all jenkins jobs: {0}'.format(e)
        log.error(msg)
        raise Exception(msg)


@view_config(route_name='ss', permission='view', renderer='twonicornweb:templates/ss.pt')
def view_ss(request):

    # Globalizing these. Otherwise will be passing them all over the
    # place for no reason.
    global jenkins_user
    global jenkins_pass
    global gerrit_server
    global verify_ssl
    jenkins_user = request.registry.settings['ss.jenkins_user']
    jenkins_pass = request.registry.settings['ss.jenkins_pass']
    gerrit_server = request.registry.settings['ss.gerrit_server']
    verify_ssl = request.registry.settings['ss.verify_ssl']

    page_title = 'Self Service'
    subtitle = 'Add an application'
    user = get_user(request)
    error_msg = None

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

        # Set up the list of jobs to check
        jobs = [ui.job_code_url, ui.job_conf_url]
        if ui.code_review == 'true' and not ui.autosnap:
            jobs.append(ui.job_review_url)
         
        try:
            check_all_resources(ui.git_repo_name, jobs)
            confirm = 'true'
        except Exception, e:
            error_msg = e

    if 'form.confirm' in request.POST:
        log.info("Processing self service request")
        try:
            ui = format_user_input(request, ui)

            # FIXME: Should only set package name for projects that need it.
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
            ui.app_id = app.location.rsplit('=', 1)[1]
            ui.app_url = '/deploys?application_id={0}'.format(ui.app_id)
            if app.status_code == 201:
                log.info("Successfully created application: {0}".format(app.location))

                if create_git_repo(ui, request.registry.settings['ss.git_job'], request.registry.settings['ss.git_token']):

                    populate_git_conf_repo(ui, request.registry.settings['ss.git_conf_populate_job'], request.registry.settings['ss.git_token'])

                    deploy_ids = get_deploy_ids(request.host, app.location)
                    if deploy_ids:
                        ui.deploy_id_conf = deploy_ids['conf']
                        ui.deploy_id_code = deploy_ids[ui.project_type]

                        create_jenkins_jobs(ui)

                    processed = 'true'

        except Exception, e:
            error_msg = "Failed to complete self service: {0}".format(e)
            log.error(error_msg)
            raise Exception(error_msg)

    return {'layout': site_layout(),
            'page_title': page_title,
            'user': user,
            'subtitle': subtitle,
            'mode': mode,
            'confirm': confirm,
            'processed': processed,
            'error_msg': error_msg,
            'ui': ui,
            'artifact_types': artifact_types,
            'jenkins_instances': jenkins_instances,
           }
