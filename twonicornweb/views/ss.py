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

from twonicornweb.models import (
    DBSession,
    Application,
    Deploy,
    ArtifactType,
    DeploymentTimeWindow,
    JenkinsInstance,
    )

log = logging.getLogger(__name__)

class SearchResult(object):

    def __init__(self, name, cs_id, lat, lon, addr_street, addr_city, addr_state, addr_zip, phone, website):
        self.name = name
        self.cs_id = cs_id
        self.lat = lat
        self.lon = lon
        self.addr_street = addr_street
        self.addr_city = addr_city
        self.addr_state = addr_state
        self.addr_zip = addr_zip
        self.phone = phone
        self.website = website

def init_results():

    results = dict.fromkeys(['project_type',
                             'project_name',
                             'code_review',
                             'job_server',
                             'job_prefix',
                             'git_conf_repo',
                             'job_review_name',
                             'job_code_name',
                             'job_conf_name',
                             'job_abs',
                             'job_abs_name',
                             'dir_app',
                             'dir_conf'])

    return results

def get_results(request, results):

    results['project_type'] = request.POST['project_type']
    results['project_name'] = request.POST['project_name']
    results['code_review'] = request.POST['code_review']
    results['job_server'] = request.POST['job_server']
    results['job_prefix'] = request.POST['job_prefix'].upper()
    try:
        results['job_abs'] = request.POST['job_abs']
    except:
        pass

    # Convert camel case, spaces and dashes to underscore for job naming and dir creation.
    a = re.compile('((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))')
    convert = a.sub(r'_\1', results['project_name']).lower()
    convert = convert.replace(" ","_")
    convert = convert.replace("-","_")

    if results['project_type'] == 'war':
        log.info("self service project type is war")

        results['dir_app'] ='/app/tomcat/webapp'
        results['dir_conf'] ='/app/tomcat/conf'

    if results['project_type'] == 'jar':
        log.info("self service project type is jar")

        results['dir_app'] ='/app/{0}/lib'.format(convert)
        results['dir_conf'] ='/app/{0}/conf'.format(convert)

    if results['project_type'] == 'python':
        log.info("self service project type is python")

        results['dir_app'] ='/app/{0}/venv'.format(convert)
        results['dir_conf'] ='/app/{0}/conf'.format(convert)

    if results['project_type'] == 'tar':
        log.info("self service project type is tar")

        results['dir_app'] ='/app/{0}'.format(convert)
        results['dir_conf'] ='/app/{0}/conf'.format(convert)

    # space to dash
    results['git_repo_name'] = results['project_name'].replace(" ","-")
    # Camel case to dash
    b = re.compile('((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))')
    results['git_repo_name'] = b.sub(r'-\1', results['git_repo_name']).lower()

    results['git_code_repo'] = 'ssh://$USER@gerrit.ctgrd.com:29418/{0}'.format(results['git_repo_name'])
    results['git_conf_repo'] = 'ssh://$USER@gerrit.ctgrd.com:29418/{0}-conf'.format(results['git_repo_name'])
    results['job_ci_name'] = 'https://ci-{0}.prod.cs/{1}_{2}'.format(results['job_server'],results['job_prefix'],results['git_repo_name'].capitalize())

    if results['code_review'] == 'review':
        results['job_review_name'] = results['job_ci_name'] + '_Build-review'
    results['job_code_name'] = results['job_ci_name'] + '_Build-artifact'
    results['job_conf_name'] = results['job_ci_name'] + '_Build-conf'

    if results['job_abs']:
        results['job_abs_name'] = 'https://abs-{0}.prod.cs/{1}_{2}_Run'.format(results['job_server'],results['job_prefix'],results['git_repo_name'].capitalize())

    return results


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
    results = init_results()

    # Build some lists of choices
    q = DBSession.query(ArtifactType)
    q = q.filter(ArtifactType.name != 'conf')
    artifact_types = q.all()

    q = DBSession.query(JenkinsInstance)
    jenkins_instances = q.all()


    if 'form.edit' in request.POST:
         log.info("Editing self service")

         results = get_results(request, results)

    if 'form.preprocess' in request.POST:
         log.info("Pre-processing self service")

         results = get_results(request, results)

         log.info('doing stuff: mode=%s,updated_by=%s'
                  % (mode,
                     user['login']))

         confirm = 'true'

    if 'form.confirm' in request.POST:
         log.info("Processing self service request")
         log.info("Creating twonicorn application")
         log.info("Creating git repos")
         log.info("Creating jenkins jobs")
         processed = 'true'

    return {'layout': site_layout(),
            'page_title': page_title,
            'user': user,
            'subtitle': subtitle,
            'mode': mode,
            'confirm': confirm,
            'processed': processed,
            'results': results,
            'artifact_types': artifact_types,
            'jenkins_instances': jenkins_instances,
           }
