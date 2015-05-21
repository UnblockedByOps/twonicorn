#  Copyright 2015 CityGrid Media, LLC
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound
import logging
from passlib.hash import sha512_crypt
from twonicornweb.views import (
    site_layout,
    get_user,
    )

from twonicornweb.models import (
    DBSession,
    User,
    )

log = logging.getLogger(__name__)


@view_config(route_name='user', permission='view', renderer='twonicornweb:templates/user.pt')
def view_user(request):

    user = get_user(request)
    page_title = 'User Data'
    subtitle = user['first_last']
    change_pw = False

    if user['auth_mode'] != 'ldap':

        if 'form.submitted' in request.POST:
            user_name = request.POST['user_name']
            first_name = request.POST['first_name']
            last_name = request.POST['last_name']
            email_address = request.POST['email_address']
            password = request.POST['password']

            # FIXME: Need some security checking here
            if user_name != user['login']:
                log.error('Bad person attemting to do bad things to:' % user_name)
            else:

                # Update
                log.info('UPDATE: user_name=%s,first_name=%s,last_name=%s,email_address=%s,password=%s'
                         % (user_name,
                           first_name,
                           last_name,
                           email_address,
                           '<redacted>'))
                try:
                    user = DBSession.query(User).filter(User.user_name==user_name).one()
                    user.first_name = first_name
                    user.last_name = last_name
                    user.email_address = email_address
                    if password:
                        log.info('Changing password for: user_name=%s password=<redacted>' % user_name)
                        salt = sha512_crypt.genconfig()[17:33]
                        encrypted_password = sha512_crypt.encrypt(password, salt=salt)
                        user.salt = salt
                        user.password = encrypted_password
                        DBSession.flush()
                        return_url = '/logout?message=Your password has been changed successfully. Please log in again.'
                        return HTTPFound(return_url)

                    DBSession.flush()

                except Exception, e:
                    pass
                    log.error("%s (%s)" % (Exception, e))

        user = get_user(request)

    return {'layout': site_layout(),
            'page_title': page_title,
            'subtitle': subtitle,
            'user': user,
            'change_pw': change_pw,
           }
