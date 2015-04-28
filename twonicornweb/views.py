#  Copyright 2015 CityGrid Media, LLC
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
from pyramid.view import view_config, forbidden_view_config
from pyramid.renderers import get_renderer
from pyramid.httpexceptions import HTTPFound
from pyramid.httpexceptions import HTTPServiceUnavailable
from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPConflict
from pyramid.security import remember, forget
from pyramid.session import signed_serialize, signed_deserialize
from pyramid_ldap import get_ldap_connector, groupfinder
from pyramid.response import Response
from sqlalchemy.sql import exists
from datetime import datetime
import logging
import os.path
import binascii
from passlib.hash import sha512_crypt
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
    User,
    UserGroupAssignment,
    Group,
    GroupPerm,
    GroupAssignment,
    )

log = logging.getLogger(__name__)


def site_layout():
    renderer = get_renderer("twonicornweb:templates/global_layout.pt")
    layout = renderer.implementation().macros['layout']
    return layout


def local_groupfinder(userid, request):
    """ queries the db for a list of groups the user belongs to.
        Returns either a list of groups (empty if no groups) or None
        if the user doesn't exist. """

    groups = None
    try:
        user = DBSession.query(User).filter(User.user_name==userid).one()
        groups = user.get_all_assignments()
    except Exception, e:
        pass
        log.info("%s (%s)" % (Exception, e))

    return groups


def local_authenticate(login, password):
    """ Checks the validity of a username/password against what
        is stored in the database. """

    try: 
        q = DBSession.query(User)
        q = q.filter(User.user_name == login)
        db_user = q.one()
    except Exception, e:
        log.info("%s (%s)" % (Exception, e))
        pass

    try: 
        if sha512_crypt.verify(password, db_user.password):
            return [login]
    except Exception, e:
        log.info("%s (%s)" % (Exception, e))
        pass

    return None


def get_user(request):
    """ Gets all the user information for an authenticated  user. Checks groups
        and permissions, and returns a dict of everything. """

    promote_prd_auth = False
    admin_auth = False
    cp_auth = False
    email_address = None
    auth_mode = 'ldap'

    if request.registry.settings['tcw.auth_mode'] == 'ldap':
        try:
            id = request.authenticated_userid
            if id: 
                (first,last) = format_user(id)
                groups = groupfinder(id, request)
                first_last = "%s %s" % (first, last)
                auth = True
        except Exception, e:
            log.error("%s (%s)" % (Exception, e))
            (first_last, id, login, groups, first, last, auth, prd_auth, admin_auth, cp_auth) = ('', '', '', '', '', '', False, False, False, False)
    else:
        try:
            id = request.authenticated_userid
            user = DBSession.query(User).filter(User.user_name==id).one()
            first = user.first_name
            last = user.last_name
            email_address = user.email_address
            groups = local_groupfinder(id, request)
            first_last = "%s %s" % (first, last)
            auth = True
            auth_mode = 'local'
        except Exception, e:
            log.error("%s (%s)" % (Exception, e))
            (first_last, id, login, groups, first, last, auth, prd_auth, admin_auth, cp_auth) = ('', '', '', '', '', '', False, False, False, False)

    try:
        login = validate_username_cookie(request.cookies['un'], request.registry.settings['tcw.cookie_token'])
        login = str(login)
    except:
        return HTTPFound('/logout?message=Your cookie has been tampered with. You have been logged out')

    # Get the groups from the DB
    group_perms = get_group_permissions()

    # Check if the user is authorized to do stuff to prd
    for a in group_perms['promote_prd_groups']:
        a = str(a)
        if a in groups:
            promote_prd_auth = True
            break

    # Check if the user is authorized for cp
    for a in group_perms['cp_groups']:
        a = str(a)
        if a in groups:
            cp_auth = True
            break

    user = {}
    user['id'] = id
    user['login'] = login
    user['groups'] = groups
    user['first'] = first
    user['last'] = last
    user['loggedin'] = auth
    user['promote_prd_auth'] = promote_prd_auth
    user['admin_auth'] = admin_auth
    user['cp_auth'] = cp_auth
    user['first_last'] = first_last
    user['email_address'] = email_address
    user['auth_mode'] = auth_mode

    return (user)

def get_group_permissions():
    """ Gets all the groups and permissions from the db, 
        and returns a dict of everything. """

    promote_prd_groups = []
    cp_groups = []
    group_perms = {}

    ga = GroupAssignment.get_assignments_by_perm('promote_prd')
    for a in ga:
        promote_prd_groups.append(a.group.group_name)

    ga = GroupAssignment.get_assignments_by_perm('cp')
    for a in ga:
        cp_groups.append(a.group.group_name)

    group_perms['promote_prd_groups'] = promote_prd_groups
    group_perms['cp_groups'] = cp_groups

    return(group_perms)

def get_all_groups():
    """ Gets all the groups that are configured in
        the db and returns a dict of everything. """

    # Get the groups from the db
    group_perms = []
    r = DBSession.query(Group).all()
    for g in range(len(r)):
        ga = r[g].get_all_assignments()
        if ga:
            ga = tuple(ga)
            group_perms.append([r[g].group_name, ga])

    return(group_perms)


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

        # AD/LDAP
        if request.registry.settings['tcw.auth_mode'] == 'ldap':
            connector = get_ldap_connector(request)
            data = connector.authenticate(login, password)
        # LOCAL
        else:
            data = local_authenticate(login, password)
            
        if data is not None:
            dn = data[0]
            encrypted = signed_serialize(login, request.registry.settings['tcw.cookie_token'])
            headers = remember(request, dn)
            headers.append(('Set-Cookie', 'un=' + str(encrypted) + '; Max-Age=604800; Path=/'))

            return HTTPFound(request.POST['return_url'], headers=headers)
        else:
            error = 'Invalid credentials'

    if request.authenticated_userid:

        if request.path == '/login':
          error = 'You are already logged in'
          page_title = 'Already Logged In'
        else:
          error = 'You do not have permission to access this page'
          page_title = 'Access Denied'

    return {'layout': site_layout(),
            'page_title': page_title,
            'user': user,
            'return_url': return_url,
            'login': login,
            'password': password,
            'error': error,
           }

@view_config(route_name='home', permission='view', renderer='twonicornweb:templates/home.pt')
def view_home(request):

    return HTTPFound('/applications')

@view_config(route_name='applications', permission='view', renderer='twonicornweb:templates/applications.pt')
def view_applications(request):
    page_title = 'Applications'
    user = get_user(request)

    perpage = 50
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
           }

@view_config(route_name='deploys', permission='view', renderer='twonicornweb:templates/deploys.pt')
def view_deploys(request):

    page_title = 'Deploys'
    user = get_user(request)

    perpage = 50
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
           }


@view_config(route_name='promote', permission='view', renderer='twonicornweb:templates/promote.pt')
def view_promote(request):

    page_title = 'Promote'
    user = get_user(request)
    office_loc = request.registry.settings['tcw.office_loc']

    error = ''
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
    referer = request.referer

    if not user['promote_prd_auth'] and to_env == 'prd':
        to_state = '3'
    else:
        to_state = '2'

    try:
        promote = Artifact.get_promotion(office_loc,to_env, deploy_id, artifact_id)
    except Exception, e:
        conn_err_msg = e
        return Response(str(conn_err_msg), content_type='text/plain', status_int=500)

    if artifact_id and commit == 'true':
        if not user['promote_prd_auth'] and to_env == 'prd' and to_state == '2':
            error = True
            message = 'You do not have permission to perform the promote action on production!'
        else:
            # Actually promoting
            try:
                # Convert the env name to the id
                env_id = Env.get_env_id(to_env)

                # Assign
                utcnow = datetime.utcnow()
                promote = ArtifactAssignment(deploy_id=deploy_id, artifact_id=artifact_id, env_id=env_id.env_id, lifecycle_id=to_state, updated_by=user['login'], created=utcnow)
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
            'error': error,
            'message': message,
            'deploy_id': deploy_id,
            'artifact_id': artifact_id,
            'to_env': to_env,
            'to_state': to_state,
            'commit': commit,
            'promote': promote,
            'referer': referer,
           }


@view_config(route_name='api', request_method='GET', renderer='json')
def view_api(request):

    params = {'id': None,
              'env': None,
              'loc': None,
              'lifecycle': None,
              'deploy_id': None,
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
    deploy_id = params['deploy_id']
    results = []

    if request.matchdict['resource'] == 'application':
        try:
            q = DBSession.query(Application)
            q = q.filter(Application.application_id == id)
            app = q.one()
        except Exception, e:
            log.error("Failed to retrive data on api call (%s)" % (e))
            return results

        for d in app.deploys:
            each = {}
            a = d.get_assignment(env, lifecycle)
            if a:
                try:
                    each['download_url'] = a.artifact.repo.get_url(loc).url + a.artifact.location
                # FIXME: Better to return empty json?
                except AttributeError:
                    each['download_url'] = 'Invalid location'
                    results.append(each)
                    continue
                each['deploy_id'] = d.deploy_id
                each['package_name'] = d.package_name
                each['artifact_assignment_id'] = a.artifact_assignment_id
                each['deploy_path'] = d.deploy_path
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
            try:
                each['download_url'] = a.artifact.repo.get_url(loc).url + a.artifact.location
                each['deploy_id'] = deploy.deploy_id
                each['package_name'] = deploy.package_name
                each['artifact_assignment_id'] = a.artifact_assignment_id
                each['deploy_path'] = deploy.deploy_path
                each['revision'] = a.artifact.revision[:8]
                each['artifact_type'] = deploy.type.name
                each['repo_type'] = a.artifact.repo.type.name
                each['repo_name'] = a.artifact.repo.name
                each['lifecycle'] = a.lifecycle.name
            # FIXME: Better to return empty json?
            except AttributeError:
                each['download_url'] = 'Invalid location'
                results.append(each)
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
        try:
            each['download_url'] = artifact.repo.get_url(loc).url + artifact.location
            each['artifact_id'] = artifact.artifact_id
            each['branch'] = artifact.branch
            each['created'] = artifact.localize_date_created
            each['repo_id'] = artifact.repo_id
            each['repo_type'] = artifact.repo.type.name
            each['revision'] = artifact.revision
            each['valid'] = artifact.valid
        # FIXME: Better to return empty json?
        except AttributeError:
            each['download_url'] = 'Invalid location'
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

    if request.matchdict['resource'] == 'repo_types':
        try:
            q = DBSession.query(RepoType)
            repo_types = q.all()
        except Exception, e:
            log.error("Failed to retrive data on api call (%s)" % (e))
            return results

        for r in repo_types:
            each = {}
            each['repo_type_id'] = r.repo_type_id
            each['name'] = r.name
            results.append(each)

    if request.matchdict['resource'] == 'artifact_types':
        if deploy_id:
            try:
                q = DBSession.query(ArtifactType)
                q = q.join(Deploy, ArtifactType.artifact_type_id == Deploy.artifact_type_id)
                q = q.filter(Deploy.deploy_id==deploy_id)
                r = q.one()
                results.append({'artifact_type':  r.name})
            except Exception, e:
                log.error("Failed to retrive data on api call (%s)" % (e))
                return results
        else:
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

    if request.matchdict['resource'] == 'repo_urls':
        try:
            q = DBSession.query(RepoUrl)
            repo_urls = q.all()
        except Exception, e:
            log.error("Failed to retrive data on api call (%s)" % (e))
            return results

        for r in repo_urls:
            each = {}
            each['ct_loc'] = r.ct_loc
            each['repo_id'] = r.repo_id
            each['repo_url_id'] = r.repo_url_id
            each['url'] = r.url
            results.append(each)

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
              'updated_by': None,
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
    updated_by = params['updated_by']

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
                log.info('Artifact location/revision combination '
                         'is not unique. Nothing to do.')
                # Rollback
                DBSession.rollback()
                return HTTPConflict('Artifact location/revision combination '
                                     'is not unique. Nothing to do.')
            else:
                # Rollback in case there is any error
                DBSession.rollback()
                raise
                log.error('There was an error updating the db!')

    if request.matchdict['resource'] == 'artifact_assignment':

        # Convert the env name to the id
        env_id = Env.get_env_id(env)

        try:
            utcnow = datetime.utcnow()
            assign = ArtifactAssignment(deploy_id=deploy_id, artifact_id=artifact_id, env_id=env_id.env_id, lifecycle_id=lifecycle_id, updated_by=updated_by, created=utcnow)
            DBSession.add(assign)
            DBSession.flush()
            artifact_assignment_id = assign.artifact_assignment_id

            each = {}
            each['artifact_assignment_id'] = artifact_assignment_id
            results.append(each)

            return results

        except Exception as ex:
            if type(ex).__name__ == 'IntegrityError':
                log.info('Artifact location/revision combination '
                         'is not unique. Nothing to do.')
                # Rollback
                DBSession.rollback()
                return HTTPConflict('Artifact location/revision combination '
                                     'is not unique. Nothing to do.')
            else:
                # Rollback in case there is any error
                DBSession.rollback()
                raise
                log.error('There was an error updating the db!')


@view_config(route_name='help', permission='view', renderer='twonicornweb:templates/help.pt')
def view_help(request):

    page_title = 'Help'
    user = get_user(request)

    return {'layout': site_layout(),
            'page_title': page_title,
            'user': user,
            'host_url': request.host_url,
           }

@view_config(route_name='user', permission='view', renderer='twonicornweb:templates/user.pt')
def view_user(request):

    user = get_user(request)
    page_title = 'User Data'
    subtitle = user['first_last']
    change_pw = False

    if user['auth_mode'] != 'ldap':

        if 'form.submitted' in request.POST:
            user_name = request.POST['user_name']
            first_name = request.POST['first_name']
            last_name = request.POST['last_name']
            email_address = request.POST['email_address']
            password = request.POST['password']

            # FIXME: Need some security checking here
            if user_name != user['login']:
                log.error('Bad person attemting to do bad things to:' % user_name)
            else:

                # Update
                log.info('UPDATE: user_name=%s,first_name=%s,last_name=%s,email_address=%s,password=%s'
                         % (user_name,
                           first_name,
                           last_name,
                           email_address,
                           '<redacted>'))
                try:
                    user = DBSession.query(User).filter(User.user_name==user_name).one()
                    user.first_name = first_name
                    user.last_name = last_name
                    user.email_address = email_address
                    if password:
                        log.info('Changing password for: user_name=%s password=<redacted>' % user_name)
                        salt = sha512_crypt.genconfig()[17:33]
                        encrypted_password = sha512_crypt.encrypt(password, salt=salt)
                        user.salt = salt
                        user.password = encrypted_password
                        DBSession.flush()
                        return_url = '/logout?message=Your password has been changed successfully. Please log in again.'
                        return HTTPFound(return_url)

                    DBSession.flush()

                except Exception, e:
                    pass
                    log.info("%s (%s)" % (Exception, e))

        user = get_user(request)

    return {'layout': site_layout(),
            'page_title': page_title,
            'subtitle': subtitle,
            'user': user,
            'change_pw': change_pw,
           }


@view_config(route_name='cp', permission='cp', renderer='twonicornweb:templates/cp.pt')
def view_cp(request):

    page_title = 'Control Panel'
    user = get_user(request)

    return {'layout': site_layout(),
            'page_title': page_title,
            'user': user,
           }


@view_config(route_name='cp_application', permission='cp', renderer='twonicornweb:templates/cp_application.pt')
def view_cp_application(request):

    page_title = 'Control Panel - Application'
    user = get_user(request)

    params = {'mode': None,
              'commit': None,
              'application_id': None,
             }
    for p in params:
        try:
            params[p] = request.params[p]
        except:
            pass

    mode = params['mode']
    commit = params['commit']
    application_id = params['application_id']
    app = None
    nodegroup = None
    deploy_id = None
    error_msg = None
    artifact_types = None

    try:
        q = DBSession.query(ArtifactType)
        artifact_types = q.all()
    except Exception, e:
        log.error("Failed to retrive data on api call (%s)" % (e))
        return log.error

    if mode == 'add':

        subtitle = 'Add an application'

        if commit:

            application_name = request.POST['application_name']
            nodegroup = request.POST['nodegroup']
            artifact_types = request.POST.getall('artifact_type')
            deploy_paths = request.POST.getall('deploy_path')
            package_names = request.POST.getall('package_name')

            subtitle = 'Add an application'
            # FIXME not trapping because length is the same. - Safari only bug
            if len(deploy_paths) != len(artifact_types):
               error_msg = "You must select an artifact type and specify a deploy path."
            else:

                try:
                    utcnow = datetime.utcnow()
                    create = Application(application_name=application_name, nodegroup=nodegroup, updated_by=user['login'], created=utcnow, updated=utcnow)
                    DBSession.add(create)
                    DBSession.flush()
                    application_id = create.application_id

                    for i in range(len(deploy_paths)):
                        artifact_type_id = ArtifactType.get_artifact_type_id(artifact_types[i])
                        create = Deploy(application_id=application_id, artifact_type_id=artifact_type_id.artifact_type_id, deploy_path=deploy_paths[i], package_name=package_names[i], updated_by=user['login'], created=utcnow, updated=utcnow)
                        DBSession.add(create)
                        deploy_id = create.deploy_id

                    DBSession.flush()

                    return_url = '/deploys?application_id=%s&nodegroup=%s' % (application_id, nodegroup)
                    return HTTPFound(return_url)

                except Exception, e:
                    raise
                    # FIXME not trapping correctly
                    DBSession.rollback()
                    error_msg = ("Failed to create application (%s)" % (e))
                    log.error(error_msg)

    if mode == 'edit':

       subtitle = 'Edit an application'

       if not commit:

           try:
               q = DBSession.query(Application)
               q = q.filter(Application.application_id == application_id)
               app = q.one()
           except Exception, e:
               conn_err_msg = e
               return Response(str(conn_err_msg), content_type='text/plain', status_int=500)

       if commit:

           subtitle = 'Edit an application'

           if 'form.submitted' in request.POST:
                application_id = request.POST['application_id']
                application_name = request.POST['application_name']
                nodegroup = request.POST['nodegroup']
                artifact_types = request.POST.getall('artifact_type')
                deploy_ids = request.POST.getall('deploy_id')
                deploy_paths = request.POST.getall('deploy_path')
                package_names = request.POST.getall('package_name')

                if len(deploy_paths) != len(artifact_types):
                    error_msg = "You must select an artifact type and specify a deploy path."
                else:

                    # Update the app
                    log.info('UPDATE: application_id=%s,application_name=%s,nodegroup=%s,updated_by=%s'
                             % (application_id,
                                application_name,
                                nodegroup,
                                user['login']))
                    app = DBSession.query(Application).filter(Application.application_id==application_id).one()
                    app.application_name = application_name
                    app.nodegroup = nodegroup
                    app.updated_by=user['login']
                    DBSession.flush()

                    # Add/Update deploys
                    for i in range(len(deploy_paths)):
                        deploy_id = None
                        try:
                            deploy_id = deploy_ids[i]
                        except:
                            pass

                        if deploy_id:
                            log.info('UPDATE: deploy=%s,deploy_id=%s,artifact_type=%s,deploy_path=%s,package_name=%s'
                                     % (i,
                                        deploy_id,
                                        artifact_types[i],
                                        deploy_paths[i],
                                        package_names[i]))
                            dep = DBSession.query(Deploy).filter(Deploy.deploy_id==deploy_id).one()
                            artifact_type_id = ArtifactType.get_artifact_type_id(artifact_types[i])
                            dep.artifact_type_id = artifact_type_id.artifact_type_id
                            dep.deploy_path = deploy_paths[i]
                            dep.package_name = package_names[i]
                            dep.updated_by=user['login'] 
                            DBSession.flush()
                            
                        else:
                            log.info('CREATE: deploy=%s,deploy_id=%s,artifact_type=%s,deploy_path=%s,package_name=%s'
                                     % (i,
                                        deploy_id,
                                        artifact_types[i],
                                        deploy_paths[i],
                                        package_names[i]))
                            utcnow = datetime.utcnow()
                            artifact_type_id = ArtifactType.get_artifact_type_id(artifact_types[i])
                            create = Deploy(application_id=application_id, artifact_type_id=artifact_type_id.artifact_type_id, deploy_path=deploy_paths[i], package_name=package_names[i], updated_by=user['login'], created=utcnow, updated=utcnow)
                            DBSession.add(create)
                            DBSession.flush()

                    return_url = '/deploys?application_id=%s&nodegroup=%s' % (application_id, nodegroup)
                    return HTTPFound(return_url)


    return {'layout': site_layout(),
            'page_title': page_title,
            'user': user,
            'subtitle': subtitle,
            'app': app,
            'application_id': application_id,
            'nodegroup': nodegroup,
            'deploy_id': deploy_id,
            'artifact_types': artifact_types,
            'mode': mode,
            'commit': commit,
            'error_msg': error_msg,
           }


@view_config(route_name='cp_user', permission='cp', renderer='twonicornweb:templates/cp_user.pt')
def view_cp_user(request):

    page_title = 'Control Panel - Users'
    user = get_user(request)
    users = DBSession.query(User).all()
    groups = DBSession.query(Group).all()

    params = {'mode': None,
              'commit': None,
              'user_id': None,
             }
    for p in params:
        try:
            params[p] = request.params[p]
        except:
            pass

    mode = params['mode']
    commit = params['commit']
    user_id = params['user_id']
    error_msg = None
    this_user = None
    this_groups = None
    subtitle = 'Users'

    if mode == 'add':

        subtitle = 'Add a new user'

        if commit:

            user_names = request.POST.getall('user_name')
            first_names = request.POST.getall('first_name')
            last_names= request.POST.getall('last_name')
            email_addresses = request.POST.getall('email_address')
            passwords = request.POST.getall('password')

            try:
                utcnow = datetime.utcnow()
                for u in range(len(user_names)):
                    salt = sha512_crypt.genconfig()[17:33]
                    encrypted_password = sha512_crypt.encrypt(passwords[u], salt=salt)
                    create = User(user_name=user_names[u], first_name=first_names[u], last_name=last_names[u], email_address=email_addresses[u], salt=salt, password=encrypted_password, updated_by=user['login'], created=utcnow, updated=utcnow)
                    DBSession.add(create)
                    DBSession.flush()
                    user_id = create.user_id

                    group_assignments = request.POST.getall('group_assignments')

                    for a in group_assignments:
                        g = DBSession.query(Group).filter(Group.group_name==a).one()
                        create = UserGroupAssignment(group_id=g.group_id, user_id=user_id, updated_by=user['login'], created=utcnow, updated=utcnow)
                        DBSession.add(create)

                        DBSession.flush()

                return_url = '/cp/user'
                return HTTPFound(return_url)

            except Exception as ex:
                if type(ex).__name__ == 'IntegrityError':
                    log.info('User already exists in the db, please edit instead.')
                    # Rollback
                    DBSession.rollback()
                    # FIXME: Return a nice page
                    return HTTPConflict('User already exists in the db, please edit instead.')
                else:
                    raise
                    # FIXME not trapping correctly
                    DBSession.rollback()
                    error_msg = ("Failed to create user (%s)" % (ex))
                    log.error(error_msg)

    if mode == 'edit':

       subtitle = 'Edit user'

       if not commit:
           try:
               q = DBSession.query(User)
               q = q.filter(User.user_id == user_id)
               this_user = q.one()

               q = DBSession.query(Group)
               q = q.join(UserGroupAssignment, Group.group_id== UserGroupAssignment.group_id)
               q = q.filter(UserGroupAssignment.user_id==this_user.user_id)
               results = q.all()
               this_groups = []
               for r in results:
                   this_groups.append(r.group_name) 
           except Exception, e:
               conn_err_msg = e
               return Response(str(conn_err_msg), content_type='text/plain', status_int=500)

       if commit:

           if 'form.submitted' in request.POST:
                user_id = request.POST.get('user_id')
                user_name = request.POST.get('user_name')
                first_name = request.POST.get('first_name')
                last_name = request.POST.get('last_name')
                email_address = request.POST.get('email_address')
                password = request.POST.get('password')
                group_assignments = request.POST.getall('group_assignments')
             
                # Update the user
                utcnow = datetime.utcnow()
                this_user = DBSession.query(User).filter(User.user_id==user_id).one()
                this_user.user_name = user_name
                this_user.first_name = first_name
                this_user.last_name = last_name
                this_user.email_address = email_address
                if password:
                    salt = sha512_crypt.genconfig()[17:33]
                    encrypted_password = sha512_crypt.encrypt(password, salt=salt)
                    this_user.salt = salt
                    this_user.password = encrypted_password
                this_user.updated_by=user['login']
                DBSession.flush()

                for g in groups:
                    if str(g.group_id) in group_assignments:
                        # assign
                        log.debug("Group: %s is in group assignments" % g.group_name)
                        q = DBSession.query(UserGroupAssignment).filter(UserGroupAssignment.group_id==g.group_id, UserGroupAssignment.user_id==this_user.user_id)
                        check = DBSession.query(q.exists()).scalar()
                        if not check:
                            log.info("Assigning local user %s to group %s" % (this_user.user_name, g.group_name))
                            update = UserGroupAssignment(group_id=g.group_id, user_id=user_id, updated_by=user['login'], created=utcnow, updated=utcnow)
                            DBSession.add(update)
                            DBSession.flush()
                    else:
                        # delete
                        log.debug("Checking to see if we need to remove assignment for user: %s in group %s" % (this_user.user_name,g.group_name))
                        q = DBSession.query(UserGroupAssignment).filter(UserGroupAssignment.group_id==g.group_id, UserGroupAssignment.user_id==this_user.user_id)
                        check = DBSession.query(q.exists()).scalar()
                        if check:
                            log.info("Removing local user %s from group %s" % (this_user.user_name, g.group_name))
                            assignment = DBSession.query(UserGroupAssignment).filter(UserGroupAssignment.group_id==g.group_id, UserGroupAssignment.user_id==this_user.user_id).one()
                            DBSession.delete(assignment)
                            DBSession.flush()
                        
                return_url = '/cp/user'
                return HTTPFound(return_url)

    return {'layout': site_layout(),
            'page_title': page_title,
            'user': user,
            'this_user': this_user,
            'this_groups': this_groups,
            'user_id': user_id,
            'users': users,
            'groups': groups,
            'subtitle': subtitle,
            'mode': mode,
            'commit': commit,
            'error_msg': error_msg,
           }

@view_config(route_name='cp_group', permission='cp', renderer='twonicornweb:templates/cp_group.pt')
def view_cp_group(request):

    page_title = 'Control Panel - Groups'
    user = get_user(request)
    all_perms = DBSession.query(GroupPerm).all()
    groups = DBSession.query(Group).all()

    params = {'mode': None,
              'commit': None,
              'group_id': None,
             }
    for p in params:
        try:
            params[p] = request.params[p]
        except:
            pass

    mode = params['mode']
    commit = params['commit']
    group_id = params['group_id']
    error_msg = None
    group_perms = None
    group = None
    subtitle = 'Groups'

    if mode == 'add':

        subtitle = 'Add a new group'

        if commit:

            subtitle = 'Add a new group'

            group_names = request.POST.getall('group_name')

            try:
                utcnow = datetime.utcnow()
                for g in range(len(group_names)):
                    create = Group(group_name=group_names[g], updated_by=user['login'], created=utcnow, updated=utcnow)
                    DBSession.add(create)
                    DBSession.flush()
                    group_id = create.group_id

                    i = 'group_perms' + str(g)
                    group_perms = request.POST.getall(i)

                    for p in group_perms:
                        perm = GroupPerm.get_group_perm_id(p)
                        create = GroupAssignment(group_id=group_id, perm_id=perm.perm_id, updated_by=user['login'], created=utcnow, updated=utcnow)
                        DBSession.add(create)
                        group_assignment_id = create.group_assignment_id

                        DBSession.flush()

                return_url = '/cp/group'
                return HTTPFound(return_url)

            except Exception as ex:
                if type(ex).__name__ == 'IntegrityError':
                    log.info('Group already exists in the db, please edit instead.')
                    # Rollback
                    DBSession.rollback()
                    # FIXME: Return a nice page
                    return HTTPConflict('Group already exists in the db, please edit instead.')
                else:
                    raise
                    # FIXME not trapping correctly
                    DBSession.rollback()
                    error_msg = ("Failed to create application (%s)" % (ex))
                    log.error(error_msg)

    if mode == 'edit':

       subtitle = 'Edit group permissions'

       if not commit:
           subtitle = 'Edit group permissions'

           try:
               q = DBSession.query(Group)
               q = q.filter(Group.group_id == group_id)
               group = q.one()
           except Exception, e:
               conn_err_msg = e
               return Response(str(conn_err_msg), content_type='text/plain', status_int=500)

       if commit:

           subtitle = 'Edit group permissions'

           if 'form.submitted' in request.POST:
                group_id = request.POST.get('group_id')
                group_name = request.POST.get('group_name')
                perms = request.POST.getall('perms')
             
                # Update the group
                utcnow = datetime.utcnow()
                group = DBSession.query(Group).filter(Group.group_id==group_id).one()
                group.group_name = group_name
                group.updated_by=user['login']
                DBSession.flush()

                # Update the perms
                all_perms = DBSession.query(GroupPerm)
                for p in all_perms:
                    # insert
                    if p.perm_name in perms:
                        perm = GroupPerm.get_group_perm_id(p.perm_name)
                        q = DBSession.query(GroupAssignment).filter(GroupAssignment.group_id==group_id, GroupAssignment.perm_id==perm.perm_id)
                        check = DBSession.query(q.exists()).scalar()
                        if not check:
                            log.info("Adding permission %s for group %s" % (p.perm_name, group_name))
                            utcnow = datetime.utcnow()
                            create = GroupAssignment(group_id=group_id, perm_id=perm.perm_id, updated_by=user['login'], created=utcnow, updated=utcnow)
                            DBSession.add(create)
                            DBSession.flush()
    
                    # delete
                    else:
                        perm = GroupPerm.get_group_perm_id(p.perm_name)
                        q = DBSession.query(GroupAssignment).filter(GroupAssignment.group_id==group_id, GroupAssignment.perm_id==perm.perm_id)
                        check = DBSession.query(q.exists()).scalar()
                        if check:
                            log.info("Deleting permission %s for group %s" % (p.perm_name, group_name))
                            assignment = DBSession.query(GroupAssignment).filter(GroupAssignment.group_id==group_id, GroupAssignment.perm_id==perm.perm_id).one()
                            DBSession.delete(assignment)
                            DBSession.flush()

                return_url = '/cp/group'
                return HTTPFound(return_url)

    return {'layout': site_layout(),
            'page_title': page_title,
            'user': user,
            'group': group,
            'group_id': group_id,
            'group_perms': group_perms,
            'groups': groups,
            'all_perms': all_perms,
            'subtitle': subtitle,
            'mode': mode,
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
           }

