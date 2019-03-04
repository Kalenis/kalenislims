# -*- coding: utf-8 -*-
# This file is part of lims_account_invoice module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta

__all__ = ['Party', 'Address']


class Party(metaclass=PoolMeta):
    __name__ = 'party.party'

    no_send_invoice = fields.Boolean('No send invoice',
        help='If checked, customer invoices will not be set by default '
        'to be mailed to contacts.')
    commercial_item = fields.Many2One('party.category', 'Commercial Item')
    commercial_zone = fields.Many2One('party.category', 'Commercial Zone')

    @staticmethod
    def default_no_send_invoice():
        return False


class Address(metaclass=PoolMeta):
    __name__ = 'party.address'

    @classmethod
    def validate(cls, addresses):
        super(Address, cls).validate(addresses)
        for address in addresses:
            address.check_invoice_type()

    def check_invoice_type(self):
        if self.invoice:
            addresses = self.search([
                ('party', '=', self.party.id),
                ('invoice', '=', True),
                ('id', '!=', self.id),
                ])
            if addresses:
                self.raise_user_error('invoice_address')
