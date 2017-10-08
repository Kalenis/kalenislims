# This file is part of lims_price_list module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

try:
    from trytond.modules.lims_price_list.tests.test_lims_price_list \
        import suite
except ImportError:
    from .test_lims_price_list import suite

__all__ = ['suite']
