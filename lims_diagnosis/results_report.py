# This file is part of lims_diagnosis module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelView, ModelSQL, fields
from trytond.wizard import Wizard, StateTransition, StateView, StateAction, \
    Button
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction
from trytond.i18n import gettext

__all__ = ['ResultsReportVersionDetail', 'ResultsReportVersionDetailSample',
    'ResultsReportVersionDetailLine', 'ChangeSampleDiagnosticianStart',
    'ChangeSampleDiagnostician', 'OpenSamplesComparatorAsk',
    'OpenSamplesComparator', 'SamplesComparator', 'SamplesComparatorLine',
    'Cron']


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
    diagnosis_states_string = diagnosis_states.translated('diagnosis_states')
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


class OpenSamplesComparatorAsk(ModelView):
    'Samples Comparator'
    __name__ = 'lims.samples_comparator.ask'

    notebook = fields.Many2One('lims.notebook', 'Sample', required=True)


class OpenSamplesComparator(Wizard):
    'Samples Comparator'
    __name__ = 'lims.samples_comparator.open'

    start = StateTransition()
    ask = StateView('lims.samples_comparator.ask',
        'lims_diagnosis.samples_comparator_ask_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Open', 'open_', 'tryton-ok', default=True),
            ])
    open_ = StateAction('lims_diagnosis.act_samples_comparator')

    def transition_start(self):
        ResultsSample = Pool().get('lims.results_report.version.detail.sample')
        active_model = Transaction().context['active_model']
        if active_model == 'lims.results_report.version.detail.sample':
            sample = ResultsSample(Transaction().context['active_id'])
            self.ask.notebook = sample.notebook.id
            return 'open_'
        return 'ask'

    def do_open_(self, action):
        SamplesComparator = Pool().get('lims.samples_comparator')
        notebook = self.ask.notebook
        lines = [{'notebook_line': l.id} for l in notebook.lines]
        comparison = SamplesComparator.create([{
            'notebook': notebook.id,
            'lines': [('create', lines)],
            }])[0]
        action['res_id'] = [comparison.id]
        return action, {}

    def transition_open_(self):
        return 'end'


class SamplesComparator(ModelSQL, ModelView):
    'Samples Comparator'
    __name__ = 'lims.samples_comparator'

    lines = fields.One2Many('lims.samples_comparator.line', 'sample',
        'Lines', readonly=True)
    notebook = fields.Many2One('lims.notebook', 'Sample', required=True,
        readonly=True)
    notebook1 = fields.Many2One('lims.notebook', 'Sample 1')
    notebook2 = fields.Many2One('lims.notebook', 'Sample 2')
    notebook3 = fields.Many2One('lims.notebook', 'Sample 3')
    notebook_diagnosis = fields.Function(fields.Text(
        'Diagnosis'), 'on_change_with_notebook_diagnosis')
    notebook1_diagnosis = fields.Function(fields.Text(
        'Diagnosis 1'), 'on_change_with_notebook1_diagnosis')
    notebook2_diagnosis = fields.Function(fields.Text(
        'Diagnosis 2'), 'on_change_with_notebook2_diagnosis')
    notebook3_diagnosis = fields.Function(fields.Text(
        'Diagnosis 3'), 'on_change_with_notebook3_diagnosis')

    @fields.depends('notebook')
    def on_change_with_notebook_diagnosis(self, name=None):
        if self.notebook:
            return self._get_notebook_diagnosis(self.notebook)
        return None

    @fields.depends('notebook1')
    def on_change_with_notebook1_diagnosis(self, name=None):
        if self.notebook1:
            return self._get_notebook_diagnosis(self.notebook1)
        return None

    @fields.depends('notebook2')
    def on_change_with_notebook2_diagnosis(self, name=None):
        if self.notebook2:
            return self._get_notebook_diagnosis(self.notebook2)
        return None

    @fields.depends('notebook3')
    def on_change_with_notebook3_diagnosis(self, name=None):
        if self.notebook3:
            return self._get_notebook_diagnosis(self.notebook3)
        return None

    def _get_notebook_diagnosis(self, notebook):
        ResultsSample = Pool().get('lims.results_report.version.detail.sample')
        samples = ResultsSample.search([
            ('notebook', '=', notebook),
            ])
        if not samples:
            return None
        return samples[0].diagnosis

    @classmethod
    def clean_buffer(cls):
        comparisons = cls.search([])
        cls.delete(comparisons)


class SamplesComparatorLine(ModelSQL, ModelView):
    'Samples Comparator Line'
    __name__ = 'lims.samples_comparator.line'

    sample = fields.Many2One('lims.samples_comparator', 'Sample',
        required=True, ondelete='CASCADE', select=True)
    notebook_line = fields.Many2One('lims.notebook.line', 'Notebook Line',
        required=True, readonly=True, select=True)
    analysis = fields.Function(fields.Many2One('lims.analysis', 'Analysis'),
        'get_nline_field')
    repetition = fields.Function(fields.Integer('Repetition'),
        'get_nline_field')
    result = fields.Function(fields.Char('Result'), 'get_line_result')
    initial_unit = fields.Function(fields.Many2One('product.uom',
        'Initial unit'), 'get_nline_field')
    converted_result = fields.Function(fields.Char('Converted result'),
        'get_line_result')
    final_unit = fields.Function(fields.Many2One('product.uom',
        'Final unit'), 'get_nline_field')
    notebook1_result = fields.Function(fields.Char('Sample 1'),
        'get_comparison_result')
    notebook2_result = fields.Function(fields.Char('Sample 2'),
        'get_comparison_result')
    notebook3_result = fields.Function(fields.Char('Sample 3'),
        'get_comparison_result')

    @classmethod
    def get_nline_field(cls, lines, names):
        result = {}
        for name in names:
            result[name] = {}
            if cls._fields[name]._type == 'many2one':
                for l in lines:
                    field = getattr(l.notebook_line, name, None)
                    result[name][l.id] = field.id if field else None
            else:
                for l in lines:
                    result[name][l.id] = getattr(l.notebook_line, name, None)
        return result

    @classmethod
    def get_line_result(cls, lines, names):
        result = {}
        for name in names:
            result[name] = {}
            if name == 'result':
                for l in lines:
                    result[name][l.id] = cls._get_result(
                        l.notebook_line)
            elif name == 'converted_result':
                for l in lines:
                    result[name][l.id] = cls._get_converted_result(
                        l.notebook_line)
        return result

    @classmethod
    def _get_result(cls, notebook_line):
        literal_result = notebook_line.literal_result
        result = notebook_line.result
        decimals = notebook_line.decimals
        result_modifier = notebook_line.result_modifier

        res = ''
        if literal_result:
            res = literal_result
        else:
            if result:
                res = round(float(result), decimals)
                if decimals == 0:
                    res = int(res)
                res = str(res)
            else:
                res = ''

            if result_modifier == 'eq':
                res = res
            elif result_modifier == 'low':
                res = gettext('lims.msg_quantification_limit', loq=res)
            elif result_modifier == 'd':
                res = gettext('lims.msg_d')
            elif result_modifier == 'nd':
                res = gettext('lims.msg_nd')
            elif result_modifier == 'ni':
                res = ''
            elif result_modifier == 'pos':
                res = gettext('lims.msg_pos')
            elif result_modifier == 'neg':
                res = gettext('lims.msg_neg')
            elif result_modifier == 'pre':
                res = gettext('lims.msg_pre')
            elif result_modifier == 'abs':
                res = gettext('lims.msg_abs')
            else:
                res = result_modifier
        return res

    @classmethod
    def _get_converted_result(cls, notebook_line):
        result = notebook_line.converted_result
        decimals = notebook_line.decimals
        result_modifier = notebook_line.converted_result_modifier

        res = ''
        if not notebook_line.literal_result:
            if result:
                res = round(float(result), decimals)
                if decimals == 0:
                    res = int(res)
                res = str(res)
            else:
                res = ''

            if result_modifier == 'eq':
                res = res
            elif result_modifier == 'low':
                res = gettext('lims.msg_quantification_limit', loq=res)
            elif result_modifier == 'd':
                res = gettext('lims.msg_d')
            elif result_modifier == 'nd':
                res = gettext('lims.msg_nd')
            elif result_modifier == 'ni':
                res = ''
            elif result_modifier == 'pos':
                res = gettext('lims.msg_pos')
            elif result_modifier == 'neg':
                res = gettext('lims.msg_neg')
            elif result_modifier == 'pre':
                res = gettext('lims.msg_pre')
            elif result_modifier == 'abs':
                res = gettext('lims.msg_abs')
            else:
                res = result_modifier
        return res

    @classmethod
    def get_comparison_result(cls, lines, names):
        result = {}
        for name in names:
            result[name] = {}
            if name == 'notebook1_result':
                for l in lines:
                    result[name][l.id] = cls._get_comparison_result(
                        l.sample.notebook1, l)
            elif name == 'notebook2_result':
                for l in lines:
                    result[name][l.id] = cls._get_comparison_result(
                        l.sample.notebook2, l)
            elif name == 'notebook3_result':
                for l in lines:
                    result[name][l.id] = cls._get_comparison_result(
                        l.sample.notebook3, l)
        return result

    @classmethod
    def _get_comparison_result(cls, notebook, line):
        NotebookLine = Pool().get('lims.notebook.line')
        if not notebook:
            return None
        notebook_line = NotebookLine.search([
            ('notebook', '=', notebook),
            ('analysis', '=', line.notebook_line.analysis),
            ('accepted', '=', True),
            ])
        if not notebook_line:
            return None
        return cls._get_result(notebook_line[0])


class Cron(metaclass=PoolMeta):
    __name__ = 'ir.cron'

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.method.selection.extend([
            ('lims.samples_comparator|clean_buffer',
                'Delete Samples comparison records'),
            ])
