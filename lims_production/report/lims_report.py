# -*- coding: utf-8 -*-
# This file is part of lims_production module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.report import Report
from trytond.transaction import Transaction
from trytond.pool import Pool

__all__ = ['FamilyEquivalentReport']


class FamilyEquivalentReport(Report):
    'Family/Equivalent'
    __name__ = 'lims.family.equivalent.report'

    @classmethod
    def get_context(cls, records, data):
        pool = Pool()
        Company = pool.get('company.company')

        report_context = super(FamilyEquivalentReport, cls).get_context(
            records, data)

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
