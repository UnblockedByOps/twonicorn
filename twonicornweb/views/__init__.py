from pyramid.renderers import get_renderer
from pyramid.httpexceptions import HTTPFound
from pyramid.session import signed_deserialize
from pyramid_ldap import groupfinder as ldap_groupfinder
import logging
import requests
from passlib.hash import sha512_crypt
from arsenalweb.models import (
    DBSession,
    User,
    Group,
    )

log = logging.getLogger(__name__)


class SearchResult(object):

    def __init__(self, name, cs_id, lat, lon, addr_street, addr_city, addr_state, addr_zip, phone, website):
        self.name = name
        self.cs_id = cs_id
        self.lat = lat
        self.lon = lon
        self.addr_street = addr_street
        self.addr_city = addr_city
        self.addr_state = addr_state
        self.addr_zip = addr_zip
        self.phone = phone
        self.website = website


def _cs_api_query(req):

    # Hardcode for now
    verify_ssl = False
    api_protocol = 'http'
    api_host = 'api.citygridmedia.com'

    # This becomes the api call
    api_url = (api_protocol
               + '://'
               + api_host
               + req)

    logging.info('Requesting data from API: %s' % api_url)
    r = requests.get(api_url, verify=verify_ssl)

    if r.status_code == requests.codes.ok:

        logging.debug('Response data: %s' % r.json())
        return r.json()

    else:

        logging.info('There was an error querying the API: '
                      'http_status_code=%s,reason=%s,request=%s'
                      % (r.status_code, r.reason, api_url))
        return None


def contains(list, filter):
    for x in list:
        if filter(x):
            return True
    return False


def site_layout(level):
    if level == 'min':
        renderer = get_renderer("arsenalweb:templates/min_layout.pt")
    else:
        renderer = get_renderer("arsenalweb:templates/global_layout.pt")
    layout = renderer.implementation().macros['layout']
    return layout


def global_groupfinder(userid, request):
    """ Wraps ldap and local groupfinders so we can use one callback
        in the auth policy """

    groups = None
    try:
        log.info("Checking local groups for userid: %s" % (userid))
        groups = local_groupfinder(userid, request)
        if groups:
            log.info("Found local groups for userid: %s groups: %s" % (userid, groups))
    except Exception, e:
        log.info("%s (%s)" % (Exception, e))
        pass

    if request.registry.settings['arsenal.use_ldap'] and not groups:
        try:
            log.info("Checking ldap groups for userid: %s" % (userid))
            groups = ldap_groupfinder(userid, request)
            if groups:
                log.info("Found ldap groups for userid: %s groups: %s" % (userid, groups))
        except Exception, e:
            log.info("%s (%s)" % (Exception, e))
            pass

    return groups


def local_groupfinder(userid, request):
    """ queries the db for a list of groups the user belongs to.
        Returns either a list of groups (empty if no groups) or None
        if the user doesn't exist. """

    groups = None
    try:
        user = DBSession.query(User).filter(User.user_name==userid).one()
        groups = user.get_all_assignments()
    except Exception, e:
        log.info("%s (%s)" % (Exception, e))
        pass

    return groups


def local_authenticate(login, password):
    """ Checks the validity of a username/password against what
        is stored in the database. """

    try: 
        q = DBSession.query(User)
        q = q.filter(User.user_name == login)
        db_user = q.one()
    except Exception, e:
        log.debug("%s (%s)" % (Exception, e))
        # Should return invalid username here somehow
        return None

    try: 
        if sha512_crypt.verify(password, db_user.password):
            return [login]
    except Exception, e:
        log.info("%s (%s)" % (Exception, e))
        pass

    return None


def get_authenticated_user(request):
    """ Gets all the user information for an authenticated  user. Checks groups
        and permissions, and returns a dict of everything. """

    (first_last, user_id, login, groups, first, last, auth, prd_auth, admin_auth, cp_auth) = ('', '', '', '', '', '', False, False, False, False)

    if request.authenticated_userid:

        user_id = request.authenticated_userid
        try:
            user = DBSession.query(User).filter(User.user_name==user_id).one()
            first = user.first_name
            last = user.last_name
            groups = local_groupfinder(user_id, request)
            first_last = "%s %s" % (first, last)
            auth = True
        except Exception, e:
            log.debug("%s (%s)" % (Exception, e))

        if request.registry.settings['arsenal.use_ldap'] and not groups:
            try:
                (first,last) = format_user(user_id)
                groups = ldap_groupfinder(user_id, request)
                first_last = "%s %s" % (first, last)
                auth = True
            except Exception, e:
                log.error("%s (%s)" % (Exception, e))

    try:
        login = validate_username_cookie(request.cookies['un'], request.registry.settings['arsenal.cookie_token'])
    except:
        return HTTPFound('/logout?message=Your cookie has been tampered with. You have been logged out')

    # authenticated user
    au = {}
    au['user_id'] = user_id
    au['login'] = login
    au['groups'] = groups
    au['first'] = first
    au['last'] = last
    au['loggedin'] = auth
    au['first_last'] = first_last

    return (au)


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

