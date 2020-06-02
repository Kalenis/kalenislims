# This file is part of lims_analysis_sheet module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from io import StringIO
from decimal import Decimal
from datetime import datetime

from trytond.model import Workflow, ModelView, ModelSQL, fields, Unique
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

__all__ = ['TemplateAnalysisSheet', 'TemplateAnalysisSheetAnalysis',
    'TemplateAnalysisSheetAnalysisExpression', 'AnalysisSheet',
    'OpenAnalysisSheetData', 'PrintAnalysisSheetReportAsk',
    'PrintAnalysisSheetReport', 'AnalysisSheetReport',
    'ExportAnalysisSheetFileStart', 'ExportAnalysisSheetFile',
    'ImportAnalysisSheetFileStart', 'ImportAnalysisSheetFile']


class TemplateAnalysisSheet(ModelSQL, ModelView):
    'Analysis Sheet Template'
    __name__ = 'lims.template.analysis_sheet'

    interface = fields.Many2One('lims.interface', 'Device Interface',
        required=True, domain=[
            ('kind', '=', 'template'),
            ('state', '=', 'active')],
        states={'readonly': Bool(Eval('interface'))})
    name = fields.Char('Name', required=True)
    analysis = fields.One2Many('lims.template.analysis_sheet.analysis',
        'template', 'Analysis', required=True,
        context={'interface_id': Eval('interface')},
        depends=['interface'])
    comments = fields.Text('Comments')
    pending_fractions = fields.Function(fields.Integer('Pending fractions'),
        'get_pending_fractions')
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
        states={'required': Bool(Eval('controls_required'))},
        depends=['controls_required'])

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
    def get_pending_fractions(cls, records, name):
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
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        Analysis = pool.get('lims.analysis')
        TemplateAnalysis = pool.get('lims.template.analysis_sheet.analysis')

        res = dict((r.id, None) for r in records)

        date_from = context.get('date_from') or None
        date_to = context.get('date_to') or None
        if not (date_from and date_to):
            return res

        cursor.execute('SELECT nl.id '
            'FROM "' + NotebookLine._table + '" nl '
                'INNER JOIN "' + PlanificationServiceDetail._table +
                '" psd ON psd.notebook_line = nl.id '
                'INNER JOIN "' + PlanificationDetail._table + '" pd '
                'ON psd.detail = pd.id '
                'INNER JOIN "' + Planification._table + '" p '
                'ON pd.planification = p.id '
            'WHERE p.state = \'preplanned\'')
        preplanned_lines = [x[0] for x in cursor.fetchall()]
        preplanned_lines_ids = ', '.join(str(x)
            for x in [0] + preplanned_lines)

        sql_select = 'SELECT nl.analysis, nl.method, frc.id '
        sql_from = (
            'FROM "' + NotebookLine._table + '" nl '
            'INNER JOIN "' + Analysis._table + '" nla '
            'ON nla.id = nl.analysis '
            'INNER JOIN "' + Notebook._table + '" nb '
            'ON nb.id = nl.notebook '
            'INNER JOIN "' + Fraction._table + '" frc '
            'ON frc.id = nb.fraction '
            'INNER JOIN "' + EntryDetailAnalysis._table + '" ad '
            'ON ad.id = nl.analysis_detail ')
        sql_where = (
            'WHERE ad.plannable = TRUE '
            'AND nl.start_date IS NULL '
            'AND nl.annulled = FALSE '
            'AND nl.id NOT IN (' + preplanned_lines_ids + ') '
            'AND nla.behavior != \'internal_relation\' '
            'AND ad.confirmation_date::date >= %s::date '
            'AND ad.confirmation_date::date <= %s::date')

        with Transaction().set_user(0):
            cursor.execute(sql_select + sql_from + sql_where,
                (date_from, date_to,))
        notebook_lines = cursor.fetchall()
        if not notebook_lines:
            return res

        templates = {}
        for nl in notebook_lines:
            cursor.execute('SELECT template '
                'FROM "' + TemplateAnalysis._table + '" '
                'WHERE analysis = %s '
                'AND (method = %s OR method IS NULL)',
                (nl[0], nl[1]))
            template = cursor.fetchone()
            if not template:
                continue
            if template[0] not in templates:
                templates[template[0]] = set()
            templates[template[0]].add(nl[2])

        for t_id, fractions in templates.items():
            res[t_id] = len(fractions)
        return res


class TemplateAnalysisSheetAnalysis(ModelSQL, ModelView):
    'Template Analysis'
    __name__ = 'lims.template.analysis_sheet.analysis'

    template = fields.Many2One('lims.template.analysis_sheet', 'Template',
        required=True, ondelete='CASCADE', select=True)
    analysis = fields.Many2One('lims.analysis', 'Analysis',
        required=True, select=True, domain=[('type', '=', 'analysis')])
    method = fields.Many2One('lims.lab.method', 'Method')
    expressions = fields.One2Many(
        'lims.template.analysis_sheet.analysis.expression',
        'analysis', 'Special formulas')

    @classmethod
    def validate(cls, template_analysis):
        super(TemplateAnalysisSheetAnalysis, cls).validate(template_analysis)
        for ta in template_analysis:
            ta.check_duplicated()

    def check_duplicated(self):
        clause = [
            ('id', '!=', self.id),
            ('analysis', '=', self.analysis.id),
            ]
        if self.method:
            clause.append(('method', '=', self.method.id))
        else:
            clause.append(('method', '=', None))
        duplicated = self.search(clause)
        if duplicated:
            raise UserError(gettext(
                'lims_analysis_sheet.msg_template_analysis_unique',
                analysis=self.analysis.rec_name))


class TemplateAnalysisSheetAnalysisExpression(ModelSQL, ModelView):
    'Special Formula'
    __name__ = 'lims.template.analysis_sheet.analysis.expression'

    analysis = fields.Many2One('lims.template.analysis_sheet.analysis',
        'Analysis', required=True, ondelete='CASCADE', select=True)
    column = fields.Many2One('lims.interface.column', 'Column',
        domain=['OR', ('id', '=', Eval('column')),
            ('interface', '=', Eval('context', {}).get('interface_id'))],
        required=True)
    expression = fields.Char('Formula')

    @fields.depends('column')
    def on_change_with_expression(self, name=None):
        if self.column:
            return self.column.expression


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
        ], 'State', required=True, readonly=True)
    planification = fields.Many2One('lims.planification', 'Planification',
        readonly=True)
    incomplete_sample = fields.Function(fields.Boolean('Incomplete sample'),
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

    @classmethod
    def __setup__(cls):
        super(AnalysisSheet, cls).__setup__()
        cls._order.insert(0, ('date', 'DESC'))
        t = cls.__table__()
        cls._sql_constraints += [
            ('compilation_uniq', Unique(t, t.compilation),
                'lims_analysis_sheet.msg_sheet_compilation_unique'),
            ]
        cls._transitions |= set((
            ('draft', 'active'),
            ('active', 'validated'),
            ('validated', 'active'),
            ('validated', 'done'),
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

    @classmethod
    def get_fields(cls, sheets, names):
        pool = Pool()
        ModelField = pool.get('ir.model.field')
        Field = pool.get('lims.interface.table.field')
        Data = pool.get('lims.interface.data')

        nl_result_field, = ModelField.search([
            ('model.model', '=', 'lims.notebook.line'),
            ('name', '=', 'result'),
            ])
        _ZERO = Decimal(0)
        digits = cls.completion_percentage.digits[1]

        result = {
            'urgent': {},
            'samples_qty': {},
            'incomplete_sample': {},
            'completion_percentage': {},
            }
        for s in sheets:
            result['urgent'][s.id] = False

            result_column = Field.search([
                ('table', '=', s.compilation.table.id),
                ('transfer_field', '=', True),
                ('related_line_field', '=', nl_result_field),
                ])
            result_field = result_column and result_column[0].name or None

            with Transaction().set_context(
                    lims_interface_table=s.compilation.table.id):
                lines = Data.search([('compilation', '=', s.compilation.id)])
                total = len(lines)
                results = _ZERO
                samples = {}
                for line in lines:
                    nl = line.notebook_line
                    if not nl:
                        continue

                    if nl.urgent:
                        result['urgent'][s.id] = True

                    if nl.fraction.id not in samples:
                        samples[nl.fraction.id] = []
                    samples[nl.fraction.id].append(nl.analysis.id)

                    if (result_field and getattr(line, result_field) and
                            s.state != 'draft'):
                        results += 1

                result['samples_qty'][s.id] = len(samples)

                result['incomplete_sample'][s.id] = False
                template_analysis = [ta.analysis.id
                    for ta in s.template.analysis]
                for k, v in samples.items():
                    if not all(x in v for x in template_analysis):
                        result['incomplete_sample'][s.id] = True
                        break

                result['completion_percentage'][s.id] = _ZERO
                if total and results:
                    result['completion_percentage'][s.id] = Decimal(
                        results / Decimal(total)
                        ).quantize(Decimal(str(10 ** -digits)))

        return result

    @classmethod
    def create(cls, vlist):
        vlist = cls.set_number(vlist)
        sheets = super(AnalysisSheet, cls).create(vlist)
        cls.update_compilation(sheets)
        return sheets

    @classmethod
    def set_number(cls, vlist):
        pool = Pool()
        Config = pool.get('lims.configuration')
        Sequence = pool.get('ir.sequence')

        config = Config(1)
        if not config.analysis_sheet_sequence:
            return vlist

        vlist = [x.copy() for x in vlist]
        for values in vlist:
            number = Sequence.get_id(config.analysis_sheet_sequence.id)
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
        compilations = [s.compilation for s in sheets]
        super(AnalysisSheet, cls).delete(sheets)
        Compilation.delete(compilations)

    @classmethod
    @ModelView.button
    @Workflow.transition('active')
    def activate(cls, sheets):
        pool = Pool()
        Data = pool.get('lims.interface.data')
        NotebookLine = pool.get('lims.notebook.line')
        Compilation = pool.get('lims.interface.compilation')

        for s in sheets:
            t_analysis_ids = [ta.analysis.id for ta in s.template.analysis]

            notebooks_ids = []
            with Transaction().set_context(
                    lims_interface_table=s.compilation.table.id):
                lines = Data.search([('compilation', '=', s.compilation.id)])
                for line in lines:
                    nl = line.notebook_line
                    if nl:
                        notebooks_ids.append(nl.notebook.id)
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

        Compilation.activate([s.compilation for s in sheets])

    @classmethod
    @ModelView.button_action(
        'lims_analysis_sheet.wiz_analysis_sheet_open_data')
    def view_data(cls, sheets):
        pass

    @classmethod
    @ModelView.button
    @Workflow.transition('validated')
    def validate_(cls, sheets):
        Compilation = Pool().get('lims.interface.compilation')
        cls.check_results(sheets)
        cls.check_controls(sheets)
        Compilation.validate_([s.compilation for s in sheets])

    @classmethod
    @ModelView.button
    @Workflow.transition('done')
    def confirm(cls, sheets):
        Compilation = Pool().get('lims.interface.compilation')
        cls.check_results(sheets)
        cls.check_controls(sheets)
        Compilation.confirm([s.compilation for s in sheets])
        cls.confirm_compilations(sheets)

    @classmethod
    def check_results(cls, sheets):
        pool = Pool()
        ModelField = pool.get('ir.model.field')
        Field = pool.get('lims.interface.table.field')
        Data = pool.get('lims.interface.data')

        nl_result_field, = ModelField.search([
            ('model.model', '=', 'lims.notebook.line'),
            ('name', '=', 'result'),
            ])

        for s in sheets:
            result_column = Field.search([
                ('table', '=', s.compilation.table.id),
                ('transfer_field', '=', True),
                ('related_line_field', '=', nl_result_field),
                ])
            if not result_column:
                raise UserError(gettext(
                    'lims_analysis_sheet.msg_template_not_result_field'))
            result_field = result_column[0].name
            with Transaction().set_context(
                    lims_interface_table=s.compilation.table.id):
                lines = Data.search([('compilation', '=', s.compilation.id)])
                if not lines:
                    raise UserError(gettext(
                        'lims_analysis_sheet.msg_sheet_not_lines'))
                for line in lines:
                    if not getattr(line, result_field) and not line.annulled:
                        raise UserError(gettext(
                            'lims_analysis_sheet.msg_sheet_not_results'))

    @classmethod
    def check_controls(cls, sheets):
        pool = Pool()
        Data = pool.get('lims.interface.data')

        for s in sheets:
            if not s.template.controls_required:
                continue
            controls_allowed = s.template.controls_allowed

            with Transaction().set_context(
                    lims_interface_table=s.compilation.table.id):
                ok = False
                lines = Data.search([('compilation', '=', s.compilation.id)])
                for line in lines:
                    nl = line.notebook_line
                    if nl and nl.fraction.special_type in controls_allowed:
                        ok = True
                        break
                if not ok:
                    raise UserError(gettext(
                        'lims_analysis_sheet.msg_sheet_not_controls'))

    @classmethod
    def confirm_compilations(cls, sheets):
        pool = Pool()
        Data = pool.get('lims.interface.data')
        NotebookLine = pool.get('lims.notebook.line')

        now = datetime.now()
        today = now.date()
        for s in sheets:
            with Transaction().set_context(
                    lims_interface_table=s.compilation.table.id):
                lines = Data.search([('compilation', '=', s.compilation.id)])
                for line in lines:
                    nb_line = line.notebook_line
                    if not nb_line:
                        continue
                    data = {
                        'end_date': today,
                        'analysis_sheet': s.id,
                        }
                    if line.annulled:
                        data.update({
                            'result_modifier': 'na',
                            'annulled': True,
                            'annulment_date': now,
                            'report': False,
                            })
                    NotebookLine.write([nb_line], data)

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

    def create_lines(self, lines):
        Data = Pool().get('lims.interface.data')

        interface = self.template.interface

        fixed_values = {}
        schema, _ = self.compilation._get_schema()
        for k in list(schema.keys()):
            if schema[k]['is_fixed_value']:
                value = schema[k]['fixed_value']
                if value.startswith('='):
                    continue
                if schema[k]['type'] == 'boolean':
                    fixed_values[k] = bool(value)
                elif schema[k]['type'] == 'date':
                    fixed_values[k] = str2date(value, interface.language)
                elif schema[k]['type'] == 'many2one':
                    resource = get_model_resource(schema[k]['model_name'],
                        value, schema[k]['field_name'])
                    fixed_values[k] = resource and resource[0].id
                else:
                    fixed_values[k] = value

        with Transaction().set_context(
                lims_interface_table=self.compilation.table.id):
            data = []
            for nl in lines:
                line = {'compilation': self.compilation.id}
                line.update(fixed_values)

                for k in list(schema.keys()):
                    if (schema[k]['is_fixed_value'] and schema[k][
                            'fixed_value'].startswith('=')):
                        path = schema[k]['fixed_value'][1:].split('.')
                        field = path.pop(0)
                        try:
                            value = getattr(nl, field)
                            while path:
                                field = path.pop(0)
                                value = getattr(value, field)
                        except AttributeError:
                            value = None
                        line[k] = value
                line['notebook_line'] = nl.id
                if interface.analysis_field:
                    if interface.analysis_field.type_ == 'many2one':
                        line[interface.analysis_field.alias] = nl.analysis.id
                    else:
                        line[interface.analysis_field.alias] = (
                            nl.analysis.rec_name)
                if interface.fraction_field:
                    if interface.fraction_field.type_ == 'many2one':
                        line[interface.fraction_field.alias] = nl.fraction.id
                    else:
                        line[interface.fraction_field.alias] = (
                            nl.fraction.number)
                if interface.repetition_field:
                    line[interface.repetition_field.alias] = nl.repetition
                data.append(line)

            if data:
                Data.create(data)


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
            }
        domain = [('compilation', '=', None)]
        name = ''

        sheet_id = Transaction().context.get('active_id', None)
        if sheet_id:
            sheet = AnalysisSheet(sheet_id)
            context['lims_analysis_sheet'] = sheet.id
            context['lims_interface_compilation'] = sheet.compilation.id
            context['lims_interface_table'] = sheet.compilation.table.id
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

        file_ = StringIO(newline=newline)
        with Transaction().set_context(
                lims_interface_compilation=sheet.compilation.id,
                lims_interface_table=sheet.compilation.table.id):
            lines = Data.search([(
                'compilation', '=', sheet.compilation.id),
                ])
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
        pool = Pool()
        AnalysisSheet = pool.get('lims.analysis_sheet')

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
            return super(AnalysisSheetReport, cls).execute(ids, data)
        return (sheet.report_format, sheet.report_cache, False, sheet.number)

    @classmethod
    def _get_records(cls, ids, model, data):
        return []

    @classmethod
    def get_context(cls, records, data):
        pool = Pool()
        AnalysisSheet = pool.get('lims.analysis_sheet')
        Field = pool.get('lims.interface.table.field')
        Data = pool.get('lims.interface.data')

        report_context = super(AnalysisSheetReport,
            cls).get_context(records, data)

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
