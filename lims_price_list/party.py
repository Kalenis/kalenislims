# -*- coding: utf-8 -*-
# This file is part of lims_price_list module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields, ModelSQL, ModelView
from trytond.pool import PoolMeta

__all__ = ['PartyPriceList', 'Party']


class PartyPriceList(ModelSQL, ModelView):
    'Party Price List'
    __name__ = 'party.party.lims.price_list'

    party = fields.Many2One('party.party', 'Party', ondelete='CASCADE',
        required=True, select=True)
    price_list = fields.Many2One('lims.price_list', 'Price list',
        ondelete='CASCADE', required=True, select=True)
    default_list = fields.Boolean('Default')

    @staticmethod
    def default_default_list():
        return False


class Party:
    __name__ = 'party.party'
    __metaclass__ = PoolMeta

    lims_price_list = fields.One2Many('party.party.lims.price_list', 'party',
        'Price Lists')

    @classmethod
    def __setup__(cls):
        super(Party, cls).__setup__()
        cls._error_messages.update({
            'invalid_price_lists_default': ('You must set one and only one '
                'price list as default'),
            })

    @classmethod
    def validate(cls, parties):
        super(Party, cls).validate(parties)
        for party in parties:
            party.check_price_lists_default()

    def check_price_lists_default(self):
        if not self.lims_price_list:
            return True
        count = 0
        for pl in self.lims_price_list:
            if pl.default_list:
                count += 1
        if count == 1:
            return True
        else:
            self.raise_user_error('invalid_price_lists_default')
