# This file is part of lims_instrument_generic_form module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

try:
    from trytond.modules.lims_instrument_generic_form.tests.test_lims \
        import suite
except ImportError:
    from .test_lims import suite

__all__ = ['suite']
