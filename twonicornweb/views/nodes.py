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


@view_config(route_name='nodes', permission='view', renderer='arsenalweb:templates/nodes.pt')
def view_nodes(request):
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

    type = params['type']
    if type == 'ec2':
        host = 'aws1prdtcw1.opsprod.ctgrd.com'
        uniq_id = 'i-303a6c4a'
        ng = 'tcw'
        vhost = 'aws1'
    elif type == 'rds':
        host = 'aws1devcpd1.csqa.ctgrd.com'
        uniq_id = 'aws1devcpd1.cltftmkcg4dd.us-east-1.rds.amazonaws.com'
        ng = 'none'
        vhost = 'aws1'
    else:
        host = 'vir1prdpaw1.prod.cs'
        uniq_id = '6A:37:2A:68:E1:B0'
        ng = 'paw'
        vhost = 'vir1prdxen41.prod.cs'

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

