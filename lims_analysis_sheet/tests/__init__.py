# This file is part of lims_analysis_sheet module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

try:
    from trytond.modules.lims_analysis_sheet.tests.test_analysis_sheet \
        import suite as _analysis_sheet_suite
    from trytond.modules.lims_analysis_sheet.tests.test_interface_integrity \
        import suite as _integrity_suite
except ImportError:
    from .test_analysis_sheet import suite as _analysis_sheet_suite
    from .test_interface_integrity import suite as _integrity_suite


def suite():
    s = _analysis_sheet_suite()
    s.addTests(_integrity_suite())
    return s


__all__ = ['suite']
