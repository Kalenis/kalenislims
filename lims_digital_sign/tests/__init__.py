# This file is part of lims_digital_sign module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

try:
    from trytond.modules.lims_digital_sign.tests.test_lims_digital_sign \
        import suite
except ImportError:
    from .test_lims_digital_sign import suite

__all__ = ['suite']
