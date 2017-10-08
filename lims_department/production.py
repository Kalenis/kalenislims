# -*- coding: utf-8 -*-
# This file is part of lims_department module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.transaction import Transaction
from trytond.pool import PoolMeta, Pool

__all__ = ['Production']


class Production:
    __name__ = 'production'
    __metaclass__ = PoolMeta

    def _explode_move_values(self, from_location, to_location, company,
            bom_io, quantity):
        User = Pool().get('res.user')
        product_location = None
        for d in User(Transaction().user).departments:
            if d.default:
                for l in bom_io.product.locations:
                    if l.department == d.department:
                        product_location = l.location
                        break
                break

        if product_location:
            if from_location == self.location:
                to_location = product_location
            else:
                from_location = product_location
        return super(Production, self)._explode_move_values(from_location,
            to_location, company, bom_io, quantity)
