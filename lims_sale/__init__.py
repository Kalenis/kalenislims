# This file is part of lims_sale module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from .sale import *


def register():
    Pool.register(
        Sale,
        SaleLoadServicesStart,
        module='lims_sale', type_='model')
    Pool.register(
        SaleLoadServices,
        module='lims_sale', type_='wizard')
