# This file is part of lims_analysis_sheet module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateTransition, StateView, Button
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction

__all__ = ['NotebookLine', 'AddFractionControlStart', 'AddFractionControl']


class NotebookLine(metaclass=PoolMeta):
    __name__ = 'lims.notebook.line'

    def get_analysis_sheet_template(self):
        cursor = Transaction().connection.cursor()
        TemplateAnalysis = Pool().get('lims.template.analysis_sheet.analysis')

        cursor.execute('SELECT template '
            'FROM "' + TemplateAnalysis._table + '" '
            'WHERE analysis = %s '
            'AND (method = %s OR method IS NULL)',
            (self.analysis.id, self.method.id))
        template = cursor.fetchone()
        return template and template[0] or None


class AddFractionControlStart(ModelView):
    'Add Fraction Control'
    __name__ = 'lims.analysis_sheet.add_fraction_con.start'

    original_fraction = fields.Many2One('lims.fraction', 'Fraction',
        required=True, domain=[('id', 'in', Eval('fraction_domain'))],
        depends=['fraction_domain'])
    fraction_domain = fields.Many2Many('lims.fraction', None, None,
        'Fraction domain')


class AddFractionControl(Wizard):
    'Add Fraction Control'
    __name__ = 'lims.analysis_sheet.add_fraction_con'

    start_state = 'check'
    check = StateTransition()
    start = StateView('lims.analysis_sheet.add_fraction_con.start',
        'lims_analysis_sheet.analysis_sheet_add_fraction_con_start_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Add', 'add', 'tryton-ok', default=True),
            ])
    add = StateTransition()

    def transition_check(self):
        pool = Pool()
        AnalysisSheet = pool.get('lims.analysis_sheet')

        analysis_sheet_id = Transaction().context['active_id']
        analysis_sheet = AnalysisSheet(analysis_sheet_id)

        if analysis_sheet.state in ('active', 'validated'):
            return 'start'
        return 'end'

    def default_start(self, fields):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        AnalysisSheet = pool.get('lims.analysis_sheet')
        Analysis = pool.get('lims.analysis')
        Fraction = pool.get('lims.fraction')
        NotebookLine = pool.get('lims.notebook.line')
        Notebook = pool.get('lims.notebook')

        defaults = {
            'fraction_domain': [],
            }

        analysis_sheet_id = Transaction().context['active_id']
        analysis_sheet = AnalysisSheet(analysis_sheet_id)

        t_analysis_ids = []
        for t_analysis in analysis_sheet.template.analysis:
            if t_analysis.analysis.type == 'analysis':
                t_analysis_ids.append(t_analysis.analysis.id)
            else:
                t_analysis_ids.extend(
                    Analysis.get_included_analysis_analysis(
                        t_analysis.analysis.id))

        stored_fractions_ids = Fraction.get_stored_fractions()

        notebook_lines = NotebookLine.search([
            ('notebook.fraction.special_type', '=', 'con'),
            ('notebook.fraction.id', 'in', stored_fractions_ids),
            ('analysis', 'in', t_analysis_ids),
            ('result', 'in', (None, '')),
            ('end_date', '=', None),
            ('annulment_date', '=', None),
            ])
        if notebook_lines:
            notebook_lines_ids = ', '.join(str(nl.id) for nl in notebook_lines)
            cursor.execute('SELECT DISTINCT(n.fraction) '
                'FROM "' + Notebook._table + '" n '
                    'INNER JOIN "' + NotebookLine._table + '" nl '
                    'ON nl.notebook = n.id '
                'WHERE nl.id IN (' + notebook_lines_ids + ')')
            defaults['fraction_domain'] = [x[0] for x in cursor.fetchall()]

        return defaults

    def transition_add(self):
        pool = Pool()
        AnalysisSheet = pool.get('lims.analysis_sheet')
        Analysis = pool.get('lims.analysis')
        NotebookLine = pool.get('lims.notebook.line')

        analysis_sheet_id = Transaction().context['active_id']
        analysis_sheet = AnalysisSheet(analysis_sheet_id)

        t_analysis_ids = []
        for t_analysis in analysis_sheet.template.analysis:
            if t_analysis.analysis.type == 'analysis':
                t_analysis_ids.append(t_analysis.analysis.id)
            else:
                t_analysis_ids.extend(
                    Analysis.get_included_analysis_analysis(
                        t_analysis.analysis.id))

        clause = [
            ('notebook.fraction.id', '=', self.start.original_fraction.id),
            ('analysis', 'in', t_analysis_ids),
            ('result', 'in', (None, '')),
            ('end_date', '=', None),
            ('annulment_date', '=', None),
            ]
        notebook_lines = NotebookLine.search(clause)
        if notebook_lines:
            analysis_sheet.create_lines(notebook_lines)
        return 'end'
