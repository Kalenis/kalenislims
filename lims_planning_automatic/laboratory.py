# This file is part of lims_planning_automatic module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from datetime import date

from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction


class Laboratory(metaclass=PoolMeta):
    __name__ = 'lims.laboratory'

    automatic_planning = fields.Boolean('Automatic Planning')
    automatic_planning_simplified = fields.Boolean(
        'Simplified Automatic Planning')


class NotebookRule(metaclass=PoolMeta):
    __name__ = 'lims.rule'

    def _exec_add_service(self, line, typification):
        notebook_lines = super()._exec_add_service(line, typification)
        self._automatic_plan(notebook_lines)
        return notebook_lines

    def _exec_sheet_add_service(self, line, typification):
        notebook_lines = super()._exec_sheet_add_service(line, typification)
        self._automatic_plan(notebook_lines)
        return notebook_lines

    def _automatic_plan(self, notebook_lines):
        pool = Pool()
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        NotebookLine = pool.get('lims.notebook.line')
        AnalysisSheet = pool.get('lims.analysis_sheet')
        Planification = pool.get('lims.planification')

        if not notebook_lines:
            return

        today = date.today()

        entries = []
        sheet_id = Transaction().context.get('lims_analysis_sheet', None)
        if sheet_id:
            sheet = AnalysisSheet(sheet_id)
            nlines_same_sheet, nlines_other_sheet = [], []
            for nl in notebook_lines:
                if nl.get_analysis_sheet_template() == sheet.template.id:
                    nlines_same_sheet.append(nl)
                else:
                    nlines_other_sheet.append(nl)
            if nlines_same_sheet:  # no need to plan
                NotebookLine.write(nlines_same_sheet, {'start_date': today})
                analysis_details = [nl.analysis_detail
                    for nl in nlines_same_sheet]
                EntryDetailAnalysis.write(analysis_details,
                    {'state': 'planned'})
                sheet.create_lines(nlines_same_sheet)
            entries = list(set(nl.sample.entry for nl in nlines_other_sheet))
        else:
            entries = list(set(nl.sample.entry for nl in notebook_lines))
        if entries:
            Planification.automatic_plan(entries=entries)

    def _add_service_to_sheet(self, notebook_lines):
        # overwritten by _automatic_plan when calling _exec_sheet_add_service
        return
