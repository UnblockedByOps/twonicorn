Changelog
=========

Wishlist
------------------

* feature: Support for listing/promoting all staged promotions by application.
* feature: Auto creation of JIRA tickets.
* cleanup: Fix all the pylint warnings.

2.8.10
~~~~~~~
bugfix: Missed the bug on editing an application.

2.8.9
~~~~~~~
bugfix: jar artifact type also requires package_name.

2.8.8
~~~~~~~
feature: Updated/cleaned up some styles and a more unified look & feel.

2.8.7
~~~~~~~
feature: Time-window based deployment implementation. Provides a role where groups can be assigned permission to promote to prod within a given time window.

2.8.6
~~~~~~~
bugfix: Fixing the svn conf promote url display
feature: Upping pages to 50 results

2.8.5
~~~~~~~
* feature: fixing default urls and making deploy.py look at it's own secrets conf
* feature: making svn user/pass a config item
* bugfix: catching invalid location

2.8.4
~~~~~~~
* feature: Local users functionality for those who don't want to use Active Directory/LDAP for authentication.

2.8.3
~~~~~~~
* bugfix: Forgot to rename parameter of api.

2.8.2
~~~~~~~
* feature: Adding support for local users/groups
* feature: Support for jars as an artifact type.
* feature: Support for tars as an artifact type.
* bugfix: Renaming ambiguous 'users' columns to 'updated_by.

2.8.1
~~~~~~~
* bugfix: Chaging the artifact type for a deploy not updating db.
* bugfix: Unable to get artifact type from db if there is not an existing artifact assignment.

2.8
~~~~~~~
* feature: Moving group management to the db. Additions to the control panel to manage them.

2.7
~~~~~~~
* feature: Control panel for admins, allows to create and edit applications and deploys within the UI.

2.6
~~~~~~~
* feature: New PUT API. Injection no longer requires direct DB access.

2.5.1
~~~~~~~
* feature: Adding python package support

2.5
~~~~~~~
* bugfix: API no longer requires auth for deployments.

2.4
~~~~~~~
* bugfix: hardcode cgm version of mysql-connector-python.

2.3
~~~~~~~
* feature: Implimentation of the API endpoint.

2.2
~~~~~~~
* bugfix: Fix exception when a deploy has no entry in the database yet.

2.1
~~~~~~~
* bugfix: explicitly inserting with utc timestamp.

2.0
~~~~~~~
* Switched to SQLAlchemy

1.5.1
~~~~~~~
* Fixing a bad cut and paste in the qat repeat of deploys.pt

1.5
~~~~~~~
* Moving dependency to TwonicornLib from TwonicornWebLib.

1.4
~~~~~~~
* bugfix: fixed bug where promote links were shown for confs.

1.3
~~~~~~~
* removing the cheeky commentary on some of the pages.

1.2
~~~~~~~
* bugfix: fixed a bug when the referer.url was an outside site (jenkins).

1.1
~~~~~~~
* Support for performing promotions via the UI. Replaces the functionality of the promote jenkins job.

1.0
~~~~~~~
* Initial release
