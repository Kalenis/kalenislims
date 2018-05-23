# This file is part of lims_analytic module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import lims
from . import stock


def register():
    Pool.register(
        lims.Location,
        stock.Move,
        module='lims_analytic', type_='model')
