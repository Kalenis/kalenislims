# -*- coding: utf-8 -*-
# This file is part of lims_price_list module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from decimal import Decimal

from trytond.model import fields, ModelView
from trytond.wizard import Wizard, StateView, StateTransition, Button
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Eval
from trytond.transaction import Transaction

__all__ = ['Invoice', 'InvoiceLine', 'InvoiceUpdateLinePriceStart',
    'InvoiceUpdateLinePrice']


class Invoice:
    __name__ = 'account.invoice'
    __metaclass__ = PoolMeta

    lims_price_list = fields.Many2One('lims.price_list', 'Price List',
        domain=[('id', 'in', Eval('lims_price_list_domain'))],
        states={
            'readonly': ((Eval('state') != 'draft')
                | (Eval('lines', [0]) & Eval('currency'))),
            'invisible': Eval('type').in_(['in'])
            },
        depends=['state', 'lines', 'currency', 'lims_price_list_domain'])
    lims_price_list_domain = fields.Function(fields.Many2Many(
        'lims.price_list', None, None, 'Price List domain'),
        'on_change_with_lims_price_list_domain')
    currency_rate = fields.Numeric('Currency rate', digits=(12, 6),
        states={
            'readonly': Eval('state') != 'draft',
            })

    @classmethod
    def __setup__(cls):
        super(Invoice, cls).__setup__()
        cls.party.states['readonly'] = (cls.party.states['readonly']
            | Eval('lines', [0]))
        cls.lines.states['readonly'] = (cls.lines.states['readonly']
            | ~Eval('party'))
        if 'party' not in cls.lines.depends:
            cls.lines.depends.append('party')

        cls._buttons.update({
            'update_line_price': {
                'invisible': (
                    (Eval('state') != 'draft') |
                    (Eval('type').in_(['in']))
                    )
                },
            })

    @staticmethod
    def default_currency_rate():
        Company = Pool().get('company.company')
        if Transaction().context.get('company'):
            company = Company(Transaction().context['company'])
            return company.currency.rate

    def on_change_party(self):
        super(Invoice, self).on_change_party()
        if self.type == 'in':
            return
        self.lims_price_list = None
        if self.party and self.party.lims_price_list:
            plist = [l.price_list for l in self.party.lims_price_list
                if l.default_list is True]
            if plist:
                self.lims_price_list = plist[0].id

    @fields.depends('party')
    def on_change_with_lims_price_list_domain(self, name=None):
        price_lists = []
        if self.party and self.party.lims_price_list:
            for plist in self.party.lims_price_list:
                price_lists.append(plist.price_list.id)
        return price_lists

    @classmethod
    @ModelView.button_action(
        'lims_price_list.wiz_invoice_update_line_price')
    def update_line_price(cls, invoices):
        pass

    def _credit(self):
        credit = super(Invoice, self)._credit()
        credit.currency_rate = self.currency_rate
        return credit


class InvoiceLine:
    __name__ = 'account.invoice.line'
    __metaclass__ = PoolMeta

    def _get_context_invoice_price(self):
        context = {}
        if getattr(self, 'invoice', None):
            if getattr(self.invoice, 'currency', None):
                context['currency'] = self.invoice.currency.id
            if getattr(self.invoice, 'currency_rate', None):
                context['currency_rate'] = self.invoice.currency_rate
            if getattr(self.invoice, 'party', None):
                context['customer'] = self.invoice.party.id
            if getattr(self.invoice, 'invoice_date', None):
                context['sale_date'] = self.invoice.invoice_date
            if getattr(self.invoice, 'lims_price_list', None):
                context['lims_price_list'] = self.invoice.lims_price_list.id
                context['lims_price_list_ccy'] = (
                    self.invoice.lims_price_list.currency.id)
        if self.unit:
            context['uom'] = self.unit.id
        else:
            context['uom'] = self.product.sale_uom.id
        context['taxes'] = [t.id for t in self.taxes]
        return context

    @fields.depends('type', 'quantity', 'unit_price', 'currency',
        '_parent_invoice.currency', '_parent_invoice.currency_rate',
        '_parent_invoice.lims_price_list')
    def on_change_product(self):
        super(InvoiceLine, self).on_change_product()
        Product = Pool().get('product.product')

        if not self.product:
            return

        if self.invoice and self.invoice.type:
            type_ = self.invoice.type
        else:
            type_ = self.invoice_type
        if type_ == 'out':
            with Transaction().set_context(self._get_context_invoice_price()):
                self.unit_price = Product.get_sale_price([self.product],
                        self.quantity or 0)[self.product.id]
                if self.unit_price:
                    self.unit_price = self.unit_price.quantize(
                        Decimal(1) / 10 ** self.__class__.unit_price.digits[1])

            self.amount = self.on_change_with_amount()


class InvoiceUpdateLinePriceStart(ModelView):
    'Invoice Update Line Price Start'
    __name__ = 'invoice.update_line_price.start'


class InvoiceUpdateLinePrice(Wizard):
    'Invoice Update Line Price'
    __name__ = 'invoice.update_line_price'

    start = StateView('invoice.update_line_price.start',
        'lims_price_list.invoice_update_line_price_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Update', 'update', 'tryton-ok', default=True),
            ])
    update = StateTransition()

    def transition_update(self):
        AccountInvoice = Pool().get('account.invoice')

        invoice = AccountInvoice(Transaction().context['active_id'])
        price_list = invoice.lims_price_list
        for line in invoice.lines:
            if (price_list and price_list.product_defined(line.product)
                    is False):
                continue
            line.on_change_product()
            line.save()

        AccountInvoice.update_taxes([invoice])
        return 'end'
