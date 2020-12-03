# This file is part of lims_analysis_sheet_stock module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta


class Configuration(metaclass=PoolMeta):
    __name__ = 'lims.configuration'

    materials_consumption_location = fields.Many2One('stock.location',
        'Materials Consumption Location',
        domain=[('type', '=', 'storage')])
