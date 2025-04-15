# -*- coding: utf-8 -*-
# This file is part of lims_account_invoice module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from datetime import datetime
from collections import defaultdict
from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from time import time
from sql import Literal
from sql.functions import Substring, Position
import logging

from trytond.model import Workflow, ModelView, ModelSQL, fields
from trytond.wizard import Wizard, StateTransition, StateView, StateAction, \
    Button
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, Bool, Or, If, PYSONEncoder
from trytond.transaction import Transaction
from trytond.tools import get_smtp_server
from trytond.config import config as tconfig
from trytond.exceptions import UserError
from trytond.i18n import gettext

logger = logging.getLogger(__name__)


class Invoice(metaclass=PoolMeta):
    __name__ = 'account.invoice'

    no_send_invoice = fields.Boolean('No send invoice',
        states={'invisible': Eval('type') == 'in'},
        help='If checked, then the invoice will not be mailed to contacts.')
    invoice_contacts = fields.One2Many('account.invoice.invoice_contacts',
        'invoice', 'Invoice contacts',
        states={'invisible': Eval('type') == 'in'})
    sent = fields.Boolean('Sent', readonly=True,
        help='If checked, then the invoice was mailed to contacts.')
    sent_date = fields.DateTime('Sent date', readonly=True,
        states={'invisible': Bool(Eval('no_send_invoice'))})
    entries_comments = fields.Text('Entries comments',
        states={'invisible': Eval('type') == 'in'}, readonly=True)

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._check_modify_exclude.update({'sent', 'sent_date',
            'invoice_contacts', 'no_send_invoice'})

    @classmethod
    def view_attributes(cls):
        return super().view_attributes() + [
            ('/form/notebook/page[@id="contacts"]', 'states', {
                    'invisible': Eval('type') == 'in',
                    }),
            ]

    @fields.depends('party')
    def on_change_party(self):
        super().on_change_party()
        self.no_send_invoice = False
        if self.party:
            self.no_send_invoice = self.party.no_send_invoice

    def _credit(self, **values):
        credit = super()._credit(**values)
        if self.invoice_contacts:
            credit.invoice_contacts = [contact._credit()
                for contact in self.invoice_contacts]
        credit.no_send_invoice = self.no_send_invoice
        return credit

    @classmethod
    @ModelView.button
    @Workflow.transition('posted')
    def post(cls, invoices):
        cls.check_invoice_contacts(invoices)
        super().post(invoices)

    @classmethod
    def check_invoice_contacts(cls, invoices):
        for invoice in invoices:
            if invoice.type == 'out':
                if (not invoice.no_send_invoice and not
                        invoice.invoice_contacts):
                    raise UserError(gettext(
                        'lims_account_invoice.msg_not_invoice_contacts'))

    @classmethod
    def cron_send_invoice(cls):
        '''
        Cron - Send Of Invoice
        '''
        logger.info('Cron - Send Of Invoice:INIT')
        t1 = time()  # DEBUG
        pool = Pool()
        SendOfInvoice = pool.get('account.invoice.send_invoice', type='wizard')
        invoices = cls.search([
            ('type', '=', 'out'),
            ('sent', '=', False),
            ('no_send_invoice', '=', False),
            ('state', 'in', ['posted', 'paid']),
            ])
        logger.info('Cron - Send Of Invoice:Se procesaran %s facturas...',
                len(invoices))
        if invoices:
            session_id, _, _ = SendOfInvoice.create()
            send_of_invoice = SendOfInvoice(session_id)
            with Transaction().set_context(active_ids=[invoice.id for invoice
                    in invoices]):
                send_of_invoice.transition_start()
        tt = round(time() - t1, 2)  # DEBUG
        logger.info('Cron - Send Of Invoice:END:Finalizado en %s segundos.',
                tt)

    def mail_send_invoice(self):
        pool = Pool()
        Config = pool.get('lims.configuration')

        if not self.invoice_report_cache:
            return

        config_ = Config(1)
        smtp_server = config_.mail_send_invoice_smtp
        from_addr = (smtp_server and smtp_server.smtp_email or
            tconfig.get('email', 'from'))
        to_addrs = [c.contact.email for c in self.invoice_contacts]
        if not (from_addr and to_addrs):
            logger.warn('mail_send_invoice():Factura %s:Envio omitido '
                    'por no contener contactos.', self.number)  # DEBUG
            return
        logger.info('mail_send_invoice():INFO:Contactos de factura:'
                'emails:(%s)', ','.join(to_addrs))  # DEBUG

        reply_to = smtp_server and smtp_server.smtp_reply_to or from_addr
        hide_recipients = config_.mail_send_invoice_hide_recipients
        subject, body = self.subject_body()
        attachments_data = self.attachment()

        msg = self.create_msg(from_addr, to_addrs, subject,
            body, reply_to, hide_recipients, attachments_data)
        return self.send_msg(smtp_server, from_addr, to_addrs, msg)

    def subject_body(self):
        pool = Pool()
        Config = pool.get('lims.configuration')
        User = pool.get('res.user')
        Lang = pool.get('ir.lang')

        config_ = Config(1)

        lang = User(Transaction().user).language
        if not lang:
            lang, = Lang.search([
                    ('code', '=', 'en'),
                    ], limit=1)

        with Transaction().set_context(language=lang.code):
            subject = str('%s %s' % (config_.mail_send_invoice_subject,
                    self.number)).strip()
            body = str(config_.mail_send_invoice_body)

        return subject, body

    def attachment(self):
        data = []
        data.append({
            'content': self.invoice_report_cache,
            'format': self.invoice_report_format,
            'mimetype':
                self.invoice_report_format == 'pdf' and 'pdf' or
                'vnd.oasis.opendocument.text',
            'filename':
                str(self.number) + '.' +
                str(self.invoice_report_format),
            'name': str(self.number),
            })
        if self.invoice_service_report_cache:
            data.append({
                'content': self.invoice_service_report_cache,
                'format': self.invoice_service_report_format,
                'mimetype':
                    self.invoice_service_report_format == 'pdf' and 'pdf' or
                    'vnd.oasis.opendocument.text',
                'filename':
                    str(self.number) + ' (II).' +
                    str(self.invoice_report_format),
                'name': str(self.number) + ' (II)',
                })
        return data

    def create_msg(self, from_addr, to_addrs, subject, body,
            reply_to, hide_recipients, attachments_data):
        if not to_addrs:
            return None

        msg = MIMEMultipart('mixed')
        msg['From'] = from_addr
        if not hide_recipients:
            msg['To'] = ', '.join(to_addrs)
        msg['Subject'] = subject

        if reply_to != from_addr:
            msg.add_header('reply-to', reply_to)

        msg_body = MIMEText('text', 'plain')
        msg_body.set_payload(body.encode('UTF-8'), 'UTF-8')
        msg.attach(msg_body)

        for attachment_data in attachments_data:
            attachment = MIMEBase('application', 'octet-stream')
            attachment.set_payload(attachment_data['content'])
            encoders.encode_base64(attachment)
            attachment.add_header('Content-Disposition', 'attachment',
                filename=attachment_data['filename'])
            msg.attach(attachment)
        return msg

    def send_msg(self, smtp_server, from_addr, to_addrs, msg):
        to_addrs = list(set(to_addrs))
        success = False
        server = None
        try:
            if smtp_server:
                server = smtp_server.get_smtp_server()
            else:
                server = get_smtp_server()
            server.sendmail(from_addr, to_addrs, msg.as_string())
            server.quit()
            success = True
        except Exception as e:
            logger.error('Unable to deliver mail for invoice %s', self.number)
            logger.error(str(e))
            if server is not None:
                server.quit()
        return success


class InvoiceContact(ModelSQL, ModelView):
    'Invoice Contact'
    __name__ = 'account.invoice.invoice_contacts'

    invoice = fields.Many2One('account.invoice', 'Invoice',
        ondelete='CASCADE', required=True)
    contact = fields.Many2One('party.address', 'Contact', required=True,
        domain=[('invoice_contact', '=', True)])

    def _credit(self):
        credit = self.__class__()
        for field in ('invoice', 'contact'):
            setattr(credit, field, getattr(self, field))
        return credit


class InvoiceLine(metaclass=PoolMeta):
    __name__ = 'account.invoice.line'

    lims_service_party = fields.Function(fields.Many2One('party.party',
        'Party', context={'company': Eval('company', -1)},
        depends={'company'}, states={
            'invisible': Or(Eval('_parent_invoice', {}).get('type') == 'in',
                Eval('invoice_type') == 'in'),
            }), 'get_fraction_field', searcher='search_fraction_field')
    lims_service_entry = fields.Function(fields.Many2One('lims.entry',
        'Entry', states={
            'invisible': Or(Eval('_parent_invoice', {}).get('type') == 'in',
                Eval('invoice_type') == 'in'),
            }), 'get_fraction_field', searcher='search_fraction_field')
    lims_service_sample = fields.Function(fields.Many2One('lims.sample',
        'Sample', states={
            'invisible': Or(Eval('_parent_invoice', {}).get('type') == 'in',
                Eval('invoice_type') == 'in'),
            }), 'get_fraction_field', searcher='search_fraction_field')
    lims_service_results_reports = fields.Function(fields.Char(
        'Results Reports', states={
            'invisible': Or(Eval('_parent_invoice', {}).get('type') == 'in',
                Eval('invoice_type') == 'in'),
            }), 'get_results_reports', searcher='search_results_reports')
    party_domain = fields.Function(fields.Many2Many('party.party',
        None, None, 'Party domain', context={'company': Eval('company', -1)},
        depends={'company'}), 'get_party_domain')
    lims_ready_to_invoice = fields.Boolean('Ready to invoice', readonly=True)
    lims_ready_to_invoice_reason = fields.Char('Reason for Ready to invoice',
        readonly=True)
    lims_ready_to_invoice_uid = fields.Many2One('res.user',
        'User of Ready to invoice', readonly=True)

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.origin.states['readonly'] = True
        cls.party.domain = ['OR', ('id', '=', Eval('party', -1)),
            If(Bool(Eval('party_domain')),
            ('id', 'in', Eval('party_domain')), ('id', '!=', -1))]
        cls.product.states['readonly'] = Or(
            Eval('invoice_state') != 'draft',
            Bool(Eval('lims_service_sample')))

    @staticmethod
    def default_lims_ready_to_invoice():
        return False

    @classmethod
    def delete(cls, lines):
        if not Transaction().context.get('delete_service', False):
            cls.check_service_invoice(lines)
        super().delete(lines)

    @classmethod
    def check_service_invoice(cls, lines):
        for line in lines:
            if (line.origin and line.origin.__name__ == 'lims.service' and
                    (not hasattr(line, 'economic_offer') or
                    not line.economic_offer)):
                raise UserError(
                    gettext('lims_account_invoice.msg_delete_service_invoice',
                        service=line.origin.rec_name))

    @classmethod
    def get_fraction_field(cls, lines, names):
        result = {}
        for name in names:
            result[name] = {}
            for l in lines:
                if l.origin and l.origin.__name__ == 'lims.service':
                    # name[13:]: remove 'lims_service_' from field name
                    field = getattr(l.origin.fraction, name[13:], None)
                    result[name][l.id] = field.id if field else None
                else:
                    result[name][l.id] = None
        return result

    @classmethod
    def search_fraction_field(cls, name, clause):
        return [('origin.fraction.' + name[13:],) + tuple(clause[1:]) +
                ('lims.service',)]

    def _order_service_field(name):
        def order_field(tables):
            Service = Pool().get('lims.service')
            field = Service._fields[name]
            table, _ = tables[None]
            service_tables = tables.get('service')
            if service_tables is None:
                service = Service.__table__()
                service_tables = {
                    None: (service, (table.origin.like('lims.service,%') &
                        (Service.id.sql_cast(Substring(table.origin,
                        Position(',', table.origin) + Literal(1))) ==
                        service.id))),
                    }
                tables['service'] = service_tables
            return field.convert_order(name, service_tables, Service)
        return staticmethod(order_field)
    order_lims_service_entry = _order_service_field('entry')

    @classmethod
    def get_results_reports(cls, lines, name):
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        result = {}
        for l in lines:
            reports = []
            if l.origin and l.origin.__name__ == 'lims.service':
                notebook_lines = NotebookLine.search([
                    ('service', '=', l.origin.id),
                    ('results_report', '!=', None),
                    ], limit=1)
                if notebook_lines:
                    reports = [nl.results_report.rec_name for nl in
                        notebook_lines]
            if reports:
                result[l.id] = ', '.join([r for r in reports])
            else:
                result[l.id] = None
        return result

    @classmethod
    def search_results_reports(cls, name, clause):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        ResultsReport = pool.get('lims.results_report')
        NotebookLine = pool.get('lims.notebook.line')

        value = clause[2]
        cursor.execute('SELECT DISTINCT(nl.service) '
            'FROM "' + ResultsReport._table + '" r '
                'INNER JOIN "' + NotebookLine._table + '" nl '
                'ON nl.results_report = r.id '
            'WHERE r.number ILIKE %s', (value,))
        services = [x[0] for x in cursor.fetchall()]
        if not services:
            return [('id', '=', -1)]

        services_ids = ['lims.service,' + str(s) for s in services]
        return [('origin', 'in', services_ids)]

    @classmethod
    def _get_origin(cls):
        models = super()._get_origin()
        models.append('lims.service')
        return models

    @fields.depends('origin')
    def get_party_domain(self, name=None):
        pool = Pool()
        Config = pool.get('lims.configuration')

        config_ = Config(1)

        parties = []
        if self.origin and self.origin.__name__ == 'lims.service':
            party = self.origin.party
            parties.append(party.id)
            if config_.invoice_party_relation_type:
                parties.extend([r.to.id for r in party.relations
                    if r.type == config_.invoice_party_relation_type])
        return parties


class PopulateInvoiceContactsStart(ModelView):
    'Populate Invoice Contacts Start'
    __name__ = 'account.invoice.populate_invoice_contacts.start'


class PopulateInvoiceContacts(Wizard):
    'Populate Invoice Contacts'
    __name__ = 'account.invoice.populate_invoice_contacts'

    start = StateView('account.invoice.populate_invoice_contacts.start',
        'lims_account_invoice.account_invoice_populate_invoice_contacts_start'
        '_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Populate', 'populate', 'tryton-ok', default=True),
            ])
    populate = StateTransition()

    def transition_populate(self):
        logger.info('transition_populate():INIT')
        t1 = time()  # DEBUG
        pool = Pool()
        Invoice = pool.get('account.invoice')
        InvoiceLine = pool.get('account.invoice.line')
        InvoiceContacts = pool.get('account.invoice.invoice_contacts')
        EntryInvoiceContacts = pool.get('lims.entry.invoice_contacts')
        Entry = pool.get('lims.entry')

        invoice = Invoice(Transaction().context['active_id'])

        # clean entry fields
        invoice.entries_comments = None
        invoice.save()
        invoice_contacts = InvoiceContacts.search([
            ('invoice', '=', invoice)])
        if invoice_contacts:
            InvoiceContacts.delete(invoice_contacts)

        lines = InvoiceLine.search([
            ('invoice', '=', invoice.id),
            ])
        if not lines:
            logger.warn('transition_populate():La factura no '
                    'posee lineas! (id: %s)', invoice.id)
            return 'end'

        entry_ids = list(set([l.lims_service_entry.id for l in lines
                if l.lims_service_entry]))
        if not entry_ids:
            logger.warn('transition_populate():La factura no '
                    'posee lineas asociadas a partidas! (id: %s)', invoice.id)
            return 'end'

        # Set entries comments
        entries_comments = ''
        entries = Entry.search([('id', 'in', entry_ids)],
            order=[('id', 'ASC')])
        for entry in entries:
            if not entry.invoice_comments:
                continue
            if entries_comments:
                entries_comments += '\n'
            entries_comments += '%s: %s' % (entry.number,
                entry.invoice_comments)
        invoice.entries_comments = entries_comments
        invoice.save()

        # Set entries contacts
        entry_invoice_contacts = EntryInvoiceContacts.search([
            ('entry', 'in', entry_ids),
            ('contact.active', '=', True),
            ('contact.invoice_contact', '=', True),
            ])
        if not entry_invoice_contacts:
            logger.warn('transition_populate():Las partidas de '
                    'las lineas de la factura, no poseen contactos de '
                    'facturacion! (id: %s)', invoice.id)
            return 'end'

        contacts_entries = list(set([c.contact for c
                in entry_invoice_contacts]))
        contacts_invoice = list(set([c.contact for c
                in invoice.invoice_contacts]))
        to_create = []
        for contact in contacts_entries:
            if contact not in contacts_invoice:
                invoice_contact = InvoiceContacts(
                    invoice=invoice,
                    contact=contact,
                    )
                to_create.append(invoice_contact)
        if not to_create:
            logger.info('transition_populate():WARN:No se encontraron '
                    'nuevos contactos para agregar. (id: %s)', invoice.id)
            return 'end'
        InvoiceContacts.save(to_create)

        tt = round(time() - t1, 2)  # DEBUG
        logger.info('transition_populate():END:Agregado(s) %d contacto(s) '
                'en %s segundos. (id: %s)', len(to_create), tt, invoice.id)
        return 'end'


class SendOfInvoice(Wizard):
    'Send Of Invoice'
    __name__ = 'account.invoice.send_invoice'

    start = StateTransition()

    def transition_start(self):
        logger.info('SendOfInvoice:transition_start():INIT')
        Invoice = Pool().get('account.invoice')

        clean_invoice_report_cache = False  # TODO: HARDCODE!
        for active_id in Transaction().context['active_ids']:
            invoice = Invoice(active_id)
            if (invoice.type != 'out' or
                    invoice.state not in {'posted', 'paid'}):
                continue
            if not invoice.no_send_invoice:
                if clean_invoice_report_cache:
                    invoice.invoice_report_cache = None
                    invoice.invoice_report_format = None
                    invoice.save()
                logger.info('SendOfInvoice:transition_start():'
                        'Factura %s (id: %s)', invoice.number, invoice.id)
                invoice.print_invoice()
                invoice.print_invoice_service()
                if not invoice.mail_send_invoice():
                    logger.error('SendOfInvoice:transition_start():'
                            'Factura %s:Envio fallido!', invoice.number)
                    continue
                logger.info('SendOfInvoice:transition_start():'
                        'Factura %s:Envio exitoso.', invoice.number)
                invoice.sent = True
                invoice.sent_date = datetime.now()
                invoice.save()
        logger.info('SendOfInvoice:transition_start():END')
        return 'end'


class ForceReadyToInvoiceStart(ModelView):
    'Force Ready To Invoice'
    __name__ = 'account.invoice.line.force_ready_to_invoice.start'

    reason = fields.Char('Reason for Ready to invoice', required=True)


class ForceReadyToInvoice(Wizard):
    'Force Ready To Invoice'
    __name__ = 'account.invoice.line.force_ready_to_invoice'

    start = StateView('account.invoice.line.force_ready_to_invoice.start',
        'lims_account_invoice.invoice_line_force_ready_to_invoice_start'
        '_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Force', 'force', 'tryton-ok', default=True),
            ])
    force = StateTransition()

    def transition_force(self):
        InvoiceLine = Pool().get('account.invoice.line')

        lines = InvoiceLine.search([
            ('id', 'in', Transaction().context['active_ids']),
            ('lims_ready_to_invoice', '!=', True),
            ])
        if lines:
            InvoiceLine.write(lines, {
                'lims_ready_to_invoice': True,
                'lims_ready_to_invoice_reason': self.start.reason,
                'lims_ready_to_invoice_uid': Transaction().user,
                })
        return 'end'

    def end(self):
        return 'reload'


class CreateInvoiceStart(ModelView):
    'Create Invoice'
    __name__ = 'account.invoice.line.create_invoice.start'


class CreateInvoice(Wizard):
    'Create Invoice'
    __name__ = 'account.invoice.line.create_invoice'

    start = StateView('account.invoice.line.create_invoice.start',
        'lims_account_invoice.invoice_line_create_invoice_start'
        '_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Create', 'create_', 'tryton-ok', default=True),
            ])
    create_ = StateAction('account_invoice.act_invoice_form')

    def do_create_(self, action):
        invoice_ids = self.create_invoice()
        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', 'in', invoice_ids),
            ])
        return action, {}

    def create_invoice(self):
        pool = Pool()
        InvoiceLine = pool.get('account.invoice.line')
        Invoice = pool.get('account.invoice')
        Company = pool.get('company.company')

        invoices = defaultdict(list)
        lines = InvoiceLine.search([
            ('id', 'in', Transaction().context['active_ids']),
            ('invoice', '=', None),
            ('lims_ready_to_invoice', '=', True),
            ])
        for line in lines:
            invoices[line.party].append(line)

        company = Company(Transaction().context.get('company'))

        res = []
        for party, lines in invoices.items():
            invoice = Invoice(
                company=company,
                type='out',
                party=party,
                currency=company.currency,
                )
            invoice.on_change_type()
            invoice.on_change_party()
            invoice.lines = lines
            invoice.save()
            invoice.update_taxes()
            res.append(invoice.id)
        return res

    def end(self):
        return 'reload'
