# This file is part of lims_sale module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelSQL, fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, Or
from trytond.transaction import Transaction


class CreateSampleStart(metaclass=PoolMeta):
    __name__ = 'lims.create_sample.start'

    sale_lines_filter_product_type_matrix = fields.Boolean(
        'Filter Quotes by Product type and Matrix')
    sale_lines = fields.Many2Many('sale.line', None, None, 'Quotes',
        domain=[('id', 'in', Eval('sale_lines_domain'))],
        states={'readonly': Or(~Eval('product_type'), ~Eval('matrix'))},
        depends=['sale_lines_domain', 'product_type', 'matrix'])
    sale_lines_domain = fields.Function(fields.Many2Many('sale.line',
        None, None, 'Quotes domain'),
        'on_change_with_sale_lines_domain')

    @staticmethod
    def default_sale_lines_filter_product_type_matrix():
        return False

    @fields.depends('party', 'product_type', 'matrix',
        'sale_lines_filter_product_type_matrix')
    def on_change_with_sale_lines_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Date = pool.get('ir.date')
        SaleLine = pool.get('sale.line')
        Analysis = pool.get('lims.analysis')

        if not self.party or not self.product_type or not self.matrix:
            return []

        analysis_domain = super().on_change_with_analysis_domain()
        if not analysis_domain:
            return []
        analysis_ids = ', '.join(str(a) for a in analysis_domain)

        cursor.execute('SELECT DISTINCT(product) '
            'FROM "' + Analysis._table + '" '
            'WHERE id IN (' + analysis_ids + ')')
        res = cursor.fetchall()
        if not res:
            return []
        product_ids = [x[0] for x in res]

        today = Date.today()
        clause = [
            ('sale.party', '=', self.party.id),
            ('sale.expiration_date', '>=', today),
            ('sale.state', 'in', [
                'quotation', 'confirmed', 'processing', 'done',
                ]),
            ('product.id', 'in', product_ids),
            ]
        if self.sale_lines_filter_product_type_matrix:
            clause.append(('product_type', '=', self.product_type.id))
            clause.append(('matrix', '=', self.matrix.id))

        sale_lines = SaleLine.search(clause)
        res = [sl.id for sl in sale_lines if not sl.services_completed]
        return res

    @fields.depends('product_type', 'matrix', 'sale_lines')
    def on_change_with_analysis_domain(self, name=None):
        analysis_domain = super().on_change_with_analysis_domain(name)

        if not self.sale_lines:
            return analysis_domain

        quoted_analysis = []
        for sale_line in self.sale_lines:
            if sale_line.analysis:
                quoted_analysis.append(sale_line.analysis.id)

        return [a for a in analysis_domain if a in quoted_analysis]


class CreateSample(metaclass=PoolMeta):
    __name__ = 'lims.create_sample'

    def _get_samples_defaults(self, entry_id):
        samples_defaults = super()._get_samples_defaults(entry_id)

        if (not hasattr(self.start, 'sale_lines') or
                not hasattr(self.start, 'services')):
            return samples_defaults

        sale_lines = {}
        for line in self.start.sale_lines:
            analysis_id = line.analysis and line.analysis.id
            if not analysis_id:
                continue
            sale_lines[analysis_id] = line.id
        if not sale_lines:
            return samples_defaults

        for sample in samples_defaults:
            if 'fractions' not in sample:
                continue
            for fraction_defaults in sample['fractions']:
                if 'create' not in fraction_defaults[0]:
                    continue
                for fraction in fraction_defaults[1]:
                    if 'services' not in fraction:
                        continue
                    for services_defaults in fraction['services']:
                        if 'create' not in services_defaults[0]:
                            continue
                        for service in services_defaults[1]:
                            analysis_id = service['analysis']
                            if analysis_id in sale_lines:
                                service['sale_lines'] = [('add',
                                    [sale_lines[analysis_id]])]
        return samples_defaults


class Sample(metaclass=PoolMeta):
    __name__ = 'lims.sample'

    sale_lines = fields.Function(fields.Many2Many('sale.line',
        None, None, 'Quotes'), 'get_sale_lines')

    def get_sale_lines(self, name):
        pool = Pool()
        ServiceSaleLine = pool.get('lims.service-sale.line')
        sale_lines = ServiceSaleLine.search([
            ('service.fraction.sample', '=', self.id),
            ])
        return [sl.sale_line.id for sl in sale_lines]


class Service(metaclass=PoolMeta):
    __name__ = 'lims.service'

    sale_lines = fields.Many2Many('lims.service-sale.line',
        'service', 'sale_line', 'Quotes', readonly=True)

    @classmethod
    def copy(cls, services, default=None):
        if default is None:
            default = {}
        current_default = default.copy()
        current_default['sale_lines'] = None
        return super().copy(services, default=current_default)

    @classmethod
    def write(cls, *args):
        super().write(*args)
        actions = iter(args)
        for services, vals in zip(actions, actions):
            if vals.get('annulled'):
                cls.unlink_sale_lines(services)

    @classmethod
    def unlink_sale_lines(cls, services):
        pool = Pool()
        ServiceSaleLine = pool.get('lims.service-sale.line')
        sale_lines = ServiceSaleLine.search([
            ('service', 'in', [s.id for s in services]),
            ])
        if sale_lines:
            ServiceSaleLine.delete(sale_lines)


class Service2(metaclass=PoolMeta):
    __name__ = 'lims.service'

    def get_invoice_line(self):
        invoice_line = super().get_invoice_line()
        if not invoice_line:
            return
        if self.sample.sale_lines:
            for sale_line in self.sample.sale_lines:
                if sale_line.product.id == self.analysis.product.id:
                    invoice_line['unit_price'] = sale_line.unit_price
        return invoice_line


class ServiceSaleLine(ModelSQL):
    'Service - Sale Line'
    __name__ = 'lims.service-sale.line'
    _table = 'lims_service_sale_line'

    service = fields.Many2One('lims.service', 'Service',
        ondelete='CASCADE', select=True, required=True)
    sale_line = fields.Many2One('sale.line', 'Sale Line',
        ondelete='CASCADE', select=True, required=True)
