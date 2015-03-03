from pyramid.config import Configurator
from pyramid_ldap import groupfinder
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.security import Allow, Authenticated
from pyramid.renderers import JSON
import ldap
import logging
import ConfigParser
from sqlalchemy import engine_from_config
from sqlalchemy import event
from sqlalchemy.exc import DisconnectionError
import os

from .models import (
    DBSession,
        Base,
        Group,
        GroupAssignment,
        GroupPerm,
            )


class RootFactory(object):

    # Additional ACLs loaded from the DB below
    __acl__ = [(Allow, Authenticated, 'view')]
    def __init__(self, request):
        pass


def getSettings(global_config, settings):
    # Secrets
    cp = ConfigParser.ConfigParser()
    cp.read(settings['tcw.secrets_file'])
    for k,v in cp.items("app:main"):
        settings[k] = v

    scp = ConfigParser.SafeConfigParser()
    scp.read(global_config)
    for k,v in scp.items("app:safe"):
        settings[k] = v

    return settings


def checkout_listener(dbapi_con, con_record, con_proxy):
    try:
        try:
            dbapi_con.ping(False)
        except TypeError:
            dbapi_con.ping()
    except Exception, e:
        import sys
        print >> sys.stderr, "Error: %s (%s)" % (Exception, e)
        raise DisconnectionError()


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    settings = getSettings(global_config['__file__'], settings)
    log = logging.getLogger(__name__)

    engine = engine_from_config(settings, 'sqlalchemy.')
    event.listen(engine, 'checkout', checkout_listener)
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine

    config = Configurator(settings=settings, root_factory=RootFactory)
    print global_config
    config.include('pyramid_chameleon')
    config.include('pyramid_ldap')
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_route('home', '/')
    config.add_route('login', '/login')
    config.add_route('logout', '/logout')
    config.add_route('applications', '/applications')
    config.add_route('deploys', '/deploys')
    config.add_route('promote', '/promote')
    config.add_route('help', '/help')
    config.add_route('user', '/user')
    config.add_route('group', '/group')
    config.add_route('cp', '/cp')
    config.add_route('cp_application', '/cp/application')
    config.add_route('cp_group', '/cp/group')
    config.add_route('api', '/api/{resource}')
    config.add_route('healthcheck', '/healthcheck')
    config.add_route('test', '/test')
    config.add_renderer('json', JSON(indent=2))

    config.set_authentication_policy(
        AuthTktAuthenticationPolicy(settings['tcw.cookie_token'], callback=groupfinder, max_age=604800)
        )
    config.set_authorization_policy(
        ACLAuthorizationPolicy()
        )

    if settings['tcw.auth_mode'] == 'ldap':
        log.info('Configuring ldap users and groups')
        # Load the cert if it's defined and exists
        if os.path.isfile(settings['tcw.ldap_cert']):
            ldap.set_option(ldap.OPT_X_TLS_CACERTFILE, settings['tcw.ldap_cert'])
    
        config.ldap_setup(
            settings['tcw.ldap_server'] + ':' + settings['tcw.ldap_port'],
            bind = settings['tcw.ldap_bind'],
            passwd = settings['tcw.ldap_password'],
            )
        
        config.ldap_set_login_query(
            base_dn = settings['tcw.login_base_dn'],
            filter_tmpl = settings['tcw.login_filter'],
            scope = ldap.SCOPE_SUBTREE,
            cache_period = 600,
            )
        
        config.ldap_set_groups_query(
            base_dn = settings['tcw.group_base_dn'],
            filter_tmpl= settings['tcw.group_filter'],
            scope = ldap.SCOPE_SUBTREE,
            cache_period = 600,
            )
    else:
        log.info('Configuring local users and groups')

    # Load our groups and perms from the db
    try:
        r = DBSession.query(Group).all()
        for g in range(len(r)):
            ga = r[g].get_all_assignments()
            if ga:
                ga = tuple(ga)
                RootFactory.__acl__.append([Allow, r[g].group_name, ga])

    except Exception, e:
        raise

    config.scan()
    return config.make_wsgi_app()
