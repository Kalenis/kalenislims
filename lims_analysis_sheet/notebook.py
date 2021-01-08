# This file is part of lims_analysis_sheet module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import formulas
import schedula
from decimal import Decimal
from datetime import datetime
from itertools import chain
from collections import defaultdict
#from dateutil.relativedelta import relativedelta

from trytond.model import ModelSQL, ModelView, fields
from trytond.wizard import Wizard, StateTransition, StateView, Button
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, Bool, Or, And
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.i18n import gettext
from trytond.modules.lims.formula_parser import FormulaParser


class NotebookLine(metaclass=PoolMeta):
    __name__ = 'lims.notebook.line'

    analysis_sheet = fields.Many2One('lims.analysis_sheet', 'Analysis Sheet',
        readonly=True)

    def get_analysis_sheet_template(self):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        TemplateAnalysis = pool.get('lims.template.analysis_sheet.analysis')

        cursor.execute('SELECT template '
            'FROM "' + TemplateAnalysis._table + '" '
            'WHERE analysis = %s '
            'AND method = %s',
            (self.analysis.id, self.method.id))
        template = cursor.fetchone()

        if not template:
            cursor.execute('SELECT template '
                'FROM "' + TemplateAnalysis._table + '" '
                'WHERE analysis = %s '
                'AND method IS NULL',
                (self.analysis.id, ))
            template = cursor.fetchone()

        return template and template[0] or None


class AddControlStart(ModelView):
    'Add Controls'
    __name__ = 'lims.analysis_sheet.add_control.start'

    analysis_sheet = fields.Many2One('lims.analysis_sheet', 'Analysis Sheet')
    type = fields.Selection([
        ('con', 'CON'),
        ('rm', 'RM'),
        ('bmz', 'BMZ'),
        ], 'Control type', sort=False, required=True)
    con_type = fields.Selection([
        ('exist', 'Existing'),
        ('coi', 'COI'),
        ('mrc', 'MRC'),
        ('sla', 'SLA'),
        ('itc', 'ITC'),
        ('itl', 'ITL'),
        ], 'Type', sort=False,
        depends=['type'], states={
            'required': Eval('type') == 'con',
            'invisible': Eval('type') != 'con',
            })
    rm_bmz_type = fields.Selection([
        ('exist', 'Existing'),
        ('sla', 'SLA'),
        ], 'Type', sort=False,
        depends=['type'], states={
            'required': Eval('type').in_(['rm', 'bmz']),
            'invisible': ~Eval('type').in_(['rm', 'bmz']),
            })
    original_fraction = fields.Many2One('lims.fraction',
        'Original/Reference Fraction',
        required=True, domain=[('id', 'in', Eval('fraction_domain'))],
        depends=['fraction_domain'])
    fraction_domain = fields.Function(fields.One2Many('lims.fraction',
        None, 'Fraction domain'), 'on_change_with_fraction_domain')
    label = fields.Char('Label', depends=['type', 'con_type', 'rm_bmz_type'],
        states={'readonly': Or(
            And(Eval('type') == 'con',
                Eval('con_type') == 'exist'),
            And(Eval('type').in_(['rm', 'bmz']),
                Eval('rm_bmz_type') == 'exist')),
            })
    concentration_level = fields.Many2One('lims.concentration.level',
        'Concentration level',
        states={'invisible': Bool(Eval('concentration_level_invisible'))},
        depends=['concentration_level_invisible'])
    concentration_level_invisible = fields.Boolean(
        'Concentration level invisible')
    quantity = fields.Integer('Quantity', required=True,
        depends=['type', 'con_type', 'rm_bmz_type'],
        states={'readonly': Or(
            And(Eval('type') == 'con',
                Eval('con_type') == 'exist'),
            And(Eval('type').in_(['rm', 'bmz']),
                Eval('rm_bmz_type') == 'exist')),
            })

    @fields.depends('type')
    def on_change_with_concentration_level_invisible(self, name=None):
        Config = Pool().get('lims.configuration')
        config = Config(1)
        if self.type == 'con':
            if (config.con_fraction_type and
                    config.con_fraction_type.control_charts):
                return False
        elif self.type == 'rm':
            if (config.rm_fraction_type and
                    config.rm_fraction_type.control_charts):
                return False
        elif self.type == 'bmz':
            if (config.bmz_fraction_type and
                    config.bmz_fraction_type.control_charts):
                return False
        return True

    @fields.depends('type', 'con_type', 'rm_bmz_type', 'analysis_sheet',
        '_parent_analysis_sheet.template')
    def on_change_with_fraction_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Fraction = pool.get('lims.fraction')
        NotebookLine = pool.get('lims.notebook.line')
        Notebook = pool.get('lims.notebook')

        if not self.type:
            return []

        special_type = ''
        existing = False
        if self.type == 'con':
            if not self.con_type:
                return []
            special_type = 'con' if self.con_type == 'exist' else self.con_type
            existing = (self.con_type == 'exist')

        elif self.type == 'rm':
            if not self.rm_bmz_type or self.rm_bmz_type == 'noref':
                return []
            special_type = 'sla' if self.rm_bmz_type == 'sla' else self.type
            existing = (self.rm_bmz_type == 'exist')

        elif self.type == 'bmz':
            if not self.rm_bmz_type or self.rm_bmz_type == 'noref':
                return []
            special_type = 'sla' if self.rm_bmz_type == 'sla' else self.type
            existing = (self.rm_bmz_type == 'exist')

        controls_allowed = (self.analysis_sheet.template.controls_allowed or
            ['0'])
        if special_type not in controls_allowed:
            return []

        t_analysis_ids = [ta.analysis.id
            for ta in self.analysis_sheet.template.analysis]

        stored_fractions_ids = Fraction.get_stored_fractions()

        clause = [
            ('notebook.fraction.special_type', '=', special_type),
            ('notebook.fraction.id', 'in', stored_fractions_ids),
            ('analysis', 'in', t_analysis_ids),
            ]
        if existing:
            #deadline = datetime.now() - relativedelta(days=5)
            clause.extend([
                ('result', 'in', (None, '')),
                ('end_date', '=', None),
                ('annulment_date', '=', None),
                #('notebook.fraction.sample.date2', '>=', deadline),
                ])
        notebook_lines = NotebookLine.search(clause)
        if not notebook_lines:
            return []

        notebook_lines_ids = ', '.join(str(nl.id) for nl in notebook_lines)
        cursor.execute('SELECT DISTINCT(n.fraction) '
            'FROM "' + Notebook._table + '" n '
                'INNER JOIN "' + NotebookLine._table + '" nl '
                'ON nl.notebook = n.id '
            'WHERE nl.id IN (' + notebook_lines_ids + ')')
        return [x[0] for x in cursor.fetchall()]

    @fields.depends('type', 'con_type', 'rm_bmz_type', 'original_fraction',
        'concentration_level', '_parent_original_fraction.label',
        '_parent_concentration_level.description')
    def on_change_with_label(self, name=None):
        Date = Pool().get('ir.date')

        if self.type == 'con':
            if self.con_type == 'exist':
                return ''
            label = ''
            if self.original_fraction:
                label += '%s' % self.original_fraction.label
            if self.concentration_level:
                label += ' (%s)' % self.concentration_level.description

        elif self.type == 'rm':
            if self.rm_bmz_type == 'exist':
                return ''
            label = 'RM'
            if self.concentration_level:
                label += ' (%s)' % self.concentration_level.description
            if self.rm_bmz_type == 'sla':
                if self.original_fraction:
                    label += ' %s' % self.original_fraction.label

        elif self.type == 'bmz':
            if self.rm_bmz_type == 'exist':
                return ''
            label = 'BMZ'
            if self.rm_bmz_type == 'sla':
                if self.original_fraction:
                    label += ' %s' % self.original_fraction.label

        else:
            return ''

        label += ' %s' % str(Date.today())
        return label

    @fields.depends('type', 'con_type', 'rm_bmz_type', 'quantity')
    def on_change_with_quantity(self, name=None):
        if ((self.type == 'con' and self.con_type == 'exist') or
                (self.type in ('rm', 'bmz') and self.rm_bmz_type == 'exist')):
            return 1
        return self.quantity


class AddControl(Wizard):
    'Add Controls'
    __name__ = 'lims.analysis_sheet.add_control'

    start_state = 'check'
    check = StateTransition()
    start = StateView('lims.analysis_sheet.add_control.start',
        'lims_analysis_sheet.analysis_sheet_add_control_start_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Add', 'add', 'tryton-ok', default=True),
            ])
    add = StateTransition()

    def _get_analysis_sheet_id(self):
        return Transaction().context.get('lims_analysis_sheet', None)

    def transition_check(self):
        AnalysisSheet = Pool().get('lims.analysis_sheet')

        sheet_id = self._get_analysis_sheet_id()
        if sheet_id:
            sheet = AnalysisSheet(sheet_id)
            if sheet.state in ('active', 'validated'):
                return 'start'

        return 'end'

    def default_start(self, fields):
        defaults = {
            'analysis_sheet': self._get_analysis_sheet_id(),
            'concentration_level_invisible': True,
            'quantity': 1,
            }
        return defaults

    def transition_add(self):
        fractions = [self.start.original_fraction]
        if ((self.start.type == 'con' and
                self.start.con_type != 'exist') or
                (self.start.type in ('rm', 'bmz') and
                self.start.rm_bmz_type != 'exist')):
            fractions = self.create_control()
        self.add_to_analysis_sheet(fractions)
        return 'end'

    def create_control(self):
        pool = Pool()
        Config = pool.get('lims.configuration')
        LabWorkYear = pool.get('lims.lab.workyear')
        Entry = pool.get('lims.entry')
        Sample = pool.get('lims.sample')
        Fraction = pool.get('lims.fraction')
        Service = pool.get('lims.service')
        Analysis = pool.get('lims.analysis')
        NotebookLine = pool.get('lims.notebook.line')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        config = Config(1)
        if self.start.type == 'con':
            if not config.con_fraction_type:
                raise UserError(gettext('lims.msg_no_con_fraction_type'))
            fraction_type = config.con_fraction_type
        elif self.start.type == 'rm':
            if not config.rm_fraction_type:
                raise UserError(gettext('lims.msg_no_rm_fraction_type'))
            fraction_type = config.rm_fraction_type
        elif self.start.type == 'bmz':
            if not config.bmz_fraction_type:
                raise UserError(gettext('lims.msg_no_bmz_fraction_type'))
            fraction_type = config.bmz_fraction_type

        if (fraction_type.control_charts and not
                self.start.concentration_level):
            raise UserError(gettext('lims.msg_no_concentration_level'))

        workyear_id = LabWorkYear.find()
        workyear = LabWorkYear(workyear_id)
        if not workyear.default_entry_control:
            raise UserError(gettext('lims.msg_no_entry_control'))

        entry = Entry(workyear.default_entry_control.id)
        original_fraction = self.start.original_fraction
        original_sample = Sample(original_fraction.sample.id)
        obj_description = self._get_obj_description(original_sample)

        sample_default = {
            'entry': entry.id,
            'date': datetime.now(),
            'label': self.start.label,
            'obj_description': obj_description,
            'fractions': [],
            }

        fraction_default = {
            'type': fraction_type.id,
            'services': [],
            }
        if self.start.type == 'con':
            fraction_default['con_type'] = self.start.con_type
            fraction_default['con_original_fraction'] = original_fraction.id
        elif self.start.type == 'rm':
            fraction_default['rm_type'] = 'sla'
            fraction_default['rm_product_type'] = (
                original_sample.product_type.id)
            fraction_default['rm_matrix'] = original_sample.matrix.id
            fraction_default['rm_original_fraction'] = original_fraction.id
        elif self.start.type == 'bmz':
            fraction_default['bmz_type'] = 'sla'
            fraction_default['bmz_product_type'] = (
                original_sample.product_type.id)
            fraction_default['bmz_matrix'] = original_sample.matrix.id
            fraction_default['bmz_original_fraction'] = original_fraction.id

        t_analysis_ids = [ta.analysis.id
            for ta in self.start.analysis_sheet.template.analysis]

        original_services = []
        services = Service.search([
            ('fraction', '=', original_fraction),
            ('annulled', '=', False),
            ])
        for service in services:
            if Analysis.is_typified(service.analysis,
                    original_sample.product_type, original_sample.matrix):
                original_services.append(service)

        res = []
        for i in range(0, self.start.quantity):

            # new sample
            new_sample, = Sample.copy([original_sample],
                default=sample_default)

            # new fraction
            new_fraction, = Fraction.copy([original_fraction],
                default={**fraction_default, 'sample': new_sample.id})

            # new services
            for service in original_services:
                method_id = service.method and service.method.id or None
                device_id = service.device and service.device.id or None
                if service.analysis.type == 'analysis':
                    original_lines = NotebookLine.search([
                        ('notebook.fraction', '=', original_fraction.id),
                        ('analysis', '=', service.analysis.id),
                        ('repetition', '=', 0),
                        ], limit=1)
                    original_line = (original_lines and
                        original_lines[0] or None)
                    if original_line:
                        method_id = original_line.method.id
                        if original_line.device:
                            device_id = original_line.device.id
                service_default = {
                    'fraction': new_fraction.id,
                    'method': method_id,
                    'device': device_id,
                    }
                new_service, = Service.copy([service], default=service_default)

                # delete services/details not related to template
                to_delete = EntryDetailAnalysis.search([
                    ('service', '=', new_service.id),
                    ('analysis', 'not in', t_analysis_ids),
                    ])
                if to_delete:
                    with Transaction().set_user(0, set_context=True):
                        EntryDetailAnalysis.delete(to_delete)
                if EntryDetailAnalysis.search_count([
                        ('service', '=', new_service.id),
                        ]) == 0:
                    with Transaction().set_user(0, set_context=True):
                        Service.delete([new_service])

            # confirm fraction: new notebook and stock move
            Fraction.confirm([new_fraction])

            # Edit notebook lines
            if fraction_type.control_charts:
                notebook_lines = NotebookLine.search([
                    ('notebook.fraction', '=', new_fraction.id),
                    ])
                if notebook_lines:
                    NotebookLine.write(notebook_lines, {
                        'concentration_level': (
                            self.start.concentration_level.id),
                        })

            if self.start.type == 'rm':
                notebook_lines = NotebookLine.search([
                    ('notebook.fraction', '=', new_fraction.id),
                    ])
                if notebook_lines:
                    defaults = {
                        'final_concentration': None,
                        'final_unit': None,
                        'detection_limit': None,
                        'quantification_limit': None,
                        'lower_limit': None,
                        'upper_limit': None,
                        }
                    if config.rm_start_uom:
                        defaults['initial_unit'] = config.rm_start_uom.id
                    NotebookLine.write(notebook_lines, defaults)
            res.append(new_fraction)

        return res

    def _get_obj_description(self, sample):
        cursor = Transaction().connection.cursor()
        ObjectiveDescription = Pool().get('lims.objective_description')

        if not sample.product_type or not sample.matrix:
            return None

        cursor.execute('SELECT id '
            'FROM "' + ObjectiveDescription._table + '" '
            'WHERE product_type = %s '
                'AND matrix = %s',
            (sample.product_type.id, sample.matrix.id))
        res = cursor.fetchone()
        return res and res[0] or None

    def add_to_analysis_sheet(self, fractions):
        NotebookLine = Pool().get('lims.notebook.line')

        sheet = self.start.analysis_sheet
        t_analysis_ids = [ta.analysis.id for ta in sheet.template.analysis]

        clause = [
            ('notebook.fraction', 'in', [f.id for f in fractions]),
            ('analysis', 'in', t_analysis_ids),
            ]
        if ((self.start.type == 'con' and
                self.start.con_type == 'exist') or
                (self.start.type in ('rm', 'bmz') and
                self.start.rm_bmz_type == 'exist')):
            clause.extend([
                ('result', 'in', (None, '')),
                ('end_date', '=', None),
                ('annulment_date', '=', None),
                ])
        notebook_lines = NotebookLine.search(clause)
        if notebook_lines:
            sheet.create_lines(notebook_lines)
        return 'end'

    def end(self):
        return 'reload'


class RepeatAnalysisStart(ModelView):
    'Repeat Analysis'
    __name__ = 'lims.analysis_sheet.repeat_analysis.start'

    lines = fields.Many2Many(
        'lims.analysis_sheet.repeat_analysis.start.line', None, None,
        'Lines', required=True, domain=[('id', 'in', Eval('lines_domain'))],
        depends=['lines_domain'])
    lines_domain = fields.One2Many(
        'lims.analysis_sheet.repeat_analysis.start.line', None,
        'Lines domain')
    annul = fields.Boolean('Annul current lines')
    urgent = fields.Boolean('Urgent repetition')


class RepeatAnalysisStartLine(ModelSQL, ModelView):
    'Analysis Sheet Line'
    __name__ = 'lims.analysis_sheet.repeat_analysis.start.line'

    line = fields.Many2One('lims.notebook.line', 'Line')
    fraction = fields.Function(fields.Many2One('lims.fraction', 'Fraction'),
        'get_line_field', searcher='search_line_field')
    analysis = fields.Function(fields.Many2One('lims.analysis', 'Analysis'),
        'get_line_field', searcher='search_line_field')
    repetition = fields.Function(fields.Integer('Repetition'),
        'get_line_field', searcher='search_line_field')
    session_id = fields.Integer('Session ID')

    @classmethod
    def __register__(cls, module_name):
        super().__register__(module_name)
        cursor = Transaction().connection.cursor()
        cursor.execute('DELETE FROM "' + cls._table + '"')

    @classmethod
    def __setup__(cls):
        super().__setup__()

    @classmethod
    def get_line_field(cls, lines, names):
        result = {}
        for name in names:
            result[name] = {}
            if name in ('fraction', 'analysis'):
                for l in lines:
                    field = getattr(l.line, name, None)
                    result[name][l.id] = field.id if field else None
            else:
                for l in lines:
                    result[name][l.id] = getattr(l.line, name, None)
        return result

    @classmethod
    def search_line_field(cls, name, clause):
        return [('line.' + name,) + tuple(clause[1:])]


class RepeatAnalysis(Wizard):
    'Repeat Analysis'
    __name__ = 'lims.analysis_sheet.repeat_analysis'

    start_state = 'check'
    check = StateTransition()
    start = StateView('lims.analysis_sheet.repeat_analysis.start',
        'lims_analysis_sheet.analysis_sheet_repeat_analysis_start_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Repeat', 'repeat', 'tryton-ok', default=True),
            ])
    repeat = StateTransition()

    def _get_analysis_sheet_id(self):
        return Transaction().context.get('lims_analysis_sheet', None)

    def transition_check(self):
        AnalysisSheet = Pool().get('lims.analysis_sheet')

        sheet_id = self._get_analysis_sheet_id()
        if sheet_id:
            sheet = AnalysisSheet(sheet_id)
            if sheet.state in ('active', 'validated'):
                return 'start'

        return 'end'

    def default_start(self, fields):
        pool = Pool()
        AnalysisSheet = pool.get('lims.analysis_sheet')
        Data = pool.get('lims.interface.data')
        RepeatAnalysisStartLine = pool.get(
            'lims.analysis_sheet.repeat_analysis.start.line')

        defaults = {
            'annul': False,
            'urgent': False,
            }

        sheet_id = self._get_analysis_sheet_id()
        sheet = AnalysisSheet(sheet_id)

        to_create = []
        selected_lines = []
        with Transaction().set_context(
                lims_interface_table=sheet.compilation.table.id):
            lines = Data.search([('compilation', '=', sheet.compilation.id)])
            for line in lines:
                nl = line.notebook_line
                if not nl:
                    continue
                to_create.append({
                    'session_id': self._session_id,
                    'line': nl,
                    })
                if line.id in Transaction().context['active_ids']:
                    selected_lines.append(line.notebook_line)

        lines = RepeatAnalysisStartLine.create(to_create)
        defaults['lines_domain'] = [l.id for l in lines]
        defaults['lines'] = [l.id for l in lines if l.line in selected_lines]
        return defaults

    def transition_repeat(self):
        pool = Pool()
        AnalysisSheet = pool.get('lims.analysis_sheet')
        Date = pool.get('ir.date')
        NotebookLine = pool.get('lims.notebook.line')
        Data = pool.get('lims.interface.data')

        sheet_id = self._get_analysis_sheet_id()
        sheet = AnalysisSheet(sheet_id)

        to_create = []
        to_update = []
        to_annul = []

        date = Date.today()
        for sheet_line in self.start.lines:
            nline_to_repeat = sheet_line.line
            detail_id = nline_to_repeat.analysis_detail.id
            defaults = {
                'notebook': nline_to_repeat.notebook.id,
                'analysis_detail': detail_id,
                'service': nline_to_repeat.service.id,
                'analysis': nline_to_repeat.analysis.id,
                'analysis_origin': nline_to_repeat.analysis_origin,
                'urgent': self.start.urgent,
                'repetition': nline_to_repeat.repetition + 1,
                'laboratory': nline_to_repeat.laboratory.id,
                'method': nline_to_repeat.method.id,
                'device': (nline_to_repeat.device.id if nline_to_repeat.device
                    else None),
                'initial_concentration': nline_to_repeat.initial_concentration,
                'decimals': nline_to_repeat.decimals,
                'significant_digits': nline_to_repeat.significant_digits,
                'report': nline_to_repeat.report,
                'concentration_level': (nline_to_repeat.concentration_level.id
                    if nline_to_repeat.concentration_level else None),
                'results_estimated_waiting': (
                    nline_to_repeat.results_estimated_waiting),
                'department': nline_to_repeat.department,
                'final_concentration': nline_to_repeat.final_concentration,
                'initial_unit': (nline_to_repeat.initial_unit.id if
                    nline_to_repeat.initial_unit else None),
                'final_unit': (nline_to_repeat.final_unit.id if
                    nline_to_repeat.final_unit else None),
                'detection_limit': nline_to_repeat.detection_limit,
                'quantification_limit': nline_to_repeat.quantification_limit,
                'lower_limit': nline_to_repeat.lower_limit,
                'upper_limit': nline_to_repeat.upper_limit,
                'start_date': date,
                }
            to_create.append(defaults)
            to_update.append(nline_to_repeat)
            if self.start.annul:
                to_annul.append(nline_to_repeat.id)

        notebook_lines = NotebookLine.create(to_create)
        if notebook_lines:
            sheet.create_lines(notebook_lines)
        NotebookLine.write(to_update, {
            'report': False,
            })

        if to_annul:
            with Transaction().set_context(
                    lims_interface_table=sheet.compilation.table.id):
                lines = Data.search([
                    ('compilation', '=', sheet.compilation.id),
                    ('notebook_line', 'in', to_annul),
                    ])
                Data.write(lines, {'annulled': True})

        return 'end'

    def end(self):
        return 'reload'


class CalculateExpressions(Wizard):
    'Calculate Expressions'
    __name__ = 'lims.analysis_sheet.calculate_expressions'

    start_state = 'check'
    check = StateTransition()
    calcuate = StateTransition()

    def _get_analysis_sheet_id(self):
        return Transaction().context.get('lims_analysis_sheet', None)

    def transition_check(self):
        AnalysisSheet = Pool().get('lims.analysis_sheet')

        sheet_id = self._get_analysis_sheet_id()
        if sheet_id:
            sheet = AnalysisSheet(sheet_id)
            if sheet.state in ('active', 'validated'):
                return 'calcuate'

        return 'end'

    def transition_calcuate(self):
        pool = Pool()
        AnalysisSheet = pool.get('lims.analysis_sheet')
        Data = pool.get('lims.interface.data')

        sheet_id = self._get_analysis_sheet_id()
        sheet = AnalysisSheet(sheet_id)

        expressions = {}
        for t_analysis in sheet.template.analysis:
            if not t_analysis.expressions:
                continue
            if t_analysis.analysis.id not in expressions:
                expressions[t_analysis.analysis.id] = {}
            for expression in t_analysis.expressions:
                expressions[t_analysis.analysis.id][
                    expression.column.alias] = expression.expression
        if not expressions:
            return 'end'

        parser = formulas.Parser()

        with Transaction().set_context(
                lims_interface_table=sheet.compilation.table.id):
            lines = Data.search([('compilation', '=', sheet.compilation.id)])
            for line in lines:
                nl = line.notebook_line
                if not nl:
                    continue
                if nl.analysis.id not in expressions:
                    continue

                with Transaction().set_context(
                        lims_analysis_notebook=nl.notebook.id):
                    for alias, formula in expressions[nl.analysis.id].items():
                        if not formula:
                            continue
                        ast = parser.ast(formula)[1].compile()
                        inputs = (' '.join([x for x in ast.inputs])).lower()
                        inputs = [getattr(line, x) for x in inputs.split()]
                        try:
                            value = ast(*inputs)
                        except schedula.utils.exc.DispatcherError as e:
                            raise UserError(e.args[0] % e.args[1:])

                        if isinstance(value, list):
                            value = str(value)
                        elif not isinstance(value,
                                (str, int, float, Decimal, type(None))):
                            value = value.tolist()
                        if isinstance(value, formulas.tokens.operand.XlError):
                            value = None
                        elif isinstance(value, list):
                            for x in chain(*value):
                                if isinstance(x,
                                        formulas.tokens.operand.XlError):
                                    value = None
                        Data.write([line], {alias: value or None})

        return 'end'

    def end(self):
        return 'reload'


class ResultsVerificationStart(ModelView):
    'Results Verification'
    __name__ = 'lims.analysis_sheet.results_verification.start'

    range_type = fields.Many2One('lims.range.type', 'Origin', required=True,
        domain=[('use', '=', 'results_verification')])


class ResultsVerification(Wizard):
    'Results Verification'
    __name__ = 'lims.analysis_sheet.results_verification'

    start_state = 'check'
    check = StateTransition()
    start = StateView('lims.analysis_sheet.results_verification.start',
        'lims_analysis_sheet.analysis_sheet_results_verification_start_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Ok', 'verify', 'tryton-ok', default=True),
            ])
    verify = StateTransition()

    def _get_analysis_sheet_id(self):
        return Transaction().context.get('lims_analysis_sheet', None)

    def transition_check(self):
        AnalysisSheet = Pool().get('lims.analysis_sheet')

        sheet_id = self._get_analysis_sheet_id()
        if sheet_id:
            sheet = AnalysisSheet(sheet_id)
            if sheet.state in ('active', 'validated'):
                return 'start'

        return 'end'

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

    def transition_verify(self):
        pool = Pool()
        AnalysisSheet = pool.get('lims.analysis_sheet')
        Data = pool.get('lims.interface.data')

        sheet_id = self._get_analysis_sheet_id()
        sheet = AnalysisSheet(sheet_id)
        table_id = sheet.compilation.table.id

        result_column = self._get_template_column(
            'result', table_id)
        if not result_column:
            raise UserError(gettext('lims_analysis_sheet.'
                'msg_template_not_result_field'))
        result_field = result_column.name

        verification_column = self._get_template_column(
            'verification', table_id)
        if not verification_column:
            raise UserError(gettext('lims_analysis_sheet.'
                'msg_template_not_verification_field'))
        verification_field = verification_column.name

        notebook_lines = {}
        with Transaction().set_context(lims_interface_table=table_id):
            lines = Data.search([('compilation', '=', sheet.compilation.id)])
            for line in lines:
                nl = line.notebook_line
                if not nl:
                    continue
                notebook_lines[line] = nl
            if not notebook_lines:
                return 'end'

            for s_line, n_line in notebook_lines.items():
                verification = self._get_result_verification(
                    getattr(s_line, result_field), n_line)
                if verification is not None:
                    Data.write([s_line],
                        {verification_field: str(verification)})

        return 'end'

    def _get_template_column(self, field_name, table_id):
        pool = Pool()
        Field = pool.get('lims.interface.table.field')

        table_column = Field.search([
            ('table', '=', table_id),
            ('transfer_field', '=', True),
            ('related_line_field.name', '=', field_name),
            ])
        return table_column and table_column[0] or None

    def _get_result_verification(self, result, notebook_line):
        pool = Pool()
        Range = pool.get('lims.range')
        UomConversion = pool.get('lims.uom.conversion')
        VolumeConversion = pool.get('lims.volume.conversion')

        try:
            result = float(result)
        except (TypeError, ValueError):
            return None

        iu = notebook_line.initial_unit
        if not iu:
            return None
        try:
            ic = float(notebook_line.initial_concentration)
        except (TypeError, ValueError):
            return None

        ranges = Range.search([
            ('range_type', '=', self.start.range_type),
            ('analysis', '=', notebook_line.analysis.id),
            ('product_type', '=', notebook_line.product_type.id),
            ('matrix', '=', notebook_line.matrix.id),
            ])
        if not ranges:
            return None
        fu = ranges[0].uom
        try:
            fc = float(ranges[0].concentration)
        except (TypeError, ValueError):
            return None

        if fu and fu.rec_name != '-':
            converted_result = None
            if (iu == fu and ic == fc):
                converted_result = result
            elif (iu != fu and ic == fc):
                formula = UomConversion.get_conversion_formula(iu,
                    fu)
                if not formula:
                    return None
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
                    return None
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

        return self._verificate_result(result, ranges[0])

    def _get_variables(self, formula, notebook_line):
        pool = Pool()
        VolumeConversion = pool.get('lims.volume.conversion')

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
                return gettext('lims.msg_out')
            elif result < range_.min95:
                return gettext('lims.msg_ok*')
            elif result <= range_.max95:
                return gettext('lims.msg_ok')
            elif result <= range_.max:
                return gettext('lims.msg_ok*')
            else:
                return gettext('lims.msg_out')
        else:
            if (range_.min and result < range_.min):
                return gettext('lims.msg_out')
            elif (range_.max and result <= range_.max):
                return gettext('lims.msg_ok')
            else:
                return gettext('lims.msg_out')

    def end(self):
        return 'reload'


class LimitsValidation(Wizard):
    'Limits Validation'
    __name__ = 'lims.analysis_sheet.limits_validation'

    start_state = 'check'
    check = StateTransition()
    validate_limits = StateTransition()

    def _get_analysis_sheet_id(self):
        return Transaction().context.get('lims_analysis_sheet', None)

    def transition_check(self):
        AnalysisSheet = Pool().get('lims.analysis_sheet')

        sheet_id = self._get_analysis_sheet_id()
        if sheet_id:
            sheet = AnalysisSheet(sheet_id)
            if sheet.state in ('active', 'validated'):
                return 'validate_limits'

        return 'end'

    def transition_validate_limits(self):
        pool = Pool()
        AnalysisSheet = pool.get('lims.analysis_sheet')
        Data = pool.get('lims.interface.data')
        NotebookLine = pool.get('lims.notebook.line')

        unattended = Transaction().context.get('unattended', False)

        sheet_id = self._get_analysis_sheet_id()
        sheet = AnalysisSheet(sheet_id)
        table_id = sheet.compilation.table.id

        result_column = self._get_template_column(
            'result', table_id)
        if not result_column:
            if unattended:
                return 'end'
            raise UserError(gettext('lims_analysis_sheet.'
                'msg_template_not_result_field'))
        result_field = result_column.name

        result_modifier_column = self._get_template_column(
            'result_modifier', table_id)
        if not result_modifier_column:
            if unattended:
                return 'end'
            raise UserError(gettext('lims_analysis_sheet.'
                'msg_template_not_result_modifier_field'))
        result_modifier_field = result_modifier_column.name

        with Transaction().set_context(lims_interface_table=table_id):
            lines = Data.search([('compilation', '=', sheet.compilation.id)])
            for line in lines:
                nl = line.notebook_line
                if not nl:
                    continue

                result = getattr(line, result_field)
                if result is None:
                    continue
                result_modifier = getattr(line, result_modifier_field) or 'eq'
                if result_modifier != 'eq':
                    continue
                try:
                    value = float(result)
                except ValueError:
                    continue

                try:
                    dl = float(nl.detection_limit)
                    ql = float(nl.quantification_limit)
                except (TypeError, ValueError):
                    continue
                ll = nl.lower_limit and float(nl.lower_limit) or None
                ul = nl.upper_limit and float(nl.upper_limit) or None

                data = {}
                if (ll and value < ll) or (ul and value > ul):
                    raise UserError(gettext(
                        'lims.msg_error_limits_allowed',
                        line=nl.rec_name))
                if dl < value and value < ql:
                    data[result_field] = str(ql)
                    data[result_modifier_field] = 'low'
                elif value < dl:
                    data[result_field] = None
                    data[result_modifier_field] = 'nd'
                elif value == dl:
                    data[result_field] = str(ql)
                    data[result_modifier_field] = 'low'
                else:
                    data[result_modifier_field] = 'eq'

                if data:
                    Data.write([line], data)
                    if data[result_modifier_field] != 'eq':
                        NotebookLine.write([nl], {'backup': str(value)})

        return 'end'

    def _get_template_column(self, field_name, table_id):
        pool = Pool()
        Field = pool.get('lims.interface.table.field')

        table_column = Field.search([
            ('table', '=', table_id),
            ('transfer_field', '=', True),
            ('related_line_field.name', '=', field_name),
            ])
        return table_column and table_column[0] or None

    def end(self):
        return 'reload'


class EvaluateRules(Wizard):
    'Evaluate Rules'
    __name__ = 'lims.analysis_sheet.evaluate_rules'

    start_state = 'check'
    check = StateTransition()
    evaluate = StateTransition()

    def _get_analysis_sheet_id(self):
        return Transaction().context.get('lims_analysis_sheet', None)

    def transition_check(self):
        AnalysisSheet = Pool().get('lims.analysis_sheet')

        sheet_id = self._get_analysis_sheet_id()
        if sheet_id:
            sheet = AnalysisSheet(sheet_id)
            if sheet.state in ('active', 'validated'):
                return 'evaluate'

        return 'end'

    def transition_evaluate(self):
        pool = Pool()
        AnalysisSheet = pool.get('lims.analysis_sheet')
        Data = pool.get('lims.interface.data')
        NotebookRule = pool.get('lims.rule')

        sheet_id = self._get_analysis_sheet_id()
        sheet = AnalysisSheet(sheet_id)

        with Transaction().set_context(
                lims_interface_table=sheet.compilation.table.id,
                lims_interface_compilation=sheet.compilation.id,
                lims_analysis_sheet=sheet.id):
            lines = Data.search([('compilation', '=', sheet.compilation.id)])
            for line in lines:
                rules = NotebookRule.search([
                    ('analysis', '=', line.notebook_line.analysis),
                    ])
                for rule in rules:
                    if rule.eval_sheet_condition(line):
                        rule.exec_sheet_action(line)
        return 'end'

    def end(self):
        return 'reload'


class EditGroupedDataStart(ModelView):
    'Edit Grouped Data'
    __name__ = 'lims.analysis_sheet.edit_grouped_data.start'

    data = fields.One2Many('lims.interface.data', None, 'Data')


class EditGroupedData(Wizard):
    'Edit Grouped Data'
    __name__ = 'lims.analysis_sheet.edit_grouped_data'

    start_state = 'check'
    check = StateTransition()
    start = StateView('lims.analysis_sheet.edit_grouped_data.start',
        'lims_analysis_sheet.analysis_sheet_edit_grouped_data_start_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Save', 'save', 'tryton-save', default=True),
            ])
    save = StateTransition()

    def _get_analysis_sheet_id(self):
        return Transaction().context.get('lims_analysis_sheet', None)

    def transition_check(self):
        AnalysisSheet = Pool().get('lims.analysis_sheet')

        line_id = Transaction().context.get('active_id', None)
        sheet_id = self._get_analysis_sheet_id()
        if line_id and sheet_id:
            sheet = AnalysisSheet(sheet_id)
            if sheet.state in ('active', 'validated', 'done'):
                return 'start'

        return 'end'

    def default_start(self, fields):
        pool = Pool()
        AnalysisSheet = pool.get('lims.analysis_sheet')
        Data = pool.get('lims.interface.data')

        line_id = Transaction().context.get('active_id', None)
        sheet_id = self._get_analysis_sheet_id()
        sheet = AnalysisSheet(sheet_id)
        fields = [f for f in sheet.compilation.table.fields_]

        data = []
        with Transaction().set_context(
                lims_interface_table=sheet.compilation.table.id):
            line = Data.search([('id', '=', line_id)])[0]
            record = {
                'notebook_line': line.notebook_line.id,
                }
            for field in fields:
                if field.group:
                    continue
                val = getattr(line, '%s' % (field.name, ))
                if val != 0.0 and not val:
                    continue
                if field.type == 'many2one':
                    record[field.name] = val and val.id or None
                else:
                    record[field.name] = val

            grouped_fields = defaultdict(list)
            for field in sheet.compilation.table.grouped_fields_:
                grouped_fields[field.group].append(field)

            for group, repetition_fields in grouped_fields.items():
                for rep in sheet.template.interface.grouped_repetitions:
                    if rep.group == group:
                        reps = (rep.repetitions or 1) + 1
                        break

                group_fields = []
                for rep in range(1, reps):
                    grouped_record = {
                        'notebook_line': line.notebook_line.id,
                        'data': line.id,
                        'iteration': rep,
                        }
                    for field in repetition_fields:
                        val = getattr(line, '%s_%s' % (field.name, str(rep)))
                        if field.type == 'many2one':
                            grouped_record[field.name] = val and val.id or None
                        else:
                            grouped_record[field.name] = val
                    group_fields.append(grouped_record)
                record['group_%s' % (group, )] = group_fields

            data.append(record)

        defaults = {
            'data': data,
            }
        return defaults

    def transition_save(self):
        pool = Pool()
        AnalysisSheet = pool.get('lims.analysis_sheet')
        Data = pool.get('lims.interface.data')

        line_id = Transaction().context.get('active_id', None)
        sheet_id = self._get_analysis_sheet_id()
        sheet = AnalysisSheet(sheet_id)

        if sheet.state not in ('active', 'validated'):
            return 'end'

        fields = [f for f in sheet.compilation.table.fields_]
        grouped_fields = [f for f in sheet.compilation.table.grouped_fields_]

        with Transaction().set_context(
                lims_interface_table=sheet.compilation.table.id):
            line = Data.search([('id', '=', line_id)])[0]
            res = {}
            for data in self.start.data:
                groups = 0
                for field in fields:
                    groups = max(groups, field.group or 0)
                    value = getattr(data, field.name)

                    if isinstance(value, list):
                        value = str(value)
                    elif not isinstance(value,
                            (str, int, float, Decimal, type(None))):
                        value = value.tolist()
                    if isinstance(value, formulas.tokens.operand.XlError):
                        value = None
                    elif isinstance(value, list):
                        for x in chain(*value):
                            if isinstance(x, formulas.tokens.operand.XlError):
                                value = None
                    res[field.name] = value

                for group in range(1, groups + 1):
                    for group_data in getattr(
                            data, 'group_%s' % (group, )):
                        for field in grouped_fields:
                            if field.group != group:
                                continue
                            field_name = '%s_%s' % (
                                field.name, str(group_data['iteration']))
                            value = group_data[field.name]
                            if value != 0.0 and not value:
                                continue

                            if isinstance(value, list):
                                value = str(value)
                            elif not isinstance(value,
                                    (str, int, float, Decimal, type(None))):
                                value = value.tolist()
                            if isinstance(
                                    value, formulas.tokens.operand.XlError):
                                value = None
                            elif isinstance(value, list):
                                for x in chain(*value):
                                    if isinstance(
                                            x, formulas.tokens.operand.XlError):
                                        value = None
                            res[field_name] = value

            Data.write([line], res)

        return 'end'

    def end(self):
        return 'reload'


class EditMultiSampleDataStart(ModelView):
    'Edit Multi Sample Data'
    __name__ = 'lims.analysis_sheet.edit_multi_sample_data.start'

    data = fields.One2Many('lims.interface.multi_sample_data', None, 'Data')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.__rpc__['fields_view_get'].cache = None

    @classmethod
    def fields_view_get(cls, view_id=None, view_type='form', level=None):
        result = super().fields_view_get(view_id, view_type, level)
        key = (cls.__name__, view_id, view_type, level)
        cls._fields_view_get_cache.set(key, False)
        return result


class MultiSampleData(ModelView):
    'Multi Sample Data'
    __name__ = 'lims.interface.multi_sample_data'

    fraction = fields.Char('Sample', readonly=True)

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.__rpc__['fields_view_get'].cache = None

    def __init__(self, id=None, **kwargs):
        kwargs_copy = kwargs.copy()
        for kw in kwargs_copy:
            kwargs.pop(kw, None)
        super().__init__(id, **kwargs)
        self._values = {}
        for kw in kwargs_copy:
            self._values[kw] = kwargs_copy[kw]

    def __getattr__(self, name):
        try:
            return super().__getattr__(name)
        except AttributeError:
            pass

    @classmethod
    def fields_view_get(cls, view_id=None, view_type='form', level=None):
        pool = Pool()
        AnalysisSheet = pool.get('lims.analysis_sheet')
        Data = pool.get('lims.interface.data')

        sheet = AnalysisSheet(Transaction().context.get('active_id'))
        fields = {
            'fraction': {'default_width': 100},
            }

        add_analysis_columns = False
        for view_column in sheet.view.columns:
            if not view_column.analysis_specific:
                fields[view_column.column.alias] = {
                    'default_width': view_column.column.default_width or 100,
                    }
            else:
                add_analysis_columns = True

        if add_analysis_columns:
            analysis_codes = set()
            with Transaction().set_context(
                    lims_interface_table=sheet.compilation.table.id):
                lines = Data.search([
                    ('compilation', '=', sheet.compilation.id),
                    ])
                for line in lines:
                    analysis_codes.add(line.notebook_line.analysis.code)
            for analysis in list(analysis_codes):
                fields[analysis] = {
                    'default_width': 60,
                    }

        res = {
            'type': 'tree',
            'view_id': view_id,
            'field_childs': None,
            'arch': cls.get_tree_multi_sample_view(fields),
            'fields': cls.fields_get(),
            'model': cls.__name__,
            }

        return res

    @classmethod
    def fields_get(cls, fields=None):
        pool = Pool()
        AnalysisSheet = pool.get('lims.analysis_sheet')
        Data = pool.get('lims.interface.data')

        sheet = AnalysisSheet(Transaction().context.get('active_id'))
        readonly = (sheet.state not in ('active', 'validated'))
        res = {
            'fraction': {
                'name': 'sample',
                'string': 'Sample',
                'type': 'char',
                'help': '',
                'readonly': True,
                },
            }

        add_analysis_columns = False
        analysis_column_type = 'float'
        for view_column in sheet.view.columns:
            if not view_column.analysis_specific:
                res[view_column.column.alias] = {
                    'name': view_column.column.alias,
                    'string': view_column.column.name,
                    'type': view_column.column.type_,
                    'help': '',
                    'readonly': bool(view_column.column.expression or
                        view_column.column.readonly or readonly),
                    }
            else:
                add_analysis_columns = True
                analysis_column_type = view_column.column.type_

        if add_analysis_columns:
            analysis_codes = set()
            with Transaction().set_context(
                    lims_interface_table=sheet.compilation.table.id):
                lines = Data.search([
                    ('compilation', '=', sheet.compilation.id),
                    ])
                for line in lines:
                    analysis_codes.add(line.notebook_line.analysis.code)
            for analysis in list(analysis_codes):
                res[analysis] = {
                    'name': analysis,
                    'string': analysis,
                    'type': analysis_column_type,
                    'help': '',
                    'readonly': readonly,
                    }

        return res

    @classmethod
    def get_tree_multi_sample_view(cls, fields):
        fields = cls._get_fields_tree_multi_sample_view(fields)
        return ('<?xml version="1.0"?>\n'
            '<tree editable="bottom">\n'
            '%s\n'
            '</tree>') % ('\n'.join(fields))

    @classmethod
    def _get_fields_tree_multi_sample_view(cls, fields):
        view_fields = []
        for field, values in fields.items():
            view_fields.append('<field name="%s" width="%s"/>' % (
                field, values['default_width']))
        return view_fields


class EditMultiSampleData(Wizard):
    'Edit Multi Sample Data'
    __name__ = 'lims.analysis_sheet.edit_multi_sample_data'

    start_state = 'check'
    check = StateTransition()
    start = StateView('lims.analysis_sheet.edit_multi_sample_data.start',
        'lims_analysis_sheet.analysis_sheet_edit_multi_sample_data_start'
        '_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Save', 'save', 'tryton-save', default=True),
            ])
    save = StateTransition()

    def transition_check(self):
        AnalysisSheet = Pool().get('lims.analysis_sheet')

        sheet_id = Transaction().context.get('active_id', None)
        if sheet_id:
            sheet = AnalysisSheet(sheet_id)
            if sheet.view and sheet.state in ('active', 'validated', 'done'):
                return 'start'

        return 'end'

    def default_start(self, fields):
        pool = Pool()
        AnalysisSheet = pool.get('lims.analysis_sheet')
        Data = pool.get('lims.interface.data')

        sheet_id = Transaction().context.get('active_id', None)
        sheet = AnalysisSheet(sheet_id)

        records = {}
        with Transaction().set_context(
                lims_interface_table=sheet.compilation.table.id):
            lines = Data.search([('compilation', '=', sheet.compilation.id)])
            for line in lines:
                fraction = line.notebook_line.fraction.number
                if fraction not in records.keys():
                    records[fraction] = {'fraction': fraction}
                for view_column in sheet.view.columns:
                    if view_column.analysis_specific:
                        alias = line.notebook_line.analysis.code
                    else:
                        alias = view_column.column.alias
                    records[fraction][alias] = getattr(
                        line, view_column.column.alias)

        data = list(records.values())
        defaults = {
            'data': data,
            }
        return defaults

    def transition_save(self):
        pool = Pool()
        AnalysisSheet = pool.get('lims.analysis_sheet')
        Data = pool.get('lims.interface.data')

        sheet_id = Transaction().context.get('active_id', None)
        sheet = AnalysisSheet(sheet_id)

        if sheet.state not in ('active', 'validated'):
            return 'end'

        columns = {}
        for view_column in sheet.view.columns:
            if view_column.analysis_specific:
                analysis_codes = set()
                with Transaction().set_context(
                        lims_interface_table=sheet.compilation.table.id):
                    lines = Data.search([
                        ('compilation', '=', sheet.compilation.id),
                        ])
                    for line in lines:
                        analysis_codes.add(line.notebook_line.analysis.code)
                for alias in list(analysis_codes):
                    columns[alias] = {
                        'field': view_column.column.alias,
                        'is_analysis': True,
                        }
            else:
                alias = view_column.column.alias
                columns[alias] = {
                    'field': view_column.column.alias,
                    'is_analysis': False,
                    }
        with Transaction().set_context(
                lims_interface_table=sheet.compilation.table.id):
            for data in self.start.data:
                fraction_clause = [
                    ('compilation', '=', sheet.compilation.id),
                    ('notebook_line.fraction.number', '=', data.fraction),
                    ]
                for alias, field in columns.items():
                    value = getattr(data, alias)
                    if field['is_analysis']:
                        analysis_clause = [
                            ('notebook_line.analysis.code', '=', alias),
                            ]
                    else:
                        analysis_clause = []
                    lines = Data.search(fraction_clause + analysis_clause)
                    if not lines:
                        continue
                    Data.write(lines, {field['field']: value})

        return 'end'

    def end(self):
        return 'reload'

    def _save(self):
        pass
