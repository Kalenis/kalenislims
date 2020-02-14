# This file is part of lims_analysis_sheet module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

try:
    from trytond.modules.lims_analysis_sheet.tests.test_analysis_sheet \
        import suite
except ImportError:
    from .test_analysis_sheet import suite

__all__ = ['suite']
