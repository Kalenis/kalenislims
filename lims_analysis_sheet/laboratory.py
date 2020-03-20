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
        pool = Pool()
        Typification = pool.get('lims.typification')

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
            Transaction().context.get('lims_interface_compilation'),
            line.notebook_line.notebook.id, self.target_analysis.id)
        if not existing_line:
            self._exec_sheet_add_service(line, typification[0])
        #else:
            #self._exec_sheet_add_repetition(existing_line)

    def _exec_sheet_add_repetition(self, line):
        pool = Pool()
        Date = pool.get('ir.date')
        NotebookLine = pool.get('lims.notebook.line')
        AnalysisSheet = pool.get('lims.analysis_sheet')

        date = Date.today()
        notebook_line = line.notebook_line
        repetition = self._get_line_last_repetition(notebook_line)
        line_create = [{
            'notebook': notebook_line.notebook.id,
            'analysis_detail': notebook_line.analysis_detail.id,
            'service': notebook_line.service.id,
            'analysis': self.target_analysis.id,
            'analysis_origin': notebook_line.analysis_origin,
            'repetition': repetition + 1,
            'laboratory': notebook_line.laboratory.id,
            'method': notebook_line.method.id,
            'device': (notebook_line.device and
                notebook_line.device.id or None),
            'initial_concentration': notebook_line.initial_concentration,
            'decimals': notebook_line.decimals,
            'report': notebook_line.report,
            'concentration_level': (notebook_line.concentration_level and
                notebook_line.concentration_level.id or None),
            'results_estimated_waiting': (
                notebook_line.results_estimated_waiting),
            'department': notebook_line.department,
            'final_concentration': notebook_line.final_concentration,
            'initial_unit': (notebook_line.initial_unit and
                notebook_line.initial_unit.id or None),
            'final_unit': (notebook_line.final_unit and
                notebook_line.final_unit.id or None),
            'detection_limit': notebook_line.detection_limit,
            'quantification_limit': notebook_line.quantification_limit,
            'start_date': date,
            }]
        notebook_lines = NotebookLine.create(line_create)
        if notebook_lines:
            sheet = AnalysisSheet(
                Transaction().context.get('lims_analysis_sheet'))
            sheet.create_lines(notebook_lines)

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
            if notebook_lines:
                date = Date.today()
                NotebookLine.write(notebook_lines, {'start_date': date})
                sheet = AnalysisSheet(
                    Transaction().context.get('lims_analysis_sheet'))
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
                Transaction().context.get('lims_interface_compilation'),
                line.notebook_line.notebook.id, self.target_analysis.id)
            if not sheet_line:
                return

        if sheet_line.annulled:
            return

        try:
            sheet_line.set_field(str(self.value), target_field)
        except Exception as e:
            return

    def _get_existing_line(self, compilation_id, notebook_id, analysis_id):
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        Data = pool.get('lims.interface.data')

        notebook_lines = NotebookLine.search([
            ('notebook', '=', notebook_id),
            ('analysis', '=', analysis_id),
            ])
        nl_ids = [nl.id for nl in notebook_lines]
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
        result = operator_func[self.condition](value, self.value)
        return result

    def check_field(self):
        if not self.rule.analysis_sheet:
            super(NotebookRuleCondition, self).check_field()
