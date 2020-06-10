# This file is part of lims_planning_automatic module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta

__all__ = ['Laboratory']


class Laboratory(metaclass=PoolMeta):
    __name__ = 'lims.laboratory'

    automatic_planning = fields.Boolean('Automatic Planning')
