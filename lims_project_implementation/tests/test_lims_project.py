# This file is part of lims_project_implementation module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import unittest

import trytond.tests.test_tryton
from trytond.tests.test_tryton import ModuleTestCase


class LimsTestCase(ModuleTestCase):
    'Test lims_project_implementation module'
    module = 'lims_project_implementation'


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
            LimsTestCase))
    return suite
