# -*- coding: utf-8 -*-
# This file is part of lims module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import pytz
from datetime import datetime

from trytond.model import fields, Unique
from trytond.pool import PoolMeta
from trytond.pyson import Bool, Eval, Or

__all__ = ['Party', 'Address', 'Company']


class Party(metaclass=PoolMeta):
    __name__ = 'party.party'

    email_report = fields.Boolean('Email report')
    single_sending_report = fields.Boolean('Single sending of report')
    english_report = fields.Boolean('English report')
    no_acknowledgment_of_receipt = fields.Boolean(
        'No acknowledgment of receipt')
    sample_producers = fields.One2Many('lims.sample.producer', 'party',
        'Sample Producers')
    is_lab_professional = fields.Boolean('Laboratory Professional')
    lims_user = fields.Many2One('res.user', 'Lims User',
        states={'required': Bool(Eval('is_lab_professional'))},
        depends=['is_lab_professional'])
    entry_zone = fields.Many2One('lims.zone', 'Entry Zone')

    @classmethod
    def __setup__(cls):
        super(Party, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('lims_user_uniq', Unique(t, t.lims_user),
                'This lims user is already assigned to a party')]

    @staticmethod
    def default_email_report():
        return False

    @staticmethod
    def default_single_sending_report():
        return False

    @staticmethod
    def default_english_report():
        return False

    @staticmethod
    def default_no_acknowledgment_of_receipt():
        return False


class Address(metaclass=PoolMeta):
    __name__ = 'party.address'

    email = fields.Char('Email',
        states={
            'required': Or(
                Bool(Eval('invoice_contact')),
                Bool(Eval('report_contact')),
                Bool(Eval('acknowledgment_contact'))),
            },
        depends=['report_contact', 'acknowledgment_contact',
            'invoice_contact'])
    report_contact = fields.Boolean('Report contact')
    report_contact_default = fields.Boolean('Report contact by default',
        states={'readonly': ~Bool(Eval('report_contact'))},
        depends=['report_contact'])
    acknowledgment_contact = fields.Boolean('Acknowledgment contact')
    acknowledgment_contact_default = fields.Boolean(
        'Acknowledgment contact by default',
        states={'readonly': ~Bool(Eval('acknowledgment_contact'))},
        depends=['acknowledgment_contact'])
    invoice_contact = fields.Boolean('Invoice contact')
    invoice_contact_default = fields.Boolean('Invoice contact by default',
        states={'readonly': ~Bool(Eval('invoice_contact'))},
        depends=['invoice_contact'])

    @classmethod
    def __setup__(cls):
        super(Address, cls).__setup__()
        cls._error_messages.update({
            'invoice_address': 'There is already a address with invoice type',
            })

    @fields.depends('report_contact')
    def on_change_report_contact(self):
        if not self.report_contact:
            self.report_contact_default = False

    @fields.depends('acknowledgment_contact')
    def on_change_acknowledgment_contact(self):
        if not self.acknowledgment_contact:
            self.acknowledgment_contact_default = False

    @fields.depends('invoice_contact')
    def on_change_invoice_contact(self):
        if not self.invoice_contact:
            self.invoice_contact_default = False


class Company(metaclass=PoolMeta):
    __name__ = 'company.company'

    logo = fields.Binary('Logo')

    def get_timezone(self):
        timezone = pytz.utc
        if self.timezone:
            timezone = pytz.timezone(self.timezone)
        return timezone

    def convert_timezone_datetime(self, datetime_):
        timezone = self.get_timezone()
        return datetime.astimezone(datetime_.replace(tzinfo=pytz.utc),
            timezone)
