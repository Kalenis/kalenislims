# This file is part of lims_diagnosis module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import Pool, PoolMeta

__all__ = ['Notebook', 'NotebookLine']


class Notebook(metaclass=PoolMeta):
    __name__ = 'lims.notebook'

    diagnostician = fields.Function(fields.Many2One('lims.diagnostician',
        'Diagnostician'), 'get_sample_field')
    diagnosis_warning = fields.Function(fields.Boolean('Diagnosis Warning'),
        'get_diagnosis_warning')

    @classmethod
    def get_diagnosis_warning(cls, notebooks, name):
        NotebookLine = Pool().get('lims.notebook.line')
        result = {}
        for n in notebooks:
            lines = NotebookLine.search_count([
                ('notebook', '=', n.id),
                ('diagnosis_warning', '=', True),
                ])
            if lines > 0:
                result[n.id] = True
            else:
                result[n.id] = False
        return result


class NotebookLine(metaclass=PoolMeta):
    __name__ = 'lims.notebook.line'

    diagnosis_warning = fields.Boolean('Diagnosis Warning', select=True)
