# This file is part of lims_administrative_task module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Eval
from trytond.exceptions import UserError
from trytond.i18n import gettext

__all__ = ['Party']


class Party(metaclass=PoolMeta):
    __name__ = 'party.party'

    _states = {'readonly': ~Eval('active', True)}
    _depends = ['active']

    complete_file = fields.Boolean('Complete File',
        states=_states, depends=_depends)

    del _states, _depends

    @classmethod
    def create(cls, vlist):
        TaskTemplate = Pool().get('lims.administrative.task.template')
        parties = super(Party, cls).create(vlist)
        records = cls.check_for_tasks(parties)
        TaskTemplate.create_tasks(cls.__name__, records)
        return parties

    @classmethod
    def check_for_tasks(cls, parties):
        AdministrativeTask = Pool().get('lims.administrative.task')
        res = []
        for party in parties:
            if party.complete_file:
                continue
            if AdministrativeTask.search([
                    ('origin', '=', '%s,%s' % (cls.__name__, party.id)),
                    ('state', 'not in', ('done', 'discarded')),
                    ]):
                continue
            res.append(party)
        return res

    @classmethod
    def validate(cls, parties):
        super(Party, cls).validate(parties)
        cls.check_complete_file(parties)

    @classmethod
    def check_complete_file(cls, parties):
        pool = Pool()
        Address = pool.get('party.address')

        for party in parties:
            if not party.complete_file:
                continue

            has_email = Address.search_count([
                ('party', '=', party.id),
                ('email', 'not in', (None, '')),
                ])
            if has_email < 1:
                raise UserError(gettext(
                    'lims_administrative_task.msg_party_email',
                    party=party.rec_name))

            has_phone = Address.search_count([
                ('party', '=', party.id),
                ('phone', 'not in', (None, '')),
                ])
            if has_phone < 1:
                raise UserError(gettext(
                    'lims_administrative_task.msg_party_phone',
                    party=party.rec_name))

            if not party.tax_identifier:
                raise UserError(gettext(
                    'lims_administrative_task.msg_party_tax_identifier',
                    party=party.rec_name))
