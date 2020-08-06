# -*- coding: utf-8 -*-
# This file is part of lims_account_invoice module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.exceptions import UserError
from trytond.i18n import gettext


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

    commercial_item = fields.Function(fields.Many2One('party.category',
        'Commercial Item'), 'get_commercial_item',
        searcher='search_commercial_item')
    commercial_zone = fields.Function(fields.Many2One('party.category',
        'Commercial Zone'), 'get_commercial_zone',
        searcher='search_commercial_zone')

    def get_commercial_item(self, name=None):
        if self.party and self.party.commercial_item:
            return self.party.commercial_item.id
        return None

    def get_commercial_zone(self, name=None):
        if self.party and self.party.commercial_zone:
            return self.party.commercial_zone.id
        return None

    @classmethod
    def search_commercial_item(cls, name, clause):
        return [('party.' + name,) + tuple(clause[1:])]

    @classmethod
    def search_commercial_zone(cls, name, clause):
        return [('party.' + name,) + tuple(clause[1:])]

    @classmethod
    def validate(cls, addresses):
        super().validate(addresses)
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
                raise UserError(
                    gettext('lims_account_invoice.msg_invoice_address'))
