# This file is part of lims_analysis_sheet module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from datetime import datetime, date
import operator

from trytond.model import ModelSQL, ModelView, fields
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from trytond.pyson import Eval, Bool, And


class LabDevice(metaclass=PoolMeta):
    __name__ = 'lims.lab.device'

    constants = fields.One2Many('lims.lab.device.constant', 'device',
        'Constants')

    def get_constant(self, name, value=None):
        pool = Pool()
        DeviceConstant = pool.get('lims.lab.device.constant')

        if not name:
            return None
        if not value:
            value = 'value1'

        constant = DeviceConstant.search([
            ('device', '=', self.id),
            ('name', '=', name),
            ])
        if not constant:
            return None

        constant = constant[0]
        if hasattr(constant, value):
            return getattr(constant, value)

        return None


class LabDeviceConstant(ModelSQL, ModelView):
    'Device Constant'
    __name__ = 'lims.lab.device.constant'

    device = fields.Many2One('lims.lab.device', 'Device', required=True,
        ondelete='CASCADE', select=True)
    name = fields.Float('Name', required=True)
    value1 = fields.Float('Value 1')
    value2 = fields.Float('Value 2')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order.insert(0, ('name', 'ASC'))


class NotebookRule(metaclass=PoolMeta):
    __name__ = 'lims.rule'

    analysis_sheet = fields.Boolean('For use in Analysis Sheets')
    apply_on_notebook = fields.Boolean('Apply directly on the Notebook',
        states={'readonly': ~And(
            Bool(Eval('analysis_sheet')), Eval('action') == 'edit')},
        depends=['analysis_sheet', 'action'])

    @staticmethod
    def default_analysis_sheet():
        return False

    @staticmethod
    def default_apply_on_notebook():
        return False

    def eval_condition(self, line):
        if self.analysis_sheet:
            return False
        return super().eval_condition(line)

    def eval_sheet_condition(self, line):
        if not self.analysis_sheet:
            return False
        for condition in self.conditions:
            if not condition.eval_sheet_condition(line):
                return False
        return True

    def exec_sheet_action(self, line):
        if self.action == 'add':
            self._exec_sheet_add(line)
        elif self.action == 'edit':
            if self.apply_on_notebook:
                self._exec_notebook_edit(line)
            else:
                self._exec_sheet_edit(line)

    def _exec_sheet_add(self, line):
        Typification = Pool().get('lims.typification')

        typification = Typification.search([
            ('product_type', '=', line.notebook_line.product_type),
            ('matrix', '=', line.notebook_line.matrix),
            ('analysis', '=', self.target_analysis),
            ('by_default', '=', True),
            ('valid', '=', True),
            ], limit=1)
        if not typification:
            return

        existing_line = self._get_existing_line(
            line.notebook_line.notebook.id, self.target_analysis.id,
            self.target_method and self.target_method.id or None)
        if not existing_line:
            self._exec_sheet_add_service(line, typification[0])

    def _exec_sheet_add_service(self, line, typification):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        AnalysisLaboratory = pool.get('lims.analysis-laboratory')
        AnalysisDevice = pool.get('lims.analysis.device')
        Service = pool.get('lims.service')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        NotebookLine = pool.get('lims.notebook.line')
        AnalysisSheet = pool.get('lims.analysis_sheet')

        today = date.today()

        cursor.execute('SELECT DISTINCT(laboratory) '
            'FROM "' + AnalysisLaboratory._table + '" '
            'WHERE analysis = %s',
            (self.target_analysis.id,))
        laboratories = [x[0] for x in cursor.fetchall()]
        if not laboratories:
            return
        laboratory_id = laboratories[0]

        method_id = self.target_method and self.target_method.id or None
        if not method_id:
            method_id = typification.method and typification.method.id or None

        cursor.execute('SELECT DISTINCT(device) '
            'FROM "' + AnalysisDevice._table + '" '
            'WHERE active IS TRUE '
                'AND analysis = %s  '
                'AND laboratory = %s '
                'AND by_default IS TRUE',
            (self.target_analysis.id, laboratory_id))
        devices = [x[0] for x in cursor.fetchall()]
        device_id = devices and devices[0] or None

        service_create = [{
            'fraction': line.notebook_line.fraction.id,
            'analysis': self.target_analysis.id,
            'urgent': True,
            'laboratory': laboratory_id,
            'method': method_id,
            'device': device_id,
            }]
        with Transaction().set_context(manage_service=True):
            new_service, = Service.create(service_create)

        Service.copy_analysis_comments([new_service])
        Service.set_confirmation_date([new_service])
        analysis_detail = EntryDetailAnalysis.search([
            ('service', '=', new_service.id)])
        if analysis_detail:
            EntryDetailAnalysis.create_notebook_lines(analysis_detail,
                line.notebook_line.fraction)
            EntryDetailAnalysis.write(analysis_detail, {
                'state': 'unplanned',
                })

            notebook_lines = NotebookLine.search([
                ('analysis_detail', 'in', [d.id for d in analysis_detail])])
            if notebook_lines:
                NotebookLine.write(notebook_lines, {'rule': self.id})

            sheet = AnalysisSheet(Transaction().context.get(
                'lims_analysis_sheet'))
            notebook_lines = [nl for nl in notebook_lines if
                nl.get_analysis_sheet_template() == sheet.template.id]
            if notebook_lines:
                NotebookLine.write(notebook_lines, {'start_date': today})
                analysis_details = [nl.analysis_detail
                    for nl in notebook_lines]
                EntryDetailAnalysis.write(analysis_details,
                    {'state': 'planned'})
                sheet.create_lines(notebook_lines)

    def _exec_sheet_edit(self, line):
        pool = Pool()
        Field = pool.get('lims.interface.table.field')
        Data = pool.get('lims.interface.data')

        target_column = Field.search([
            ('table', '=', Transaction().context.get('lims_interface_table')),
            ('transfer_field', '=', True),
            ('related_line_field', '=', self.target_field),
            ])
        if not target_column:
            return
        target_field = target_column[0].name

        if line.notebook_line.analysis == self.target_analysis:
            sheet_line = Data(line.id)
        else:
            sheet_line = self._get_existing_line(
                line.notebook_line.notebook.id, self.target_analysis.id,
                self.target_method and self.target_method.id or None,
                Transaction().context.get('lims_interface_compilation'))
            if not sheet_line:
                return

        if sheet_line.annulled:
            return

        value = self.value
        if self.value.startswith('='):
            path = self.value[1:].split('.')
            field = path.pop(0)
            try:
                value = getattr(sheet_line, field)
                while path:
                    field = path.pop(0)
                    value = getattr(value, field)
            except AttributeError:
                value = None
        try:
            Data.write([sheet_line], {target_field: str(value)})
        except Exception as e:
            return

    def _exec_notebook_edit(self, line):
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        Data = pool.get('lims.interface.data')
        AnalysisSheet = pool.get('lims.analysis_sheet')
        Field = pool.get('lims.interface.table.field')

        now = datetime.now()
        today = now.date()

        # update notebook line
        if line.notebook_line.analysis == self.target_analysis:
            notebook_line = NotebookLine(line.notebook_line.id)
        else:
            clause = [
                ('notebook', '=', line.notebook_line.notebook),
                ('analysis', '=', self.target_analysis),
                ('accepted', '=', False),
                ('annulled', '=', False),
                ]
            if self.target_method:
                clause.append(('method', '=', self.target_method))
            target_line = NotebookLine.search(clause,
                order=[('repetition', 'DESC')], limit=1)
            if not target_line:
                return
            notebook_line = target_line[0]

        if notebook_line.accepted or notebook_line.annulled:
            return

        try:
            value = self.value
            if self.value.startswith('='):
                path = self.value[1:].split('.')
                field = path.pop(0)
                try:
                    value = getattr(line, field)
                    while path:
                        field = path.pop(0)
                        value = getattr(value, field)
                except AttributeError:
                    value = None
            if self.target_field.ttype == 'many2one':
                value = int(value)
            setattr(notebook_line, self.target_field.name, value)
            if self.target_field.name in ('result', 'literal_result'):
                if not notebook_line.start_date:
                    notebook_line.start_date = today
                notebook_line.end_date = today
                if notebook_line.laboratory.automatic_accept_result:
                    notebook_line.accepted = True
                    notebook_line.acceptance_date = now
            notebook_line.rule = self.id
            notebook_line.save()
        except Exception as e:
            return

        # find analysis sheet line and update it
        if notebook_line.analysis_sheet:
            sheets = [notebook_line.analysis_sheet]
        else:
            template_id = notebook_line.get_analysis_sheet_template()
            if not template_id:
                return
            sheets = AnalysisSheet.search([
                ('template', '=', template_id),
                ('state', 'in', ['draft', 'active', 'validated'])
                ], order=[('id', 'DESC')])
        for s in sheets:
            with Transaction().set_context(
                    lims_interface_table=s.compilation.table.id):
                lines = Data.search([
                    ('compilation', '=', s.compilation.id),
                    ('notebook_line', '=', notebook_line.id),
                    ], limit=1)
                if not lines:
                    continue
                target_column = Field.search([
                    ('table', '=', s.compilation.table.id),
                    ('transfer_field', '=', True),
                    ('related_line_field', '=', self.target_field),
                    ])
                if not target_column:
                    return
                target_field = target_column[0].name
                try:
                    Data.write(lines, {target_field: str(value)})
                except Exception as e:
                    return

    def _get_existing_line(self, notebook_id, analysis_id, method_id,
            compilation_id=None):
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        Data = pool.get('lims.interface.data')

        clause = [
            ('notebook', '=', notebook_id),
            ('analysis', '=', analysis_id),
            ('accepted', '=', False),
            ('annulled', '=', False),
            ]
        if method_id:
            clause.append(('method', '=', method_id))
        notebook_lines = NotebookLine.search(clause)
        nl_ids = [nl.id for nl in notebook_lines]
        if not compilation_id:
            return bool(len(nl_ids))

        existing_line = Data.search([
            ('compilation', '=', compilation_id),
            ('notebook_line', 'in', nl_ids),
            ], order=[('notebook_line', 'DESC')], limit=1)
        return existing_line and existing_line[0] or None


class NotebookRuleCondition(metaclass=PoolMeta):
    __name__ = 'lims.rule.condition'

    def eval_sheet_condition(self, line):
        path = self.field.split('.')
        field = path.pop(0)
        try:
            value = getattr(line, field)
            while path:
                field = path.pop(0)
                value = getattr(value, field)
        except AttributeError:
            return False

        operator_func = {
            'eq': operator.eq,
            'ne': operator.ne,
            'gt': operator.gt,
            'ge': operator.ge,
            'lt': operator.lt,
            'le': operator.le,
            'in': lambda v, l: v in l,
            'not_in': lambda v, l: v not in l,
            }

        if self.condition in ('in', 'not_in'):
            values = [str(x).strip() for x in self.value.split(',')]
            try:
                result = operator_func[self.condition](
                    float(value), [float(x) for x in values])
            except (TypeError, ValueError):
                result = (value and operator_func[self.condition](
                    str(value), [str(x) for x in values]) or False)
        else:
            try:
                result = operator_func[self.condition](
                    float(value), float(self.value))
            except (TypeError, ValueError):
                result = (value and operator_func[self.condition](
                    str(value), str(self.value)) or False)
        return result

    def check_field(self):
        if not self.rule.analysis_sheet:
            super().check_field()
