# -*- coding: utf-8 -*-
# This file is part of lims_price_list module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.transaction import Transaction
from trytond.pool import Pool, PoolMeta

__all__ = ['Product']


class Product:
    __name__ = 'product.product'
    __metaclass__ = PoolMeta

    @classmethod
    def get_sale_price(cls, products, quantity=0):
        pool = Pool()
        PriceList = pool.get('lims.price_list')
        context = Transaction().context

        prices = super(Product, cls).get_sale_price(products,
            quantity=quantity)
        if context.get('lims_price_list'):
            price_list = PriceList(Transaction().context['lims_price_list'])
            for product in products:
                price = price_list.compute(product, prices[product.id])
                prices[product.id] = price

        return prices
