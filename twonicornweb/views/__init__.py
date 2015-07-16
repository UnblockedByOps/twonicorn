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
from pyramid.renderers import get_renderer
from pyramid.httpexceptions import HTTPFound
from pyramid.session import signed_deserialize
from pyramid_ldap import groupfinder
from datetime import datetime
import logging
import binascii
from passlib.hash import sha512_crypt
from twonicornweb.models import (
    DBSession,
    Application,
    User,
    Group,
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
        log.error("%s (%s)" % (Exception, e))

    return groups


def local_authenticate(login, password):
    """ Checks the validity of a username/password against what
        is stored in the database. """

    try: 
        q = DBSession.query(User)
        q = q.filter(User.user_name == login)
        db_user = q.one()
    except Exception, e:
        log.error("%s (%s)" % (Exception, e))
        pass

    try: 
        if sha512_crypt.verify(password, db_user.password):
            return [login]
    except Exception, e:
        log.error("%s (%s)" % (Exception, e))
        pass

    return None


def get_user(request):
    """ Gets all the user information for an authenticated  user. Checks groups
        and permissions, and returns a dict of everything. """

    promote_prd_auth = False
    promote_prd_time_auth = False
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

    # Check if the user is authorized to do stuff to prd in a time window
    for a in group_perms['promote_prd_time_groups']:
        a = str(a)
        if a in groups:
            promote_prd_time_auth = True
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
    user['promote_prd_time_auth'] = promote_prd_time_auth
    user['admin_auth'] = admin_auth
    user['cp_auth'] = cp_auth
    user['first_last'] = first_last
    user['email_address'] = email_address
    user['auth_mode'] = auth_mode

    return (user)


# FIXME: Ugly and repetative
def get_group_permissions():
    """ Gets all the groups and permissions from the db, 
        and returns a dict of everything. """

    promote_prd_groups = []
    promote_prd_time_groups = []
    cp_groups = []
    group_perms = {}

    ga = GroupAssignment.get_assignments_by_perm('promote_prd')
    for a in ga:
        promote_prd_groups.append(a.group.group_name)

    ga = GroupAssignment.get_assignments_by_perm('promote_prd_time')
    for a in ga:
        promote_prd_time_groups.append(a.group.group_name)

    ga = GroupAssignment.get_assignments_by_perm('cp')
    for a in ga:
        cp_groups.append(a.group.group_name)

    group_perms['promote_prd_groups'] = promote_prd_groups
    group_perms['promote_prd_time_groups'] = promote_prd_time_groups
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


def format_window(w):
    days = {'1': 'Monday',
            '2': 'Tuesday',
            '3': 'Wednesday',
            '4': 'Thursday',
            '5': 'Friday',
            '6': 'Saturday',
            '7': 'Sunday'
    }
    
    fs = "{0} - {1} {2:02d}:{3:02d} - {4:02d}:{5:02d}".format(days[str(w.day_start)], days[str(w.day_end)], w.hour_start, w.minute_start, w.hour_end, w.minute_end)
    log.debug("Formatted time window: {0}".format(fs))

    return fs


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


def validate_time_deploy(app_id):

    valid = None

    q = DBSession.query(Application)
    q = q.filter(Application.application_id == app_id)
    app = q.one()
    w = app.deployment_time_windows[0]

    print "WINDOW day_start: %s day_end: %s start_time: %s:%s end_time: %s:%s " % (w.day_start, w.day_end, w.hour_start, w.minute_start, w.hour_end, w.minute_end)

    d = datetime.now()
    
    # check if weekday is Monday - Thursday
    if d.isoweekday() in range(w.day_start, w.day_end + 1) and d.hour*60+d.minute in range(w.hour_start*60+w.minute_start, w.hour_end*60+w.minute_end):
        print "we are in range"
        valid = True

    return {'day_start': 'Monday',
            'day_end': 'Thursday',
            'hour_start': '8',
            'minute_start': '00',
            'hour_end': '16',
            'minute_end': '00',
            'valid': valid
    }
