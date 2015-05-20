from pyramid.view import view_config
import logging
from arsenalweb.views import (
    site_layout,
    )

@view_config(route_name='help', renderer='arsenalweb:templates/help.pt')
def help(request):

    page_title = 'Login'

    return {'layout': site_layout('max'),
            'page_title': page_title,
            }


