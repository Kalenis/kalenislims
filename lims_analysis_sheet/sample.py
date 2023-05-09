# This file is part of lims_analysis_sheet module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction


class Sample(metaclass=PoolMeta):
    __name__ = 'lims.sample'

    analysis_sheet_activated_date = fields.Date(
        'Analysis sheet activation date', readonly=True)

    def _get_sample_dates(self):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Fraction = pool.get('lims.fraction')
        Service = pool.get('lims.service')
        NotebookLine = pool.get('lims.notebook.line')

        res = super()._get_sample_dates()

        # Sheet activation date
        cursor.execute('SELECT MIN(nl.analysis_sheet_activated_date) '
            'FROM "' + NotebookLine._table + '" nl '
                'INNER JOIN "' + Service._table + '" s '
                'ON s.id = nl.service '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON f.id = s.fraction '
            'WHERE f.sample = %s',
            (self.id,))
        res['analysis_sheet_activated_date'] = cursor.fetchone()[0] or None

        return res

    def _get_sample_state(self):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Fraction = pool.get('lims.fraction')
        Service = pool.get('lims.service')
        NotebookLine = pool.get('lims.notebook.line')

        sample_state = super()._get_sample_state()

        if sample_state == 'planned':
            cursor.execute('SELECT COUNT(*) '
                'FROM "' + NotebookLine._table + '" nl '
                    'INNER JOIN "' + Service._table + '" s '
                    'ON s.id = nl.service '
                    'INNER JOIN "' + Fraction._table + '" f '
                    'ON f.id = s.fraction '
                'WHERE f.sample = %s '
                    'AND nl.report = TRUE '
                    'AND nl.annulled = FALSE '
                    'AND nl.analysis_sheet_activated_date IS NOT NULL',
                (self.id,))
            if cursor.fetchone()[0] > 0:
                return 'in_lab'
        return sample_state
