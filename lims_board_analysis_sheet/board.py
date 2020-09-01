# This file is part of lims_board_analysis_sheet module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelView, fields
from trytond.pool import PoolMeta, Pool
from trytond.transaction import Transaction


class BoardLaboratory(metaclass=PoolMeta):
    __name__ = 'lims.board.laboratory'

    analysis_sheet_templates = fields.One2Many(
        'lims.board.laboratory.analysis_sheet_template', None,
        'Unplanned samples per Analysis sheet', states={'readonly': True})

    @ModelView.button_change('analysis_sheet_templates')
    def apply_filter(self):
        super().apply_filter()
        self.analysis_sheet_templates = self.get_analysis_sheet_templates()

    def get_analysis_sheet_templates(self):
        pool = Pool()
        TemplateAnalysisSheet = pool.get('lims.template.analysis_sheet')

        records = []

        with Transaction().set_context(
                date_from=self.date_from, date_to=self.date_to):
            templates = TemplateAnalysisSheet.browse(self._get_templates())
            for t in templates:
                record = {'t': t.name, 'q': t.pending_fractions}
                records.append(record)

        return records

    def _get_templates(self):
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
        if self.date_from:
            dates_where += ('AND ad.confirmation_date::date >= \'%s\'::date ' %
                self.date_from)
        if self.date_to:
            dates_where += ('AND ad.confirmation_date::date <= \'%s\'::date ' %
                self.date_to)

        sql_select = 'SELECT nl.analysis, nl.method '
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
            'AND nla.behavior != \'internal_relation\' ' +
            preplanned_where + dates_where)

        with Transaction().set_user(0):
            cursor.execute(sql_select + sql_from + sql_where)
        notebook_lines = cursor.fetchall()
        if not notebook_lines:
            return []

        result = []
        for nl in notebook_lines:
            cursor.execute('SELECT template '
                'FROM "' + TemplateAnalysis._table + '" '
                'WHERE analysis = %s '
                'AND (method = %s OR method IS NULL)',
                (nl[0], nl[1]))
            template = cursor.fetchone()
            if template:
                result.append(template[0])
        return list(set(result))


class BoardLaboratoryTemplateAnalysisSheet(ModelView):
    'Laboratory Dashboard - Analysis sheet template'
    __name__ = 'lims.board.laboratory.analysis_sheet_template'

    t = fields.Char('Analysis Sheet', readonly=True)
    q = fields.Integer('Samples Qty.', readonly=True)
