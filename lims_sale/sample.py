# This file is part of lims_sale module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelSQL, fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval

__all__ = ['CreateSampleStart', 'CreateSample', 'Sample', 'SampleSaleLine',
    'Service']


class CreateSampleStart(metaclass=PoolMeta):
    __name__ = 'lims.create_sample.start'

    sale_lines = fields.Many2Many('sale.line',
        None, None, 'Quotes', depends=['sale_lines_domain'],
        domain=[('id', 'in', Eval('sale_lines_domain'))])
    sale_lines_domain = fields.Function(fields.Many2Many('sale.line',
        None, None, 'Quotes domain'),
        'on_change_with_sale_lines_domain')

    @fields.depends('party', 'product_type', 'matrix')
    def on_change_with_sale_lines_domain(self, name=None):
        pool = Pool()
        Date = pool.get('ir.date')
        SaleLine = pool.get('sale.line')

        today = Date.today()
        clause = [
            ('sale.party', '=', self.party.id),
            ('sale.expiration_date', '>=', today),
            ('sale.state', 'in', [
                'quotation', 'confirmed', 'processing', 'done',
                ]),
            ]
        if self.product_type:
            clause.append(('product_type', '=', self.product_type.id))
        if self.matrix:
            clause.append(('matrix', '=', self.matrix.id))
        res = SaleLine.search(clause)
        return [x.id for x in res]

    @fields.depends('product_type', 'matrix', 'sale_lines')
    def on_change_with_analysis_domain(self, name=None):
        analysis_domain = super(CreateSampleStart,
            self).on_change_with_analysis_domain(name)

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
        samples_defaults = super(CreateSample,
            self)._get_samples_defaults(entry_id)

        analysis = [s.analysis.id for s in self.start.services]
        sale_lines = []
        for line in self.start.sale_lines:
            if line.analysis and line.analysis.id in analysis:
                sale_lines.append(line.id)

        if sale_lines:
            for sample in samples_defaults:
                sample['sale_lines'] = [('add', sale_lines)]
        return samples_defaults


class Sample(metaclass=PoolMeta):
    __name__ = 'lims.sample'

    sale_lines = fields.Many2Many('lims.sample-sale.line',
        'sample', 'sale_line', 'Quotes', readonly=True)


class SampleSaleLine(ModelSQL):
    'Sample - Sale Line'
    __name__ = 'lims.sample-sale.line'
    _table = 'lims_sample_sale_line'

    sample = fields.Many2One('lims.sample', 'Sample',
        ondelete='CASCADE', select=True, required=True)
    sale_line = fields.Many2One('sale.line', 'Sale Line',
        ondelete='CASCADE', select=True, required=True)


class Service(metaclass=PoolMeta):
    __name__ = 'lims.service'

    def get_invoice_line(self, invoice_type):
        invoice_line = super(Service, self).get_invoice_line(invoice_type)
        if self.sample.sale_lines:
            for sale_line in self.sample.sale_lines:
                if sale_line.product.id == self.analysis.product.id:
                    invoice_line['unit_price'] = sale_line.unit_price
        return invoice_line
