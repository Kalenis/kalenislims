# -*- coding: utf-8 -*-
# This file is part of lims_account_invoice module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta


class SaleLine(metaclass=PoolMeta):
    __name__ = 'sale.line'

    invoice_condition = fields.Selection([
        ('service_confirmation', 'Upon confirmation of service'),
        ('report_issuance', 'Upon issuance of the report'),
        ], 'Billing Condition')

    @staticmethod
    def default_invoice_condition():
        return 'service_confirmation'
