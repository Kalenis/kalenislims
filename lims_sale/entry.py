# This file is part of lims_sale module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateView, StateTransition, Button
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction
from trytond.exceptions import UserWarning
from trytond.i18n import gettext


class Entry(metaclass=PoolMeta):
    __name__ = 'lims.entry'

    allow_services_without_quotation = fields.Function(fields.Boolean(
        'Allow services without quotation'),
        'get_allow_services_without_quotation')

    def get_allow_services_without_quotation(self, name):
        if self.party:
            return self.party.allow_services_without_quotation
        return True


class RelateSaleStart(ModelView):
    'Relate Sale to Entry'
    __name__ = 'lims.entry.relate_sale.start'

    party = fields.Many2One('party.party', 'Party')
    product_types = fields.Many2Many('lims.product.type', None, None,
        'Product types')
    matrices = fields.Many2Many('lims.matrix', None, None,
        'Matrices')
    analyses = fields.Many2Many('lims.analysis', None, None,
        'Analyses')
    sale_lines_filter_product_type_matrix = fields.Boolean(
        'Filter Quotes by Product type and Matrix')
    sale_lines = fields.Many2Many('sale.line', None, None, 'Quotes',
        domain=[('id', 'in', Eval('sale_lines_domain'))])
    sale_lines_domain = fields.Function(fields.Many2Many('sale.line',
        None, None, 'Quotes domain'),
        'on_change_with_sale_lines_domain')

    @staticmethod
    def default_sale_lines_filter_product_type_matrix():
        return False

    @fields.depends('party', 'product_types', 'matrices', 'analyses',
        'sale_lines_filter_product_type_matrix')
    def on_change_with_sale_lines_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Date = pool.get('ir.date')
        SaleLine = pool.get('sale.line')
        Analysis = pool.get('lims.analysis')

        if (not self.party or not self.product_types or not self.matrices or
                not self.analyses):
            return []

        analysis_ids = ', '.join(str(a.id) for a in self.analyses)
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
                'quotation', 'confirmed', 'processing',
                ]),
            ('product.id', 'in', product_ids),
            ]
        if self.sale_lines_filter_product_type_matrix:
            clause.append(('product_type', 'in', self.product_types))
            clause.append(('matrix', 'in', self.matrices))

        sale_lines = SaleLine.search(clause)
        res = [sl.id for sl in sale_lines if not sl.services_completed]
        return res


class RelateSale(Wizard):
    'Relate Sale to Entry'
    __name__ = 'lims.entry.relate_sale'

    start_state = 'check'
    check = StateTransition()
    start = StateView('lims.entry.relate_sale.start',
        'lims_sale.entry_relate_sale_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Relate', 'relate', 'tryton-ok', default=True),
            ])
    relate = StateTransition()

    def transition_check(self):
        entry = self.record
        if entry.state == 'draft':
            return 'start'
        return 'end'

    def default_start(self, fields):
        defaults = {
            'party': None,
            'product_types': [],
            'matrices': [],
            'analyses': [],
            }
        entry = self.record
        defaults['party'] = entry.party.id
        for sample in entry.samples:
            defaults['product_types'].append(sample.product_type.id)
            defaults['matrices'].append(sample.matrix.id)
            for fraction in sample.fractions:
                for service in fraction.services:
                    if service.sale_lines:
                        continue
                    defaults['analyses'].append(service.analysis.id)
        return defaults

    def transition_relate(self):
        pool = Pool()
        Analysis = pool.get('lims.analysis')
        Service = pool.get('lims.service')
        Warning = pool.get('res.user.warning')

        if not hasattr(self.start, 'sale_lines'):
            return 'end'

        sale_lines = {}
        for sl in self.start.sale_lines:
            analysis_id = sl.analysis and sl.analysis.id
            if not analysis_id:
                product_id = sl.product and sl.product.id
                if not product_id:
                    continue
                analysis = Analysis.search([('product', '=', product_id)])
                if not analysis:
                    continue
                analysis_id = analysis[0].id
            sale_lines[analysis_id] = {
                'line': sl.id,
                'available': sl.services_available,
                'qty': 0,
                'completed': False,
                }
        if not sale_lines:
            return 'end'

        entry = self.record
        error_key = 'lims_services_without_quotation@%s' % entry.number
        error_msg = 'lims_sale.msg_services_without_quotation'

        for sample in entry.samples:
            for fraction in sample.fractions:
                for service in fraction.services:
                    if service.sale_lines:
                        continue
                    analysis_id = service.analysis.id
                    if analysis_id not in sale_lines:
                        continue

                    if sale_lines[analysis_id]['completed']:
                        if Warning.check(error_key):
                            raise UserWarning(error_key, gettext(error_msg))
                        continue

                    Service.write([service],
                        {'sale_lines': [('add',
                            [sale_lines[analysis_id]['line']])]})
                    sale_lines[analysis_id]['qty'] += 1

                    if sale_lines[analysis_id]['available'] is None:
                        continue
                    if (sale_lines[analysis_id]['available'] >
                            sale_lines[analysis_id]['qty']):
                        continue
                    if (sale_lines[analysis_id]['available'] ==
                            sale_lines[analysis_id]['qty']):
                        sale_lines[analysis_id]['completed'] = True
                        continue

        return 'end'
