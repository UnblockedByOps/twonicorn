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
from sqlalchemy.orm.exc import NoResultFound
import logging
from twonicornweb.views import (
    site_layout,
    get_user,
    )

from twonicornweb.models import (
    DBSession,
    Application,
    )

log = logging.getLogger(__name__)


@view_config(route_name='deploys', permission='view', renderer='twonicornweb:templates/deploys.pt')
def view_deploys(request):

    page_title = 'Deploys'
    user = get_user(request)

    perpage = 50
    offset = 0
    end = 10
    total = 0
    app = None

    try:
        offset = int(request.GET.getone("start"))
        end = perpage + offset
    except:
        pass


    params = {'application_id': None,
              'history': None,
              'deploy_id': None,
              'env': None,
              'to_env': None,
              'to_state': None,
              'commit': None,
              'artifact_id': None,
             }
    for p in params:
        try:
            params[p] = request.params[p]
        except:
            pass

    application_id = params['application_id']
    deploy_id = params['deploy_id']
    env = params['env']
    to_env = params['to_env']
    to_state = params['to_state']
    commit = params['commit']
    artifact_id = params['artifact_id']

    if application_id:
        try:
            q = DBSession.query(Application)
            q = q.filter(Application.application_id == application_id)
            app = q.one()
        except NoResultFound, e:
            error_msg = "No such application id: {0} Exception: {1}".format(application_id, e)
            log.error(error_msg)
            raise Exception("No such application id: {0}".format(application_id))
        except Exception, e:
            error_msg = "Error: {0}".format(e)
            log.error(error_msg)
            raise Exception(error_msg)

    return {'layout': site_layout(),
            'page_title': page_title,
            'user': user,
            'perpage': perpage,
            'offset': offset,
            'total': 1000, #STUB
            'app': app,
            'application_id': application_id,
            'history': None,
            'hist_list': None,
            'histassignments': None,
            'env': env,
            'deploy_id': deploy_id,
            'to_env': to_env,
            'to_state': to_state,
            'commit': commit,
            'artifact_id': artifact_id,
           }
