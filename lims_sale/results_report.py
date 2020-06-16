# This file is part of lims_sale module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.wizard import Wizard, StateAction
from trytond.pool import Pool
from trytond.pyson import PYSONEncoder
from trytond.transaction import Transaction

__all__ = ['OpenSampleSale', 'OpenResultsDetailSale']


class OpenSampleSale(Wizard):
    'Sample Sale'
    __name__ = 'lims.notebook.open_sale'

    start = StateAction('sale.act_sale_form')

    def do_start(self, action):
        Notebook = Pool().get('lims.notebook')

        active_ids = Transaction().context['active_ids']
        notebooks = Notebook.browse(active_ids)

        sale_ids = []
        for n in notebooks:
            if n.fraction.sample.sale_lines:
                for sale_line in n.fraction.sample.sale_lines:
                    sale_ids.append(sale_line.sale.id)

        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', 'in', sale_ids),
            ])
        action['name'] += ' (%s)' % ', '.join(n.rec_name for n in notebooks)
        return action, {}


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
        action['name'] += ' (%s)' % ', '.join(d.rec_name for d in details)
        return action, {}
