# This file is part of lims_report_html module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import unittest
from datetime import date
from unittest.mock import patch

import trytond.tests.test_tryton
from trytond.pool import Pool
from trytond.tests.test_tryton import ModuleTestCase, with_transaction


class LimsTestCase(ModuleTestCase):
    'Test lims_report_html module'
    module = 'lims_report_html'

    @with_transaction()
    def test_print_date_keeps_report_value(self):
        "The generic print date does not override the one of the report"
        ResultReport = Pool().get('lims.result_report', type='report')

        with patch.object(ResultReport, 'get_context',
                return_value={'print_date': date(2026, 10, 10)}):
            rendered = ResultReport.render_lims_template(
                None, '{{ print_date }}', records=[], data={})
            self.assertIn('2026-10-10', rendered)
            self.assertNotIn(':', rendered)
        with patch.object(ResultReport, 'get_context', return_value={}):
            self.assertIn(':', ResultReport.render_lims_template(
                    None, '{{ print_date }}', records=[], data={}))


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
            LimsTestCase))
    return suite
