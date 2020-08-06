# This file is part of lims_diagnosis module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta


class Analysis(metaclass=PoolMeta):
    __name__ = 'lims.analysis'

    diagnostician = fields.Many2One('lims.diagnostician', 'Diagnostician')
    not_block_diagnosis = fields.Boolean('Does not block diagnosis',
        help="This analysis is not necessary to begin diagnosing the sample")


class ProductType(metaclass=PoolMeta):
    __name__ = 'lims.product.type'

    diagnostician = fields.Many2One('lims.diagnostician', 'Diagnostician')
