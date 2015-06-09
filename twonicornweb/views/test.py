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
from pyramid.view import view_config, forbidden_view_config
from pyramid.httpexceptions import HTTPFound
from pyramid.httpexceptions import HTTPServiceUnavailable
from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPConflict
from pyramid.security import remember, forget
from pyramid.session import signed_serialize
from pyramid_ldap import get_ldap_connector
from pyramid.response import Response
from datetime import datetime
import logging
import os.path
from passlib.hash import sha512_crypt
from twonicornweb.views import (
    site_layout,
    local_authenticate,
    get_user,
    format_window,
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
    User,
    UserGroupAssignment,
    Group,
    GroupPerm,
    GroupAssignment,
    DeploymentTimeWindow,
    )

log = logging.getLogger(__name__)

@view_config(route_name='test', permission='view', renderer='twonicornweb:templates/test.pt')
def view_test(request):

    page_title = 'Test'
    user = get_user(request)

    return {'layout': site_layout(),
            'page_title': page_title,
            'user': user,
           }

