# -*- coding: utf-8 -*-
# This file is part of lims module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelView, ModelSQL, fields
from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.i18n import gettext


class Headquarters(ModelSQL, ModelView):
    'Headquarters'
    __name__ = 'company.headquarters'

    name = fields.Char('Name', required=True, translate=True)


class Department(ModelSQL, ModelView):
    'Department'
    __name__ = 'company.department'

    code = fields.Char('Code', required=True)
    name = fields.Char('Name', required=True)
    headquarters = fields.Many2One('company.headquarters', 'Headquarters')
    default_location = fields.Many2One('stock.location', 'Default Location',
        domain=[('type', '=', 'storage')])
    responsible = fields.Many2One('res.user', 'Responsible User')
    laboratory_professional = fields.Function(fields.Many2One(
        'lims.laboratory.professional', 'Laboratory professional'),
        'on_change_with_laboratory_professional')

    @fields.depends('responsible')
    def on_change_with_laboratory_professional(self, name=None):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LaboratoryProfessional = pool.get('lims.laboratory.professional')

        if not self.responsible:
            return None
        cursor.execute('SELECT id '
            'FROM party_party '
            'WHERE is_lab_professional = true '
                'AND lims_user = %s '
            'LIMIT 1', (self.responsible.id,))
        party_id = cursor.fetchone()
        if not party_id:
            return None
        cursor.execute('SELECT id '
            'FROM "' + LaboratoryProfessional._table + '" '
            'WHERE party = %s '
            'LIMIT 1', (party_id[0],))
        lab_professional_id = cursor.fetchone()
        if not lab_professional_id:
            return None
        return lab_professional_id[0]


class UserDepartment(ModelSQL, ModelView):
    'User Department'
    __name__ = 'user.department'

    user = fields.Many2One('res.user', 'User', required=True)
    department = fields.Many2One('company.department', 'Department',
        required=True)
    default = fields.Boolean('By default')

    @staticmethod
    def default_default():
        return False

    @classmethod
    def validate(cls, user_departments):
        super().validate(user_departments)
        for ud in user_departments:
            ud.check_default()

    def check_default(self):
        if self.default:
            user_departments = self.search([
                ('user', '=', self.user.id),
                ('default', '=', True),
                ('id', '!=', self.id),
                ])
            if user_departments:
                raise UserError(gettext('lims.msg_default_department'))
