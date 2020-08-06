# This file is part of lims_sale_industry module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta


class Analysis(metaclass=PoolMeta):
    __name__ = 'lims.analysis'

    product_kit = fields.Many2One('product.product', 'Product Kit')
