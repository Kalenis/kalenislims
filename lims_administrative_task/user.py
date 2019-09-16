# This file is part of lims_administrative_task module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta

__all__ = ['User']


class User(metaclass=PoolMeta):
    __name__ = 'res.user'

    superior = fields.Function(fields.Many2One('res.user',
        'Responsible Superior'), 'get_superior')

    def get_superior(self, name):
        for dep in self.departments:
            if dep.default and dep.department.responsible:
                return dep.department.responsible.id
        return None
