# This file is part of lims_sale_industry module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import formula_mixin
from . import record_log

def register():
    Pool.register(
        formula_mixin.FormulaTemplate,
        formula_mixin.FormulaCategory,
        record_log.RecordLog,
        module='lims_tools', type_='model')
