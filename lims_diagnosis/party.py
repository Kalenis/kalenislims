# This file is part of lims_diagnosis module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelView, ModelSQL, fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction


class Diagnostician(ModelSQL, ModelView):
    'Diagnostician'
    __name__ = 'lims.diagnostician'

    party = fields.Many2One('party.party', 'Party', required=True)
    signature = fields.Binary('Signature')

    def get_rec_name(self, name):
        if self.party:
            return self.party.name

    @classmethod
    def search_rec_name(cls, name, clause):
        return [('party',) + tuple(clause[1:])]

    @classmethod
    def get_diagnostician(cls):
        cursor = Transaction().connection.cursor()
        login_user_id = Transaction().user
        cursor.execute('SELECT id '
            'FROM party_party '
            'WHERE lims_user = %s '
            'LIMIT 1', (login_user_id,))
        party_id = cursor.fetchone()
        if not party_id:
            return None
        cursor.execute('SELECT id '
            'FROM "' + cls._table + '" '
            'WHERE party = %s '
            'LIMIT 1', (party_id[0],))
        diagnostician_id = cursor.fetchone()
        if (diagnostician_id):
            return diagnostician_id[0]
        return None


class Party(metaclass=PoolMeta):
    __name__ = 'party.party'

    diagnostician = fields.Many2One('lims.diagnostician', 'Diagnostician')
    diagnosis_template = fields.Many2One('lims.diagnosis.template',
        'Diagnosis Template', domain=['OR', ('active', '=', True),
            ('id', '=', Eval('diagnosis_template'))])
