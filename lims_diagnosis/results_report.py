# This file is part of lims_diagnosis module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateTransition, StateView, Button
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction

__all__ = ['ResultsReportVersionDetail', 'ResultsReportVersionDetailSample',
    'ResultsReportVersionDetailLine', 'ChangeSampleDiagnosticianStart',
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
            states = {}
            for state in self.diagnosis_template.diagnosis_states:
                states[state.name] = '*'
            for sample in self.samples:
                if not sample.diagnosis:
                    sample.diagnosis = content
                if not sample.diagnosis_states:
                    sample.diagnosis_states = states

    @classmethod
    def _get_fields_from_samples(cls, samples):
        Notebook = Pool().get('lims.notebook')
        detail_default = super(ResultsReportVersionDetail,
            cls)._get_fields_from_samples(samples)
        for sample in samples:
            notebook = Notebook(sample['notebook'])
            diagnostician = notebook.fraction.sample.diagnostician
            if diagnostician:
                detail_default['diagnostician'] = diagnostician.id
            result_template = notebook.fraction.sample.result_template
            if result_template and result_template.diagnosis_template:
                detail_default['diagnosis_template'] = (
                    result_template.diagnosis_template.id)
        return detail_default

    @classmethod
    def _get_fields_from_detail(cls, detail):
        detail_default = super(ResultsReportVersionDetail,
            cls)._get_fields_from_detail(detail)
        if detail.diagnostician:
            detail_default['diagnostician'] = detail.diagnostician.id
        if detail.diagnosis_template:
            detail_default['diagnosis_template'] = detail.diagnosis_template.id
        return detail_default


class ResultsReportVersionDetailSample(metaclass=PoolMeta):
    __name__ = 'lims.results_report.version.detail.sample'

    diagnosis = fields.Text('Diagnosis')
    diagnosis_states = fields.Dict('lims.diagnosis.state', 'States',
        domain=[('id', 'in', Eval('diagnosis_states_domain'))],
        depends=['diagnosis_states_domain'])
    diagnosis_states_domain = fields.Function(fields.Many2Many(
        'lims.diagnosis.state', None, None, 'States domain'),
        'on_change_with_diagnosis_states_domain')
    diagnosis_warning = fields.Function(fields.Boolean('Diagnosis Warning'),
        'get_notebook_field')

    @classmethod
    def create(cls, vlist):
        samples = super(ResultsReportVersionDetailSample, cls).create(vlist)
        for sample in samples:
            template = sample.version_detail.template
            if not template or not template.diagnosis_template:
                continue
            save = False
            if not sample.diagnosis:
                content = template.diagnosis_template.content
                sample.diagnosis = content
                save = True
            if not sample.diagnosis_states:
                states = {}
                for state in template.diagnosis_template.diagnosis_states:
                    states[state.name] = '*'
                sample.diagnosis_states = states
                save = True
            if save:
                sample.save()
        return samples

    @fields.depends('version_detail',
        '_parent_version_detail.diagnosis_template')
    def on_change_with_diagnosis_states_domain(self, name=None):
        if (self.version_detail and
                self.version_detail.diagnosis_template and
                self.version_detail.diagnosis_template.diagnosis_states):
            return [s.id for s in
                self.version_detail.diagnosis_template.diagnosis_states]
        return []

    @classmethod
    def _get_fields_from_sample(cls, sample):
        sample_default = super(ResultsReportVersionDetailSample,
            cls)._get_fields_from_sample(sample)
        sample_default['diagnosis'] = sample.diagnosis
        sample_default['diagnosis_states'] = sample.diagnosis_states
        return sample_default


class ResultsReportVersionDetailLine(metaclass=PoolMeta):
    __name__ = 'lims.results_report.version.detail.line'

    diagnosis_warning = fields.Function(fields.Boolean('Diagnosis Warning'),
        'get_nline_field')


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
