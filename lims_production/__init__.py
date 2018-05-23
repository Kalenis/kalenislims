# This file is part of lims_production module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import stock
from . import configuration
from . import production


def register():
    Pool.register(
        stock.PurityDegree,
        stock.Brand,
        stock.FamilyEquivalent,
        stock.LotCategory,
        stock.Lot,
        stock.Move,
        stock.ShipmentIn,
        stock.Template,
        stock.Product,
        configuration.ProductionConfiguration,
        configuration.ProductionConfigurationLotSequence,
        configuration.Configuration,
        configuration.ConfigurationSolvents,
        production.BOM,
        production.Production,
        module='lims_production', type_='model')
    Pool.register(
        stock.MoveProductionRelated,
        module='lims_production', type_='wizard')
    Pool.register(
        production.FamilyEquivalentReport,
        module='lims_production', type_='report')
