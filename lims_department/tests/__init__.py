# This file is part of lims_department module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

try:
    from trytond.modules.lims_department.tests.test_lims_department \
        import suite
except ImportError:
    from .test_lims_department import suite

__all__ = ['suite']
