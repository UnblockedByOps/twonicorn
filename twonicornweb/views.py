import TwonicornWebLib
from pyramid.view import view_config, forbidden_view_config
from pyramid.renderers import get_renderer
from pyramid.httpexceptions import HTTPFound
from pyramid.security import remember, forget
from pyramid_ldap import get_ldap_connector, groupfinder


t_core = TwonicornWebLib.Core('/app/twonicorn_web/conf/twonicorn.conf')
t_facts = TwonicornWebLib.tFacter()
denied = ''

def site_layout():
    renderer = get_renderer("templates/global_layout.pt")
    layout = renderer.implementation().macros['layout']
    return layout

def format_user(user):
    # Make the name readable
    (last,first,junk) = user.split(',',2)
    last = last.rstrip('\\')
    last = last.strip('CN=')
    return(first,last)

def format_groups(groups):

    formatted = []
    for g in range(len(groups)):
        formatted.append(find_between(groups[g], 'CN=', ',OU='))
    return formatted

def find_between(s, first, last):
    try:
        start = s.index( first ) + len( first )
        end = s.index( last, start )
        return s[start:end]
    except ValueError:
        return ""

@view_config(route_name='logout', renderer='templates/logout.pt')
def logout(request):

    headers = forget(request)
    request.response.headers = headers

    # No idea why I have to re-define these, but I do or it poops itself
    request.response.content_type = 'text/html'
    request.response.charset = 'UTF-8'
    request.response.status = '200 OK'
    
    return {'message': 'You have been logged out'}

@view_config(route_name='login', renderer='templates/login.pt')
@forbidden_view_config(renderer='templates/login.pt')
def login(request):

    user = ''
    groups = ''
    first = ''
    last = ''
    denied = ''

    url = request.current_route_url()
    path = request.path
    if path == '/login':
        url = '/'
    login = ''
    password = ''
    error = ''
    page_title = 'Login'

    if 'form.submitted' in request.POST:
        login = request.POST['login']
        password = request.POST['password']
        connector = get_ldap_connector(request)
        data = connector.authenticate(login, password)

        if data is not None:
            dn = data[0]
            headers = remember(request, dn)
            return HTTPFound(url, headers=headers)
        else:
            error = 'Invalid credentials'

    if request.authenticated_userid:
        # Get and format user/groups
        user = request.authenticated_userid
        (first,last) = format_user(user)
    
        groups = groupfinder(user, request)
        groups = format_groups(groups)

        if request.path == '/login':
          error = 'You are already logged in'
          page_title = 'Already Logged In'
          denied = True
        else:
          error = 'You do not have permission to access that page'
          page_title = 'Access Denied'
          denied = True

    return {'layout': site_layout(),
            'page_title': page_title,
            'user': user,
            'groups': groups,
            'first':first,
            'last': last,
            'login_url': url,
            'login': login,
            'password': password,
            'error': error,
            'denied': denied,
           }

@view_config(route_name='home', permission='view', renderer='templates/home.pt')
def view_home(request):

    page_title = 'Home'

    # Get and format user/groups
    user = request.authenticated_userid
    (first,last) = format_user(user)

    groups = groupfinder(user, request)
    groups = format_groups(groups)

    return {'layout': site_layout(),
            'page_title': page_title,
            'user': user,
            'groups': groups,
            'first':first,
            'last': last,
            'denied': denied
           }

@view_config(route_name='applications', permission='view', renderer='templates/applications.pt')
def view_applications(request):

    page_title = 'Applications'

    # Get and format user/groups
    user = request.authenticated_userid
    (first,last) = format_user(user)

    groups = groupfinder(user, request)
    groups = format_groups(groups)

    perpage = 10
    offset = 0
    end = 10

    try:
        offset = int(request.GET.getone("start"))
        end = perpage + offset
    except:
        pass

    try:
        apps = t_core.list_applications()
        total = len(apps)
        applications = apps[offset:end]

    except:
        raise
    return {'layout': site_layout(),
            'page_title': page_title,
            'user': user,
            'groups': groups,
            'first':first,
            'last': last,
            'applications': applications,
            'perpage': perpage,
            'offset': offset,
            'total': total,
            'denied': denied
           }

@view_config(route_name='deploys', permission='view', renderer='templates/deploys.pt')
def view_deploys(request):

    page_title = 'Deploys'

    # Get and format user/groups
    user = request.authenticated_userid
    (first,last) = format_user(user)

    groups = groupfinder(user, request)
    groups = format_groups(groups)

    params = {'application_id': None,
              'nodegroup': None,
              'history': None,
              'deploy_id': None,
              'env': None}
    for p in params:
        try:
            params[p] = request.params[p]
        except:
            pass

    application_id = params['application_id']
    nodegroup = params['nodegroup']
    history = params['history']
    deploy_id = params['deploy_id']
    env = params['env']

    deploys_dev = None
    deploys_qat = None
    deploys_prd = None
    hist_list = None

    if application_id:
        try: 
            deploys_dev = t_core.list_deploys('dev',application_id,nodegroup)
            deploys_qat = t_core.list_deploys('qat',application_id,nodegroup)
            deploys_prd = t_core.list_deploys('prd',application_id,nodegroup)
        except:
            raise
    elif nodegroup:
        try:
            deploys_dev = t_core.list_deploys('dev',application_id,nodegroup)
            deploys_qat = t_core.list_deploys('qat',application_id,nodegroup)
            deploys_prd = t_core.list_deploys('prd',application_id,nodegroup)
        except:
            raise

    if history:
        try:
            hist_list = t_core.list_history(env,deploy_id)
        except:
            raise

    return {'layout': site_layout(),
            'page_title': page_title,
            'user': user,
            'groups': groups,
            'first':first,
            'last': last,
            'deploys_dev': deploys_dev,
            'deploys_qat': deploys_qat,
            'deploys_prd': deploys_prd,
            'application_id': application_id,
            'nodegroup': nodegroup,
            'history': history,
            'hist_list': hist_list,
            'env': env,
            'deploy_id': deploy_id,
            'denied': denied
           }

@view_config(route_name='promote', permission='prom', renderer='templates/promote.pt')
def view_promote(request):

    page_title = 'Promote'

    # Get and format user/groups
    user = request.authenticated_userid
    (first,last) = format_user(user)

    groups = groupfinder(user, request)
    groups = format_groups(groups)

    return {'layout': site_layout(),
            'page_title': page_title,
            'user': user,
            'groups': groups,
            'first':first,
            'last': last,
            'denied': denied
           }

@view_config(route_name='help', permission='view', renderer='templates/help.pt')
def view_help(request):

    page_title = 'Help'

    # Get and format user/groups
    user = request.authenticated_userid
    (first,last) = format_user(user)

    groups = groupfinder(user, request)
    groups = format_groups(groups)

    return {'layout': site_layout(),
            'page_title': page_title,
            'user': user,
            'groups': groups,
            'first':first,
            'last': last,
            'denied': denied
           }

@view_config(route_name='user', permission='view', renderer='templates/user.pt')
def view_user(request):

    page_title = 'User Data'

    # Get and format user/groups
    user = request.authenticated_userid
    (first,last) = format_user(user)

    groups = groupfinder(user, request)
    groups = format_groups(groups)

    return {'layout': site_layout(),
            'page_title': page_title,
            'user': user,
            'groups': groups,
            'first':first,
            'last': last,
            'denied': denied,
           }
