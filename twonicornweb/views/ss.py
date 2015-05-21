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



@view_config(route_name='ss', permission='view', renderer='twonicornweb:templates/ss.pt')
def view_ss(request):

    page_title = 'Self Service'
    subtitle = 'Add an application'
    user = get_user(request)

    params = {'mode': None,
              'confirm': None,
             }
    for p in params:
        try:
            params[p] = request.params[p]
        except:
            pass

    mode = params['mode']
    confirm = params['confirm']
    results = None

    if 'form.process' in request.POST:
         print "process"
         project_type = request.POST['project_type']
         project_name = request.POST['project_name']
         code_review = request.POST['code_review']
         job_server = request.POST['job_server']
         job_prefix = request.POST['job_prefix']

         if project_type == 'tomcat':
             print "tomcat"
             dir_app ='/app/tomcat/webapp'
             dir_conf ='/app/tomcat/conf'
         if project_type == 'python':
             print "python"
             dir_app ='/app/{0}/venv'.format(project_name.replace(" ","_"))
             dir_conf ='/app/{0}/conf'.format(project_name.replace(" ","_"))

         git_repo_name = project_name.replace(" ","-")
         git_code_repo = 'ssh://$USER@gerrit.ctgrd.com:29418/{0}'.format(git_repo_name)
         git_conf_repo = 'ssh://$USER@gerrit.ctgrd.com:29418/{0}-conf'.format(git_repo_name)
         job_part_name = 'https://ci-{0}.prod.cs/{1}_{2}'.format(job_server,job_prefix,project_name.replace(" ","-").capitalize())
         if code_review:
             job_review_name = job_part_name + '_Build-review'
         job_code_name = job_part_name + '_Build-artifact'
         job_conf_name = job_part_name + '_Build-conf'

         results = {'project_type': project_type,
                    'git_code_repo': git_code_repo,
                    'git_conf_repo': git_conf_repo,
                    'job_review_name': job_review_name,
                    'job_code_name': job_code_name,
                    'job_conf_name': job_conf_name,
                    'dir_app': dir_app,
                    'dir_conf': dir_conf,
                   }


         log.info('doing stuff: mode=%s,updated_by=%s'
                  % (mode,
                     user['login']))

         confirm = 'true'

    if 'form.confirm' in request.POST:
         nodegroup = request.POST['nodegroup']

    return {'layout': site_layout(),
            'page_title': page_title,
            'user': user,
            'subtitle': subtitle,
            'mode': mode,
            'confirm': confirm,
            'results': results,
           }
