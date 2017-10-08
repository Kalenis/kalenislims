# This file is part of lims_analytic module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from .lims import *
from .stock import *


def register():
    Pool.register(
        Location,
        Move,
        module='lims_analytic', type_='model')
