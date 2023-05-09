# This file is part of lims_analysis_sheet module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import formulas
import schedula
import functools
from itertools import chain
from io import StringIO
from decimal import Decimal
from datetime import datetime, date
from sql import Table, Column, Literal, Null
from sql.aggregate import Count
from sql.conditionals import Coalesce

from trytond.model import Workflow, ModelView, ModelSQL, DeactivableMixin, \
    fields, Unique, Index
from trytond.wizard import Wizard, StateTransition, StateView, StateAction, \
    Button
from trytond.pool import Pool
from trytond.pyson import PYSONEncoder, Eval, Bool, If
from trytond.transaction import Transaction
from trytond.report import Report
from trytond.exceptions import UserError
from trytond.i18n import gettext
from trytond.modules.lims_interface.interface import str2date, \
    get_model_resource
from trytond.modules.lims_interface.data import ALLOWED_RESULT_TYPES


class TemplateAnalysisSheet(DeactivableMixin, ModelSQL, ModelView):
    'Analysis Sheet Template'
    __name__ = 'lims.template.analysis_sheet'

    interface = fields.Many2One('lims.interface', 'Device Interface',
        required=True, domain=[
            ('kind', '=', 'template'),
            ('state', '=', 'active')],
        states={'readonly': Bool(Eval('interface'))})
    name = fields.Char('Name', required=True)
    analysis = fields.One2Many('lims.template.analysis_sheet.analysis',
        'template', 'Analysis', states={'required': Bool(Eval('active'))},
        context={'interface_id': Eval('interface')},
        depends={'interface'})
    comments = fields.Text('Comments')
    pending_fractions = fields.Function(fields.Integer('Pending fractions'),
        'get_fields')
    urgent = fields.Function(fields.Boolean('Urgent'), 'get_fields',
        searcher='search_urgent')
    report = fields.Many2One('ir.action.report', 'Report',
        domain=[
            ('model', '=', 'lims.analysis_sheet'),
            ('report_name', 'ilike', 'lims.analysis_sheet.report%%'),
            ])
    controls_required = fields.Boolean('Requires Controls')
    controls_allowed = fields.MultiSelection([
        ('con', 'Control'),
        ('bmz', 'BMZ'),
        ('rm', 'RM'),
        ('bre', 'BRE'),
        ('mrt', 'MRT'),
        ('coi', 'COI'),
        ('mrc', 'MRC'),
        ('sla', 'SLA'),
        ('itc', 'ITC'),
        ('itl', 'ITL'),
        ], 'Controls allowed', sort=False,
        states={'required': Bool(Eval('controls_required'))})

    @staticmethod
    def default_report():
        ActionReport = Pool().get('ir.action.report')
        report = ActionReport.search([
            ('model', '=', 'lims.analysis_sheet'),
            ('report_name', '=', 'lims.analysis_sheet.report'),
            ])
        return report and report[0].id or None

    @fields.depends('interface', '_parent_interface.name')
    def on_change_with_name(self, name=None):
        if self.interface:
            return self.interface.name

    @classmethod
    def get_fields(cls, records, names):
        context = Transaction().context
        cursor = Transaction().connection.cursor()
        pool = Pool()
        PlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')
        PlanificationDetail = pool.get('lims.planification.detail')
        Planification = pool.get('lims.planification')
        NotebookLine = pool.get('lims.notebook.line')
        Notebook = pool.get('lims.notebook')
        Fraction = pool.get('lims.fraction')
        Sample = pool.get('lims.sample')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        Analysis = pool.get('lims.analysis')
        Template = pool.get('lims.template.analysis_sheet')
        TemplateAnalysis = pool.get('lims.template.analysis_sheet.analysis')

        result = {
            'urgent': dict((r.id, False) for r in records),
            'pending_fractions': dict((r.id, 0) for r in records),
            }

        date_from = context.get('date_from') or str(date.min)
        date_to = context.get('date_to') or str(date.max)
        if not (date_from and date_to):
            return result

        cursor.execute('SELECT nl.id '
            'FROM "' + NotebookLine._table + '" nl '
                'INNER JOIN "' + PlanificationServiceDetail._table +
                '" psd ON psd.notebook_line = nl.id '
                'INNER JOIN "' + PlanificationDetail._table + '" pd '
                'ON psd.detail = pd.id '
                'INNER JOIN "' + Planification._table + '" p '
                'ON pd.planification = p.id '
            'WHERE p.state = \'preplanned\'')
        planned_lines = [x[0] for x in cursor.fetchall()]
        planned_lines_ids = ', '.join(str(x) for x in [0] + planned_lines)
        preplanned_where = 'AND nl.id NOT IN (%s) ' % planned_lines_ids

        dates_where = ''
        dates_where += ('AND ad.confirmation_date::date >= \'%s\'::date ' %
            date_from)
        dates_where += ('AND ad.confirmation_date::date <= \'%s\'::date ' %
            date_to)

        sql_select = (
            'SELECT nl.analysis, nl.method, s.product_type, s.matrix, '
            'nl.urgent, f.id ')
        sql_from = (
            'FROM "' + NotebookLine._table + '" nl '
            'INNER JOIN "' + Analysis._table + '" nla '
            'ON nla.id = nl.analysis '
            'INNER JOIN "' + Notebook._table + '" n '
            'ON n.id = nl.notebook '
            'INNER JOIN "' + Fraction._table + '" f '
            'ON f.id = n.fraction '
            'INNER JOIN "' + Sample._table + '" s '
            'ON s.id = f.sample '
            'INNER JOIN "' + EntryDetailAnalysis._table + '" ad '
            'ON ad.id = nl.analysis_detail ')
        sql_where = (
            'WHERE ad.plannable = TRUE '
            'AND nl.start_date IS NULL '
            'AND nl.annulled = FALSE '
            'AND nla.behavior != \'internal_relation\' ' +
            preplanned_where + dates_where)
        params = []

        if context.get('laboratory'):
            sql_where += 'AND nl.laboratory = %s '
            params.append(context.get('laboratory'))
        if context.get('department'):
            sql_where += 'AND nl.department = %s '
            params.append(context.get('department'))

        with Transaction().set_user(0):
            cursor.execute(sql_select + sql_from + sql_where, tuple(params))
        notebook_lines = cursor.fetchall()
        if not notebook_lines:
            return result

        templates = {}
        for nl in notebook_lines:
            cursor.execute('SELECT t.id '
                'FROM "' + Template._table + '" t '
                    'INNER JOIN "' + TemplateAnalysis._table + '" ta '
                    'ON t.id = ta.template '
                'WHERE t.active IS TRUE '
                    'AND ta.analysis = %s '
                    'AND (ta.method = %s OR ta.method IS NULL) '
                    'AND (ta.product_type = %s OR ta.product_type IS NULL) '
                    'AND (ta.matrix = %s OR ta.matrix IS NULL)',
                (nl[0], nl[1], nl[2], nl[3]))
            template = cursor.fetchone()
            if not template:
                continue
            if template[0] not in templates:
                templates[template[0]] = set()
            templates[template[0]].add(nl[5])
            if nl[4]:
                result['urgent'][template[0]] = True
        for t_id, fractions in templates.items():
            result['pending_fractions'][t_id] = len(fractions)
        return result

    @classmethod
    def search_urgent(cls, name, clause):
        context = Transaction().context
        cursor = Transaction().connection.cursor()
        pool = Pool()
        PlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')
        PlanificationDetail = pool.get('lims.planification.detail')
        Planification = pool.get('lims.planification')
        NotebookLine = pool.get('lims.notebook.line')
        Notebook = pool.get('lims.notebook')
        Fraction = pool.get('lims.fraction')
        Sample = pool.get('lims.sample')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        Analysis = pool.get('lims.analysis')
        Template = pool.get('lims.template.analysis_sheet')
        TemplateAnalysis = pool.get('lims.template.analysis_sheet.analysis')

        date_from = context.get('date_from') or str(date.min)
        date_to = context.get('date_to') or str(date.max)
        if not (date_from and date_to):
            return [('id', '=', -1)]

        cursor.execute('SELECT nl.id '
            'FROM "' + NotebookLine._table + '" nl '
                'INNER JOIN "' + PlanificationServiceDetail._table +
                '" psd ON psd.notebook_line = nl.id '
                'INNER JOIN "' + PlanificationDetail._table + '" pd '
                'ON psd.detail = pd.id '
                'INNER JOIN "' + Planification._table + '" p '
                'ON pd.planification = p.id '
            'WHERE p.state = \'preplanned\'')
        planned_lines = [x[0] for x in cursor.fetchall()]
        planned_lines_ids = ', '.join(str(x) for x in [0] + planned_lines)
        preplanned_where = 'AND nl.id NOT IN (%s) ' % planned_lines_ids

        dates_where = ''
        dates_where += ('AND ad.confirmation_date::date >= \'%s\'::date ' %
            date_from)
        dates_where += ('AND ad.confirmation_date::date <= \'%s\'::date ' %
            date_to)

        sql_select = 'SELECT nl.analysis, nl.method, s.product_type, s.matrix '
        sql_from = (
            'FROM "' + NotebookLine._table + '" nl '
            'INNER JOIN "' + Analysis._table + '" nla '
            'ON nla.id = nl.analysis '
            'INNER JOIN "' + Notebook._table + '" n '
            'ON n.id = nl.notebook '
            'INNER JOIN "' + Fraction._table + '" f '
            'ON f.id = n.fraction '
            'INNER JOIN "' + Sample._table + '" s '
            'ON s.id = f.sample '
            'INNER JOIN "' + EntryDetailAnalysis._table + '" ad '
            'ON ad.id = nl.analysis_detail ')
        sql_where = (
            'WHERE nl.urgent = TRUE '
            'AND ad.plannable = TRUE '
            'AND nl.start_date IS NULL '
            'AND nl.annulled = FALSE '
            'AND nla.behavior != \'internal_relation\' ' +
            preplanned_where + dates_where)
        params = []

        if context.get('laboratory'):
            sql_where += 'AND nl.laboratory = %s '
            params.append(context.get('laboratory'))
        if context.get('department'):
            sql_where += 'AND nl.department = %s '
            params.append(context.get('department'))

        field, op, operand = clause
        with Transaction().set_user(0):
            cursor.execute(sql_select + sql_from + sql_where, tuple(params))
        urgent_lines = cursor.fetchall()
        if not urgent_lines:
            if (op, operand) in (('=', True), ('!=', False)):
                return [('id', '=', -1)]
            return []

        urgent_templates = []
        for nl in urgent_lines:
            cursor.execute('SELECT t.id '
                'FROM "' + Template._table + '" t '
                    'INNER JOIN "' + TemplateAnalysis._table + '" ta '
                    'ON t.id = ta.template '
                'WHERE t.active IS TRUE '
                    'AND ta.analysis = %s '
                    'AND (ta.method = %s OR ta.method IS NULL) '
                    'AND (ta.product_type = %s OR ta.product_type IS NULL) '
                    'AND (ta.matrix = %s OR ta.matrix IS NULL)',
                (nl[0], nl[1], nl[2], nl[3]))
            template = cursor.fetchone()
            if not template:
                continue
            urgent_templates.append(template[0])

        if (op, operand) in (('=', True), ('!=', False)):
            return [('id', 'in', urgent_templates)]
        return [('id', 'not in', urgent_templates)]


class TemplateAnalysisSheetAnalysis(ModelSQL, ModelView):
    'Template Analysis'
    __name__ = 'lims.template.analysis_sheet.analysis'

    template = fields.Many2One('lims.template.analysis_sheet', 'Template',
        required=True, ondelete='CASCADE')
    analysis = fields.Many2One('lims.analysis', 'Analysis',
        required=True, domain=[('type', '=', 'analysis')])
    method = fields.Many2One('lims.lab.method', 'Method',
        domain=[('id', 'in', Eval('method_domain'))])
    method_domain = fields.Function(fields.Many2Many('lims.lab.method',
        None, None, 'Method domain'),
        'on_change_with_method_domain')
    product_type = fields.Many2One('lims.product.type', 'Product type')
    matrix = fields.Many2One('lims.matrix', 'Matrix')
    expressions = fields.One2Many(
        'lims.template.analysis_sheet.analysis.expression',
        'analysis', 'Special formulas')
    interface = fields.Function(fields.Many2One(
        'lims.interface', 'Device Interface'), 'get_interface',
        searcher='search_interface')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        t = cls.__table__()
        #cls._sql_indexes.update({
            #Index(t, (t.analysis, Index.Equality())),
            #})

    @fields.depends('analysis', '_parent_analysis.methods')
    def on_change_with_method_domain(self, name=None):
        methods = []
        if self.analysis and self.analysis.methods:
            methods = [m.id for m in self.analysis.methods]
        return methods

    def get_interface(self, name):
        return self.template.interface.id

    @classmethod
    def search_interface(cls, name, clause):
        return [('template.interface',) + tuple(clause[1:])]

    @classmethod
    def validate(cls, template_analysis):
        super().validate(template_analysis)
        for ta in template_analysis:
            ta.check_duplicated()

    def check_duplicated(self):
        clause = [
            ('id', '!=', self.id),
            ('analysis', '=', self.analysis.id),
            ('template.active', '=', True),
            ]
        if self.method:
            clause.append(('method', '=', self.method.id))
        else:
            clause.append(('method', '=', None))
        if self.product_type:
            clause.append(('product_type', '=', self.product_type.id))
        else:
            clause.append(('product_type', '=', None))
        if self.matrix:
            clause.append(('matrix', '=', self.matrix.id))
        else:
            clause.append(('matrix', '=', None))
        duplicated = self.search(clause)
        if duplicated:
            raise UserError(gettext(
                'lims_analysis_sheet.msg_template_analysis_unique',
                analysis=self.analysis.rec_name))


class TemplateAnalysisSheetAnalysisExpression(ModelSQL, ModelView):
    'Special Formula'
    __name__ = 'lims.template.analysis_sheet.analysis.expression'

    analysis = fields.Many2One('lims.template.analysis_sheet.analysis',
        'Analysis', required=True, ondelete='CASCADE')
    column = fields.Many2One('lims.interface.column', 'Column',
        domain=['OR', ('id', '=', Eval('column', -1)),
            ('interface', '=', Eval('context', {}).get('interface_id'))],
        required=True)
    expression = fields.Char('Formula')

    @fields.depends('column')
    def on_change_with_expression(self, name=None):
        if self.column:
            return self.column.expression


def set_state_info(kind):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(cls, sheets, *args, **kwargs):
            pool = Pool()
            LaboratoryProfessional = pool.get('lims.laboratory.professional')

            result = func(cls, sheets, *args, **kwargs)
            professional_id = LaboratoryProfessional.get_lab_professional()
            if professional_id:
                cls.write(sheets, {
                    '%s_by' % kind: professional_id,
                    '%s_date' % kind: datetime.now(),
                    })
            return result
        return wrapper
    return decorator


class AnalysisSheet(Workflow, ModelSQL, ModelView):
    'Analysis Sheet'
    __name__ = 'lims.analysis_sheet'
    _rec_name = 'number'

    template = fields.Many2One('lims.template.analysis_sheet', 'Template',
        required=True, readonly=True)
    compilation = fields.Many2One('lims.interface.compilation', 'Compilation',
        required=True, readonly=True)
    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        readonly=True)
    professional = fields.Many2One('lims.laboratory.professional',
        'Professional', required=True, readonly=True)
    urgent = fields.Function(fields.Boolean('Urgent'), 'get_fields')
    samples_qty = fields.Function(fields.Integer('Samples Qty.'),
        'get_fields')
    number = fields.Char('Number', readonly=True)
    date = fields.Function(fields.DateTime('Date'), 'get_date',
        searcher='search_date')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('validated', 'Validated'),
        ('done', 'Done'),
        ('annulled', 'Annulled'),
        ], 'State', required=True, readonly=True)
    planification = fields.Many2One('lims.planification', 'Planification',
        readonly=True)
    planning_date = fields.Function(fields.Date('Planning Date'),
        'get_planning_date', searcher='search_planning_date')
    partial_analysys = fields.Function(fields.Boolean('Partial analysis'),
        'get_fields')
    completion_percentage = fields.Function(fields.Numeric('Complete',
        digits=(1, 4), domain=[
            ('completion_percentage', '>=', 0),
            ('completion_percentage', '<=', 1),
            ]),
        'get_fields')
    report_cache = fields.Binary('Report', readonly=True,
        file_id='report_cache_id', store_prefix='analysis_sheet')
    report_cache_id = fields.Char('Report ID', readonly=True)
    report_format = fields.Char('Report Format', readonly=True)
    activated_by = fields.Many2One('lims.laboratory.professional',
        'Activated By', readonly=True)
    activated_date = fields.DateTime('Activated Date', readonly=True)
    validated_by = fields.Many2One('lims.laboratory.professional',
        'Validated By', readonly=True)
    validated_date = fields.DateTime('Validated Date', readonly=True)
    confirmed_by = fields.Many2One('lims.laboratory.professional',
        'Confirmed By', readonly=True)
    confirmed_date = fields.DateTime('Confirmed Date', readonly=True)
    annulled_by = fields.Many2One('lims.laboratory.professional',
        'Annulled By', readonly=True)
    annulled_date = fields.DateTime('Annulled Date', readonly=True)
    view = fields.Many2One('lims.interface.view', 'View',
        domain=[('interface', '=', Eval('interface'))],
        states={'invisible': Eval('state') == 'draft'})
    interface = fields.Function(fields.Many2One('lims.interface', 'Interface'),
        'get_interface')
    samples = fields.Char('Samples', readonly=True)
    out_of_ranges = fields.Function(fields.Boolean('Out of Ranges'),
        'get_out_of_ranges')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order.insert(0, ('date', 'DESC'))
        t = cls.__table__()
        cls._sql_constraints += [
            ('compilation_uniq', Unique(t, t.compilation),
                'lims_analysis_sheet.msg_sheet_compilation_unique'),
            ]
        cls._transitions |= set((
            ('draft', 'active'),
            ('draft', 'annulled'),
            ('active', 'validated'),
            ('active', 'annulled'),
            ('validated', 'active'),
            ('validated', 'done'),
            ('validated', 'annulled'),
            ))
        cls._buttons.update({
            'activate': {
                'invisible': ~Eval('state').in_(['draft', 'validated']),
                'icon': If(Eval('state') == 'draft', 'tryton-forward',
                    'tryton-back'),
                'depends': ['state'],
                },
            'view_data': {
                'invisible': Eval('state') == 'draft',
                'depends': ['state'],
                },
            'view_grouped_data': {
                'invisible': Eval('state') == 'draft',
                'depends': ['state'],
                },
            'validate_': {
                'invisible': Eval('state') != 'active',
                'icon': 'tryton-forward',
                'depends': ['state'],
                },
            'confirm': {
                'invisible': Eval('state') != 'validated',
                'icon': 'tryton-ok',
                'depends': ['state'],
                },
            'annul': {
                'invisible': ~Eval('state').in_(
                    ['draft', 'active', 'validated']),
                'icon': 'tryton-cancel',
                'depends': ['state'],
                },
            })

    @staticmethod
    def default_state():
        return 'draft'

    def get_date(self, name):
        return self.compilation.date_time

    @classmethod
    def search_date(cls, name, clause):
        return [('compilation.date_time',) + tuple(clause[1:])]

    @classmethod
    def order_date(cls, tables):
        Compilation = Pool().get('lims.interface.compilation')
        field = Compilation._fields['date_time']
        table, _ = tables[None]
        compilation_tables = tables.get('compilation')
        if compilation_tables is None:
            compilation = Compilation.__table__()
            compilation_tables = {
                None: (compilation, compilation.id == table.compilation),
                }
            tables['compilation'] = compilation_tables
        return field.convert_order('date_time', compilation_tables,
            Compilation)

    def get_planning_date(self, name):
        return self.planification and self.planification.date or None

    @classmethod
    def search_planning_date(cls, name, clause):
        return [('planification.date',) + tuple(clause[1:])]

    @classmethod
    def get_fields(cls, sheets, names):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        ModelData = pool.get('ir.model.data')
        Field = pool.get('lims.interface.table.field')
        notebook_line = pool.get('lims.notebook.line').__table__()

        _ZERO = Decimal(0)
        digits = cls.completion_percentage.digits[1]
        result_modifiers = [
            ModelData.get_id('lims', 'result_modifier_d'),
            ModelData.get_id('lims', 'result_modifier_nd'),
            ModelData.get_id('lims', 'result_modifier_pos'),
            ModelData.get_id('lims', 'result_modifier_neg'),
            ModelData.get_id('lims', 'result_modifier_ni'),
            ModelData.get_id('lims', 'result_modifier_abs'),
            ModelData.get_id('lims', 'result_modifier_pre')]

        result = {
            'urgent': {},
            'samples_qty': {},
            'partial_analysys': {},
            'completion_percentage': {},
            }
        for s in sheets:
            sql_table = Table(s.compilation.table.name)
            sql_join = sql_table.join(notebook_line,
                condition=sql_table.notebook_line == notebook_line.id)

            cursor.execute(*sql_table.select(Count(Literal('*')),
                where=((sql_table.compilation == s.compilation.id) &
                    (sql_table.notebook_line != Null))))
            total = cursor.fetchone()[0]

            results = _ZERO
            if s.state != 'draft':
                table_id = s.compilation.table.id

                result_field = None
                result_column = Field.search([
                    ('table', '=', table_id),
                    ('transfer_field', '=', True),
                    ('related_line_field.name', '=', 'result'),
                    ])
                if result_column:
                    result_field = result_column[0].name
                    result_field_type = result_column[0].type

                literal_result_column = Field.search([
                    ('table', '=', table_id),
                    ('transfer_field', '=', True),
                    ('related_line_field.name', '=', 'literal_result'),
                    ])
                literal_result_field = (literal_result_column and
                    literal_result_column[0].name or None)

                result_modifier_column = Field.search([
                    ('table', '=', table_id),
                    ('transfer_field', '=', True),
                    ('related_line_field.name', '=', 'result_modifier'),
                    ])
                result_modifier_field = (result_modifier_column and
                    result_modifier_column[0].name or None)

                result_clause = Literal(False)
                if result_field:
                    if result_field_type == 'char':
                        result_clause |= (Coalesce(Column(sql_table,
                            result_field), '') != '')
                    else:
                        result_clause |= (Column(sql_table,
                            result_field) != Null)
                if literal_result_field:
                    result_clause |= (Coalesce(Column(sql_table,
                        literal_result_field), '') != '')
                if result_modifier_field:
                    result_clause |= (Column(sql_table,
                        result_modifier_field).in_(result_modifiers))

                cursor.execute(*sql_join.select(Count(Literal('*')),
                    where=(sql_table.compilation == s.compilation.id) & (
                        (notebook_line.end_date != Null) |
                        (sql_table.annulled == Literal(True)) |
                        result_clause)))
                results = cursor.fetchone()[0]

            result['urgent'][s.id] = False
            cursor.execute(*sql_join.select(Count(Literal('*')),
                where=(sql_table.compilation == s.compilation.id) &
                    (notebook_line.urgent == Literal(True))))
            if cursor.fetchone()[0] > 0:
                result['urgent'][s.id] = True

            samples = {}
            cursor.execute(*sql_join.select(notebook_line.notebook,
                notebook_line.analysis,
                where=sql_table.compilation == s.compilation.id))
            for x in cursor.fetchall():
                if x[0] not in samples:
                    samples[x[0]] = []
                samples[x[0]].append(x[1])
            result['samples_qty'][s.id] = len(samples)

            result['partial_analysys'][s.id] = False
            template_analysis = [ta.analysis.id
                for ta in s.template.analysis]
            for k, v in samples.items():
                if not all(x in v for x in template_analysis):
                    result['partial_analysys'][s.id] = True
                    break

            result['completion_percentage'][s.id] = _ZERO
            if total and results:
                result['completion_percentage'][s.id] = Decimal(
                    results / Decimal(total)
                    ).quantize(Decimal(str(10 ** -digits)))

        return result

    def get_interface(self, name):
        return self.compilation.interface.id

    def get_out_of_ranges(self, name):
        # TODO: improve perf
        pool = Pool()
        Column = pool.get('lims.interface.column')
        Data = pool.get('lims.interface.data')

        res = False

        validation_column = Column.search([
            ('interface', '=', self.interface),
            ('validation_column', '=', True)
            ])
        if not len(validation_column):
            return res
        validation_column = validation_column[0].alias
        with Transaction().set_context(
                lims_interface_table=self.compilation.table.id):
            clause = [('compilation', '=', self.compilation.id)]
            lines = Data.search(clause)
            for line in lines:
                try:
                    if getattr(line, validation_column):
                        res = True
                        break
                except AttributeError:
                    pass

        return res

    @classmethod
    def get_notebook_lines(cls, records):
        pool = Pool()
        Data = pool.get('lims.interface.data')
        notebook_lines = []
        for record in records:
            with Transaction().set_context(
                    lims_interface_table=record.compilation.table.id):
                lines = Data.search([
                    ('compilation', '=', record.compilation.id),
                    ])
                notebook_lines += filter(None,
                    [line.notebook_line for line in lines])

        return notebook_lines

    @classmethod
    def create(cls, vlist):
        vlist = cls.set_number(vlist)
        sheets = super().create(vlist)
        cls.update_compilation(sheets)
        return sheets

    @classmethod
    def set_number(cls, vlist):
        pool = Pool()
        Config = pool.get('lims.configuration')

        config = Config(1)
        if not config.analysis_sheet_sequence:
            return vlist

        vlist = [x.copy() for x in vlist]
        for values in vlist:
            number = config.analysis_sheet_sequence.get()
            values['number'] = number
        return vlist

    @classmethod
    def update_compilation(cls, sheets):
        Compilation = Pool().get('lims.interface.compilation')
        to_save = []
        for s in sheets:
            compilation = Compilation(s.compilation.id)
            compilation.analysis_sheet = s.id
            to_save.append(compilation)
        Compilation.save(to_save)

    @classmethod
    def delete(cls, sheets):
        Compilation = Pool().get('lims.interface.compilation')
        for s in sheets:
            if s.state == 'done':
                raise UserError(gettext(
                    'lims_analysis_sheet.delete_done_sheet'))
        compilations = [s.compilation for s in sheets]
        super().delete(sheets)
        Compilation.delete(compilations)

    @classmethod
    @ModelView.button
    @Workflow.transition('active')
    @set_state_info('activated')
    def activate(cls, sheets):
        pool = Pool()
        Data = pool.get('lims.interface.data')
        NotebookLine = pool.get('lims.notebook.line')
        Compilation = pool.get('lims.interface.compilation')
        Date = pool.get('ir.date')

        today = Date.today()

        for s in sheets:
            t_analysis_ids = [ta.analysis.id for ta in s.template.analysis]

            notebooks_ids, notebook_lines_ids = [], []
            with Transaction().set_context(
                    lims_interface_table=s.compilation.table.id):
                lines = Data.search([('compilation', '=', s.compilation.id)])
                for line in lines:
                    nb_line = line.notebook_line
                    if nb_line:
                        notebooks_ids.append(nb_line.notebook.id)
                        notebook_lines_ids.append(nb_line.id)
            if notebooks_ids:
                clause = [
                    ('notebook', 'in', notebooks_ids),
                    ('analysis', 'in', t_analysis_ids),
                    ('analysis.behavior', '=', 'internal_relation'),
                    ('result', 'in', (None, '')),
                    ('end_date', '=', None),
                    ('annulment_date', '=', None),
                    ]
                notebook_lines = NotebookLine.search(clause)
                if notebook_lines:
                    s.create_lines(notebook_lines)
                    notebook_lines_ids.extend(nl.id for nl in notebook_lines)

                notebook_lines = NotebookLine.browse(notebook_lines_ids)
                NotebookLine.write(notebook_lines,
                    {'analysis_sheet_activated_date': today})

        Compilation.activate([s.compilation for s in sheets])

    @classmethod
    @ModelView.button_action(
        'lims_analysis_sheet.wiz_analysis_sheet_open_data')
    def view_data(cls, sheets):
        pass

    @classmethod
    @ModelView.button_action(
        'lims_analysis_sheet.wiz_analysis_sheet_edit_multi_sample_data')
    def view_grouped_data(cls, sheets):
        pass

    @classmethod
    @ModelView.button
    @Workflow.transition('validated')
    @set_state_info('validated')
    def validate_(cls, sheets):
        Compilation = Pool().get('lims.interface.compilation')
        cls.check_results(sheets)
        cls.check_controls(sheets)
        Compilation.validate_([s.compilation for s in sheets])

    @classmethod
    @ModelView.button
    @Workflow.transition('done')
    @set_state_info('confirmed')
    def confirm(cls, sheets):
        Compilation = Pool().get('lims.interface.compilation')
        cls.exec_sheet_wizards(sheets)
        #cls.check_results(sheets)  # already done in validate_()
        #cls.check_controls(sheets)  # already done in validate_()
        with Transaction().set_context(avoid_accept_result=True):
            Compilation.confirm([s.compilation for s in sheets])
            cls.exec_notebook_wizards(sheets)
            cls.confirm_compilations(sheets)

    @classmethod
    def check_results(cls, sheets):
        pool = Pool()
        Field = pool.get('lims.interface.table.field')
        Data = pool.get('lims.interface.data')
        Compilation = pool.get('lims.interface.compilation')

        for s in sheets:
            table_id = s.compilation.table.id

            result_column = Field.search([
                ('table', '=', table_id),
                ('transfer_field', '=', True),
                ('related_line_field.name', '=', 'result'),
                ])
            result_field = (result_column and
                result_column[0].name or None)

            literal_result_column = Field.search([
                ('table', '=', table_id),
                ('transfer_field', '=', True),
                ('related_line_field.name', '=', 'literal_result'),
                ])
            literal_result_field = (literal_result_column and
                literal_result_column[0].name or None)

            result_modifier_column = Field.search([
                ('table', '=', table_id),
                ('transfer_field', '=', True),
                ('related_line_field.name', '=', 'result_modifier'),
                ])
            result_modifier_field = (result_modifier_column and
                result_modifier_column[0].name or None)

            if (not result_column and not literal_result_column and
                    not result_modifier_column):
                raise UserError(gettext(
                    'lims_analysis_sheet.msg_template_not_result_field'))

            with Transaction().set_context(lims_interface_table=table_id):
                lines = Data.search([('compilation', '=', s.compilation.id)])
                if not lines:
                    raise UserError(gettext(
                        'lims_analysis_sheet.msg_sheet_not_lines'))
                for line in lines:
                    if not Compilation._allow_confirm_line(line):
                        continue
                    if line.annulled:
                        continue
                    if (result_field and getattr(line,
                            result_field) not in (None, '')):
                        continue
                    if (literal_result_field and getattr(line,
                            literal_result_field) not in (None, '')):
                        continue
                    if (result_modifier_field and getattr(line,
                            result_modifier_field) and getattr(line,
                            result_modifier_field).code in (
                            'd', 'nd', 'pos', 'neg', 'ni', 'abs', 'pre')):
                        continue
                    raise UserError(gettext(
                            'lims_analysis_sheet.msg_sheet_not_results'))

    @classmethod
    def check_controls(cls, sheets):
        pool = Pool()
        Data = pool.get('lims.interface.data')
        Compilation = pool.get('lims.interface.compilation')

        for s in sheets:
            if not s.template.controls_required:
                continue
            controls_allowed = s.template.controls_allowed

            with Transaction().set_context(
                    lims_interface_table=s.compilation.table.id):
                ok = False
                lines = Data.search([('compilation', '=', s.compilation.id)])
                for line in lines:
                    if not Compilation._allow_confirm_line(line):
                        continue
                    nb_line = line.notebook_line
                    if nb_line.fraction.special_type in controls_allowed:
                        ok = True
                        break
                if not ok:
                    raise UserError(gettext(
                        'lims_analysis_sheet.msg_sheet_not_controls'))

    @classmethod
    def exec_sheet_wizards(cls, sheets):
        pool = Pool()
        EvaluateRules = pool.get('lims.analysis_sheet.evaluate_rules',
            type='wizard')
        LimitsValidation = pool.get('lims.analysis_sheet.limits_validation',
            type='wizard')

        for s in sheets:
            # Evaluate Sheet Rules
            session_id, _, _ = EvaluateRules.create()
            evaluate_rules = EvaluateRules(session_id)
            with Transaction().set_context(lims_analysis_sheet=s.id):
                evaluate_rules.transition_evaluate()

            # Validate Limits
            session_id, _, _ = LimitsValidation.create()
            limits_validation = LimitsValidation(session_id)
            with Transaction().set_context(lims_analysis_sheet=s.id,
                    unattended=True):
                limits_validation.transition_validate_limits()

        return

    @classmethod
    def exec_notebook_wizards(cls, sheets):
        pool = Pool()
        Data = pool.get('lims.interface.data')
        NotebookLine = pool.get('lims.notebook.line')
        EvaluateRules = pool.get('lims.notebook.evaluate_rules',
            type='wizard')
        CalculateInternalRelations = pool.get(
            'lims.notebook.internal_relations_calc_1',
            type='wizard')
        LimitsValidation = pool.get('lims.notebook.limits_validation',
            type='wizard')

        for s in sheets:
            notebook_ids = []
            with Transaction().set_context(
                    lims_interface_table=s.compilation.table.id):
                lines = Data.search([('compilation', '=', s.compilation.id)])
                for line in lines:
                    if line.notebook_line:
                        notebook_ids.append(line.notebook_line.notebook.id)

            for i in range(2):
                # Evaluate Notebook Rules
                session_id, _, _ = EvaluateRules.create()
                evaluate_rules = EvaluateRules(session_id)
                for notebook_id in list(set(notebook_ids)):
                    with Transaction().set_context(_check_access=True):
                        notebook_lines = NotebookLine.search([
                            ('notebook', '=', notebook_id),
                            ])
                    evaluate_rules.evaluate_rules(notebook_lines)

                # Calculate Internal Relations
                session_id, _, _ = CalculateInternalRelations.create()
                calculate_ir = CalculateInternalRelations(session_id)
                for notebook_id in list(set(notebook_ids)):
                    with Transaction().set_context(_check_access=True):
                        notebook_lines = NotebookLine.search([
                            ('notebook', '=', notebook_id),
                            ])
                    if calculate_ir.get_relations(notebook_lines):
                        calculate_ir.transition_confirm()

            # Validate Limits
            session_id, _, _ = LimitsValidation.create()
            limits_validation = LimitsValidation(session_id)
            for notebook_id in list(set(notebook_ids)):
                with Transaction().set_context(_check_access=True):
                    notebook_lines = NotebookLine.search([
                        ('notebook', '=', notebook_id),
                        ])
                limits_validation.lines_limits_validation(notebook_lines)

        return

    @classmethod
    def confirm_compilations(cls, sheets):
        pool = Pool()
        Data = pool.get('lims.interface.data')
        NotebookLine = pool.get('lims.notebook.line')
        Compilation = pool.get('lims.interface.compilation')
        Date = pool.get('ir.date')

        avoid_accept_result = Transaction().context.get('avoid_accept_result',
            False)

        now = datetime.now()
        today = Date.today()

        for s in sheets:
            with Transaction().set_context(
                    lims_interface_table=s.compilation.table.id):
                lines = Data.search([('compilation', '=', s.compilation.id)])
                for line in lines:
                    if not Compilation._allow_confirm_line(line):
                        continue
                    nb_line = line.notebook_line
                    data = {
                        'end_date': today,
                        'analysis_sheet': s.id,
                        }
                    # if the analysis was scheduled for a future date
                    if nb_line.start_date > today:
                        data['start_date'] = today
                    # if already avoided in compilations then accept here
                    if not line.annulled and (avoid_accept_result and
                            nb_line.laboratory.automatic_accept_result):
                        #data['end_date'] = today
                        data['accepted'] = True
                        data['acceptance_date'] = now
                    NotebookLine.write([nb_line], data)

    @classmethod
    @ModelView.button
    @Workflow.transition('annulled')
    @set_state_info('annulled')
    def annul(cls, sheets):
        Compilation = Pool().get('lims.interface.compilation')
        Compilation.annul([s.compilation for s in sheets])

    def get_new_compilation(self, defaults={}):
        Compilation = Pool().get('lims.interface.compilation')
        compilation = Compilation(
            table=self.template.interface.table.id,
            interface=self.template.interface.id,
            revision=self.template.interface.revision,
            )
        for field, value in defaults.items():
            setattr(compilation, field, value)
        return compilation

    def create_lines(self, lines, update_samples_list=True):
        Data = Pool().get('lims.interface.data')

        interface = self.template.interface
        schema, _ = self.compilation._get_schema()
        defaults = self.get_data_defaults()

        with Transaction().set_context(
                lims_interface_table=self.compilation.table.id):
            data = []
            for nl in lines:
                line = {
                    'compilation': self.compilation.id,
                    'notebook_line': nl.id,
                    }
                line.update(defaults)

                for k in list(schema.keys()):
                    if (schema[k]['default_value'] is not None and
                            schema[k]['default_value'].startswith('=') and
                            not schema[k]['default_value'].startswith(
                                '=REFERENCE_VALUE')):
                        path = schema[k]['default_value'][1:].split('.')
                        field = path.pop(0)
                        try:
                            value = getattr(nl, field)
                            while path:
                                field = path.pop(0)
                                value = getattr(value, field)
                        except AttributeError:
                            value = None
                        if schema[k]['grouped_repetitions'] is None:
                            line[k] = value
                        else:
                            reps = (schema[k]['grouped_repetitions'] or 1) + 1
                            for rep in range(1, reps):
                                line['%s_%s' % (k, rep)] = value

                if interface.fraction_field:
                    if interface.fraction_field.type_ == 'many2one':
                        line[interface.fraction_field.alias] = nl.fraction.id
                    else:
                        line[interface.fraction_field.alias] = (
                            nl.fraction.number)
                if interface.analysis_field:
                    if interface.analysis_field.type_ == 'many2one':
                        line[interface.analysis_field.alias] = nl.analysis.id
                    else:
                        line[interface.analysis_field.alias] = (
                            nl.analysis.rec_name)
                if interface.method_field:
                    if interface.method_field.type_ == 'many2one':
                        line[interface.method_field.alias] = nl.method.id
                    else:
                        line[interface.method_field.alias] = (
                            nl.method.rec_name)
                if interface.repetition_field:
                    line[interface.repetition_field.alias] = nl.repetition
                data.append(line)

            if data:
                Data.create(data)

            if update_samples_list:
                self._update_samples_list()

    def _update_samples_list(self):
        Data = Pool().get('lims.interface.data')

        samples = set()
        with Transaction().set_context(
                lims_interface_table=self.compilation.table.id):
            data_lines = Data.search([
                ('compilation', '=', self.compilation.id),
                ('notebook_line', '!=', None),
                ])
            for data_line in data_lines:
                samples.add(data_line.notebook_line.fraction.sample.number)
        self.samples = ' - '.join(list(samples))
        self.save()

    def get_data_defaults(self):
        defaults = {}
        schema, _ = self.compilation._get_schema()
        for k in list(schema.keys()):
            value = schema[k]['default_value']
            if value in (None, ''):
                continue
            if value.startswith('=REFERENCE_VALUE'):
                parser = formulas.Parser()
                ast = parser.ast(value)[1].compile()
                try:
                    value = ast()
                except schedula.utils.exc.DispatcherError as e:
                    raise UserError(e.args[0] % e.args[1:])
                if isinstance(value, list):
                    value = str(value)
                elif not isinstance(value, ALLOWED_RESULT_TYPES):
                    value = value.tolist()
                if isinstance(value, formulas.tokens.operand.XlError):
                    value = None
                elif isinstance(value, list):
                    for x in chain(*value):
                        if isinstance(x, formulas.tokens.operand.XlError):
                            value = None
                if schema[k]['grouped_repetitions'] is None:
                    defaults[k] = value
                else:
                    reps = (schema[k]['grouped_repetitions'] or 1) + 1
                    for rep in range(1, reps):
                        defaults['%s_%s' % (k, rep)] = value
                continue
            if value.startswith('='):
                continue

            if schema[k]['type'] == 'integer':
                default_value = int(value)
            elif schema[k]['type'] == 'float':
                default_value = float(value)
            elif schema[k]['type'] == 'numeric':
                default_value = Decimal(str(value))
            elif schema[k]['type'] == 'boolean':
                default_value = bool(value)
            elif schema[k]['type'] == 'date':
                default_value = str2date(value,
                    self.compilation.interface.language)
            elif schema[k]['type'] == 'many2one':
                resource = get_model_resource(
                    schema[k]['model_name'], value,
                    schema[k]['field_name'])
                default_value = resource and resource[0].id
            else:
                default_value = str(value)

            if schema[k]['grouped_repetitions'] is None:
                defaults[k] = default_value
            else:
                reps = (schema[k]['grouped_repetitions'] or 1) + 1
                for rep in range(1, reps):
                    defaults['%s_%s' % (k, rep)] = default_value

        return defaults


class OpenAnalysisSheetData(Wizard):
    'Open Analysis Sheet Data'
    __name__ = 'lims.analysis_sheet.open_data'

    start = StateAction('lims_interface.act_open_compilation_data')

    def do_start(self, action):
        AnalysisSheet = Pool().get('lims.analysis_sheet')

        context = {
            'lims_analysis_sheet': None,
            'lims_interface_compilation': None,
            'lims_interface_table': None,
            'lims_interface_readonly': False,
            }
        domain = [('compilation', '=', None)]
        name = ''

        sheet_id = Transaction().context.get('active_id', None)
        if sheet_id:
            sheet = AnalysisSheet(sheet_id)
            readonly = (sheet.state in ('validated', 'done', 'annulled'))
            context['lims_analysis_sheet'] = sheet.id
            context['lims_interface_compilation'] = sheet.compilation.id
            context['lims_interface_table'] = sheet.compilation.table.id
            context['lims_interface_readonly'] = readonly
            domain = [('compilation', '=', sheet.compilation.id)]
            name = ' (%s - %s)' % (sheet.number, sheet.template.name)
        action['pyson_context'] = PYSONEncoder().encode(context)
        action['pyson_domain'] = PYSONEncoder().encode(domain)
        action['name'] += name
        return action, {}


class ExportAnalysisSheetFileStart(ModelView):
    'Export Analysis Sheet File'
    __name__ = 'lims.analysis_sheet.export_file.start'

    file = fields.Binary('File', readonly=True)


class ExportAnalysisSheetFile(Wizard):
    'Export Analysis Sheet File'
    __name__ = 'lims.analysis_sheet.export_file'

    start = StateTransition()
    export_ = StateView('lims.analysis_sheet.export_file.start',
        'lims_analysis_sheet.analysis_sheet_export_start_view_form', [
            Button('Close', 'end', 'tryton-close'),
            ])

    def _get_analysis_sheet_id(self):
        return Transaction().context.get('lims_analysis_sheet',
            Transaction().context.get('active_id', None))

    def transition_start(self):
        AnalysisSheet = Pool().get('lims.analysis_sheet')

        sheet_id = self._get_analysis_sheet_id()
        if not sheet_id:
            return 'end'

        sheet = AnalysisSheet(sheet_id)
        if sheet.state == 'draft':
            return 'end'

        file_type = sheet.template.interface.export_file_type
        if not file_type:
            return 'end'

        return 'export_'

    def default_export_(self, fields):
        file_ = self.get_file(self._get_analysis_sheet_id())
        cast = self.export_.__class__.file.cast
        return {
            'file': cast(file_) if file_ else None,
            }

    def get_file(self, sheet_id):
        AnalysisSheet = Pool().get('lims.analysis_sheet')
        sheet = AnalysisSheet(sheet_id)
        file_type = sheet.template.interface.export_file_type
        return getattr(self, 'export_%s' % file_type)(sheet)

    def export_csv(self, sheet, newline='\n'):
        pool = Pool()
        Column = pool.get('lims.interface.column')
        Data = pool.get('lims.interface.data')

        columns = Column.search([
            ('interface', '=', sheet.template.interface),
            ('destination_column', '!=', None),
            ], order=[('destination_column', 'ASC')])
        if not columns:
            return
        cols = [c.alias for c in columns]

        separator = {
            'comma': ',',
            'colon': ':',
            'semicolon': ';',
            'tab': '\t',
            'space': ' ',
            'other': sheet.template.interface.export_field_separator_other,
            }
        delimiter = separator[sheet.template.interface.export_field_separator]

        order = None
        if sheet.template.interface.export_order_field:
            order = [(sheet.template.interface.export_order_field.alias,
                'ASC')]

        file_ = StringIO(newline=newline)
        with Transaction().set_context(
                lims_interface_compilation=sheet.compilation.id,
                lims_interface_table=sheet.compilation.table.id):
            lines = Data.search([(
                'compilation', '=', sheet.compilation.id),
                ], order=order)
            for line in lines:
                entry = ''
                for field in cols:
                    if entry:
                        entry += delimiter
                    val = getattr(line, field)
                    entry += str(val if val is not None else '')
                entry += newline
                file_.write(entry)

        if not file_:
            return

        return str(file_.getvalue()).encode('utf-8')

    def export_txt(self, sheet):
        return

    def export_excel(self, sheet):
        return


class PrintAnalysisSheetReportAsk(ModelView):
    'Analysis Sheet Report'
    __name__ = 'lims.analysis_sheet.print_report.ask'

    print_expression_column = fields.Boolean('Print formula column')


class PrintAnalysisSheetReport(Wizard):
    'Analysis Sheet Report'
    __name__ = 'lims.analysis_sheet.print_report'

    start = StateTransition()
    ask = StateView('lims.analysis_sheet.print_report.ask',
        'lims_analysis_sheet.analysis_sheet_print_report_ask_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print', 'print_', 'tryton-ok', default=True),
            ])
    print_ = StateAction('lims_analysis_sheet.report_analysis_sheet')

    def _get_analysis_sheet_id(self):
        return Transaction().context.get('lims_analysis_sheet',
            Transaction().context.get('active_id', None))

    def transition_start(self):
        AnalysisSheet = Pool().get('lims.analysis_sheet')

        sheet_id = self._get_analysis_sheet_id()
        if not sheet_id:
            return 'end'

        sheet = AnalysisSheet(sheet_id)
        if sheet.state == 'draft':
            return 'end'

        if not sheet.template.report:
            raise UserError(gettext(
                'lims_analysis_sheet.msg_template_not_report',
                template=sheet.template.rec_name))

        return 'ask'

    def do_print_(self, action):
        pool = Pool()
        AnalysisSheet = pool.get('lims.analysis_sheet')

        sheet = AnalysisSheet(self._get_analysis_sheet_id())

        report_name = sheet.template.report.report_name
        AnalysisSheetReport = pool.get(report_name, type='report')
        result = AnalysisSheetReport.execute([sheet.id],
            {'execute': True, 'id': sheet.id,
                'print_expression_column': self.ask.print_expression_column})
        AnalysisSheet.write([sheet], {
            'report_format': result[0],
            'report_cache': result[1],
            })

        data = {
            'id': self._get_analysis_sheet_id(),
            }
        return action, data


class AnalysisSheetReport(Report):
    'Analysis Sheet Report'
    __name__ = 'lims.analysis_sheet.report'

    @classmethod
    def execute(cls, ids, data):
        AnalysisSheet = Pool().get('lims.analysis_sheet')

        sheet = AnalysisSheet(data.get('id'))
        if data.get('execute') or not sheet.report_cache:
            return super().execute(ids, data)
        return (sheet.report_format, sheet.report_cache, False, sheet.number)

    @classmethod
    def _get_records(cls, ids, model, data):
        return []

    @classmethod
    def get_context(cls, records, header, data):
        pool = Pool()
        AnalysisSheet = pool.get('lims.analysis_sheet')
        Field = pool.get('lims.interface.table.field')
        Data = pool.get('lims.interface.data')

        report_context = super().get_context(records, header, data)

        sheet = AnalysisSheet(data.get('id'))
        print_expression_column = data.get('print_expression_column')
        report_context['sheet'] = sheet

        limit = 20
        alias = []

        # Columns
        columns = {}
        i = 0
        fields = Field.search([('table', '=', sheet.compilation.table.id)])
        for field in fields:
            if not print_expression_column and field.formula:
                continue
            alias.append(field.name)
            columns[i] = field.string
            i += 1
        for x in range(i, limit):
            columns[x] = ''
        report_context['columns'] = columns

        # Rows
        rows = []
        with Transaction().set_context(
                lims_interface_table=sheet.compilation.table.id):
            lines = Data.search([('compilation', '=', sheet.compilation.id)])
            for line in lines:
                row = {}
                i = 0
                for field_name in alias:
                    row[i] = getattr(line, field_name)
                    i += 1
                for x in range(i, limit):
                    row[x] = ''
                rows.append(row)
        report_context['rows'] = rows

        return report_context


class ImportAnalysisSheetFileStart(ModelView):
    'Import Analysis Sheet File'
    __name__ = 'lims.analysis_sheet.import_file.start'

    origin_file = fields.Binary('Origin File', filename='file_name',
        required=True)
    file_name = fields.Char('Name')


class ImportAnalysisSheetFile(Wizard):
    'Import Analysis Sheet File'
    __name__ = 'lims.analysis_sheet.import_file'

    start = StateTransition()
    ask_file = StateView('lims.analysis_sheet.import_file.start',
        'lims_analysis_sheet.analysis_sheet_import_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Collect', 'collect', 'tryton-ok', default=True),
            ])
    collect = StateTransition()

    def _get_analysis_sheet_id(self):
        return Transaction().context.get('lims_analysis_sheet',
            Transaction().context.get('active_id', None))

    def transition_start(self):
        AnalysisSheet = Pool().get('lims.analysis_sheet')

        sheet_id = self._get_analysis_sheet_id()
        if not sheet_id:
            return 'end'

        sheet = AnalysisSheet(sheet_id)
        if sheet.state != 'active':
            return 'end'

        return 'ask_file'

    def transition_collect(self):
        pool = Pool()
        AnalysisSheet = pool.get('lims.analysis_sheet')
        CompilationOrigin = pool.get('lims.interface.compilation.origin')

        sheet_id = self._get_analysis_sheet_id()
        sheet = AnalysisSheet(sheet_id)

        origin = CompilationOrigin(
            compilation=sheet.compilation.id,
            origin_file=self.ask_file.origin_file,
            file_name=self.ask_file.file_name,
            )
        origin.save()

        sheet.compilation.collect([sheet.compilation])
        return 'end'

    def end(self):
        return 'reload'


class OpenAnalysisSheetSample(Wizard):
    'Open Analysis Sheet Samples'
    __name__ = 'lims.analysis_sheet.open_sample'

    start = StateAction('lims.act_lims_notebook_list')

    def _get_analysis_sheet_id(self):
        return Transaction().context.get('lims_analysis_sheet',
            Transaction().context.get('active_id', None))

    def do_start(self, action):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        AnalysisSheet = pool.get('lims.analysis_sheet')
        notebook_line = pool.get('lims.notebook.line').__table__()

        sheet_id = self._get_analysis_sheet_id()
        if not sheet_id:
            return 'end'

        sheet = AnalysisSheet(sheet_id)
        sql_table = Table(sheet.compilation.table.name)
        sql_join = sql_table.join(notebook_line,
            condition=sql_table.notebook_line == notebook_line.id)
        cursor.execute(*sql_join.select(notebook_line.notebook,
            where=sql_table.compilation == sheet.compilation.id))

        samples = set()
        for x in cursor.fetchall():
            samples.add(x[0])

        domain = [('id', 'in', list(samples))]
        action['pyson_domain'] = PYSONEncoder().encode(domain)
        action['name'] += ' (%s - %s)' % (sheet.number, sheet.template.name)
        return action, {}
