# This file is part of lims_purchase module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

try:
    from trytond.modules.lims_purchase.tests.test_lims_purchase import suite
except ImportError:
    from .test_lims_purchase import suite

__all__ = ['suite']
