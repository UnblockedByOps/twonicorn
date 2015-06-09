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
    format_window,
    )

from twonicornweb.models import (
    DBSession,
    Application,
    Artifact,
    ArtifactAssignment,
    Env,
    )

log = logging.getLogger(__name__)


@view_config(route_name='promote', permission='view', renderer='twonicornweb:templates/promote.pt')
def view_promote(request):

    page_title = 'Promote'
    user = get_user(request)
    office_loc = request.registry.settings['tcw.office_loc']

    error = ''
    message = ''
    promote = ''
    valid_time = None

    params = {'deploy_id': None,
              'artifact_id': None,
              'to_env': None,
              'commit': 'false'
             }
    for p in params:
        try:
            params[p] = request.params[p]
        except:
            pass

    deploy_id = params['deploy_id']
    artifact_id = params['artifact_id']
    to_env = params['to_env']
    commit = params['commit']
    referer = request.referer

    if not any((user['promote_prd_auth'], user['promote_prd_time_auth'])) and to_env == 'prd':
        to_state = '3'
    else:
        to_state = '2'

    try:
        promote = Artifact.get_promotion(office_loc,to_env, deploy_id, artifact_id)
    except Exception, e:
        conn_err_msg = e
        return Response(str(conn_err_msg), content_type='text/plain', status_int=500)

    if artifact_id and commit == 'true':
        if not any((user['promote_prd_auth'], user['promote_prd_time_auth'])) and to_env == 'prd' and to_state == '2':
            error = True
            message = 'You do not have permission to perform the promote action on production!'
        else:
            # Actually promoting
            try:
                app = Application.get_app_by_deploy_id(deploy_id)

                # Check on time based-users
                if user['promote_prd_time_auth'] and not user['promote_prd_auth'] and to_env == 'prd' and to_state == '2':
                    log.info("%s has access via time based promote permission" % (user['login']))
                    w = app.time_valid
                    fw = format_window(w)
                    if w.valid:
                        log.info("Promotion attempt by %s is inside the valid window: %s" % (user['login'], fw))
                        valid_time = True
                    else:
                        log.error("Promotion attempt by %s is outside the valid window for %s: %s" % (user['login'], app.application_name, fw))
                else:
                    valid_time = True
                    log.info("%s has access via global promote permission" % (user['login']))

                if valid_time:
                    # Convert the env name to the id
                    env_id = Env.get_env_id(to_env)

                    # Assign
                    utcnow = datetime.utcnow()
                    promote = ArtifactAssignment(deploy_id=deploy_id, artifact_id=artifact_id, env_id=env_id.env_id, lifecycle_id=to_state, updated_by=user['login'], created=utcnow)
                    DBSession.add(promote)
                    DBSession.flush()
                    
                    return_url = '/deploys?application_id=%s&nodegroup=%s&artifact_id=%s&to_env=%s&to_state=%s&commit=%s' % (app.application_id, app.nodegroup, artifact_id, to_env, to_state, commit)
                    return HTTPFound(return_url)
                else:
                    error = True
                    message = "ACCESS DENIED: You are attempting to promote outside the allowed time window for %s: %s" % (app.application_name, fw)
            except Exception, e:
                log.error("Failed to promote artifact (%s)" % (e))

    return {'layout': site_layout(),
            'page_title': page_title,
            'user': user,
            'error': error,
            'message': message,
            'deploy_id': deploy_id,
            'artifact_id': artifact_id,
            'to_env': to_env,
            'to_state': to_state,
            'commit': commit,
            'promote': promote,
            'referer': referer,
           }
