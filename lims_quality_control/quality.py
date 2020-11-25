# This file is part of lims_quality_control module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import datetime
from io import BytesIO
from PyPDF2 import PdfFileMerger

from trytond.model import Workflow, ModelView, ModelSQL, DeactivableMixin, \
    fields
from trytond.wizard import Wizard, StateView, StateTransition, StateAction, \
    StateReport, Button
from trytond.pyson import PYSONEncoder, Bool, Equal, Eval, Not
from trytond.transaction import Transaction
from trytond.pool import Pool
from trytond.report import Report
from trytond.tools import grouped_slice, reduce_ids
from trytond.exceptions import UserError
from trytond.i18n import gettext
from trytond.modules.company import CompanyReport


class QualitativeValue(DeactivableMixin, ModelSQL, ModelView):
    'Quality Value'
    __name__ = 'lims.quality.qualitative.value'

    name = fields.Char('Name', required=True, translate=True,
        select=True)
    analysis = fields.Many2One('lims.analysis', 'Analysis')
    typification = fields.Many2One('lims.typification', 'Typification')


class Template(Workflow, ModelSQL, ModelView):
    'Quality Template'
    __name__ = 'lims.quality.template'
    _history = True

    _states = {'readonly': Eval('state') != 'draft'}
    _depends = ['state']

    name = fields.Char('Name', required=True, translate=True,
        select=True, states=_states, depends=_depends)
    product = fields.Many2One('product.product', 'Product', required=True,
        select=True, states=_states, depends=_depends)
    company = fields.Many2One('company.company', 'Company', required=True,
        select=True, states=_states, depends=_depends)
    comments = fields.Text('Comments', states=_states, depends=_depends)
    lines = fields.One2Many('lims.typification', 'quality_template', 'Lines',
        domain=[
            ('quality', '=', True),
            ],
        context={'quality': True},
        states=_states, depends=_depends + ['product'])
    revision = fields.Integer(
        "Revision", required=True, readonly=True)
    countersample_required = fields.Boolean('Countersample Required',
        states=_states, depends=_depends)
    results_report_required = fields.Boolean('Results Report Required',
        states=_states, depends=_depends)
    range_validate = fields.Boolean('Ranges Validate',
        states=_states, depends=_depends)
    range_type = fields.Many2One('lims.range.type', 'Range Type',
        states={
            'readonly': Eval('state') != 'draft',
            'invisible': Not(Bool(Eval('range_validate'))),
            'required': Bool(Eval('range_validate')),
        }, depends=_depends + ['range_validate'])
    start_date = fields.Date('Start Date', states=_states, depends=_depends)
    end_date = fields.Date('End Date', states=_states, depends=_depends)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('not_active', 'Not Active'),
        ], 'State', readonly=True, required=True)

    del _states, _depends

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._transitions |= set((
            ('draft', 'active'),
            ('active', 'draft'),
            ('active', 'not_active'),
            ('not_active', 'active'),
            ))
        cls._buttons.update({
            'active': {
                'invisible': (Eval('state') == 'active'),
                'icon': 'tryton-forward',
                },
            'not_active': {
                'invisible': (Eval('state') != 'active'),
                'icon': 'tryton-forward',
                },
            'draft': {
                'invisible': (Eval('state') != 'active'),
                'icon': 'tryton-clear',
                },
            })

    @classmethod
    def default_revision(cls):
        return 1

    @classmethod
    def default_start_date(cls):
        Date = Pool().get('ir.date')
        return Date.today()

    @staticmethod
    def default_state():
        return 'draft'

    @staticmethod
    def default_company():
        return Transaction().context.get('company')

    @classmethod
    def copy(cls, templates, default=None):
        if default is None:
            default = {}
        if 'lines' not in default:
            default['lines'] = None
            default['revision'] = 1
        return super().copy(templates, default)

    @classmethod
    def check_delete(cls, templates):
        for t in templates:
            if t.state != 'draft' or t.revision > 1:
                raise UserError(gettext(
                    'lims_quality_control.msg_delete_template',
                    template=t.rec_name))

    @classmethod
    def delete(cls, templates):
        cls.check_delete(templates)
        super().delete(templates)

    @classmethod
    @ModelView.button
    @Workflow.transition('draft')
    def draft(cls, templates):
        cursor = Transaction().connection.cursor()
        table = cls.__table__()

        # Use SQL and before super to avoid two history entries
        for sub_sales in grouped_slice(templates):
            cursor.execute(*table.update(
                    [table.revision],
                    [table.revision + 1],
                    where=reduce_ids(table.id, sub_sales)))

    @classmethod
    @ModelView.button
    @Workflow.transition('active')
    def active(cls, templates):
        for template in templates:
            if not template.lines:
                raise UserError(gettext(
                    'lims_quality_control.msg_missing_template_lines'))

    @classmethod
    @ModelView.button
    @Workflow.transition('not_active')
    def not_active(cls, templates):
        pass


class QualityTest(Workflow, ModelSQL, ModelView):
    'Quality Test'
    __name__ = 'lims.quality.test'
    _rec_name = 'number'

    _states = {'readonly': Eval('state') != 'draft'}
    _depends = ['state']

    number = fields.Char('Number', readonly=True, select=True,
        states={'required': Not(Equal(Eval('state'), 'draft'))})
    company = fields.Many2One('company.company', 'Company', required=True,
        select=True, states=_states, depends=_depends)
    test_date = fields.DateTime('Date', states=_states, depends=_depends)
    comments = fields.Text('Comments', states=_states, depends=_depends)
    lines = fields.One2Many('lims.notebook.line', 'quality_test', 'Lines',
        domain=[
            ('quality_test_report', '=', True),
            ],
        readonly=True, context={'quality': True})
    template = fields.Many2One('lims.quality.template', 'Template',
        required=True, states=_states, depends=_depends)
    sample = fields.Many2One('lims.sample', 'Sample',
        domain=[('lot.product', '=', Eval('product'))],
        states=_states, depends=_depends + ['product'])
    countersample = fields.Function(fields.Many2One('lims.sample',
        'Countersample',
        states={
            'invisible': Not(Bool(Eval('countersample'))),
            }), 'get_countersample')
    product = fields.Function(fields.Many2One('product.product', 'Product',
        states=_states, depends=_depends), 'on_change_with_product',
        searcher='search_product')
    lot = fields.Function(fields.Many2One('stock.lot', 'Lot',
        states=_states, depends=_depends), 'on_change_with_lot',
        searcher='search_lot')
    success = fields.Function(fields.Boolean('Success'), 'get_success')
    confirmed_date = fields.DateTime('Confirmed Date', readonly=True,
        states={
            'invisible': Eval('state') == 'draft',
            },
        depends=_depends)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('successful', 'Successful'),
        ('failed', 'Failed'),
        ], 'State', readonly=True, required=True)
    state_string = state.translated('state')

    del _states, _depends

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order.insert(0, ('number', 'DESC'))
        cls._transitions |= set((
            ('draft', 'confirmed'),
            ('confirmed', 'successful'),
            ('confirmed', 'failed'),
            ))
        cls._buttons.update({
            'confirm': {
                'invisible': (Eval('state') != 'draft'),
                'icon': 'tryton-forward',
                },
            'manager_validate': {
                'invisible': (Eval('state') != 'confirmed'),
                'icon': 'tryton-ok',
                },
            })

    def get_success(self, name):
        if not self.lines:
            return False
        for line in self.lines:
            if not line.success:
                return False
        return True

    @fields.depends('sample')
    def get_countersample(self, name):
        if self.sample and self.sample.countersample:
            return self.sample.countersample.id

    @staticmethod
    def default_test_date():
        return datetime.datetime.now()

    @staticmethod
    def default_state():
        return 'draft'

    @staticmethod
    def default_company():
        return Transaction().context.get('company')

    @fields.depends('template')
    def on_change_with_product(self, name=None):
        if self.template:
            return self.template.product.id

    @classmethod
    def search_product(cls, name, clause):
        return ['OR', ('template.product.name',) + tuple(clause[1:]),
            ('template.product.code',) + tuple(clause[1:]),
            ]

    @fields.depends('sample')
    def on_change_with_lot(self, name=None):
        if self.sample:
            return self.sample.lot.id

    @classmethod
    def search_lot(cls, name, clause):
        return [('sample.lot',) + tuple(clause[1:])]

    @classmethod
    def check_delete(cls, tests):
        for t in tests:
            if t.state != 'draft':
                raise UserError(gettext(
                    'lims_quality_control.msg_delete_test',
                    test=t.rec_name))

    @classmethod
    def delete(cls, tests):
        cls.check_delete(tests)
        super().delete(tests)

    @classmethod
    @ModelView.button
    @Workflow.transition('confirmed')
    def confirm(cls, tests):
        for test in tests:
            test.apply_template_values()
            test.save()
        cls.set_number(tests)
        cls.write(tests, {'confirmed_date': datetime.datetime.now()})

    @classmethod
    @Workflow.transition('successful')
    def successful(cls, tests):
        pass

    @classmethod
    @Workflow.transition('failed')
    def failed(cls, tests):
        pass

    @classmethod
    @ModelView.button
    def manager_validate(cls, tests):
        for test in tests:
            results_report_required = test.template.results_report_required
            for line in test.lines:
                if not line.accepted:
                    raise UserError(gettext(
                        'lims_quality_control.msg_missing_accepted_lines'))
                if (results_report_required and
                        line.report and not line.results_report):
                    raise UserError(gettext(
                        'lims_quality_control.msg_missing_results_report'))
            if (test.template.countersample_required and
                    test.sample.test_state != 'countersample' and
                    not test.sample.countersamples):
                raise UserError(gettext(
                    'lims_quality_control.msg_missing_countersample'))
            if test.success:
                cls.successful(tests)
            else:
                cls.failed(tests)

    @classmethod
    def set_number(cls, tests):
        pool = Pool()
        Config = pool.get('lims.quality.configuration')
        Sequence = pool.get('ir.sequence')
        config = Config(1)
        for test in tests:
            test.number = Sequence.get_id(config.quality_sequence.id)
            test.save()

    def apply_template_values(self):
        pool = Pool()
        Service = pool.get('lims.service')
        Fraction = pool.get('lims.fraction')

        # new services
        services_default = []
        for line in self.template.lines:
            laboratory_id = (line.analysis.laboratories[0].laboratory.id
                if line.analysis.type != 'group' else None)
            services_default.append({
                'fraction': self.sample.fractions[0].id,
                'analysis': line.analysis.id,
                'laboratory': laboratory_id,
                'method': line.method.id,
                'device': (line.analysis.devices[0].device.id
                    if line.analysis.devices else None),
                })
        for service in services_default:
            new_service, = Service.create([service])

            # new analysis details (on service create)

        # confirm fraction: new notebook and stock move
        context = {
            'template': self.template.id,
            'test': self.id,
            }
        with Transaction().set_context(context):
            Fraction.confirm(self.sample.fractions)

        sample = self.sample
        if sample.test_state != 'countersample':
            sample.test_state = 'done'
        sample.quality_test = self.id
        sample.save()

    @classmethod
    def copy(cls, tests, default=None):
        if default is None:
            default = {}
        if 'templates' not in default:
            default['templates'] = None
        return super().copy(tests, default)


class CreateQualityTestStart(ModelView):
    'Create Quality Test Start'
    __name__ = 'lims.create.quality.test.start'

    template = fields.Many2One('lims.quality.template', 'Template',
        required=True,
        domain=[
            ('product', '=', Eval('product')),
            ('state', '=', 'active'),
            ('end_date', '>=', Eval('date')),
            ],
        depends=['product', 'date'])
    product = fields.Many2One('product.product', 'Product')
    test_created = fields.Many2One('lims.quality.test', 'Test created')
    date = fields.Date('Date')

    @staticmethod
    def default_date():
        Date = Pool().get('ir.date')
        return Date.today()


class CreateQualityTest(Wizard):
    'Create Quality Test'
    __name__ = 'lims.create.quality.test'

    start = StateTransition()
    ask = StateView('lims.create.quality.test.start',
        'lims_quality_control.lims_create_quality_test_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Confirm', 'confirm', 'tryton-ok', default=True),
            ])
    confirm = StateTransition()
    open_ = StateAction('lims_quality_control.act_quality_test')

    def transition_start(self):
        Sample = Pool().get('lims.sample')

        sample = Sample(Transaction().context['active_id'])
        if sample.test_state == 'done':
            raise UserError(gettext(
                    'lims_quality_control.msg_sample_used'))
        return 'ask'

    def default_ask(self, fields):
        pool = Pool()
        Sample = pool.get('lims.sample')
        Template = pool.get('lims.quality.template')
        Date = pool.get('ir.date')

        sample = Sample(Transaction().context['active_id'])
        product_id = sample.lot.product.id
        res = {
            'product': product_id,
            }

        templates = Template.search([
            ('product', '=', product_id),
            ('state', '=', 'active'),
            ('end_date', '>=', Date.today()),
            ])
        if len(templates) == 1:
            res['template'] = templates[0].id
        return res

    def transition_confirm(self):
        test = self.create_test()
        self.ask.test_created = test.id
        return 'open_'

    def create_test(self):
        pool = Pool()
        Sample = pool.get('lims.sample')
        Test = pool.get('lims.quality.test')

        sample = Sample(Transaction().context.get('active_id'))

        new_test, = Test.create([{
            'template': self.ask.template.id,
            'sample': sample.id,
            }])
        return new_test

    def do_open_(self, action):
        action['views'].reverse()
        return action, {
            'res_id': [self.ask.test_created.id],
            }


class TemplateAddServiceStart(ModelView):
    'Template Add Service Start'
    __name__ = 'lims.template.add.service.start'

    service = fields.Many2One('lims.analysis', 'Service',
        required=True,
        domain=[
            ('type', 'in', ['set', 'group']),
            ('state', '=', 'active'),
            ])


class TemplateAddService(Wizard):
    'Template Add Service'
    __name__ = 'lims.template.add.service'

    start = StateTransition()
    ask = StateView('lims.template.add.service.start',
        'lims_quality_control.lims_template_add_service_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Add', 'add', 'tryton-ok', default=True),
            ])
    add = StateTransition()

    def transition_start(self):
        Template = Pool().get('lims.quality.template')

        template = Template(Transaction().context['active_id'])
        if template.state != 'draft':
            raise UserError(gettext(
                    'lims_quality_control.msg_template_not_draft'))
        return 'ask'

    def transition_add(self):
        self.add_service()
        return 'end'

    def add_service(self):
        pool = Pool()
        Template = pool.get('lims.quality.template')
        Typification = pool.get('lims.typification')

        template = Template(Transaction().context.get('active_id'))

        for analysis in self.ask.service.all_included_analysis:
            typification = Typification()
            typification.quality = True
            typification.quality_template = template.id
            typification.analysis = analysis.id
            typification.method = analysis.methods[0]
            if analysis.quality_type == 'qualitative':
                typification.valid_value = \
                    analysis.quality_possible_values[0].id
            typification.save()


class TestResultsReport(Wizard):
    'Test Results Report'
    __name__ = 'lims.test.results_report'

    start = StateAction('lims.act_lims_results_report_list')

    def do_start(self, action):
        pool = Pool()
        Test = pool.get('lims.quality.test')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        active_ids = Transaction().context['active_ids']
        tests = Test.browse(active_ids)
        sample_ids = [test.sample.id for test in tests]

        results_report_ids = []
        details = EntryDetailAnalysis.search([('sample', 'in', sample_ids)])
        if details:
            results_report_ids = [d.results_report.id for d in details
                if d.results_report]

        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', 'in', results_report_ids),
            ])
        action['name'] += ' (%s)' % ', '.join(
            t.rec_name for t in tests)
        return action, {}


class OpenTestAttachment(Wizard):
    'Test Attachment'
    __name__ = 'lims.quality.test.open_attachment'

    start = StateAction('lims.act_attachment')

    def do_start(self, action):
        Test = Pool().get('lims.quality.test')

        active_ids = Transaction().context['active_ids']
        tests = Test.browse(active_ids)

        resources = self.get_resource(tests)

        action['pyson_domain'] = PYSONEncoder().encode([
            ('resource', 'in', resources),
            ])
        action['name'] += ' (%s)' % ', '.join(t.rec_name for t in tests)
        return action, {}

    def get_resource(self, tests):
        res = []
        for test in tests:
            res.append(self._get_resource(test))
            for line in test.lines:
                if line.analysis_sheet:
                    res.append(self._get_resource(line.analysis_sheet))
        return res

    def _get_resource(self, obj):
        return '%s,%s' % (obj.__name__, obj.id)


class PrintTest(Wizard):
    'Print Test'
    __name__ = 'lims.print_test'
    start = StateTransition()
    print_ = StateReport('lims.quality.control.report')

    def transition_start(self):
        Test = Pool().get('lims.quality.test')

        test = Test(Transaction().context['active_id'])
        if test.state not in ['successful', 'failed']:
            raise UserError(gettext(
                    'lims_quality_control.msg_can_not_print_test'))
        return 'print_'

    def do_print_(self, action):
        return action, {
            'ids': Transaction().context['active_ids'],
            }


class TestReport(CompanyReport):
    'Test Report'
    __name__ = 'lims.quality.control.report'

    @classmethod
    def execute(cls, ids, data):
        pool = Pool()
        Test = pool.get('lims.quality.test')
        result = super().execute(ids, data)
        if len(ids) == 1:
            test, = Test.browse(ids)
            result = result[:3] + (
                test.product.product_type.code + ' - ' + test.lot.number,)
        return result

    @classmethod
    def get_context(cls, records, data):
        Test = Pool().get('lims.quality.test')

        report_context = super().get_context(records, data)

        report_context['objects'] = Test.browse(data['ids'])
        report_context['get_professionals'] = cls.get_professionals

        return report_context

    @classmethod
    def get_professionals(cls, test):
        professionals = []
        for line in test.lines:
            for professional in line.professionals:
                professionals.append(professional)
        professionals = list(set([
            p.professional.party.name for p in professionals]))

        return ' / '.join(professionals)


class TestAttachmentReport(Report):
    'Test Attachment Report'
    __name__ = 'lims.quality.test.attachment.report'

    @classmethod
    def execute(cls, ids, data):
        pool = Pool()
        Test = pool.get('lims.quality.test')
        Attachment = pool.get('ir.attachment')

        if len(ids) > 1:
            raise UserError(gettext('lims.msg_multiple_reports'))

        test = Test(ids[0])

        resources = []
        for line in test.lines:
            if line.analysis_sheet:
                resources.append(cls._get_resource(line.analysis_sheet))

        attachments = Attachment.search([
            ('resource', 'in', resources),
            ])

        merger = PdfFileMerger(strict=False)

        for attachment in attachments:
            filedata = BytesIO(attachment.data)
            merger.append(filedata)
        output = BytesIO()
        merger.write(output)
        document = output.getvalue()

        return 'pdf', document

    @classmethod
    def _get_resource(cls, obj):
        return '%s,%s' % (obj.__name__, obj.id)
