# This file is part of lims_diagnosis module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelView, fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval

__all__ = ['ResultsReportVersionDetail', 'ResultsReportVersionDetailSample']


class ResultsReportVersionDetail(metaclass=PoolMeta):
    __name__ = 'lims.results_report.version.detail'

    diagnostician = fields.Many2One('lims.diagnostician', 'Diagnostician',
        states={'readonly': Eval('state') != 'draft'}, depends=['state'])
    diagnosis_template = fields.Many2One('lims.diagnosis.template',
        'Diagnosis Template', depends=['state'],
        states={'readonly': Eval('state') != 'draft'})

    @classmethod
    def __setup__(cls):
        super(ResultsReportVersionDetail, cls).__setup__()
        diagnosed_state = ('diagnosed', 'Diagnosed')
        if diagnosed_state not in cls.state.selection:
            cls.state.selection.append(diagnosed_state)
        cls._buttons.update({
            'diagnose': {
                'invisible': Eval('state') != 'draft',
                'depends': ['state'],
                },
            })
        cls._buttons['revise']['invisible'] = Eval('state') != 'diagnosed'

    @classmethod
    @ModelView.button
    def diagnose(cls, details):
        cls.write(details, {'state': 'diagnosed'})

    @fields.depends('template', '_parent_template.diagnosis_template',
        methods=['on_change_diagnosis_template'])
    def on_change_template(self):
        if self.template and self.template.diagnosis_template:
            self.diagnosis_template = self.template.diagnosis_template
            self.on_change_diagnosis_template()

    @fields.depends('diagnosis_template', '_parent_diagnosis_template.content',
        'samples')
    def on_change_diagnosis_template(self):
        if self.diagnosis_template:
            content = self.diagnosis_template.content
            for sample in self.samples:
                sample.diagnosis = content


class ResultsReportVersionDetailSample(metaclass=PoolMeta):
    __name__ = 'lims.results_report.version.detail.sample'

    diagnosis = fields.Text('Diagnosis')
    diagnosis_states = fields.Dict('lims.diagnosis.state', 'States',
        domain=[('id', 'in', Eval('diagnosis_states_domain'))],
        depends=['diagnosis_states_domain'])
    diagnosis_states_domain = fields.Function(fields.Many2Many(
        'lims.diagnosis.state', None, None, 'States domain'),
        'on_change_with_diagnosis_states_domain')

    @fields.depends('version_detail',
        '_parent_version_detail.diagnosis_template')
    def on_change_with_diagnosis_states_domain(self, name=None):
        if (self.version_detail and
                self.version_detail.diagnosis_template and
                self.version_detail.diagnosis_template.diagnosis_states):
            return [s.id for s in
                self.version_detail.diagnosis_template.diagnosis_states]
        return []
