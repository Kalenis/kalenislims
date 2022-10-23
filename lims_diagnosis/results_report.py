# This file is part of lims_diagnosis module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import Workflow, ModelView, ModelSQL, fields
from trytond.wizard import Wizard, StateTransition, StateView, StateAction, \
    Button
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, Not, Bool
from trytond.transaction import Transaction
from trytond.exceptions import UserError, UserWarning
from trytond.i18n import gettext


class ResultsReportVersionDetail(metaclass=PoolMeta):
    __name__ = 'lims.results_report.version.detail'

    diagnostician = fields.Many2One('lims.diagnostician', 'Diagnostician',
        states={'readonly': Eval('state') != 'draft'}, depends=['state'])
    diagnosis_template = fields.Many2One('lims.diagnosis.template',
        'Diagnosis Template', domain=['OR', ('active', '=', True),
            ('id', '=', Eval('diagnosis_template'))],
        states={'readonly': Eval('state') != 'draft'},
        depends=['state'])

    @classmethod
    def __setup__(cls):
        super().__setup__()
        diagnosed_state = ('diagnosed', 'Diagnosed')
        if diagnosed_state not in cls.state.selection:
            cls.state.selection.append(diagnosed_state)
        cls._transitions = set((
            ('draft', 'waiting'),
            ('waiting', 'draft'),
            ('draft', 'diagnosed'),
            ('diagnosed', 'draft'),
            ('diagnosed', 'revised'),
            ('revised', 'draft'),
            ('revised', 'released'),
            ('released', 'annulled'),
            ))
        cls._buttons.update({
            'diagnose': {
                'invisible': Eval('state') != 'draft',
                'depends': ['state'],
                },
            })
        cls._buttons['revise']['invisible'] = Eval('state') != 'diagnosed'

    @classmethod
    @ModelView.button
    @Workflow.transition('diagnosed')
    def diagnose(cls, details):
        cls.check_diagnosis_states(details)
        cls.check_diagnosis_length(details)

    @classmethod
    def check_diagnosis_states(cls, details):
        for detail in details:
            for sample in detail.samples:
                if not sample.diagnosis_states:
                    continue
                for state in sample.diagnosis_states.values():
                    if state == '*':
                        raise UserError(gettext(
                            'lims_diagnosis.msg_invalid_diagnosis_state'))

    @classmethod
    def check_diagnosis_length(cls, details):
        Warning = Pool().get('res.user.warning')
        for detail in details:
            if not detail.template or not detail.template.diagnosis_length:
                continue
            diagnosis_length = detail.template.diagnosis_length
            for sample in detail.samples:
                if not sample.diagnosis:
                    continue
                if len(sample.diagnosis) > diagnosis_length:
                    key = 'lims_diagnosis_length@%s' % sample.id
                    if Warning.check(key):
                        raise UserWarning(key, gettext(
                            'lims_diagnosis.msg_invalid_diagnosis_length',
                            length=str(len(sample.diagnosis)),
                            allowed=str(diagnosis_length)))

    @fields.depends('template', '_parent_template.diagnosis_template',
        methods=['on_change_diagnosis_template'])
    def on_change_template(self):
        super().on_change_template()
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
                states = {}
                for state in self.diagnosis_template.diagnosis_states:
                    states[state.name] = sample.get_default_diagnosis_state(
                            sample, state.name)
                sample.diagnosis_states = states
        else:
            for sample in self.samples:
                states = {}
                sample.diagnosis_states = states

    @classmethod
    def _get_fields_from_samples(cls, samples, generate_report_form=None):
        pool = Pool()
        Notebook = pool.get('lims.notebook')
        ReportTemplate = pool.get('lims.report.template')

        detail_default = super()._get_fields_from_samples(samples,
            generate_report_form)

        diagnostician_id = None
        diagnosis_template = None
        for sample in samples:
            nb = Notebook(sample['notebook'])
            if not diagnostician_id:
                diagnostician_id = cls._get_diagnostician_from_sample(nb)
            if not diagnosis_template:
                diagnosis_template = (
                    cls._get_diagnosis_template_from_sample(nb))

        if diagnosis_template:
            detail_default['diagnosis_template'] = diagnosis_template.id
        elif 'template' in detail_default and detail_default['template']:
            result_template = ReportTemplate(detail_default['template'])
            if result_template.diagnosis_template:
                detail_default['diagnosis_template'] = (
                    result_template.diagnosis_template.id)

        if diagnostician_id:
            detail_default['diagnostician'] = diagnostician_id

        return detail_default

    @classmethod
    def _get_diagnostician_from_sample(cls, notebook):
        pool = Pool()
        Diagnostician = pool.get('lims.diagnostician')

        if notebook.fraction.sample.diagnostician:
            diagnostician_id = notebook.fraction.sample.diagnostician.id
        else:
            diagnostician_id = Diagnostician.get_diagnostician()
        return diagnostician_id

    @classmethod
    def _get_diagnosis_template_from_sample(cls, notebook):
        pool = Pool()
        Service = pool.get('lims.service')

        diagnosis_template = notebook.fraction.sample.diagnosis_template
        if not diagnosis_template:
            ok = True
            services = Service.search([
                ('fraction', '=', notebook.fraction),
                ('analysis.type', '=', 'group'),
                ('annulled', '=', False),
                ])
            for service in services:
                if service.analysis.diagnosis_template:
                    if not diagnosis_template:
                        diagnosis_template = (
                            service.analysis.diagnosis_template)
                    elif (diagnosis_template !=
                            service.analysis.diagnosis_template):
                        ok = False
                elif diagnosis_template:
                    ok = False
            if not ok:
                diagnosis_template = None
        return diagnosis_template

    @classmethod
    def _get_fields_not_overwrite(cls):
        fields = super()._get_fields_not_overwrite()
        fields.extend(['diagnostician', 'diagnosis_template'])
        return fields

    @classmethod
    def _get_fields_from_detail(cls, detail):
        detail_default = super()._get_fields_from_detail(detail)
        if detail.diagnostician:
            detail_default['diagnostician'] = detail.diagnostician.id
        if detail.diagnosis_template:
            detail_default['diagnosis_template'] = detail.diagnosis_template.id
        return detail_default


class ResultsReportVersionDetailSample(metaclass=PoolMeta):
    __name__ = 'lims.results_report.version.detail.sample'

    diagnosis = fields.Text('Diagnosis')
    diagnosis_plain = fields.Function(fields.Text('Diagnosis'),
        'get_diagnosis_plain', setter='set_diagnosis_plain')
    diagnosis_states = fields.Dict('lims.diagnosis.state', 'States',
        domain=[('id', 'in', Eval('diagnosis_states_domain'))],
        depends=['diagnosis_states_domain'])
    diagnosis_states_string = diagnosis_states.translated('diagnosis_states')
    diagnosis_states_domain = fields.Function(fields.Many2Many(
        'lims.diagnosis.state', None, None, 'States domain'),
        'on_change_with_diagnosis_states_domain')
    diagnosis_warning = fields.Function(fields.Boolean('Diagnosis Warning'),
        'get_notebook_field')
    template_type = fields.Function(fields.Selection([
        (None, ''),
        ('base', 'HTML'),
        ('header', 'HTML - Header'),
        ('footer', 'HTML - Footer'),
        ], 'Report Template Type'), 'get_template_type')

    @classmethod
    def view_attributes(cls):
        return super().view_attributes() + [
            ('//page[@id="diagnosis"]', 'states', {
                    'invisible': Not(Bool(Eval('template_type'))),
                    }),
            ('//page[@id="diagnosis_plain"]', 'states', {
                    'invisible': Eval('template_type') == 'base',
                    }),
            ]

    def get_diagnosis_plain(self, name):
        return self.diagnosis

    @classmethod
    def set_diagnosis_plain(cls, records, name, value):
        cls.write(records, {'diagnosis': value})

    def get_template_type(self, name):
        return (self.version_detail.template and
            self.version_detail.template.type or None)

    @classmethod
    def create(cls, vlist):
        samples = super().create(vlist)
        for sample in samples:
            diagnosis_template = None
            report = sample.version_detail
            if report.diagnosis_template:
                diagnosis_template = report.diagnosis_template
            elif report.template and report.template.diagnosis_template:
                diagnosis_template = report.template.diagnosis_template
            if not diagnosis_template:
                continue
            save = False
            if not sample.diagnosis:
                content = diagnosis_template.content
                sample.diagnosis = content
                save = True
            if not sample.diagnosis_states:
                states = {}
                for state in diagnosis_template.diagnosis_states:
                    states[state.name] = cls.get_default_diagnosis_state(
                        sample, state.name)
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
    def _get_fields_from_sample(cls, sample, only_accepted=True):
        sample_default = super()._get_fields_from_sample(sample,
            only_accepted)
        sample_default['diagnosis'] = sample.diagnosis
        sample_default['diagnosis_states'] = sample.diagnosis_states
        return sample_default

    @classmethod
    def get_default_diagnosis_state(cls, sample, state_name):
        return '*'


class ResultsReportVersionDetailLine(metaclass=PoolMeta):
    __name__ = 'lims.results_report.version.detail.line'

    diagnosis_warning = fields.Function(fields.Boolean('Diagnosis Warning'),
        'get_nline_field')


class ChangeSampleDiagnosticianStart(ModelView):
    'Change Sample Diagnostician'
    __name__ = 'lims.notebook.change_diagnostician.start'

    diagnostician = fields.Many2One('lims.diagnostician', 'Diagnostician')


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
        diagnostician = (self.start.diagnostician and
            self.start.diagnostician.id or None)
        Sample.write(samples, {'diagnostician': diagnostician})
        return 'end'


class ResultsReportRelease(metaclass=PoolMeta):
    __name__ = 'lims.results_report_release'

    def _process_transitions(self, detail):
        ResultsDetail = Pool().get('lims.results_report.version.detail')
        if detail.state == 'draft':
            ResultsDetail.diagnose([detail])
        elif detail.state == 'diagnosed':
            ResultsDetail.revise([detail])
        super()._process_transitions(detail)


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
                    result[name][l.id] = (
                        l.notebook_line.get_formated_result())
            elif name == 'converted_result':
                for l in lines:
                    result[name][l.id] = (
                        l.notebook_line.formated_converted_result)
        return result

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
        return notebook_line[0].get_formated_result()


class Cron(metaclass=PoolMeta):
    __name__ = 'ir.cron'

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.method.selection.extend([
            ('lims.samples_comparator|clean_buffer',
                'Delete Samples comparison records'),
            ])


class ResultReport(metaclass=PoolMeta):
    __name__ = 'lims.result_report'

    @classmethod
    def get_context(cls, records, header, data):
        report_context = super().get_context(records, header, data)
        report_context['state_image'] = cls.get_state_image
        return report_context

    @classmethod
    def get_state_image(cls, sample, state):
        DiagnosisState = Pool().get('lims.diagnosis.state')

        diagnosis_states = DiagnosisState.search([('name', '=', state)])
        if not diagnosis_states:
            return None
        diagnosis_state, = diagnosis_states
        for image in diagnosis_state.images:
            if image.name == sample.diagnosis_states.get(state, ''):
                return image.image

        return None
