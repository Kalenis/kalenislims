# This file is part of lims_sale module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval

__all__ = ['CreateSampleStart']


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
