# This file is part of lims_diagnosis module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta

__all__ = ['NotebookLine']


class NotebookLine(metaclass=PoolMeta):
    __name__ = 'lims.notebook.line'

    diagnosis_warning = fields.Boolean('Diagnosis Warning')
