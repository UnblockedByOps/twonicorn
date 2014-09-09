from pyramid.config import Configurator
from pyramid_ldap import groupfinder
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.security import Allow, Authenticated
import ldap


class RootFactory(object):
    __acl__ = [(Allow, Authenticated, 'view')]
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

    config.set_authentication_policy(
        AuthTktAuthenticationPolicy('seekr1t', callback=groupfinder)
        )
    config.set_authorization_policy(
        ACLAuthorizationPolicy()
        )
    config.ldap_setup(
        'ldap://wh-cs-dc1.cs.iac.corp:3268',
        bind='ldapauth',
        passwd='THE_PASSWORD',
        )
    
    config.ldap_set_login_query(
        base_dn='OU=Technology,OU=User Accounts by Department,OU=CGM Accounts Security Groups and Distribution Lists, DC=cs,DC=iac,DC=corp',
        filter_tmpl='(&(objectClass=user)(sAMAccountName=%(login)s))',
        scope = ldap.SCOPE_SUBTREE
        )
    
    config.ldap_set_groups_query(
#        base_dn='OU=Citysearch Accounts and Security Groups,DC=cs,DC=iac,DC=corp',
#        base_dn='OU=Security Groups,OU=CGM Accounts Security Groups and Distribution Lists,DC=cs,DC=iac,DC=corp',
#        base_dn='OU=User Accounts by Department,OU=CGM Accounts Security Groups and Distribution Lists,DC=cs,DC=iac,DC=corp',
#        base_dn='OU=Distribution Lists,OU=CGM Accounts Security Groups and Distribution Lists,DC=cs,DC=iac,DC=corp',
        base_dn='DC=cs,DC=iac,DC=corp',
        filter_tmpl='(&(objectCategory=group)(member=%(userdn)s))',
#        filter_tmpl='(&(objectCategory=group)(member=%(userdn)s))',
#        filter_tmpl='(&(objectCategory=CN=Organizational-Unit,CN=Schema,CN=Configuration,DC=iac,DC=corp)(member=%(userdn)s))',
#        filter_tmpl='(&(objectCategory=CN=Organizational-Unit,CN=Schema,CN=Configuration,DC=iac,DC=corp)(member=%(userdn)s))',
        scope = ldap.SCOPE_SUBTREE,
        cache_period = 600,
        )

    config.scan()
    return config.make_wsgi_app()
