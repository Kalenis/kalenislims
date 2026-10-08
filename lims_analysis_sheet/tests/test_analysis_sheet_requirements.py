# This file is part of lims_analysis_sheet module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
"""Unit tests for the analysis sheet requirement checks.

These exercise the decision logic only (template lookup order, requirement
resolution, missing template report) with stand-in records, so they need no
database. Model registration and views are covered by the module test case.
"""
import unittest
from types import SimpleNamespace as NS
from unittest import mock

from trytond.exceptions import UserError
from trytond.modules.lims_analysis_sheet import notebook, sheet


def rec(name, id_=1):
    return NS(id=id_, rec_name=name)


def line(analysis='A', method='M', product_type='P', matrix='X',
        exempt=False, required=True, template=None):
    lab = NS(analysis_sheet_required=required)
    return NS(
        analysis=NS(id=1, rec_name=analysis, no_analysis_sheet=exempt),
        method=rec(method), product_type=rec(product_type),
        matrix=rec(matrix), laboratory=lab,
        get_analysis_sheet_template=lambda: template,
        analysis_sheet_required=lambda: (
            notebook.NotebookLine.analysis_sheet_required(NS(
                analysis=NS(no_analysis_sheet=exempt), laboratory=lab))))


class AnalysisSheetRequiredTestCase(unittest.TestCase):

    def required(self, lab_flag, exempt):
        return notebook.NotebookLine.analysis_sheet_required(NS(
            analysis=NS(no_analysis_sheet=exempt),
            laboratory=NS(analysis_sheet_required=lab_flag)))

    def test_follows_laboratory(self):
        self.assertTrue(self.required(True, False))
        self.assertFalse(self.required(False, False))

    def test_exempt_analysis_never_required(self):
        self.assertFalse(self.required(True, True))

    def test_no_laboratory_not_required(self):
        self.assertFalse(notebook.NotebookLine.analysis_sheet_required(NS(
            analysis=NS(no_analysis_sheet=False), laboratory=None)))


@mock.patch.object(notebook, 'gettext',
    side_effect=lambda msg, **kw: '%s %s' % (msg, kw.get('lines', '')))
class CheckTemplatesTestCase(unittest.TestCase):

    def check(self, lines):
        notebook.NotebookLine.check_analysis_sheet_templates.__func__(
            notebook.NotebookLine, lines)

    def test_line_with_template_passes(self, _):
        self.check([line(template=7)])

    def test_missing_template_raises_with_combination(self, _):
        with self.assertRaises(UserError) as cm:
            self.check([line(analysis='Propiconazole', method='LC',
                product_type='Fruta', matrix='Pera')])
        self.assertIn('Propiconazole / LC / Fruta / Pera', str(cm.exception))

    def test_not_required_is_ignored(self, _):
        self.check([line(required=False)])

    def test_exempt_is_ignored(self, _):
        self.check([line(exempt=True)])

    def test_repeated_combinations_listed_once(self, _):
        with self.assertRaises(UserError) as cm:
            self.check([line(), line(), line(analysis='B')])
        text = str(cm.exception)
        self.assertEqual(text.count('A / M / P / X'), 1)
        self.assertIn('B / M / P / X', text)


class TemplateLookupOrderTestCase(unittest.TestCase):
    """The lookup must keep the historical precedence, most specific first."""

    def queries(self, **values):
        executed = []
        cursor = mock.Mock()
        cursor.execute.side_effect = lambda q, p: executed.append((q, p))
        cursor.fetchone.return_value = None
        transaction = mock.Mock()
        transaction.return_value.connection.cursor.return_value = cursor
        pool = mock.Mock()
        pool.return_value.get.return_value = NS(_table='ta')
        with mock.patch.object(sheet, 'Transaction', transaction), \
                mock.patch.object(sheet, 'Pool', pool):
            template = sheet.TemplateAnalysisSheet
            with mock.patch.object(template, '_table', 't', create=True):
                result = template.get_template.__func__(template, 1, **values)
        self.assertIsNone(result)
        return executed

    def test_full_precedence(self):
        executed = self.queries(method_id=2, product_type_id=3, matrix_id=4)
        self.assertEqual([p for _, p in executed], [
            [1, 2, 3, 4], [1, 2, 3], [1, 2, 4], [1, 3, 4],
            [1, 3], [1, 4], [1, 2], [1],
            ])
        self.assertIn('ta.method IS NULL', executed[-1][0])
        self.assertIn('ta.matrix IS NULL', executed[1][0])

    def test_missing_method_skips_method_steps(self):
        executed = self.queries(product_type_id=3, matrix_id=4)
        self.assertEqual([p for _, p in executed], [
            [1, 3, 4], [1, 3], [1, 4], [1],
            ])


def suite():
    loader = unittest.TestLoader()
    s = unittest.TestSuite()
    for case in (AnalysisSheetRequiredTestCase, CheckTemplatesTestCase,
            TemplateLookupOrderTestCase):
        s.addTests(loader.loadTestsFromTestCase(case))
    return s
