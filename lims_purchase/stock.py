# -*- coding: utf-8 -*-
# This file is part of lims_purchase module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta

__all__ = ['ProductLocation', 'Move']


class ProductLocation:
    __name__ = 'stock.product.location'
    __metaclass__ = PoolMeta

    department = fields.Many2One('company.department', 'Department')


class Move:
    __name__ = 'stock.move'
    __metaclass__ = PoolMeta

    department = fields.Many2One('company.department', 'Department',
        readonly=True)
