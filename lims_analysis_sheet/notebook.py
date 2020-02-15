# This file is part of lims_analysis_sheet module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction

__all__ = ['NotebookLine']


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
