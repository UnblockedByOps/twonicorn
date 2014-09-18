import TwonicornWebLib
import ConfigParser
from pyramid.view import view_config, forbidden_view_config
from pyramid.renderers import get_renderer
from pyramid.httpexceptions import HTTPFound
from pyramid.security import remember, forget
from pyramid.session import signed_serialize, signed_deserialize
from pyramid_ldap import get_ldap_connector, groupfinder


t_core = TwonicornWebLib.Core('/app/twonicorn_web/conf/twonicorn.conf')
t_facts = TwonicornWebLib.tFacter()
denied = ''
prod_groups = ['Unix_Team']

# Parse the secret config
secret_config_file = ConfigParser.ConfigParser()
secret_config_file.read('/app/secrets/twonicorn.conf')
cookie_token = secret_config_file.get('cookie', 'token')

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

def validate_username_cookie(cookieval):

    (name, encrypted) = cookieval.split('-')
    signed_deserialize(encrypted, cookie_token)

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
            encrypted = signed_serialize(login, cookie_token)
            headers = remember(request, dn)
            headers.append(('Set-Cookie', 'un=' + str(login) + '-' + str(encrypted) + '; Max-Age=604800; Path=/'))

            try:
                 validate_username_cookie(request.cookies['un'])
            except:
                print "DIE"
            
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
          error = 'You do not have permission to access this page'
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

    try:
         validate_username_cookie(request.cookies['un'])
    except:
        print "DIE"

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
            'perpage': perpage,
            'offset': offset,
            'total': total,
            'applications': applications,
            'denied': denied,
           }

@view_config(route_name='deploys', permission='view', renderer='templates/deploys.pt')
def view_deploys(request):

    page_title = 'Deploys'

    # Get and format user/groups
    user = request.authenticated_userid
    (first,last) = format_user(user)

    groups = groupfinder(user, request)
    groups = format_groups(groups)

    perpage = 10
    offset = 0
    end = 10
    total = 0
    prod_auth = False

    # Check if the user is authorized to do stuff to prod
    for a in prod_groups:
        if a in groups:
            prod_auth = True
            break

    try:
        offset = int(request.GET.getone("start"))
        end = perpage + offset
    except:
        pass

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
            h_list = t_core.list_history(env,deploy_id)
            total = len(h_list)
            hist_list = h_list[offset:end]
        except:
            raise

    return {'layout': site_layout(),
            'page_title': page_title,
            'user': user,
            'groups': groups,
            'first':first,
            'last': last,
            'perpage': perpage,
            'offset': offset,
            'total': total,
            'deploys_dev': deploys_dev,
            'deploys_qat': deploys_qat,
            'deploys_prd': deploys_prd,
            'application_id': application_id,
            'nodegroup': nodegroup,
            'history': history,
            'hist_list': hist_list,
            'env': env,
            'deploy_id': deploy_id,
            'denied': denied,
            'prod_auth': prod_auth
           }

@view_config(route_name='promote', permission='view', renderer='templates/promote.pt')
def view_promote(request):

    page_title = 'Promote'
    prod_auth = False
    denied = ''
    message = ''
    promote = ''

    params = {'deploy_id': None,
              'artifact_id': None,
              'to_env': None,
              'state': None,
              'commit': 'false'
             }
    for p in params:
        try:
            params[p] = request.params[p]
        except:
            pass

    deploy_id = params['deploy_id']
    artifact_id = params['artifact_id']
    to_env = params['to_env']
    state = params['state']
    commit = params['commit']

    # Get and format user/groups
    user = request.authenticated_userid
    (first,last) = format_user(user)

    groups = groupfinder(user, request)
    groups = format_groups(groups)

    # Check if the user is authorized to do stuff to prod
    for a in prod_groups:
        if a in groups:
            prod_auth = True
            break

    if not prod_auth and state == 'current':
        denied = True
        message = 'You do not have permission to perform the promote action on production!'

    # Displaying artifact to be stage to prod
    if artifact_id and commit == 'false':
        try:
            promote = t_core.list_promotion(deploy_id, artifact_id)
        except:
            raise

    # Actually promoting
    if artifact_id and commit == 'true':
        try:
            promote = t_core.promote(deploy_id, artifact_id, options.user)
        except:
            raise

    return {'layout': site_layout(),
            'page_title': page_title,
            'user': user,
            'groups': groups,
            'first':first,
            'last': last,
            'denied': denied,
            'message': message,
            'prod_auth': prod_auth,
            'deploy_id': deploy_id,
            'artifact_id': artifact_id,
            'to_env': to_env,
            'state': state,
            'commit': commit,
            'promote': promote,
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
