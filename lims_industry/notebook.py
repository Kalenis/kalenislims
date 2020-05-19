# This file is part of lims_industry module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta

__all__ = ['Notebook']


class Notebook(metaclass=PoolMeta):
    __name__ = 'lims.notebook'

    plant = fields.Function(fields.Many2One('lims.plant', 'Plant'),
        'get_sample_field')
    equipment = fields.Function(fields.Many2One('lims.equipment', 'Equipment'),
        'get_sample_field')
    component = fields.Function(fields.Many2One('lims.component', 'Component'),
        'get_sample_field')
