# This file is part of lims_sale_industry module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction


class CreateSampleStart(metaclass=PoolMeta):
    __name__ = 'lims.create_sample.start'

    @fields.depends('party', 'product_type', 'matrix',
        'sale_lines_filter_product_type_matrix',
        'label', 'component', 'equipment')
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

        if self.label:
            try:
                label = int(self.label)
                clause.extend([
                    ('sale.label_from', '<=', label),
                    ('sale.label_to', '>=', label),
                    ])
                sale_lines = SaleLine.search(clause)
                res = [sl.id for sl in sale_lines if not sl.services_completed]
                return res
            except ValueError:
                pass

        if self.component:
            clause.append(['OR',
                ('components', '=', self.component.id),
                ('sale.components', '=', self.component.id),
                ])
            sale_lines = SaleLine.search(clause)
            if sale_lines:
                res = [sl.id for sl in sale_lines if not sl.services_completed]
                return res

        if self.equipment:
            clause.append(['OR',
                ('equipments', '=', self.equipment.id),
                ('sale.equipments', '=', self.equipment.id),
                ])
            sale_lines = SaleLine.search(clause)
            if sale_lines:
                res = [sl.id for sl in sale_lines if not sl.services_completed]
                return res

        if self.sale_lines_filter_product_type_matrix:
            clause.append(('product_type', '=', self.product_type.id))
            clause.append(('matrix', '=', self.matrix.id))

        sale_lines = SaleLine.search(clause)
        res = [sl.id for sl in sale_lines if not sl.services_completed]
        return res

    @fields.depends('party', 'product_type', 'matrix',
        'sale_lines', 'component', 'comercial_product')
    def on_change_with_analysis_domain(self, name=None):
        return super().on_change_with_analysis_domain(name)
