# This file is part of lims_purchase module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from .stock import *
from .purchase_request import *
from .purchase import *
from .shipment import *


def register():
    Pool.register(
        ProductLocation,
        Move,
        PurchaseRequest,
        Purchase,
        PurchaseLine,
        ReturnPurchaseStart,
        LimsUserRole,
        ShipmentIn,
        ShipmentOutReturn,
        module='lims_purchase', type_='model')
    Pool.register(
        ReturnPurchase,
        CreatePurchase,
        module='lims_purchase', type_='wizard')
