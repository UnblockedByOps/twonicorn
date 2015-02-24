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

INSERT INTO group_perms VALUES (1,'promote_prd',NOW(),NOW());
INSERT INTO group_perms VALUES (2,'cp',NOW(),NOW());



# This is just test data for screwing around in dev/qa and should NOT
# be applied to prod
# INSERT INTO applications VALUES (1,"tst", NOW());
# INSERT INTO applications VALUES (2,"otr", NOW());
# 
# INSERT INTO deploys VALUES (1,1,2,"/app/tomcat/webapp",NOW());
# INSERT INTO deploys VALUES (2,1,1,"/app/tomcat/conf",NOW());
# INSERT INTO deploys VALUES (3,1,1,"/app/logwatcher/etc",NOW());
# INSERT INTO deploys VALUES (4,2,2,"/app/tomcat/webapp",NOW());
# 
# INSERT INTO artifacts VALUES (1,1,"/content/repositories/snapshots/citygrid/core/tracking/rblTracker/2.3.5/rblTracker-2.3.5.war",NULL,1,NOW()-1000);
# INSERT INTO artifacts VALUES (2,2,"/repository/publisher/api/profile-webservice/conf/","229148",1,NOW()-1000);
# INSERT INTO artifacts VALUES (3,2,"/repository/operations/logwatcher/trunk/test/","229199",1,NOW()-1000);
# INSERT INTO artifacts VALUES (4,1,"/content/repositories/snapshots/citygrid/core/tracking/rblTracker/2.3.6/rblTracker-2.3.6.war",NULL,1,NOW()-100);
# INSERT INTO artifacts VALUES (5,1,"/content/repositories/snapshots/citygrid/core/tracking/other/version/something.123.war",NULL,1,NOW()-10);
# INSERT INTO artifacts VALUES (6,1,"/content/repositories/snapshots/citygrid/core/tracking/rblTracker/2.3.7/rblTracker-2.3.7.war",NULL,1,NOW()-1);
# INSERT INTO artifacts VALUES (7,2,"/repository/publisher/api/profile-webservice/conf/","229200",1,NOW());
# INSERT INTO artifacts VALUES (8,1,"/content/repositories/snapshots/citygrid/core/tracking/other/version/something.125.war",NULL,1,NOW());
# 
# INSERT INTO artifact_assignments VALUES (1,1,1,1,1,'heitritterw','2014-03-01 10:00:00'); # initial insert
# INSERT INTO artifact_assignments VALUES (2,2,1,1,2,'heitritterw','2014-03-01 10:00:00');
# INSERT INTO artifact_assignments VALUES (3,3,1,1,3,'heitritterw','2014-03-01 10:00:00');
# INSERT INTO artifact_assignments VALUES (4,1,1,2,1,'heitritterw','2014-03-01 13:00:00'); # promote to dev
# INSERT INTO artifact_assignments VALUES (5,2,1,2,2,'heitritterw','2014-03-01 13:00:00');
# INSERT INTO artifact_assignments VALUES (6,3,1,2,3,'heitritterw','2014-03-01 13:00:00');
# INSERT INTO artifact_assignments VALUES (7,1,2,2,1,'heitritterw','2014-03-02 11:00:00'); # promote to qat
# INSERT INTO artifact_assignments VALUES (8,2,2,2,2,'heitritterw','2014-03-02 11:00:00');
# INSERT INTO artifact_assignments VALUES (9,3,2,2,3,'heitritterw','2014-03-02 11:00:00');
# INSERT INTO artifact_assignments VALUES (10,1,1,1,4,'heitritterw','2014-03-03 10:00:00'); # initial insert 4
# INSERT INTO artifact_assignments VALUES (11,1,1,2,4,'heitritterw','2014-03-03 10:00:00');  # promote to dev 4
# INSERT INTO artifact_assignments VALUES (12,1,3,2,1,'heitritterw','2014-03-03 15:00:00'); # promote to prd
# INSERT INTO artifact_assignments VALUES (13,2,3,2,2,'heitritterw','2014-03-03 15:00:00');
# INSERT INTO artifact_assignments VALUES (14,3,3,2,3,'heitritterw','2014-03-03 15:00:00');
# INSERT INTO artifact_assignments VALUES (15,1,2,2,4,'heitritterw','2014-03-03 15:00:00');  # promote to qat 4
# INSERT INTO artifact_assignments VALUES (16,1,1,1,6,'heitritterw','2014-03-06 11:00:00'); # initial insert 6
# INSERT INTO artifact_assignments VALUES (17,1,1,2,6,'heitritterw','2014-03-06 11:00:00');  # promote to dev 6
# INSERT INTO artifact_assignments VALUES (18,1,3,2,4,'heitritterw','2014-03-06 12:00:00');  # promote to prd 4
# INSERT INTO artifact_assignments VALUES (19,1,2,2,6,'heitritterw','2014-03-06 14:00:00');  # promote to qat 6
# INSERT INTO artifact_assignments VALUES (20,1,3,2,6,'heitritterw',NOW());  # promote to prd 6

# GROUPS
#
# INSERT INTO groups VALUES (1,'CN=Unix_Team,OU=Security Groups,OU=CGM Accounts Security Groups and Distribution Lists,DC=cs,DC=iac,DC=corp','bandta',NOW(),NOW());
# INSERT INTO groups VALUES (2,'CN=CM_Team,OU=Security Groups,OU=CGM Accounts Security Groups and Distribution Lists,DC=cs,DC=iac,DC=corp','bandta',NOW(),NOW());
# 
# 
# INSERT INTO group_assignments (group_id,perm_id,user) VALUES (1,1,'bandta');
# INSERT INTO group_assignments (group_id,perm_id,user) VALUES (1,2,'bandta');
# INSERT INTO group_assignments (group_id,perm_id,user) VALUES (2,2,'bandta');

