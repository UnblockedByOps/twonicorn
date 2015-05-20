from pyramid.view import view_config
from pyramid.response import Response
from sqlalchemy.sql import func
from sqlalchemy import or_
from sqlalchemy import desc
from sqlalchemy.sql import label
from arsenalweb.views import (
    get_authenticated_user,
    site_layout,
    log,
    )
from arsenalweb.models import (
    DBSession,
    )

@view_config(route_name='api', permission='api_write', request_method='PUT', renderer='json')
def write_api(request):
    au = get_authenticated_user(request)

    params = {'format': None,
             }
    for p in params:
        try:
            params[p] = request.params[p]
        except:
            pass

    format = params['format']

#    if format == 'json' or format == 'xml':
    return {'format':format}
