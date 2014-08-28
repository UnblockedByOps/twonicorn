from pyramid.view import view_config
import twonicorn


@view_config(route_name='home', renderer='templates/home.pt')
def view_home(request):
    return {'project': 'twonicorn-ui'}

@view_config(route_name='applications', renderer='templates/applications.pt')
def view_applications(request):
    perpage = 15
    offset = 0

    try:
        offset = int(request.GET.getone("start"))
    except:
        pass

    try:
        dq = DBSession.query(Detection)
        dq = dq.order_by(Detection.detected.desc())
        dets = dq.limit(perpage).offset(offset)
        total = dq.count()
        log.debug(pprint.pformat(dets))
    except DBAPIError, e:
        return Response(conn_err_msg, content_type='text/plain', status_int=500)
    return {'dets': dets, 'perpage': perpage, 'offset': offset, 'total': total }

    return {'project': 'twonicorn-ui'}

@view_config(route_name='artifacts', renderer='templates/artifacts.pt')
def view_artifacts(request):
    return {'project': 'twonicorn-ui'}

@view_config(route_name='promote', renderer='templates/promote.pt')
def view_promote(request):
    return {'project': 'twonicorn-ui'}

