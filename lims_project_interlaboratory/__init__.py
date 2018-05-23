# This file is part of lims_project_interlaboratory module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import project


def register():
    Pool.register(
        project.Project,
        project.Entry,
        module='lims_project_interlaboratory', type_='model')
