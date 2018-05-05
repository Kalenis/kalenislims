# -*- coding: utf-8 -*-
# This file is part of lims module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelView, ModelSQL, fields

__all__ = ['Department', 'UserDepartment']


class Department(ModelSQL, ModelView):
    'Department'
    __name__ = 'company.department'

    code = fields.Char('Code', required=True)
    name = fields.Char('Name', required=True)
    default_location = fields.Many2One('stock.location', 'Default Location',
        domain=[('type', '=', 'storage')])


class UserDepartment(ModelSQL, ModelView):
    'User Department'
    __name__ = 'user.department'

    user = fields.Many2One('res.user', 'User', required=True)
    department = fields.Many2One('company.department', 'Department',
        required=True)
    default = fields.Boolean('By default')

    @classmethod
    def __setup__(cls):
        super(UserDepartment, cls).__setup__()
        cls._error_messages.update({
            'default_department': ('There is already a default department'
                ' for this user'),
            })

    @staticmethod
    def default_default():
        return False

    @classmethod
    def validate(cls, user_departments):
        super(UserDepartment, cls).validate(user_departments)
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
                self.raise_user_error('default_department')
