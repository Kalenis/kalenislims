# This file is part of lims_instrument module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

try:
    from trytond.modules.lims_instrument.tests.test_lims_instrument \
        import suite
except ImportError:
    from .test_lims_instrument import suite

__all__ = ['suite']
