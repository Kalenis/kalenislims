# This file is part of lims_account_invoice module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import configuration
from . import party
from . import invoice
from . import stock
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
        lims.FractionType,
        lims.Entry,
        lims.Fraction,
        lims.Service,
        invoice.PopulateInvoiceContactsStart,
        module='lims_account_invoice', type_='model')
    Pool.register(
        lims.ManageServices,
        lims.EditSampleService,
        lims.AddSampleService,
        lims.OpenEntriesReadyForInvoicing,
        lims.OpenLinesPendingInvoicing,
        invoice.PopulateInvoiceContacts,
        invoice.SendOfInvoice,
        module='lims_account_invoice', type_='wizard')
    Pool.register(
        lims.EntriesReadyForInvoicingSpreadsheet,
        module='lims_account_invoice', type_='report')
