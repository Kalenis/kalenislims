# This file is part of lims_diagnosis module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

try:
    from trytond.modules.lims_diagnosis.tests.test_diagnosis import suite
except ImportError:
    from .test_diagnosis import suite

__all__ = ['suite']
