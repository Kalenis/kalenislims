# This file is part of lims_price_list module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from .price_list import *
from .party import *
from .product import *
from .invoice import *
from .sale import *


def register():
    Pool.register(
        PriceList,
        PriceListLine,
        Currency,
        UpdatePriceListLinesAsk,
        PrintPriceListStart,
        PartyPriceList,
        Party,
        Product,
        Invoice,
        InvoiceLine,
        InvoiceUpdateLinePriceStart,
        Sale,
        SaleLine,
        module='lims_price_list', type_='model')
    Pool.register(
        UpdatePriceListLines,
        PrintPriceList,
        InvoiceUpdateLinePrice,
        module='lims_price_list', type_='wizard')
    Pool.register(
        PriceListReport,
        module='lims_price_list', type_='report')
