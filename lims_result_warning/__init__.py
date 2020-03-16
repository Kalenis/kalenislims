# This file is part of lims_result_warning module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import notebook
from . import task


def register():
    Pool.register(
        notebook.NotebookLine,
        task.AdministrativeTaskTemplate,
        task.AdministrativeTask,
        module='lims_result_warning', type_='model')
