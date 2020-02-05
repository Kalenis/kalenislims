# This file is part of lims_sale_industry module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import Pool, PoolMeta

__all__ = ['CreateSampleStart']


class CreateSampleStart(metaclass=PoolMeta):
    __name__ = 'lims.create_sample.start'

    @fields.depends('party', 'label', 'component', 'equipment',
        'product_type', 'matrix')
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

        if self.label:
            try:
                label = int(self.label)
                clause.extend([
                    ('sale.label_from', '<=', label),
                    ('sale.label_to', '>=', label),
                    ])
                res = SaleLine.search(clause)
                return [x.id for x in res]
            except ValueError:
                pass

        if self.component:
            clause.append(['OR',
                ('components', '=', self.component.id),
                ('sale.components', '=', self.component.id),
                ])
            res = SaleLine.search(clause)
            if res:
                return [x.id for x in res]

        if self.equipment:
            clause.append(['OR',
                ('equipments', '=', self.equipment.id),
                ('sale.equipments', '=', self.equipment.id),
                ])
            res = SaleLine.search(clause)
            if res:
                return [x.id for x in res]

        if self.product_type:
            clause.append(('product_type', '=', self.product_type.id))
        if self.matrix:
            clause.append(('matrix', '=', self.matrix.id))
        res = SaleLine.search(clause)
        return [x.id for x in res]
