# This file is part of lims_sale module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import configuration
from . import party
from . import sale
from . import sample
from . import results_report


def register():
    Pool.register(
        configuration.Configuration,
        configuration.Clause,
        party.Party,
        sale.Sale,
        sale.SaleClause,
        sale.SaleLine,
        sale.SaleLoadServicesStart,
        sale.SaleLoadAnalysisStart,
        sample.CreateSampleStart,
        sample.Sample,
        sample.SampleSaleLine,
        module='lims_sale', type_='model')
    Pool.register(
        sample.Service,
        module='lims_sale', type_='model',
        depends=['lims_account_invoice'])
    Pool.register(
        sale.SaleLoadServices,
        sale.SaleLoadAnalysis,
        sample.CreateSample,
        results_report.OpenSampleSale,
        results_report.OpenResultsDetailSale,
        module='lims_sale', type_='wizard')
