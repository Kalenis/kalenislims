# This file is part of lims_sale module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.wizard import Wizard, StateAction
from trytond.pool import Pool, PoolMeta
from trytond.pyson import PYSONEncoder
from trytond.transaction import Transaction


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


class OpenResultsDetailAttachment(metaclass=PoolMeta):
    __name__ = 'lims.results_report.version.detail.open_attachment'

    def get_resource(self, details):
        res = super().get_resource(details)
        for detail in details:
            for s in detail.samples:
                if s.notebook.fraction.sample.sale_lines:
                    for sale_line in s.notebook.fraction.sample.sale_lines:
                        res.append(self._get_resource(sale_line.sale))
        return res


class ResultsReportVersionDetail(metaclass=PoolMeta):
    __name__ = 'lims.results_report.version.detail'

    @classmethod
    def get_contract_numbers(cls, details, name):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Service = pool.get('lims.service')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        NotebookLine = pool.get('lims.notebook.line')
        ResultsLine = pool.get('lims.results_report.version.detail.line')
        ResultsSample = pool.get('lims.results_report.version.detail.sample')

        result = {}
        for d in details:
            result[d.id] = ''
            cursor.execute('SELECT ad.service '
                'FROM "' + EntryDetailAnalysis._table + '" ad '
                    'INNER JOIN "' + NotebookLine._table + '" nl '
                    'ON ad.id = nl.analysis_detail '
                    'INNER JOIN "' + ResultsLine._table + '" rl '
                    'ON nl.id = rl.notebook_line '
                    'INNER JOIN "' + ResultsSample._table + '" rs '
                    'ON rl.detail_sample = rs.id '
                'WHERE rs.version_detail = %s', (d.id,))
            service_ids = [int(x[0]) for x in cursor.fetchall()]
            if not service_ids:
                continue
            contract_numbers = set()
            services = Service.browse(service_ids)
            for service in services:
                if service.contract_number:
                    contract_numbers.add(service.contract_number)
                elif service.sale_lines:
                    for sl in service.sale_lines:
                        contract_numbers.add(sl.sale.number)
            if contract_numbers:
                result[d.id] = ' / '.join(contract_numbers)
        return result
