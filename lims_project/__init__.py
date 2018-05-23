# This file is part of lims_project module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import project


def register():
    Pool.register(
        project.Project,
        project.Entry,
        project.Sample,
        project.CreateSampleStart,
        module='lims_project', type_='model')
    Pool.register(
        project.CreateSample,
        module='lims_project', type_='wizard')
