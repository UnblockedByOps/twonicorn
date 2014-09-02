from pyramid.view import view_config
import TwonicornWebLib


t_core = TwonicornWebLib.Core('conf/twonicorn.conf')
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

    try:
        application_id = request.params['application_id']
    except:
        application_id = None
        pass

    try:
        nodegroup = request.params['nodegroup']
    except:
        nodegroup = None
        pass


    if application_id:
        try: 
            deploys_dev = t_core.list_deploys('dev',application_id,nodegroup)
            deploys_qat = t_core.list_deploys('qat',application_id,nodegroup)
            deploys_prd = t_core.list_deploys('prd',application_id,nodegroup)
        except:
            raise
        return {'deploys_dev': deploys_dev, 'deploys_qat': deploys_qat,'deploys_prd': deploys_prd,'application_id': application_id}
    elif nodegroup:
        try:
            deploys_dev = t_core.list_deploys('dev',application_id,nodegroup)
            deploys_qat = t_core.list_deploys('qat',application_id,nodegroup)
            deploys_prd = t_core.list_deploys('prd',application_id,nodegroup)
        except:
            raise
        return {'deploys_dev': deploys_dev, 'deploys_qat': deploys_qat,'deploys_prd': deploys_prd,'application_id': application_id}
    else:
        return {'project': 'twonicorn-ui'}

@view_config(route_name='promote', renderer='templates/promote.pt')
def view_promote(request):
    return {'project': 'twonicorn-ui'}

