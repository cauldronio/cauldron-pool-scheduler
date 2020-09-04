import os
import codecs
from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))
readme_md = os.path.join(here, 'README.md')
with codecs.open(readme_md, encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="poolsched",
    version="0.1",
    description="A Django app to schedule jobs and analyze them",
    long_description=long_description,
    long_description_content_type='text/markdown',
    license='GPLv3',
    author='cauldron.io',
    author_email='contact@cauldron.io',
    url='https://gitlab.com/cauldronio/cauldron-pool-scheduler',
    packages=['poolsched',
              'poolsched.models',
              'poolsched.migrations',
              'poolsched.models.targets'],
    include_package_data=True,
    keywords="django scheduler cauldron",
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 3.0',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Database :: Database Engines/Servers',
    ],
    install_requires=[
        "django>=3.0",
        "mysqlclient"
    ]
)
