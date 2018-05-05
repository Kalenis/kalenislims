# This file is part of lims_account_invoice module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from .configuration import *
from .party import *
from .invoice import *
from .stock import *
from .lims import *
from wizard import *


def register():
    Pool.register(
        LimsConfiguration,
        Party,
        Address,
        InvoiceContact,
        Invoice,
        InvoiceLine,
        InventoryLine,
        LimsFractionType,
        LimsEntry,
        LimsFraction,
        LimsService,
        PopulateInvoiceContactsStart,
        module='lims_account_invoice', type_='model')
    Pool.register(
        CreditInvoice,
        LimsManageServices,
        PopulateInvoiceContacts,
        SendOfInvoice,
        module='lims_account_invoice', type_='wizard')
