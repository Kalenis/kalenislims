# This file is part of lims_diagnosis module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelView, ModelSQL, fields
from trytond.pool import PoolMeta


class Diagnostician(ModelSQL, ModelView):
    'Diagnostician'
    __name__ = 'lims.diagnostician'

    party = fields.Many2One('party.party', 'Party', required=True)

    def get_rec_name(self, name):
        if self.party:
            return self.party.name

    @classmethod
    def search_rec_name(cls, name, clause):
        return [('party',) + tuple(clause[1:])]


class Party(metaclass=PoolMeta):
    __name__ = 'party.party'

    diagnostician = fields.Many2One('lims.diagnostician', 'Diagnostician')
