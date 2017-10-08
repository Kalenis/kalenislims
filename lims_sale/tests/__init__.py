# This file is part of lims_sale module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

try:
    from trytond.modules.lims_sale.tests.test_lims_sale import suite
except ImportError:
    from .test_lims_sale import suite

__all__ = ['suite']
