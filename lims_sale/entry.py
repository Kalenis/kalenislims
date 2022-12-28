# This file is part of lims_sale module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta


class Entry(metaclass=PoolMeta):
    __name__ = 'lims.entry'

    allow_services_without_quotation = fields.Function(fields.Boolean(
        'Allow services without quotation'),
        'get_allow_services_without_quotation')

    def get_allow_services_without_quotation(self, name):
        if self.party:
            return self.party.allow_services_without_quotation
        return True
