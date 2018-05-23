# This file is part of lims_sale module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import sale


def register():
    Pool.register(
        sale.Sale,
        sale.SaleLoadServicesStart,
        module='lims_sale', type_='model')
    Pool.register(
        sale.SaleLoadServices,
        module='lims_sale', type_='wizard')
