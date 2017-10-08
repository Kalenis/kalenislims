# -*- coding: utf-8 -*-
# This file is part of lims_analytic module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pyson import Eval
from trytond.pool import PoolMeta

__all__ = ['Location']


class Location:
    __name__ = 'stock.location'
    __metaclass__ = PoolMeta

    cost_center = fields.Many2One('analytic_account.account', 'Cost center',
        domain=[('type', '=', 'normal')],
        states={
            'invisible': ~Eval('type').in_(['storage']),
            })
