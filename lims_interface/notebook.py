# This file is part of lims_interface module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta


class NotebookLine(metaclass=PoolMeta):
    __name__ = 'lims.notebook.line'

    compilation = fields.Many2One('lims.interface.compilation', 'Compilation',
        readonly=True)
