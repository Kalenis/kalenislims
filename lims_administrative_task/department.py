# This file is part of lims_administrative_task module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta


class Department(metaclass=PoolMeta):
    __name__ = 'company.department'

    responsible = fields.Many2One('res.user', 'Responsible User')
