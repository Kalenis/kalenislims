# This file is part of lims_project_implementation module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import configuration
from . import project


def register():
    Pool.register(
        configuration.Configuration,
        project.Project,
        project.ProjectSolventAndReagent,
        project.Entry,
        project.Fraction,
        module='lims_project_implementation', type_='model')
    Pool.register(
        project.ImplementationsReport,
        module='lims_project_implementation', type_='report')
