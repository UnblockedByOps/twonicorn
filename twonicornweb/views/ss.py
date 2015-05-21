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


@view_config(route_name='ss', permission='view', renderer='twonicornweb:templates/ss.pt')
def view_ss(request):

    page_title = 'Self Service'
    subtitle = 'Add an application'
    user = get_user(request)

    params = {'mode': None,
              'commit': None,
             }
    for p in params:
        try:
            params[p] = request.params[p]
        except:
            pass

    mode = params['mode']
    commit = params['commit']
    error_msg = None

    if mode == 'confirm':

       if not commit:

           if 'form.submitted' in request.POST:
                nodegroup = request.POST['nodegroup']
                artifact_types = request.POST.getall('artifact_type')


                log.info('UPDATE TIME WINDOW: application_id=%s,day_start=%s,day_end=%s,hour_start=%s,minute_start=%s,hour_end=%s,minute_end=%s,updated_by=%s'
                         % (application_id,
                            day_start,
                            day_end,
                            hour_start,
                            minute_start,
                            hour_end,
                            minute_end,
                            user['login']))

                return_url = '/deploys?application_id=%s&nodegroup=%s' % (application_id, nodegroup)
                return HTTPFound(return_url)


    return {'layout': site_layout(),
            'page_title': page_title,
            'user': user,
            'subtitle': subtitle,
            'mode': mode,
            'commit': commit,
            'error_msg': error_msg,
           }
