# This file is part of lims_project_tas module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import project
from . import configuration
from . import invoice


def register():
    Pool.register(
        project.TasType,
        project.Project,
        project.Entry,
        configuration.LabWorkYear,
        configuration.LabWorkYearSequence,
        module='lims_project_tas', type_='model')
    Pool.register(
        invoice.Invoice,
        module='lims_project_tas', type_='model',
        depends=['lims_account_invoice'])
