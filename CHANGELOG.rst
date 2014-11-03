Changelog
=========

Next Release (TBD)
------------------

* feature: Support for listing all staged promotions by application.
* feature: Support for jars as an artifact type.
* feature: Auto creation of JIRA tickets.
* cleanup: Fix all the pylint warnings.

2.3
~~~~~~~

* feature: Implimentation of teh API endpoint.

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
* Moving dependency to TwonicornLib from TwonicornWebLib

1.4
~~~~~~~
* bugfix: fixed bug where promote links were shown for confs.

1.3
~~~~~~~
* removing the cheeky commentary on some of the pages

1.2
~~~~~~~
* bugfix: fixed a bug when the referer.url was an outside site (jenkins)

1.1
~~~~~~~
* Support for performing promotions via the UI. Replaces the functionality of
  the promote jenkins job.

1.0
~~~~~~~
* Initial release
