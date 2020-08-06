# This file is part of lims_diagnosis module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta


class Plant(metaclass=PoolMeta):
    __name__ = 'lims.plant'

    diagnostician = fields.Many2One('lims.diagnostician', 'Diagnostician')
