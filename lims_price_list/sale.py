# -*- coding: utf-8 -*-
# This file is part of lims_price_list module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pyson import Eval, Not, Equal, Or, Bool
from trytond.pool import PoolMeta, Pool
from trytond.transaction import Transaction

__all__ = ['Sale', 'SaleLine']


class Sale:
    __name__ = 'sale.sale'
    __metaclass__ = PoolMeta

    lims_price_list = fields.Many2One('lims.price_list', 'Price List',
        domain=[('id', 'in', Eval('lims_price_list_domain'))],
        states={
            'readonly': Or(Not(Equal(Eval('state'), 'draft')),
                Bool(Eval('lines', [0]))),
            },
        depends=['lims_price_list_domain', 'state'])
    lims_price_list_domain = fields.Function(fields.Many2Many(
        'lims.price_list', None, None, 'Price List domain'),
        'on_change_with_lims_price_list_domain')
    currency_rate = fields.Numeric('Currency rate', digits=(12, 6),
        states={
            'readonly': Eval('state') != 'draft',
            })

    @classmethod
    def __setup__(cls):
        super(Sale, cls).__setup__()
        cls.party.states['readonly'] = (cls.party.states['readonly']
            | Eval('lines', [0]))
        cls.lines.states['readonly'] = (cls.lines.states['readonly']
            | ~Eval('party'))
        if 'party' not in cls.lines.depends:
            cls.lines.depends.append('party')

    @staticmethod
    def default_currency_rate():
        Company = Pool().get('company.company')
        if Transaction().context.get('company'):
            company = Company(Transaction().context['company'])
            return company.currency.rate

    def on_change_party(self):
        super(Sale, self).on_change_party()
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


class SaleLine:
    __name__ = 'sale.line'
    __metaclass__ = PoolMeta

    def _get_context_sale_price(self):
        context = super(SaleLine, self)._get_context_sale_price()
        if self.sale:
            if getattr(self.sale, 'lims_price_list', None):
                context['lims_price_list'] = self.sale.lims_price_list.id
                context['lims_price_list_ccy'] = (
                    self.sale.lims_price_list.currency.id)
            if getattr(self.sale, 'currency_rate', None):
                context['currency_rate'] = self.sale.currency_rate
        return context

    @fields.depends('_parent_sale.lims_price_list',
        '_parent_sale.currency_rate')
    def on_change_product(self):
        super(SaleLine, self).on_change_product()

    @fields.depends('_parent_sale.lims_price_list',
        '_parent_sale.currency_rate')
    def on_change_quantity(self):
        super(SaleLine, self).on_change_quantity()

    @fields.depends('_parent_sale.lims_price_list',
        '_parent_sale.currency_rate')
    def on_change_unit(self):
        super(SaleLine, self).on_change_unit()
