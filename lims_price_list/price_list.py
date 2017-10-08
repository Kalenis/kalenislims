# -*- coding: utf-8 -*-
# This file is part of lims_price_list module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from decimal import Decimal
from sql import Table

from trytond.model import ModelView, ModelSQL, fields
from trytond.wizard import Wizard, StateView, StateTransition, StateReport, \
    Button
from trytond.report import Report
from trytond.pyson import Eval
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from trytond.modules.product import price_digits

__all__ = ['PriceList', 'PriceListLine', 'Currency', 'UpdatePriceListLinesAsk',
    'UpdatePriceListLines', 'PrintPriceListStart', 'PrintPriceList',
    'PriceListReport']


class PriceList(ModelSQL, ModelView):
    'Price List'
    __name__ = 'lims.price_list'

    code = fields.Char('Code', required=True)
    name = fields.Char('Name', required=True)
    currency = fields.Many2One('currency.currency', 'Currency')
    calc_method = fields.Selection([
        ('direct', 'Direct'),
        ('based_on', 'Based on...'),
        ], 'Calculation method', required=True)
    base_list = fields.Many2One('lims.price_list', 'Base list',
        domain=[
            ('id', '!=', Eval('id')),
            ('calc_method', '=', 'direct'),
            ('currency', '=', Eval('currency')),
            ],
        states={
            'required': Eval('calc_method') == 'based_on',
            'invisible': Eval('calc_method') == 'direct'},
        depends=['id', 'calc_method', 'currency'])
    percentage = fields.Float('Percentage',
        states={
            'readonly': Eval('calc_method') == 'direct'},
        depends=['calc_method'])
    lines = fields.One2Many('lims.price_list.line', 'price_list', 'Lines')

    @classmethod
    def __setup__(cls):
        super(PriceList, cls).__setup__()
        cls._error_messages.update({
            'no_rate': ('No rate found for currency "%(currency)s" on '
                '"%(date)s"'),
            })

    @classmethod
    def validate(cls, lists):
        super(PriceList, cls).validate(lists)
        cls.check_recursion(lists, parent='base_list', rec_name='name')

    @staticmethod
    def default_calc_method():
        return 'direct'

    @staticmethod
    def default_currency():
        Company = Pool().get('company.company')
        company = Transaction().context.get('company')
        if company:
            return Company(company).currency.id

    @fields.depends('calc_method', 'percentage')
    def on_change_calc_method(self):
        if self.calc_method == 'direct':
            self.percentage = None

    def product_defined(self, product):
        '''
        If the product is defined in the list
        or in the base list, then return True
        '''
        cursor = Transaction().connection.cursor()
        lines = Table('lims_price_list_line')

        cursor.execute(*lines.select(lines.id,
            where=(lines.product == product.id) &
                (lines.price_list == self.id)))
        if cursor.fetchall():
            return True
        if self.calc_method == 'based_on':
            cursor.execute(*lines.select(lines.id,
                where=(lines.product == product.id) &
                    (lines.price_list == self.base_list.id)))
            if cursor.fetchall():
                return True
        return False

    def compute(self, product, unit_price, percentage=None):
        PriceListLine = Pool().get('lims.price_list.line')
        price = None
        # First search the lines for a product coincidence,
        # no matter the calc_method is 'direct' or 'based on'
        cursor = Transaction().connection.cursor()
        lines_table = Table('lims_price_list_line')
        cursor.execute(*lines_table.select(lines_table.id,
            where=(lines_table.product == product.id) &
                (lines_table.price_list == self.id)))
        lines = [line_id for line_id, in cursor.fetchall()]
        lines = PriceListLine.browse(lines)

        for line in lines:
            price = line.get_unit_price(unit_price)
            if price:
                break
        # If no result (price) found, check whether is a 'based on' list
        # A 'based on' list should always be based on a 'direct' list
        if not price and self.calc_method == 'based_on':
            return self.base_list.compute(product, unit_price, self.percentage)
        # If no result, use default unit price
        if not price:
            price = Decimal('0.00')
        if percentage:
            price = price * (1 + (Decimal(percentage) / 100))
        return price


class PriceListLine(ModelSQL, ModelView):
    'Price List Line'
    __name__ = 'lims.price_list.line'

    price_list = fields.Many2One('lims.price_list', 'Price List',
        required=True, ondelete='CASCADE')
    product = fields.Many2One('product.product', 'Product', required=True)
    calc_method = fields.Selection([
        ('direct', 'Direct'),
        ('based_on', 'Based on...'),
        ], 'Calculation method', required=True)
    base_list = fields.Many2One('lims.price_list', 'Base list',
        domain=[
            ('id', '!=', Eval('_parent_price_list', {}).get('id', -1)),
            ('calc_method', '=', 'direct'),
            ('currency', '=', Eval('_parent_price_list', {}).get(
                'currency', -1)),
            ],
        states={
            'required': Eval('calc_method') == 'based_on',
            'invisible': Eval('calc_method') == 'direct'},
        depends=['calc_method'])
    percentage = fields.Float('Percentage',
        states={
            'readonly': Eval('calc_method') == 'direct'},
        depends=['calc_method'])
    price = fields.Numeric('Price', digits=price_digits,
        states={
            'required': Eval('calc_method') == 'direct',
            'readonly': Eval('calc_method') == 'based_on'},
        depends=['calc_method'])

    @staticmethod
    def default_calc_method():
        return 'direct'

    @staticmethod
    def default_price():
        return Decimal('0.0')

    @fields.depends('calc_method', 'percentage', 'price')
    def on_change_calc_method(self):
        if self.calc_method == 'direct':
            self.percentage = None
        if self.calc_method == 'based_on':
            self.price = None

    def get_unit_price(self, unit_price):
        pool = Pool()
        Currency = pool.get('currency.currency')

        currency = None
        plist_currency = None
        currency_rate = None
        if Transaction().context.get('currency'):
            currency = Currency(Transaction().context.get('currency'))
        if Transaction().context.get('lims_price_list_ccy'):
            plist_currency = Currency(
                Transaction().context.get('lims_price_list_ccy'))
        if Transaction().context.get('currency_rate'):
            currency_rate = Transaction().context.get('currency_rate')

        price = None
        # If it's a 'based on' line, use line's percentage
        if self.calc_method == 'based_on':
            return self.base_list.compute(
                self.product, unit_price, self.percentage)
        # Price should be positive
        if self.price > Decimal('0.0'):
            price = self.price
        if not price:
            price = unit_price

        if currency and plist_currency:
            if currency_rate:
                price = self.compute_currency(plist_currency, price,
                    currency, currency_rate, round=False)
            else:
                price = Currency.compute(plist_currency, price,
                    currency, round=False)

        return price

    @classmethod
    def compute_currency(cls, from_currency, amount, to_currency,
            currency_rate, round=True):
        pool = Pool()
        Company = pool.get('company.company')

        if to_currency == from_currency:
            if round:
                return to_currency.round(amount)
            else:
                return amount

        company = Company(Transaction().context['company'])
        if from_currency == company.currency:
            from_currency_rate = currency_rate
            currency_rate = Decimal('1.0')
        else:
            from_currency_rate = Decimal('1.0')

        if round:
            return to_currency.round(
                amount * currency_rate / from_currency_rate)
        else:
            return amount * currency_rate / from_currency_rate


class Currency:
    __name__ = 'currency.currency'
    __metaclass__ = PoolMeta

    @classmethod
    def compute(cls, from_currency, amount, to_currency, round=True):
        pool = Pool()
        PriceListLine = pool.get('lims.price_list.line')

        currency_rate = Transaction().context.get('currency_rate')
        if currency_rate:
            return PriceListLine.compute_currency(from_currency, amount,
                to_currency, currency_rate, round)
        return super(Currency, cls).compute(from_currency, amount,
            to_currency, round)


class UpdatePriceListLinesAsk(ModelView):
    'Update Price List Lines Ask'
    __name__ = 'lims.price_list.update_lines.ask'
    update_percentage = fields.Float('Percentage', required=True)


class UpdatePriceListLines(Wizard):
    'Update Price List Lines'
    __name__ = 'lims.price_list.update_lines'
    start_state = 'ask_percentage'
    ask_percentage = StateView('lims.price_list.update_lines.ask',
        'lims_price_list.update_price_list_lines_ask_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Update', 'update', 'tryton-go-next', default=True),
            ])
    update = StateTransition()

    def transition_update(self):
        PriceList = Pool().get('lims.price_list')
        PriceListLine = Pool().get('lims.price_list.line')

        update_percentage = self.ask_percentage.update_percentage
        price_lists = PriceList.browse(Transaction().context['active_ids'])

        for price_list in price_lists:
            lines_ids = [l.id for l in price_list.lines
                if l.calc_method == 'direct']
            lines = PriceListLine.browse(lines_ids)
            for l in lines:
                l.price = l.price * (1 + Decimal(update_percentage) / 100)
                l.price = l.price.quantize(Decimal(1) / 10 ** price_digits[1])
                l.save()

        return 'end'


class PrintPriceListStart(ModelView):
    'Print Price List start'
    __name__ = 'lims.price_list.print_report.start'

    price_list = fields.Many2One('lims.price_list', 'Price List',
        required=True)
    explode = fields.Boolean('Explode products',
        help='Explode products according to its analysis type')
    analytic_distribution = fields.Many2One(
        'analytic_account.distribution', 'Analytic Distribution')

    @staticmethod
    def default_explode():
        return False


class PrintPriceList(Wizard):
    'Print Price List'
    __name__ = 'lims.price_list.print_report'
    start = StateView('lims.price_list.print_report.start',
        'lims_price_list.print_price_list_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print', 'print_', 'tryton-print', default=True),
            ])
    print_ = StateReport('lims.price_list.report')

    def do_print_(self, action):
        data = {
            'price_list': self.start.price_list.id,
            'explode': self.start.explode,
            'analytic_distribution': self.start.analytic_distribution.id
                if self.start.analytic_distribution else None,
            }
        return action, data

    def transition_print_(self):
        return 'end'


class PriceListReport(Report):
    __name__ = 'lims.price_list.report'

    @classmethod
    def get_context(cls, records, data):
        report_context = super(PriceListReport, cls).get_context(records, data)

        pool = Pool()
        PriceList = pool.get('lims.price_list')
        Analysis = pool.get('lims.analysis')
        AnalyticDistribution = pool.get('analytic_account.distribution')
        KitLine = pool.get('product.kit.line')

        ad = (AnalyticDistribution(data['analytic_distribution']).description
            if data['analytic_distribution'] else None)
        price_list = PriceList(data['price_list'])
        lines = []
        for line in price_list.lines:
            if data['analytic_distribution']:
                if (not line.product.analytic_distribution or
                        data['analytic_distribution'] !=
                        line.product.analytic_distribution.id):
                    continue
            is_kit = line.product.kit
            analysis_explode = []
            if data['explode'] and is_kit is False:
                clause = [('type', 'in', ['set', 'group']),
                    ('product', '=', line.product.id)]
                analysis_ids = [x.id for x in Analysis.search(clause)]
                analysis = Analysis.browse(analysis_ids)
                for a in analysis:
                    L1 = [ia.included_analysis for ia in a.included_analysis]
                    for analysis_L1 in L1:
                        L2 = []
                        if analysis_L1.type in ['set', 'group']:
                            L2 = [ia_L2.included_analysis
                                for ia_L2 in analysis_L1.included_analysis]
                        detail = {}
                        detail['description'] = (analysis_L1.product.rec_name
                            if analysis_L1.product else analysis_L1.rec_name)
                        detail['L2_descriptions'] = []
                        for a in L2:
                            detail['L2_descriptions'].append(a.product.rec_name
                                if a.product else a.rec_name)
                        analysis_explode.append(detail)
            elif data['explode'] and is_kit is True:
                kit_lines = KitLine.search([('parent', '=', line.product.id)])
                for kit_line in kit_lines:
                    detail = {}
                    detail['description'] = kit_line.product.rec_name
                    detail['L2_descriptions'] = []
                    analysis_explode.append(detail)

            record = {}
            eot = ''
            if is_kit:
                if line.product.economic_offer_type == 'normal':
                    eot = 'Normal'
                elif line.product.economic_offer_type == 'based_on_qty':
                    eot = 'Basado en cantidad: %s' % str(
                        line.product.lines_needed_to_match)
                    if line.product.max_lines_needed_to_match:
                        eot += ' hasta %s' % str(
                            line.product.max_lines_needed_to_match)
                eot = ' - Tipo de oferta ' + eot
            record['product'] = line.product.rec_name + eot
            record['price'] = (line.price if line.price else
                line.get_unit_price(Decimal('0.0')))
            record['analysis_explode'] = analysis_explode
            lines.append(record)

        report_context['company'] = report_context['user'].company
        report_context['price_list'] = price_list
        report_context['lines'] = lines
        report_context['analytic_distribution'] = ad
        return report_context
