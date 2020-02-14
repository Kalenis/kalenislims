# This file is part of lims_analysis_sheet module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import Workflow, ModelView, ModelSQL, fields, Unique
from trytond.wizard import Wizard, StateAction
from trytond.pool import Pool
from trytond.pyson import PYSONEncoder, Eval, Bool
from trytond.transaction import Transaction

__all__ = ['TemplateAnalysisSheet', 'TemplateAnalysisSheetAnalysis',
    'AnalysisSheet', 'OpenAnalysisSheetData']


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
    max_qty_samples = fields.Integer('Maximum quantity of samples',
        help='For generation from racks')
    comments = fields.Text('Comments')

    @fields.depends('interface')
    def on_change_with_name(self, name=None):
        if self.interface:
            return self.interface.name


class TemplateAnalysisSheetAnalysis(ModelSQL, ModelView):
    'Template Analysis'
    __name__ = 'lims.template.analysis_sheet.analysis'

    template = fields.Many2One('lims.template.analysis_sheet', 'Template',
        required=True, ondelete='CASCADE', select=True)
    analysis = fields.Many2One('lims.analysis', 'Analysis',
        required=True, select=True)
    method = fields.Many2One('lims.lab.method', 'Method')


class AnalysisSheet(Workflow, ModelSQL, ModelView):
    'Analysis Sheet'
    __name__ = 'lims.analysis_sheet'

    template = fields.Many2One('lims.template.analysis_sheet', 'Template',
        required=True, readonly=True)
    compilation = fields.Many2One('lims.interface.compilation', 'Compilation',
        required=True, readonly=True)
    laboratory = fields.Many2One('lims.laboratory', 'Laboratory')
    professional = fields.Many2One('lims.laboratory.professional',
        'Professional', required=True)
    samples_qty = fields.Function(fields.Integer('Samples Qty.'),
        'get_samples_qty')
    number = fields.Char('Number', readonly=True)
    date = fields.Function(fields.DateTime('Date'), 'get_date')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ], 'State', required=True, readonly=True)
    planification = fields.Many2One('lims.planification', 'Planification',
        readonly=True)

    @classmethod
    def __setup__(cls):
        super(AnalysisSheet, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('compilation_uniq', Unique(t, t.compilation),
                'lims_analysis_sheet.msg_sheet_compilation_unique'),
            ]
        cls._transitions |= set((
            ('draft', 'active'),
            ))
        cls._buttons.update({
            'view_data': {
                'invisible': Eval('state') == 'draft',
                },
            'activate': {
                'invisible': Eval('state') != 'draft',
                },
            })

    @staticmethod
    def default_state():
        return 'draft'

    def get_date(self, name):
        return self.compilation.date_time

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
    def create(cls, vlist):
        vlist = cls.set_number(vlist)
        return super(AnalysisSheet, cls).create(vlist)

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
        'lims_analysis_sheet.wiz_open_analysis_sheet_data')
    def view_data(cls, sheets):
        pass


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
            name = ' (%s)' % sheet.number
        action['pyson_context'] = PYSONEncoder().encode(context)
        action['pyson_domain'] = PYSONEncoder().encode(domain)
        action['name'] += name
        return action, {}
