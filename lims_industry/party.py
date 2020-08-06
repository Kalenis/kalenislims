# This file is part of lims_industry module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.exceptions import UserError
from trytond.i18n import gettext
from trytond.transaction import Transaction


class Party(metaclass=PoolMeta):
    __name__ = 'party.party'

    _states = {'readonly': ~Eval('active', True)}
    _depends = ['active']

    fantasy_name = fields.Char('Fantasy Name',
        states=_states, depends=_depends)
    plants = fields.One2Many('lims.plant', 'party', 'Plants',
        states=_states, depends=_depends)
    complete_file = fields.Boolean('Complete File',
        states=_states, depends=_depends)

    del _states, _depends

    @classmethod
    def create(cls, vlist):
        TaskTemplate = Pool().get('lims.administrative.task.template')
        parties = super().create(vlist)
        TaskTemplate.create_tasks('party_incomplete_file',
            cls._for_task_incomplete_file(parties))
        return parties

    @classmethod
    def _for_task_incomplete_file(cls, parties):
        AdministrativeTask = Pool().get('lims.administrative.task')
        res = []
        for party in parties:
            if party.complete_file:
                continue
            if AdministrativeTask.search([
                    ('type', '=', 'party_incomplete_file'),
                    ('origin', '=', '%s,%s' % (cls.__name__, party.id)),
                    ('state', 'not in', ('done', 'discarded')),
                    ]):
                continue
            res.append(party)
        return res

    @classmethod
    def search_rec_name(cls, name, clause):
        res = super().search_rec_name(name, clause)
        res.append(('fantasy_name',) + tuple(clause[1:]))
        return res

    @classmethod
    def validate(cls, parties):
        super().validate(parties)
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
                    'lims_industry.msg_party_no_email',
                    party=party.rec_name))

            has_phone = Address.search_count([
                ('party', '=', party.id),
                ('phone', 'not in', (None, '')),
                ])
            if has_phone < 1:
                raise UserError(gettext(
                    'lims_industry.msg_party_no_phone',
                    party=party.rec_name))

            if not party.tax_identifier:
                raise UserError(gettext(
                    'lims_industry.msg_party_no_tax_identifier',
                    party=party.rec_name))


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

    @staticmethod
    def default_country():
        Company = Pool().get('company.company')
        company_id = Transaction().context.get('company')
        if company_id:
            address = Company(company_id).party.address_get()
            if address and address.country:
                return address.country.id

    @staticmethod
    def default_plant():
        return Transaction().context.get('plant', None)
