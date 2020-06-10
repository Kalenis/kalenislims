# This file is part of lims_analysis_sheet module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import operator

from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction

__all__ = ['NotebookRule', 'NotebookRuleCondition']


class NotebookRule(metaclass=PoolMeta):
    __name__ = 'lims.rule'

    analysis_sheet = fields.Boolean('For use in Analysis Sheets')

    @staticmethod
    def default_analysis_sheet():
        return False

    def eval_condition(self, line):
        if self.analysis_sheet:
            return False
        return super(NotebookRule, self).eval_condition(line)

    def eval_sheet_condition(self, line):
        for condition in self.conditions:
            if not condition.eval_sheet_condition(line):
                return False
        return True

    def exec_sheet_action(self, line):
        if self.action == 'add':
            self._exec_sheet_add(line)
        elif self.action == 'edit':
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
            line.notebook_line.notebook.id, self.target_analysis.id)
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
        Date = pool.get('ir.date')
        AnalysisSheet = pool.get('lims.analysis_sheet')

        cursor.execute('SELECT DISTINCT(laboratory) '
            'FROM "' + AnalysisLaboratory._table + '" '
            'WHERE analysis = %s',
            (self.target_analysis.id,))
        laboratories = [x[0] for x in cursor.fetchall()]
        if not laboratories:
            return
        laboratory_id = laboratories[0]

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
            notebook_lines = NotebookLine.search([
                ('analysis_detail', 'in', [d.id for d in analysis_detail])])
            sheet = AnalysisSheet(Transaction().context.get(
                'lims_analysis_sheet'))
            notebook_lines = [nl for nl in notebook_lines if
                nl.get_analysis_sheet_template() == sheet.template.id]
            if notebook_lines:
                date = Date.today()
                NotebookLine.write(notebook_lines, {'start_date': date})
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
                Transaction().context.get('lims_interface_compilation'))
            if not sheet_line:
                return

        if sheet_line.annulled:
            return

        try:
            Data.write([sheet_line], {target_field: str(self.value)})
        except Exception as e:
            return

    def _get_existing_line(self, notebook_id, analysis_id,
            compilation_id=None):
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        Data = pool.get('lims.interface.data')

        notebook_lines = NotebookLine.search([
            ('notebook', '=', notebook_id),
            ('analysis', '=', analysis_id),
            ])
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
            }
        try:
            result = operator_func[self.condition](
                float(value), float(self.value))
        except (TypeError, ValueError):
            result = (value and operator_func[self.condition](
                str(value), str(self.value)) or False)
        return result

    def check_field(self):
        if not self.rule.analysis_sheet:
            super(NotebookRuleCondition, self).check_field()
