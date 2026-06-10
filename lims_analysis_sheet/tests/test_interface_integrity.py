# This file is part of lims_analysis_sheet module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import unittest
from unittest import mock

import trytond.tests.test_tryton
from trytond.pool import Pool
from trytond.tests.test_tryton import ModuleTestCase, with_transaction
from trytond.transaction import Transaction


class InterfaceIntegrityTestCase(ModuleTestCase):
    'Test analysis sheet interface integrity'
    module = 'lims_analysis_sheet'

    _ACTIVE_SHEET_STATES = ['draft', 'active', 'validated']

    def setUp(self):
        # test_tryton sets Pool.test=True; lims.interface.data needs False
        # to resolve dynamic tables against a real database.
        Pool.test = False

    def _find_sheet_with_interface_data(self):
        pool = Pool()
        AnalysisSheet = pool.get('lims.analysis_sheet')
        Data = pool.get('lims.interface.data')

        sheets = AnalysisSheet.search([
            ('state', 'in', self._ACTIVE_SHEET_STATES),
            ], order=[('id', 'DESC')], limit=200)
        for sheet in sheets:
            with Transaction().set_context(
                    lims_interface_table=sheet.compilation.table.id):
                lines = Data.search([
                    ('compilation', '=', sheet.compilation.id),
                    ], limit=1)
                if lines:
                    return sheet
        return None

    def _find_interface_row_with_notebook_line(self):
        pool = Pool()
        AnalysisSheet = pool.get('lims.analysis_sheet')
        Data = pool.get('lims.interface.data')

        sheets = AnalysisSheet.search([
            ('state', 'in', self._ACTIVE_SHEET_STATES),
            ], order=[('id', 'DESC')], limit=200)
        for sheet in sheets:
            with Transaction().set_context(
                    lims_interface_table=sheet.compilation.table.id):
                lines = Data.search([
                    ('compilation', '=', sheet.compilation.id),
                    ('notebook_line', '!=', None),
                    ])
                for line in lines:
                    if line.notebook_line:
                        return sheet, line, line.notebook_line
        return None, None, None

    @with_transaction()
    def test_evaluate_rules_skips_orphan_line(self):
        pool = Pool()
        AnalysisSheet = pool.get('lims.analysis_sheet')
        Data = pool.get('lims.interface.data')
        EvaluateRules = pool.get(
            'lims.analysis_sheet.evaluate_rules', type='wizard')

        sheet = self._find_sheet_with_interface_data()
        if not sheet:
            self.skipTest('No analysis sheet with interface data')

        orphan_id = 999999999
        with Transaction().set_context(
                lims_interface_table=sheet.compilation.table.id,
                lims_interface_compilation=sheet.compilation.id,
                lims_analysis_sheet=sheet.id):
            Data.create([{
                'compilation': sheet.compilation.id,
                'notebook_line': orphan_id,
                }])
            session_id, _, _ = EvaluateRules.create()
            wizard = EvaluateRules(session_id)
            result = wizard.transition_evaluate()
            self.assertEqual(result, 'end')

    @with_transaction()
    def test_delete_notebook_line_cleans_interface(self):
        pool = Pool()
        Data = pool.get('lims.interface.data')
        NotebookLine = pool.get('lims.notebook.line')

        sheet, data_line, nb_line = self._find_interface_row_with_notebook_line()
        if not data_line:
            self.skipTest('No interface row with notebook line')

        data_line_id = data_line.id
        with Transaction().set_context(
                lims_interface_table=sheet.compilation.table.id):
            # Mock parent delete: on real DBs the notebook line often has
            # FKs (planification, etc.). We only need to verify interface
            # cleanup; rollback restores the interface row afterwards.
            with mock.patch(
                    'trytond.modules.lims.notebook.NotebookLine.delete',
                    return_value=None) as parent_delete:
                NotebookLine.delete([nb_line])
                parent_delete.assert_called_once()
            remaining = Data.search([('id', '=', data_line_id)])
            self.assertEqual(remaining, [])

    @with_transaction()
    def test_create_lines_relinks_annulled(self):
        pool = Pool()
        AnalysisSheet = pool.get('lims.analysis_sheet')
        Data = pool.get('lims.interface.data')
        NotebookLine = pool.get('lims.notebook.line')

        sheets = AnalysisSheet.search([
            ('state', 'in', self._ACTIVE_SHEET_STATES),
            ], order=[('id', 'DESC')], limit=200)
        relink_case = None
        for sheet in sheets:
            with Transaction().set_context(
                    lims_interface_table=sheet.compilation.table.id):
                annulled_rows = Data.search([
                    ('compilation', '=', sheet.compilation.id),
                    ('annulled', '=', True),
                    ('notebook_line', '!=', None),
                    ])
                for row in annulled_rows:
                    if not row.notebook_line:
                        continue
                    active_nls = NotebookLine.search([
                        ('notebook', '=', row.notebook_line.notebook.id),
                        ('analysis', '=', row.notebook_line.analysis.id),
                        ('annulled', '=', False),
                        ('end_date', '=', None),
                        ])
                    if active_nls:
                        relink_case = (sheet, row, active_nls[0])
                        break
            if relink_case:
                break
        if not relink_case:
            self.skipTest('No annulled interface row with active notebook line')

        sheet, annulled_row, active_nl = relink_case
        annulled_row_id = annulled_row.id
        with Transaction().set_context(
                lims_interface_table=sheet.compilation.table.id):
            sheet.create_lines([active_nl], update_samples_list=False)
            rows = Data.search([
                ('compilation', '=', sheet.compilation.id),
                ('id', '=', annulled_row_id),
                ])
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].notebook_line.id, active_nl.id)
            self.assertFalse(rows[0].annulled)
            duplicates = Data.search([
                ('compilation', '=', sheet.compilation.id),
                ('notebook_line', '=', active_nl.id),
                ])
            self.assertEqual(len(duplicates), 1)

    @with_transaction()
    def test_sync_after_service_change(self):
        pool = Pool()
        AnalysisSheet = pool.get('lims.analysis_sheet')
        Data = pool.get('lims.interface.data')
        Fraction = pool.get('lims.fraction')

        fractions = Fraction.search([], limit=50)
        target = None
        for fraction in fractions:
            sheets = AnalysisSheet.search([
                ('state', 'in', ['draft', 'active', 'validated']),
                ('samples', 'ilike', '%%%s%%' % fraction.sample.number),
                ])
            if sheets:
                target = fraction
                break
        if not target:
            self.skipTest('No fraction with active analysis sheets')

        AnalysisSheet.sync_fraction_after_service_change(target)

        sheets = AnalysisSheet.search([
            ('state', 'in', ['draft', 'active', 'validated']),
            ('samples', 'ilike', '%%%s%%' % target.sample.number),
            ])
        for sheet in sheets:
            with Transaction().set_context(
                    lims_interface_table=sheet.compilation.table.id):
                lines = Data.search([
                    ('compilation', '=', sheet.compilation.id),
                    ('notebook_line', '!=', None),
                    ])
                orphans = [l for l in lines if not l.notebook_line]
                self.assertEqual(orphans, [])


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
            InterfaceIntegrityTestCase))
    return suite
