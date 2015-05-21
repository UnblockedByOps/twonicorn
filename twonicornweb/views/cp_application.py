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
from pyramid.response import Response
from datetime import datetime
import logging
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

            application_name = request.POST['application_name']
            nodegroup = request.POST['nodegroup']
            artifact_types = request.POST.getall('artifact_type')
            deploy_paths = request.POST.getall('deploy_path')
            package_names = request.POST.getall('package_name')
            day_start = request.POST['day_start']
            day_end = request.POST['day_end']
            hour_start = request.POST['hour_start']
            minute_start = request.POST['minute_start']
            hour_end = request.POST['hour_end']
            minute_end = request.POST['minute_end']

            subtitle = 'Add an application'
            # FIXME not trapping because length is the same. - Safari only bug
            if len(deploy_paths) != len(artifact_types):
               error_msg = "You must select an artifact type and specify a deploy path."
            else:

                try:
                    utcnow = datetime.utcnow()
                    create = Application(application_name=application_name, nodegroup=nodegroup, updated_by=user['login'], created=utcnow, updated=utcnow)
                    DBSession.add(create)
                    DBSession.flush()
                    application_id = create.application_id

                    # Create a time window assignment
                    create = DeploymentTimeWindow(application_id=application_id,
                                                  day_start=day_start, 
                                                  day_end=day_end, 
                                                  hour_start=hour_start, 
                                                  minute_start=minute_start, 
                                                  hour_end=hour_end, 
                                                  minute_end=minute_end, 
                                                  updated_by=user['login'],
                                                  created=utcnow,
                                                  updated=utcnow)
                    DBSession.add(create)
                    DBSession.flush()

                    for i in range(len(deploy_paths)):
                        artifact_type_id = ArtifactType.get_artifact_type_id(artifact_types[i])
                        create = Deploy(application_id=application_id, artifact_type_id=artifact_type_id.artifact_type_id, deploy_path=deploy_paths[i], package_name=package_names[i], updated_by=user['login'], created=utcnow, updated=utcnow)
                        DBSession.add(create)
                        deploy_id = create.deploy_id

                    DBSession.flush()

                    return_url = '/deploys?application_id=%s&nodegroup=%s' % (application_id, nodegroup)
                    return HTTPFound(return_url)

                except Exception, e:
                    raise
                    # FIXME not trapping correctly
                    DBSession.rollback()
                    error_msg = ("Failed to create application (%s)" % (e))
                    log.error(error_msg)

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
                application_id = request.POST['application_id']
                application_name = request.POST['application_name']
                nodegroup = request.POST['nodegroup']
                artifact_types = request.POST.getall('artifact_type')
                deploy_ids = request.POST.getall('deploy_id')
                deploy_paths = request.POST.getall('deploy_path')
                package_names = request.POST.getall('package_name')
                day_start = request.POST['day_start']
                day_end = request.POST['day_end']
                hour_start = request.POST['hour_start']
                minute_start = request.POST['minute_start']
                hour_end = request.POST['hour_end']
                minute_end = request.POST['minute_end']


                if len(deploy_paths) != len(artifact_types):
                    error_msg = "You must select an artifact type and specify a deploy path."
                else:

                    # Update the app
                    log.info('UPDATE APP: application_id=%s,application_name=%s,nodegroup=%s,updated_by=%s'
                             % (application_id,
                                application_name,
                                nodegroup,
                                user['login']))
                    log.info('UPDATE TIME WINDOW: application_id=%s,day_start=%s,day_end=%s,hour_start=%s,minute_start=%s,hour_end=%s,minute_end=%s,updated_by=%s'
                             % (application_id,
                                day_start,
                                day_end,
                                hour_start,
                                minute_start,
                                hour_end,
                                minute_end,
                                user['login']))

                    app = DBSession.query(Application).filter(Application.application_id==application_id).one()
                    app.application_name = application_name
                    app.nodegroup = nodegroup
                    app.time_valid.day_start = day_start
                    app.time_valid.day_end = day_end
                    app.time_valid.hour_start = hour_start
                    app.time_valid.minute_start = minute_start
                    app.time_valid.hour_end = hour_end
                    app.time_valid.minute_end = minute_end
                    app.updated_by=user['login']
                    DBSession.flush()

                    # Add/Update deploys
                    for i in range(len(deploy_paths)):
                        deploy_id = None
                        try:
                            deploy_id = deploy_ids[i]
                        except:
                            pass

                        if deploy_id:
                            log.info('UPDATE: deploy=%s,deploy_id=%s,artifact_type=%s,deploy_path=%s,package_name=%s'
                                     % (i,
                                        deploy_id,
                                        artifact_types[i],
                                        deploy_paths[i],
                                        package_names[i]))
                            dep = DBSession.query(Deploy).filter(Deploy.deploy_id==deploy_id).one()
                            artifact_type_id = ArtifactType.get_artifact_type_id(artifact_types[i])
                            dep.artifact_type_id = artifact_type_id.artifact_type_id
                            dep.deploy_path = deploy_paths[i]
                            dep.package_name = package_names[i]
                            dep.updated_by=user['login'] 
                            DBSession.flush()
                            
                        else:
                            log.info('CREATE: deploy=%s,deploy_id=%s,artifact_type=%s,deploy_path=%s,package_name=%s'
                                     % (i,
                                        deploy_id,
                                        artifact_types[i],
                                        deploy_paths[i],
                                        package_names[i]))
                            utcnow = datetime.utcnow()
                            artifact_type_id = ArtifactType.get_artifact_type_id(artifact_types[i])
                            create = Deploy(application_id=application_id, artifact_type_id=artifact_type_id.artifact_type_id, deploy_path=deploy_paths[i], package_name=package_names[i], updated_by=user['login'], created=utcnow, updated=utcnow)
                            DBSession.add(create)
                            DBSession.flush()

                    return_url = '/deploys?application_id=%s&nodegroup=%s' % (application_id, nodegroup)
                    return HTTPFound(return_url)


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
