# -*- coding: utf-8 -*-
# This file is part of lims_project_tas module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelView, ModelSQL, fields, Unique
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, Equal, Bool, Not
from trytond.exceptions import UserError
from trytond.i18n import gettext


class Project(metaclass=PoolMeta):
    __name__ = 'lims.project'

    _states = {'required': Bool(Equal(Eval('type'), 'tas'))}
    _depends = ['type']

    tas_invoice_party = fields.Many2One('party.party', 'Invoice party',
        domain=['OR', ('id', '=', Eval('tas_invoice_party')),
            ('id', 'in', Eval('tas_invoice_party_domain'))],
        states=_states, depends=['type', 'tas_invoice_party_domain'])
    tas_invoice_party_domain = fields.Function(fields.Many2Many('party.party',
        None, None, 'TAS Invoice party domain'),
        'on_change_with_tas_invoice_party_domain')
    tas_laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        states=_states, depends=_depends)
    tas_type = fields.Many2One('lims.tas.type', 'TAS type')
    tas_responsible = fields.Many2One('lims.laboratory.professional',
        'Responsible', domain=[('id', 'in', Eval('tas_responsible_domain'))],
        depends=['tas_responsible_domain'])
    tas_responsible_domain = fields.Function(fields.Many2Many(
        'lims.laboratory.professional', None, None, 'TAS responsible domain'),
        'on_change_with_tas_responsible_domain')
    tas_comments = fields.Text('Comments')

    del _states, _depends

    @classmethod
    def __setup__(cls):
        super().__setup__()
        project_type = ('tas', 'TAS')
        if project_type not in cls.type.selection:
            cls.type.selection.append(project_type)
        cls.client.states = {'required': Bool(Equal(Eval('type'), 'tas'))}
        cls.client.depends = ['type']

    @classmethod
    def view_attributes(cls):
        return super().view_attributes() + [
            ('//group[@id="tas"]', 'states', {
                    'invisible': Not(Bool(Equal(Eval('type'), 'tas'))),
                    }),
            ]

    @fields.depends('client', 'tas_invoice_party')
    def on_change_client(self):
        parties = []
        if self.client:
            parties.append(self.client.id)
        if self.tas_invoice_party:
            parties.append(self.tas_invoice_party.id)

        if self.client and not self.tas_invoice_party:
            tas_invoice_party_domain = \
                self.on_change_with_tas_invoice_party_domain()
            if len(tas_invoice_party_domain) == 1:
                self.tas_invoice_party = tas_invoice_party_domain[0]

    @fields.depends('client')
    def on_change_with_tas_invoice_party_domain(self, name=None):
        Config = Pool().get('lims.configuration')

        config_ = Config(1)
        parties = []
        if self.client:
            parties.append(self.client.id)
            if config_.invoice_party_relation_type:
                parties.extend([r.to.id for r in self.client.relations
                    if r.type == config_.invoice_party_relation_type])
        return parties

    @fields.depends('tas_laboratory')
    def on_change_with_tas_responsible_domain(self, name=None):
        pool = Pool()
        UserLaboratory = pool.get('lims.user-laboratory')
        LaboratoryProfessional = pool.get('lims.laboratory.professional')

        if not self.tas_laboratory:
            return []

        users = UserLaboratory.search([
            ('laboratory', '=', self.tas_laboratory.id),
            ])
        if not users:
            return []
        professionals = LaboratoryProfessional.search([
            ('party.lims_user', 'in', [u.user.id for u in users]),
            ('role', '!=', ''),
            ])
        if not professionals:
            return []
        return [p.id for p in professionals]

    @classmethod
    def create(cls, vlist):
        pool = Pool()
        LabWorkYear = pool.get('lims.lab.workyear')

        workyear_id = LabWorkYear.find()
        workyear = LabWorkYear(workyear_id)
        sequence = workyear.get_sequence('project_tas')
        if not sequence:
            raise UserError(gettext(
                'lims_project_tas.msg_no_project_tas_sequence',
                work_year=workyear.rec_name))

        vlist = [x.copy() for x in vlist]
        for values in vlist:
            if values['type'] == 'tas':
                values['code'] = sequence.get()
        return super().create(vlist)


class Entry(metaclass=PoolMeta):
    __name__ = 'lims.entry'

    @classmethod
    def __setup__(cls):
        super().__setup__()
        project_type = ('tas', 'TAS')
        if project_type not in cls.project_type.selection:
            cls.project_type.selection.append(project_type)


class TasType(ModelSQL, ModelView):
    'TAS Type'
    __name__ = 'lims.tas.type'

    code = fields.Char('Code', required=True)
    description = fields.Char('Description', required=True)

    @classmethod
    def __setup__(cls):
        super().__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code),
                'lims_project_tas.msg_tas_type_code_unique_id'),
            ]

    def get_rec_name(self, name):
        if self.code:
            return self.code + ' - ' + self.description
        else:
            return self.description

    @classmethod
    def search_rec_name(cls, name, clause):
        field = None
        for field in ('code', 'description'):
            records = cls.search([(field,) + tuple(clause[1:])], limit=1)
            if records:
                break
        if records:
            return [(field,) + tuple(clause[1:])]
        return [(cls._rec_name,) + tuple(clause[1:])]
