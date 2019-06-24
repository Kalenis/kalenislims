# -*- coding: utf-8 -*-
# This file is part of lims module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import operator
from datetime import datetime
from dateutil.relativedelta import relativedelta
from sql import Literal, Join
from trytond.model import ModelView, ModelSQL, fields
from trytond.wizard import Wizard, StateTransition, StateView, StateAction, \
    StateReport, Button
from trytond.pool import Pool
from trytond.pyson import PYSONEncoder, Eval, Bool, Not, Or
from trytond.transaction import Transaction
from trytond.report import Report
from .formula_parser import FormulaParser
from .results_report import get_print_date

__all__ = ['Notebook', 'NotebookLine', 'NotebookLineAllFields',
    'NotebookLineLaboratoryProfessional',
    'NotebookLineProfessional', 'NotebookInitialConcentrationCalcStart',
    'NotebookInitialConcentrationCalc', 'NotebookLineInitialConcentrationCalc',
    'NotebookResultsConversionStart', 'NotebookResultsConversion',
    'NotebookLineResultsConversion', 'NotebookLimitsValidationStart',
    'NotebookLimitsValidation', 'NotebookLineLimitsValidation',
    'NotebookInternalRelationsCalc1Start',
    'NotebookInternalRelationsCalc1Relation',
    'NotebookInternalRelationsCalc1Variable', 'NotebookInternalRelationsCalc1',
    'NotebookLineInternalRelationsCalc1',
    'NotebookInternalRelationsCalc2Start',
    'NotebookInternalRelationsCalc2Result',
    'NotebookInternalRelationsCalc2Relation',
    'NotebookInternalRelationsCalc2Variable',
    'NotebookInternalRelationsCalc2Process', 'NotebookInternalRelationsCalc2',
    'NotebookLineInternalRelationsCalc2', 'NotebookLoadResultsFormulaStart',
    'NotebookLoadResultsFormulaEmpty', 'NotebookLoadResultsFormulaResult',
    'NotebookLoadResultsFormulaLine', 'NotebookLoadResultsFormulaAction',
    'NotebookLoadResultsFormulaProcess', 'NotebookLoadResultsFormulaVariable',
    'NotebookLoadResultsFormulaBeginning', 'NotebookLoadResultsFormulaConfirm',
    'NotebookLoadResultsFormulaSit1', 'NotebookLoadResultsFormulaSit2',
    'NotebookLoadResultsFormulaSit2Detail',
    'NotebookLoadResultsFormulaSit2DetailLine', 'NotebookLoadResultsFormula',
    'NotebookLoadResultsManualStart', 'NotebookLoadResultsManualEmpty',
    'NotebookLoadResultsManualResult', 'NotebookLoadResultsManualLine',
    'NotebookLoadResultsManualSit1', 'NotebookLoadResultsManualSit2',
    'NotebookLoadResultsManual', 'NotebookAddInternalRelationsStart',
    'NotebookAddInternalRelations', 'NotebookLineRepeatAnalysisStart',
    'NotebookLineRepeatAnalysis', 'NotebookAcceptLinesStart',
    'NotebookAcceptLines', 'NotebookLineAcceptLines',
    'NotebookLineUnacceptLines', 'NotebookResultsVerificationStart',
    'NotebookResultsVerification', 'NotebookLineResultsVerification',
    'UncertaintyCalcStart', 'UncertaintyCalc', 'NotebookLineUncertaintyCalc',
    'NotebookPrecisionControlStart', 'NotebookPrecisionControl',
    'NotebookLinePrecisionControl', 'OpenNotebookLines',
    'ChangeEstimatedDaysForResultsStart', 'ChangeEstimatedDaysForResults']


class Notebook(ModelSQL, ModelView):
    'Laboratory Notebook'
    __name__ = 'lims.notebook'

    fraction = fields.Many2One('lims.fraction', 'Fraction', required=True,
        readonly=True, ondelete='CASCADE', select=True)
    lines = fields.One2Many('lims.notebook.line', 'notebook', 'Lines')
    product_type = fields.Function(fields.Many2One('lims.product.type',
        'Product type'), 'get_sample_field', searcher='search_sample_field')
    matrix = fields.Function(fields.Many2One('lims.matrix', 'Matrix'),
        'get_sample_field', searcher='search_sample_field')
    party = fields.Function(fields.Many2One('party.party', 'Party'),
        'get_sample_field', searcher='search_sample_field')
    party_code = fields.Function(fields.Char('Party'), 'get_party_code',
        searcher='search_party_code')
    label = fields.Function(fields.Char('Label'), 'get_sample_field',
        searcher='search_sample_field')
    date = fields.Function(fields.DateTime('Date'), 'get_sample_field',
        searcher='search_sample_field')
    date2 = fields.Function(fields.Date('Date'), 'get_sample_field',
        searcher='search_sample_field')
    fraction_type = fields.Function(fields.Many2One('lims.fraction.type',
        'Fraction type'), 'get_fraction_field',
        searcher='search_fraction_field')
    fraction_comments = fields.Function(fields.Text('Fraction Comments'),
        'get_fraction_field')
    shared = fields.Function(fields.Boolean('Shared'), 'get_fraction_field',
        searcher='search_fraction_field')
    current_location = fields.Function(fields.Many2One('stock.location',
        'Current Location'), 'get_current_location',
        searcher='search_current_location')
    divided_report = fields.Function(fields.Boolean('Divided report'),
        'get_divided_report')
    icon = fields.Function(fields.Char("Icon"), 'get_icon')
    obj_description = fields.Function(fields.Char('Objective description',
        translate=True), 'get_obj_description')

    @classmethod
    def __setup__(cls):
        super(Notebook, cls).__setup__()
        cls._order.insert(0, ('fraction', 'DESC'))

    def get_rec_name(self, name):
        if self.fraction:
            return self.fraction.rec_name

    @classmethod
    def search_rec_name(cls, name, clause):
        return [('fraction',) + tuple(clause[1:])]

    @classmethod
    def get_sample_field(cls, notebooks, names):
        result = {}
        for name in names:
            result[name] = {}
            if name in ('label', 'date', 'date2'):
                for n in notebooks:
                    result[name][n.id] = getattr(n.fraction.sample, name, None)
            else:
                for n in notebooks:
                    field = getattr(n.fraction.sample, name, None)
                    result[name][n.id] = field.id if field else None
        return result

    @classmethod
    def search_sample_field(cls, name, clause):
        return [('fraction.sample.' + name,) + tuple(clause[1:])]

    @classmethod
    def get_obj_description(cls, notebooks, name):
        result = {}
        for n in notebooks:
            field = getattr(n.fraction.sample, 'obj_description', None)
            if field:
                result[n.id] = field.description
            else:
                result[n.id] = getattr(n.fraction.sample,
                    'obj_description_manual', None)
        return result

    @classmethod
    def get_party_code(cls, notebooks, name):
        result = {}
        for n in notebooks:
            result[n.id] = n.party.code
        return result

    @classmethod
    def search_party_code(cls, name, clause):
        return [('fraction.sample.entry.party.code',) + tuple(clause[1:])]

    @classmethod
    def get_fraction_field(cls, notebooks, names):
        result = {}
        for name in names:
            result[name] = {}
            if name == 'fraction_type':
                for n in notebooks:
                    field = getattr(n.fraction, 'type', None)
                    result[name][n.id] = field.id if field else None
            elif name == 'fraction_comments':
                for n in notebooks:
                    result[name][n.id] = getattr(n.fraction, 'comments', None)
            else:
                for n in notebooks:
                    result[name][n.id] = getattr(n.fraction, name, None)
        return result

    @classmethod
    def search_fraction_field(cls, name, clause):
        if name == 'fraction_type':
            name = 'type'
        return [('fraction.' + name,) + tuple(clause[1:])]

    def get_divided_report(self, name):
        if not self.fraction or not self.fraction.services:
            return False
        for s in self.fraction.services:
            if s.divide:
                return True
        return False

    @classmethod
    def get_current_location(cls, notebooks, name=None):
        cursor = Transaction().connection.cursor()
        Move = Pool().get('stock.move')

        result = {}
        for n in notebooks:
            cursor.execute('SELECT to_location '
                'FROM "' + Move._table + '" '
                'WHERE fraction = %s '
                    'AND state IN (\'assigned\', \'done\') '
                'ORDER BY effective_date DESC, id DESC '
                'LIMIT 1', (n.fraction.id,))
            location = cursor.fetchone()
            result[n.id] = location[0] if location else None
        return result

    @classmethod
    def search_current_location(cls, name, domain=None):

        def _search_current_location_eval_domain(line, domain):
            operator_funcs = {
                '=': operator.eq,
                '>=': operator.ge,
                '>': operator.gt,
                '<=': operator.le,
                '<': operator.lt,
                '!=': operator.ne,
                'in': lambda v, l: v in l,
                'not in': lambda v, l: v not in l,
                'ilike': lambda v, l: False,
                }
            field, op, operand = domain
            value = line.get(field)
            return operator_funcs[op](value, operand)

        if domain and domain[1] == 'ilike':
            Location = Pool().get('stock.location')
            locations = Location.search([
                ('code', '=', domain[2]),
                ], order=[])
            if not locations:
                locations = Location.search([
                    ('name',) + tuple(domain[1:]),
                    ], order=[])
                if not locations:
                    return []
            domain = ('current_location', 'in', [l.id for l in locations])

        all_notebooks = cls.search([])
        current_locations = iter(cls.get_current_location(all_notebooks).items())

        processed_lines = [{
            'fraction': fraction,
            'current_location': location,
            } for fraction, location in current_locations]

        record_ids = [line['fraction'] for line in processed_lines
            if _search_current_location_eval_domain(line, domain)]
        return [('id', 'in', record_ids)]

    def get_icon(self, name):
        if self.fraction_comments:
            return 'lims-blue'
        return 'lims-white'


class NotebookLine(ModelSQL, ModelView):
    'Laboratory Notebook Line'
    __name__ = 'lims.notebook.line'

    notebook = fields.Many2One('lims.notebook', 'Laboratory notebook',
        ondelete='CASCADE', select=True, required=True)
    analysis_detail = fields.Many2One('lims.entry.detail.analysis',
        'Analysis detail', select=True)
    service = fields.Many2One('lims.service', 'Service', readonly=True,
        ondelete='CASCADE', select=True)
    analysis = fields.Many2One('lims.analysis', 'Analysis', required=True,
        readonly=True)
    repetition = fields.Integer('Repetition', readonly=True)
    start_date = fields.Date('Start date', readonly=True)
    end_date = fields.Date('End date', states={
        'readonly': Or(~Bool(Eval('start_date')), Bool(Eval('accepted'))),
        }, depends=['start_date', 'accepted'])
    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        readonly=True)
    method = fields.Many2One('lims.lab.method', 'Method',
        required=True, domain=['OR', ('id', '=', Eval('method')),
            ('id', 'in', Eval('method_domain'))],
        depends=['method_domain'])
    method_view = fields.Function(fields.Many2One('lims.lab.method',
        'Method'), 'get_views_field')
    method_domain = fields.Function(fields.Many2Many('lims.lab.method',
        None, None, 'Method domain'),
        'on_change_with_method_domain')
    device = fields.Many2One('lims.lab.device', 'Device',
        domain=['OR', ('id', '=', Eval('device')),
            ('id', 'in', Eval('device_domain'))],
        depends=['device_domain'])
    device_view = fields.Function(fields.Many2One('lims.lab.device',
        'Device'), 'get_views_field')
    device_domain = fields.Function(fields.Many2Many('lims.lab.device',
        None, None, 'Device domain'), 'on_change_with_device_domain')
    analysis_origin = fields.Char('Analysis origin', readonly=True)
    initial_concentration = fields.Char('Initial concentration')
    final_concentration = fields.Char('Final concentration')
    laboratory_professionals = fields.Many2Many(
        'lims.notebook.line-laboratory.professional', 'notebook_line',
        'professional', 'Preparation professionals')
    initial_unit = fields.Many2One('product.uom', 'Initial unit',
        domain=[('category.lims_only_available', '=', True)],
        states={'readonly': Bool(Eval('accepted'))}, depends=['accepted'])
    final_unit = fields.Many2One('product.uom', 'Final unit',
        domain=[('category.lims_only_available', '=', True)],
        states={'readonly': Bool(Eval('accepted'))}, depends=['accepted'])
    result_modifier = fields.Selection([
        ('eq', '='),
        ('low', '<'),
        ('nd', 'nd'),
        ('na', 'na'),
        ('pos', 'Positive'),
        ('neg', 'Negative'),
        ('ni', 'ni'),
        ('abs', 'Absence'),
        ('pre', 'Presence'),
        ], 'Result modifier', sort=False,
        states={'readonly': Bool(Eval('accepted'))}, depends=['accepted'])
    result_modifier_string = result_modifier.translated('result_modifier')
    converted_result_modifier = fields.Selection([
        ('eq', '='),
        ('low', '<'),
        ('nd', 'nd'),
        ('pos', 'Positive'),
        ('neg', 'Negative'),
        ('ni', 'ni'),
        ], 'Converted result modifier', sort=False,
        states={'readonly': Bool(Eval('accepted'))}, depends=['accepted'])
    converted_result_modifier_string = converted_result_modifier.translated(
        'converted_result_modifier')
    result = fields.Char('Result',
        states={'readonly': Bool(Eval('accepted'))}, depends=['accepted'])
    converted_result = fields.Char('Converted result',
        states={'readonly': Bool(Eval('accepted'))}, depends=['accepted'])
    detection_limit = fields.Char('Detection limit',
        states={'readonly': Bool(Eval('accepted'))}, depends=['accepted'])
    quantification_limit = fields.Char('Quantification limit',
        states={'readonly': Bool(Eval('accepted'))}, depends=['accepted'])
    check_result_limits = fields.Function(fields.Boolean(
        'Validate limits directly on the result'), 'get_typification_field')
    chromatogram = fields.Char('Chromatogram')
    professionals = fields.One2Many('lims.notebook.line.professional',
        'notebook_line', 'Analytic professionals')
    comments = fields.Text('Entry comments')
    theoretical_concentration = fields.Char('Theoretical concentration')
    concentration_level = fields.Many2One('lims.concentration.level',
        'Concentration level')
    decimals = fields.Integer('Decimals')
    backup = fields.Char('Backup')
    reference = fields.Char('Reference')
    literal_result = fields.Char('Literal result', translate=True,
        states={'readonly': Bool(Eval('accepted'))}, depends=['accepted'])
    rm_correction_formula = fields.Char('RM Correction Formula')
    report = fields.Boolean('Report')
    uncertainty = fields.Char('Uncertainty')
    verification = fields.Char('Verification')
    analysis_order = fields.Function(fields.Integer('Order'),
        'get_analysis_order')
    dilution_factor = fields.Float('Dilution factor')
    accepted = fields.Boolean('Accepted')
    acceptance_date = fields.DateTime('Acceptance date',
        states={'readonly': True})
    not_accepted_message = fields.Text('Message', readonly=True,
        states={'invisible': Not(Bool(Eval('not_accepted_message')))})
    annulled = fields.Boolean('Annulled', states={'readonly': True})
    annulment_date = fields.DateTime('Annulment date',
        states={'readonly': True})
    results_report = fields.Many2One('lims.results_report', 'Results Report',
        readonly=True)
    planification = fields.Many2One('lims.planification', 'Planification',
        readonly=True)
    urgent = fields.Function(fields.Boolean('Urgent'), 'get_service_field',
        searcher='search_service_field')
    priority = fields.Function(fields.Integer('Priority'),
        'get_service_field', searcher='search_service_field')
    report_date = fields.Function(fields.Date('Date agreed for result'),
        'get_service_field', searcher='search_service_field')
    fraction = fields.Function(fields.Many2One('lims.fraction', 'Fraction'),
        'get_service_field', searcher='search_service_field')
    fraction_type = fields.Function(fields.Many2One('lims.fraction.type',
        'Fraction type'), 'get_fraction_field',
        searcher='search_fraction_field')
    party = fields.Function(fields.Many2One('party.party', 'Party'),
        'get_fraction_field', searcher='search_fraction_field')
    product_type = fields.Function(fields.Many2One('lims.product.type',
        'Product type'), 'get_sample_field', searcher='search_sample_field')
    matrix = fields.Function(fields.Many2One('lims.matrix', 'Matrix'),
        'get_sample_field', searcher='search_sample_field')
    label = fields.Function(fields.Char('Label'), 'get_sample_field',
        searcher='search_sample_field')
    date = fields.Function(fields.DateTime('Date'), 'get_sample_field',
        searcher='search_sample_field')
    date2 = fields.Function(fields.Date('Date'), 'get_sample_field',
        searcher='search_sample_field')
    report_type = fields.Function(fields.Char('Report type'),
        'get_typification_field', searcher='search_typification_field')
    report_result_type = fields.Function(fields.Char('Result type'),
        'get_typification_field', searcher='search_typification_field')
    results_estimated_waiting = fields.Integer(
        'Estimated number of days for results', states={'readonly': True})
    results_estimated_date = fields.Function(fields.Date(
        'Estimated date of result'), 'get_results_estimated_date')
    department = fields.Many2One('company.department', 'Department',
        readonly=True)
    icon = fields.Function(fields.Char("Icon"), 'get_icon')
    planning_comments = fields.Function(fields.Text('Planification comments'),
        'get_planning_comments')
    controls = fields.Many2Many('lims.notebook.line-fraction',
        'notebook_line', 'fraction', 'Controls')

    @classmethod
    def __setup__(cls):
        super(NotebookLine, cls).__setup__()
        cls._order.insert(0, ('analysis_order', 'ASC'))
        cls._order.insert(1, ('repetition', 'ASC'))
        cls._error_messages.update({
            'end_date': 'The end date cannot be lower than start date',
            'end_date_wrong': ('End date should not be greater than the '
                'current date'),
            'accepted': 'The analysis "%s" is already accepted',
            'not_accepted_1': 'The analysis is not reported',
            'not_accepted_2': 'The analysis is annulled',
            'not_accepted_3': 'The analysis has not End date',
            'not_accepted_4': 'The analysis has not Result / Converted result',
            'not_accepted_5': 'The Converted result modifier is invalid',
            'not_accepted_6': 'The Result modifier is invalid',
            'not_accepted_7': ('The Converted result / Converted result '
                'modifier is invalid'),
            'accepted_1': 'The analysis is already reported (%s)',
            })

    @staticmethod
    def default_repetition():
        return 0

    @staticmethod
    def default_result_modifier():
        return 'eq'

    @staticmethod
    def default_converted_result_modifier():
        return 'eq'

    @staticmethod
    def default_decimals():
        return 2

    @staticmethod
    def default_report():
        return True

    @staticmethod
    def default_dilution_factor():
        return 1.0

    @staticmethod
    def default_accepted():
        return False

    @staticmethod
    def default_annulled():
        return False

    @classmethod
    def create(cls, vlist):
        lines = super(NotebookLine, cls).create(vlist)
        cls.update_detail_report(lines)
        return lines

    @classmethod
    def write(cls, *args):
        super(NotebookLine, cls).write(*args)
        actions = iter(args)
        for lines, vals in zip(actions, actions):
            if vals.get('not_accepted_message'):
                cls.write(lines, {
                    'not_accepted_message': None,
                    })
            if 'accepted' in vals:
                cls.update_detail_analysis(lines, vals['accepted'])
            if 'report' in vals:
                cls.update_detail_report(lines)

    @staticmethod
    def update_detail_analysis(lines, accepted):
        EntryDetailAnalysis = Pool().get('lims.entry.detail.analysis')

        details = [nl.analysis_detail.id for nl in lines]
        if accepted:
            analysis_details = EntryDetailAnalysis.search([
                ('id', 'in', details),
                ])
            if analysis_details:
                EntryDetailAnalysis.write(analysis_details, {
                    'state': 'done',
                    })
        else:
            analysis_details = EntryDetailAnalysis.search([
                ('id', 'in', details),
                ('analysis.behavior', '!=', 'internal_relation'),
                ])
            if analysis_details:
                EntryDetailAnalysis.write(analysis_details, {
                    'state': 'planned',
                    })
            analysis_details = EntryDetailAnalysis.search([
                ('id', 'in', details),
                ('analysis.behavior', '=', 'internal_relation'),
                ])
            if analysis_details:
                EntryDetailAnalysis.write(analysis_details, {
                    'state': 'unplanned',
                    })

    @staticmethod
    def update_detail_report(lines):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        NotebookLine = pool.get('lims.notebook.line')

        to_save = []
        details_ids = list(set(nl.analysis_detail.id for nl in lines))
        with Transaction().set_context(_check_access=False):
            analysis_details = EntryDetailAnalysis.browse(details_ids)
        for d in analysis_details:
            cursor.execute('SELECT report '
                'FROM "' + NotebookLine._table + '" '
                'WHERE analysis_detail = %s '
                'ORDER BY id DESC LIMIT 1',
                (d.id,))
            value = cursor.fetchone()
            d.report = value[0] if value else False
            to_save.append(d)
        EntryDetailAnalysis.save(to_save)

    @classmethod
    def validate(cls, notebook_lines):
        super(NotebookLine, cls).validate(notebook_lines)
        for line in notebook_lines:
            line.check_end_date()
            line.check_accepted()

    def check_end_date(self):
        if self.end_date:
            if not self.start_date or self.end_date < self.start_date:
                self.raise_user_error('end_date')
            if not self.start_date or self.end_date > datetime.now().date():
                self.raise_user_error('end_date_wrong')

    def check_accepted(self):
        if self.accepted:
            accepted_lines = self.search([
                ('notebook', '=', self.notebook.id),
                ('analysis', '=', self.analysis.id),
                ('accepted', '=', True),
                ('id', '!=', self.id),
                ])
            if accepted_lines:
                self.raise_user_error('accepted', (self.analysis.rec_name,))

    @classmethod
    def get_analysis_order(cls, notebook_lines, name):
        result = {}
        for nl in notebook_lines:
            analysis = getattr(nl, 'analysis', None)
            result[nl.id] = analysis.order if analysis else None
        return result

    @staticmethod
    def order_analysis_order(tables):
        Analysis = Pool().get('lims.analysis')
        field = Analysis._fields['order']
        table, _ = tables[None]
        analysis_tables = tables.get('analysis')
        if analysis_tables is None:
            analysis = Analysis.__table__()
            analysis_tables = {
                None: (analysis, analysis.id == table.analysis),
                }
            tables['analysis'] = analysis_tables
        return field.convert_order('order', analysis_tables, Analysis)

    @classmethod
    def get_views_field(cls, notebook_lines, names):
        result = {}
        for name in names:
            field_name = name[:-5]
            result[name] = {}
            for nl in notebook_lines:
                field = getattr(nl, field_name, None)
                result[name][nl.id] = field.id if field else None
        return result

    @classmethod
    def get_service_field(cls, notebook_lines, names):
        result = {}
        for name in names:
            result[name] = {}
            if name == 'fraction':
                for nl in notebook_lines:
                    field = getattr(nl.service, name, None)
                    result[name][nl.id] = field.id if field else None
            else:
                for nl in notebook_lines:
                    result[name][nl.id] = getattr(nl.service, name, None)
        return result

    @classmethod
    def search_service_field(cls, name, clause):
        return [('service.' + name,) + tuple(clause[1:])]

    @classmethod
    def get_fraction_field(cls, notebook_lines, names):
        result = {}
        for name in names:
            result[name] = {}
            if name == 'fraction_type':
                for nl in notebook_lines:
                    fraction = getattr(nl.service, 'fraction', None)
                    if fraction:
                        field = getattr(fraction, 'type', None)
                        result[name][nl.id] = field.id if field else None
                    else:
                        result[name][nl.id] = None
            else:
                for nl in notebook_lines:
                    fraction = getattr(nl.service, 'fraction', None)
                    if fraction:
                        field = getattr(fraction, name, None)
                        result[name][nl.id] = field.id if field else None
                    else:
                        result[name][nl.id] = None
        return result

    @classmethod
    def search_fraction_field(cls, name, clause):
        if name == 'fraction_type':
            name = 'type'
        return [('service.fraction.' + name,) + tuple(clause[1:])]

    @classmethod
    def get_sample_field(cls, notebook_lines, names):
        result = {}
        for name in names:
            result[name] = {}
            for nl in notebook_lines:
                result[name][nl.id] = None
                fraction = getattr(nl.service, 'fraction', None)
                if fraction:
                    sample = getattr(fraction, 'sample', None)
                    if sample:
                        field = getattr(fraction, name, None)
                        if name in ('label', 'date', 'date2'):
                            result[name][nl.id] = field
                        else:
                            result[name][nl.id] = field.id if field else None
        return result

    @classmethod
    def search_sample_field(cls, name, clause):
        return [('service.fraction.sample.' + name,) + tuple(clause[1:])]

    def get_rec_name(self, name):
        if self.analysis:
            return self.analysis.rec_name

    @classmethod
    def search_rec_name(cls, name, clause):
        return [('analysis',) + tuple(clause[1:])]

    @classmethod
    def fields_view_get(cls, view_id=None, view_type='form'):
        pool = Pool()
        User = pool.get('res.user')
        Config = pool.get('lims.configuration')
        UiView = pool.get('ir.ui.view')

        result = super(NotebookLine, cls).fields_view_get(view_id=view_id,
            view_type=view_type)

        # All Notebook Lines view
        if view_id and UiView(view_id).name == 'notebook_line_all_list':
            return result

        notebook_view = User(Transaction().user).notebook_view
        if not notebook_view:
            notebook_view = Config(1).default_notebook_view
            if not notebook_view:
                return result

        if view_type == 'tree':
            xml = '<?xml version="1.0"?>\n' \
                '<tree editable="bottom">\n'
            fields = set()
            for column in notebook_view.columns:
                fields.add(column.field.name)
                attrs = []
                if column.field.name == 'analysis':
                    attrs.append('icon="icon"')
                if column.field.name in ('acceptance_date', 'annulment_date'):
                    attrs.append('widget="date"')
                xml += ('<field name="%s" %s/>\n'
                    % (column.field.name, ' '.join(attrs)))
                for depend in getattr(cls, column.field.name).depends:
                    fields.add(depend)
            for field in ('report_date', 'result', 'converted_result',
                    'result_modifier', 'converted_result_modifier',
                    'literal_result', 'backup', 'verification', 'uncertainty',
                    'accepted', 'acceptance_date', 'end_date', 'report',
                    'annulled', 'annulment_date', 'icon'):
                fields.add(field)
            xml += '</tree>'
            result['arch'] = xml
            result['fields'] = cls.fields_get(fields_names=list(fields))
        return result

    @fields.depends('result', 'converted_result', 'converted_result_modifier',
        'backup', 'verification', 'uncertainty', 'end_date')
    def on_change_result(self):
        self.converted_result = None
        self.converted_result_modifier = 'eq'
        self.backup = None
        self.verification = None
        self.uncertainty = None
        self.end_date = None

    @fields.depends('accepted', 'report', 'annulled', 'result',
        'converted_result', 'literal_result', 'result_modifier',
        'converted_result_modifier', 'end_date', 'acceptance_date')
    def on_change_accepted(self):
        self.not_accepted_message = ''
        if self.accepted:
            if not self.report:
                self.accepted = False
                self.not_accepted_message = self.raise_user_error(
                    'not_accepted_1', raise_exception=False)
            elif self.annulled:
                self.accepted = False
                self.not_accepted_message = self.raise_user_error(
                    'not_accepted_2', raise_exception=False)
            elif not self.end_date:
                self.accepted = False
                self.not_accepted_message = self.raise_user_error(
                    'not_accepted_3', raise_exception=False)
            elif not (self.result or self.converted_result or
                    self.literal_result or
                    self.result_modifier in
                    ('nd', 'pos', 'neg', 'ni', 'abs', 'pre') or
                    self.converted_result_modifier in
                    ('nd', 'pos', 'neg', 'ni', 'abs', 'pre')):
                self.accepted = False
                self.not_accepted_message = self.raise_user_error(
                    'not_accepted_4', raise_exception=False)
            else:
                if (self.converted_result and self.converted_result_modifier
                        not in ('ni', 'eq', 'low')):
                    self.accepted = False
                    self.not_accepted_message = self.raise_user_error(
                        'not_accepted_5', raise_exception=False)
                elif (self.result and self.result_modifier
                        not in ('ni', 'eq', 'low')):
                    self.accepted = False
                    self.not_accepted_message = self.raise_user_error(
                        'not_accepted_6', raise_exception=False)
                elif (self.result_modifier == 'ni' and
                        not self.literal_result and
                        (not self.converted_result_modifier or
                            not self.converted_result) and
                        self.converted_result_modifier != 'nd'):
                    self.accepted = False
                    self.not_accepted_message = self.raise_user_error(
                        'not_accepted_7', raise_exception=False)
                else:
                    self.acceptance_date = datetime.now()
        else:
            ResultsReportVersionDetailLine = Pool().get(
                'lims.results_report.version.detail.line')
            report_lines = ResultsReportVersionDetailLine.search([
                ('notebook_line', '=', self.id),
                ('report_version_detail.state', '!=', 'annulled'),
                ])
            if report_lines:
                self.accepted = True
                report_detail = report_lines[0].report_version_detail
                self.not_accepted_message = self.raise_user_error('accepted_1',
                    (report_detail.report_version.results_report.number,),
                    raise_exception=False)
            else:
                self.acceptance_date = None

    @fields.depends('result_modifier', 'annulled', 'annulment_date', 'report')
    def on_change_result_modifier(self):
        if self.result_modifier == 'na' and not self.annulled:
            self.annulled = True
            self.annulment_date = datetime.now()
            self.report = False
        elif self.result_modifier != 'na' and self.annulled:
            self.annulled = False
            self.annulment_date = None
            self.report = True

    @classmethod
    def get_typification_field(cls, notebook_lines, names):
        Typification = Pool().get('lims.typification')
        result = dict((name, {}) for name in names)
        for nl in notebook_lines:
            typifications = Typification.search([
                ('product_type', '=', nl.notebook.product_type.id),
                ('matrix', '=', nl.notebook.matrix.id),
                ('analysis', '=', nl.analysis.id),
                ('method', '=', nl.method.id),
                ('valid', '=', True),
                ])
            typification = (typifications[0] if len(typifications) == 1
                else None)
            for name in names:
                if typification:
                    result[name][nl.id] = getattr(typification, name, None)
                else:
                    if name == 'report_type':
                        result[name][nl.id] = 'normal'
                    elif name == 'report_result_type':
                        result[name][nl.id] = 'result'
                    elif name == 'check_result_limits':
                        result[name][nl.id] = False
                    else:
                        result[name][nl.id] = None
        return result

    @classmethod
    def search_typification_field(cls, name, clause):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Notebook = pool.get('lims.notebook')
        Fraction = pool.get('lims.fraction')
        Sample = pool.get('lims.sample')
        Typification = pool.get('lims.typification')

        operator_ = clause[1:2][0]
        cursor.execute('SELECT nl.id '
            'FROM "' + cls._table + '" nl '
                'INNER JOIN "' + Notebook._table + '" n '
                'ON nl.notebook = n.id '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON n.fraction = f.id '
                'INNER JOIN "' + Sample._table + '" s '
                'ON f.sample = s.id '
                'INNER JOIN "' + Typification._table + '" t '
                'ON (nl.analysis = t.analysis AND nl.method = t.method '
                'AND s.product_type = t.product_type AND t.matrix = t.matrix) '
            'WHERE t.valid = TRUE '
                'AND t.' + name + ' ' + operator_ + ' %s',
            clause[2:3])
        return [('id', 'in', [x[0] for x in cursor.fetchall()])]

    @fields.depends('method', 'party')
    def on_change_with_results_estimated_waiting(self, name=None):
        LabMethodWaitingTime = Pool().get('lims.lab.method.results_waiting')
        if self.method:
            waiting_times = LabMethodWaitingTime.search([
                ('method', '=', self.method.id),
                ('party', '=', self.party.id),
                ])
            if waiting_times:
                return waiting_times[0].results_estimated_waiting
            return self.method.results_estimated_waiting
        return None

    @classmethod
    def get_results_estimated_date(cls, notebook_lines, name):
        result = {}
        for nl in notebook_lines:
            result[nl.id] = None
            detail = getattr(nl, 'analysis_detail', None)
            if not detail:
                continue
            confirmation_date = getattr(detail, 'confirmation_date', None)
            if not confirmation_date:
                continue
            estimated_waiting = getattr(nl, 'results_estimated_waiting', None)
            if not estimated_waiting:
                continue
            result[nl.id] = cls._get_results_estimated_date(confirmation_date,
                estimated_waiting)
        return result

    @staticmethod
    def _get_results_estimated_date(confirmation_date, estimated_waiting):
        date = (confirmation_date +
            relativedelta(days=estimated_waiting))
        return date

    @fields.depends('analysis')
    def on_change_with_method_domain(self, name=None):
        methods = []
        if self.analysis and self.analysis.methods:
            methods = [m.id for m in self.analysis.methods]
        return methods

    @fields.depends('analysis', 'laboratory')
    def on_change_with_device_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        AnalysisDevice = Pool().get('lims.analysis.device')

        if not self.analysis or not self.laboratory:
            return []

        cursor.execute('SELECT DISTINCT(device) '
            'FROM "' + AnalysisDevice._table + '" '
            'WHERE analysis = %s  '
                'AND laboratory = %s',
            (self.analysis.id, self.laboratory.id))
        res = cursor.fetchall()
        if not res:
            return []
        return [x[0] for x in res]

    def get_icon(self, name):
        if self.report_date:
            return 'lims-red'
        return 'lims-white'

    def get_planning_comments(self, name=None):
        if self.planification:
            return self.planification.comments
        return ''


class NotebookLineAllFields(ModelSQL, ModelView):
    'Laboratory Notebook Line'
    __name__ = 'lims.notebook.line.all_fields'

    line = fields.Many2One('lims.notebook.line', 'Notebook Line')
    fraction = fields.Many2One('lims.fraction', 'Fraction', readonly=True)
    fraction_type = fields.Many2One('lims.fraction.type', 'Fraction type',
        readonly=True)
    party = fields.Many2One('party.party', 'Party', readonly=True)
    party_code = fields.Char('Party', readonly=True)
    product_type = fields.Many2One('lims.product.type', 'Product type',
        readonly=True)
    matrix = fields.Many2One('lims.matrix', 'Matrix', readonly=True)
    label = fields.Char('Label', readonly=True)
    date = fields.DateTime('Date', readonly=True)
    analysis = fields.Many2One('lims.analysis', 'Analysis', readonly=True)
    repetition = fields.Integer('Repetition', readonly=True)
    start_date = fields.Date('Start date', readonly=True)
    end_date = fields.Date('End date', readonly=True)
    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        readonly=True)
    method = fields.Many2One('lims.lab.method', 'Method', readonly=True)
    device = fields.Many2One('lims.lab.device', 'Device', readonly=True)
    service = fields.Many2One('lims.service', 'Service', readonly=True)
    analysis_origin = fields.Char('Analysis origin', readonly=True)
    urgent = fields.Boolean('Urgent', readonly=True)
    priority = fields.Integer('Priority', readonly=True)
    report_date = fields.Date('Date agreed for result', readonly=True)
    initial_concentration = fields.Char('Initial concentration', readonly=True)
    final_concentration = fields.Char('Final concentration', readonly=True)
    laboratory_professionals = fields.Function(fields.Many2Many(
        'lims.laboratory.professional', None, None,
        'Preparation professionals'), 'get_line_field',
        searcher='search_line_field')
    initial_unit = fields.Many2One('product.uom', 'Initial unit',
        readonly=True)
    final_unit = fields.Many2One('product.uom', 'Final unit', readonly=True)
    result_modifier = fields.Selection([
        ('eq', '='),
        ('low', '<'),
        ('nd', 'nd'),
        ('na', 'na'),
        ('pos', 'Positive'),
        ('neg', 'Negative'),
        ('ni', 'ni'),
        ('abs', 'Absence'),
        ('pre', 'Presence'),
        ], 'Result modifier', readonly=True)
    converted_result_modifier = fields.Selection([
        ('eq', '='),
        ('low', '<'),
        ('nd', 'nd'),
        ('pos', 'Positive'),
        ('neg', 'Negative'),
        ('ni', 'ni'),
        ], 'Converted result modifier', readonly=True)
    result_modifier_string = result_modifier.translated('result_modifier')
    converted_result_modifier_string = converted_result_modifier.translated(
        'converted_result_modifier')
    result = fields.Char('Result', readonly=True)
    converted_result = fields.Char('Converted result', readonly=True)
    detection_limit = fields.Char('Detection limit', readonly=True)
    quantification_limit = fields.Char('Quantification limit', readonly=True)
    chromatogram = fields.Char('Chromatogram', readonly=True)
    professionals = fields.Function(fields.One2Many(
        'lims.notebook.line.professional', None,
        'Analytic professionals'), 'get_line_field',
        searcher='search_line_field')
    comments = fields.Text('Entry comments', readonly=True)
    theoretical_concentration = fields.Char('Theoretical concentration',
        readonly=True)
    concentration_level = fields.Many2One('lims.concentration.level',
        'Concentration level', readonly=True)
    decimals = fields.Integer('Decimals', readonly=True)
    backup = fields.Char('Backup', readonly=True)
    reference = fields.Char('Reference', readonly=True)
    literal_result = fields.Char('Literal result', readonly=True)
    rm_correction_formula = fields.Char('RM Correction Formula', readonly=True)
    report = fields.Boolean('Report', readonly=True)
    uncertainty = fields.Char('Uncertainty', readonly=True)
    verification = fields.Char('Verification', readonly=True)
    dilution_factor = fields.Float('Dilution factor', readonly=True)
    accepted = fields.Boolean('Accepted', readonly=True)
    acceptance_date = fields.DateTime('Acceptance date', readonly=True)
    annulled = fields.Boolean('Annulled', readonly=True)
    annulment_date = fields.DateTime('Annulment date', readonly=True)
    results_report = fields.Many2One('lims.results_report', 'Results Report',
        readonly=True)
    planification = fields.Many2One('lims.planification', 'Planification',
        readonly=True)
    confirmation_date = fields.Date('Confirmation date', readonly=True)
    results_estimated_waiting = fields.Integer(
        'Estimated number of days for results')
    results_estimated_date = fields.Function(fields.Date(
        'Estimated date of result'), 'get_line_field')
    department = fields.Many2One('company.department', 'Department',
        readonly=True)

    @classmethod
    def __setup__(cls):
        super(NotebookLineAllFields, cls).__setup__()
        cls._order.insert(0, ('fraction', 'DESC'))
        cls._order.insert(1, ('analysis', 'ASC'))
        cls._order.insert(2, ('repetition', 'ASC'))

    @staticmethod
    def table_query():
        pool = Pool()
        line = pool.get('lims.notebook.line').__table__()
        detail = pool.get('lims.entry.detail.analysis').__table__()
        service = pool.get('lims.service').__table__()
        fraction = pool.get('lims.fraction').__table__()
        sample = pool.get('lims.sample').__table__()
        entry = pool.get('lims.entry').__table__()
        party = pool.get('party.party').__table__()

        join1 = Join(line, service)
        join1.condition = join1.right.id == line.service
        join2 = Join(join1, fraction)
        join2.condition = join2.right.id == join1.right.fraction
        join3 = Join(join2, sample)
        join3.condition = join3.right.id == join2.right.sample
        join4 = Join(join3, entry)
        join4.condition = join4.right.id == join3.right.entry
        join5 = Join(join4, party)
        join5.condition = join5.right.id == join4.right.party
        join6 = Join(join5, detail)
        join6.condition = join6.right.id == join1.left.analysis_detail

        columns = [
            line.id,
            line.create_uid,
            line.create_date,
            line.write_uid,
            line.write_date,
            line.id.as_('line'),
            service.fraction,
            entry.party,
            party.code.as_('party_code'),
            sample.product_type,
            sample.matrix,
            sample.label,
            fraction.type.as_('fraction_type'),
            sample.date,
            line.analysis,
            line.repetition,
            line.start_date,
            line.end_date,
            line.laboratory,
            line.method,
            line.device,
            line.service,
            line.analysis_origin,
            service.urgent,
            service.priority,
            service.report_date,
            line.initial_concentration,
            line.final_concentration,
            line.initial_unit,
            line.final_unit,
            line.result_modifier,
            line.converted_result_modifier,
            line.result,
            line.converted_result,
            line.detection_limit,
            line.quantification_limit,
            line.dilution_factor,
            line.chromatogram,
            line.comments,
            line.theoretical_concentration,
            line.concentration_level,
            line.decimals,
            line.backup,
            line.reference,
            line.literal_result,
            line.rm_correction_formula,
            line.report,
            line.uncertainty,
            line.verification,
            line.accepted,
            line.acceptance_date,
            line.annulled,
            line.annulment_date,
            line.results_report,
            line.planification,
            detail.confirmation_date,
            line.results_estimated_waiting,
            line.department,
            ]
        where = Literal(True)
        return join6.select(*columns, where=where)

    @classmethod
    def get_line_field(cls, notebook_lines, names):
        result = dict((name, {}) for name in names)
        for nl in notebook_lines:
            for name in names:
                field = getattr(nl.line, name, None)
                if isinstance(field, ModelSQL):
                    result[name][nl.id] = field.id if field else None
                elif isinstance(field, tuple):
                    result[name][nl.id] = [f.id for f in field]
                else:
                    result[name][nl.id] = field
        return result

    @classmethod
    def search_line_field(cls, name, clause):
        return [('line.' + name,) + tuple(clause[1:])]


class NotebookLineLaboratoryProfessional(ModelSQL):
    'Laboratory Notebook Line - Laboratory Professional'
    __name__ = 'lims.notebook.line-laboratory.professional'

    notebook_line = fields.Many2One('lims.notebook.line', 'Notebook Line',
        ondelete='CASCADE', select=True, required=True)
    professional = fields.Many2One('lims.laboratory.professional',
        'Laboratory professional', ondelete='CASCADE', select=True,
        required=True)


class NotebookLineProfessional(ModelSQL, ModelView):
    'Laboratory Notebook Line Professional'
    __name__ = 'lims.notebook.line.professional'

    notebook_line = fields.Many2One('lims.notebook.line', 'Notebook Line',
        ondelete='CASCADE', select=True, required=True)
    professional = fields.Many2One('lims.laboratory.professional',
        'Laboratory professional', required=True)


class NotebookInitialConcentrationCalcStart(ModelView):
    'Initial Concentration Calculation'
    __name__ = 'lims.notebook.initial_concentration_calc.start'


class NotebookInitialConcentrationCalc(Wizard):
    'Initial Concentration Calculation'
    __name__ = 'lims.notebook.initial_concentration_calc'

    start_state = 'ok'
    start = StateView('lims.notebook.initial_concentration_calc.start',
        'lims.lims_notebook_initial_concentration_calc_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Ok', 'ok', 'tryton-ok', default=True),
            ])
    ok = StateTransition()

    def transition_ok(self):
        Notebook = Pool().get('lims.notebook')

        for active_id in Transaction().context['active_ids']:
            notebook = Notebook(active_id)
            if not notebook.lines:
                continue
            self.lines_initial_concentration_calc(notebook.lines)
        return 'end'

    def lines_initial_concentration_calc(self, notebook_lines):
        NotebookLine = Pool().get('lims.notebook.line')

        lines_to_save = []
        for notebook_line in notebook_lines:
            if notebook_line.accepted:
                continue
            ic = notebook_line.initial_concentration
            if not ic:
                continue
            if ic[0] == 'A':
                analysis_code = ic[1:]
                result = self._get_analysis_result(analysis_code,
                    notebook_line.notebook)
                if result is not None:
                    notebook_line.initial_concentration = str(result)
                    lines_to_save.append(notebook_line)
            elif ic[0] == 'R':
                analysis_code = ic[1:]
                result = self._get_relation_result(analysis_code,
                    notebook_line.notebook)
                if result is not None:
                    notebook_line.initial_concentration = str(result)
                    lines_to_save.append(notebook_line)
            else:
                continue
        if lines_to_save:
            NotebookLine.save(lines_to_save)

    def _get_analysis_result(self, analysis_code, notebook, round_=False):
        NotebookLine = Pool().get('lims.notebook.line')

        with Transaction().set_user(0):
            notebook_lines = NotebookLine.search([
                ('notebook', '=', notebook.id),
                ('analysis.code', '=', analysis_code),
                ('annulment_date', '=', None),
                ])
        if not notebook_lines:
            return None

        try:
            res = float(notebook_lines[0].result)
        except (TypeError, ValueError):
            return None
        if not round_:
            return res
        return round(res, notebook_lines[0].decimals)

    def _get_relation_result(self, analysis_code, notebook, round_=False):
        pool = Pool()
        Analysis = pool.get('lims.analysis')
        NotebookLine = pool.get('lims.notebook.line')

        internal_relations = Analysis.search([
            ('code', '=', analysis_code),
            ])
        if not internal_relations:
            return None
        formula = internal_relations[0].result_formula
        if not formula:
            return None
        for i in (' ', '\t', '\n', '\r'):
            formula = formula.replace(i, '')
        variables = self._get_variables(formula, notebook)
        if not variables:
            return None

        parser = FormulaParser(formula, variables)
        value = parser.getValue()

        if int(value) == value:
            res = int(value)
        else:
            epsilon = 0.0000000001
            if int(value + epsilon) != int(value):
                res = int(value + epsilon)
            elif int(value - epsilon) != int(value):
                res = int(value)
            else:
                res = float(value)
        if not round_:
            return res

        with Transaction().set_user(0):
            notebook_lines = NotebookLine.search([
                ('notebook', '=', notebook.id),
                ('analysis.code', '=', analysis_code),
                ('repetition', '=', 0),
                ('annulment_date', '=', None),
                ])
        if not notebook_lines:
            return None
        return round(res, notebook_lines[0].decimals)

    def _get_variables(self, formula, notebook):
        VolumeConversion = Pool().get('lims.volume.conversion')

        variables = {}
        for prefix in ('A', 'D', 'T', 'Y', 'R'):
            while True:
                idx = formula.find(prefix)
                if idx >= 0:
                    var = formula[idx:idx + 5]
                    variables[var] = None
                    formula = formula.replace(var, '_')
                else:
                    break
        for var in variables.keys():
            if var[0] == 'A':
                analysis_code = var[1:]
                result = self._get_analysis_result(analysis_code, notebook,
                    round_=True)
                if result is not None:
                    variables[var] = result
            elif var[0] == 'D':
                analysis_code = var[1:]
                result = self._get_analysis_result(analysis_code, notebook,
                    round_=True)
                if result is not None:
                    result = VolumeConversion.brixToDensity(result)
                    if result is not None:
                        variables[var] = result
            elif var[0] == 'T':
                analysis_code = var[1:]
                result = self._get_analysis_result(analysis_code, notebook,
                    round_=True)
                if result is not None:
                    result = VolumeConversion.brixToSolubleSolids(result)
                    if result is not None:
                        variables[var] = result
            elif var[0] == 'R':
                analysis_code = var[1:]
                result = self._get_relation_result(analysis_code, notebook,
                    round_=True)
                if result is not None:
                    result = VolumeConversion.brixToSolubleSolids(result)
                    if result is not None:
                        variables[var] = result
            elif var[0] == 'Y':
                analysis_code = var[1:]
                result = self._get_relation_result(analysis_code, notebook,
                    round_=True)
                if result is not None:
                    result = VolumeConversion.brixToDensity(result)
                    if result is not None:
                        variables[var] = result
        for var in variables.values():
            if var is None:
                return None
        return variables


class NotebookLineInitialConcentrationCalc(NotebookInitialConcentrationCalc):
    'Initial Concentration Calculation'
    __name__ = 'lims.notebook_line.initial_concentration_calc'

    def transition_ok(self):
        NotebookLine = Pool().get('lims.notebook.line')

        notebook_lines = NotebookLine.browse(
            Transaction().context['active_ids'])
        if not notebook_lines:
            return 'end'

        self.lines_initial_concentration_calc(notebook_lines)
        return 'end'


class NotebookResultsConversionStart(ModelView):
    'Results Conversion'
    __name__ = 'lims.notebook.results_conversion.start'


class NotebookResultsConversion(Wizard):
    'Results Conversion'
    __name__ = 'lims.notebook.results_conversion'

    start_state = 'ok'
    start = StateView('lims.notebook.results_conversion.start',
        'lims.lims_notebook_results_conversion_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Ok', 'ok', 'tryton-ok', default=True),
            ])
    ok = StateTransition()

    def transition_ok(self):
        Notebook = Pool().get('lims.notebook')

        for active_id in Transaction().context['active_ids']:
            notebook = Notebook(active_id)
            if not notebook.lines:
                continue
            self.lines_results_conversion(notebook.lines)
        return 'end'

    def lines_results_conversion(self, notebook_lines):
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        UomConversion = pool.get('lims.uom.conversion')
        VolumeConversion = pool.get('lims.volume.conversion')

        lines_to_save = []
        for notebook_line in notebook_lines:
            if notebook_line.accepted:
                continue
            if (notebook_line.converted_result or not notebook_line.result or
                    notebook_line.result_modifier != 'eq'):
                continue
            iu = notebook_line.initial_unit
            if not iu:
                continue
            fu = notebook_line.final_unit
            if not fu:
                continue
            try:
                ic = float(notebook_line.initial_concentration)
            except (TypeError, ValueError):
                continue
            try:
                fc = float(notebook_line.final_concentration)
            except (TypeError, ValueError):
                continue
            try:
                result = float(notebook_line.result)
            except (TypeError, ValueError):
                continue

            if (iu == fu and ic == fc):
                converted_result = result
                notebook_line.converted_result = str(converted_result)
                notebook_line.converted_result_modifier = 'eq'
                lines_to_save.append(notebook_line)
            elif (iu != fu and ic == fc):
                formula = UomConversion.get_conversion_formula(iu, fu)
                if not formula:
                    continue
                variables = self._get_variables(formula, notebook_line)
                parser = FormulaParser(formula, variables)
                formula_result = parser.getValue()

                converted_result = result * formula_result
                notebook_line.converted_result = str(converted_result)
                notebook_line.converted_result_modifier = 'eq'
                lines_to_save.append(notebook_line)
            elif (iu == fu and ic != fc):
                converted_result = result * (fc / ic)
                notebook_line.converted_result = str(converted_result)
                notebook_line.converted_result_modifier = 'eq'
                lines_to_save.append(notebook_line)
            else:
                formula = None
                conversions = UomConversion.search([
                    ('initial_uom', '=', iu),
                    ('final_uom', '=', fu),
                    ])
                if conversions:
                    formula = conversions[0].conversion_formula
                if not formula:
                    continue

                initial_uom_volume = conversions[0].initial_uom_volume
                final_uom_volume = conversions[0].final_uom_volume
                variables = self._get_variables(formula, notebook_line,
                    initial_uom_volume, final_uom_volume)
                parser = FormulaParser(formula, variables)
                formula_result = parser.getValue()

                if initial_uom_volume and final_uom_volume:
                    d_ic = VolumeConversion.brixToDensity(ic)
                    d_fc = VolumeConversion.brixToDensity(fc)
                    converted_result = (result * (fc / ic) * (d_fc / d_ic) *
                        formula_result)
                    notebook_line.converted_result = str(converted_result)
                    notebook_line.converted_result_modifier = 'eq'
                    lines_to_save.append(notebook_line)
                else:
                    converted_result = result * (fc / ic) * formula_result
                    notebook_line.converted_result = str(converted_result)
                    notebook_line.converted_result_modifier = 'eq'
                    lines_to_save.append(notebook_line)
        if lines_to_save:
            NotebookLine.save(lines_to_save)

    def _get_variables(self, formula, notebook_line,
            initial_uom_volume=False, final_uom_volume=False):
        VolumeConversion = Pool().get('lims.volume.conversion')

        variables = {}
        for var in ('DI',):
            while True:
                idx = formula.find(var)
                if idx >= 0:
                    variables[var] = 0
                    formula = formula.replace(var, '_')
                else:
                    break
        for var in variables.keys():
            if var == 'DI':
                if initial_uom_volume:
                    c = float(notebook_line.initial_concentration)
                    result = VolumeConversion.brixToDensity(c)
                    if result:
                        variables[var] = result
                elif final_uom_volume:
                    c = float(notebook_line.final_concentration)
                    result = VolumeConversion.brixToDensity(c)
                    if result:
                        variables[var] = result
        return variables


class NotebookLineResultsConversion(NotebookResultsConversion):
    'Results Conversion'
    __name__ = 'lims.notebook_line.results_conversion'

    def transition_ok(self):
        NotebookLine = Pool().get('lims.notebook.line')

        notebook_lines = NotebookLine.browse(
            Transaction().context['active_ids'])
        if not notebook_lines:
            return 'end'

        self.lines_results_conversion(notebook_lines)
        return 'end'


class NotebookLimitsValidationStart(ModelView):
    'Limits Validation'
    __name__ = 'lims.notebook.limits_validation.start'


class NotebookLimitsValidation(Wizard):
    'Limits Validation'
    __name__ = 'lims.notebook.limits_validation'

    start_state = 'ok'
    start = StateView('lims.notebook.limits_validation.start',
        'lims.lims_notebook_limits_validation_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Ok', 'ok', 'tryton-ok', default=True),
            ])
    ok = StateTransition()

    def transition_ok(self):
        Notebook = Pool().get('lims.notebook')

        for active_id in Transaction().context['active_ids']:
            notebook = Notebook(active_id)
            if not notebook.lines:
                continue
            self.lines_limits_validation(notebook.lines)
        return 'end'

    def lines_limits_validation(self, notebook_lines):
        NotebookLine = Pool().get('lims.notebook.line')

        lines_to_save = []
        for notebook_line in notebook_lines:
            if notebook_line.accepted:
                continue
            try:
                dl = float(notebook_line.detection_limit)
                ql = float(notebook_line.quantification_limit)
            except (TypeError, ValueError):
                continue

            if (notebook_line.result and (
                    notebook_line.check_result_limits or
                    not notebook_line.converted_result)):
                if notebook_line.result_modifier != 'eq':
                    continue
                try:
                    value = float(notebook_line.result)
                except ValueError:
                    continue
                if dl < value and value < ql:
                    notebook_line.result = str(ql)
                    notebook_line.result_modifier = 'low'
                    notebook_line.converted_result = None
                    notebook_line.converted_result_modifier = 'eq'
                    notebook_line.rm_correction_formula = None
                elif value < dl:
                    notebook_line.result = None
                    notebook_line.result_modifier = 'nd'
                    notebook_line.converted_result = None
                    notebook_line.converted_result_modifier = 'eq'
                    notebook_line.rm_correction_formula = None
                elif value == dl:
                    notebook_line.result = str(ql)
                    notebook_line.result_modifier = 'low'
                    notebook_line.converted_result = None
                    notebook_line.converted_result_modifier = 'eq'
                    notebook_line.rm_correction_formula = None
                notebook_line.backup = str(value)
                lines_to_save.append(notebook_line)

            elif notebook_line.converted_result:
                if notebook_line.converted_result_modifier != 'eq':
                    continue
                try:
                    value = float(notebook_line.converted_result)
                except ValueError:
                    continue
                if dl < value and value < ql:
                    notebook_line.converted_result = str(ql)
                    notebook_line.converted_result_modifier = 'low'
                    notebook_line.result_modifier = 'ni'
                    notebook_line.rm_correction_formula = None
                elif value < dl:
                    notebook_line.converted_result = None
                    notebook_line.converted_result_modifier = 'nd'
                    notebook_line.result_modifier = 'ni'
                    notebook_line.rm_correction_formula = None
                elif value == dl:
                    notebook_line.converted_result = str(ql)
                    notebook_line.converted_result_modifier = 'low'
                    notebook_line.result_modifier = 'ni'
                    notebook_line.rm_correction_formula = None
                notebook_line.backup = str(value)
                lines_to_save.append(notebook_line)

            else:
                continue

        if lines_to_save:
            NotebookLine.save(lines_to_save)


class NotebookLineLimitsValidation(NotebookLimitsValidation):
    'Limits Validation'
    __name__ = 'lims.notebook_line.limits_validation'

    def transition_ok(self):
        NotebookLine = Pool().get('lims.notebook.line')

        notebook_lines = NotebookLine.browse(
            Transaction().context['active_ids'])
        if not notebook_lines:
            return 'end'

        self.lines_limits_validation(notebook_lines)
        return 'end'


class NotebookInternalRelationsCalc1Start(ModelView):
    'Internal Relations Calculation'
    __name__ = 'lims.notebook.internal_relations_calc_1.start'


class NotebookInternalRelationsCalc1Relation(ModelSQL):
    'Internal Relations Calculation'
    __name__ = 'lims.notebook.internal_relations_calc_1.relation'
    _table = 'lims_notebook_internal_relations_c_1_rel'

    notebook = fields.Many2One('lims.notebook', 'Laboratory notebook')
    internal_relation = fields.Many2One('lims.analysis', 'Internal relation')
    variables = fields.One2Many(
        'lims.notebook.internal_relations_calc_1.variable', 'relation',
        'Variables')
    session_id = fields.Integer('Session ID')

    @classmethod
    def __register__(cls, module_name):
        super(NotebookInternalRelationsCalc1Relation,
            cls).__register__(module_name)
        cursor = Transaction().connection.cursor()
        cursor.execute('DELETE FROM "' + cls._table + '"')


class NotebookInternalRelationsCalc1Variable(ModelSQL):
    'Formula Variable'
    __name__ = 'lims.notebook.internal_relations_calc_1.variable'

    relation = fields.Many2One(
        'lims.notebook.internal_relations_calc_1.relation', 'Relation',
        ondelete='CASCADE', readonly=True)
    line = fields.Many2One('lims.notebook.line', 'Line')
    analysis = fields.Many2One('lims.analysis', 'Analysis', readonly=True)
    repetition = fields.Integer('Repetition', readonly=True)
    use = fields.Boolean('Use')


class NotebookInternalRelationsCalc1(Wizard):
    'Internal Relations Calculation'
    __name__ = 'lims.notebook.internal_relations_calc_1'

    start_state = 'search'
    start = StateView('lims.notebook.internal_relations_calc_1.start',
        'lims.lims_notebook_internal_relations_calc_1_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search', 'search', 'tryton-forward', default=True),
            ])
    search = StateTransition()
    confirm = StateTransition()

    def transition_search(self):
        Notebook = Pool().get('lims.notebook')

        notebook = Notebook(Transaction().context['active_id'])
        if not notebook.lines:
            return 'end'

        if self.get_relations(notebook.lines):
            return 'confirm'
        return 'end'

    def get_relations(self, notebook_lines):
        NotebookInternalRelationsCalc1Relation = Pool().get(
            'lims.notebook.internal_relations_calc_1.relation')

        relations = {}
        for notebook_line in notebook_lines:
            if notebook_line.accepted:
                continue
            analysis_code = notebook_line.analysis.code
            if (not analysis_code or notebook_line.analysis.behavior !=
                    'internal_relation'):
                continue
            if notebook_line.result or notebook_line.converted_result:
                continue

            formulas = notebook_line.analysis.result_formula
            formulas += ("+" +
                notebook_line.analysis.converted_result_formula)
            for i in (' ', '\t', '\n', '\r'):
                formulas = formulas.replace(i, '')
            variables = self._get_variables_list(formulas,
                notebook_line.notebook, {})
            if not variables:
                continue
            has_repetition_zero = False
            for var in variables:
                if var['use']:
                    has_repetition_zero = True
            if not has_repetition_zero:
                continue

            relations[notebook_line.analysis.id] = {
                'notebook': notebook_line.notebook.id,
                'internal_relation': notebook_line.analysis.id,
                'variables': [('create', variables)],
                'session_id': self._session_id,
                }
        if relations:
            NotebookInternalRelationsCalc1Relation.create(
                [ir for ir in relations.values()])
            return True
        return False

    def _get_variables_list(self, formula, notebook, analysis={}):
        pool = Pool()
        Analysis = pool.get('lims.analysis')
        NotebookLine = pool.get('lims.notebook.line')

        variables = {}
        for prefix in ('A', 'D', 'T', 'Y', 'R'):
            while True:
                idx = formula.find(prefix)
                if idx >= 0:
                    var = formula[idx:idx + 5]
                    variables[var] = None
                    formula = formula.replace(var, '_')
                else:
                    break
        for var in variables.keys():
            if var[0] in ('A', 'D', 'T'):
                analysis_code = var[1:]
                with Transaction().set_user(0):
                    notebook_lines = NotebookLine.search([
                        ('notebook', '=', notebook.id),
                        ('analysis.code', '=', analysis_code),
                        ('annulment_date', '=', None),
                        ])
                if not notebook_lines:
                    continue
                for nl in notebook_lines:
                    analysis[nl.id] = {
                        'line': nl.id,
                        'analysis': nl.analysis.id,
                        'repetition': nl.repetition,
                        'use': True if nl.repetition == 0 else False,
                        }
            elif var[0] in ('Y', 'R'):
                analysis_code = var[1:]
                internal_relations = Analysis.search([
                    ('code', '=', analysis_code),
                    ])
                if not internal_relations:
                    continue
                more_formulas = internal_relations[0].converted_result_formula
                more_formulas += "+" + internal_relations[0].result_formula
                for i in (' ', '\t', '\n', '\r'):
                    more_formulas = more_formulas.replace(i, '')
                self._get_variables_list(more_formulas, notebook, analysis)

        return [v for v in analysis.values()]

    def transition_confirm(self):
        pool = Pool()
        Date = pool.get('ir.date')
        NotebookInternalRelationsCalc1Relation = pool.get(
            'lims.notebook.internal_relations_calc_1.relation')
        NotebookLine = pool.get('lims.notebook.line')

        date = Date.today()

        relations = NotebookInternalRelationsCalc1Relation.search([
            ('session_id', '=', self._session_id),
            ])
        notebook_lines_to_save = []
        for relation in relations:
            notebook_lines = NotebookLine.search([
                ('notebook', '=', relation.notebook.id),
                ('analysis', '=', relation.internal_relation.id)
                ])
            if len(notebook_lines) != 1:
                continue

            analysis_code = relation.internal_relation.code
            result = self._get_relation_result(analysis_code,
                relation.notebook, analysis_code)
            converted_result = self._get_relation_result(analysis_code,
                relation.notebook, analysis_code, converted=True)

            notebook_line = notebook_lines[0]
            if result is not None:
                notebook_line.result = str(result)
            if converted_result is not None:
                notebook_line.converted_result = str(converted_result)
            if result is not None or converted_result is not None:
                notebook_line.start_date = date
                notebook_line.end_date = date
                notebook_lines_to_save.append(notebook_line)
        NotebookLine.save(notebook_lines_to_save)
        return 'end'

    def _get_analysis_result(self, analysis_code, notebook, relation_code,
            converted=False):
        NotebookInternalRelationsCalc1Variable = Pool().get(
            'lims.notebook.internal_relations_calc_1.variable')

        variables = NotebookInternalRelationsCalc1Variable.search([
            ('relation.session_id', '=', self._session_id),
            ('relation.notebook', '=', notebook.id),
            ('relation.internal_relation.code', '=', relation_code),
            ('analysis.code', '=', analysis_code),
            ('use', '=', True),
            ])
        if not variables:
            return None

        notebook_line = variables[0].line
        if not notebook_line:
            return None

        try:
            if converted:
                res = float(notebook_line.converted_result)
            else:
                res = float(notebook_line.result)
        except (TypeError, ValueError):
            return None
        return round(res, notebook_line.decimals)

    def _get_relation_result(self, analysis_code, notebook, relation_code,
            converted=False, round_=False):
        pool = Pool()
        Analysis = pool.get('lims.analysis')
        NotebookLine = pool.get('lims.notebook.line')

        internal_relations = Analysis.search([
            ('code', '=', analysis_code),
            ])
        if not internal_relations:
            return None
        if converted:
            formula = internal_relations[0].converted_result_formula
        else:
            formula = internal_relations[0].result_formula
        if not formula:
            return None
        for i in (' ', '\t', '\n', '\r'):
            formula = formula.replace(i, '')
        variables = self._get_variables(formula, notebook, relation_code,
            converted)
        if not variables:
            return None

        parser = FormulaParser(formula, variables)
        value = parser.getValue()

        if int(value) == value:
            res = int(value)
        else:
            epsilon = 0.0000000001
            if int(value + epsilon) != int(value):
                res = int(value + epsilon)
            elif int(value - epsilon) != int(value):
                res = int(value)
            else:
                res = float(value)
        if not round_:
            return res

        with Transaction().set_user(0):
            notebook_lines = NotebookLine.search([
                ('notebook', '=', notebook.id),
                ('analysis.code', '=', analysis_code),
                ('repetition', '=', 0),
                ('annulment_date', '=', None),
                ])
        if not notebook_lines:
            return None
        return round(res, notebook_lines[0].decimals)

    def _get_variables(self, formula, notebook, relation_code,
            converted=False):
        VolumeConversion = Pool().get('lims.volume.conversion')

        variables = {}
        for prefix in ('A', 'D', 'T', 'Y', 'R'):
            while True:
                idx = formula.find(prefix)
                if idx >= 0:
                    var = formula[idx:idx + 5]
                    variables[var] = None
                    formula = formula.replace(var, '_')
                else:
                    break
        for var in variables.keys():
            if var[0] == 'A':
                analysis_code = var[1:]
                result = self._get_analysis_result(analysis_code, notebook,
                    relation_code, converted)
                if result is not None:
                    variables[var] = result
            elif var[0] == 'D':
                analysis_code = var[1:]
                result = self._get_analysis_result(analysis_code, notebook,
                    relation_code, converted)
                if result is not None:
                    result = VolumeConversion.brixToDensity(result)
                    if result is not None:
                        variables[var] = result
            elif var[0] == 'T':
                analysis_code = var[1:]
                result = self._get_analysis_result(analysis_code, notebook,
                    relation_code, converted)
                if result is not None:
                    result = VolumeConversion.brixToSolubleSolids(result)
                    if result is not None:
                        variables[var] = result
            elif var[0] == 'R':
                analysis_code = var[1:]
                result = self._get_relation_result(analysis_code, notebook,
                    relation_code, converted, round_=True)
                if result is not None:
                    result = VolumeConversion.brixToSolubleSolids(result)
                    if result is not None:
                        variables[var] = result
            elif var[0] == 'Y':
                analysis_code = var[1:]
                result = self._get_relation_result(analysis_code, notebook,
                    relation_code, converted, round_=True)
                if result is not None:
                    result = VolumeConversion.brixToDensity(result)
                    if result is not None:
                        variables[var] = result
        for var in variables.values():
            if var is None:
                return None
        return variables


class NotebookLineInternalRelationsCalc1(NotebookInternalRelationsCalc1):
    'Internal Relations Calculation'
    __name__ = 'lims.notebook_line.internal_relations_calc_1'

    def transition_search(self):
        NotebookLine = Pool().get('lims.notebook.line')

        notebook_lines = NotebookLine.browse(
            Transaction().context['active_ids'])
        if not notebook_lines:
            return 'end'

        if self.get_relations(notebook_lines):
            return 'confirm'
        return 'end'


class NotebookInternalRelationsCalc2Start(ModelView):
    'Internal Relations Calculation'
    __name__ = 'lims.notebook.internal_relations_calc_2.start'


class NotebookInternalRelationsCalc2Result(ModelView):
    'Internal Relations Calculation'
    __name__ = 'lims.notebook.internal_relations_calc_2.result'

    relations = fields.Many2Many(
        'lims.notebook.internal_relations_calc_2.relation', None, None,
        'Relation')
    total = fields.Integer('Total')
    index = fields.Integer('Index')


class NotebookInternalRelationsCalc2Relation(ModelSQL, ModelView):
    'Internal Relations Calculation'
    __name__ = 'lims.notebook.internal_relations_calc_2.relation'
    _table = 'lims_notebook_internal_relations_c_2_rel'

    notebook = fields.Many2One('lims.notebook', 'Laboratory notebook')
    internal_relation = fields.Many2One('lims.analysis', 'Internal relation')
    variables = fields.One2Many(
        'lims.notebook.internal_relations_calc_2.variable', 'relation',
        'Variables')
    session_id = fields.Integer('Session ID')

    @classmethod
    def __register__(cls, module_name):
        super(NotebookInternalRelationsCalc2Relation,
            cls).__register__(module_name)
        cursor = Transaction().connection.cursor()
        cursor.execute('DELETE FROM "' + cls._table + '"')


class NotebookInternalRelationsCalc2Variable(ModelSQL, ModelView):
    'Formula Variable'
    __name__ = 'lims.notebook.internal_relations_calc_2.variable'

    relation = fields.Many2One(
        'lims.notebook.internal_relations_calc_2.relation', 'Relation',
        ondelete='CASCADE', readonly=True)
    line = fields.Many2One('lims.notebook.line', 'Line')
    analysis = fields.Many2One('lims.analysis', 'Analysis', readonly=True)
    repetition = fields.Integer('Repetition', readonly=True)
    result_modifier = fields.Function(fields.Selection([
        ('eq', '='),
        ('low', '<'),
        ('nd', 'nd'),
        ('na', 'na'),
        ('pos', 'Positive'),
        ('neg', 'Negative'),
        ('ni', 'ni'),
        ('abs', 'Absence'),
        ('pre', 'Presence'),
        ], 'Result modifier'), 'get_line_field')
    result = fields.Function(fields.Char('Result'), 'get_line_field')
    initial_unit = fields.Function(fields.Many2One('product.uom',
        'Initial unit'), 'get_line_field')
    initial_concentration = fields.Function(fields.Char(
        'Initial concentration'), 'get_line_field')
    converted_result_modifier = fields.Function(fields.Selection([
        ('eq', '='),
        ('low', '<'),
        ('nd', 'nd'),
        ('na', 'na'),
        ('pos', 'Positive'),
        ('neg', 'Negative'),
        ('ni', 'ni'),
        ], 'Converted result modifier'), 'get_line_field')
    converted_result = fields.Function(fields.Char('Converted result'),
        'get_line_field')
    final_unit = fields.Function(fields.Many2One('product.uom', 'Final unit'),
        'get_line_field')
    final_concentration = fields.Function(fields.Char('Final concentration'),
        'get_line_field')
    use = fields.Boolean('Use')

    @classmethod
    def __setup__(cls):
        super(NotebookInternalRelationsCalc2Variable, cls).__setup__()
        cls._order.insert(0, ('relation', 'ASC'))
        cls._order.insert(1, ('analysis', 'ASC'))
        cls._order.insert(2, ('repetition', 'ASC'))

    @classmethod
    def get_line_field(cls, variables, names):
        result = {}
        for name in names:
            result[name] = {}
            if name in ('initial_unit', 'final_unit'):
                for v in variables:
                    field = getattr(v.line, name, None)
                    result[name][v.id] = field.id if field else None
            else:
                for v in variables:
                    result[name][v.id] = getattr(v.line, name, None)
        return result


class NotebookInternalRelationsCalc2Process(ModelView):
    'Internal Relations Calculation'
    __name__ = 'lims.notebook.internal_relations_calc_2.process'

    notebook = fields.Many2One('lims.notebook', 'Laboratory notebook',
        readonly=True)
    internal_relation = fields.Many2One('lims.analysis', 'Internal relation',
        readonly=True)
    variables = fields.One2Many(
        'lims.notebook.internal_relations_calc_2.variable', None,
        'Variables')


class NotebookInternalRelationsCalc2(Wizard):
    'Internal Relations Calculation'
    __name__ = 'lims.notebook.internal_relations_calc_2'

    start_state = 'search'
    start = StateView('lims.notebook.internal_relations_calc_2.start',
        'lims.lims_notebook_internal_relations_calc_2_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search', 'search', 'tryton-forward', default=True),
            ])
    search = StateTransition()
    result = StateView('lims.notebook.internal_relations_calc_2.result',
        'lims.lims_notebook_internal_relations_calc_2_result_view_form', [])
    next_ = StateTransition()
    process = StateView('lims.notebook.internal_relations_calc_2.process',
        'lims.lims_notebook_internal_relations_calc_2_process_view_form', [
            Button('Next', 'check_variables', 'tryton-forward', default=True),
            ])
    check_variables = StateTransition()
    confirm = StateTransition()

    def transition_search(self):
        Notebook = Pool().get('lims.notebook')

        for active_id in Transaction().context['active_ids']:
            notebook = Notebook(active_id)
            if not notebook.lines:
                continue

            if self.get_relations(notebook.lines):
                return 'next_'
        return 'end'

    def get_relations(self, notebook_lines):
        NotebookInternalRelationsCalc2Relation = Pool().get(
            'lims.notebook.internal_relations_calc_2.relation')

        relations = {}
        for notebook_line in notebook_lines:
            if notebook_line.accepted:
                continue
            analysis_code = notebook_line.analysis.code
            if (not analysis_code or notebook_line.analysis.behavior !=
                    'internal_relation'):
                continue
            if notebook_line.result or notebook_line.converted_result:
                continue

            formulas = notebook_line.analysis.result_formula
            formulas += ("+" +
                notebook_line.analysis.converted_result_formula)
            for i in (' ', '\t', '\n', '\r'):
                formulas = formulas.replace(i, '')
            variables = self._get_variables_list(formulas,
                notebook_line.notebook, {})
            if not variables:
                continue
            has_repetitions = False
            for var in variables:
                if var['repetition'] > 0:
                    has_repetitions = True
            if not has_repetitions:
                continue

            relations[notebook_line.analysis.id] = {
                'notebook': notebook_line.notebook.id,
                'internal_relation': notebook_line.analysis.id,
                'variables': [('create', variables)],
                'session_id': self._session_id,
                }

        if relations:
            res_lines = NotebookInternalRelationsCalc2Relation.create(
                [ir for ir in relations.values()])
            self.result.relations = res_lines
            self.result.total = len(self.result.relations)
            self.result.index = 0
            return True
        return False

    def transition_next_(self):
        if self.result.index < self.result.total:
            relation = self.result.relations[self.result.index]
            self.process.notebook = relation.notebook.id
            self.process.internal_relation = relation.internal_relation.id
            self.process.variables = None
            self.result.index += 1
            return 'process'
        return 'confirm'

    def default_process(self, fields):
        NotebookInternalRelationsCalc2Variable = Pool().get(
            'lims.notebook.internal_relations_calc_2.variable')

        if not self.process.internal_relation:
            return {}

        default = {}
        default['notebook'] = self.process.notebook.id
        default['internal_relation'] = self.process.internal_relation.id
        if self.process.variables:
            default['variables'] = [v.id for v in self.process.variables]
        else:
            variables = NotebookInternalRelationsCalc2Variable.search([
                ('relation.session_id', '=', self._session_id),
                ('relation.notebook', '=', self.process.notebook.id),
                ('relation.internal_relation', '=',
                    self.process.internal_relation.id),
                ])
            if variables:
                default['variables'] = [v.id for v in variables]
        return default

    def _get_variables_list(self, formula, notebook, analysis={}):
        pool = Pool()
        Analysis = pool.get('lims.analysis')
        NotebookLine = pool.get('lims.notebook.line')

        variables = {}
        for prefix in ('A', 'D', 'T', 'Y', 'R'):
            while True:
                idx = formula.find(prefix)
                if idx >= 0:
                    var = formula[idx:idx + 5]
                    variables[var] = None
                    formula = formula.replace(var, '_')
                else:
                    break
        for var in variables.keys():
            if var[0] in ('A', 'D', 'T'):
                analysis_code = var[1:]
                with Transaction().set_user(0):
                    notebook_lines = NotebookLine.search([
                        ('notebook', '=', notebook.id),
                        ('analysis.code', '=', analysis_code),
                        ('annulment_date', '=', None),
                        ])
                if not notebook_lines:
                    continue
                for nl in notebook_lines:
                    analysis[nl.id] = {
                        'line': nl.id,
                        'analysis': nl.analysis.id,
                        'repetition': nl.repetition,
                        'use': True if nl.repetition == 0 else False,
                        }
            elif var[0] in ('R', 'Y'):
                analysis_code = var[1:]
                internal_relations = Analysis.search([
                    ('code', '=', analysis_code),
                    ])
                if not internal_relations:
                    continue
                more_formulas = internal_relations[0].converted_result_formula
                more_formulas += "+" + internal_relations[0].result_formula
                for i in (' ', '\t', '\n', '\r'):
                    more_formulas = more_formulas.replace(i, '')
                self._get_variables_list(more_formulas, notebook, analysis)

        return [v for v in analysis.values()]

    def transition_check_variables(self):
        variables = {}
        for var in self.process.variables:
            analysis_code = var.analysis.code
            if analysis_code not in variables:
                variables[analysis_code] = False
            if var.use:
                if variables[analysis_code]:
                    variables[analysis_code] = False
                else:
                    variables[analysis_code] = True
            var.save()

        for var in variables.values():
            if not var:
                return 'process'
        return 'next_'

    def transition_confirm(self):
        pool = Pool()
        Date = pool.get('ir.date')
        NotebookInternalRelationsCalc2Relation = pool.get(
            'lims.notebook.internal_relations_calc_2.relation')
        NotebookLine = pool.get('lims.notebook.line')

        date = Date.today()

        relations = NotebookInternalRelationsCalc2Relation.search([
            ('session_id', '=', self._session_id),
            ])
        notebook_lines_to_save = []
        for relation in relations:
            notebook_lines = NotebookLine.search([
                ('notebook', '=', relation.notebook.id),
                ('analysis', '=', relation.internal_relation.id)
                ])
            if len(notebook_lines) != 1:
                continue

            analysis_code = relation.internal_relation.code
            result = self._get_relation_result(analysis_code,
                relation.notebook, analysis_code)
            converted_result = self._get_relation_result(analysis_code,
                relation.notebook, analysis_code, converted=True)

            notebook_line = notebook_lines[0]
            if result is not None:
                notebook_line.result = str(result)
            if converted_result is not None:
                notebook_line.converted_result = str(converted_result)
            if result is not None or converted_result is not None:
                notebook_line.start_date = date
                notebook_line.end_date = date
                notebook_lines_to_save.append(notebook_line)
        NotebookLine.save(notebook_lines_to_save)

        return 'end'

    def _get_analysis_result(self, analysis_code, notebook, relation_code,
            converted=False):
        NotebookInternalRelationsCalc2Variable = Pool().get(
            'lims.notebook.internal_relations_calc_2.variable')

        variables = NotebookInternalRelationsCalc2Variable.search([
            ('relation.session_id', '=', self._session_id),
            ('relation.notebook', '=', notebook.id),
            ('relation.internal_relation.code', '=', relation_code),
            ('analysis.code', '=', analysis_code),
            ('use', '=', True),
            ])
        if not variables:
            return None

        notebook_line = variables[0].line
        if not notebook_line:
            return None

        try:
            if converted:
                res = float(notebook_line.converted_result)
            else:
                res = float(notebook_line.result)
        except (TypeError, ValueError):
            return None
        return round(res, notebook_line.decimals)

    def _get_relation_result(self, analysis_code, notebook, relation_code,
            converted=False, round_=False):
        pool = Pool()
        Analysis = pool.get('lims.analysis')
        NotebookLine = pool.get('lims.notebook.line')

        internal_relations = Analysis.search([
            ('code', '=', analysis_code),
            ])
        if not internal_relations:
            return None
        if converted:
            formula = internal_relations[0].converted_result_formula
        else:
            formula = internal_relations[0].result_formula
        if not formula:
            return None
        for i in (' ', '\t', '\n', '\r'):
            formula = formula.replace(i, '')
        variables = self._get_variables(formula, notebook, relation_code,
            converted)
        if not variables:
            return None

        parser = FormulaParser(formula, variables)
        value = parser.getValue()

        if int(value) == value:
            res = int(value)
        else:
            epsilon = 0.0000000001
            if int(value + epsilon) != int(value):
                res = int(value + epsilon)
            elif int(value - epsilon) != int(value):
                res = int(value)
            else:
                res = float(value)
        if not round_:
            return res

        with Transaction().set_user(0):
            notebook_lines = NotebookLine.search([
                ('notebook', '=', notebook.id),
                ('analysis.code', '=', analysis_code),
                ('repetition', '=', 0),
                ('annulment_date', '=', None),
                ])
        if not notebook_lines:
            return None
        return round(res, notebook_lines[0].decimals)

    def _get_variables(self, formula, notebook, relation_code,
            converted=False):
        VolumeConversion = Pool().get('lims.volume.conversion')

        variables = {}
        for prefix in ('A', 'D', 'T', 'Y', 'R'):
            while True:
                idx = formula.find(prefix)
                if idx >= 0:
                    var = formula[idx:idx + 5]
                    variables[var] = None
                    formula = formula.replace(var, '_')
                else:
                    break
        for var in variables.keys():
            if var[0] == 'A':
                analysis_code = var[1:]
                result = self._get_analysis_result(analysis_code, notebook,
                    relation_code, converted)
                if result is not None:
                    variables[var] = result
            elif var[0] == 'D':
                analysis_code = var[1:]
                result = self._get_analysis_result(analysis_code, notebook,
                    relation_code, converted)
                if result is not None:
                    result = VolumeConversion.brixToDensity(result)
                    if result is not None:
                        variables[var] = result
            elif var[0] == 'T':
                analysis_code = var[1:]
                result = self._get_analysis_result(analysis_code, notebook,
                    relation_code, converted)
                if result is not None:
                    result = VolumeConversion.brixToSolubleSolids(result)
                    if result is not None:
                        variables[var] = result
            elif var[0] == 'R':
                analysis_code = var[1:]
                result = self._get_relation_result(analysis_code, notebook,
                    relation_code, converted, round_=True)
                if result is not None:
                    result = VolumeConversion.brixToSolubleSolids(result)
                    if result is not None:
                        variables[var] = result
            elif var[0] == 'Y':
                analysis_code = var[1:]
                result = self._get_relation_result(analysis_code, notebook,
                    relation_code, converted, round_=True)
                if result is not None:
                    result = VolumeConversion.brixToDensity(result)
                    if result is not None:
                        variables[var] = result
        for var in variables.values():
            if var is None:
                return None
        return variables


class NotebookLineInternalRelationsCalc2(NotebookInternalRelationsCalc2):
    'Internal Relations Calculation'
    __name__ = 'lims.notebook_line.internal_relations_calc_2'

    def transition_search(self):
        NotebookLine = Pool().get('lims.notebook.line')

        notebook_lines = NotebookLine.browse(
            Transaction().context['active_ids'])
        if not notebook_lines:
            return 'end'

        if self.get_relations(notebook_lines):
            return 'next_'
        return 'end'


class NotebookLoadResultsFormulaStart(ModelView):
    'Load Results by Formula'
    __name__ = 'lims.notebook.load_results_formula.start'

    analysis = fields.Many2One('lims.analysis', 'Analysis',
        domain=[('state', '=', 'active'), ('formula', '!=', None)])
    method = fields.Many2One('lims.lab.method', 'Method')
    start_date = fields.Date('Start date', required=True)


class NotebookLoadResultsFormulaEmpty(ModelView):
    'Load Results by Formula'
    __name__ = 'lims.notebook.load_results_formula.empty'


class NotebookLoadResultsFormulaResult(ModelView):
    'Load Results by Formula'
    __name__ = 'lims.notebook.load_results_formula.result'

    lines = fields.Many2Many('lims.notebook.load_results_formula.line',
        None, None, 'Lines')
    total = fields.Integer('Total')
    index = fields.Integer('Index')


class NotebookLoadResultsFormulaLine(ModelSQL, ModelView):
    'Load Results by Formula'
    __name__ = 'lims.notebook.load_results_formula.line'

    index = fields.Integer('Index')
    line = fields.Many2One('lims.notebook.line', 'Line')
    session_id = fields.Integer('Session ID')

    @classmethod
    def __register__(cls, module_name):
        super(NotebookLoadResultsFormulaLine, cls).__register__(module_name)
        cursor = Transaction().connection.cursor()
        cursor.execute('DELETE FROM "' + cls._table + '"')


class NotebookLoadResultsFormulaAction(ModelSQL):
    'Load Results by Formula'
    __name__ = 'lims.notebook.load_results_formula.action'

    line = fields.Many2One('lims.notebook.line', 'Line')
    result = fields.Char('Result')
    result_modifier = fields.Selection([
        ('eq', '='),
        ('low', '<'),
        ('nd', 'nd'),
        ('na', 'na'),
        ('pos', 'Positive'),
        ('neg', 'Negative'),
        ('ni', 'ni'),
        ('abs', 'Absence'),
        ('pre', 'Presence'),
        ], 'Result modifier', sort=False)
    end_date = fields.Date('End date')
    professional = fields.Many2One('lims.laboratory.professional',
        'Laboratory professional')
    chromatogram = fields.Char('Chromatogram')
    initial_concentration = fields.Char('Initial concentration')
    comments = fields.Text('Comments')
    formula = fields.Many2One('lims.formula', 'Formula')
    variables = fields.One2Many('lims.notebook.load_results_formula.variable',
        'action', 'Variables')
    session_id = fields.Integer('Session ID')

    @classmethod
    def __register__(cls, module_name):
        super(NotebookLoadResultsFormulaAction,
            cls).__register__(module_name)
        cursor = Transaction().connection.cursor()
        cursor.execute('DELETE FROM "' + cls._table + '"')


class NotebookLoadResultsFormulaProcess(ModelView):
    'Load Results by Formula'
    __name__ = 'lims.notebook.load_results_formula.process'

    line = fields.Many2One('lims.notebook.line', 'Line', readonly=True)
    repetition = fields.Integer('Repetition', readonly=True)
    fraction = fields.Many2One('lims.fraction', 'Fraction', readonly=True)
    product_type = fields.Many2One('lims.product.type', 'Product type',
        readonly=True)
    matrix = fields.Many2One('lims.matrix', 'Matrix', readonly=True)
    formula = fields.Many2One('lims.formula', 'Formula', readonly=True)
    formula_formula = fields.Function(fields.Char('Formula'),
        'on_change_with_formula_formula')
    variables = fields.One2Many('lims.notebook.load_results_formula.variable',
        None, 'Variables')
    result = fields.Char('Result', required=True)
    result_modifier = fields.Selection([
        ('eq', '='),
        ('low', '<'),
        ('nd', 'nd'),
        ('na', 'na'),
        ('pos', 'Positive'),
        ('neg', 'Negative'),
        ('ni', 'ni'),
        ('abs', 'Absence'),
        ('pre', 'Presence'),
        ], 'Result modifier', sort=False, required=True)
    end_date = fields.Date('End date')
    end_date_copy = fields.Boolean('Field copy')
    professional = fields.Many2One('lims.laboratory.professional',
        'Laboratory professional', required=True, readonly=True)
    chromatogram = fields.Char('Chromatogram')
    chromatogram_copy = fields.Boolean('Field copy')
    initial_concentration = fields.Char('Initial concentration')
    initial_concentration_copy = fields.Boolean('Field copy')
    comments = fields.Text('Comments')
    comments_copy = fields.Boolean('Field copy')

    @fields.depends('formula', 'variables')
    def on_change_with_result(self, name=None):
        if not self.formula or not self.variables:
            return None

        formula = self.formula.formula
        variables = {}
        for variable in self.variables:
            if not variable.value:
                return ''
            variables[variable.number] = variable.value

        parser = FormulaParser(formula, variables)
        value = parser.getValue()

        return str(value)

    @fields.depends('formula')
    def on_change_with_formula_formula(self, name=None):
        if self.formula:
            formula = self.formula.formula
            variables = {}
            for variable in self.variables:
                variables[variable.number] = variable.description
            for k, v in variables.items():
                formula = formula.replace(k, v)
            return formula
        return ''


class NotebookLoadResultsFormulaVariable(ModelSQL, ModelView):
    'Formula Variable'
    __name__ = 'lims.notebook.load_results_formula.variable'

    action = fields.Many2One('lims.notebook.load_results_formula.action',
        'Action', ondelete='CASCADE')
    number = fields.Char('Number', readonly=True)
    description = fields.Char('Description', readonly=True)
    value = fields.Char('Value')


class NotebookLoadResultsFormulaBeginning(ModelView):
    'Load Results by Formula'
    __name__ = 'lims.notebook.load_results_formula.beginning'


class NotebookLoadResultsFormulaConfirm(ModelView):
    'Load Results by Formula'
    __name__ = 'lims.notebook.load_results_formula.confirm'


class NotebookLoadResultsFormulaSit1(ModelView):
    'Professionals Control'
    __name__ = 'lims.notebook.load_results_formula.sit1'

    msg = fields.Text('Message')


class NotebookLoadResultsFormulaSit2(ModelView):
    'Professionals Control'
    __name__ = 'lims.notebook.load_results_formula.sit2'

    details = fields.One2Many('lims.notebook.load_results_formula.sit2.detail',
        None, 'Supervisors')


class NotebookLoadResultsFormulaSit2Detail(ModelSQL, ModelView):
    'Supervisor'
    __name__ = 'lims.notebook.load_results_formula.sit2.detail'
    _table = 'lims_notebook_load_results_formula_s2_detail'

    professional = fields.Many2One('lims.laboratory.professional',
        'Professional', readonly=True)
    method = fields.Many2One('lims.lab.method', 'Method', readonly=True)
    supervisor = fields.Many2One('lims.laboratory.professional',
        'Supervisor', depends=['supervisor_domain'],
        domain=[('id', 'in', Eval('supervisor_domain'))])
    supervisor_domain = fields.Function(fields.Many2Many(
        'lims.laboratory.professional', None, None, 'Supervisor domain'),
        'get_supervisor_domain')
    lines = fields.Many2Many(
        'lims.notebook.load_results_formula.sit2.detail.line',
        'load_results', 'notebook_line', 'Lines')
    session_id = fields.Integer('Session ID')

    @classmethod
    def __register__(cls, module_name):
        super(NotebookLoadResultsFormulaSit2Detail,
            cls).__register__(module_name)
        cursor = Transaction().connection.cursor()
        cursor.execute('DELETE FROM "' + cls._table + '"')

    def get_supervisor_domain(self, name=None):
        LabProfessionalMethod = Pool().get('lims.lab.professional.method')

        res = []
        qualifications = LabProfessionalMethod.search([
            ('method', '=', self.method.id),
            ('type', '=', 'analytical'),
            ('state', 'in', ('qualified', 'requalified')),
            ])
        if qualifications:
            res = [q.professional.id for q in qualifications]
        return res


class NotebookLoadResultsFormulaSit2DetailLine(ModelSQL):
    'Notebook Line'
    __name__ = 'lims.notebook.load_results_formula.sit2.detail.line'
    _table = 'lims_notebook_load_results_formula_sit2_d_l'

    load_results = fields.Many2One(
        'lims.notebook.load_results_formula.sit2.detail', 'Load Results',
        ondelete='CASCADE', select=True, required=True)
    notebook_line = fields.Many2One('lims.notebook.line', 'Notebook Line',
        ondelete='CASCADE', select=True, required=True)


class NotebookLoadResultsFormula(Wizard):
    'Load Results by Formula'
    __name__ = 'lims.notebook.load_results_formula'

    start = StateView('lims.notebook.load_results_formula.start',
        'lims.lims_notebook_load_results_formula_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search', 'search', 'tryton-forward', default=True),
            ])
    search = StateTransition()
    empty = StateView('lims.notebook.load_results_formula.empty',
        'lims.lims_notebook_load_results_formula_empty_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search again', 'start', 'tryton-forward', default=True),
            ])
    result = StateView('lims.notebook.load_results_formula.result',
        'lims.lims_notebook_load_results_formula_result_view_form', [])
    next_ = StateTransition()
    prev_ = StateTransition()
    process = StateView('lims.notebook.load_results_formula.process',
        'lims.lims_notebook_load_results_formula_process_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Previous', 'prev_', 'tryton-back'),
            Button('Next', 'next_', 'ttryton-forward', default=True),
            ])
    beginning = StateView('lims.notebook.load_results_formula.beginning',
        'lims.lims_notebook_load_results_formula_beginning_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Next', 'next_', 'tryton-forward', default=True),
            ])
    confirm = StateView('lims.notebook.load_results_formula.confirm',
        'lims.lims_notebook_load_results_formula_confirm_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Previous', 'prev_', 'tryton-back'),
            Button('Confirm', 'check_professional', 'tryton-ok', default=True),
            ])
    check_professional = StateTransition()
    sit1 = StateView('lims.notebook.load_results_formula.sit1',
        'lims.lims_notebook_load_results_formula_sit1_view_form', [
            Button('Cancel', 'end', 'tryton-cancel', default=True),
            ])
    sit2 = StateView('lims.notebook.load_results_formula.sit2',
        'lims.lims_notebook_load_results_formula_sit2_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Confirm', 'sit2_ok', 'tryton-ok', default=True),
            ])
    sit2_ok = StateTransition()
    confirm_ = StateTransition()

    def transition_search(self):
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        NotebookLoadResultsFormulaLine = pool.get(
            'lims.notebook.load_results_formula.line')

        clause = [
            ('start_date', '=', self.start.start_date),
            ('end_date', '=', None),
            ('analysis.formula', '!=', None),
            ]
        if self.start.analysis:
            clause.append(('analysis', '=', self.start.analysis.id))
        if self.start.method:
            clause.append(('method', '=', self.start.method.id))

        lines = NotebookLine.search(clause, order=[
            ('analysis_order', 'ASC'), ('id', 'ASC')])
        if lines:
            res_lines = []
            count = 1
            for line in lines:
                res_line, = NotebookLoadResultsFormulaLine.create([{
                    'session_id': self._session_id,
                    'index': count,
                    'line': line.id,
                    }])
                res_lines.append(res_line.id)
                count += 1

            self.result.lines = res_lines
            self.result.total = len(res_lines)
            self.result.index = 0
            return 'next_'
        return 'empty'

    def transition_next_(self):
        pool = Pool()
        NotebookLoadResultsFormulaAction = pool.get(
            'lims.notebook.load_results_formula.action')
        NotebookLoadResultsFormulaLine = pool.get(
            'lims.notebook.load_results_formula.line')
        LaboratoryProfessional = pool.get('lims.laboratory.professional')

        has_prev = (hasattr(self.process, 'line') and
            getattr(self.process, 'line'))
        if has_prev:
            defaults = {
                'session_id': self._session_id,
                'line': self.process.line.id,
                'result': self.process.result,
                'result_modifier': self.process.result_modifier,
                'end_date': self.process.end_date,
                'professional': self.process.professional.id,
                'chromatogram': self.process.chromatogram,
                'initial_concentration': self.process.initial_concentration,
                'comments': self.process.comments,
                'formula': (self.process.formula.id if
                    self.process.formula else None),
                }
            variables = []
            for var in self.process.variables:
                variables.append({
                    'number': var.number,
                    'description': var.description,
                    'value': var.value,
                    })
            defaults['variables'] = [('create', variables)]

            action = NotebookLoadResultsFormulaAction.search([
                ('session_id', '=', self._session_id),
                ('line', '=', self.process.line.id),
                ])
            if action:
                defaults['variables'] = [(
                    'delete', [v.id for a in action for v in a.variables],
                    )] + defaults['variables']
                NotebookLoadResultsFormulaAction.write(action, defaults)
            else:
                NotebookLoadResultsFormulaAction.create([defaults])

        self.result.index += 1
        if self.result.index <= self.result.total:

            line = NotebookLoadResultsFormulaLine.search([
                ('session_id', '=', self._session_id),
                ('index', '=', self.result.index),
                ])
            self.process.line = line[0].line.id

            action = NotebookLoadResultsFormulaAction.search([
                ('session_id', '=', self._session_id),
                ('line', '=', line[0].line.id),
                ])
            if action:
                self.process.result = action[0].result
                self.process.result_modifier = action[0].result_modifier
                self.process.end_date = action[0].end_date
                self.process.professional = action[0].professional.id
                self.process.chromatogram = action[0].chromatogram
                self.process.initial_concentration = (
                    action[0].initial_concentration)
                self.process.comments = action[0].comments
                self.process.formula = action[0].formula
                self.process.variables = [v.id for v in action[0].variables]
            elif has_prev:
                self.process.result = None
                self.process.result_modifier = 'eq'
                if not self.process.end_date_copy:
                    self.process.end_date = None
                if not self.process.chromatogram_copy:
                    self.process.chromatogram = None
                if not self.process.initial_concentration_copy:
                    self.process.initial_concentration = None
                if not self.process.comments_copy:
                    self.process.comments = None
                self.process.formula = None
                self.process.variables = None
            else:
                professional_id = (
                    LaboratoryProfessional.get_lab_professional())
                self.process.professional = professional_id

            return 'process'
        return 'confirm'

    def transition_prev_(self):
        pool = Pool()
        NotebookLoadResultsFormulaAction = pool.get(
            'lims.notebook.load_results_formula.action')
        NotebookLoadResultsFormulaLine = pool.get(
            'lims.notebook.load_results_formula.line')

        self.result.index -= 1
        if self.result.index >= 1:
            line = NotebookLoadResultsFormulaLine.search([
                ('session_id', '=', self._session_id),
                ('index', '=', self.result.index),
                ])
            self.process.line = line[0].line.id

            action = NotebookLoadResultsFormulaAction.search([
                ('session_id', '=', self._session_id),
                ('line', '=', line[0].line.id),
                ])
            if action:
                self.process.result = action[0].result
                self.process.result_modifier = action[0].result_modifier
                self.process.end_date = action[0].end_date
                self.process.professional = action[0].professional.id
                self.process.chromatogram = action[0].chromatogram
                self.process.initial_concentration = (
                    action[0].initial_concentration)
                self.process.comments = action[0].comments
                self.process.formula = action[0].formula
                self.process.variables = [v.id for v in action[0].variables]
            else:
                self.process.result = None
                self.process.result_modifier = 'eq'
                self.process.end_date = None
                self.process.professional = None
                self.process.chromatogram = None
                self.process.initial_concentration = None
                self.process.comments = None
                self.process.formula = None
                self.process.variables = None

            return 'process'

        self.process.line = None
        return 'beginning'

    def default_process(self, fields):
        if not self.process.line:
            return {}

        default = {}
        default['line'] = self.process.line.id
        default['fraction'] = self.process.line.notebook.fraction.id
        default['repetition'] = self.process.line.repetition
        default['product_type'] = (
            self.process.line.notebook.product_type.id)
        default['matrix'] = self.process.line.notebook.matrix.id

        if (hasattr(self.process, 'formula') and
                getattr(self.process, 'formula')):
            formula = self.process.formula
            default['formula'] = formula.id
            variables = []
            variables_desc = {}
            for var in self.process.variables:
                variables.append({
                    'number': var.number,
                    'description': var.description,
                    'value': var.value,
                    })
                variables_desc[var.number] = var.description
            default['variables'] = variables
            formula_formula = formula.formula
            for k, v in variables_desc.items():
                formula_formula = formula_formula.replace(k, v)
            default['formula_formula'] = formula_formula

            default['result'] = self.process.result
            default['result_modifier'] = self.process.result_modifier

            default['initial_concentration'] = (
                self.process.initial_concentration)
            default['comments'] = self.process.comments
            default['professional'] = self.process.professional.id
            default['end_date'] = self.process.end_date
            default['chromatogram'] = self.process.chromatogram

        else:
            formula = self.process.line.analysis.formula
            if formula:
                default['formula'] = formula.id
                variables = []
                variables_desc = {}
                for var in formula.variables:
                    variables.append({
                        'number': var.number,
                        'description': var.description,
                        'value': var.constant,
                        })
                    variables_desc[var.number] = var.description
                default['variables'] = variables
                formula_formula = formula.formula
                for k, v in variables_desc.items():
                    formula_formula = formula_formula.replace(k, v)
                default['formula_formula'] = formula_formula
            default['result_modifier'] = 'eq'

            for field in ('initial_concentration', 'comments'):
                if (hasattr(self.process, field + '_copy') and
                        getattr(self.process, field + '_copy')):
                    default[field] = getattr(self.process, field)
                    default[field + '_copy'] = getattr(self.process,
                        field + '_copy')
                else:
                    default[field] = getattr(self.process.line, field)
            for field in ('professional',):
                if (hasattr(self.process, field) and
                        getattr(self.process, field)):
                    default[field] = getattr(self.process, field).id
            for field in ('end_date', 'chromatogram'):
                if (hasattr(self.process, field) and
                        getattr(self.process, field)):
                    default[field] = getattr(self.process, field)
            for field in ('end_date_copy', 'chromatogram_copy'):
                if (hasattr(self.process, field) and
                        getattr(self.process, field)):
                    default[field] = getattr(self.process, field)

        return default

    def transition_check_professional(self):
        pool = Pool()
        NotebookLoadResultsFormulaAction = pool.get(
            'lims.notebook.load_results_formula.action')
        LabProfessionalMethod = pool.get('lims.lab.professional.method')
        LaboratoryProfessional = pool.get('lims.laboratory.professional')
        LabMethod = pool.get('lims.lab.method')
        NotebookLoadResultsFormulaSit2Detail = pool.get(
            'lims.notebook.load_results_formula.sit2.detail')

        actions = NotebookLoadResultsFormulaAction.search([
            ('session_id', '=', self._session_id),
            ])

        situations = {}
        prof_lines = {}
        for data in actions:
            key = (data.professional.id, data.line.method.id)
            if key not in situations:
                situations[key] = 0
            if key not in prof_lines:
                prof_lines[key] = []
            prof_lines[key].append(data.line.id)

        situation_1 = []
        for key in situations.keys():
            qualifications = LabProfessionalMethod.search([
                ('professional', '=', key[0]),
                ('method', '=', key[1]),
                ('type', '=', 'analytical'),
                ])
            if not qualifications:
                situations[key] = 1
                situation_1.append(key)
            elif qualifications[0].state == 'training':
                situations[key] = 2
            elif (qualifications[0].state in ('qualified', 'requalified')):
                situations[key] = 3
        if situation_1:
            msg = ''
            for key in situation_1:
                professional = LaboratoryProfessional(key[0])
                method = LabMethod(key[1])
                msg += '%s: %s\n' % (professional.rec_name, method.code)
            self.sit1.msg = msg
            return 'sit1'

        situation_2 = []
        for key, sit in situations.items():
            if sit == 2:
                situation_2.append({
                    'session_id': self._session_id,
                    'professional': key[0],
                    'method': key[1],
                    'lines': [('add', prof_lines[key])],
                    })
        if situation_2:
            details = NotebookLoadResultsFormulaSit2Detail.create(
                situation_2)
            self.sit2.details = details
            return 'sit2'

        return 'confirm_'

    def default_sit1(self, fields):
        defaults = {}
        if self.sit1.msg:
            defaults['msg'] = self.sit1.msg
        return defaults

    def default_sit2(self, fields):
        defaults = {}
        if self.sit2.details:
            defaults['details'] = [d.id for d in self.sit2.details]
        return defaults

    def transition_sit2_ok(self):
        for detail in self.sit2.details:
            if not detail.supervisor:
                return 'sit2'
        return 'confirm_'

    def transition_confirm_(self):
        pool = Pool()
        NotebookLoadResultsFormulaAction = pool.get(
            'lims.notebook.load_results_formula.action')
        NotebookLine = pool.get('lims.notebook.line')
        LabProfessionalMethod = pool.get('lims.lab.professional.method')
        LabProfessionalMethodRequalification = pool.get(
            'lims.lab.professional.method.requalification')
        Date = pool.get('ir.date')

        # Write Results to Notebook lines
        actions = NotebookLoadResultsFormulaAction.search([
            ('session_id', '=', self._session_id),
            ])
        for data in actions:
            notebook_line = NotebookLine(data.line.id)
            if not notebook_line:
                continue
            notebook_line_write = {
                'result': data.result,
                'result_modifier': data.result_modifier,
                'end_date': data.end_date,
                'chromatogram': data.chromatogram,
                'initial_concentration': data.initial_concentration,
                'comments': data.comments,
                'converted_result': None,
                'converted_result_modifier': 'eq',
                'backup': None,
                'verification': None,
                'uncertainty': None,
                }
            if data.result_modifier == 'na':
                notebook_line_write['annulled'] = True
                notebook_line_write['annulment_date'] = datetime.now()
                notebook_line_write['report'] = False
            professionals = [{'professional': data.professional.id}]
            notebook_line_write['professionals'] = (
                [('delete', [p.id for p in notebook_line.professionals])] +
                [('create', professionals)])
            NotebookLine.write([notebook_line], notebook_line_write)

        # Write Supervisors to Notebook lines
        supervisor_lines = {}
        if hasattr(self.sit2, 'details'):
            for detail in self.sit2.details:
                if detail.supervisor.id not in supervisor_lines:
                    supervisor_lines[detail.supervisor.id] = []
                supervisor_lines[detail.supervisor.id].extend([
                    l.id for l in detail.lines])
        for prof_id, lines in supervisor_lines.items():
            notebook_lines = NotebookLine.search([
                ('id', 'in', lines),
                ])
            if notebook_lines:
                professionals = [{'professional': prof_id}]
                notebook_line_write = {
                    'professionals': [('create', professionals)],
                    }
                NotebookLine.write(notebook_lines, notebook_line_write)

        # Write the execution of method
        all_prof = {}
        for data in actions:
            key = (data.professional.id, data.line.method.id)
            if key not in all_prof:
                all_prof[key] = []
        if hasattr(self.sit2, 'details'):
            for detail in self.sit2.details:
                key = (detail.supervisor.id, detail.method.id)
                if key not in all_prof:
                    all_prof[key] = []
                key = (detail.professional.id, detail.method.id)
                if detail.supervisor.id not in all_prof[key]:
                    all_prof[key].append(detail.supervisor.id)

        today = Date.today()
        for key, sup in all_prof.items():
            professional_method, = LabProfessionalMethod.search([
                ('professional', '=', key[0]),
                ('method', '=', key[1]),
                ('type', '=', 'analytical'),
                ])
            if professional_method.state == 'training':
                history = LabProfessionalMethodRequalification.search([
                    ('professional_method', '=', professional_method.id),
                    ('type', '=', 'training'),
                    ])
                if history:
                    prev_supervisors = [s.supervisor.id for s in
                        history[0].supervisors]
                    supervisors = [{'supervisor': s} for s in sup
                        if s not in prev_supervisors]
                    LabProfessionalMethodRequalification.write(history, {
                        'last_execution_date': today,
                        'supervisors': [('create', supervisors)],
                        })
                else:
                    supervisors = [{'supervisor': s} for s in sup]
                    to_create = [{
                        'professional_method': professional_method.id,
                        'type': 'training',
                        'date': today,
                        'last_execution_date': today,
                        'supervisors': [('create', supervisors)],
                        }]
                    LabProfessionalMethodRequalification.create(to_create)

            elif professional_method.state == 'qualified':
                history = LabProfessionalMethodRequalification.search([
                    ('professional_method', '=', professional_method.id),
                    ('type', '=', 'qualification'),
                    ])
                if history:
                    LabProfessionalMethodRequalification.write(history, {
                        'last_execution_date': today,
                        })
                else:
                    to_create = [{
                        'professional_method': professional_method.id,
                        'type': 'qualification',
                        'date': today,
                        'last_execution_date': today,
                        }]
                    LabProfessionalMethodRequalification.create(to_create)

            else:
                history = LabProfessionalMethodRequalification.search([
                    ('professional_method', '=', professional_method.id),
                    ('type', '=', 'requalification'),
                    ])
                if history:
                    LabProfessionalMethodRequalification.write(history, {
                        'last_execution_date': today,
                        })
                else:
                    to_create = [{
                        'professional_method': professional_method.id,
                        'type': 'requalification',
                        'date': today,
                        'last_execution_date': today,
                        }]
                    LabProfessionalMethodRequalification.create(to_create)

        return 'end'


class NotebookLoadResultsManualStart(ModelView):
    'Load Results Manually'
    __name__ = 'lims.notebook.load_results_manual.start'

    method = fields.Many2One('lims.lab.method', 'Method', required=True)
    start_date = fields.Date('Start date', required=True)


class NotebookLoadResultsManualEmpty(ModelView):
    'Load Results Manually'
    __name__ = 'lims.notebook.load_results_manual.empty'


class NotebookLoadResultsManualResult(ModelView):
    'Load Results Manually'
    __name__ = 'lims.notebook.load_results_manual.result'

    method = fields.Many2One('lims.lab.method', 'Method', readonly=True)
    start_date = fields.Date('Start date', readonly=True)
    professional = fields.Many2One('lims.laboratory.professional',
        'Laboratory professional', required=True, readonly=True)
    lines = fields.One2Many('lims.notebook.load_results_manual.line',
        None, 'Lines')


class NotebookLoadResultsManualLine(ModelSQL, ModelView):
    'Load Results Manually'
    __name__ = 'lims.notebook.load_results_manual.line'

    line = fields.Many2One('lims.notebook.line', 'Analysis', readonly=True)
    repetition = fields.Integer('Repetition', readonly=True)
    fraction = fields.Many2One('lims.fraction', 'Fraction', readonly=True)
    result = fields.Char('Result')
    result_modifier = fields.Selection([
        ('eq', '='),
        ('low', '<'),
        ('nd', 'nd'),
        ('na', 'na'),
        ('pos', 'Positive'),
        ('neg', 'Negative'),
        ('ni', 'ni'),
        ('abs', 'Absence'),
        ('pre', 'Presence'),
        ], 'Result modifier', sort=False)
    end_date = fields.Date('End date')
    chromatogram = fields.Char('Chromatogram')
    initial_unit = fields.Many2One('product.uom', 'Initial unit',
        domain=[('category.lims_only_available', '=', True)])
    comments = fields.Text('Comments')
    literal_result = fields.Char('Literal result')
    fraction_type = fields.Many2One('lims.fraction.type', 'Fraction type',
        readonly=True)
    session_id = fields.Integer('Session ID')

    @classmethod
    def __register__(cls, module_name):
        super(NotebookLoadResultsManualLine,
            cls).__register__(module_name)
        cursor = Transaction().connection.cursor()
        cursor.execute('DELETE FROM "' + cls._table + '"')

    @fields.depends('result', 'literal_result', 'result_modifier', 'end_date')
    def on_change_with_end_date(self):
        pool = Pool()
        Date = pool.get('ir.date')
        if self.end_date:
            return self.end_date
        if (self.result or self.literal_result or
                self.result_modifier not in ('eq', 'low')):
            return Date.today()
        return None


class NotebookLoadResultsManualSit1(ModelView):
    'Professionals Control'
    __name__ = 'lims.notebook.load_results_manual.sit1'

    msg = fields.Text('Message')


class NotebookLoadResultsManualSit2(ModelView):
    'Professionals Control'
    __name__ = 'lims.notebook.load_results_manual.sit2'

    supervisor = fields.Many2One('lims.laboratory.professional',
        'Supervisor', depends=['supervisor_domain'],
        domain=[('id', 'in', Eval('supervisor_domain'))], required=True)
    supervisor_domain = fields.Many2Many('lims.laboratory.professional',
        None, None, 'Supervisor domain')
    lines = fields.Many2Many('lims.notebook.line', None, None, 'Lines')


class NotebookLoadResultsManual(Wizard):
    'Load Results Manually'
    __name__ = 'lims.notebook.load_results_manual'

    start = StateView('lims.notebook.load_results_manual.start',
        'lims.lims_notebook_load_results_manual_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search', 'search', 'tryton-forward', default=True),
            ])
    search = StateTransition()
    empty = StateView('lims.notebook.load_results_manual.empty',
        'lims.lims_notebook_load_results_manual_empty_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search again', 'start', 'tryton-forward', default=True),
            ])
    result = StateView('lims.notebook.load_results_manual.result',
        'lims.lims_notebook_load_results_manual_result_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Confirm', 'check_professional', 'tryton-ok', default=True),
            ])
    check_professional = StateTransition()
    sit1 = StateView('lims.notebook.load_results_manual.sit1',
        'lims.lims_notebook_load_results_manual_sit1_view_form', [
            Button('Cancel', 'end', 'tryton-cancel', default=True),
            ])
    sit2 = StateView('lims.notebook.load_results_manual.sit2',
        'lims.lims_notebook_load_results_manual_sit2_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Confirm', 'confirm_', 'tryton-ok', default=True),
            ])
    confirm_ = StateTransition()

    def transition_search(self):
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        LaboratoryProfessional = pool.get('lims.laboratory.professional')
        NotebookLoadResultsManualLine = pool.get(
            'lims.notebook.load_results_manual.line')

        clause = [
            ('end_date', '=', None),
            ('method', '=', self.start.method.id),
            ('start_date', '=', self.start.start_date),
            ]

        lines = NotebookLine.search(clause, order=[
            ('analysis_order', 'ASC'), ('id', 'ASC')])
        if lines:
            res_lines = []
            for line in lines:
                res_line, = NotebookLoadResultsManualLine.create([{
                    'session_id': self._session_id,
                    'line': line.id,
                    'repetition': line.repetition,
                    'result': line.result,
                    'result_modifier': line.result_modifier,
                    'end_date': line.end_date,
                    'chromatogram': line.chromatogram,
                    'initial_unit': (line.initial_unit.id if
                        line.initial_unit else None),
                    'comments': line.comments,
                    'fraction': line.fraction.id,
                    'fraction_type': line.fraction_type.id,
                    'literal_result': line.literal_result,
                    }])
                res_lines.append(res_line.id)

            professional_id = LaboratoryProfessional.get_lab_professional()
            self.result.method = self.start.method.id
            self.result.start_date = self.start.start_date
            self.result.professional = professional_id
            self.result.lines = res_lines
            if line.result_modifier == 'na':
                self.result.annulled = True
                self.result.annulment_date = datetime.now()
                self.result.report = False
            return 'result'
        return 'empty'

    def default_result(self, fields):
        default = {}
        default['method'] = self.result.method.id
        default['start_date'] = self.result.start_date
        default['professional'] = (self.result.professional.id
            if self.result.professional else None)
        default['lines'] = [l.id for l in self.result.lines]
        return default

    def transition_check_professional(self):
        pool = Pool()
        NotebookLoadResultsManualLine = pool.get(
            'lims.notebook.load_results_manual.line')
        LabProfessionalMethod = pool.get('lims.lab.professional.method')

        lines_to_save = []
        for line in self.result.lines:
            if line.line:  # Avoid empty lines created with ENTER key
                lines_to_save.append(line)
        NotebookLoadResultsManualLine.save(lines_to_save)

        professional = self.result.professional
        method = self.result.method

        qualifications = LabProfessionalMethod.search([
            ('professional', '=', professional.id),
            ('method', '=', method.id),
            ('type', '=', 'analytical'),
            ])
        if not qualifications:
            msg = '%s: %s' % (professional.rec_name, method.code)
            self.sit1.msg = msg
            return 'sit1'
        elif qualifications[0].state == 'training':
            situation_2_lines = [l.line.id for l in lines_to_save]
            supervisor_domain = []
            qualifications = LabProfessionalMethod.search([
                ('method', '=', method.id),
                ('type', '=', 'analytical'),
                ('state', 'in', ('qualified', 'requalified')),
                ])
            if qualifications:
                supervisor_domain = [q.professional.id for q in qualifications]

            self.sit2.lines = situation_2_lines
            self.sit2.supervisor_domain = supervisor_domain
            return 'sit2'

        return 'confirm_'

    def default_sit1(self, fields):
        defaults = {}
        if self.sit1.msg:
            defaults['msg'] = self.sit1.msg
        return defaults

    def default_sit2(self, fields):
        defaults = {}
        if self.sit2.supervisor_domain:
            defaults['supervisor_domain'] = [p.id for p in
                self.sit2.supervisor_domain]
        if self.sit2.lines:
            defaults['lines'] = [l.id for l in self.sit2.lines]
        return defaults

    def transition_confirm_(self):
        pool = Pool()
        NotebookLoadResultsManualLine = pool.get(
            'lims.notebook.load_results_manual.line')
        NotebookLine = pool.get('lims.notebook.line')
        LabProfessionalMethod = pool.get('lims.lab.professional.method')
        LabProfessionalMethodRequalification = pool.get(
            'lims.lab.professional.method.requalification')
        Date = pool.get('ir.date')

        # Write Results to Notebook lines
        actions = NotebookLoadResultsManualLine.search([
            ('session_id', '=', self._session_id),
            ])

        for data in actions:
            notebook_line = NotebookLine(data.line.id)
            if not notebook_line:
                continue
            notebook_line_write = {
                'result': data.result,
                'result_modifier': data.result_modifier,
                'end_date': data.end_date,
                'chromatogram': data.chromatogram,
                'initial_unit': (data.initial_unit.id if
                    data.initial_unit else None),
                'comments': data.comments,
                'literal_result': data.literal_result,
                'converted_result': None,
                'converted_result_modifier': 'eq',
                'backup': None,
                'verification': None,
                'uncertainty': None,
                }
            if data.result_modifier == 'na':
                notebook_line_write['annulled'] = True
                notebook_line_write['annulment_date'] = datetime.now()
                notebook_line_write['report'] = False
            professionals = [{'professional': self.result.professional.id}]
            notebook_line_write['professionals'] = (
                [('delete', [p.id for p in notebook_line.professionals])] +
                [('create', professionals)])
            NotebookLine.write([notebook_line], notebook_line_write)

        # Write Supervisors to Notebook lines
        supervisor_lines = {}
        if hasattr(self.sit2, 'supervisor'):
            supervisor_lines[self.sit2.supervisor.id] = [
                l.id for l in self.sit2.lines]
        for prof_id, lines in supervisor_lines.items():
            notebook_lines = NotebookLine.search([
                ('id', 'in', lines),
                ])
            if notebook_lines:
                professionals = [{'professional': prof_id}]
                notebook_line_write = {
                    'professionals': [('create', professionals)],
                    }
                NotebookLine.write(notebook_lines, notebook_line_write)

        # Write the execution of method
        all_prof = {}
        key = (self.result.professional.id, self.result.method.id)
        all_prof[key] = []
        if hasattr(self.sit2, 'supervisor'):
            for detail in self.sit2.lines:
                key = (self.sit2.supervisor.id, detail.method.id)
                if key not in all_prof:
                    all_prof[key] = []
                key = (self.result.professional.id, detail.method.id)
                if self.sit2.supervisor.id not in all_prof[key]:
                    all_prof[key].append(self.sit2.supervisor.id)

        today = Date.today()
        for key, sup in all_prof.items():
            professional_method, = LabProfessionalMethod.search([
                ('professional', '=', key[0]),
                ('method', '=', key[1]),
                ('type', '=', 'analytical'),
                ])
            if professional_method.state == 'training':
                history = LabProfessionalMethodRequalification.search([
                    ('professional_method', '=', professional_method.id),
                    ('type', '=', 'training'),
                    ])
                if history:
                    prev_supervisors = [s.supervisor.id for s in
                        history[0].supervisors]
                    supervisors = [{'supervisor': s} for s in sup
                        if s not in prev_supervisors]
                    LabProfessionalMethodRequalification.write(history, {
                        'last_execution_date': today,
                        'supervisors': [('create', supervisors)],
                        })
                else:
                    supervisors = [{'supervisor': s} for s in sup]
                    to_create = [{
                        'professional_method': professional_method.id,
                        'type': 'training',
                        'date': today,
                        'last_execution_date': today,
                        'supervisors': [('create', supervisors)],
                        }]
                    LabProfessionalMethodRequalification.create(to_create)

            elif professional_method.state == 'qualified':
                history = LabProfessionalMethodRequalification.search([
                    ('professional_method', '=', professional_method.id),
                    ('type', '=', 'qualification'),
                    ])
                if history:
                    LabProfessionalMethodRequalification.write(history, {
                        'last_execution_date': today,
                        })
                else:
                    to_create = [{
                        'professional_method': professional_method.id,
                        'type': 'qualification',
                        'date': today,
                        'last_execution_date': today,
                        }]
                    LabProfessionalMethodRequalification.create(to_create)

            else:
                history = LabProfessionalMethodRequalification.search([
                    ('professional_method', '=', professional_method.id),
                    ('type', '=', 'requalification'),
                    ])
                if history:
                    LabProfessionalMethodRequalification.write(history, {
                        'last_execution_date': today,
                        })
                else:
                    to_create = [{
                        'professional_method': professional_method.id,
                        'type': 'requalification',
                        'date': today,
                        'last_execution_date': today,
                        }]
                    LabProfessionalMethodRequalification.create(to_create)

        return 'end'


class NotebookAddInternalRelationsStart(ModelView):
    'Add Internal Relations'
    __name__ = 'lims.notebook.add_internal_relations.start'

    analysis = fields.Many2Many('lims.analysis', None, None,
        'Internal relations', required=True,
        domain=[('id', 'in', Eval('analysis_domain'))],
        depends=['analysis_domain'])
    analysis_domain = fields.One2Many('lims.analysis', None,
        'Internal relations domain')


class NotebookAddInternalRelations(Wizard):
    'Add Internal Relations'
    __name__ = 'lims.notebook.add_internal_relations'

    start = StateView('lims.notebook.add_internal_relations.start',
        'lims.lims_notebook_add_internal_relations_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Add', 'add', 'tryton-ok', default=True),
            ])
    add = StateTransition()

    def default_start(self, fields):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Notebook = pool.get('lims.notebook')
        Analysis = pool.get('lims.analysis')
        Typification = pool.get('lims.typification')

        notebook = Notebook(Transaction().context['active_id'])
        default = {
            'analysis_domain': [],
            }
        if not notebook.lines:
            return default

        notebook_analysis = []
        for notebook_line in notebook.lines:
            notebook_analysis.append(notebook_line.analysis.code)
        notebook_analysis_codes = '\', \''.join(str(a) for a
            in notebook_analysis)

        cursor.execute('SELECT DISTINCT(a.id, a.result_formula) '
            'FROM "' + Analysis._table + '" a '
                'INNER JOIN "' + Typification._table + '" t '
                'ON a.id = t.analysis '
            'WHERE t.product_type = %s '
                'AND t.matrix = %s '
                'AND t.valid '
                'AND a.behavior = \'internal_relation\' '
                'AND a.code NOT IN (\'' + notebook_analysis_codes + '\')',
            (notebook.fraction.product_type.id,
            notebook.fraction.matrix.id))
        internal_relations = cursor.fetchall()
        if not internal_relations:
            return default

        for internal_relation in internal_relations:
            formula = internal_relation[0].split(',')[1][:-1]
            if not formula:
                continue
            for i in (' ', '\t', '\n', '\r'):
                formula = formula.replace(i, '')
            variables = self._get_variables(formula)

            available = True
            if variables:
                for v in variables:
                    if v not in notebook_analysis:
                        available = False
                        break
            if available:
                ir_id = int(internal_relation[0].split(',')[0][1:])
                default['analysis_domain'].append(ir_id)

        return default

    def _get_variables(self, formula):
        variables = []
        for prefix in ('A', 'D', 'T', 'Y', 'R'):
            while True:
                idx = formula.find(prefix)
                if idx >= 0:
                    var = formula[idx:idx + 5]
                    formula = formula.replace(var, '_')
                    variables.append(var[1:])
                else:
                    break
        return variables

    def transition_add(self):
        Notebook = Pool().get('lims.notebook')
        notebook = Notebook(Transaction().context['active_id'])
        for analysis in self.start.analysis:
            self._create_service(analysis, notebook.fraction)
        return 'end'

    def _create_service(self, analysis, fraction):
        pool = Pool()
        Typification = pool.get('lims.typification')
        Service = pool.get('lims.service')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        divide, report_grouper = self._get_report_grouper(analysis)

        laboratory_id = (analysis.laboratories[0].laboratory.id if
            analysis.laboratories else None)

        typifications = Typification.search([
            ('product_type', '=', fraction.product_type.id),
            ('matrix', '=', fraction.matrix.id),
            ('analysis', '=', analysis.id),
            ('by_default', '=', True),
            ('valid', '=', True),
            ])
        method_id = (typifications[0].method.id if typifications
            else None)

        device_id = None
        if analysis.devices:
            for d in analysis.devices:
                if (d.laboratory.id == laboratory_id and
                        d.by_default is True):
                    device_id = d.device.id

        service_create = [{
            'fraction': fraction.id,
            'analysis': analysis.id,
            'laboratory': laboratory_id,
            'method': method_id,
            'device': device_id,
            'divide': divide,
            }]
        new_service, = Service.create(service_create)
        Service.set_confirmation_date([new_service])
        analysis_detail = list(new_service.analysis_detail)
        if report_grouper != 0:
            EntryDetailAnalysis.write(analysis_detail, {
                'report_grouper': report_grouper,
                })

        EntryDetailAnalysis.create_notebook_lines(analysis_detail,
            fraction)
        EntryDetailAnalysis.write(analysis_detail, {
            'state': 'unplanned',
            })

    def _get_report_grouper(self, analysis):
        pool = Pool()
        Notebook = pool.get('lims.notebook')

        divide = False
        report_grouper = 0

        notebook = Notebook(Transaction().context['active_id'])
        notebook_analysis = {}
        for notebook_line in notebook.lines:
            notebook_analysis[notebook_line.analysis.code] = notebook_line

        formula = analysis.result_formula
        for i in (' ', '\t', '\n', '\r'):
            formula = formula.replace(i, '')
        variables = self._get_variables(formula)
        for v in variables:
            if v in notebook_analysis:
                divide = notebook_analysis[v].service.divide
                report_grouper = (
                    notebook_analysis[v].analysis_detail.report_grouper)
                break
        return divide, report_grouper


class NotebookLineRepeatAnalysisStart(ModelView):
    'Repeat Analysis'
    __name__ = 'lims.notebook.line.repeat_analysis.start'

    analysis = fields.Many2One('lims.analysis', 'Analysis', required=True,
        domain=[('id', 'in', Eval('analysis_domain'))],
        depends=['analysis_domain'])
    analysis_domain = fields.One2Many('lims.analysis', None,
        'Analysis domain')


class NotebookLineRepeatAnalysis(Wizard):
    'Repeat Analysis'
    __name__ = 'lims.notebook.line.repeat_analysis'

    start = StateView('lims.notebook.line.repeat_analysis.start',
        'lims.lims_notebook_line_repeat_analysis_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Repeat', 'repeat', 'tryton-ok', default=True),
            ])
    repeat = StateTransition()

    def default_start(self, fields):
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        Analysis = pool.get('lims.analysis')

        notebook_line = NotebookLine(Transaction().context['active_id'])

        analysis_origin = notebook_line.analysis_origin
        analysis_origin_list = analysis_origin.split(' > ')

        analysis_code = notebook_line.analysis.code
        analysis_origin_list.append(analysis_code)

        analysis = Analysis.search([
            ('code', 'in', analysis_origin_list),
            ('behavior', '=', 'normal'),
            ])
        notebook_analysis = [a.id for a in analysis]
        default = {
            'analysis_domain': notebook_analysis,
            }
        if len(notebook_analysis) == 1:
            default['analysis'] = notebook_analysis[0]
        return default

    def transition_repeat(self):
        pool = Pool()
        Analysis = pool.get('lims.analysis')
        NotebookLine = pool.get('lims.notebook.line')
        Notebook = pool.get('lims.notebook')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        Config = pool.get('lims.configuration')

        analysis = self.start.analysis
        if analysis.type == 'analysis':
            analysis_to_repeat = [analysis.id]
        else:
            analysis_to_repeat = Analysis.get_included_analysis_analysis(
                analysis.id)

        notebook_line = NotebookLine(Transaction().context['active_id'])
        notebook = Notebook(notebook_line.notebook.id)

        rm_type = (notebook.fraction.special_type == 'rm')
        if rm_type:
            config = Config(1)
            rm_start_uom = (config.rm_start_uom.id if config.rm_start_uom
                else None)

        to_create = []
        details_to_update = []
        for analysis_id in analysis_to_repeat:
            nlines = NotebookLine.search([
                ('notebook', '=', notebook.id),
                ('analysis', '=', analysis_id),
                ('analysis.behavior', '=', 'normal'),
                ])
            if not nlines:
                continue
            nline_to_repeat = nlines[0]
            for nline in nlines:
                if nline.repetition > nline_to_repeat.repetition:
                    nline_to_repeat = nline

            detail_id = nline_to_repeat.analysis_detail.id
            defaults = {
                'analysis_detail': detail_id,
                'service': nline_to_repeat.service.id,
                'analysis': analysis_id,
                'analysis_origin': nline_to_repeat.analysis_origin,
                'repetition': nline_to_repeat.repetition + 1,
                'laboratory': nline_to_repeat.laboratory.id,
                'method': nline_to_repeat.method.id,
                'device': (nline_to_repeat.device.id if nline_to_repeat.device
                    else None),
                'initial_concentration': nline_to_repeat.initial_concentration,
                'decimals': nline_to_repeat.decimals,
                'report': nline_to_repeat.report,
                'concentration_level': (nline_to_repeat.concentration_level.id
                    if nline_to_repeat.concentration_level else None),
                'results_estimated_waiting': (
                    nline_to_repeat.results_estimated_waiting),
                'department': nline_to_repeat.department,
                }
            if rm_type:
                defaults['final_concentration'] = None
                defaults['initial_unit'] = rm_start_uom
                defaults['final_unit'] = None
                defaults['detection_limit'] = None
                defaults['quantification_limit'] = None
            else:
                defaults['final_concentration'] = (
                    nline_to_repeat.final_concentration)
                defaults['initial_unit'] = (nline_to_repeat.initial_unit.id if
                    nline_to_repeat.initial_unit else None)
                defaults['final_unit'] = (nline_to_repeat.final_unit.id if
                    nline_to_repeat.final_unit else None)
                defaults['detection_limit'] = nline_to_repeat.detection_limit
                defaults['quantification_limit'] = (
                    nline_to_repeat.quantification_limit)
            to_create.append(defaults)
            details_to_update.append(detail_id)

        Notebook.write([notebook], {
            'lines': [('create', to_create)],
            })

        details = EntryDetailAnalysis.search([
            ('id', 'in', details_to_update),
            ])
        if details:
            EntryDetailAnalysis.write(details, {
                'state': 'unplanned',
                })

        return 'end'


class NotebookAcceptLinesStart(ModelView):
    'Accept Lines'
    __name__ = 'lims.notebook.accept_lines.start'


class NotebookAcceptLines(Wizard):
    'Accept Lines'
    __name__ = 'lims.notebook.accept_lines'

    start_state = 'ok'
    start = StateView('lims.notebook.accept_lines.start',
        'lims.lims_notebook_accept_lines_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Ok', 'ok', 'tryton-ok', default=True),
            ])
    ok = StateTransition()

    def transition_ok(self):
        pool = Pool()
        Notebook = pool.get('lims.notebook')
        NotebookLine = pool.get('lims.notebook.line')

        for active_id in Transaction().context['active_ids']:
            notebook = Notebook(active_id)
            if not notebook.lines:
                continue

            repeated_analysis = []
            repetitions = NotebookLine.search([
                ('notebook', '=', notebook.id),
                ('repetition', '>', 0),
                ])
            if repetitions:
                repeated_analysis = [l.analysis.id for l in repetitions]
            notebook_lines = [l for l in notebook.lines
                if l.analysis.id not in repeated_analysis]

            self.lines_accept(notebook_lines)
        return 'end'

    def lines_accept(self, notebook_lines):
        NotebookLine = Pool().get('lims.notebook.line')

        accepted_analysis = {}
        lines_to_write = []
        for notebook_line in notebook_lines:
            if notebook_line.accepted:
                continue
            if not notebook_line.report:
                continue
            if notebook_line.annulled:
                continue
            if not notebook_line.end_date:
                continue
            if not (notebook_line.result or notebook_line.converted_result or
                    notebook_line.literal_result or
                    notebook_line.result_modifier in
                    ('nd', 'pos', 'neg', 'ni', 'abs', 'pre') or
                    notebook_line.converted_result_modifier in
                    ('nd', 'pos', 'neg', 'ni', 'abs', 'pre')):
                continue
            if (notebook_line.converted_result and
                    notebook_line.converted_result_modifier
                    not in ('ni', 'eq', 'low')):
                continue
            if (notebook_line.result and notebook_line.result_modifier
                    not in ('ni', 'eq', 'low')):
                continue

            notebook_id = notebook_line.notebook.id
            if notebook_id not in accepted_analysis:
                accepted_lines = NotebookLine.search([
                    ('notebook', '=', notebook_id),
                    ('accepted', '=', True),
                    ])
                accepted_analysis[notebook_id] = [l.analysis.id
                    for l in accepted_lines]
            if notebook_line.analysis.id in accepted_analysis[notebook_id]:
                continue

            accepted_analysis[notebook_id].append(notebook_line.analysis.id)
            lines_to_write.append(notebook_line)

        if lines_to_write:
            acceptance_date = datetime.now()
            NotebookLine.write(lines_to_write, {
                'accepted': True,
                'acceptance_date': acceptance_date,
                })


class NotebookLineAcceptLines(NotebookAcceptLines):
    'Accept Lines'
    __name__ = 'lims.notebook_line.accept_lines'

    def transition_ok(self):
        NotebookLine = Pool().get('lims.notebook.line')

        notebook_lines = NotebookLine.browse(
            Transaction().context['active_ids'])
        if not notebook_lines:
            return 'end'

        self.lines_accept(notebook_lines)
        return 'end'


class NotebookLineUnacceptLines(Wizard):
    'Unaccept Lines'
    __name__ = 'lims.notebook_line.unaccept_lines'

    start_state = 'ok'
    ok = StateTransition()

    def transition_ok(self):
        NotebookLine = Pool().get('lims.notebook.line')

        notebook_lines = NotebookLine.browse(
            Transaction().context['active_ids'])
        if not notebook_lines:
            return 'end'

        self.lines_unaccept(notebook_lines)
        return 'end'

    def lines_unaccept(self, notebook_lines):
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        ResultsReportVersionDetailLine = pool.get(
            'lims.results_report.version.detail.line')

        lines_to_write = []
        for notebook_line in notebook_lines:
            if not notebook_line.accepted:
                continue
            report_lines = ResultsReportVersionDetailLine.search([
                ('notebook_line', '=', notebook_line.id),
                ('report_version_detail.state', '!=', 'annulled'),
                ])
            if report_lines:
                continue

            lines_to_write.append(notebook_line)

        if lines_to_write:
            NotebookLine.write(lines_to_write, {
                'accepted': False,
                'acceptance_date': None,
                })


class NotebookResultsVerificationStart(ModelView):
    'Results Verification'
    __name__ = 'lims.notebook.results_verification.start'

    range_type = fields.Many2One('lims.range.type', 'Origin', required=True,
        domain=[('use', '=', 'results_verification')])


class NotebookResultsVerification(Wizard):
    'Results Verification'
    __name__ = 'lims.notebook.results_verification'

    start = StateView('lims.notebook.results_verification.start',
        'lims.lims_notebook_results_verification_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Ok', 'ok', 'tryton-ok', default=True),
            ])
    ok = StateTransition()

    @classmethod
    def __setup__(cls):
        super(NotebookResultsVerification, cls).__setup__()
        cls._error_messages.update({
            'ok': 'OK',
            'ok*': 'OK*',
            'out': 'Out of Range',
            })

    def default_start(self, fields):
        RangeType = Pool().get('lims.range.type')

        default = {}
        default_range_type = RangeType.search([
            ('use', '=', 'results_verification'),
            ('by_default', '=', True),
            ])
        if default_range_type:
            default['range_type'] = default_range_type[0].id
        return default

    def transition_ok(self):
        Notebook = Pool().get('lims.notebook')

        for active_id in Transaction().context['active_ids']:
            notebook = Notebook(active_id)
            if not notebook.lines:
                continue
            self.lines_results_verification(notebook.lines)
        return 'end'

    def lines_results_verification(self, notebook_lines):
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        Range = pool.get('lims.range')
        UomConversion = pool.get('lims.uom.conversion')
        VolumeConversion = pool.get('lims.volume.conversion')

        verifications = self._get_verifications()

        lines_to_save = []
        for notebook_line in notebook_lines:
            if notebook_line.accepted:
                continue

            result = notebook_line.converted_result
            if not result:
                result = notebook_line.result
                iu = notebook_line.initial_unit
                if not iu:
                    continue
                try:
                    ic = float(notebook_line.initial_concentration)
                except (TypeError, ValueError):
                    continue
            else:
                iu = notebook_line.final_unit
                if not iu:
                    continue
                try:
                    ic = float(notebook_line.final_concentration)
                except (TypeError, ValueError):
                    continue

            try:
                result = float(result)
            except (TypeError, ValueError):
                continue

            ranges = Range.search([
                ('range_type', '=', self.start.range_type),
                ('analysis', '=', notebook_line.analysis.id),
                ('product_type', '=', notebook_line.notebook.product_type.id),
                ('matrix', '=', notebook_line.notebook.matrix.id),
                ])
            if not ranges:
                continue
            fu = ranges[0].uom
            try:
                fc = float(ranges[0].concentration)
            except (TypeError, ValueError):
                continue

            if fu and fu.rec_name != '-':
                converted_result = None
                if (iu == fu and ic == fc):
                    converted_result = result
                elif (iu != fu and ic == fc):
                    formula = UomConversion.get_conversion_formula(iu,
                        fu)
                    if not formula:
                        continue
                    variables = self._get_variables(formula, notebook_line)
                    parser = FormulaParser(formula, variables)
                    formula_result = parser.getValue()

                    converted_result = result * formula_result
                elif (iu == fu and ic != fc):
                    converted_result = result * (fc / ic)
                else:
                    formula = None
                    conversions = UomConversion.search([
                        ('initial_uom', '=', iu),
                        ('final_uom', '=', fu),
                        ])
                    if conversions:
                        formula = conversions[0].conversion_formula
                    if not formula:
                        continue
                    variables = self._get_variables(formula, notebook_line)
                    parser = FormulaParser(formula, variables)
                    formula_result = parser.getValue()

                    if (conversions[0].initial_uom_volume and
                            conversions[0].final_uom_volume):
                        d_ic = VolumeConversion.brixToDensity(ic)
                        d_fc = VolumeConversion.brixToDensity(fc)
                        converted_result = (result * (fc / ic) *
                            (d_fc / d_ic) * formula_result)
                    else:
                        converted_result = (result * (fc / ic) *
                            formula_result)
                result = float(converted_result)

            verification = self._verificate_result(result, ranges[0])
            notebook_line.verification = verifications.get(verification)
            lines_to_save.append(notebook_line)
        if lines_to_save:
            NotebookLine.save(lines_to_save)

    def _get_variables(self, formula, notebook_line):
        VolumeConversion = Pool().get('lims.volume.conversion')

        variables = {}
        for var in ('DI',):
            while True:
                idx = formula.find(var)
                if idx >= 0:
                    variables[var] = 0
                    formula = formula.replace(var, '_')
                else:
                    break
        for var in variables.keys():
            if var == 'DI':
                ic = float(notebook_line.final_concentration)
                result = VolumeConversion.brixToDensity(ic)
                if result:
                    variables[var] = result
        return variables

    def _verificate_result(self, result, range_):
        if range_.min95 and range_.max95:
            if result < range_.min:
                return 'out'
            elif result < range_.min95:
                return 'ok*'
            elif result <= range_.max95:
                return 'ok'
            elif result <= range_.max:
                return 'ok*'
            else:
                return 'out'
        else:
            if (range_.min and result < range_.min):
                return 'out'
            elif (range_.max and result <= range_.max):
                return 'ok'
            else:
                return 'out'

    def _get_verifications(self):
        pool = Pool()
        User = pool.get('res.user')
        Lang = pool.get('ir.lang')

        lang = User(Transaction().user).language
        if not lang:
            lang, = Lang.search([
                    ('code', '=', 'en'),
                    ], limit=1)

        verifications = {}
        with Transaction().set_context(language=lang.code):
            verifications['ok'] = self.raise_user_error('ok',
                raise_exception=False)
            verifications['ok*'] = self.raise_user_error('ok*',
                raise_exception=False)
            verifications['out'] = self.raise_user_error('out',
                raise_exception=False)

        return verifications


class NotebookLineResultsVerification(NotebookResultsVerification):
    'Results Verification'
    __name__ = 'lims.notebook_line.results_verification'

    def transition_ok(self):
        NotebookLine = Pool().get('lims.notebook.line')

        notebook_lines = NotebookLine.browse(
            Transaction().context['active_ids'])
        if not notebook_lines:
            return 'end'

        self.lines_results_verification(notebook_lines)
        return 'end'


class UncertaintyCalcStart(ModelView):
    'Uncertainty Calculation'
    __name__ = 'lims.notebook.uncertainty_calc.start'

    range_type = fields.Many2One('lims.range.type', 'Origin', required=True,
        domain=[('use', '=', 'uncertainty_calc')])


class UncertaintyCalc(Wizard):
    'Uncertainty Calculation'
    __name__ = 'lims.notebook.uncertainty_calc'

    start_state = 'check'
    check = StateTransition()
    start = StateView('lims.notebook.uncertainty_calc.start',
        'lims.lims_notebook_uncertainty_calc_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Ok', 'ok', 'tryton-ok', default=True),
            ])
    ok = StateTransition()

    def transition_check(self):
        RangeType = Pool().get('lims.range.type')

        default_range_type = RangeType.search([
            ('use', '=', 'uncertainty_calc'),
            ('by_default', '=', True),
            ])
        if default_range_type:
            self.start.range_type = default_range_type[0].id
            return 'ok'
        return 'start'

    def default_start(self, fields):
        RangeType = Pool().get('lims.range.type')

        default = {}
        default_range_type = RangeType.search([
            ('use', '=', 'uncertainty_calc'),
            ('by_default', '=', True),
            ])
        if default_range_type:
            default['range_type'] = default_range_type[0].id
        return default

    def transition_ok(self):
        Notebook = Pool().get('lims.notebook')

        for active_id in Transaction().context['active_ids']:
            notebook = Notebook(active_id)
            if not notebook.lines:
                continue
            self.lines_uncertainty_calc(notebook.lines)
        return 'end'

    def lines_uncertainty_calc(self, notebook_lines):
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        Range = pool.get('lims.range')

        lines_to_save = []
        for notebook_line in notebook_lines:
            if notebook_line.accepted:
                continue
            result = notebook_line.converted_result
            if not result:
                result = notebook_line.result
            try:
                result = float(result)
            except (TypeError, ValueError):
                continue

            ranges = Range.search([
                ('range_type', '=', self.start.range_type),
                ('analysis', '=', notebook_line.analysis.id),
                ('product_type', '=', notebook_line.notebook.product_type.id),
                ('matrix', '=', notebook_line.notebook.matrix.id),
                ])
            if not ranges:
                continue

            uncertainty = self._get_uncertainty(result, notebook_line,
                ranges[0])
            if uncertainty is None:
                continue
            notebook_line.uncertainty = str(uncertainty)
            lines_to_save.append(notebook_line)
        if lines_to_save:
            NotebookLine.save(lines_to_save)

    def _get_uncertainty(self, result, notebook_line, range_):
        dilution_factor = notebook_line.dilution_factor
        if not dilution_factor or dilution_factor == 0.0:
            dilution_factor = 1.0
        diluted_result = result / dilution_factor
        try:
            factor = range_.factor or 1.0
            low_level = range_.low_level or 0.0 * factor
            middle_level = range_.middle_level or 0.0 * factor
            high_level = range_.high_level or 0.0 * factor
        except TypeError:
            return None

        uncertainty = 0.0
        if (range_.low_level_value and
                not (range_.middle_level_value and range_.high_level_value) and
                (diluted_result > low_level)):
            uncertainty = range_.low_level_value
        elif (range_.low_level_value and range_.middle_level_value and
                range_.high_level_value):
            if (low_level <= diluted_result and
                    diluted_result < middle_level):
                uncertainty = range_.low_level_value
            elif (middle_level <= diluted_result and
                    diluted_result < high_level):
                uncertainty = range_.middle_level_value
            elif diluted_result >= high_level:
                uncertainty = range_.high_level_value
        if (range_.low_level_value and range_.middle_level_value and not
                range_.high_level_value):
            if (low_level <= diluted_result and
                    diluted_result < middle_level):
                uncertainty = range_.low_level_value
            elif (middle_level <= diluted_result and
                    diluted_result < high_level):
                uncertainty = range_.middle_level_value

        if uncertainty > 0.0:
            uncertainty = result * uncertainty / 100

        return uncertainty


class NotebookLineUncertaintyCalc(UncertaintyCalc):
    'Uncertainty Calculation'
    __name__ = 'lims.notebook_line.uncertainty_calc'

    def transition_ok(self):
        NotebookLine = Pool().get('lims.notebook.line')

        notebook_lines = NotebookLine.browse(
            Transaction().context['active_ids'])
        if not notebook_lines:
            return 'end'

        self.lines_uncertainty_calc(notebook_lines)
        return 'end'


class NotebookPrecisionControlStart(ModelView):
    'Precision Control'
    __name__ = 'lims.notebook.precision_control.start'

    range_type = fields.Many2One('lims.range.type', 'Origin', required=True,
        domain=[('use', '=', 'repeatability_calc')])
    product_type = fields.Many2One('lims.product.type', 'Product type',
        required=True)
    matrix = fields.Many2One('lims.matrix', 'Matrix', required=True,
        domain=[
            ('id', 'in', Eval('matrix_domain')),
            ], depends=['matrix_domain'])
    matrix_domain = fields.Function(fields.Many2Many('lims.matrix',
        None, None, 'Matrix domain'),
        'on_change_with_matrix_domain')
    factor = fields.Float('Factor', required=True)

    @fields.depends('product_type')
    def on_change_with_matrix_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        Typification = Pool().get('lims.typification')

        if not self.product_type:
            return []

        cursor.execute('SELECT DISTINCT(matrix) '
            'FROM "' + Typification._table + '" '
            'WHERE product_type = %s '
            'AND valid',
            (self.product_type.id,))
        res = cursor.fetchall()
        if not res:
            return []
        return [x[0] for x in res]


class NotebookPrecisionControl(Wizard):
    'Precision Control'
    __name__ = 'lims.notebook.precision_control'

    start_state = 'check'
    check = StateTransition()
    start = StateView('lims.notebook.precision_control.start',
        'lims.lims_notebook_precision_control_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Ok', 'ok', 'tryton-ok', default=True),
            ])
    ok = StateTransition()

    @classmethod
    def __setup__(cls):
        super(NotebookPrecisionControl, cls).__setup__()
        cls._error_messages.update({
            'acceptable': 'Acceptable / Factor: %s - CV: %s',
            'unacceptable': 'Unacceptable / Factor: %s - CV: %s',
            })

    def transition_check(self):
        Notebook = Pool().get('lims.notebook')

        notebook = Notebook(Transaction().context['active_id'])
        if notebook.fraction.special_type in ('rm', 'con'):
            return 'start'
        return 'end'

    def default_start(self, fields):
        pool = Pool()
        Notebook = pool.get('lims.notebook')
        RangeType = pool.get('lims.range.type')

        notebook = Notebook(Transaction().context['active_id'])
        default = {
            'product_type': notebook.product_type.id,
            'matrix': notebook.matrix.id,
            'factor': 2,
            }
        default_range_type = RangeType.search([
            ('use', '=', 'repeatability_calc'),
            ('by_default', '=', True),
            ])
        if default_range_type:
            default['range_type'] = default_range_type[0].id
        return default

    def transition_ok(self):
        Notebook = Pool().get('lims.notebook')

        notebook = Notebook(Transaction().context['active_id'])
        if not notebook.lines:
            return 'end'

        self.lines_precision_control(notebook.lines)
        return 'end'

    def lines_precision_control(self, notebook_lines):
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        Range = pool.get('lims.range')

        lines_to_save = []
        for notebook_line in notebook_lines:
            if notebook_line.verification:
                continue
            concentration_level = notebook_line.concentration_level
            if not concentration_level:
                continue

            ranges = Range.search([
                ('range_type', '=', self.start.range_type.id),
                ('analysis', '=', notebook_line.analysis.id),
                ('product_type', '=', self.start.product_type.id),
                ('matrix', '=', self.start.matrix.id),
                ])
            if not ranges:
                continue

            if concentration_level.code == 'NC':
                cv = ranges[0].low_level_coefficient_variation
            elif concentration_level.code == 'NM':
                cv = ranges[0].middle_level_coefficient_variation
            elif concentration_level.code == 'NA':
                cv = ranges[0].high_level_coefficient_variation
            else:
                continue
            if not cv:
                continue

            try:
                if notebook_line.repetition == 0:
                    rep_0 = float(notebook_line.result)
                    rep_1 = float(self._get_repetition_result(notebook_line,
                        1))
                elif notebook_line.repetition == 1:
                    rep_0 = float(self._get_repetition_result(notebook_line,
                        0))
                    rep_1 = float(notebook_line.result)
                else:
                    continue
            except (TypeError, ValueError):
                continue

            if not rep_0 or not rep_1:
                continue

            average = (rep_0 + rep_1) / 2
            error = abs(rep_0 - rep_1) / average * 100

            if error < (cv * self.start.factor):
                res = self.raise_user_error('acceptable', (
                    self.start.factor, cv), raise_exception=False)
            else:
                res = self.raise_user_error('unacceptable', (
                    self.start.factor, cv), raise_exception=False)
            notebook_line.verification = res
            lines_to_save.append(notebook_line)
        if lines_to_save:
            NotebookLine.save(lines_to_save)

    def _get_repetition_result(self, notebook_line, repetition):
        NotebookLine = Pool().get('lims.notebook.line')

        repetition = NotebookLine.search([
            ('notebook', '=', notebook_line.notebook.id),
            ('analysis', '=', notebook_line.analysis.id),
            ('repetition', '=', repetition),
            ])
        if not repetition:
            return None
        return repetition[0].result


class NotebookLinePrecisionControl(NotebookPrecisionControl):
    'Precision Control'
    __name__ = 'lims.notebook_line.precision_control'

    def transition_check(self):
        NotebookLine = Pool().get('lims.notebook.line')

        reference_line = NotebookLine(Transaction().context['active_id'])
        if reference_line.notebook.fraction.special_type in ('rm', 'con'):
            return 'start'
        return 'end'

    def default_start(self, fields):
        NotebookLine = Pool().get('lims.notebook.line')

        reference_line = NotebookLine(Transaction().context['active_id'])
        with Transaction().set_context(active_id=reference_line.notebook.id):
            return super(NotebookLinePrecisionControl,
                self).default_start(fields)

    def transition_ok(self):
        NotebookLine = Pool().get('lims.notebook.line')

        reference_line = NotebookLine(Transaction().context['active_id'])

        notebook_lines = NotebookLine.browse(
            Transaction().context['active_ids'])
        notebook_lines = [l for l in notebook_lines
            if l.notebook.id == reference_line.notebook.id]
        if not notebook_lines:
            return 'end'

        self.lines_precision_control(notebook_lines)
        return 'end'


class OpenNotebookLines(Wizard):
    'Open Notebook Lines'
    __name__ = 'lims.open_notebook_lines'
    start_state = 'open_'
    open_ = StateAction('lims.act_lims_notebook_line_related1')

    def do_open_(self, action):
        Notebook = Pool().get('lims.notebook')

        notebook = Notebook.browse(Transaction().context['active_ids'])[0]
        action['pyson_domain'] = PYSONEncoder().encode(
            [('notebook', 'in', Transaction().context['active_ids'])])

        action['name'] = \
            '%s - %s - %s - %s - %s' % (notebook.fraction.number,
                notebook.party.name, notebook.product_type.description,
                notebook.matrix.description, notebook.label)
        return action, {}


class ChangeEstimatedDaysForResultsStart(ModelView):
    'Change Estimated Days For Results'
    __name__ = 'lims.change_results_estimated_waiting.start'

    date_from = fields.Date('Confirmation date From', required=True)
    date_to = fields.Date('Confirmation date To', required=True)
    methods = fields.Many2Many('lims.lab.method',
        None, None, 'Methods', required=True)
    results_estimated_waiting = fields.Integer('Days to add')
    party = fields.Many2One('party.party', 'Party')


class ChangeEstimatedDaysForResults(Wizard):
    'Change Estimated Days For Results'
    __name__ = 'lims.change_results_estimated_waiting'

    start = StateView('lims.change_results_estimated_waiting.start',
        'lims.change_results_estimated_waiting_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Change', 'change', 'tryton-ok', default=True),
            ])
    change = StateTransition()

    def transition_change(self):
        NotebookLine = Pool().get('lims.notebook.line')

        methods_ids = [m.id for m in self.start.methods]
        clause = [('method', 'in', methods_ids)]
        clause.append(('analysis_detail.confirmation_date',
            '>=', self.start.date_from))
        clause.append(('analysis_detail.confirmation_date',
            '<=', self.start.date_to))
        clause.append(('accepted', '=', False))
        party_id = self.start.party and self.start.party.id or None
        if party_id:
            clause.append(('party', '=', party_id))

        notebook_lines = NotebookLine.search(clause)
        if notebook_lines:
            lines_to_save = []
            for line in notebook_lines:
                line.results_estimated_waiting = ((
                    line.results_estimated_waiting or 0) +
                    self.start.results_estimated_waiting)
                lines_to_save.append(line)
            NotebookLine.save(lines_to_save)
        return 'end'


class PrintAnalysisPendingInformStart(ModelView):
    'Analysis Pending of Inform'
    __name__ = 'lims.print_analysis_pending_inform.start'

    date_from = fields.Date('Date from', required=True)
    date_to = fields.Date('Date to', required=True)
    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        required=True)
    party = fields.Many2One('party.party', 'Party')
    include_comments_of_fraction = fields.Boolean(
        'Include comments of the fraction')


class PrintAnalysisPendingInform(Wizard):
    'Analysis Pending of Inform'
    __name__ = 'lims.print_analysis_pending_inform'

    start = StateView('lims.print_analysis_pending_inform.start',
        'lims.print_analysis_pending_inform_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print', 'print_', 'tryton-print', default=True),
        ])
    print_ = StateReport('lims.analysis_pending_inform')

    def do_print_(self, action):
        data = {
            'date_from': self.start.date_from,
            'date_to': self.start.date_to,
            'laboratory': self.start.laboratory.id,
            'party': self.start.party and self.start.party.id or None,
            'include_comments_of_fraction': (
                self.start.include_comments_of_fraction),
            }
        return action, data

    def transition_print_(self):
        return 'end'


class AnalysisPendingInform(Report):
    'Analysis Pending of Inform'
    __name__ = 'lims.analysis_pending_inform'

    @classmethod
    def get_context(cls, records, data):
        pool = Pool()
        Laboratory = pool.get('lims.laboratory')
        Party = pool.get('party.party')

        report_context = super(AnalysisPendingInform, cls).get_context(
            records, data)

        today = get_print_date()
        report_context['today'] = today
        report_context['company'] = report_context['user'].company
        report_context['date_from'] = data['date_from']
        report_context['date_to'] = data['date_to']
        report_context['laboratory'] = Laboratory(data['laboratory']).rec_name
        report_context['party'] = ''

        if data['party']:
            report_context['party'] = Party(data['party']).rec_name
        report_context['include_comments_of_fraction'] = \
            data['include_comments_of_fraction']

        objects = cls._get_report_records(data['date_from'], data['date_to'],
            data['laboratory'], data['party'])

        report_context['records'] = objects

        return report_context

    @classmethod
    def _get_report_records(cls, date_from, date_to, laboratory, party):
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')

        res = []

        excluded_notebooks = cls._get_excluded_notebooks(date_from, date_to,
            laboratory, party)
        if excluded_notebooks:
            for n_id, a_ids in excluded_notebooks.items():
                clause = [
                    ('notebook.id', '=', n_id),
                    ('analysis', 'in', a_ids),
                    ('laboratory', '=', laboratory),
                    ('report', '=', True),
                    ('annulled', '=', False),
                    ]
                excluded_lines = NotebookLine.search(clause)
                if excluded_lines:
                    res.extend(line for line in excluded_lines)
        return res

    @classmethod
    def _get_excluded_notebooks(cls, date_from, date_to, laboratory, party):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        Notebook = pool.get('lims.notebook')
        Fraction = pool.get('lims.fraction')
        Sample = pool.get('lims.sample')
        Entry = pool.get('lims.entry')
        FractionType = pool.get('lims.fraction.type')

        party_clause = ''
        if party:
            party_clause = 'AND e.party = ' + str(party)

        cursor.execute('SELECT nl.notebook, nl.analysis, nl.accepted '
            'FROM "' + NotebookLine._table + '" nl '
                'INNER JOIN "' + Notebook._table + '" n '
                'ON n.id = nl.notebook '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON f.id = n.fraction '
                'INNER JOIN "' + Sample._table + '" s '
                'ON s.id = f.sample '
                'INNER JOIN "' + Entry._table + '" e '
                'ON e.id = s.entry '
                'INNER JOIN "' + FractionType._table + '" ft '
                'ON ft.id = f.type '
            'WHERE ft.report = TRUE '
                'AND s.date::date >= %s::date '
                'AND s.date::date <= %s::date '
                'AND nl.laboratory = %s '
                'AND nl.report = TRUE '
                'AND nl.annulled = FALSE ' +
                party_clause,
            (date_from, date_to, laboratory,))
        notebook_lines = cursor.fetchall()

        # Check accepted repetitions
        to_check = []
        oks = []
        for line in notebook_lines:
            key = (line[0], line[1])
            if not line[2]:
                to_check.append(key)
            else:
                oks.append(key)

        to_check = list(set(to_check) - set(oks))

        excluded_notebooks = {}
        for n_id, a_id in to_check:
            if n_id not in excluded_notebooks:
                excluded_notebooks[n_id] = []
            excluded_notebooks[n_id].append(a_id)
        return excluded_notebooks


class PrintAnalysisCheckedPendingInformStart(ModelView):
    'Analysis checked pending of Inform'
    __name__ = 'lims.print_analysis_checked_pending_inform.start'

    date_from = fields.Date('Date from', required=True)
    date_to = fields.Date('Date to', required=True)
    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        required=True)
    party = fields.Many2One('party.party', 'Party')


class PrintAnalysisCheckedPendingInform(Wizard):
    'Analysis Checked pending of Inform'
    __name__ = 'lims.print_analysis_checked_pending_inform'

    start = StateView('lims.print_analysis_checked_pending_inform.start',
        'lims.print_analysis_checked_pending_inform_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print', 'print_', 'tryton-print', default=True),
        ])
    print_ = StateReport('lims.analysis_checked_pending_inform')

    def do_print_(self, action):
        data = {
            'date_from': self.start.date_from,
            'date_to': self.start.date_to,
            'laboratory': self.start.laboratory.id,
            'party': self.start.party and self.start.party.id or None,
            }
        return action, data

    def transition_print_(self):
        return 'end'


class AnalysisCheckedPendingInform(Report):
    'Analysis checked pending of Inform'
    __name__ = 'lims.analysis_checked_pending_inform'

    @classmethod
    def get_context(cls, records, data):
        pool = Pool()
        Laboratory = pool.get('lims.laboratory')
        Party = pool.get('party.party')

        report_context = super(AnalysisCheckedPendingInform, cls).get_context(
            records, data)

        today = get_print_date()
        report_context['today'] = today
        report_context['company'] = report_context['user'].company
        report_context['date_from'] = data['date_from']
        report_context['date_to'] = data['date_to']
        report_context['laboratory'] = Laboratory(data['laboratory']).rec_name
        report_context['party'] = ''
        if data['party']:
            report_context['party'] = Party(data['party']).rec_name

        objects = cls._get_report_records(data['date_from'], data['date_to'],
            data['laboratory'], data['party'])

        report_context['records'] = objects
        return report_context

    @classmethod
    def _get_report_records(cls, date_from, date_to, laboratory, party):
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')

        res = []

        included_notebooks = cls._get_included_notebooks(date_from, date_to,
            laboratory, party)
        if included_notebooks:
            for n_id, a_ids in included_notebooks:
                clause = [
                    ('notebook.id', '=', n_id),
                    ('analysis', 'in', [a_ids]),
                    ('laboratory', '=', laboratory),
                    ('report', '=', True),
                    ('annulled', '=', False),
                    ]
                included_lines = NotebookLine.search(clause)
                if included_lines:
                    res.extend(line for line in included_lines)
        return res

    @classmethod
    def _get_included_notebooks(cls, date_from, date_to, laboratory, party):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        Notebook = pool.get('lims.notebook')
        Fraction = pool.get('lims.fraction')
        Sample = pool.get('lims.sample')
        Entry = pool.get('lims.entry')
        FractionType = pool.get('lims.fraction.type')

        party_clause = ''
        if party:
            party_clause = 'AND e.party = ' + str(party)

        cursor.execute('SELECT nl.notebook, nl.analysis '
            'FROM "' + NotebookLine._table + '" nl '
                'INNER JOIN "' + Notebook._table + '" n '
                'ON n.id = nl.notebook '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON f.id = n.fraction '
                'INNER JOIN "' + Sample._table + '" s '
                'ON s.id = f.sample '
                'INNER JOIN "' + Entry._table + '" e '
                'ON e.id = s.entry '
                'INNER JOIN "' + FractionType._table + '" ft '
                'ON ft.id = f.type '
            'WHERE ft.report = TRUE '
                'AND s.date::date >= %s::date '
                'AND s.date::date <= %s::date '
                'AND nl.laboratory = %s '
                'AND nl.report = TRUE '
                'AND nl.accepted = TRUE '
                'AND nl.results_report IS NULL '
                'AND nl.annulled = FALSE ' +
                party_clause,
            (date_from, date_to, laboratory,))

        notebook_lines = cursor.fetchall()
        return notebook_lines
