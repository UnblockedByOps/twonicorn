from pyramid.view import view_config

@view_config(context=Exception, renderer='twonicornweb:templates/exception.pt')
def error(exc, request):
    request.response.status_int = 500
    return {'error': exc.message}
