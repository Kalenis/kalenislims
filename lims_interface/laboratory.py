# This file is part of lims_interface module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta


class Laboratory(metaclass=PoolMeta):
    __name__ = 'lims.laboratory'

    automatic_accept_result = fields.Boolean('Automatic Accept Result')
