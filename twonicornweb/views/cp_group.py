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
from twonicornweb.views import (
    site_layout,
    get_user,
    )

from twonicornweb.models import (
    DBSession,
    Group,
    GroupPerm,
    GroupAssignment,
    )

log = logging.getLogger(__name__)


@view_config(route_name='cp_group', permission='cp', renderer='twonicornweb:templates/cp_group.pt')
def view_cp_group(request):

    page_title = 'Control Panel - Groups'
    user = get_user(request)
    all_perms = DBSession.query(GroupPerm).all()
    groups = DBSession.query(Group).all()

    params = {'mode': None,
              'commit': None,
              'group_id': None,
             }
    for p in params:
        try:
            params[p] = request.params[p]
        except:
            pass

    mode = params['mode']
    commit = params['commit']
    group_id = params['group_id']
    error_msg = None
    group_perms = None
    group = None
    subtitle = 'Groups'

    if mode == 'add':

        subtitle = 'Add a new group'

        if commit:

            subtitle = 'Add a new group'

            group_names = request.POST.getall('group_name')

            try:
                utcnow = datetime.utcnow()
                for g in range(len(group_names)):
                    create = Group(group_name=group_names[g], updated_by=user['login'], created=utcnow, updated=utcnow)
                    DBSession.add(create)
                    DBSession.flush()
                    group_id = create.group_id

                    i = 'group_perms' + str(g)
                    group_perms = request.POST.getall(i)

                    for p in group_perms:
                        perm = GroupPerm.get_group_perm_id(p)
                        create = GroupAssignment(group_id=group_id, perm_id=perm.perm_id, updated_by=user['login'], created=utcnow, updated=utcnow)
                        DBSession.add(create)
                        group_assignment_id = create.group_assignment_id

                        DBSession.flush()

                return_url = '/cp/group'
                return HTTPFound(return_url)

            except Exception as ex:
                if type(ex).__name__ == 'IntegrityError':
                    log.error('Group already exists in the db, please edit instead.')
                    # Rollback
                    DBSession.rollback()
                    # FIXME: Return a nice page
                    return HTTPConflict('Group already exists in the db, please edit instead.')
                else:
                    raise
                    # FIXME not trapping correctly
                    DBSession.rollback()
                    error_msg = ("Failed to create application (%s)" % (ex))
                    log.error(error_msg)

    if mode == 'edit':

       subtitle = 'Edit group permissions'

       if not commit:
           subtitle = 'Edit group permissions'

           try:
               q = DBSession.query(Group)
               q = q.filter(Group.group_id == group_id)
               group = q.one()
           except Exception, e:
               conn_err_msg = e
               return Response(str(conn_err_msg), content_type='text/plain', status_int=500)

       if commit:

           subtitle = 'Edit group permissions'

           if 'form.submitted' in request.POST:
                group_id = request.POST.get('group_id')
                group_name = request.POST.get('group_name')
                perms = request.POST.getall('perms')
             
                # Update the group
                utcnow = datetime.utcnow()
                group = DBSession.query(Group).filter(Group.group_id==group_id).one()
                group.group_name = group_name
                group.updated_by=user['login']
                DBSession.flush()

                # Update the perms
                all_perms = DBSession.query(GroupPerm)
                for p in all_perms:
                    # insert
                    if p.perm_name in perms:
                        perm = GroupPerm.get_group_perm_id(p.perm_name)
                        q = DBSession.query(GroupAssignment).filter(GroupAssignment.group_id==group_id, GroupAssignment.perm_id==perm.perm_id)
                        check = DBSession.query(q.exists()).scalar()
                        if not check:
                            log.info("Adding permission %s for group %s" % (p.perm_name, group_name))
                            utcnow = datetime.utcnow()
                            create = GroupAssignment(group_id=group_id, perm_id=perm.perm_id, updated_by=user['login'], created=utcnow, updated=utcnow)
                            DBSession.add(create)
                            DBSession.flush()
    
                    # delete
                    else:
                        perm = GroupPerm.get_group_perm_id(p.perm_name)
                        q = DBSession.query(GroupAssignment).filter(GroupAssignment.group_id==group_id, GroupAssignment.perm_id==perm.perm_id)
                        check = DBSession.query(q.exists()).scalar()
                        if check:
                            log.info("Deleting permission %s for group %s" % (p.perm_name, group_name))
                            assignment = DBSession.query(GroupAssignment).filter(GroupAssignment.group_id==group_id, GroupAssignment.perm_id==perm.perm_id).one()
                            DBSession.delete(assignment)
                            DBSession.flush()

                return_url = '/cp/group'
                return HTTPFound(return_url)

    return {'layout': site_layout(),
            'page_title': page_title,
            'user': user,
            'group': group,
            'group_id': group_id,
            'group_perms': group_perms,
            'groups': groups,
            'all_perms': all_perms,
            'subtitle': subtitle,
            'mode': mode,
            'commit': commit,
            'error_msg': error_msg,
           }
