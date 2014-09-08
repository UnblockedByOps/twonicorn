from pyramid.config import Configurator


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings)
    config.include('pyramid_chameleon')
    config.include('pyramid_ldap')
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_route('home', '/')
    config.add_route('applications', '/applications')
    config.add_route('deploys', '/deploys')
    config.add_route('promote', '/promote')
    config.add_route('help', '/help')
    config.scan()
    return config.make_wsgi_app()
