# This file is part of lims_industry module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval

__all__ = ['Party', 'Address']


class Party(metaclass=PoolMeta):
    __name__ = 'party.party'

    _states = {'readonly': ~Eval('active', True)}
    _depends = ['active']

    fantasy_name = fields.Char('Fantasy Name',
        states=_states, depends=_depends)
    plants = fields.One2Many('lims.plant', 'party', 'Plants',
        states=_states, depends=_depends)

    del _states, _depends

    @classmethod
    def search_rec_name(cls, name, clause):
        res = super(Party, cls).search_rec_name(name, clause)
        res.append(('fantasy_name',) + tuple(clause[1:]))
        return res


class Address(metaclass=PoolMeta):
    __name__ = 'party.address'

    plant = fields.Many2One('lims.plant', 'Plant',
        ondelete='CASCADE', select=True,
        domain=[('party', '=', Eval('party'))], depends=['party'])
    equipment = fields.Many2One('lims.equipment', 'Equipment',
        select=True,
        domain=[('party', '=', Eval('party'))], depends=['party'])
    phone = fields.Char('Phone')
    purchase_contact = fields.Boolean('Purchase contact')
    technical_contact = fields.Boolean('Technical contact')
    administrative_contact = fields.Boolean('Administrative contact')
    contract_contact = fields.Boolean('Contract contact')
