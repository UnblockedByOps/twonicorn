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
use twonicorn;

# These inserts are required to prime the db. Perhaps at some point
# this would be managed in a web interface?
INSERT INTO lifecycles VALUES (1,'init');
INSERT INTO lifecycles VALUES (2,'current');
INSERT INTO lifecycles VALUES (3,'stage');

INSERT INTO envs VALUES (1,'dev');
INSERT INTO envs VALUES (2,'qat');
INSERT INTO envs VALUES (3,'prd');

INSERT INTO repos VALUES (1,1,'nexus');
INSERT INTO repos VALUES (2,2,'subversion');
INSERT INTO repos VALUES (3,3,'gerrit');
INSERT INTO repos VALUES (4,4,'pip');
INSERT INTO repos VALUES (5,1,'s3-bucket');

INSERT INTO repo_types VALUES (1,'http');
INSERT INTO repo_types VALUES (2,'svn');
INSERT INTO repo_types VALUES (3,'git');
INSERT INTO repo_types VALUES (4,'pip');

INSERT INTO artifact_types VALUES (1,'conf');
INSERT INTO artifact_types VALUES (2,'war');
INSERT INTO artifact_types VALUES (3,'jar');
INSERT INTO artifact_types VALUES (4,'python');
INSERT INTO artifact_types VALUES (5,'tar');

INSERT INTO group_perms VALUES (1,'promote_prd',NOW(),NOW());
INSERT INTO group_perms VALUES (2,'cp',NOW(),NOW());

# Initial Admin password is 'password'
INSERT INTO users VALUES (1, 'Admin', 'Morgan', 'Freeman', 'admin@yourcompany.com', '$6$Vf7ZmjQarLus/TqT', '$6$Vf7ZmjQarLus/TqT$l5qsqY4ntpX8nEzbm33n5StF5D.93yV3uoh8ucthwFf8mEJBitnGLr5SWhzD2vpkpnAJnUiLl40d0hH24qPOq1', 'Admin', NOW(),NOW());
INSERT INTO groups VALUES (1,'local_admin','Admin',NOW(),NOW());
INSERT INTO user_group_assignments VALUES (1, 1, 1, 'Admin', NOW(),NOW());
INSERT INTO group_assignments (group_id,perm_id,user) VALUES (1,1,'Admin');
INSERT INTO group_assignments (group_id,perm_id,user) VALUES (1,2,'Admin');

# These are the only thing in this file that need to be customized for 
# an install at another company.
INSERT INTO repo_urls VALUES (1,1, 'lax1','http://nexus.prod.cs:8081');
INSERT INTO repo_urls VALUES (2,1, 'vir1','http://nexus.prod.cs:8081');
INSERT INTO repo_urls VALUES (3,1, 'aws1','https://nexus-prd-aws1.ctgrd.com:4001');
INSERT INTO repo_urls VALUES (4,2, 'lax1','https://svn.prod.cs');
INSERT INTO repo_urls VALUES (5,2, 'vir1','https://svn.prod.cs');
INSERT INTO repo_urls VALUES (6,2, 'aws1','https://svn-prd-aws1.ctgrd.com:4002');
INSERT INTO repo_urls VALUES (7,3, 'lax1','https://gerrit.ctgrd.com');
INSERT INTO repo_urls VALUES (8,3, 'vir1','https://gerrit.ctgrd.com');
INSERT INTO repo_urls VALUES (9,3, 'aws1','https://gerrit-prd-aws1.ctgrd.com:4003');
INSERT INTO repo_urls VALUES (10,4, 'lax1','http://pip.ctgrd.com/simple/');
INSERT INTO repo_urls VALUES (11,4, 'vir1','http://pip.ctgrd.com/simple/');
INSERT INTO repo_urls VALUES (12,4, 'aws1','http://pip.ctgrd.com/simple/');
