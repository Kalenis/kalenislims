# This file is part of lims module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import unittest
import doctest
from datetime import date
from unittest.mock import patch

import trytond.tests.test_tryton
from trytond.pool import Pool
from trytond.tests.test_tryton import ModuleTestCase
from trytond.tests.test_tryton import doctest_teardown
from trytond.tests.test_tryton import doctest_checker
from trytond.tests.test_tryton import with_transaction
from trytond.transaction import Transaction


class LimsTestCase(ModuleTestCase):
    'Test lims module'
    module = 'lims'

    def _create_sequences(self):
        pool = Pool()
        Sequence = pool.get('ir.sequence')
        ModelData = pool.get('ir.model.data')
        company = Transaction().context.get('company')

        def make(name, xml_id):
            return Sequence.create([{
                'name': '%s Sequence Test' % name,
                'sequence_type': ModelData.get_id('lims', xml_id),
                'company': company,
                }])[0]

        return {
            'entry': make('Entry', 'seq_type_entry'),
            'sample': make('Sample', 'seq_type_sample'),
            'service': make('Service', 'seq_type_service'),
            'results_report': make('Results Report', 'seq_type_results_report'),
            }

    def _create_workyear(self, code, start, end, sequences):
        pool = Pool()
        LabWorkYear = pool.get('lims.lab.workyear')
        workyear, = LabWorkYear.create([{
            'code': code,
            'start_date': start,
            'end_date': end,
            'entry_sequence': sequences['entry'].id,
            'sample_sequence': sequences['sample'].id,
            'service_sequence': sequences['service'].id,
            'results_report_sequence': sequences['results_report'].id,
            }])
        return workyear

    @with_transaction()
    def test_get_target_date_cross_month_holidays(self):
        "Holidays from next month's workyear are applied"
        pool = Pool()
        Holiday = pool.get('lims.lab.workyear.holiday')

        sequences = self._create_sequences()
        june = self._create_workyear(
            'Prod 2026-06', date(2026, 6, 1), date(2026, 6, 30), sequences)
        july = self._create_workyear(
            'Prod 2026-07', date(2026, 7, 1), date(2026, 7, 31), sequences)

        Holiday.create([
            {'workyear': june.id, 'name': 'June 15', 'date': date(2026, 6, 15)},
            {'workyear': june.id, 'name': 'June 20', 'date': date(2026, 6, 20)},
            {'workyear': july.id, 'name': 'July 9', 'date': date(2026, 7, 9)},
            {'workyear': july.id, 'name': 'July 10', 'date': date(2026, 7, 10)},
            ])

        # Case 26062439: start 24/06, 11 workdays → must skip 09/07 and 10/07
        result = june.get_target_date(date(2026, 6, 24), 11)
        self.assertEqual(result, date(2026, 7, 13))

    @with_transaction()
    def test_get_target_date_same_month_holiday(self):
        "Holidays inside the start workyear still apply"
        pool = Pool()
        Holiday = pool.get('lims.lab.workyear.holiday')

        sequences = self._create_sequences()
        june = self._create_workyear(
            'Prod 2026-06b', date(2026, 6, 1), date(2026, 6, 30), sequences)
        Holiday.create([{
            'workyear': june.id,
            'name': 'June 15',
            'date': date(2026, 6, 15),
            }])

        result = june.get_target_date(date(2026, 6, 10), 5)
        self.assertEqual(result, date(2026, 6, 18))

    @with_transaction()
    def test_get_target_date_cross_year_holiday(self):
        "Holidays in next year's workyear are applied"
        pool = Pool()
        Holiday = pool.get('lims.lab.workyear.holiday')

        sequences = self._create_sequences()
        dec = self._create_workyear(
            'Prod 2026-12', date(2026, 12, 1), date(2026, 12, 31), sequences)
        jan = self._create_workyear(
            'Prod 2027-01', date(2027, 1, 1), date(2027, 1, 31), sequences)
        Holiday.create([{
            'workyear': jan.id,
            'name': 'New Year',
            'date': date(2027, 1, 1),
            }])

        result = dec.get_target_date(date(2026, 12, 28), 5)
        self.assertEqual(result, date(2027, 1, 5))

    @with_transaction()
    def test_report_kind_complete_and_incomplete(self):
        "Report type follows notebook completeness, not a batch flag"
        GenerateReport = Pool().get('lims.notebook.generate_results_report')

        class Notebook(object):
            def __init__(self, state):
                self.state = state

        self.assertEqual(
            GenerateReport._report_kind(Notebook('complete')),
            ('final', 'complete'))
        self.assertEqual(
            GenerateReport._report_kind(Notebook('in_progress')),
            ('preliminary', 'in_progress'))
        self.assertEqual(
            GenerateReport._report_kind(Notebook(None)),
            ('preliminary', 'in_progress'))

    @with_transaction()
    def test_new_version_type_on_released_report(self):
        "Corrective when an analysis is reported again, else complementary"
        GenerateReport = Pool().get('lims.notebook.generate_results_report')

        self.assertEqual(
            GenerateReport._new_version_type([1, 2], [2]), 'corrective')
        self.assertEqual(
            GenerateReport._new_version_type([1, 2], [3]), 'complementary')
        self.assertEqual(
            GenerateReport._new_version_type([1, 2], [2, 3]), 'corrective')
        self.assertEqual(
            GenerateReport._new_version_type([], [3]), 'complementary')

    @with_transaction()
    def test_results_estimated_date_skips_weekends(self):
        "Estimated results date counts workdays, not calendar days"
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')

        sequences = self._create_sequences()
        self._create_workyear(
            'Test 2099-06', date(2099, 6, 1), date(2099, 6, 30), sequences)

        # Wed 10/06 + 5 workdays -> Wed 17/06 (skips Sat 13 and Sun 14),
        # not Mon 15/06 as plain calendar days would give
        result = NotebookLine._get_results_estimated_date(date(2099, 6, 10), 5)
        self.assertEqual(result, date(2099, 6, 17))

    @with_transaction()
    def test_results_estimated_date_skips_holidays(self):
        "Estimated results date skips holidays of the work year"
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        Holiday = pool.get('lims.lab.workyear.holiday')

        sequences = self._create_sequences()
        workyear = self._create_workyear(
            'Test 2099-06b', date(2099, 6, 1), date(2099, 6, 30), sequences)
        Holiday.create([{
            'workyear': workyear.id,
            'name': 'June 15',
            'date': date(2099, 6, 15),
            }])

        # Same case as above, but 15/06 is now a holiday -> one day later
        result = NotebookLine._get_results_estimated_date(date(2099, 6, 10), 5)
        self.assertEqual(result, date(2099, 6, 18))

    @with_transaction()
    def test_results_estimated_date_without_workyear(self):
        "Without a work year for the date, calendar days are used"
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')

        sequences = self._create_sequences()
        self._create_workyear(
            'Test 2099-06c', date(2099, 6, 1), date(2099, 6, 30), sequences)

        # 10/01/2099 is not covered by any work year: no error, calendar days
        result = NotebookLine._get_results_estimated_date(date(2099, 1, 10), 5)
        self.assertEqual(result, date(2099, 1, 15))

    @with_transaction()
    def test_labels_list_skips_blank_lines(self):
        "Blank lines in the labels box do not create extra samples"
        pool = Pool()
        for name in ('lims.sample.duplicate', 'lims.entry.duplicate_sample',
                'lims.create_sample'):
            get_labels = pool.get(name, type='wizard')._get_labels_list
            # a trailing newline used to add one sample with an empty label
            self.assertEqual(get_labels(None, 'A\n'), ['A'])
            self.assertEqual(get_labels(None, 'A\nB\n'), ['A', 'B'])
            self.assertEqual(get_labels(None, 'A\r\nB\r\n'), ['A', 'B'])
            self.assertEqual(get_labels(None, 'A\n\nB'), ['A', 'B'])
            # nothing usable means one copy without label, as before
            self.assertEqual(get_labels(None, '  \n '), [None])
            self.assertEqual(get_labels(None, ''), [None])
            self.assertEqual(get_labels(None, None), [None])

    @with_transaction()
    def test_generate_report_skips_inactive_transcription(self):
        "Releasing does not fail when the transcription report is disabled"
        pool = Pool()
        ActionReport = pool.get('ir.action.report')
        Detail = pool.get('lims.results_report.version.detail')
        ResultReport = pool.get('lims.result_report', type='report')
        Transcription = pool.get(
            'lims.result_report.transcription', type='report')

        action, = ActionReport.search([
                ('report_name', '=', Transcription.__name__),
                ])
        detail = Detail()
        with patch.object(ResultReport, 'execute') as report, \
                patch.object(Transcription, 'execute') as transcription:
            detail.generate_report()
            self.assertEqual(report.call_count, 1)
            self.assertEqual(transcription.call_count, 1)

            action.active = False
            action.save()
            detail.generate_report()
            self.assertEqual(report.call_count, 2)
            self.assertEqual(transcription.call_count, 1)

    @with_transaction()
    def test_included_analysis_write_updates_calculated_typifications(self):
        "Changing an included analysis or its method recalculates typifications"
        from trytond.model import ModelSQL
        Included = Pool().get('lims.analysis.included')

        first, second = Included(1), Included(2)
        with patch.object(ModelSQL, 'write'), \
                patch.object(Included,
                    'create_typification_calculated') as update:
            Included.write([first], {'method': 5}, [second], {'laboratory': 3})
            update.assert_called_once_with([first])

            update.reset_mock()
            Included.write([first, second], {'laboratory': 3})
            update.assert_not_called()

            Included.write([first, second], {'included_analysis': 7})
            update.assert_called_once_with([first, second])

    @with_transaction()
    def test_create_sample_party_changed(self):
        "Creating samples fails if the entry party changed meanwhile"
        from types import SimpleNamespace
        from trytond.exceptions import UserError
        CreateSample = Pool().get('lims.create_sample', type='wizard')

        entry = SimpleNamespace(multi_party=False, rec_name='2026/1',
            party=SimpleNamespace(id=1))
        CreateSample.check_party(entry, SimpleNamespace(id=1, rec_name='A'))
        CreateSample.check_party(entry, None)
        with self.assertRaises(UserError):
            CreateSample.check_party(entry,
                SimpleNamespace(id=2, rec_name='B'))

    @with_transaction()
    def test_create_sample_party_changed_multi_party(self):
        "In multi party entries the related parties of the invoice party are valid"
        from types import SimpleNamespace
        from trytond.exceptions import UserError
        pool = Pool()
        CreateSample = pool.get('lims.create_sample', type='wizard')
        Party = pool.get('party.party')
        RelationType = pool.get('party.relation.type')
        Relation = pool.get('party.relation')
        Configuration = pool.get('lims.configuration')

        invoice, related, other = Party.create([
                {'name': 'Invoice'}, {'name': 'Related'}, {'name': 'Other'}])
        relation_type, = RelationType.create([{'name': 'Invoice party'}])
        Relation.create([{
                    'from_': related.id,
                    'to': invoice.id,
                    'type': relation_type.id,
                    }])

        entry = SimpleNamespace(multi_party=True, rec_name='2026/1',
            party=None, invoice_party=invoice)
        with patch.object(Configuration, 'invoice_party_relation_type',
                relation_type):
            self.assertEqual(sorted(CreateSample.get_party_domain(entry)),
                sorted([invoice.id, related.id]))
            CreateSample.check_party(entry, invoice)
            CreateSample.check_party(entry, related)
            with self.assertRaises(UserError):
                CreateSample.check_party(entry, other)

    @with_transaction()
    def test_method_waiting_updates_lines_with_query(self):
        "Changing the method waiting does not write the lines through the ORM"
        from types import SimpleNamespace
        from trytond.modules.lims import laboratory
        pool = Pool()
        LabMethod = pool.get('lims.lab.method')
        NotebookLine = pool.get('lims.notebook.line')

        lines = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
        method = SimpleNamespace(id=10, results_waiting=[],
            results_estimated_waiting=9)
        with patch.object(NotebookLine, 'search', return_value=lines), \
                patch.object(NotebookLine, 'write') as write, \
                patch.object(laboratory,
                    'set_notebook_lines_estimated_waiting') as update:
            LabMethod.update_laboratory_notebook([method], 9)
        update.assert_called_once_with(lines, 9)
        write.assert_not_called()

        laboratory.set_notebook_lines_estimated_waiting(
            [SimpleNamespace(id=-1)], 9)

    @with_transaction()
    def test_copy_lines_setup_values(self):
        "Copy the setup of the source line without touching other fields"
        from types import SimpleNamespace
        CopyLinesSetup = Pool().get('lims.notebook.copy_lines_setup',
            type='wizard')

        unit_mg, unit_ug = SimpleNamespace(id=1), SimpleNamespace(id=2)
        source = SimpleNamespace(initial_unit=unit_ug, detection_limit='0.5',
            quantification_limit='1', decimals=3, result='10')
        line = SimpleNamespace(initial_unit=unit_mg, detection_limit=None,
            quantification_limit='2', decimals=3, result='99')
        names = ['initial_unit', 'detection_limit', 'quantification_limit',
            'decimals']

        self.assertEqual(
            CopyLinesSetup.get_setup_values(source, line, names),
            {'initial_unit': 2, 'detection_limit': '0.5',
                'quantification_limit': '1'})
        self.assertEqual(
            CopyLinesSetup.get_setup_values(source, line, names,
                only_empty=True),
            {'detection_limit': '0.5'})
        self.assertEqual(
            CopyLinesSetup.get_setup_values(source, line, ['decimals']), {})


    def test_limits_modifier(self):
        "The limits validation gives nd below the DL and low up to the QL"
        from trytond.modules.lims.notebook import get_limits_modifier

        self.assertEqual(get_limits_modifier(0.2, 0.5, 1), 'nd')
        self.assertEqual(get_limits_modifier(0.5, 0.5, 1), 'low')
        self.assertEqual(get_limits_modifier(0.7, 0.5, 1), 'low')
        self.assertEqual(get_limits_modifier(1, 0.5, 1), None)
        self.assertEqual(get_limits_modifier(390, 0.5, 1), None)

    def test_limits_revalidation_field(self):
        "Only modifiers set by the limits validation are evaluated again"
        from types import SimpleNamespace
        from trytond.modules.lims.notebook import (
            get_limits_revalidation_field)

        nd, low, ni = (SimpleNamespace(code=c) for c in ('nd', 'low', 'ni'))

        def line(**kwargs):
            values = dict(result=None, result_modifier=None,
                converted_result=None, converted_result_modifier=None,
                backup=None)
            values.update(kwargs)
            return SimpleNamespace(**values)

        self.assertEqual(get_limits_revalidation_field(
                line(result_modifier=nd, backup='390.0')), 'result')
        self.assertEqual(get_limits_revalidation_field(
                line(result='1.0', result_modifier=low, backup='0.7')),
            'result')
        self.assertEqual(get_limits_revalidation_field(
                line(result_modifier=ni, converted_result_modifier=nd,
                    backup='0.003')), 'converted_result')
        # Modifiers set by hand keep the result next to the backup
        self.assertIsNone(get_limits_revalidation_field(
                line(result='10', result_modifier=low, backup='10.0')))
        self.assertIsNone(get_limits_revalidation_field(
                line(result='5', result_modifier=nd, backup='5.0')))
        self.assertIsNone(get_limits_revalidation_field(
                line(result_modifier=nd)))
        self.assertIsNone(get_limits_revalidation_field(
                line(result='12.5', backup='12.5')))

    def test_inconsistent_result(self):
        "Detect results that the report would show against their limits"
        from types import SimpleNamespace
        from trytond.modules.lims.notebook import get_inconsistent_result

        nd = SimpleNamespace(code='nd')

        def line(**kwargs):
            values = dict(result=None, result_modifier=None,
                converted_result=None, converted_result_modifier=None,
                backup=None, literal_result=None, detection_limit='0.01',
                decimals=3, significant_digits=None)
            values.update(kwargs)
            return SimpleNamespace(**values)

        self.assertEqual(get_inconsistent_result(line(result_modifier=nd,
                    backup='390.0', detection_limit='0.50')), 'nd')
        self.assertIsNone(get_inconsistent_result(line(result_modifier=nd,
                    backup='0.0', detection_limit='0.50')))
        self.assertEqual(get_inconsistent_result(line(result='0.360',
                    decimals=0)), 'rounding')
        self.assertIsNone(get_inconsistent_result(line(result='0.360')))
        self.assertIsNone(get_inconsistent_result(line(result='0.360',
                    decimals=0, significant_digits=2)))
        self.assertIsNone(get_inconsistent_result(line(result='0.005',
                    decimals=0)))
        self.assertIsNone(get_inconsistent_result(line(result='12',
                    decimals=0, detection_limit='0')))
        self.assertIsNone(get_inconsistent_result(line(result_modifier=nd,
                    backup='390.0', detection_limit='0.50',
                    literal_result='Ausencia')))

    @with_transaction()
    def test_limits_validation_follows_new_limits(self):
        "A validated modifier is evaluated again when the limits change"
        from types import SimpleNamespace
        from trytond.modules.lims.notebook import apply_limits_validation
        pool = Pool()
        ModelData = pool.get('ir.model.data')
        NotebookLine = pool.get('lims.notebook.line')

        nd = ModelData.get_id('lims', 'result_modifier_nd')
        low = ModelData.get_id('lims', 'result_modifier_low')
        modifiers = {nd: SimpleNamespace(id=nd, code='nd'),
            low: SimpleNamespace(id=low, code='low')}

        def line(**kwargs):
            values = dict(accepted=False, result=None, result_modifier=None,
                converted_result=None, converted_result_modifier=None,
                backup=None, detection_limit='500', quantification_limit='1000',
                lower_limit=None, upper_limit=None, check_result_limits=False,
                rm_correction_formula=None, rec_name='line')
            values.update(kwargs)
            return SimpleNamespace(**values)

        detected = line(result='390')
        manual = line(result='390', result_modifier=modifiers[low])
        with patch.object(NotebookLine, 'save'):
            apply_limits_validation([detected, manual])
        self.assertEqual(detected.result_modifier, nd)
        self.assertIsNone(detected.result)
        self.assertEqual(detected.backup, '390.0')
        self.assertEqual(manual.result, '390')

        detected.result_modifier = modifiers[nd]
        detected.detection_limit, detected.quantification_limit = '0.5', '1'
        with patch.object(NotebookLine, 'save'):
            apply_limits_validation([detected])
        self.assertIsNone(detected.result_modifier)
        self.assertEqual(detected.result, '390.0')

        between = line(result_modifier=modifiers[nd], backup='0.7',
            detection_limit='0.5', quantification_limit='1')
        with patch.object(NotebookLine, 'save'):
            apply_limits_validation([between])
        self.assertEqual(between.result_modifier, low)
        self.assertEqual(between.result, '1.0')

def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
            LimsTestCase))
    suite.addTests(doctest.DocFileSuite('scenario_lims.rst',
            tearDown=doctest_teardown, encoding='utf-8',
            checker=doctest_checker,
            optionflags=doctest.REPORT_ONLY_FIRST_FAILURE))
    return suite
