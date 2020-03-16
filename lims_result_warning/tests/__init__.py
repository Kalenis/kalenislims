# This file is part of lims_result_warning module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

try:
    from \
        trytond.modules.lims_result_warning.tests.test_result_warning \
        import suite
except ImportError:
    from .test_result_warning import suite

__all__ = ['suite']
