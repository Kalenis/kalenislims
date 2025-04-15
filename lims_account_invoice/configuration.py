# -*- coding: utf-8 -*-
# This file is part of lims_account_invoice module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta


class Configuration(metaclass=PoolMeta):
    __name__ = 'lims.configuration'

    mail_send_invoice_subject = fields.Char('Email subject of Invoice report',
        help="In the text will be added suffix with the invoice report number")
    mail_send_invoice_body = fields.Text('Email body of Invoice report')
    invoice_condition = fields.Selection([
        ('service_confirmation', 'Upon confirmation of service'),
        ('report_issuance', 'Upon issuance of the report'),
        ], 'Billing Condition')
    invoice_party_change_relation_type = fields.Many2One('party.relation.type',
        'Relationship type for Party changes in Invoices')

    @staticmethod
    def default_invoice_condition():
        return 'service_confirmation'


class Cron(metaclass=PoolMeta):
    __name__ = 'ir.cron'

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.method.selection.extend([
                ('account.invoice|cron_send_invoice', "Send Of Invoice"),
                ])
