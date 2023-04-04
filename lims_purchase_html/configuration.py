# This file is part of lims_purchase_html module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta


class Configuration(metaclass=PoolMeta):
    __name__ = 'purchase.configuration'

    default_template = fields.Many2One('lims.report.template',
        'Default Template', domain=[
            ('report_name', '=', 'purchase.purchase'),
            ('type', 'in', [None, 'base']),
            ])
