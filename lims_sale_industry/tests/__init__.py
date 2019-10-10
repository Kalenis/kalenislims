# This file is part of lims_sale_industry module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

try:
    from trytond.modules.lims_sale_industry.tests.test_lims_sale_industry \
        import suite
except ImportError:
    from .test_lims_sale_industry import suite

__all__ = ['suite']
