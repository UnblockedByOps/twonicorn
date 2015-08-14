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
from pyramid.httpexceptions import HTTPCreated
from pyramid.response import Response
from datetime import datetime
import logging
import transaction
from twonicornweb.views import (
    site_layout,
    get_user,
    )

from twonicornweb.models import (
    DBSession,
    Application,
    Deploy,
    ArtifactType,
    DeploymentTimeWindow,
    )

log = logging.getLogger(__name__)


def create_application(**kwargs):

    try:
        ss = kwargs['ss']
    except:
        ss = None

    try:
#        foo = bar()
        utcnow = datetime.utcnow()
        create = Application(application_name=kwargs['application_name'],
                             nodegroup=kwargs['nodegroup'],
                             updated_by=kwargs['updated_by'],
                             created=utcnow,
                             updated=utcnow)

        DBSession.add(create)
        DBSession.flush()
        application_id = create.application_id
    
        # Create a time window assignment
        create = DeploymentTimeWindow(application_id=application_id,
                                      day_start=kwargs['day_start'],
                                      day_end=kwargs['day_end'],
                                      hour_start=kwargs['hour_start'],
                                      minute_start=kwargs['minute_start'],
                                      hour_end=kwargs['hour_end'],
                                      minute_end=kwargs['minute_end'],
                                      updated_by=kwargs['updated_by'],
                                      created=utcnow,
                                      updated=utcnow)
        DBSession.add(create)
        DBSession.flush()
    
        for i in range(len(kwargs['deploy_paths'])):
            artifact_type_id = ArtifactType.get_artifact_type_id(kwargs['artifact_types'][i])
            create = Deploy(application_id=application_id,
                            artifact_type_id=artifact_type_id.artifact_type_id,
                            deploy_path=kwargs['deploy_paths'][i],
                            package_name=kwargs['package_names'][i],
                            updated_by=kwargs['updated_by'],
                            created=utcnow,
                            updated=utcnow)
            DBSession.add(create)
    
        DBSession.flush()
        # Have to force commit transaction for self service. 
        # For some reason returning isn't committing.
        transaction.commit()
    
        if ss:
            return_url = '/api/application?id=%s' % (application_id)
            return HTTPCreated(location=return_url)
        else:
            return_url = '/deploys?application_id=%s&nodegroup=%s' % (application_id, kwargs['nodegroup'])
        return HTTPFound(return_url)
    
    except Exception, e:
        error_msg = ("Failed to create application: %s" % (e))
        log.error(error_msg)
        raise Exception(error_msg)

def edit_application(**kwargs):
    # Update the app
    log.info('UPDATE APP: application_id=%s,application_name=%s,nodegroup=%s,updated_by=%s'
             % (kwargs['application_id'],
                kwargs['application_name'],
                kwargs['nodegroup'],
                kwargs['updated_by']))
    log.info('UPDATE TIME WINDOW: application_id=%s,day_start=%s,day_end=%s,hour_start=%s,minute_start=%s,hour_end=%s,minute_end=%s,updated_by=%s'
             % (kwargs['application_id'],
                kwargs['day_start'],
                kwargs['day_end'],
                kwargs['hour_start'],
                kwargs['minute_start'],
                kwargs['hour_end'],
                kwargs['minute_end'],
                kwargs['updated_by']))
    
    app = DBSession.query(Application).filter(Application.application_id==kwargs['application_id']).one()
    app.application_name = kwargs['application_name']
    app.nodegroup = kwargs['nodegroup']
    app.time_valid.day_start = kwargs['day_start']
    app.time_valid.day_end = kwargs['day_end']
    app.time_valid.hour_start = kwargs['hour_start']
    app.time_valid.minute_start = kwargs['minute_start']
    app.time_valid.hour_end = kwargs['hour_end']
    app.time_valid.minute_end = kwargs['minute_end']
    app.updated_by=kwargs['updated_by']
    DBSession.flush()
    
    # Add/Update deploys
    for i in range(len(kwargs['deploy_paths'])):
        deploy_id = None
        try:
            deploy_id = kwargs['deploy_ids'][i]
        except:
            pass
    
        if deploy_id:
            log.info('UPDATE: deploy=%s,deploy_id=%s,artifact_type=%s,deploy_path=%s,package_name=%s'
                     % (i,
                        deploy_id,
                        kwargs['artifact_types'][i],
                        kwargs['deploy_paths'][i],
                        kwargs['package_names'][i]))
            dep = DBSession.query(Deploy).filter(Deploy.deploy_id==deploy_id).one()
            artifact_type_id = ArtifactType.get_artifact_type_id(kwargs['artifact_types'][i])
            dep.artifact_type_id = artifact_type_id.artifact_type_id
            dep.deploy_path = kwargs['deploy_paths'][i]
            dep.package_name = kwargs['package_names'][i]
            dep.updated_by=kwargs['updated_by']
            DBSession.flush()
    
        else:
            log.info('CREATE: deploy=%s,deploy_id=%s,artifact_type=%s,deploy_path=%s,package_name=%s'
                     % (i,
                        deploy_id,
                        kwargs['artifact_types'][i],
                        kwargs['deploy_paths'][i],
                        kwargs['package_names'][i]))
            utcnow = datetime.utcnow()
            artifact_type_id = ArtifactType.get_artifact_type_id(kwargs['artifact_types'][i])
            create = Deploy(application_id=kwargs['application_id'], artifact_type_id=artifact_type_id.artifact_type_id, deploy_path=kwargs['deploy_paths'][i], package_name=kwargs['package_names'][i], updated_by=kwargs['updated_by'], created=utcnow, updated=utcnow)
            DBSession.add(create)
            DBSession.flush()

    # FIXME: This is broken due to the relationship with artifact assignments. Needs discussion on possible solutions.
    # Delete deploys
    for d in kwargs['deploy_ids_delete']:
        try:
            log.info('DELETE Deploy: application_id=%s,deploy_id=%s'
                     % (kwargs['application_id'], d))
    
            q = DBSession.query(Deploy)
            q = q.filter(Deploy.deploy_id==d)
            q = q.one()

            DBSession.delete(q)
            DBSession.flush()
        except Exception as e:
            log.error('Error DELETE Deploy: application_id=%s,deploy_id=%s,exception=%s'
                     % (kwargs['application_id'], d, str(e)))


    return_url = '/deploys?application_id=%s' % (kwargs['application_id'])
    return HTTPFound(return_url)


@view_config(route_name='cp_application', permission='cp', renderer='twonicornweb:templates/cp_application.pt')
def view_cp_application(request):

    page_title = 'Control Panel - Application'
    user = get_user(request)

    params = {'mode': None,
              'commit': None,
              'application_id': None,
             }
    for p in params:
        try:
            params[p] = request.params[p]
        except:
            pass

    mode = params['mode']
    commit = params['commit']
    application_id = params['application_id']
    app = None
    nodegroup = None
    deploy_id = None
    error_msg = None
    artifact_types = None

    try:
        q = DBSession.query(ArtifactType)
        artifact_types = q.all()
    except Exception, e:
        log.error("Failed to retrive data on api call (%s)" % (e))
        return log.error

    if mode == 'add':

        subtitle = 'Add an application'

        if commit:

            ca = {'application_name': request.POST['application_name'],
                  'nodegroup': request.POST['nodegroup'],
                  'artifact_types': request.POST.getall('artifact_type'),
                  'deploy_paths': request.POST.getall('deploy_path'),
                  'package_names': request.POST.getall('package_name'),
                  'day_start': request.POST['day_start'],
                  'day_end': request.POST['day_end'],
                  'hour_start': request.POST['hour_start'],
                  'minute_start': request.POST['minute_start'],
                  'hour_end': request.POST['hour_end'],
                  'minute_end': request.POST['minute_end'],
                  'updated_by': user['login']
            }

            # FIXME not trapping because length is the same. - Safari only bug
            if len(ca['deploy_paths']) != len(ca['artifact_types']):
               error_msg = "You must select an artifact type and specify a deploy path."
            else:

                return create_application(**ca)

    if mode == 'edit':

       subtitle = 'Edit an application'

       if not commit:

           try:
               q = DBSession.query(Application)
               q = q.filter(Application.application_id == application_id)
               app = q.one()
           except Exception, e:
               conn_err_msg = e
               return Response(str(conn_err_msg), content_type='text/plain', status_int=500)

       if commit:

           subtitle = 'Edit an application'

           if 'form.submitted' in request.POST:
                ea = {'application_id': request.POST['application_id'],
                      'application_name': request.POST['application_name'],
                      'nodegroup': request.POST['nodegroup'],
                      'artifact_types': request.POST.getall('artifact_type'),
                      'deploy_ids': request.POST.getall('deploy_id'),
                      'deploy_ids_delete': request.POST.getall('deploy_id_delete'),
                      'deploy_paths': request.POST.getall('deploy_path'),
                      'package_names': request.POST.getall('package_name'),
                      'day_start': request.POST['day_start'],
                      'day_end': request.POST['day_end'],
                      'hour_start': request.POST['hour_start'],
                      'minute_start': request.POST['minute_start'],
                      'hour_end': request.POST['hour_end'],
                      'minute_end': request.POST['minute_end'],
                      'updated_by': user['login']
                }

                if len(ea['deploy_paths']) != len(ea['artifact_types']):
                    error_msg = "You must select an artifact type and specify a deploy path."
                else:

                    # Update the app
                    return edit_application(**ea)

    return {'layout': site_layout(),
            'page_title': page_title,
            'user': user,
            'subtitle': subtitle,
            'app': app,
            'application_id': application_id,
            'nodegroup': nodegroup,
            'deploy_id': deploy_id,
            'artifact_types': artifact_types,
            'mode': mode,
            'commit': commit,
            'error_msg': error_msg,
           }
