# This file is part of lims_sale module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import configuration
from . import html_template
from . import party
from . import sale
from . import sample
from . import entry
from . import results_report
from . import invoice


def register():
    Pool.register(
        configuration.Configuration,
        html_template.SaleClauseTemplate,
        html_template.SaleReportTemplate,
        party.Party,
        sale.Sale,
        sale.SaleSection,
        sale.SaleLine,
        sale.SaleLoadServicesStart,
        sale.SaleLoadAnalysisStart,
        sample.CreateSampleStart,
        sample.Sample,
        sample.Service,
        sample.ServiceSaleLine,
        entry.Entry,
        module='lims_sale', type_='model')
    Pool.register(
        sale.Sale2,
        sale.SaleLine2,
        sample.Service2,
        invoice.InvoiceLine,
        module='lims_sale', type_='model',
        depends=['lims_account_invoice'])
    Pool.register(
        sale.SaleLoadServices,
        sale.SaleLoadAnalysis,
        sample.CreateSample,
        results_report.OpenSampleSale,
        results_report.OpenResultsDetailSale,
        results_report.OpenResultsDetailAttachment,
        module='lims_sale', type_='wizard')
    Pool.register(
        sale.SaleReport,
        module='lims_sale', type_='report')
