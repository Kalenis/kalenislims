# This file is part of lims_administrative_task module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

try:
    from trytond.modules.lims_administrative_task.tests.test_task import suite
except ImportError:
    from .test_task import suite

__all__ = ['suite']
