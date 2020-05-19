# This file is part of lims_diagnosis module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateTransition, StateView, Button
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction

__all__ = ['ResultsReportVersionDetail', 'ResultsReportVersionDetailSample',
    'ResultReport', 'ChangeSampleDiagnosticianStart',
    'ChangeSampleDiagnostician']


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


class ResultReport(metaclass=PoolMeta):
    __name__ = 'lims.result_report'

    @classmethod
    def get_results_report_template(cls, action, detail_id):
        content = super(ResultReport, cls).get_results_report_template(
            action, detail_id)
        signature = 'show_diagnosis_content'
        diagnosis_content = (
            '{%% macro %s(sample) %%}\n%s\n{%% endmacro %%}' % (
                signature, '{{ sample.diagnosis }}'))
        return '%s\n\n%s' % (diagnosis_content, content)

    @classmethod
    def get_context(cls, records, data):
        ResultsSample = Pool().get('lims.results_report.version.detail.sample')

        report_context = super(ResultReport, cls).get_context(records, data)

        if 'id' in data:
            report_id = data['id']
        else:
            report_id = records[0].id
        for fraction in report_context['fractions']:
            detail_sample = ResultsSample.search([
                ('version_detail', '=', report_id),
                ('notebook.fraction.sample.number', '=', fraction['fraction']),
                ], limit=1)
            if not detail_sample:
                fraction['diagnosis'] = ''
                continue
            fraction['diagnosis'] = detail_sample[0].diagnosis
        return report_context


class ChangeSampleDiagnosticianStart(ModelView):
    'Change Sample Diagnostician'
    __name__ = 'lims.notebook.change_diagnostician.start'

    diagnostician = fields.Many2One('lims.diagnostician', 'Diagnostician',
        required=True)


class ChangeSampleDiagnostician(Wizard):
    'Change Sample Diagnostician'
    __name__ = 'lims.notebook.change_diagnostician'

    start = StateView('lims.notebook.change_diagnostician.start',
        'lims_diagnosis.notebook_change_diagnostician_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Change', 'change', 'tryton-ok', default=True),
            ])
    change = StateTransition()

    def transition_change(self):
        pool = Pool()
        Notebook = pool.get('lims.notebook')
        Sample = pool.get('lims.sample')

        samples_ids = set()
        for notebook in Notebook.browse(Transaction().context['active_ids']):
            samples_ids.add(notebook.fraction.sample.id)
        samples = Sample.browse(list(samples_ids))
        Sample.write(samples, {'diagnostician': self.start.diagnostician.id})
        return 'end'
