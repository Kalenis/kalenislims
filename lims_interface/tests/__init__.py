# This file is part of lims_interface module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

try:
    from trytond.modules.lims_interface.tests.test_lims_interface \
        import suite
except ImportError:
    from .test_lims_interface import suite

__all__ = ['suite']
