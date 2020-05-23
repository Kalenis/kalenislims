#!/usr/bin/env python3
# encoding: utf-8

import io
import os
import re
from configparser import ConfigParser
from setuptools import setup

MODULE2PREFIX = {
    'html_report': 'trytonspain',
    }


def kalenis_test_suite():
    from trytond.tests.test_tryton import modules_suite
    return modules_suite([name for name in os.listdir('.')
        if name.startswith('lims')])


def read(fname):
    return io.open(
        os.path.join(os.path.dirname(__file__), fname),
        'r', encoding='utf-8').read()


def get_require_version(name):
    if name in LINKS:
        return '%s @ %s' % (name, LINKS[name])
    if minor_version % 2:
        require = '%s >= %s.%s.dev0, < %s.%s'
    else:
        require = '%s >= %s.%s, < %s.%s'
    require %= (name, major_version, minor_version,
        major_version, minor_version + 1)
    return require


version = '5.4.0'
major_version, minor_version, _ = version.split('.', 2)
major_version = int(major_version)
minor_version = int(minor_version)

# TODO: check new openpyxl versions, v.3 seems to be buggy in PyPI
requires = ['appdirs', 'Click', 'formulas', 'openpyxl==2.6.4', 'pandas',
    'psycopg2', 'PyPDF2', 'pytz', 'unidecode', 'xlrd', 'xlutils']

LINKS = {
    'trytonspain_html_report': ('https://github.com/Kalenis/'
        'trytond-html_report/tarball/master#egg='
        'trytonspain_html_report-%s.%s' %
        (major_version, minor_version)),
    }

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
            module_name = '%s_%s' % (MODULE2PREFIX.get(dep, 'trytond'), dep)
            requires.append(get_require_version(module_name))

    package = 'trytond.modules.%s' % name
    package_dir[package] = os.path.join('.', name)
    packages.append(package)
    if os.path.isdir(os.path.join(name, 'tests')):
        packages.append(package + '.tests')
    module_entry_points.append('%s = %s' % (name, package))
    data = []
    for data_pattern in (info.get('xml', []) + ['tryton.cfg']):
        data.append(data_pattern)
    subpackage = package
    for data_pattern in (info.get('xml', []) + ['tryton.cfg', 'view/*.xml',
                'locale/*.po', 'locale/override/*.po', 'report/*.fodt',
                'report/*.fods', 'report/*.html', 'report/stylesheet/*.css',
                'report/translations/*/*/*.po', 'icons/*.svg', 'tests/*.rst']):
        data.append(data_pattern)
    if data:
        package_data[subpackage] = data
requires.append(get_require_version('trytond'))
requires.append(get_require_version('proteus'))

tests_require = [get_require_version('proteus')]
dependency_links = list(LINKS.values())

if __name__ == '__main__':
    setup(name='kalenis_lims',
        version=version,
        description='Kalenis LIMS',
        long_description=read('README.md'),
        author='Kalenis',
        author_email='info@kalenislims.com',
        url='http://www.kalenislims.com/',
        download_url='https://github.com/Kalenis/kalenislims',
        keywords='',
        package_dir=package_dir,
        packages=packages,
        package_data=package_data,
        py_modules=['kalenis_cli'],
        data_files=[
            ('/kalenis_lims', ['kalenis.conf.dist'])
            ],
        classifiers=[
            'Development Status :: 5 - Production/Stable',
            'Environment :: Plugins',
            'Framework :: Tryton',
            'Intended Audience :: Developers',
            'Intended Audience :: Manufacturing',
            'Intended Audience :: Science/Research',
            'Intended Audience :: Other Audience',
            'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
            'Natural Language :: English',
            'Natural Language :: Spanish',
            'Operating System :: OS Independent',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.5',
            'Programming Language :: Python :: 3.6',
            'Programming Language :: Python :: 3.7',
            'Programming Language :: Python :: Implementation :: CPython',
            'Programming Language :: Python :: Implementation :: PyPy',
            'Topic :: Office/Business',
            'Topic :: Scientific/Engineering',
            ],
        license='GPL-3',
        python_requires='>=3.5',
        install_requires=requires,
        dependency_links=dependency_links,
        zip_safe=False,
        entry_points="""
        [console_scripts]
        kalenis-cli = kalenis_cli:cli

        [trytond.modules]
        %s
        """ % '\n'.join(module_entry_points),
        test_suite='setup.kalenis_test_suite',
        test_loader='trytond.test_loader:Loader',
        tests_require=tests_require,
        )
