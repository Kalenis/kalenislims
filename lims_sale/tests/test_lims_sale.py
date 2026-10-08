# This file is part of lims_sale module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import unittest
from types import SimpleNamespace

import trytond.tests.test_tryton
from trytond.pool import Pool
from trytond.tests.test_tryton import ModuleTestCase, with_transaction


class LimsTestCase(ModuleTestCase):
    'Test lims_sale module'
    module = 'lims_sale'

    @with_transaction()
    def test_quoted_analysis_methods(self):
        "Quoted analyses come from the sale line analysis, not its product"
        from trytond.modules.lims_sale.sample import (
            get_quoted_analysis_methods)
        pool = Pool()
        Uom = pool.get('product.uom')
        Template = pool.get('product.template')
        Product = pool.get('product.product')
        Analysis = pool.get('lims.analysis')

        unit, = Uom.search([('symbol', '=', 'u')])
        template, = Template.create([{
                    'name': 'Shared product',
                    'type': 'service',
                    'default_uom': unit.id,
                    }])
        product, = Product.create([{'template': template.id}])
        quoted, sibling = Analysis.create([{
                    'code': code,
                    'description': code,
                    'type': 'set',
                    'behavior': 'normal',
                    'product': product.id,
                    } for code in ('QUOTED', 'SIBLING')])

        def line(analysis=None, product=None, method=None):
            return SimpleNamespace(
                analysis=analysis, product=product, method=method)

        # a line with analysis quotes only that analysis
        self.assertEqual(
            get_quoted_analysis_methods([line(quoted, product, 'M1')]),
            {quoted.id: 'M1'})
        # a line without analysis quotes every analysis of its product
        self.assertEqual(
            get_quoted_analysis_methods([line(None, product, 'M2')]),
            {quoted.id: 'M2', sibling.id: 'M2'})
        # the method of the line with analysis is kept, in any order
        for lines in (
                [line(quoted, product, 'M1'), line(None, product, 'M2')],
                [line(None, product, 'M2'), line(quoted, product, 'M1')]):
            self.assertEqual(get_quoted_analysis_methods(lines),
                {quoted.id: 'M1', sibling.id: 'M2'})
        # a line without analysis nor product quotes nothing
        self.assertEqual(get_quoted_analysis_methods([line()]), {})

    @with_transaction()
    def test_allowed_analysis(self):
        "Services without quotation allow any analysis even with quotes"
        from trytond.modules.lims_sale.sample import get_allowed_analysis
        pool = Pool()
        Uom = pool.get('product.uom')
        Template = pool.get('product.template')
        Product = pool.get('product.product')
        Analysis = pool.get('lims.analysis')

        unit, = Uom.search([('symbol', '=', 'u')])
        template, = Template.create([{
                    'name': 'Metals',
                    'type': 'service',
                    'default_uom': unit.id,
                    }])
        product, = Product.create([{'template': template.id}])
        quoted, = Analysis.create([{
                    'code': 'METALS',
                    'description': 'METALS',
                    'type': 'set',
                    'behavior': 'normal',
                    'product': product.id,
                    }])
        other = quoted.id + 1000
        domain = [quoted.id, other]
        quote = [SimpleNamespace(
                analysis=quoted, product=product, method=None)]

        # with quotes, only the quoted analyses unless it is allowed
        self.assertEqual(get_allowed_analysis(domain, quote, False),
            [quoted.id])
        self.assertEqual(get_allowed_analysis(domain, quote, True), domain)
        # without quotes, everything or nothing
        self.assertEqual(get_allowed_analysis(domain, [], True), domain)
        self.assertEqual(get_allowed_analysis(domain, [], False), [])


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
            LimsTestCase))
    return suite
