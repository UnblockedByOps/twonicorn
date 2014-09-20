from pyramid.config import Configurator
from pyramid_ldap import groupfinder
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.security import Allow, Authenticated
import ldap
import ConfigParser


class RootFactory(object):
    __acl__ = [(Allow, Authenticated, 'view'),
               (Allow, 'CN=CM_Team,OU=Security Groups,OU=CGM Accounts Security Groups and Distribution Lists,DC=cs,DC=iac,DC=corp', 'prom')]
    def __init__(self, request):
        pass

def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
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

    # Parse the config
    config_file = ConfigParser.ConfigParser()
    config_file.read('/app/twonicorn_web/conf/twonicorn.conf')
    ldap_server = config_file.get('ldap', 'server')
    ldap_port = config_file.get('ldap', 'port')
    ldap_bind = config_file.get('ldap', 'bind')

    # Parse the secret config
    secret_config_file = ConfigParser.ConfigParser()
    secret_config_file.read('/app/secrets/twonicorn.conf')
    ldap_password = secret_config_file.get('ldap', 'password')
    cookie_token = secret_config_file.get('cookie', 'token')

    ldap.set_option(ldap.OPT_X_TLS_CACERTFILE, "/etc/pki/CA/certs/ny-dc1.iac.corp.crt")

    config.set_authentication_policy(
        AuthTktAuthenticationPolicy(cookie_token, callback=groupfinder, max_age=604800)
        )
    config.set_authorization_policy(
        ACLAuthorizationPolicy()
        )
    config.ldap_setup(
        ldap_server + ':' + ldap_port,
        bind = ldap_bind,
        passwd = ldap_password,
        )
    
    config.ldap_set_login_query(
        base_dn='OU=Technology,OU=User Accounts by Department,OU=CGM Accounts Security Groups and Distribution Lists, DC=cs,DC=iac,DC=corp',
        filter_tmpl='(&(objectClass=user)(sAMAccountName=%(login)s))',
        scope = ldap.SCOPE_SUBTREE,
        cache_period = 600,
        )
    
    config.ldap_set_groups_query(
        base_dn='DC=cs,DC=iac,DC=corp',
        filter_tmpl='(&(objectCategory=group)(member=%(userdn)s))',
        scope = ldap.SCOPE_SUBTREE,
        cache_period = 600,
        )

    config.scan()
    return config.make_wsgi_app()
