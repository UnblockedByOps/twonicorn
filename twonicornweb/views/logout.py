from pyramid.view import view_config
from pyramid.security import forget
import logging
from arsenalweb.views import (
    site_layout,
    )

@view_config(route_name='logout', renderer='arsenalweb:templates/logout.pt')
def logout(request):

    page_title = 'Login'
    message = None

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
    
    return {'layout': site_layout('max'),
            'page_title': page_title,
            'message': message,
            }
