# This file is part of lims_sale module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import unittest
from types import SimpleNamespace
from unittest.mock import patch

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


    def test_included_analysis_ids(self):
        "Included analyses follow nested sets and groups without repeating"
        from trytond.modules.lims_sale.sale import get_included_analysis_ids

        def analysis(id_, type_='analysis', included=()):
            return SimpleNamespace(id=id_, type=type_, included_analysis=[
                    SimpleNamespace(included_analysis=i) for i in included])

        benzene, toluene, xylene = analysis(1), analysis(2), analysis(3)
        btex = analysis(10, 'set', [benzene, toluene, xylene])
        group = analysis(20, 'group', [btex, analysis(4), toluene])

        self.assertEqual(get_included_analysis_ids(btex), [1, 2, 3])
        self.assertEqual(get_included_analysis_ids(group), [1, 2, 3, 4])

    @with_transaction()
    def test_quoted_analysis(self):
        "A quoted set leaves out its excluded analyses"
        SaleLine = Pool().get('sale.line')

        def analysis(id_, type_='analysis', included=()):
            return SimpleNamespace(id=id_, type=type_, included_analysis=[
                    SimpleNamespace(included_analysis=i) for i in included])

        benzene, toluene, xylene = analysis(1), analysis(2), analysis(3)
        btex = analysis(10, 'set', [benzene, toluene, xylene])

        line = SimpleNamespace(analysis=btex, excluded_analysis=[])
        self.assertEqual(SaleLine.get_quoted_analysis(line), [1, 2, 3])
        line.excluded_analysis = [xylene]
        self.assertEqual(SaleLine.get_quoted_analysis(line), [1, 2])
        line = SimpleNamespace(analysis=benzene, excluded_analysis=[])
        self.assertEqual(SaleLine.get_quoted_analysis(line), [1])

    @with_transaction()
    def test_service_without_excluded_analysis(self):
        "The service of a quoted set gets no detail for excluded analyses"
        from trytond.modules.lims.sample import Service as LimsService
        pool = Pool()
        Service = pool.get('lims.service')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        btex = SimpleNamespace(id=10)
        quote = SimpleNamespace(analysis=btex,
            excluded_analysis=[SimpleNamespace(id=3)])
        other_quote = SimpleNamespace(analysis=SimpleNamespace(id=11),
            excluded_analysis=[SimpleNamespace(id=1)])
        service = SimpleNamespace(id=1, analysis=btex, sale_lines=[])
        service.get_quote_excluded_analysis = (
            lambda: Service.get_quote_excluded_analysis(service))
        details = [SimpleNamespace(service=service,
                analysis=SimpleNamespace(id=i)) for i in (1, 2, 3)]

        with patch.object(LimsService, 'update_analysis_detail',
                    classmethod(lambda cls, services: list(details))), \
                patch.object(EntryDetailAnalysis, 'delete') as delete:
            self.assertEqual(Service.update_analysis_detail([service]),
                details)
            delete.assert_not_called()

            service.sale_lines = [quote, other_quote]
            self.assertEqual(Service.update_analysis_detail([service]),
                details[:2])
            delete.assert_called_once_with([details[2]])

def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
            LimsTestCase))
    return suite
