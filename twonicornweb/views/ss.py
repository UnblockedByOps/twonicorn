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
from pyramid.httpexceptions import HTTPFound
from pyramid.response import Response
from datetime import datetime
import logging
import re
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
                 application_name = None,
                 nodegroup = None,
                 code_review = None,
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
        self.application_name = application_name
        self.nodegroup = nodegroup
        self.code_review = code_review
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
    ui.application_name = request.POST['application_name']
    ui.nodegroup = request.POST['nodegroup']
    ui.code_review = request.POST['code_review']
    ui.job_server = request.POST['job_server']
    ui.job_prefix = request.POST['job_prefix'].upper()
    try:
        ui.job_abs = request.POST['job_abs']
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

    if ui.code_review == 'review':
        ui.job_review_name = ui.job_ci_name + '_Build-review'
    ui.job_code_name = ui.job_ci_name + '_Build-artifact'
    ui.job_conf_name = ui.job_ci_name + '_Build-conf'

    if ui.job_abs:
        ui.job_abs_name = 'https://abs-{0}.prod.cs/{1}_{2}_Run'.format(ui.job_server, ui.job_prefix, ui.git_repo_name.capitalize())

    return ui

def create_git_repo(ui):

    log.info("Creating git repos for {0}".format(ui.git_repo_name))

#    /buildWithParameters?token=TOKEN_NAME&cause=Cause+Text


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
             ca = {'application_name': ui.application_name,
                   'nodegroup': ui.nodegroup,
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

             r = create_application(**ca)
             log.info("Successfully created application: {0}".format(r.location))

             log.info("Creating git repos")
             try:
                 create_git_repo(ui)
             except Exception, e:
                 log.error("Failed to create git repo: {0}".format(e))

             log.info("Creating jenkins jobs")
             processed = 'true'

         except Exception, e:
             log.error("Failed to create application: {0}".format(e))

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
