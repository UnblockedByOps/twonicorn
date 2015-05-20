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

@view_config(route_name='api', request_method='GET', renderer='json')
@view_config(route_name='api', request_method='GET', request_param='format=json', renderer='json')
@view_config(route_name='api', request_method='GET', request_param='format=xml', renderer='xml')
def read_api(request):
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
    return {'read_api':'true'}
