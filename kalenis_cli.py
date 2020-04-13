import os
import pkg_resources
import subprocess
import appdirs
import click
from pathlib import Path
from shutil import copyfile
from proteus import config, Model

ERROR_COLOR = 'red'
OK_COLOR = 'green'
MODULES = {
    'qc': ['lims_quality_control'],
    'services': ['lims'],
    }


def get_config():
    """
    Read configuration file and return its contents
    """
    cfg_dir = appdirs.user_config_dir('kalenis')
    Path(cfg_dir).mkdir(exist_ok=True)
    cfg_file = os.path.join(cfg_dir, 'kalenis.conf')
    if not os.path.isfile(cfg_file):
        source = pkg_resources.resource_filename(
            __name__, '/kalenis_lims/kalenis.conf.dist')
        copyfile(source, cfg_file)
    return cfg_file


@click.group()
@click.version_option()
def cli():
    pass


@cli.command()
@click.option('-d', '--database', default='kalenislims', show_default=True)
@click.option('-l', '--language', required=True,
              type=click.Choice(['en', 'es'], case_sensitive=False))
@click.option('-i', '--industry', required=True,
              type=click.Choice(['qc', 'services'], case_sensitive=False))
def setup(database, language, industry):
    """
    This is the setup command for Kalenis LIMS
    """
    click.echo('Setup Kalenis for %s...' % industry)

    click.echo('Creating user config file...')
    config_file = get_config()

    click.echo('Creating the database...')
    process = subprocess.run(['createdb', database],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if process.returncode != 0:
        err = process.stdout.decode('utf-8')
        if len(err) == 0:
            err = process.stderr.decode('utf-8')
            click.echo(click.style(err.format(ERROR_COLOR), fg=ERROR_COLOR))
            return process.returncode

    click.echo('Initializing the database...')
    subprocess.run(['trytond-admin', '-d', database, '-c', config_file,
        '--all'])

    click.echo('Installing modules...')
    subprocess.run(['trytond-admin', '-d', database, '-c', config_file, '-u',
        ' '.join(MODULES[industry]), '--activate-dependencies'])

    if language == 'es':
        click.echo('Loading translations for spanish language...')
        config.set_trytond(database, config_file=config_file)
        User = Model.get('res.user')
        Lang = Model.get('ir.lang')

        lang, = Lang.find([('code', '=', language)])
        lang.translatable = True
        lang.save()

        subprocess.run(['trytond-admin', '-d', database, '-c', config_file,
            '--all'])

        user = User.find()[0]
        user.language = lang
        user.save()

    click.echo('Downloading front-end...')
    front_end_dir = '%s/kalenis_front_end' % os.environ.get('HOME', '')
    front_end_file = 'frontend_dist_5.4.tar.gz'
    Path(front_end_dir).mkdir(exist_ok=True)
    subprocess.run(['wget',
        'https://downloads.kalenislims.com/%s' % front_end_file, '-O',
        '%s/%s' % (front_end_dir, front_end_file)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(['tar', 'xzvf', '%s/%s' % (front_end_dir, front_end_file),
        '--directory', front_end_dir],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    click.echo(click.style(
        'Congratulations, the setup process has finished ok. Now you can '
        'execute "kalenis-cli run" to start Kalenis LIMS server'.format(
            OK_COLOR), fg=OK_COLOR))

@cli.command()
@click.option('-d', '--database', default='kalenislims', show_default=True)
def run(database):
    """
    Run Kalenis LIMS service
    """
    click.echo('Starting Kalenis LIMS server')
    click.echo('Kalenis LIMS running, you can go to http://localhost:8000')
    config_file = get_config()
    os.environ['TRYTOND_web__root'] = \
        '%s/kalenis_front_end/frontend_dist_5.4' % os.environ.get('HOME', '')
    subprocess.run(['trytond', '-d', database, '-c', config_file])
