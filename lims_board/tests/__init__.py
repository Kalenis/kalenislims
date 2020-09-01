# This file is part of lims_board module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

try:
    from trytond.modules.lims_board.tests.test_board import suite
except ImportError:
    from .lims_board import suite

__all__ = ['suite']
