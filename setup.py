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
    'waitress==0.8.9',
    'pyramid_ldap==0.2',
    'python-ldap==2.4.16',
    'ldappool==1.0',
    'TwonicornLib==1.0',
    ]

setup(name='TwonicornWeb',
      version='1.6',
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
      """,
      )
