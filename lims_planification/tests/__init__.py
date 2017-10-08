# This file is part of lims_planification module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

try:
    from trytond.modules.lims_planification.tests.test_lims_planification \
        import suite
except ImportError:
    from .test_lims_planification import suite

__all__ = ['suite']
