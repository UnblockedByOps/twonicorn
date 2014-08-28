from pyramid.view import view_config
import TwonicornWebLib


t_core = TwonicornWebLib.Core('/app/twonicorn_web/conf/twonicorn.conf')
t_facts = TwonicornWebLib.tFacter()

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
        applications = t_core.get_application_deploys()
    except:
        pass
    return {'applications': applications, 'perpage': perpage, 'offset': offset }

@view_config(route_name='artifacts', renderer='templates/artifacts.pt')
def view_artifacts(request):
    return {'project': 'twonicorn-ui'}

@view_config(route_name='promote', renderer='templates/promote.pt')
def view_promote(request):
    return {'project': 'twonicorn-ui'}

