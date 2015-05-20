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


class PlaceResponse(object):
    name = ""
    place_id = ""
    avg = ""
    pa = ""

    def __init__(self, name, place_id, avg, pa):
        self.name = name
        self.place_id = place_id
        self.avg = avg
        self.pa = pa

def _place_response(name, place_id, avg, pa):
    response = PlaceResponse(name, place_id, avg, pa)
    return response


@view_config(route_name='home', permission='view', renderer='arsenalweb:templates/home.pt')
def view_home(request):
    page_title = 'Home'
    au = get_authenticated_user(request)
    results = False
    params = {'type': 'vir',
             }
    for p in params:
        try:
            params[p] = request.params[p]
        except:
            pass
    print au
    # print dir(request)
#    print request.authenticated_userid
#    print request.authorization
#    print request.cookies
#    print request.effective_principals
#    print request.has_permission

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

