# This file is part of lims_sale_industry module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import formula_mixin


def register():
    Pool.register(
        formula_mixin.FormulaTemplate,
        module='lims_tools', type_='model')