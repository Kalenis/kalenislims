# This file is part of lims_industry module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelView
from trytond.pool import PoolMeta


class AnalysisSheet(metaclass=PoolMeta):
    __name__ = 'lims.analysis_sheet'

    @classmethod
    @ModelView.button_action(
        'lims_industry.wiz_comercial_product_warn_dangerous')
    def activate(cls, sheets):
        super().activate(sheets)
