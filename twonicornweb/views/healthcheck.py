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
from pyramid.httpexceptions import HTTPServiceUnavailable
import logging
import os.path

log = logging.getLogger(__name__)


@view_config(route_name='healthcheck', renderer='twonicornweb:templates/healthcheck.pt')
def healthcheck(request):

    if os.path.isfile(request.registry.settings['tcw.healthcheck_file']):
        return {'message': 'ok'}
    else:
        return HTTPServiceUnavailable()
