# This file is part of lims_account_invoice module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

try:
    from trytond.modules.lims_account_invoice.tests.test_lims_account_invoice \
        import suite
except ImportError:
    from .test_lims_account_invoice import suite

__all__ = ['suite']
