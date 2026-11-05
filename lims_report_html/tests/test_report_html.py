# This file is part of lims_report_html module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import unittest
from datetime import date
from types import SimpleNamespace
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

    @with_transaction()
    def test_generate_report_origin(self):
        "The origin of the wizard prevails over the sample and template ones"
        from trytond.modules.lims.results_report import (
            ResultsReportVersionDetail as LimsDetail)
        Detail = Pool().get('lims.results_report.version.detail')

        def origin(id_):
            return SimpleNamespace(id=id_)

        template = SimpleNamespace(id=1, resultrange_origin=origin(10),
            trend_charts=[], sections=[])
        samples = [{'notebook': 1}]

        def fields(form, sample_origin=None):
            with patch.object(LimsDetail, '_get_fields_from_samples',
                        classmethod(lambda cls, samples, form=None: {})), \
                    patch.object(Detail, '_get_result_template_from_sample',
                        return_value=template), \
                    patch.object(Detail, '_get_resultrange_from_sample',
                        return_value=sample_origin):
                return Detail._get_fields_from_samples(samples, form)

        form = SimpleNamespace(template=template, resultrange_origin=None)
        self.assertEqual(fields(form)['resultrange_origin'], 10)
        self.assertEqual(fields(form, origin(20))['resultrange_origin'], 20)
        form.resultrange_origin = origin(30)
        self.assertEqual(fields(form, origin(20))['resultrange_origin'], 30)
        # other wizards do not have the origin field
        self.assertEqual(fields(SimpleNamespace())['resultrange_origin'], 10)


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
            LimsTestCase))
    return suite
