# This file is part of lims_analysis_sheet module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from io import StringIO
import sql

from trytond.model import Workflow, ModelView, ModelSQL, fields, Unique
from trytond.wizard import Wizard, StateView, StateAction, Button
from trytond.pool import Pool, PoolMeta
from trytond.pyson import PYSONEncoder, Eval, Bool, Or
from trytond.transaction import Transaction
from trytond.report import Report
from trytond.exceptions import UserError
from trytond.i18n import gettext

__all__ = ['TemplateAnalysisSheet', 'TemplateAnalysisSheetAnalysis',
    'AnalysisSheet', 'OpenAnalysisSheetData', 'AnalysisSheetReport',
    'Compilation', 'Column', 'Data', 'ExportAnalysisSheetFileStart',
    'ExportAnalysisSheetFile']


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
        'template', 'Analysis', required=True)
    comments = fields.Text('Comments')
    pending_fractions = fields.Function(fields.Integer('Pending fractions'),
        'get_pending_fractions')
    report = fields.Many2One('ir.action.report', 'Report',
        domain=[
            ('model', '=', 'lims.analysis_sheet'),
            ('report_name', 'ilike', 'lims.analysis_sheet.report%%'),
            ])

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
        required=True, select=True)
    method = fields.Many2One('lims.lab.method', 'Method')

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
        duplicated = self.search(clause)
        if duplicated:
            raise UserError(gettext(
                'lims_analysis_sheet.msg_template_analysis_unique',
                analysis=self.analysis.rec_name))


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
    urgent = fields.Function(fields.Boolean('Urgent'), 'get_urgent')
    samples_qty = fields.Function(fields.Integer('Samples Qty.'),
        'get_samples_qty')
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
        'get_incomplete_sample')
    completion_percentage = fields.Function(fields.Float('Complete',
        digits=(1, 4), domain=[
            ('completion_percentage', '>=', 0),
            ('completion_percentage', '<=', 1),
            ]),
        'get_completion_percentage')
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
            ('validated', 'done'),
            ))
        cls._buttons.update({
            'activate': {
                'invisible': Eval('state') != 'draft',
                },
            'view_data': {
                'invisible': Eval('state') == 'draft',
                },
            'export_file': {
                'invisible': Eval('state') == 'draft',
                },
            'print_report': {
                'invisible': Eval('state') == 'draft',
                },
            'validate_': {
                'invisible': Eval('state') != 'active',
                },
            'confirm': {
                'invisible': Eval('state') != 'validated',
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
    def get_urgent(cls, sheets, name):
        pool = Pool()
        Data = pool.get('lims.interface.data')
        NotebookLine = pool.get('lims.notebook.line')

        result = {}
        for s in sheets:
            result[s.id] = False
            nl_field = (s.template.interface.notebook_line_field and
                s.template.interface.notebook_line_field.alias or None)
            if not nl_field:
                continue
            with Transaction().set_context(
                    lims_interface_table=s.compilation.table.id):
                lines = Data.search([('compilation', '=', s.compilation.id)])
                for line in lines:
                    nl = getattr(line, nl_field)
                    if nl and NotebookLine(nl).service.urgent:
                        result[s.id] = True
                        break
        return result

    @classmethod
    def get_samples_qty(cls, sheets, name):
        pool = Pool()
        Data = pool.get('lims.interface.data')
        NotebookLine = pool.get('lims.notebook.line')

        result = {}
        for s in sheets:
            result[s.id] = 0
            nl_field = (s.template.interface.notebook_line_field and
                s.template.interface.notebook_line_field.alias or None)
            if not nl_field:
                continue
            with Transaction().set_context(
                    lims_interface_table=s.compilation.table.id):
                samples = []
                lines = Data.search([('compilation', '=', s.compilation.id)])
                for line in lines:
                    nl = getattr(line, nl_field)
                    if nl:
                        samples.append(NotebookLine(nl).fraction.id)
                result[s.id] = len(list(set(samples)))
        return result

    @classmethod
    def get_incomplete_sample(cls, sheets, name):
        pool = Pool()
        Data = pool.get('lims.interface.data')
        NotebookLine = pool.get('lims.notebook.line')

        result = {}
        for s in sheets:
            result[s.id] = False
            nl_field = (s.template.interface.notebook_line_field and
                s.template.interface.notebook_line_field.alias or None)
            if not nl_field:
                continue
            with Transaction().set_context(
                    lims_interface_table=s.compilation.table.id):
                samples = {}
                lines = Data.search([('compilation', '=', s.compilation.id)])
                for line in lines:
                    nl = getattr(line, nl_field)
                    if not nl:
                        continue
                    nl = NotebookLine(nl)
                    if nl.fraction.id not in samples:
                        samples[nl.fraction.id] = []
                    samples[nl.fraction.id].append(nl.analysis.id)

                template_analysis = [ta.analysis.id
                    for ta in s.template.analysis]
                result[s.id] = False
                for k, v in samples.items():
                    if not all(x in v for x in template_analysis):
                        result[s.id] = True
                        break
        return result

    @classmethod
    def get_completion_percentage(cls, sheets, name):
        pool = Pool()
        ModelField = pool.get('ir.model.field')
        Column = pool.get('lims.interface.column')
        Data = pool.get('lims.interface.data')

        nl_result_field, = ModelField.search([
            ('model.model', '=', 'lims.notebook.line'),
            ('name', '=', 'result'),
            ])

        result = {}
        for s in sheets:
            result[s.id] = 0
            result_column = Column.search([
                ('interface', '=', s.template.interface),
                ('transfer_field', '=', True),
                ('related_line_field', '=', nl_result_field)
                ])
            if not result_column:
                continue
            result_field = result_column[0].alias
            with Transaction().set_context(
                    lims_interface_table=s.compilation.table.id):
                lines = Data.search([('compilation', '=', s.compilation.id)])
                total = len(lines)
                if not total:
                    continue
                results = 0
                for line in lines:
                    if getattr(line, result_field):
                        results += 1
                result[s.id] = round(results / total, 4)
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
        Compilation = Pool().get('lims.interface.compilation')
        Compilation.activate([s.compilation for s in sheets])

    @classmethod
    @ModelView.button_action(
        'lims_analysis_sheet.wiz_analysis_sheet_open_data')
    def view_data(cls, sheets):
        pass

    @classmethod
    @ModelView.button_action(
        'lims_analysis_sheet.wiz_analysis_sheet_export_file')
    def export_file(cls, sheets):
        pass

    @classmethod
    @ModelView.button_action(
        'lims_analysis_sheet.report_analysis_sheet')
    def print_report(cls, sheets):
        pool = Pool()
        for s in sheets:
            if not s.template.report:
                raise UserError(gettext(
                    'lims_analysis_sheet.msg_template_not_report',
                    template=s.template.rec_name))
            report_name = s.template.report.report_name
            AnalysisSheetReport = pool.get(report_name, type='report')
            result = AnalysisSheetReport.execute([s.id],
                {'execute': True, 'id': s.id})
            cls.write([s], {
                'report_format': result[0],
                'report_cache': result[1],
                })

    @classmethod
    @ModelView.button
    @Workflow.transition('validated')
    def validate_(cls, sheets):
        Compilation = Pool().get('lims.interface.compilation')
        cls.check_results(sheets)
        Compilation.validate_([s.compilation for s in sheets])

    @classmethod
    @ModelView.button
    @Workflow.transition('done')
    def confirm(cls, sheets):
        Compilation = Pool().get('lims.interface.compilation')
        cls.check_results(sheets)
        Compilation.confirm([s.compilation for s in sheets])

    @classmethod
    def check_results(cls, sheets):
        pool = Pool()
        ModelField = pool.get('ir.model.field')
        Column = pool.get('lims.interface.column')
        Data = pool.get('lims.interface.data')

        nl_result_field, = ModelField.search([
            ('model.model', '=', 'lims.notebook.line'),
            ('name', '=', 'result'),
            ])

        for s in sheets:
            result_column = Column.search([
                ('interface', '=', s.template.interface),
                ('transfer_field', '=', True),
                ('related_line_field', '=', nl_result_field)
                ])
            if not result_column:
                raise UserError(gettext(
                    'lims_analysis_sheet.msg_template_not_result_field'))
            result_field = result_column[0].alias
            with Transaction().set_context(
                    lims_interface_table=s.compilation.table.id):
                lines = Data.search([('compilation', '=', s.compilation.id)])
                if not lines:
                    raise UserError(gettext(
                        'lims_analysis_sheet.msg_sheet_not_lines'))
                for line in lines:
                    if not getattr(line, result_field):
                        raise UserError(gettext(
                            'lims_analysis_sheet.msg_sheet_not_results'))

    def get_new_compilation(self):
        Compilation = Pool().get('lims.interface.compilation')
        compilation = Compilation(
            table=self.template.interface.table.id,
            interface=self.template.interface.id,
            revision=self.template.interface.revision,
            )
        return compilation

    def create_lines(self, lines):
        Data = Pool().get('lims.interface.data')

        interface = self.template.interface
        if not interface.notebook_line_field:
            return

        with Transaction().set_context(
                lims_interface_table=self.compilation.table.id):
            data = []
            for nl in lines:
                line = {'compilation': self.compilation.id}
                line[interface.notebook_line_field.alias] = nl.id
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
                            nl.fraction.rec_name)
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
            'lims_interface_compilation': None,
            'lims_interface_table': None,
            }
        domain = [('compilation', '=', None)]
        name = ''

        sheet_id = Transaction().context.get('active_id', None)
        if sheet_id:
            sheet = AnalysisSheet(sheet_id)
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

    start = StateView('lims.analysis_sheet.export_file.start',
        'lims_analysis_sheet.analysis_sheet_export_start_view_form', [
            Button('Close', 'end', 'tryton-close'),
            ])

    def default_start(self, fields):
        file_ = self.get_file(Transaction().context.get('active_id', None))
        cast = self.start.__class__.file.cast
        return {
            'file': cast(file_) if file_ else None,
            }

    def get_file(self, sheet_id, sep=';', newline='\n'):
        pool = Pool()
        Column = pool.get('lims.interface.column')
        AnalysisSheet = pool.get('lims.analysis_sheet')
        Data = pool.get('lims.interface.data')

        if not sheet_id:
            return
        sheet = AnalysisSheet(sheet_id)

        columns = Column.search([
            ('interface', '=', sheet.template.interface),
            ('destination_column', '!=', None),
            ], order=[('destination_column', 'ASC')])
        if not columns:
            return
        cols = [c.alias for c in columns]

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
                        entry += sep
                    entry += str(getattr(line, field))
                entry += newline
                file_.write(entry)

        if file_:
            return str(file_.getvalue()).encode('utf-8')
        return


class AnalysisSheetReport(Report):
    'Analysis Sheet Report'
    __name__ = 'lims.analysis_sheet.report'

    @classmethod
    def execute(cls, ids, data):
        AnalysisSheet = Pool().get('lims.analysis_sheet')

        sheet = AnalysisSheet(ids[0])
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
        report_context['sheet'] = sheet

        limit = 20
        alias = []

        # Columns
        columns = {}
        i = 0
        fields = Field.search([('table', '=', sheet.compilation.table.id)])
        for field in fields:
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


class Compilation(metaclass=PoolMeta):
    __name__ = 'lims.interface.compilation'

    analysis_sheet = fields.Many2One('lims.analysis_sheet', 'Analysis Sheet')

    @classmethod
    def __setup__(cls):
        super(Compilation, cls).__setup__()
        cls.date_time.states['readonly'] = Bool(Eval('analysis_sheet'))
        if 'analysis_sheet' not in cls.date_time.depends:
            cls.date_time.depends.append('analysis_sheet')
        cls.interface.states['readonly'] = Bool(Eval('analysis_sheet'))
        if 'analysis_sheet' not in cls.interface.depends:
            cls.interface.depends.append('analysis_sheet')
        cls.revision.states['readonly'] = Or(Bool(Eval('analysis_sheet')),
            Eval('state') != 'draft')
        if 'analysis_sheet' not in cls.revision.depends:
            cls.revision.depends.append('analysis_sheet')

        cls._buttons['draft']['invisible'] = Or(Eval('state') != 'active',
            Bool(Eval('analysis_sheet')))
        cls._buttons['activate']['invisible'] = Or(Eval('state') != 'draft',
            Bool(Eval('analysis_sheet')))
        cls._buttons['validate_']['invisible'] = Or(Eval('state') != 'active',
            Bool(Eval('analysis_sheet')))
        cls._buttons['confirm']['invisible'] = Or(Eval('state') != 'validated',
            Bool(Eval('analysis_sheet')))
        #cls._buttons['view_data']['invisible'] = Or(Eval('state') == 'draft',
            #Bool(Eval('analysis_sheet')))
        #cls._buttons['collect']['invisible'] = Or(Eval('state') != 'active',
            #Bool(Eval('analysis_sheet')))


class Column(metaclass=PoolMeta):
    __name__ = 'lims.interface.column'

    destination_column = fields.Integer('Destination Column',
        help='Mapped column in batch file')


class Data(metaclass=PoolMeta):
    __name__ = 'lims.interface.data'

    def set_result(self, result, result_field=None):
        pool = Pool()
        cursor = Transaction().connection.cursor()
        ModelField = pool.get('ir.model.field')
        Column = pool.get('lims.interface.column')

        if not result_field:
            nl_result_field, = ModelField.search([
                ('model.model', '=', 'lims.notebook.line'),
                ('name', '=', 'result'),
                ])
            result_column = Column.search([
                ('interface', '=', self.compilation.interface),
                ('transfer_field', '=', True),
                ('related_line_field', '=', nl_result_field)
                ])
            if not result_column:
                return
            result_field = result_column[0].alias

        table = self.get_sql_table()
        query = table.update([sql.Column(table, result_field)], [result],
            where=(table.id == self.id))
        cursor.execute(*query)
