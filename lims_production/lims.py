# -*- coding: utf-8 -*-
# This file is part of lims_production module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelView, ModelSQL, fields
from trytond.report import Report
from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.i18n import gettext


class PurityDegree(ModelSQL, ModelView):
    'Purity Degree'
    __name__ = 'lims.purity.degree'

    code = fields.Char('Code', required=True)
    name = fields.Char('Name', required=True)


class Brand(ModelSQL, ModelView):
    'Brand'
    __name__ = 'lims.brand'

    code = fields.Char('Code', required=True)
    name = fields.Char('Name', required=True)


class FamilyEquivalent(ModelSQL, ModelView):
    'Family/Equivalent'
    __name__ = 'lims.family.equivalent'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)
    uom = fields.Many2One('product.uom', 'UoM', required=True,
        domain=[('category.lims_only_available', '=', False)],
        help='The UoM\'s Category selected here will determine the set '
        'of Products that can be related to this Family/Equivalent.')
    products = fields.One2Many('product.template', 'family_equivalent',
        'Products', readonly=True)

    @classmethod
    def validate(cls, family_equivalents):
        super().validate(family_equivalents)
        for fe in family_equivalents:
            fe.check_products()

    def check_products(self):
        if self.products:
            main_category = self.uom.category
            for product in self.products:
                if main_category != product.default_uom.category:
                    raise UserError(gettext(
                        'lims_production.msg_invalid_product_uom_category'))

    @classmethod
    def copy(cls, family_equivalents, default=None):
        if default is None:
            default = {}
        current_default = default.copy()
        current_default['products'] = None
        return super().copy(family_equivalents, default=current_default)


class FamilyEquivalentReport(Report):
    'Family/Equivalent'
    __name__ = 'lims.family.equivalent.report'

    @classmethod
    def get_context(cls, records, header, data):
        pool = Pool()
        Company = pool.get('company.company')

        report_context = super().get_context(records, header, data)

        report_context['company'] = Company(Transaction().context['company'])
        report_context['records'] = cls._get_family_records(records)
        report_context['compute_qty'] = cls.compute_qty
        return report_context

    @classmethod
    def _get_family_records(cls, records):
        pool = Pool()
        Location = pool.get('stock.location')
        Date_ = pool.get('ir.date')
        FamilyEquivalent = pool.get('lims.family.equivalent')

        locations = Location.search([
            ('type', '=', 'storage'),
            ])
        context = {}
        context['locations'] = [l.id for l in locations]
        context['stock_date_end'] = Date_.today()

        with Transaction().set_context(context):
            res = FamilyEquivalent.browse(records)
        return res

    @classmethod
    def compute_qty(cls, from_uom, qty, to_uom):
        pool = Pool()
        Uom = pool.get('product.uom')
        return Uom.compute_qty(from_uom, qty, to_uom)
