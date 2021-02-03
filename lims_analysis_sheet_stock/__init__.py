# This file is part of lims_analysis_sheet_stock module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import configuration
from . import stock
from . import sheet


def register():
    Pool.register(
        configuration.Configuration,
        stock.LotAttributeType,
        stock.LotAttribute,
        stock.ProductCategory,
        stock.ProductCategoryLotAttributeType,
        stock.Lot,
        stock.Move,
        sheet.TemplateAnalysisSheet,
        sheet.TemplateAnalysisSheetMaterial,
        sheet.AnalysisSheet,
        sheet.AddMaterialStart,
        sheet.AddMaterialDetailStart,
        sheet.AddMaterialAssignFailed,
        module='lims_analysis_sheet_stock', type_='model')
    Pool.register(
        sheet.AddMaterial,
        module='lims_analysis_sheet_stock', type_='wizard')
