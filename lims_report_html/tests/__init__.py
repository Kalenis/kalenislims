# This file is part of lims_report_html module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

try:
    from trytond.modules.lims_report_html.tests.test_report_html import suite
except ImportError:
    from .test_report_html import suite

__all__ = ['suite']
