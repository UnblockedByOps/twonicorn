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

@view_config(route_name='status', permission='view', renderer='arsenalweb:templates/status.pt')
def view_status(request):
    page_title = 'Status'
    au = get_authenticated_user(request)
    params = {'status': None,
             }
    for p in params:
        try:
            params[p] = request.params[p]
        except:
            pass

    status = params['status']
    status_id = request.matchdict['resource']

    return {'page_title': page_title,
            'au': au,
            'status': status,
            'status_id': status_id,
           }
