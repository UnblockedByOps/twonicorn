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
from pyramid.httpexceptions import HTTPConflict
from pyramid.response import Response
from datetime import datetime
import logging
from passlib.hash import sha512_crypt
from twonicornweb.views import (
    site_layout,
    get_user,
    )

from twonicornweb.models import (
    DBSession,
    User,
    UserGroupAssignment,
    Group,
    )

log = logging.getLogger(__name__)


@view_config(route_name='cp_user', permission='cp', renderer='twonicornweb:templates/cp_user.pt')
def view_cp_user(request):

    page_title = 'Control Panel - Users'
    user = get_user(request)
    users = DBSession.query(User).all()
    groups = DBSession.query(Group).all()

    params = {'mode': None,
              'commit': None,
              'user_id': None,
             }
    for p in params:
        try:
            params[p] = request.params[p]
        except:
            pass

    mode = params['mode']
    commit = params['commit']
    user_id = params['user_id']
    error_msg = None
    this_user = None
    this_groups = None
    subtitle = 'Users'

    if mode == 'add':

        subtitle = 'Add a new user'

        if commit:

            user_names = request.POST.getall('user_name')
            first_names = request.POST.getall('first_name')
            last_names= request.POST.getall('last_name')
            email_addresses = request.POST.getall('email_address')
            passwords = request.POST.getall('password')

            try:
                utcnow = datetime.utcnow()
                for u in range(len(user_names)):
                    salt = sha512_crypt.genconfig()[17:33]
                    encrypted_password = sha512_crypt.encrypt(passwords[u], salt=salt)
                    create = User(user_name=user_names[u], first_name=first_names[u], last_name=last_names[u], email_address=email_addresses[u], salt=salt, password=encrypted_password, updated_by=user['login'], created=utcnow, updated=utcnow)
                    DBSession.add(create)
                    DBSession.flush()
                    user_id = create.user_id

                    group_assignments = request.POST.getall('group_assignments')

                    for a in group_assignments:
                        g = DBSession.query(Group).filter(Group.group_name==a).one()
                        create = UserGroupAssignment(group_id=g.group_id, user_id=user_id, updated_by=user['login'], created=utcnow, updated=utcnow)
                        DBSession.add(create)

                        DBSession.flush()

                return_url = '/cp/user'
                return HTTPFound(return_url)

            except Exception as ex:
                if type(ex).__name__ == 'IntegrityError':
                    log.error('User already exists in the db, please edit instead.')
                    # Rollback
                    DBSession.rollback()
                    # FIXME: Return a nice page
                    return HTTPConflict('User already exists in the db, please edit instead.')
                else:
                    raise
                    # FIXME not trapping correctly
                    DBSession.rollback()
                    error_msg = ("Failed to create user (%s)" % (ex))
                    log.error(error_msg)

    if mode == 'edit':

       subtitle = 'Edit user'

       if not commit:
           try:
               q = DBSession.query(User)
               q = q.filter(User.user_id == user_id)
               this_user = q.one()

               q = DBSession.query(Group)
               q = q.join(UserGroupAssignment, Group.group_id== UserGroupAssignment.group_id)
               q = q.filter(UserGroupAssignment.user_id==this_user.user_id)
               results = q.all()
               this_groups = []
               for r in results:
                   this_groups.append(r.group_name) 
           except Exception, e:
               conn_err_msg = e
               return Response(str(conn_err_msg), content_type='text/plain', status_int=500)

       if commit:

           if 'form.submitted' in request.POST:
                user_id = request.POST.get('user_id')
                user_name = request.POST.get('user_name')
                first_name = request.POST.get('first_name')
                last_name = request.POST.get('last_name')
                email_address = request.POST.get('email_address')
                password = request.POST.get('password')
                group_assignments = request.POST.getall('group_assignments')
             
                # Update the user
                utcnow = datetime.utcnow()
                this_user = DBSession.query(User).filter(User.user_id==user_id).one()
                this_user.user_name = user_name
                this_user.first_name = first_name
                this_user.last_name = last_name
                this_user.email_address = email_address
                if password:
                    salt = sha512_crypt.genconfig()[17:33]
                    encrypted_password = sha512_crypt.encrypt(password, salt=salt)
                    this_user.salt = salt
                    this_user.password = encrypted_password
                this_user.updated_by=user['login']
                DBSession.flush()

                for g in groups:
                    if str(g.group_id) in group_assignments:
                        # assign
                        log.debug("Group: %s is in group assignments" % g.group_name)
                        q = DBSession.query(UserGroupAssignment).filter(UserGroupAssignment.group_id==g.group_id, UserGroupAssignment.user_id==this_user.user_id)
                        check = DBSession.query(q.exists()).scalar()
                        if not check:
                            log.info("Assigning local user %s to group %s" % (this_user.user_name, g.group_name))
                            update = UserGroupAssignment(group_id=g.group_id, user_id=user_id, updated_by=user['login'], created=utcnow, updated=utcnow)
                            DBSession.add(update)
                            DBSession.flush()
                    else:
                        # delete
                        log.debug("Checking to see if we need to remove assignment for user: %s in group %s" % (this_user.user_name,g.group_name))
                        q = DBSession.query(UserGroupAssignment).filter(UserGroupAssignment.group_id==g.group_id, UserGroupAssignment.user_id==this_user.user_id)
                        check = DBSession.query(q.exists()).scalar()
                        if check:
                            log.info("Removing local user %s from group %s" % (this_user.user_name, g.group_name))
                            assignment = DBSession.query(UserGroupAssignment).filter(UserGroupAssignment.group_id==g.group_id, UserGroupAssignment.user_id==this_user.user_id).one()
                            DBSession.delete(assignment)
                            DBSession.flush()
                        
                return_url = '/cp/user'
                return HTTPFound(return_url)

    return {'layout': site_layout(),
            'page_title': page_title,
            'user': user,
            'this_user': this_user,
            'this_groups': this_groups,
            'user_id': user_id,
            'users': users,
            'groups': groups,
            'subtitle': subtitle,
            'mode': mode,
            'commit': commit,
            'error_msg': error_msg,
           }
