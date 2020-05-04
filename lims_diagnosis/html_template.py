# This file is part of lims_diagnosis module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelSQL, ModelView, fields
from trytond.pool import PoolMeta

__all__ = ['DiagnosisTemplate', 'ReportTemplate']


class DiagnosisTemplate(ModelSQL, ModelView):
    'Diagnosis Template'
    __name__ = 'lims.diagnosis.template'

    name = fields.Char('Name', required=True)
    content = fields.Text('Content', required=True)


class ReportTemplate(metaclass=PoolMeta):
    __name__ = 'lims.result_report.template'

    diagnosis_template = fields.Many2One('lims.diagnosis.template',
        'Diagnosis Template')
