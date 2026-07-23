# This file is part of lims module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import unittest
import doctest
from datetime import date

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


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
            LimsTestCase))
    suite.addTests(doctest.DocFileSuite('scenario_lims.rst',
            tearDown=doctest_teardown, encoding='utf-8',
            checker=doctest_checker,
            optionflags=doctest.REPORT_ONLY_FIRST_FAILURE))
    return suite
