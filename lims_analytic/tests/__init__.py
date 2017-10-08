# This file is part of lims_analytic module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

try:
    from trytond.modules.lims_analytic.tests.test_lims_analytic import suite
except ImportError:
    from .test_lims_analytic import suite

__all__ = ['suite']
