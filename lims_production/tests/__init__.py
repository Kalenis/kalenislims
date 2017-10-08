# This file is part of lims_production module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

try:
    from trytond.modules.lims_production.tests.test_lims_production \
        import suite
except ImportError:
    from .test_lims_production import suite

__all__ = ['suite']
