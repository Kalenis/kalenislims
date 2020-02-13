# -*- coding: utf-8 -*-
# This file is part of lims_interface module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

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
    require = '%s >= %s.%s, < %s.%s'
    require %= (name, major_version, minor_version,
        major_version, minor_version + 1)
    return require


def get_lims_require_version(name):
    require = '%s >= %s.%s, < %s.%s'
    require %= (name, lims_major_version, lims_minor_version,
        lims_major_version, lims_minor_version + 1)
    return require


config = ConfigParser()
config.readfp(open('tryton.cfg'))
info = dict(config.items('tryton'))
for key in ('depends', 'extras_depend', 'xml'):
    if key in info:
        info[key] = info[key].strip().splitlines()

version = info.get('version', '5.2.0')
major_version, minor_version, _ = version.split('.', 2)
major_version = int(major_version)
minor_version = int(minor_version)

lims_version = dict(config.items('tryton')).get('version', '5.2.0')
lims_major_version, lims_minor_version, _ = lims_version.split('.', 2)
lims_major_version = int(lims_major_version)
lims_minor_version = int(lims_minor_version)

name = 'lims_interface'
download_url = 'https://www.kalenislims.com'

# TODO: check new openpyxl versions, v.3 seems to be buggy in PyPI
requires = ['formulas', 'openpyxl==2.6.4']
for dep in info.get('depends', []):
    if re.match(r'^lims*', dep):
            continue
    elif not re.match(r'(ir|res|webdav)(\W|$)', dep):
        prefix = MODULE2PREFIX.get(dep, 'trytond')
        requires.append(get_require_version('%s_%s' % (prefix, dep)))
requires.append(get_require_version('trytond'))

tests_require = [get_require_version('proteus')]
dependency_links = []

setup(name=name,
    version=version,
    description=('Import data interface module for Kalenis LIMS'),
    long_description=read('README'),
    author='Pwentu',
    author_email='info@kalenislims.com',
    url='https://www.kalenislims.com',
    download_url=download_url,
    package_dir={'trytond.modules.lims_interface': '.'},
    packages=[
        'trytond.modules.lims_interface',
        'trytond.modules.lims_interface.tests',
        ],
    package_data={
        'trytond.modules.lims_interface': (info.get('xml', []) +
        # ['tryton.cfg', 'view/*.xml', 'locale/*.po', 'locale/override/*.po']),
        ['tryton.cfg', 'view/*.xml']),
        },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Plugins',
        'Framework :: Tryton',
        'Intended Audience :: Developers',
        'Intended Audience :: Laboratory Industry',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Natural Language :: English',
        'Natural Language :: Spanish',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
        ],
    license='GPL-3',
    install_requires=requires,
    dependency_links=dependency_links,
    zip_safe=False,
    entry_points="""
    [trytond.modules]
    lims_interface = trytond.modules.lims_interface
    """,
    test_suite='tests',
    test_loader='trytond.test_loader:Loader',
    tests_require=tests_require,
    )
