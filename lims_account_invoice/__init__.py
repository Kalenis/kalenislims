# This file is part of lims_account_invoice module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import configuration
from . import party
from . import invoice
from . import stock
from . import product
from . import sale
from . import lims


def register():
    Pool.register(
        configuration.Configuration,
        configuration.Cron,
        party.Party,
        party.Address,
        invoice.InvoiceContact,
        invoice.Invoice,
        invoice.InvoiceLine,
        stock.InventoryLine,
        product.Product,
        lims.FractionType,
        lims.Entry,
        lims.Fraction,
        lims.Service,
        lims.ResultsReportVersionDetail,
        invoice.PopulateInvoiceContactsStart,
        invoice.ForceReadyToInvoiceStart,
        invoice.CreateInvoiceStart,
        module='lims_account_invoice', type_='model')
    Pool.register(
        sale.SaleLine,
        module='lims_account_invoice', type_='model',
        depends=['sale'])
    Pool.register(
        lims.ManageServices,
        lims.EditSampleService,
        lims.AddSampleService,
        lims.EditFractionService,
        lims.AddFractionService,
        lims.EntryCancel,
        lims.OpenEntriesReadyForInvoicing,
        lims.OpenLinesPendingInvoicing,
        invoice.PopulateInvoiceContacts,
        invoice.SendOfInvoice,
        invoice.ForceReadyToInvoice,
        invoice.CreateInvoice,
        module='lims_account_invoice', type_='wizard')
    Pool.register(
        lims.EntriesReadyForInvoicingSpreadsheet,
        module='lims_account_invoice', type_='report')
