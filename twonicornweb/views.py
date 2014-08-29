from pyramid.view import view_config
import TwonicornWebLib


t_core = TwonicornWebLib.Core('/app/twonicorn_web/conf/twonicorn.conf')
t_facts = TwonicornWebLib.tFacter()

@view_config(route_name='home', renderer='templates/home.pt')
def view_home(request):
    return {'project': 'twonicorn-ui'}

@view_config(route_name='applications', renderer='templates/applications.pt')
def view_applications(request):

    try:
        applications = t_core.list_applications()
    except:
        raise
    return {'applications': applications, 'total': len(applications)}

@view_config(route_name='deploys', renderer='templates/deploys.pt')
def view_deploys(request):

    application_id = int(request.GET['application_id'])
    nodegroup = int(request.GET['nodegroup'])

    if application_id:
        try: 
            deploys = t_core.list_deploys(application_id)
        except:
            raise
        return {'deploys': deploys, 'total': len(deploys), 'application_id': application_id}
    elif nodegroup:
        try:
            deploys = t_core.list_deploys(application_id)
        except:
            raise
        return {'deploys': deploys, 'total': len(deploys), 'application_id': application_id}
    else:
        return {'project': 'twonicorn-ui'}

@view_config(route_name='promote', renderer='templates/promote.pt')
def view_promote(request):
    return {'project': 'twonicorn-ui'}

