from pyramid.config import Configurator
from pyramid_ldap import groupfinder
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.security import Allow, Authenticated
import ldap
import ConfigParser
from sqlalchemy import engine_from_config
from sqlalchemy import event
from sqlalchemy.exc import DisconnectionError

from .models import (
    DBSession,
        Base,
            )


class RootFactory(object):
    __acl__ = [(Allow, Authenticated, 'view'),
               (Allow, 'CN=CM_Team,OU=Security Groups,OU=CGM Accounts Security Groups and Distribution Lists,DC=cs,DC=iac,DC=corp', 'prom')]
    def __init__(self, request):
        pass


def getSettings(settings):
    # Secrets
    cp = ConfigParser.ConfigParser()
    cp.read(settings['tcw.secrets_file'])
    for k,v in cp.items("app:main"):
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
    settings = getSettings(settings)

    engine = engine_from_config(settings, 'sqlalchemy.')
    event.listen(engine, 'checkout', checkout_listener)
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine

    config = Configurator(settings=settings, root_factory=RootFactory)
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
    config.add_route('admin', '/admin')

    ldap.set_option(ldap.OPT_X_TLS_CACERTFILE, "/etc/pki/CA/certs/ny-dc1.iac.corp.crt")

    config.set_authentication_policy(
        AuthTktAuthenticationPolicy(settings['tcw.cookie_token'], callback=groupfinder, max_age=604800)
        )
    config.set_authorization_policy(
        ACLAuthorizationPolicy()
        )
    config.ldap_setup(
        settings['tcw.ldap_server'] + ':' + settings['tcw.ldap_port'],
        bind = settings['tcw.ldap_bind'],
        passwd = settings['tcw.ldap_password'],
        )
    
    config.ldap_set_login_query(
        base_dn = settings['tcw.login_base_dn'],
        filter_tmpl = '(&(objectClass=user)(sAMAccountName=%(login)s))',
        scope = ldap.SCOPE_SUBTREE,
        cache_period = 600,
        )
    
    config.ldap_set_groups_query(
        base_dn = settings['tcw.group_base_dn'],
        filter_tmpl='(&(objectCategory=group)(member=%(userdn)s))',
        scope = ldap.SCOPE_SUBTREE,
        cache_period = 600,
        )

    config.scan()
    return config.make_wsgi_app()
