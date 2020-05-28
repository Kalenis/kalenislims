# This file is part of lims_sale module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.wizard import Wizard, StateAction
from trytond.pool import Pool
from trytond.pyson import PYSONEncoder
from trytond.transaction import Transaction

__all__ = ['OpenResultsDetailSale']


class OpenResultsDetailSale(Wizard):
    'Results Report Sale'
    __name__ = 'lims.results_report.version.detail.open_sale'

    start = StateAction('sale.act_sale_form')

    def do_start(self, action):
        pool = Pool()
        ResultsDetail = pool.get('lims.results_report.version.detail')
        ResultsSample = pool.get('lims.results_report.version.detail.sample')

        active_ids = Transaction().context['active_ids']
        details = ResultsDetail.browse(active_ids)

        sale_ids = []
        samples = ResultsSample.search([
            ('version_detail', 'in', active_ids),
            ])
        for s in samples:
            if s.notebook.fraction.sample.sale_lines:
                for sale_line in s.notebook.fraction.sample.sale_lines:
                    sale_ids.append(sale_line.sale.id)

        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', 'in', sale_ids),
            ])
        action['name'] += ' (%s)' % ', '.join(
            '%s-%s' % (d.report_version.number, d.number)
            for d in details)
        return action, {}
