from pyramid.view import view_config, forbidden_view_config
from pyramid.renderers import get_renderer
from pyramid.httpexceptions import HTTPFound
from pyramid.httpexceptions import HTTPServiceUnavailable
from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPBadRequest
from pyramid.httpexceptions import HTTPConflict
from pyramid.security import remember, forget
from pyramid.session import signed_serialize, signed_deserialize
from pyramid_ldap import get_ldap_connector, groupfinder
from pyramid.response import Response
from datetime import datetime
import logging
import os.path
import binascii
from twonicornweb.models import (
    DBSession,
    Application,
    Deploy,
    Artifact,
    ArtifactAssignment,
    ArtifactNote,
    Lifecycle,
    Env,
    Repo,
    RepoType,
    ArtifactType,
    RepoUrl,
    )


log = logging.getLogger(__name__)
denied = ''


def site_layout():
    renderer = get_renderer("twonicornweb:templates/global_layout.pt")
    layout = renderer.implementation().macros['layout']
    return layout

def get_user(request):
    """ Gets all the user information for an authenticated  user. Checks groups
        and permissions, and returns a dict of everything. """

    prod_auth = False
    admin_auth = False
    cp_auth = False

    try:
        id = request.authenticated_userid
        (first,last) = format_user(id)
        groups = format_groups(groupfinder(id, request))
        auth = True
        pretty = "%s %s" % (first, last)
    except Exception, e:
        log.error("%s (%s)" % (Exception, e))
        (pretty, id, ad_login, groups, first, last, auth, prd_auth, admin_auth, cp_auth) = ('', '', '', '', '', '', False, False, False, False)

    try:
        ad_login = validate_username_cookie(request.cookies['un'], request.registry.settings['tcw.cookie_token'])
    except:
        return HTTPFound('/logout?message=Your cookie has been tampered with. You have been logged out')

    # Check if the user is authorized to do stuff to prod
    prod_groups = request.registry.settings['tcw.prod_groups'].splitlines()
    for a in prod_groups:
        if a in groups:
            prod_auth = True
            break

    # Check if the user is authorized as an admin
    admin_groups = request.registry.settings['tcw.admin_groups'].splitlines()
    for a in admin_groups:
        if a in groups:
            admin_auth = True
            break

    # Check if the user is authorized for cp
    cp_groups = request.registry.settings['tcw.cp_groups'].splitlines()
    for a in cp_groups:
        if a in groups:
            cp_auth = True
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
    user['cp_auth'] = cp_auth
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

def validate_username_cookie(cookieval, cookie_token):
    """ Returns the username if it validates. Otherwise throws
    an exception"""

    return signed_deserialize(cookieval, cookie_token)


def basicauth(request, l_login, l_password):
    try:
        authorization = request.environ['HTTP_AUTHORIZATION']
    except:
        return None

    try:
        authmeth, auth = authorization.split(' ', 1)
    except ValueError:  # not enough values to unpack
        return None
    if authmeth.lower() == 'basic':
        try:
            auth = auth.strip().decode('base64')
        except binascii.Error:  # can't decode
            return None
        try:
            login, password = auth.split(':', 1)
        except ValueError:  # not enough values to unpack
            return None

        if login == l_login and password == l_password:
            return True

    return None


@view_config(route_name='healthcheck', renderer='twonicornweb:templates/healthcheck.pt')
def healthcheck(request):

    if os.path.isfile(request.registry.settings['tcw.healthcheck_file']):
        return {'message': 'ok'}
    else:
        return HTTPServiceUnavailable()

@view_config(route_name='logout', renderer='twonicornweb:templates/logout.pt')
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

@view_config(route_name='login', renderer='twonicornweb:templates/login.pt')
@forbidden_view_config(renderer='twonicornweb:templates/login.pt')
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
        return_url = '/applications'

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
            encrypted = signed_serialize(login, request.registry.settings['tcw.cookie_token'])
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

@view_config(route_name='home', permission='view', renderer='twonicornweb:templates/home.pt')
def view_home(request):

    return HTTPFound('/applications')

@view_config(route_name='applications', permission='view', renderer='twonicornweb:templates/applications.pt')
def view_applications(request):
    page_title = 'Applications'
    user = get_user(request)

    perpage = 10
    offset = 0

    try:
        offset = int(request.GET.getone("start"))
    except:
        pass


    try:
        q = DBSession.query(Application)
        total = q.count()
        applications = q.limit(perpage).offset(offset)
    except Exception, e:
        conn_err_msg = e
        return Response(str(conn_err_msg), content_type='text/plain', status_int=500)


    return {'layout': site_layout(),
            'page_title': page_title,
            'user': user,
            'perpage': perpage,
            'offset': offset,
            'total': total,
            'applications': applications,
            'denied': denied,
           }

@view_config(route_name='deploys', permission='view', renderer='twonicornweb:templates/deploys.pt')
def view_deploys(request):

    page_title = 'Deploys'
    user = get_user(request)

    perpage = 10
    offset = 0
    end = 10
    total = 0
    app = None

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
    deploy_id = params['deploy_id']
    env = params['env']
    to_env = params['to_env']
    to_state = params['to_state']
    commit = params['commit']
    artifact_id = params['artifact_id']

    if application_id:
        try:
            q = DBSession.query(Application)
            q = q.filter(Application.application_id == application_id)
            app = q.one()
        except Exception, e:
            conn_err_msg = e
            return Response(str(conn_err_msg), content_type='text/plain', status_int=500)

    return {'layout': site_layout(),
            'page_title': page_title,
            'user': user,
            'perpage': perpage,
            'offset': offset,
            'total': 1000, #STUB
            'app': app,
            'application_id': application_id,
            'nodegroup': nodegroup,
            'history': None,
            'hist_list': None,
            'env': env,
            'deploy_id': deploy_id,
            'to_env': to_env,
            'to_state': to_state,
            'commit': commit,
            'artifact_id': artifact_id,
            'denied': denied,
           }


@view_config(route_name='promote', permission='view', renderer='twonicornweb:templates/promote.pt')
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

    try:
        promote = Artifact.get_promotion(to_env, deploy_id, artifact_id)
    except Exception, e:
        conn_err_msg = e
        return Response(str(conn_err_msg), content_type='text/plain', status_int=500)

    if artifact_id and commit == 'true':
        if not user['prod_auth'] and to_env == 'prd' and to_state == '2':
            denied = True
            message = 'You do not have permission to perform the promote action on production!'
        else:
            # Actually promoting
            try:
                # Convert the env name to the id
                env_id = Env.get_env_id(to_env)

                # Assign
                utcnow = datetime.utcnow()
                promote = ArtifactAssignment(deploy_id=deploy_id, artifact_id=artifact_id, env_id=env_id.env_id, lifecycle_id=to_state, user=user['ad_login'], created=utcnow)
                DBSession.add(promote)
                DBSession.flush()
                
                app = Application.get_app_by_deploy_id(deploy_id)
                return_url = '/deploys?application_id=%s&nodegroup=%s&artifact_id=%s&to_env=%s&to_state=%s&commit=%s' % (app.application_id, app.nodegroup, artifact_id, to_env, to_state, commit)
                return HTTPFound(return_url)
            except Exception, e:
                log.error("Failed to promote artifact (%s)" % (e))

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


@view_config(route_name='api', request_method='GET', renderer='json')
def view_api(request):

    params = {'id': None,
              'env': None,
              'loc': None,
              'lifecycle': None,
             }
    for p in params:
        try:
            params[p] = request.params[p]
        except:
            pass

    id = params['id']
    env = params['env']
    loc = params['loc']
    lifecycle = params['lifecycle']
    results = []

#    if application_id and deploy_id:
#        return HTTPBadRequest()

    if request.matchdict['resource'] == 'application':
        try:
            q = DBSession.query(Application)
            q = q.filter(Application.application_id == id)
            app = q.one()
            print "******************** APPP IS: ", app
        except Exception, e:
            log.error("Failed to retrive data on api call (%s)" % (e))
            return results

        for d in app.deploys:
            each = {}
            a = d.get_assignment(env, lifecycle)
            if a:
                each['deploy_id'] = d.deploy_id
                each['package_name'] = d.package_name
                each['artifact_assignment_id'] = a.artifact_assignment_id
                each['deploy_path'] = d.deploy_path
                each['download_url'] = a.artifact.repo.get_url(loc).url + a.artifact.location
                each['revision'] = a.artifact.revision[:8]
                each['artifact_type'] = d.type.name
                each['repo_type'] = a.artifact.repo.type.name
                each['repo_name'] = a.artifact.repo.name
                each['lifecycle'] = a.lifecycle.name
            results.append(each)

    if request.matchdict['resource'] == 'deploy':
        try:
            q = DBSession.query(Deploy)
            q = q.filter(Deploy.deploy_id == id)
            deploy = q.one()
        except Exception, e:
            log.error("Failed to retrive data on api call (%s)" % (e))
            return results

        each = {}
        a = deploy.get_assignment(env, lifecycle)
        if a:
            each['deploy_id'] = deploy.deploy_id
            each['package_name'] = deploy.package_name
            each['artifact_assignment_id'] = a.artifact_assignment_id
            each['deploy_path'] = deploy.deploy_path
            each['download_url'] = a.artifact.repo.get_url(loc).url + a.artifact.location
            each['revision'] = a.artifact.revision[:8]
            each['artifact_type'] = deploy.type.name
            each['repo_type'] = a.artifact.repo.type.name
            each['repo_name'] = a.artifact.repo.name
            each['lifecycle'] = a.lifecycle.name
        results.append(each)

    if request.matchdict['resource'] == 'artifact':
        try:
            q = DBSession.query(Artifact)
            q = q.filter(Artifact.artifact_id == id)
            artifact = q.one()
        except Exception, e:
            log.error("Failed to retrive data on api call (%s)" % (e))
            return results

        each = {}
        each['artifact_id'] = artifact.artifact_id
        each['branch'] = artifact.branch
        each['created'] = artifact.localize_date
        each['download_url'] = artifact.repo.get_url(loc).url + artifact.location
        each['repo_id'] = artifact.repo_id
        each['repo_type'] = artifact.repo.type.name
        each['revision'] = artifact.revision
        each['valid'] = artifact.valid
        results.append(each)

    if request.matchdict['resource'] == 'envs':
        try:
            q = DBSession.query(Env)
            envs = q.all()
        except Exception, e:
            log.error("Failed to retrive data on api call (%s)" % (e))
            return results

        for e in envs:
            each = {}
            each['env_id'] = e.env_id
            each['name'] = e.name
            results.append(each)

    if request.matchdict['resource'] == 'artifact_types':
        try:
            q = DBSession.query(ArtifactType)
            artifact_types = q.all()
        except Exception, e:
            log.error("Failed to retrive data on api call (%s)" % (e))
            return results

        for a in artifact_types:
            each = {}
            each['artifact_type_id'] = a.artifact_type_id
            each['name'] = a.name
            results.append(each)

    if request.matchdict['resource'] == 'lifecycles':
        try:
            q = DBSession.query(Lifecycle)
            lifecycles = q.all()
        except Exception, e:
            log.error("Failed to retrive data on api call (%s)" % (e))
            return results

        for l in lifecycles:
            each = {}
            each['lifecycle_id'] = l.lifecycle_id
            each['name'] = l.name
            results.append(each)

    # FIXME: Need repo/repo_urls still

    return results


@view_config(route_name='api', request_method='PUT', renderer='json')
def write_api(request):

    # Require auth
    if not basicauth(request, request.registry.settings['tcw.api_user'], request.registry.settings['tcw.api_pass']):
        return HTTPForbidden('Invalid username/password')

    results = []
    params = {'deploy_id': None,
              'artifact_id': None,
              'repo_id': None,
              'env': None,
              'location': None,
              'branch': None,
              'revision': None,
              'user': None,
             }
    for p in params:
        try:
            params[p] = request.params[p]
        except:
            pass

    deploy_id = params['deploy_id']
    artifact_id = params['artifact_id']
    repo_id = params['repo_id']
    env = params['env']
    location = params['location']
    revision = params['revision']
    branch = params['branch']
    user = params['user']

    # Dev and qat go live immediately, prd goes to init
    if env == 'prd':
        lifecycle_id = '1'
    else:
        lifecycle_id = '2'

    if request.matchdict['resource'] == 'artifact':

        try:
            utcnow = datetime.utcnow()
            create = Artifact(repo_id=repo_id, location=location, revision=revision, branch=branch, valid='1', created=utcnow)
            DBSession.add(create)
            DBSession.flush()
            artifact_id = create.artifact_id
        
            each = {}
            each['artifact_id'] = artifact_id
            results.append(each)

            return results
    
        except Exception as ex:
            if type(ex).__name__ == 'IntegrityError':
                logging.info('Artifact location/revision combination '
                              'is not unique. Nothing to do.')
                # Rollback
                DBSession.rollback()
                return HTTPConflict('Artifact location/revision combination '
                                     'is not unique. Nothing to do.')
            else:
                # Rollback in case there is any error
                DBSession.rollback()
                raise
                logging.error('There was an error updating the db!')

    if request.matchdict['resource'] == 'artifact_assignment':

        # Convert the env name to the id
        env_id = Env.get_env_id(env)

        try:
            utcnow = datetime.utcnow()
            assign = ArtifactAssignment(deploy_id=deploy_id, artifact_id=artifact_id, env_id=env_id.env_id, lifecycle_id=lifecycle_id, user=user, created=utcnow)
            DBSession.add(assign)
            DBSession.flush()
            artifact_assignment_id = assign.artifact_assignment_id

            each = {}
            each['artifact_assignment_id'] = artifact_assignment_id
            results.append(each)

            return results

        except Exception as ex:
            if type(ex).__name__ == 'IntegrityError':
                logging.info('Artifact location/revision combination '
                              'is not unique. Nothing to do.')
                # Rollback
                DBSession.rollback()
                return HTTPConflict('Artifact location/revision combination '
                                     'is not unique. Nothing to do.')
            else:
                # Rollback in case there is any error
                DBSession.rollback()
                raise
                logging.error('There was an error updating the db!')


@view_config(route_name='help', permission='view', renderer='twonicornweb:templates/help.pt')
def view_help(request):

    page_title = 'Help'
    user = get_user(request)

    return {'layout': site_layout(),
            'page_title': page_title,
            'user': user,
            'host_url': request.host_url,
            'denied': denied
           }

@view_config(route_name='user', permission='view', renderer='twonicornweb:templates/user.pt')
def view_user(request):

    page_title = 'User Data'
    user = get_user(request)

    return {'layout': site_layout(),
            'page_title': page_title,
            'user': user,
            'denied': denied,
           }

@view_config(route_name='admin', permission='view', renderer='twonicornweb:templates/admin.pt')
def view_admin(request):

    page_title = 'Admin'
    user = get_user(request)
    prod_groups = request.registry.settings['tcw.prod_groups'].splitlines()

    return {'layout': site_layout(),
            'page_title': page_title,
            'user': user,
            'prod_groups': prod_groups,
            'denied': denied,
           }

@view_config(route_name='cp', permission='cp', renderer='twonicornweb:templates/cp.pt')
def view_cp(request):

    page_title = 'Control Panel'
    user = get_user(request)
    prod_groups = request.registry.settings['tcw.prod_groups'].splitlines()

    return {'layout': site_layout(),
            'page_title': page_title,
            'user': user,
            'prod_groups': prod_groups,
            'denied': denied,
           }


@view_config(route_name='cp_application', permission='cp', renderer='twonicornweb:templates/cp_application.pt')
def view_cp_application(request):

    page_title = 'Control Panel - Application'
    user = get_user(request)
    prod_groups = request.registry.settings['tcw.prod_groups'].splitlines()

    params = {'mode': None,
              'commit': None,
             }
    for p in params:
        try:
            params[p] = request.params[p]
        except:
            pass

    mode = params['mode']
    commit = params['commit']
    application_id = None
    deploy_id = None
    error_msg = None
    artifact_types = None
    artifact_type = None
    deploy_path = None
    package_name = None

    if mode == 'add':

        try:
            q = DBSession.query(ArtifactType)
            artifact_types = q.all()
        except Exception, e:
            log.error("Failed to retrive data on api call (%s)" % (e))
            # FIXME
            return log.error
 
        subtitle = 'Add an application'

        if commit:

            subtitle = 'Add an application'

            if 'form.submitted' in request.POST:
                 print request.POST.dict_of_lists()
                 artifact_types = request.POST.getall('artifact_type')
                 deploy_paths = request.POST.getall('deploy_path')
                 package_names = request.POST.getall('package_name')

                 for i in range(len(deploy_paths)):
                     total = len(deploy_paths)
                     print "There are %s deploys" % total
                     print "Deploy: %s Type: %s Path: %s Package Name: %s" % (i, artifact_types[i], deploy_paths[i], package_names[i])


#                application_name = request.POST['application_name']
#                nodegroup = request.POST['nodegroup']
#                artifact_type = request.POST['artifact_type']
#                deploy_path = request.POST['deploy_path']
#                package_name = request.POST['package_name']
#
#            try:
#                utcnow = datetime.utcnow()
#                # FIXME: Add user to Application table or audit table?
#                # create = Application(application_name=application_name, nodegroup=nodegroup, user=user['ad_login'], created=utcnow)
#                create = Application(application_name=application_name, nodegroup=nodegroup, created=utcnow)
#                DBSession.add(create)
#                DBSession.flush()
#
#                application_id = create.application_id
#                artifact_type_id = ArtifactType.get_artifact_type_id(artifact_type)
#
#                create = Deploy(application_id=application_id, artifact_type_id=artifact_type_id.artifact_type_id, deploy_path=deploy_path, package_name=package_name, created=utcnow)
#                DBSession.add(create)
#                DBSession.flush()
#
#                deploy_id = create.deploy_id
#
#            except Exception, e:
#                # FIXME not trapping correctly
#                DBSession.rollback()
#                error_msg = ("Failed to create application (%s)" % (e))
#                log.error(error_msg)

    if mode == 'edit':

       subtitle = 'Edit an application'

       if commit:

           subtitle = 'Edit an application'


    return {'layout': site_layout(),
            'page_title': page_title,
            'user': user,
            'prod_groups': prod_groups,
            'denied': denied,
            'subtitle': subtitle,
            'application_id': application_id,
            'deploy_id': deploy_id,
            'artifact_types': artifact_types,
            'commit': commit,
            'error_msg': error_msg,
           }


@view_config(route_name='test', permission='view', renderer='twonicornweb:templates/test.pt')
def view_test(request):

    page_title = 'Test'
    user = get_user(request)

    return {'layout': site_layout(),
            'page_title': page_title,
            'user': user,
            'denied': denied,
           }

