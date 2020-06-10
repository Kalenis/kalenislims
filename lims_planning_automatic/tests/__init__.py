# This file is part of lims_planning_automatic module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

try:
    from \
        trytond.modules.lims_planning_automatic.tests.test_planning_automatic \
        import suite
except ImportError:
    from .test_planning_automatic import suite

__all__ = ['suite']
