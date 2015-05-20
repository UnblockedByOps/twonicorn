from pyramid.view import view_config
from pyramid.response import Response
from datetime import datetime
from datetime import timedelta
import arrow
from arsenalweb.views import (
    get_authenticated_user,
    site_layout,
    log,
    )
from arsenalweb.models import (
    DBSession,
    User,
    )


@view_config(route_name='statuses', permission='view', renderer='arsenalweb:templates/statuses.pt')
def view_statuses(request):
    page_title = 'Nodes'
    au = get_authenticated_user(request)
    results = False
    params = {'type': 'vir',
             }
    for p in params:
        try:
            params[p] = request.params[p]
        except:
            pass

    return {'layout': site_layout('max'),
            'page_title': page_title,
            'au': au,
            'results': results,
            'type': type,
            'host': host,
            'uniq_id': uniq_id,
            'ng': ng,
            'vhost': vhost,
           }

