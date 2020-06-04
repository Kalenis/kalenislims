# This file is part of lims_diagnosis module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelSQL, ModelView, fields, DictSchemaMixin
from trytond.pool import PoolMeta

__all__ = ['DiagnosisState', 'DiagnosisTemplate', 'DiagnosisTemplateState',
    'ReportTemplate']


class DiagnosisTemplate(ModelSQL, ModelView):
    'Diagnosis Template'
    __name__ = 'lims.diagnosis.template'

    name = fields.Char('Name', required=True)
    content = fields.Text('Content', required=True)
    diagnosis_states = fields.Many2Many(
        'lims.diagnosis.template-diagnosis.state',
        'template', 'state', 'States')


class DiagnosisState(DictSchemaMixin, ModelSQL, ModelView):
    'Diagnosis State'
    __name__ = 'lims.diagnosis.state'
    _rec_name = 'name'

    @staticmethod
    def default_type_():
        return 'selection'


class DiagnosisTemplateState(ModelSQL):
    'Diagnosis Template - State'
    __name__ = 'lims.diagnosis.template-diagnosis.state'
    _table = 'lims_diagnosis_template_diagnosis_state'

    template = fields.Many2One('lims.diagnosis.template', 'Template',
        required=True, ondelete='CASCADE', select=True)
    state = fields.Many2One('lims.diagnosis.state', 'State',
        required=True, ondelete='CASCADE', select=True)


class ReportTemplate(metaclass=PoolMeta):
    __name__ = 'lims.result_report.template'

    diagnosis_template = fields.Many2One('lims.diagnosis.template',
        'Diagnosis Template')
