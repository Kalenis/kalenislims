# This file is part of lims_planning_automatic module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction


class NotebookRepeatAnalysis(metaclass=PoolMeta):
    __name__ = 'lims.notebook.repeat_analysis'

    def transition_repeat(self):
        pool = Pool()
        Notebook = pool.get('lims.notebook')
        Planification = pool.get('lims.planification')

        res = super().transition_repeat()

        entries = set()
        for notebook in Notebook.browse(Transaction().context['active_ids']):
            entries.add(notebook.fraction.entry)
        Planification.automatic_plan(entries=list(entries))
        return res


class NotebookLineRepeatAnalysis(metaclass=PoolMeta):
    __name__ = 'lims.notebook.line.repeat_analysis'

    def transition_repeat(self):
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        Planification = pool.get('lims.planification')

        res = super().transition_repeat()

        line_id = self._get_notebook_line_id()
        notebook_line = NotebookLine(line_id)
        entries = [notebook_line.notebook.fraction.entry]
        Planification.automatic_plan(entries=entries)
        return res
