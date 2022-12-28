# This file is part of lims_sale module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import Pool, PoolMeta


class Party(metaclass=PoolMeta):
    __name__ = 'party.party'

    purchase_order_required = fields.Boolean('Purchase order required')
    internal_code = fields.Char('Internal Code')
    allow_services_without_quotation = fields.Boolean(
        'Allow services without quotation')

    @staticmethod
    def default_allow_services_without_quotation():
        Config = Pool().get('sale.configuration')
        return Config(1).allow_services_without_quotation
