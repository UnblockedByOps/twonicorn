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
from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPConflict
from datetime import datetime
import logging
from twonicornweb.views import (
    basicauth,
    )

from twonicornweb.models import (
    DBSession,
    Application,
    Deploy,
    Artifact,
    ArtifactAssignment,
    Lifecycle,
    Env,
    RepoType,
    ArtifactType,
    RepoUrl,
    )

log = logging.getLogger(__name__)


@view_config(route_name='api', request_method='GET', renderer='json')
def view_api(request):

    params = {'id': None,
              'env': None,
              'loc': None,
              'lifecycle': None,
              'deploy_id': None,
             }
    for p in params:
        try:
            params[p] = request.params[p]
        except:
            pass

    id = params['id']
    env = params['env']
    loc = params['loc']
    lifecycle = params['lifecycle']
    deploy_id = params['deploy_id']
    results = []

    if request.matchdict['resource'] == 'application':
        try:
            q = DBSession.query(Application)
            q = q.filter(Application.application_id == id)
            app = q.one()
        except Exception, e:
            log.error("Failed to retrive data on api call (%s)" % (e))
            return results

        for d in app.deploys:
            each = {}
            a = d.get_assignment(env, lifecycle)
            if a:
                try:
                    each['download_url'] = a.artifact.repo.get_url(loc).url + a.artifact.location
                # FIXME: Better to return empty json?
                except AttributeError:
                    each['download_url'] = 'Invalid location'
                    results.append(each)
                    continue
                each['deploy_id'] = d.deploy_id
                each['package_name'] = d.package_name
                each['artifact_assignment_id'] = a.artifact_assignment_id
                each['deploy_path'] = d.deploy_path
                each['revision'] = a.artifact.revision[:8]
                each['artifact_type'] = d.type.name
                each['repo_type'] = a.artifact.repo.type.name
                each['repo_name'] = a.artifact.repo.name
                each['lifecycle'] = a.lifecycle.name
            results.append(each)

    if request.matchdict['resource'] == 'deploy':
        try:
            q = DBSession.query(Deploy)
            q = q.filter(Deploy.deploy_id == id)
            deploy = q.one()
        except Exception, e:
            log.error("Failed to retrive data on api call (%s)" % (e))
            return results

        each = {}
        a = deploy.get_assignment(env, lifecycle)
        if a:
            try:
                each['download_url'] = a.artifact.repo.get_url(loc).url + a.artifact.location
                each['deploy_id'] = deploy.deploy_id
                each['package_name'] = deploy.package_name
                each['artifact_assignment_id'] = a.artifact_assignment_id
                each['deploy_path'] = deploy.deploy_path
                each['revision'] = a.artifact.revision[:8]
                each['artifact_type'] = deploy.type.name
                each['repo_type'] = a.artifact.repo.type.name
                each['repo_name'] = a.artifact.repo.name
                each['lifecycle'] = a.lifecycle.name
            # FIXME: Better to return empty json?
            except AttributeError:
                each['download_url'] = 'Invalid location'
                results.append(each)
        results.append(each)

    if request.matchdict['resource'] == 'artifact':
        try:
            q = DBSession.query(Artifact)
            q = q.filter(Artifact.artifact_id == id)
            artifact = q.one()
        except Exception, e:
            log.error("Failed to retrive data on api call (%s)" % (e))
            return results

        each = {}
        try:
            each['download_url'] = artifact.repo.get_url(loc).url + artifact.location
            each['artifact_id'] = artifact.artifact_id
            each['branch'] = artifact.branch
            each['created'] = artifact.localize_date_created
            each['repo_id'] = artifact.repo_id
            each['repo_type'] = artifact.repo.type.name
            each['revision'] = artifact.revision
            each['valid'] = artifact.valid
        # FIXME: Better to return empty json?
        except AttributeError:
            each['download_url'] = 'Invalid location'
        results.append(each)

    if request.matchdict['resource'] == 'envs':
        try:
            q = DBSession.query(Env)
            envs = q.all()
        except Exception, e:
            log.error("Failed to retrive data on api call (%s)" % (e))
            return results

        for e in envs:
            each = {}
            each['env_id'] = e.env_id
            each['name'] = e.name
            results.append(each)

    if request.matchdict['resource'] == 'repo_types':
        try:
            q = DBSession.query(RepoType)
            repo_types = q.all()
        except Exception, e:
            log.error("Failed to retrive data on api call (%s)" % (e))
            return results

        for r in repo_types:
            each = {}
            each['repo_type_id'] = r.repo_type_id
            each['name'] = r.name
            results.append(each)

    if request.matchdict['resource'] == 'artifact_types':
        if deploy_id:
            try:
                q = DBSession.query(ArtifactType)
                q = q.join(Deploy, ArtifactType.artifact_type_id == Deploy.artifact_type_id)
                q = q.filter(Deploy.deploy_id==deploy_id)
                r = q.one()
                results.append({'artifact_type':  r.name})
            except Exception, e:
                log.error("Failed to retrive data on api call (%s)" % (e))
                return results
        else:
            try:
                q = DBSession.query(ArtifactType)
                artifact_types = q.all()
            except Exception, e:
                log.error("Failed to retrive data on api call (%s)" % (e))
                return results

            for a in artifact_types:
                each = {}
                each['artifact_type_id'] = a.artifact_type_id
                each['name'] = a.name
                results.append(each)

    if request.matchdict['resource'] == 'lifecycles':
        try:
            q = DBSession.query(Lifecycle)
            lifecycles = q.all()
        except Exception, e:
            log.error("Failed to retrive data on api call (%s)" % (e))
            return results

        for l in lifecycles:
            each = {}
            each['lifecycle_id'] = l.lifecycle_id
            each['name'] = l.name
            results.append(each)

    if request.matchdict['resource'] == 'repo_urls':
        try:
            q = DBSession.query(RepoUrl)
            repo_urls = q.all()
        except Exception, e:
            log.error("Failed to retrive data on api call (%s)" % (e))
            return results

        for r in repo_urls:
            each = {}
            each['ct_loc'] = r.ct_loc
            each['repo_id'] = r.repo_id
            each['repo_url_id'] = r.repo_url_id
            each['url'] = r.url
            results.append(each)

    return results


@view_config(route_name='api', request_method='PUT', renderer='json')
def write_api(request):

    # Require auth
    if not basicauth(request, request.registry.settings['tcw.api_user'], request.registry.settings['tcw.api_pass']):
        return HTTPForbidden('Invalid username/password')

    results = []
    params = {'deploy_id': None,
              'artifact_id': None,
              'repo_id': None,
              'env': None,
              'location': None,
              'branch': None,
              'revision': None,
              'updated_by': None,
             }
    for p in params:
        try:
            params[p] = request.params[p]
        except:
            pass

    deploy_id = params['deploy_id']
    artifact_id = params['artifact_id']
    repo_id = params['repo_id']
    env = params['env']
    location = params['location']
    revision = params['revision']
    branch = params['branch']
    updated_by = params['updated_by']

    # Dev and qat go live immediately, prd goes to init
    if env == 'prd':
        lifecycle_id = '1'
    else:
        lifecycle_id = '2'

    if request.matchdict['resource'] == 'artifact':

        try:
            utcnow = datetime.utcnow()
            create = Artifact(repo_id=repo_id, location=location, revision=revision, branch=branch, valid='1', created=utcnow)
            DBSession.add(create)
            DBSession.flush()
            artifact_id = create.artifact_id
        
            each = {}
            each['artifact_id'] = artifact_id
            results.append(each)

            return results
    
        except Exception as ex:
            if type(ex).__name__ == 'IntegrityError':
                log.info('Artifact location/revision combination '
                         'is not unique. Nothing to do.')
                # Rollback
                DBSession.rollback()
                return HTTPConflict('Artifact location/revision combination '
                                     'is not unique. Nothing to do.')
            else:
                # Rollback in case there is any error
                DBSession.rollback()
                raise
                log.error('There was an error updating the db!')

    if request.matchdict['resource'] == 'artifact_assignment':

        # Convert the env name to the id
        env_id = Env.get_env_id(env)

        try:
            utcnow = datetime.utcnow()
            assign = ArtifactAssignment(deploy_id=deploy_id, artifact_id=artifact_id, env_id=env_id.env_id, lifecycle_id=lifecycle_id, updated_by=updated_by, created=utcnow)
            DBSession.add(assign)
            DBSession.flush()
            artifact_assignment_id = assign.artifact_assignment_id

            each = {}
            each['artifact_assignment_id'] = artifact_assignment_id
            results.append(each)

            return results

        except Exception as ex:
            if type(ex).__name__ == 'IntegrityError':
                log.info('Artifact location/revision combination '
                         'is not unique. Nothing to do.')
                # Rollback
                DBSession.rollback()
                return HTTPConflict('Artifact location/revision combination '
                                     'is not unique. Nothing to do.')
            else:
                # Rollback in case there is any error
                DBSession.rollback()
                raise
                log.error('There was an error updating the db!')

