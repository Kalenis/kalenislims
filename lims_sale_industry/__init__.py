# This file is part of lims_sale_industry module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import configuration
from . import sale
from . import sample
from . import analysis
from . import product
from . import task


def register():
    Pool.register(
        configuration.Configuration,
        configuration.ConfigurationSequence,
        sale.Sale,
        sale.SalePlant,
        sale.SaleEquipment,
        sale.SaleComponent,
        sale.SaleContact,
        sale.SaleLine,
        sale.SaleLinePlant,
        sale.SaleLineEquipment,
        sale.SaleLineComponent,
        sale.SaleAddProductKitStart,
        sale.SalePrintLabelStart,
        sale.SaleSearchLabelStart,
        sample.CreateSampleStart,
        analysis.Analysis,
        product.Template,
        task.AdministrativeTaskTemplate,
        task.AdministrativeTask,
        module='lims_sale_industry', type_='model')
    Pool.register(
        sale.SaleAddProductKit,
        sale.SalePrintLabel,
        sale.SaleSearchLabel,
        module='lims_sale_industry', type_='wizard')
    Pool.register(
        sale.SaleLabel,
        sale.SaleLabelShipping,
        sale.SaleLabelReturn,
        module='lims_sale_industry', type_='report')
