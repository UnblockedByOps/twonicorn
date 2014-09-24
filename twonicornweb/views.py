import TwonicornWebLib
import ConfigParser
from pyramid.view import view_config, forbidden_view_config
from pyramid.renderers import get_renderer
from pyramid.httpexceptions import HTTPFound
from pyramid.security import remember, forget
from pyramid.session import signed_serialize, signed_deserialize
from pyramid_ldap import get_ldap_connector, groupfinder
import logging
log = logging.getLogger(__name__)


t_core = TwonicornWebLib.Core('/app/twonicorn_web/conf/twonicorn.conf', '/app/secrets/twonicorn.conf', inject=True)
t_facts = TwonicornWebLib.tFacter()
denied = ''
prod_groups = ['CM_Team']
admin_groups = ['CM_Team']

# Parse the secret config - would like to pass this from __init__.py
secret_config_file = ConfigParser.ConfigParser()
secret_config_file.read('/app/secrets/twonicorn.conf')
cookie_token = secret_config_file.get('cookie', 'token')

def site_layout():
    renderer = get_renderer("templates/global_layout.pt")
    layout = renderer.implementation().macros['layout']
    return layout

def get_user(request):
    """ Gets all the user information for an authenticated  user. Checks groups
        and permissions, and returns a dict of everything. """

    prod_auth = False
    admin_auth = False

    try:
        id = request.authenticated_userid
        (first,last) = format_user(id)
        groups = format_groups(groupfinder(id, request))
        auth = True
        pretty = "%s %s" % (first, last)
    except Exception, e:
        log.error("%s (%s)" % (Exception, e))
        (pretty, id, ad_login, groups, first, last, auth, prd_auth, admin_auth) = ('', '', '', '', '', '', False, False, False)

    try:
        ad_login = validate_username_cookie(request.cookies['un'])
    except:
        return HTTPFound('/logout?message=Your cookie has been tampered with. You have been logged out')

    # Check if the user is authorized to do stuff to prod
    for a in prod_groups:
        if a in groups:
            prod_auth = True
            break

    # Check if the user is authorized as an admin
    for a in admin_groups:
        if a in groups:
            admin_auth = True
            break

    user = {}
    user['id'] = id
    user['ad_login'] = ad_login
    user['groups'] = groups
    user['first'] = first
    user['last'] = last
    user['loggedin'] = auth
    user['prod_auth'] = prod_auth
    user['admin_auth'] = admin_auth
    user['pretty'] = pretty

    return (user)

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
    """ Returns the username if it validates. Otherwise throws
    an exception"""

#    return signed_deserialize(cookieval, 'titspervert')
    return signed_deserialize(cookieval, cookie_token)

@view_config(route_name='logout', renderer='templates/logout.pt')
def logout(request):

    message = 'You have been logged out'

    try:
        if request.params['message']:
            message = request.params['message']
    except:
        pass

    headers = forget(request)
    # Do I really need this?
    headers.append(('Set-Cookie', 'un=; Max-Age=0; Path=/'))
    request.response.headers = headers

    # No idea why I have to re-define these, but I do or it poops itself
    request.response.content_type = 'text/html'
    request.response.charset = 'UTF-8'
    request.response.status = '200 OK'
    
    return {'message': message}

@view_config(route_name='login', renderer='templates/login.pt')
@forbidden_view_config(renderer='templates/login.pt')
def login(request):
    page_title = 'Login'

    user = get_user(request)
    denied = ''

    if request.referer:
        referer_host = request.referer.split('/')[2]
    else:
        referer_host = None

    if request.referer and referer_host == request.host and request.referer.split('/')[3][:6] != 'logout':
        return_url = request.referer
    elif request.path != '/login':
        return_url = request.url
    else:
        return_url = '/'

    login = ''
    password = ''
    error = ''

    if 'form.submitted' in request.POST:
        login = request.POST['login']
        password = request.POST['password']
        connector = get_ldap_connector(request)
        data = connector.authenticate(login, password)

        if data is not None:
            dn = data[0]
            encrypted = signed_serialize(login, cookie_token)
            #encrypted = signed_serialize(login, 'titspervert')
            headers = remember(request, dn)
            headers.append(('Set-Cookie', 'un=' + str(encrypted) + '; Max-Age=604800; Path=/'))

            return HTTPFound(request.POST['return_url'], headers=headers)
        else:
            error = 'Invalid credentials'

    if request.authenticated_userid:

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
            'return_url': return_url,
            'login': login,
            'password': password,
            'error': error,
            'denied': denied,
           }

@view_config(route_name='home', permission='view', renderer='templates/home.pt')
def view_home(request):

    page_title = 'Home'
    user = get_user(request)

    return {'layout': site_layout(),
            'page_title': page_title,
            'user': user,
            'denied': denied
           }

@view_config(route_name='applications', permission='view', renderer='templates/applications.pt')
def view_applications(request):

    page_title = 'Applications'
    user = get_user(request)

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
            'perpage': perpage,
            'offset': offset,
            'total': total,
            'applications': applications,
            'denied': denied,
           }

@view_config(route_name='deploys', permission='view', renderer='templates/deploys.pt')
def view_deploys(request):

    page_title = 'Deploys'
    user = get_user(request)

    perpage = 10
    offset = 0
    end = 10
    total = 0

    try:
        offset = int(request.GET.getone("start"))
        end = perpage + offset
    except:
        pass


    params = {'application_id': None,
              'nodegroup': None,
              'history': None,
              'deploy_id': None,
              'env': None,
              'to_env': None,
              'to_state': None,
              'commit': None,
              'artifact_id': None,
             }
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
    to_env = params['to_env']
    to_state = params['to_state']
    commit = params['commit']
    artifact_id = params['artifact_id']

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
            'to_env': to_env,
            'to_state': to_state,
            'commit': commit,
            'artifact_id': artifact_id,
            'denied': denied,
           }

@view_config(route_name='promote', permission='view', renderer='templates/promote.pt')
def view_promote(request):

    page_title = 'Promote'
    user = get_user(request)

    denied = ''
    message = ''
    promote = ''

    params = {'deploy_id': None,
              'artifact_id': None,
              'to_env': None,
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
    commit = params['commit']

    if not user['prod_auth'] and to_env == 'prd':
        to_state = '3'
    else:
        to_state = '2'

    # Displaying artifact to be stage to prod
    if artifact_id and commit == 'false':
        try:
            promote = t_core.list_promotion(deploy_id, artifact_id)
        except:
            raise

    if artifact_id and commit == 'true':
        if not user['prod_auth'] and to_env == 'prd' and to_state == '2':
            denied = True
            message = 'You do not have permission to perform the promote action on production!'
        else:
            # Actually promoting
            try:
                promote = t_core.promote(deploy_id, artifact_id, to_env, to_state, user['ad_login'])
                results = t_core.list_app_details_by_deploy(deploy_id)
                return_url = '/deploys?application_id=%s&nodegroup=%s&artifact_id=%s&to_env=%s&to_state=%s&commit=%s' % (results[0][0], results[0][1], artifact_id, to_env, to_state, commit)
                return HTTPFound(return_url)
            except:
                raise

    return {'layout': site_layout(),
            'page_title': page_title,
            'user': user,
            'denied': denied,
            'message': message,
            'deploy_id': deploy_id,
            'artifact_id': artifact_id,
            'to_env': to_env,
            'to_state': to_state,
            'commit': commit,
            'promote': promote,
           }

@view_config(route_name='help', permission='view', renderer='templates/help.pt')
def view_help(request):

    page_title = 'Help'
    user = get_user(request)

    return {'layout': site_layout(),
            'page_title': page_title,
            'user': user,
            'denied': denied
           }

@view_config(route_name='user', permission='view', renderer='templates/user.pt')
def view_user(request):

    page_title = 'User Data'
    user = get_user(request)

    return {'layout': site_layout(),
            'page_title': page_title,
            'user': user,
            'denied': denied,
           }

@view_config(route_name='admin', permission='view', renderer='templates/admin.pt')
def view_admin(request):

    page_title = 'Admin'
    user = get_user(request)

    return {'layout': site_layout(),
            'page_title': page_title,
            'user': user,
            'prod_groups': prod_groups,
            'denied': denied,
           }
