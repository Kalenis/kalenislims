# This file is part of lims_sale module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import configuration
from . import party
from . import sale
from . import sample


def register():
    Pool.register(
        configuration.Configuration,
        configuration.Clause,
        party.Party,
        sale.Sale,
        sale.SaleClause,
        sale.SaleLine,
        sale.SaleLoadServicesStart,
        sample.CreateSampleStart,
        module='lims_sale', type_='model')
    Pool.register(
        sale.SaleLoadServices,
        module='lims_sale', type_='wizard')
