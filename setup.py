import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.rst')) as f:
    README = f.read()
with open(os.path.join(here, 'CHANGELOG.rst')) as f:
    CHANGELOG = f.read()

requires = [
    'pyramid==1.5.1',
    'pyramid_chameleon==0.3',
    'pyramid_debugtoolbar==2.2',
    'pyramid-tm==0.7',
    'pyramid_ldap==0.2',
    'pyramid-mako==1.0.2',
    'Pygments==1.6',
    'waitress==0.8.9',
    'SQLAlchemy==0.9.7',
    'mysql-connector-python',
    'transaction==1.4.3',
    'zope.sqlalchemy==0.7.5',
    'python-ldap==2.4.16',
    'ldappool==1.0',
    'requests==2.3.0',
    'arrow==0.4.4',
    ]

setup(name='TwonicornWeb',
      version='2.0',
      description='TwonicornWeb',
      long_description=README + '\n\n' + CHANGELOG,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        ],
      author='Aaron Bandt',
      author_email='aaron.bandt@citygridmedia.com',
      url='',
      keywords='Twonicorn web api/ui',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      tests_require=requires,
      test_suite="TwonicornWeb",
      entry_points="""\
      [paste.app_factory]
      main = twonicornweb:main
      [console_scripts]
      initialize_twonicorn-web_db = twonicornweb.scripts.initializedb:main
      """,
      )
