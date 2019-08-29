# This file is part of lims_industry module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

try:
    from trytond.modules.lims_industry.tests.test_industry import suite
except ImportError:
    from .test_industry import suite

__all__ = ['suite']
