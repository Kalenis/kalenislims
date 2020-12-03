# This file is part of lims_analysis_sheet_stock module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

try:
    from trytond.modules.lims_analysis_sheet_stock.tests.test_analysis_sheet_stock \
        import suite
except ImportError:
    from .test_analysis_sheet_stock import suite

__all__ = ['suite']
