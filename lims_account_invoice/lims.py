# -*- coding: utf-8 -*-
# This file is part of lims_account_invoice module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import operator
from collections import defaultdict
from decimal import Decimal

from trytond.model import fields
from trytond.wizard import Wizard, StateAction
from trytond.report import Report
from trytond.pool import Pool, PoolMeta
from trytond.pyson import PYSONEncoder
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.i18n import gettext


class FractionType(metaclass=PoolMeta):
    __name__ = 'lims.fraction.type'

    invoiceable = fields.Boolean('Invoiceable')

    @staticmethod
    def default_invoiceable():
        return True


class Entry(metaclass=PoolMeta):
    __name__ = 'lims.entry'

    last_release_date = fields.Function(fields.DateTime(
        'Last Release date'), 'get_last_release_date')
    qty_lines_pending_invoicing = fields.Function(fields.Integer(
        'Lines pending invoicing'), 'get_qty_lines_pending_invoicing')

    @classmethod
    def get_last_release_date(cls, entries, name):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        ResultsVersion = pool.get('lims.results_report.version')
        ResultsDetail = pool.get('lims.results_report.version.detail')
        NotebookLine = pool.get('lims.notebook.line')
        Notebook = pool.get('lims.notebook')
        Fraction = pool.get('lims.fraction')
        Sample = pool.get('lims.sample')

        result = {}
        for e in entries:
            cursor.execute('SELECT MAX(rd.release_date) '
                'FROM "' + ResultsVersion._table + '" rv '
                    'INNER JOIN "' + ResultsDetail._table + '" rd '
                    'ON rv.id = rd.report_version '
                    'INNER JOIN "' + NotebookLine._table + '" nl '
                    'ON nl.results_report = rv.results_report '
                    'INNER JOIN "' + Notebook._table + '" n '
                    'ON n.id = nl.notebook '
                    'INNER JOIN "' + Fraction._table + '" f '
                    'ON f.id = n.fraction '
                    'INNER JOIN "' + Sample._table + '" s '
                    'ON s.id = f.sample '
                'WHERE s.entry = %s '
                    'AND rd.state = \'released\' '
                    'AND rd.type != \'preliminary\'',
                (str(e.id),))
            result[e.id] = cursor.fetchone()[0]

        return result

    @classmethod
    def get_qty_lines_pending_invoicing(cls, entries, name):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Sample = pool.get('lims.sample')
        Fraction = pool.get('lims.fraction')
        Service = pool.get('lims.service')
        InvoiceLine = pool.get('account.invoice.line')

        result = {}
        for e in entries:
            result[e.id] = 0

            cursor.execute('SELECT srv.id '
                'FROM "' + Service._table + '" srv '
                    'INNER JOIN "' + Fraction._table + '" f '
                    'ON f.id = srv.fraction '
                    'INNER JOIN "' + Sample._table + '" s '
                    'ON s.id = f.sample '
                'WHERE s.entry = %s',
                (str(e.id),))
            services_ids = [x[0] for x in cursor.fetchall()]
            if not services_ids:
                continue

            origins = '\', \''.join(['lims.service,' + str(s)
                for s in services_ids])
            cursor.execute('SELECT COUNT(*) '
                'FROM "' + InvoiceLine._table + '" '
                'WHERE origin IN (\'' + origins + '\') '
                    'AND invoice IS NULL')
            result[e.id] = cursor.fetchone()[0]

        return result

    @classmethod
    def on_hold(cls, entries):
        super().on_hold(entries)
        cls.create_invoice_lines(entries)

    @classmethod
    def create_invoice_lines(cls, entries):
        Service = Pool().get('lims.service')

        with Transaction().set_context(_check_access=False):
            services = Service.search([
                ('entry', 'in', [e.id for e in entries]),
                ('annulled', '=', False),
                ])
        for service in services:
            service.create_invoice_line()

    @classmethod
    def view_toolbar_get(cls):
        if not Transaction().context.get('ready_for_invoicing', False):
            return super().view_toolbar_get()

        # Entries Ready for Invoicing uses specific keywords
        prints = cls.get_entries_ready_for_invoicing_keyword('form_print')
        actions = cls.get_entries_ready_for_invoicing_keyword('form_action')
        relates = cls.get_entries_ready_for_invoicing_keyword('form_relate')
        result = {
            'print': prints,
            'action': actions,
            'relate': relates,
            'exports': [],
            'emails': [],
            }
        return result

    @classmethod
    def get_entries_ready_for_invoicing_keyword(cls, keyword):
        """
        Method copied from ActionKeyword. It search for specific keywords
        for Entries Ready for Invoicing: lims.entry,-2
        """
        pool = Pool()
        ActionKeyword = pool.get('ir.action.keyword')
        Action = pool.get('ir.action')

        key = (keyword, ('lims.entry', -2))
        keywords = ActionKeyword._get_keyword_cache.get(key)
        if keywords is not None:
            return keywords

        clause = [
            ('keyword', '=', keyword),
            ('model', '=', 'lims.entry,-2'),
            ('action.active', '=', True),
            ]
        action_keywords = ActionKeyword.search(clause, order=[])
        types = defaultdict(list)
        for action_keyword in action_keywords:
            type_ = action_keyword.action.type
            types[type_].append(action_keyword.action.id)
        keywords = []
        for type_, action_ids in types.items():
            for value in Action.get_action_values(type_, action_ids):
                value['keyword'] = keyword
                keywords.append(value)
        keywords.sort(key=operator.itemgetter('name'))
        ActionKeyword._get_keyword_cache.set(key, keywords)
        return keywords


class Fraction(metaclass=PoolMeta):
    __name__ = 'lims.fraction'

    @classmethod
    def confirm(cls, fractions):
        fractions_to_invoice = [f for f in fractions if
            f.sample.entry.state != 'pending']
        super().confirm(fractions)
        if fractions_to_invoice:
            cls.create_invoice_lines(fractions_to_invoice)

    @classmethod
    def create_invoice_lines(cls, fractions):
        Service = Pool().get('lims.service')

        with Transaction().set_context(_check_access=False):
            services = Service.search([
                ('fraction', 'in', [f.id for f in fractions]),
                ('annulled', '=', False),
                ])
        for service in services:
            service.create_invoice_line()


class Service(metaclass=PoolMeta):
    __name__ = 'lims.service'

    @classmethod
    def create(cls, vlist):
        services = super().create(vlist)
        services_to_invoice = [s for s in services if
            s.entry.state == 'pending']
        for service in services_to_invoice:
            service.create_invoice_line()
        return services

    def create_invoice_line(self):
        pool = Pool()
        InvoiceLine = pool.get('account.invoice.line')

        if (not self.fraction.type.invoiceable or
                self.fraction.cie_fraction_type):
            return
        with Transaction().set_context(_check_access=False):
            if InvoiceLine.search_count([('origin', '=', str(self))]) != 0:
                return
        invoice_line = self.get_invoice_line()
        if not invoice_line:
            return
        with Transaction().set_context(_check_access=False):
            InvoiceLine.create([invoice_line])

    def get_invoice_line(self):
        pool = Pool()
        Config = pool.get('lims.configuration')
        Company = pool.get('company.company')

        config_ = Config(1)
        company = Transaction().context.get('company')
        currency = Company(company).currency.id
        product = self.analysis.product if self.analysis else None
        if not product:
            return
        account_revenue = product.account_revenue_used
        if not account_revenue:
            raise UserError(
                gettext('lims_account_invoice.msg_missing_account_revenue',
                    product=self.analysis.product.rec_name,
                    service=self.rec_name))

        party = self.entry.invoice_party
        taxes = []
        pattern = {}
        for tax in product.customer_taxes_used:
            if party.customer_tax_rule:
                tax_ids = party.customer_tax_rule.apply(tax, pattern)
                if tax_ids:
                    taxes.extend(tax_ids)
                continue
            taxes.append(tax.id)
        if party.customer_tax_rule:
            tax_ids = party.customer_tax_rule.apply(None, pattern)
            if tax_ids:
                taxes.extend(tax_ids)
        taxes_to_add = None
        if taxes:
            taxes_to_add = [('add', taxes)]

        ready_to_invoice = False
        if config_.invoice_condition == 'service_confirmation':
            ready_to_invoice = True

        return {
            'company': company,
            'currency': currency,
            'invoice_type': 'out',
            'party': party,
            'description': self.number + ' - ' + self.analysis.rec_name,
            'origin': str(self),
            'quantity': 1,
            'unit': product.default_uom,
            'product': product,
            'unit_price': Decimal('1.00'),
            'taxes': taxes_to_add,
            'account': account_revenue,
            'lims_ready_to_invoice': ready_to_invoice,
            }

    @classmethod
    def delete(cls, services):
        cls.delete_invoice_lines(services)
        super().delete(services)

    @classmethod
    def write(cls, *args):
        super().write(*args)
        actions = iter(args)
        for services, vals in zip(actions, actions):
            if vals.get('annulled'):
                cls.delete_invoice_lines(services)

    @classmethod
    def delete_invoice_lines(cls, services):
        InvoiceLine = Pool().get('account.invoice.line')

        lines_to_delete = []
        for service in services:
            with Transaction().set_context(_check_access=False):
                lines = InvoiceLine.search([
                    ('origin', '=', str(service)),
                    ])
            lines_to_delete.extend(lines)
        if lines_to_delete:
            for line in lines_to_delete:
                if line.invoice:
                    raise UserError(gettext(
                        'lims_account_invoice.msg_delete_service_invoice'))
            with Transaction().set_context(_check_access=False,
                    delete_service=True):
                InvoiceLine.delete(lines_to_delete)


class ManageServices(metaclass=PoolMeta):
    __name__ = 'lims.manage_services'

    def create_service(self, service, fraction):
        new_service = super().create_service(service, fraction)
        new_service.create_invoice_line()
        return new_service


class EditSampleService(metaclass=PoolMeta):
    __name__ = 'lims.sample.edit_service'

    def create_service(self, service, fraction):
        new_service = super().create_service(service, fraction)
        new_service.create_invoice_line()
        return new_service


class AddSampleService(metaclass=PoolMeta):
    __name__ = 'lims.sample.add_service'

    def create_service(self, service, fraction):
        new_service = super().create_service(service, fraction)
        new_service.create_invoice_line()
        return new_service


class EditFractionService(metaclass=PoolMeta):
    __name__ = 'lims.fraction.edit_service'

    def create_service(self, service, fraction):
        new_service = super().create_service(service, fraction)
        new_service.create_invoice_line()
        return new_service


class AddFractionService(metaclass=PoolMeta):
    __name__ = 'lims.fraction.add_service'

    def create_service(self, service, fraction):
        new_service = super().create_service(service, fraction)
        new_service.create_invoice_line()
        return new_service


class EntryCancel(metaclass=PoolMeta):
    __name__ = 'lims.entry.cancel'

    def transition_check(self):
        pool = Pool()
        Entry = pool.get('lims.entry')
        Service = pool.get('lims.service')
        InvoiceLine = pool.get('account.invoice.line')

        res = super().transition_check()

        entry = Entry(Transaction().context['active_id'])

        with Transaction().set_context(_check_access=False):
            services = Service.search([
                ('fraction.sample.entry', '=', entry),
                ('annulled', '=', False),
                ])
            for service in services:
                if InvoiceLine.search_count([
                        ('origin', '=', str(service)),
                        ('invoice', '!=', None),
                        ]) > 0:
                    raise UserError(gettext(
                        'lims_account_invoice.msg_entry_cancellation_invoiced'))

        return 'start'


class OpenEntriesReadyForInvoicing(Wizard):
    'Entries Ready for Invoicing'
    __name__ = 'lims.entries_ready_for_invoicing'

    start_state = 'open_'
    open_ = StateAction('lims_account_invoice.act_entries_ready_for_invoicing')

    def _get_entries_ready_for_invoicing(self):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        InvoiceLine = pool.get('account.invoice.line')
        NotebookLine = pool.get('lims.notebook.line')
        Notebook = pool.get('lims.notebook')
        Fraction = pool.get('lims.fraction')
        Sample = pool.get('lims.sample')

        cursor.execute('SELECT origin '
            'FROM "' + InvoiceLine._table + '" '
            'WHERE origin LIKE \'lims.service,%\' '
                'AND invoice IS NULL')
        invoiced_services = [x[0][13:] for x in cursor.fetchall()]
        if not invoiced_services:
            return []
        services_ids = ', '.join(s for s in invoiced_services)

        cursor.execute('SELECT DISTINCT(s.entry) '
            'FROM "' + NotebookLine._table + '" nl '
                'INNER JOIN "' + Notebook._table + '" n '
                'ON n.id = nl.notebook '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON f.id = n.fraction '
                'INNER JOIN "' + Sample._table + '" s '
                'ON s.id = f.sample '
            'WHERE nl.service IN (' + services_ids + ')')
        invoiced_entries = [x[0] for x in cursor.fetchall()]

        cursor.execute('SELECT DISTINCT(s.entry) '
            'FROM "' + NotebookLine._table + '" nl '
                'INNER JOIN "' + Notebook._table + '" n '
                'ON n.id = nl.notebook '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON f.id = n.fraction '
                'INNER JOIN "' + Sample._table + '" s '
                'ON s.id = f.sample '
            'WHERE nl.service IN (' + services_ids + ') '
                'AND (nl.annulled = FALSE '
                'AND nl.report = TRUE '
                'AND nl.results_report IS NULL)')
        pending_entries = [x[0] for x in cursor.fetchall()]

        entries = list(set(invoiced_entries) - set(pending_entries))
        if not entries:
            return []
        return entries

    def do_open_(self, action):
        entries_ids = self._get_entries_ready_for_invoicing()
        action['pyson_context'] = PYSONEncoder().encode({
            'ready_for_invoicing': True,
            })
        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', 'in', entries_ids),
            ])
        return action, {}


class OpenLinesPendingInvoicing(Wizard):
    'Lines Pending Invoicing'
    __name__ = 'lims.lines_pending_invoicing'

    start_state = 'open_'
    open_ = StateAction('lims_account_invoice.act_invoice_line')

    def do_open_(self, action):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Entry = pool.get('lims.entry')
        Sample = pool.get('lims.sample')
        Fraction = pool.get('lims.fraction')
        Service = pool.get('lims.service')
        InvoiceLine = pool.get('account.invoice.line')

        lines_ids = []
        entries = Entry.browse(Transaction().context['active_ids'])
        for entry in entries:
            cursor.execute('SELECT srv.id '
                'FROM "' + Service._table + '" srv '
                    'INNER JOIN "' + Fraction._table + '" f '
                    'ON f.id = srv.fraction '
                    'INNER JOIN "' + Sample._table + '" s '
                    'ON s.id = f.sample '
                'WHERE s.entry = %s',
                (str(entry.id),))
            services_ids = [x[0] for x in cursor.fetchall()]
            if not services_ids:
                continue

            origins = '\', \''.join(['lims.service,' + str(s)
                for s in services_ids])
            cursor.execute('SELECT id '
                'FROM "' + InvoiceLine._table + '" '
                'WHERE origin IN (\'' + origins + '\') '
                    'AND invoice IS NULL')
            lines_ids.extend(x[0] for x in cursor.fetchall())

        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', 'in', lines_ids),
            ])
        action['name'] += ' (%s)' % ', '.join(
            e.rec_name for e in entries)
        return action, {}


class EntriesReadyForInvoicingSpreadsheet(Report):
    'Entries Ready for Invoicing'
    __name__ = 'lims.entries_ready_for_invoicing.spreadsheet'


class ResultsReportVersionDetail(metaclass=PoolMeta):
    __name__ = 'lims.results_report.version.detail'

    @classmethod
    def do_release(cls, details):
        pool = Pool()
        Config = pool.get('lims.configuration')
        super().do_release(details)
        config_ = Config(1)
        if config_.invoice_condition == 'report_issuance':
            for detail in details:
                detail.set_invoice_lines_ready()

    def set_invoice_lines_ready(self):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        InvoiceLine = pool.get('account.invoice.line')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        NotebookLine = pool.get('lims.notebook.line')
        ResultsLine = pool.get('lims.results_report.version.detail.line')
        ResultsSample = pool.get('lims.results_report.version.detail.sample')

        cursor.execute('SELECT DISTINCT(ad.service) '
            'FROM "' + EntryDetailAnalysis._table + '" ad '
                'INNER JOIN "' + NotebookLine._table + '" nl '
                'ON ad.id = nl.analysis_detail '
                'INNER JOIN "' + ResultsLine._table + '" rl '
                'ON nl.id = rl.notebook_line '
                'INNER JOIN "' + ResultsSample._table + '" rs '
                'ON rl.detail_sample = rs.id '
            'WHERE rs.version_detail = %s', (self.id,))
        services_ids = [str(x[0]) for x in cursor.fetchall()]
        if not services_ids:
            return

        origins = '\', \''.join(['lims.service,' + str(s)
            for s in services_ids])
        cursor.execute('SELECT id '
            'FROM "' + InvoiceLine._table + '" '
            'WHERE origin IN (\'' + origins + '\') '
                'AND invoice IS NULL '
                'AND lims_ready_to_invoice IS NOT TRUE')
        lines_ids = [x[0] for x in cursor.fetchall()]
        if not lines_ids:
            return

        with Transaction().set_context(_check_access=False):
            lines = InvoiceLine.browse(lines_ids)
            InvoiceLine.write(lines, {'lims_ready_to_invoice': True})
