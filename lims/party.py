# -*- coding: utf-8 -*-
# This file is part of lims module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import re
import pytz
from datetime import datetime
from sql import Literal

from trytond.model import DeactivableMixin, fields, Unique
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Bool, Eval, Or
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.i18n import gettext


class Party(metaclass=PoolMeta):
    __name__ = 'party.party'

    email_report = fields.Boolean('Email report')
    single_sending_report = fields.Boolean(
        'Single sending of report per Sample')
    entry_single_sending_report = fields.Boolean(
        'Single sending of report per Entry')
    report_language = fields.Many2One('ir.lang',
        'Results Report Language',
        domain=[('translatable', '=', True)])
    no_acknowledgment_of_receipt = fields.Boolean(
        'No acknowledgment of receipt')
    sample_producers = fields.One2Many('lims.sample.producer', 'party',
        'Sample Producers')
    is_lab_professional = fields.Boolean('Laboratory Professional')
    lims_user = fields.Many2One('res.user', 'Lims User',
        states={'required': Bool(Eval('is_lab_professional'))},
        depends=['is_lab_professional'])
    entry_zone = fields.Many2One('lims.zone', 'Entry Zone')
    block_entry_confirmation = fields.Boolean('Block Entry Confirmation')
    carrier = fields.Many2One('carrier', 'Carrier')
    trace_report = fields.Boolean('Trace report')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('lims_user_uniq', Unique(t, t.lims_user),
                'lims.msg_party_lims_user_unique_id')]

    @classmethod
    def __register__(cls, module_name):
        party_h = cls.__table_handler__(module_name)
        english_report_exist = party_h.column_exist('english_report')
        super().__register__(module_name)
        if english_report_exist:
            cls._migrate_english_report()
            party_h.drop_column('english_report')

    @classmethod
    def _migrate_english_report(cls):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Configuration = pool.get('lims.configuration')
        Lang = pool.get('ir.lang')

        party_table = cls.__table__()
        configuration_table = Configuration.__table__()
        lang_table = Lang.__table__()

        cursor.execute(*configuration_table.select(
            configuration_table.results_report_language,
            where=Literal(True)))
        default_language = cursor.fetchone()
        if default_language:
            cursor.execute(*party_table.update(
                [party_table.report_language], [default_language[0]],
                where=(party_table.english_report == Literal(False))))

        cursor.execute(*lang_table.select(
            lang_table.id,
            where=lang_table.code == Literal('en')))
        english_language = cursor.fetchone()
        if english_language:
            cursor.execute(*party_table.update(
                [party_table.report_language], [english_language[0]],
                where=(party_table.english_report == Literal(True))))

    @staticmethod
    def default_email_report():
        return False

    @staticmethod
    def default_single_sending_report():
        return False

    @staticmethod
    def default_entry_single_sending_report():
        return False

    @staticmethod
    def default_report_language():
        Config = Pool().get('lims.configuration')
        default_language = Config(1).results_report_language
        return default_language and default_language.id or None

    @staticmethod
    def default_no_acknowledgment_of_receipt():
        return False

    @staticmethod
    def default_trace_report():
        return False

    def get_results_report_address(self):
        pool = Pool()
        Address = pool.get('party.address')

        address = Address.search([
            ('party', '=', self.id),
            ('report', '=', True),
            ])
        if address:
            return address[0]

        try:
            address = Address.search([
                ('party', '=', self.id),
                ('invoice', '=', True),
                ])
            if address:
                return address[0]
        except KeyError:
            pass

        address = Address.search([
            ('party', '=', self.id),
            ])
        if address:
            return address[0]

        return None


class Address(metaclass=PoolMeta):
    __name__ = 'party.address'

    report = fields.Boolean('Results Report')
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

    @classmethod
    def validate(cls, addresses):
        super().validate(addresses)
        for address in addresses:
            address.check_email()

    def check_email(self):
        if self.email and not re.match(
                r"^[a-zA-Z0-9._'%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
                self.email):
            raise UserError(gettext('lims.msg_invalid_email'))


class Company(metaclass=PoolMeta):
    __name__ = 'company.company'

    logo = fields.Binary('Logo')
    short_name = fields.Char('Short Name')

    def get_timezone(self):
        timezone = pytz.utc
        if self.timezone:
            timezone = pytz.timezone(self.timezone)
        return timezone

    def convert_timezone_datetime(self, datetime_):
        timezone = self.get_timezone()
        return datetime.astimezone(datetime_.replace(tzinfo=pytz.utc),
            timezone)


class Employee(DeactivableMixin, metaclass=PoolMeta):
    __name__ = 'company.employee'
