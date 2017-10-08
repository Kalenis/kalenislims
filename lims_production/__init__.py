# This file is part of lims_production module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from .stock import *
from .configuration import *
from .production import *
from report import *


def register():
    Pool.register(
        PurityDegree,
        Brand,
        FamilyEquivalent,
        LotCategory,
        Lot,
        Move,
        ShipmentIn,
        Template,
        Product,
        ProductionConfiguration,
        ProductionConfigurationLotSequence,
        LimsConfiguration,
        LimsConfigurationSolvents,
        BOM,
        Production,
        module='lims_production', type_='model')
    Pool.register(
        UpdateCostPrice,
        ShipmentInLabels,
        LimsMoveProductionRelated,
        module='lims_production', type_='wizard')
    Pool.register(
        FamilyEquivalentReport,
        module='lims_production', type_='report')
