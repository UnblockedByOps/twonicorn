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
from pyramid.response import Response
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


@view_config(route_name='applications', permission='view', renderer='twonicornweb:templates/applications.pt')
def view_applications(request):
    page_title = 'Applications'
    user = get_user(request)

    perpage = 50
    offset = 0

    try:
        offset = int(request.GET.getone("start"))
    except:
        pass

    try:
        q = DBSession.query(Application)
        total = q.count()
        applications = q.limit(perpage).offset(offset)
    except Exception, e:
        conn_err_msg = e
        return Response(str(conn_err_msg), content_type='text/plain', status_int=500)

    return {'layout': site_layout(),
            'page_title': page_title,
            'user': user,
            'perpage': perpage,
            'offset': offset,
            'total': total,
            'applications': applications,
           }

