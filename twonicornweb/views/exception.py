from pyramid.view import view_config
from twonicornweb.views import (
    site_layout,
    get_user,
    )

@view_config(context=Exception, renderer='twonicornweb:templates/exception.pt')
def error(exc, request):

    request.response.status_int = 500
    page_title = 'Internal Server Error'
    user = get_user(request)

    return {'layout': site_layout(),
            'page_title': page_title,
            'user': user,
            'error': exc.message
            }
