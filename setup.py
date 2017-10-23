#!/usr/bin/env python
# encoding: utf-8

from setuptools import setup
import re
import os
import io
try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser

MODULE2PREFIX = {}


def read(fname):
    return io.open(
        os.path.join(os.path.dirname(__file__), fname),
        'r', encoding='utf-8').read()


def get_require_version(name):
    if minor_version % 2:
        require = '%s >= %s.%s.dev0, < %s.%s'
    else:
        require = '%s >= %s.%s, < %s.%s'
    require %= (name, major_version, minor_version,
        major_version, minor_version + 1)
    return require


version = '4.4.0'
major_version, minor_version, _ = version.split('.', 2)
major_version = int(major_version)
minor_version = int(minor_version)

requires = ['pytz', 'xlrd', 'xlutils']
packages = []
package_dir = {}
package_data = {}
module_entry_points = []

for name in os.listdir('.'):
    cfg = os.path.join(name, 'tryton.cfg')
    if not os.path.isfile(cfg):
        continue
    config = ConfigParser()
    config.readfp(open(cfg))
    info = dict(config.items('tryton'))
    for key in ('depends', 'extras_depend', 'xml'):
        if key in info:
            info[key] = info[key].strip().splitlines()
    for dep in info.get('depends', []):
        if re.match(r'^lims*', dep):
            continue
        if not re.match(r'(ir|res)(\W|$)', dep):
            prefix = MODULE2PREFIX.get(dep, 'trytond')
            requires.append(get_require_version('%s_%s' % (prefix, dep)))
    package = 'trytond.modules.%s' % name
    package_dir[package] = os.path.join('.', name)
    packages.append(package)
    if os.path.isdir(os.path.join(name, 'tests')):
        packages.append(package + '.tests')
    module_entry_points.append('%s = %s' % (name, package))
    for suffix in [None, 'report', 'wizard']:
        data = []
        if not suffix:
            for data_pattern in (info.get('xml', []) + ['tryton.cfg']):
                data.append(data_pattern)
            subpackage = package
        elif os.path.isdir(os.path.join(name, suffix)):
            subpackage = package + '.' + suffix
            package_dir[subpackage] = os.path.join(name, suffix)
            packages.append(subpackage)
        for data_pattern in (info.get('xml', []) + ['view/*.xml',
                    'locale/*.po', '*.odt', 'icons/*.svg', 'tests/*.rst']):
            data.append(data_pattern)
        if data:
            package_data[subpackage] = data
requires.append(get_require_version('trytond'))

tests_require = []
dependency_links = []
if minor_version % 2:
    # Add development index for testing with proteus
    dependency_links.append('https://trydevpi.tryton.org/')

setup(name='kalenis_lims',
    version=version,
    description='Kalensis LIMS & ERP',
    long_description=read('README.md'),
    author='',
    author_email='info@kalensis.com',
    url='http://www.kalensis.com/',
    download_url='https://bitbucket.org/kalenis/kalenislims',
    keywords='',
    package_dir=package_dir,
    packages=packages,
    package_data=package_data,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Plugins',
        'Framework :: Tryton',
        'Intended Audience :: Developers',
        'Intended Audience :: Financial and Insurance Industry',
        'Intended Audience :: Legal Industry',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Office/Business',
        ],
    license='GPL-3',
    install_requires=requires,
    dependency_links=dependency_links,
    zip_safe=False,
    entry_points="""
    [trytond.modules]
    %s
    """ % '\n'.join(module_entry_points),
    test_suite='tests',
    test_loader='trytond.test_loader:Loader',
    tests_require=tests_require,
    use_2to3=True,
    )
