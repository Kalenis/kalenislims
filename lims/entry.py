# -*- coding: utf-8 -*-
# This file is part of lims module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import logging
from datetime import datetime
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from trytond.model import Workflow, ModelView, ModelSQL, fields, Unique
from trytond.wizard import Wizard, StateTransition, StateView, StateReport, \
    Button
from trytond.pool import Pool
from trytond.pyson import Eval, Equal, Bool, Not
from trytond.transaction import Transaction
from trytond.tools import get_smtp_server
from trytond.config import config
from trytond.report import Report
from trytond.rpc import RPC

__all__ = ['Entry', 'EntryInvoiceContact', 'EntryReportContact',
    'EntryAcknowledgmentContact', 'EntrySuspensionReason',
    'EntryDetailAnalysis', 'ForwardAcknowledgmentOfReceipt',
    'ChangeInvoicePartyStart', 'ChangeInvoicePartyError', 'ChangeInvoiceParty',
    'PrintAcknowledgmentOfReceipt', 'AcknowledgmentOfReceipt', 'EntryDetail',
    'EntryLabels']

# Genshi fix: https://genshi.edgewall.org/ticket/582
from genshi.template.astutil import ASTCodeGenerator, ASTTransformer
if not hasattr(ASTCodeGenerator, 'visit_NameConstant'):
    def visit_NameConstant(self, node):
        if node.value is None:
            self._write('None')
        elif node.value is True:
            self._write('True')
        elif node.value is False:
            self._write('False')
        else:
            raise Exception("Unknown NameConstant %r" % (node.value,))
    ASTCodeGenerator.visit_NameConstant = visit_NameConstant
if not hasattr(ASTTransformer, 'visit_NameConstant'):
    # Re-use visit_Name because _clone is deleted
    ASTTransformer.visit_NameConstant = ASTTransformer.visit_Name


class Entry(Workflow, ModelSQL, ModelView):
    'Entry'
    __name__ = 'lims.entry'
    _rec_name = 'number'

    number = fields.Char('Number', select=True, readonly=True)
    create_date2 = fields.Function(fields.DateTime('Create Date'),
       'get_create_date2', searcher='search_create_date2')
    date = fields.DateTime('Date')
    date2 = fields.Function(fields.Date('Date'), 'get_date',
        searcher='search_date')
    party = fields.Many2One('party.party', 'Party', required=True,
        states={'readonly': Eval('state') != 'draft'}, depends=['state'])
    invoice_party = fields.Many2One('party.party', 'Invoice party',
        domain=[('id', 'in', Eval('invoice_party_domain'))],
        depends=['invoice_party_domain', 'state'], required=True,
        states={'readonly': Eval('state') != 'draft'})
    invoice_party_view = fields.Function(fields.Many2One('party.party',
        'Invoice party'), 'get_views_field',
        searcher='search_views_field')
    invoice_party_domain = fields.Function(fields.Many2Many('party.party',
        None, None, 'Invoice party domain'),
        'on_change_with_invoice_party_domain')
    invoice_contacts = fields.One2Many('lims.entry.invoice_contacts',
        'entry', 'Invoice contacts')
    report_contacts = fields.One2Many('lims.entry.report_contacts',
        'entry', 'Report contacts')
    acknowledgment_contacts = fields.One2Many(
        'lims.entry.acknowledgment_contacts', 'entry',
        'Acknowledgment contacts')
    carrier = fields.Many2One('carrier', 'Carrier')
    package_type = fields.Many2One('lims.packaging.type', 'Package type')
    package_state = fields.Many2One('lims.packaging.integrity',
        'Package state')
    packages_quantity = fields.Integer('Packages quantity')
    email_report = fields.Boolean('Email report')
    single_sending_report = fields.Boolean('Single sending of report')
    english_report = fields.Boolean('English report')
    no_acknowledgment_of_receipt = fields.Boolean(
        'No acknowledgment of receipt')
    samples = fields.One2Many('lims.sample', 'entry', 'Samples',
        context={
            'entry': Eval('id'), 'party': Eval('party'),
            }, depends=['party'])
    invoice_comments = fields.Text('Invoice comments')
    report_comments = fields.Text('Report comments', translate=True)
    transfer_comments = fields.Text('Transfer comments')
    comments = fields.Text('Comments')
    pending_reason = fields.Many2One('lims.entry.suspension.reason',
        'Pending reason', states={
            'invisible': Not(Bool(Equal(Eval('state'), 'pending'))),
            'required': Bool(Equal(Eval('state'), 'pending')),
            }, depends=['state'])
    state = fields.Selection([
        ('draft', 'Draft'),
        ('ongoing', 'Ongoing'),
        ('pending', 'Administration pending'),
        ('closed', 'Closed'),
        ], 'State', required=True, readonly=True)
    state_string = state.translated('state')
    ack_report_cache = fields.Binary('Acknowledgment report cache',
        readonly=True,
        file_id='ack_report_cache_id', store_prefix='ack_report')
    ack_report_cache_id = fields.Char('Acknowledgment report cache ID',
        readonly=True)
    ack_report_format = fields.Char('Acknowledgment report format',
        readonly=True)
    confirmed = fields.Function(fields.Boolean('Confirmed'), 'get_confirmed')
    sent_date = fields.DateTime('Sent date', readonly=True)
    result_cron = fields.Selection([
        ('', ''),
        ('failed_print', 'Failed to print'),
        ('failed_send', 'Failed to send'),
        ('sent', 'Sent'),
        ], 'Result cron', sort=False, readonly=True)
    icon = fields.Function(fields.Char("Icon"), 'get_icon')

    @classmethod
    def __setup__(cls):
        super(Entry, cls).__setup__()
        cls._order.insert(0, ('number', 'DESC'))
        cls._transitions |= set((
            ('draft', 'ongoing'),
            ('draft', 'pending'),
            ('pending', 'ongoing'),
            ('ongoing', 'closed'),
            ))
        cls._buttons.update({
            'create_sample': {
                'invisible': ~Eval('state').in_(['draft']),
                },
            'confirm': {
                'invisible': ~Eval('state').in_(['draft', 'pending']),
                },
            'on_hold': {
                'invisible': ~Eval('state').in_(['draft']),
                },
            })
        cls._error_messages.update({
            'no_entry_sequence': ('There is no entry sequence for '
                'the work year "%s".'),
            'delete_entry': ('You can not delete entry "%s" because '
                'it is not in draft state'),
            'not_fraction': ('You can not confirm entry "%s" because '
                'has not fractions'),
            'missing_entry_contacts': ('Missing contacts in entry "%s"'),
            'enac_acredited': ('The analysis marked with * are not '
                'covered by the Accreditation.'),
            'english_report': ('Do not forget to load the translations '
                'into English'),
            })

    @staticmethod
    def default_date():
        return datetime.now()

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

    @staticmethod
    def default_result_cron():
        return ''

    @staticmethod
    def default_state():
        return 'draft'

    def get_date(self, name):
        pool = Pool()
        Company = pool.get('company.company')

        date = self.date
        if not date:
            return None
        company_id = Transaction().context.get('company')
        if company_id:
            date = Company(company_id).convert_timezone_datetime(date)
        return date.date()

    def get_create_date2(self, name):
        return self.create_date.replace(microsecond=0)

    @classmethod
    def search_date(cls, name, clause):
        pool = Pool()
        Company = pool.get('company.company')
        cursor = Transaction().connection.cursor()

        timezone = None
        company_id = Transaction().context.get('company')
        if company_id:
            timezone = Company(company_id).timezone
        timezone_datetime = 'date::timestamp AT TIME ZONE \'UTC\''
        if timezone:
            timezone_datetime += ' AT TIME ZONE \'' + timezone + '\''

        operator_ = clause[1:2][0]
        cursor.execute('SELECT id '
                'FROM "' + cls._table + '" '
                'WHERE (' + timezone_datetime + ')::date ' +
                operator_ + ' %s::date', clause[2:3])
        return [('id', 'in', [x[0] for x in cursor.fetchall()])]

    @classmethod
    def search_create_date2(cls, name, clause):
        cursor = Transaction().connection.cursor()
        operator_ = clause[1:2][0]
        cursor.execute('SELECT id '
                'FROM "' + cls._table + '" '
                'WHERE create_date' + operator_ + ' %s',
                clause[2:3])
        return [('id', 'in', [x[0] for x in cursor.fetchall()])]

    @fields.depends('party', 'invoice_party', 'invoice_contacts',
        'report_contacts', 'acknowledgment_contacts')
    def on_change_party(self):
        pool = Pool()
        ReportContacts = pool.get('lims.entry.report_contacts')
        AcknowledgmentContacts = pool.get('lims.entry.acknowledgment_contacts')

        email = False
        single_sending = False
        english = False
        no_ack = False
        invoice_contacts = []
        a_report_contacts = []
        report_contacts = []
        a_acknowledgment_contacts = []
        acknowledgment_contacts = []
        parties = []
        if self.party:
            parties.append(self.party.id)
        if self.invoice_party:
            parties.append(self.invoice_party.id)

        if self.invoice_contacts:
            for c in self.invoice_contacts:
                if c.contact.party.id in parties:
                    invoice_contacts.append(c)
        if self.report_contacts:
            for c in self.report_contacts:
                if c.contact.party.id in parties:
                    report_contacts.append(c)
                    a_report_contacts.append(c.contact)
        if self.acknowledgment_contacts:
            for c in self.acknowledgment_contacts:
                if c.contact.party.id in parties:
                    acknowledgment_contacts.append(c)
                    a_acknowledgment_contacts.append(c.contact)

        if self.party:
            email = self.party.email_report
            single_sending = self.party.single_sending_report
            english = self.party.english_report
            no_ack = self.party.no_acknowledgment_of_receipt
            if self.party.addresses:
                for c in self.party.addresses:
                    if (c.report_contact_default and c not
                            in a_report_contacts):
                        value = ReportContacts(**ReportContacts.default_get(
                            list(ReportContacts._fields.keys())))
                        value.contact = c
                        report_contacts.append(value)
                    if (c.acknowledgment_contact_default and c not
                            in a_acknowledgment_contacts):
                        value = AcknowledgmentContacts(
                            **AcknowledgmentContacts.default_get(
                                list(AcknowledgmentContacts._fields.keys())))
                        value.contact = c
                        acknowledgment_contacts.append(value)

        self.email_report = email
        self.single_sending_report = single_sending
        self.english_report = english
        self.no_acknowledgment_of_receipt = no_ack
        self.invoice_contacts = invoice_contacts
        self.report_contacts = report_contacts
        self.acknowledgment_contacts = acknowledgment_contacts
        if self.party and not self.invoice_party:
            invoice_party_domain = self.on_change_with_invoice_party_domain()
            if len(invoice_party_domain) == 1:
                self.invoice_party = invoice_party_domain[0]
                self.on_change_invoice_party()

    @fields.depends('party', 'invoice_party', 'invoice_contacts',
        'report_contacts', 'acknowledgment_contacts')
    def on_change_invoice_party(self):
        pool = Pool()
        InvoiceContacts = pool.get('lims.entry.invoice_contacts')

        a_invoice_contacts = []
        invoice_contacts = []
        report_contacts = []
        acknowledgment_contacts = []
        parties = []
        if self.party:
            parties.append(self.party.id)
        if self.invoice_party:
            parties.append(self.invoice_party.id)

        if self.invoice_contacts:
            for c in self.invoice_contacts:
                if c.contact.party.id in parties:
                    invoice_contacts.append(c)
                    a_invoice_contacts.append(c.contact)
        if self.report_contacts:
            for c in self.report_contacts:
                if c.contact.party.id in parties:
                    report_contacts.append(c)
        if self.acknowledgment_contacts:
            for c in self.acknowledgment_contacts:
                if c.contact.party.id in parties:
                    acknowledgment_contacts.append(c)

        if self.invoice_party:
            if self.invoice_party.addresses:
                for c in self.invoice_party.addresses:
                    if (c.invoice_contact_default and c not
                            in a_invoice_contacts):
                        value = InvoiceContacts(**InvoiceContacts.default_get(
                            list(InvoiceContacts._fields.keys())))
                        value.contact = c
                        invoice_contacts.append(value)

        self.invoice_contacts = invoice_contacts
        self.report_contacts = report_contacts
        self.acknowledgment_contacts = acknowledgment_contacts

    @fields.depends('party')
    def on_change_with_invoice_party_domain(self, name=None):
        Config = Pool().get('lims.configuration')

        config_ = Config(1)
        parties = []
        if self.party:
            parties.append(self.party.id)
            if config_.invoice_party_relation_type:
                parties.extend([r.to.id for r in self.party.relations
                    if r.type == config_.invoice_party_relation_type])
        return parties

    @classmethod
    def get_views_field(cls, parties, names):
        result = {}
        for name in names:
            field_name = name[:-5]
            result[name] = {}
            for p in parties:
                field = getattr(p, field_name, None)
                result[name][p.id] = field.id if field else None
        return result

    @classmethod
    def search_views_field(cls, name, clause):
        return [(name[:-5],) + tuple(clause[1:])]

    @classmethod
    def create(cls, vlist):
        pool = Pool()
        LabWorkYear = pool.get('lims.lab.workyear')
        Sequence = pool.get('ir.sequence')

        workyear_id = LabWorkYear.find()
        workyear = LabWorkYear(workyear_id)
        sequence = workyear.get_sequence('entry')
        if not sequence:
            cls.raise_user_error('no_entry_sequence',
                (workyear.rec_name,))

        vlist = [x.copy() for x in vlist]
        for values in vlist:
            values['number'] = Sequence.get_id(sequence.id)
        return super(Entry, cls).create(vlist)

    @classmethod
    def copy(cls, entries, default=None):
        if default is None:
            default = {}

        new_entries = []
        for entry in entries:
            current_default = default.copy()
            current_default['state'] = 'draft'
            current_default['ack_report_cache'] = None
            current_default['ack_report_format'] = None
            current_default['sent_date'] = None
            current_default['result_cron'] = ''

            new_entry, = super(Entry, cls).copy([entry],
                default=current_default)
            new_entries.append(new_entry)
        return new_entries

    @classmethod
    @ModelView.button_action('lims.wiz_lims_create_sample')
    def create_sample(cls, entries):
        pass

    @classmethod
    @ModelView.button
    @Workflow.transition('ongoing')
    def confirm(cls, entries):
        for entry in entries:
            entry.check_contacts()
            entry.warn_english_report()
            entry._confirm()

    @classmethod
    def cron_acknowledgment_of_receipt(cls):
        '''
        Cron - Acknowledgment Of Receipt (Samples)
        '''
        logging.getLogger('lims').info(
                'Cron - Acknowledgment Of Receipt (Samples):INIT')
        pool = Pool()
        ForwardAcknowledgmentOfReceipt = pool.get(
            'lims.entry.acknowledgment.forward', type='wizard')
        Entry = pool.get('lims.entry')
        entries = Entry.search([
            ('result_cron', '!=', 'sent'),
            ('no_acknowledgment_of_receipt', '=', False),
            ('state', '=', 'ongoing'),
            ])
        session_id, _, _ = ForwardAcknowledgmentOfReceipt.create()
        acknowledgment_forward = ForwardAcknowledgmentOfReceipt(session_id)
        with Transaction().set_context(active_ids=[entry.id for entry
                in entries]):
            data = acknowledgment_forward.transition_start()
        if data:
            logging.getLogger('lims').info('data:%s' % data)  # debug
        logging.getLogger('lims').info(
                'Cron - Acknowledgment Of Receipt (Samples):END')

    @classmethod
    @ModelView.button
    def on_hold(cls, entries):
        pool = Pool()
        Fraction = pool.get('lims.fraction')
        EntrySuspensionReason = pool.get('lims.entry.suspension.reason')

        for entry in entries:
            entry.check_contacts()
            entry.warn_english_report()

        fractions = Fraction.search([
            ('entry', 'in', [e.id for e in entries]),
            ])
        if fractions:
            Fraction.check_divided_report(fractions)

        default_pending_reason = None
        reasons = EntrySuspensionReason.search([('by_default', '=', True)])
        if reasons:
            default_pending_reason = reasons[0].id
        cls.pending_reason.states['required'] = False
        cls.write(entries, {
            'state': 'pending',
            'pending_reason': default_pending_reason,
            })
        cls.pending_reason.states['required'] = (
            Bool(Equal(Eval('state'), 'pending')))

    @classmethod
    @Workflow.transition('closed')
    def close(cls, entries):
        pass

    def check_contacts(self):
        if (not self.invoice_contacts or
                not self.report_contacts or
                not self.acknowledgment_contacts):
            self.raise_user_error('missing_entry_contacts', (self.rec_name,))

    def warn_english_report(self):
        if self.english_report:
            self.raise_user_warning('lims_english_report@%s' %
                    self.number, 'english_report')

    def print_report(self):
        if self.ack_report_cache:
            return
        AcknowledgmentOfReceipt = Pool().get(
            'lims.entry.acknowledgment.report', type='report')
        success = False
        try:
            AcknowledgmentOfReceipt.execute([self.id], {})
            success = True
        except Exception:
            logging.getLogger('lims').error(
                'Unable to print report Acknowledgment of receipt for '
                'Entry:%s' % (self.number))
        return success

    def mail_acknowledgment_of_receipt(self):
        if not self.ack_report_cache:
            return

        from_addr = config.get('email', 'from')
        to_addrs = [c.contact.email for c in self.acknowledgment_contacts]
        if not (from_addr and to_addrs):
            return

        subject, body = self.subject_body()
        attachment_data = self.attachment()
        msg = self.create_msg(from_addr, to_addrs, subject,
            body, attachment_data)
        return self.send_msg(from_addr, to_addrs, msg)

    def subject_body(self):
        pool = Pool()
        Config = pool.get('lims.configuration')
        User = pool.get('res.user')
        Lang = pool.get('ir.lang')

        config = Config(1)

        lang = User(Transaction().user).language
        if not lang:
            lang, = Lang.search([
                    ('code', '=', 'en'),
                    ], limit=1)

        with Transaction().set_context(language=lang.code):
            subject = str('%s %s' % (config.mail_ack_subject,
                    self.number)).strip()
            body = str(config.mail_ack_body)

        return subject, body

    def attachment(self):
        data = {
            'content': self.ack_report_cache,
            'format': self.ack_report_format,
            'mimetype':
                self.ack_report_format == 'pdf' and 'pdf' or
                'vnd.oasis.opendocument.text',
            'filename':
                (str(self.number) + '.' +
                    str(self.ack_report_format)),
            'name': str(self.number),
            }
        return data

    def create_msg(self, from_addr, to_addrs, subject, body, attachment_data):
        if not to_addrs:
            return None

        msg = MIMEMultipart()
        msg['From'] = from_addr
        hidden = True  # TODO: HARDCODE!
        if not hidden:
            msg['To'] = ', '.join(to_addrs)
        msg['Subject'] = subject

        msg_body = MIMEBase('text', 'plain')
        msg_body.set_payload(body.encode('UTF-8'), 'UTF-8')
        msg.attach(msg_body)

        attachment = MIMEApplication(
            attachment_data['content'],
            Name=attachment_data['filename'], _subtype="pdf")
        attachment.add_header('content-disposition', 'attachment',
            filename=('utf-8', '', attachment_data['filename']))
        msg.attach(attachment)

        return msg

    def send_msg(self, from_addr, to_addrs, msg):
        to_addrs = list(set(to_addrs))
        success = False
        try:
            server = get_smtp_server()
            server.sendmail(from_addr, to_addrs, msg.as_string())
            server.quit()
            success = True
        except Exception:
            logging.getLogger('lims').error(
                'Unable to deliver mail for entry %s' % (self.number))
        return success

    def _confirm(self):
        Fraction = Pool().get('lims.fraction')
        fractions = Fraction.search([
            ('entry', '=', self.id),
            ('confirmed', '=', False),
            ], order=[
            ('sample', 'ASC'), ('id', 'ASC'),
            ])
        if not fractions:
            Company = Pool().get('company.company')
            companies = Company.search([])
            if self.party.id not in [c.party.id for c in companies]:
                self.raise_user_error('not_fraction', (self.rec_name,))
        Fraction.confirm(fractions)

    @classmethod
    def check_delete(cls, entries):
        for entry in entries:
            if entry.state != 'draft':
                cls.raise_user_error('delete_entry', (entry.rec_name,))

    @classmethod
    def delete(cls, entries):
        cls.check_delete(entries)
        super(Entry, cls).delete(entries)

    def get_confirmed(self, name=None):
        if not self.samples:
            return False
        for sample in self.samples:
            if not sample.fractions:
                return False
            for fraction in sample.fractions:
                if not fraction.confirmed:
                    return False
        return True

    @classmethod
    def order_create_date2(cls, tables):
        return cls.create_date.convert_order('create_date', tables, cls)

    def get_icon(self, name):
        if not self.confirmed:
            return 'lims-red'
        return 'lims-white'


class EntryInvoiceContact(ModelSQL, ModelView):
    'Entry Invoice Contact'
    __name__ = 'lims.entry.invoice_contacts'

    entry = fields.Many2One('lims.entry', 'Entry',
        ondelete='CASCADE', select=True, required=True)
    contact = fields.Many2One('party.address', 'Contact', required=True,
        domain=[
            ('party', 'in', [Eval('_parent_entry', {}).get('party'),
                Eval('_parent_entry', {}).get('invoice_party')]),
            ('invoice_contact', '=', True),
        ])


class EntryReportContact(ModelSQL, ModelView):
    'Entry Report Contact'
    __name__ = 'lims.entry.report_contacts'

    entry = fields.Many2One('lims.entry', 'Entry',
        ondelete='CASCADE', select=True, required=True)
    contact = fields.Many2One('party.address', 'Contact', required=True,
        domain=[
            ('party', 'in', [Eval('_parent_entry', {}).get('party'),
                Eval('_parent_entry', {}).get('invoice_party')]),
            ('report_contact', '=', True),
        ])


class EntryAcknowledgmentContact(ModelSQL, ModelView):
    'Entry Acknowledgment Contact'
    __name__ = 'lims.entry.acknowledgment_contacts'

    entry = fields.Many2One('lims.entry', 'Entry',
        ondelete='CASCADE', select=True, required=True)
    contact = fields.Many2One('party.address', 'Contact', required=True,
        domain=[
            ('party', 'in', [Eval('_parent_entry', {}).get('party'),
                Eval('_parent_entry', {}).get('invoice_party')]),
            ('acknowledgment_contact', '=', True),
        ])


class EntrySuspensionReason(ModelSQL, ModelView):
    'Entry Suspension Reason'
    __name__ = 'lims.entry.suspension.reason'
    _rec_name = 'description'

    code = fields.Char('Code', required=True)
    description = fields.Char('Description', required=True)
    by_default = fields.Boolean('By default')

    @classmethod
    def __setup__(cls):
        super(EntrySuspensionReason, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code),
                'Suspension reason code must be unique'),
            ]
        cls._error_messages.update({
            'default_suspension_reason':
                'There is already a default '
                'suspension reason',
            })

    @staticmethod
    def default_by_default():
        return False

    def get_rec_name(self, name):
        if self.code:
            return self.code + ' - ' + self.description
        else:
            return self.description

    @classmethod
    def search_rec_name(cls, name, clause):
        field = None
        for field in ('code', 'description'):
            records = cls.search([(field,) + tuple(clause[1:])], limit=1)
            if records:
                break
        if records:
            return [(field,) + tuple(clause[1:])]
        return [(cls._rec_name,) + tuple(clause[1:])]

    @classmethod
    def validate(cls, reasons):
        super(EntrySuspensionReason, cls).validate(reasons)
        for sr in reasons:
            sr.check_default()

    def check_default(self):
        if self.by_default:
            reasons = self.search([
                ('by_default', '=', True),
                ('id', '!=', self.id),
                ])
            if reasons:
                self.raise_user_error('default_suspension_reason')


class EntryDetailAnalysis(ModelSQL, ModelView):
    'Entry Detail Analysis'
    __name__ = 'lims.entry.detail.analysis'

    service = fields.Many2One('lims.service', 'Service', required=True,
        ondelete='CASCADE', select=True, readonly=True)
    service_view = fields.Function(fields.Many2One('lims.service',
        'Service', states={'invisible': Not(Bool(Eval('_parent_service')))}),
        'on_change_with_service_view')
    create_date2 = fields.Function(fields.DateTime('Create Date'),
       'get_create_date2', searcher='search_create_date2')
    fraction = fields.Function(fields.Many2One('lims.fraction', 'Fraction'),
        'get_service_field', searcher='search_service_field')
    sample = fields.Function(fields.Many2One('lims.sample', 'Sample'),
        'get_service_field', searcher='search_service_field')
    entry = fields.Function(fields.Many2One('lims.entry', 'Entry'),
        'get_service_field', searcher='search_service_field')
    party = fields.Function(fields.Many2One('party.party', 'Party'),
        'get_service_field', searcher='search_service_field')
    analysis = fields.Many2One('lims.analysis', 'Analysis', required=True,
        states={'readonly': True})
    analysis_type = fields.Function(fields.Selection([
        ('analysis', 'Analysis'),
        ('set', 'Set'),
        ('group', 'Group'),
        ], 'Type', sort=False),
        'on_change_with_analysis_type')
    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        states={'readonly': True})
    method = fields.Many2One('lims.lab.method', 'Method',
        states={'readonly': True})
    device = fields.Many2One('lims.lab.device', 'Device',
        states={'readonly': True})
    analysis_origin = fields.Char('Analysis origin',
        states={'readonly': True})
    confirmation_date = fields.Date('Confirmation date', readonly=True)
    report_grouper = fields.Integer('Report Grouper')
    results_report = fields.Function(fields.Many2One('lims.results_report',
        'Results Report'), 'get_results_report')
    report = fields.Boolean('Report', states={'readonly': True})
    state = fields.Selection([
        ('draft', 'Draft'),
        ('unplanned', 'Unplanned'),
        ('planned', 'Planned'),
        ('done', 'Done'),
        ('reported', 'Reported'),
        ], 'State', readonly=True)
    cie_min_value = fields.Char('Minimum value')
    cie_max_value = fields.Char('Maximum value')
    cie_fraction_type = fields.Function(fields.Boolean('Blind Sample'),
        'get_cie_fraction_type')

    @classmethod
    def __setup__(cls):
        super(EntryDetailAnalysis, cls).__setup__()
        cls._order.insert(0, ('service', 'DESC'))
        cls._error_messages.update({
            'delete_detail': ('You can not delete the analysis detail because '
                'its fraction is confirmed'),
            })

    @classmethod
    def copy(cls, details, default=None):
        if default is None:
            default = {}
        current_default = default.copy()
        current_default['confirmation_date'] = None
        return super(EntryDetailAnalysis, cls).copy(details,
            default=current_default)

    @classmethod
    def check_delete(cls, details):
        for detail in details:
            if detail.fraction and detail.fraction.confirmed:
                cls.raise_user_error('delete_detail')

    @classmethod
    def delete(cls, details):
        if Transaction().user != 0:
            cls.check_delete(details)
        super(EntryDetailAnalysis, cls).delete(details)

    @classmethod
    def create_notebook_lines(cls, details, fraction):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Typification = pool.get('lims.typification')
        Method = pool.get('lims.lab.method')
        WaitingTime = pool.get('lims.lab.method.results_waiting')
        AnalysisLaboratory = pool.get('lims.analysis-laboratory')
        Fraction = pool.get('lims.fraction')
        Notebook = pool.get('lims.notebook')
        Company = pool.get('company.company')

        lines_create = []

        for detail in details:
            cursor.execute('SELECT default_repetitions, '
                    'initial_concentration, final_concentration, start_uom, '
                    'end_uom, detection_limit, quantification_limit, '
                    'calc_decimals, report '
                'FROM "' + Typification._table + '" '
                'WHERE product_type = %s '
                    'AND matrix = %s '
                    'AND analysis = %s '
                    'AND method = %s '
                    'AND valid',
                (fraction.product_type.id, fraction.matrix.id,
                    detail.analysis.id, detail.method.id))
            typifications = cursor.fetchall()
            typification = (typifications[0] if len(typifications) == 1
                else None)
            if typification:
                repetitions = typification[0]
                initial_concentration = str(typification[1] or '')
                final_concentration = str(typification[2] or '')
                initial_unit = typification[3]
                final_unit = typification[4]
                detection_limit = str(typification[5])
                quantification_limit = str(typification[6])
                decimals = typification[7]
                report = typification[8]
            else:
                repetitions = 0
                initial_concentration = None
                final_concentration = None
                initial_unit = None
                final_unit = None
                detection_limit = None
                quantification_limit = None
                decimals = 2
                report = False

            cursor.execute('SELECT results_estimated_waiting '
                'FROM "' + WaitingTime._table + '" '
                'WHERE method = %s '
                    'AND party = %s',
                (detail.method.id, detail.party.id))
            res = cursor.fetchone()
            if res:
                results_estimated_waiting = res[0]
            else:
                cursor.execute('SELECT results_estimated_waiting '
                    'FROM "' + Method._table + '" '
                    'WHERE id = %s', (detail.method.id,))
                res = cursor.fetchone()
                results_estimated_waiting = res and res[0] or None

            cursor.execute('SELECT department '
                'FROM "' + AnalysisLaboratory._table + '" '
                'WHERE analysis = %s '
                    'AND laboratory = %s',
                    (detail.analysis.id, detail.laboratory.id))
            res = cursor.fetchone()
            department = res and res[0] or None

            for i in range(0, repetitions + 1):
                notebook_line = {
                    'analysis_detail': detail.id,
                    'service': detail.service.id,
                    'analysis': detail.analysis.id,
                    'analysis_origin': detail.analysis_origin,
                    'repetition': i,
                    'laboratory': detail.laboratory.id,
                    'method': detail.method.id,
                    'device': detail.device.id if detail.device else None,
                    'initial_concentration': initial_concentration,
                    'final_concentration': final_concentration,
                    'initial_unit': initial_unit,
                    'final_unit': final_unit,
                    'detection_limit': detection_limit,
                    'quantification_limit': quantification_limit,
                    'decimals': decimals,
                    'report': report,
                    'results_estimated_waiting': results_estimated_waiting,
                    'department': department,
                    }
                lines_create.append(notebook_line)

        if not lines_create:
            companies = Company.search([])
            if fraction.party.id not in [c.party.id for c in companies]:
                Fraction.raise_user_error('not_services',
                    (fraction.rec_name,))

        with Transaction().set_user(0):
            notebook = Notebook.search([
                ('fraction', '=', fraction.id),
                ])
            Notebook.write(notebook, {
                'lines': [('create', lines_create)],
                })

    @staticmethod
    def default_service_view():
        if (Transaction().context.get('service', 0) > 0):
            return Transaction().context.get('service')
        return None

    @fields.depends('service')
    def on_change_with_service_view(self, name=None):
        if self.service:
            return self.service.id
        return None

    @staticmethod
    def default_fraction():
        if (Transaction().context.get('fraction', 0) > 0):
            return Transaction().context.get('fraction')
        return None

    @staticmethod
    def default_sample():
        if (Transaction().context.get('sample', 0) > 0):
            return Transaction().context.get('sample')
        return None

    @staticmethod
    def default_entry():
        if (Transaction().context.get('entry', 0) > 0):
            return Transaction().context.get('entry')
        return None

    @staticmethod
    def default_party():
        if (Transaction().context.get('party', 0) > 0):
            return Transaction().context.get('party')
        return None

    @staticmethod
    def default_report_grouper():
        return 0

    @staticmethod
    def default_report():
        return True

    @fields.depends('analysis')
    def on_change_with_analysis_type(self, name=None):
        if self.analysis:
            return self.analysis.type
        return ''

    @classmethod
    def get_service_field(cls, details, names):
        result = {}
        for name in names:
            result[name] = {}
            for d in details:
                field = getattr(d.service, name, None)
                result[name][d.id] = field.id if field else None
        return result

    @classmethod
    def get_create_date2(cls, details, name):
        result = {}
        for d in details:
            result[d.id] = d.create_date.replace(microsecond=0)
        return result

    @classmethod
    def search_create_date2(cls, name, clause):
        cursor = Transaction().connection.cursor()
        operator_ = clause[1:2][0]
        cursor.execute('SELECT id '
                'FROM "' + cls._table + '" '
                'WHERE create_date' + operator_ + ' %s',
                clause[2:3])
        return [('id', 'in', [x[0] for x in cursor.fetchall()])]

    @classmethod
    def search_service_field(cls, name, clause):
        return [('service.' + name,) + tuple(clause[1:])]

    @classmethod
    def order_create_date2(cls, tables):
        return cls.create_date.convert_order('create_date', tables, cls)

    def _order_service_field(name):
        def order_field(tables):
            Service = Pool().get('lims.service')
            field = Service._fields[name]
            table, _ = tables[None]
            service_tables = tables.get('service')
            if service_tables is None:
                service = Service.__table__()
                service_tables = {
                    None: (service, service.id == table.service),
                    }
                tables['service'] = service_tables
            return field.convert_order(name, service_tables, Service)
        return staticmethod(order_field)
    # Redefine convert_order function with 'order_%s' % field
    order_fraction = _order_service_field('fraction')
    order_sample = _order_service_field('sample')
    order_entry = _order_service_field('entry')
    order_party = _order_service_field('party')

    @classmethod
    def get_results_report(cls, details, name):
        cursor = Transaction().connection.cursor()
        NotebookLine = Pool().get('lims.notebook.line')

        result = {}
        for d in details:
            cursor.execute('SELECT results_report '
                'FROM "' + NotebookLine._table + '" '
                'WHERE analysis_detail = %s '
                    'AND results_report IS NOT NULL '
                'ORDER BY id ASC LIMIT 1',
                (d.id,))
            value = cursor.fetchone()
            result[d.id] = value[0] if value else None
        return result

    @staticmethod
    def default_state():
        return 'draft'

    def get_cie_fraction_type(self, name=None):
        if (self.service and self.service.fraction and
                self.service.fraction.cie_fraction_type and
                not self.service.fraction.cie_original_fraction):
            return True
        return False

    @classmethod
    def view_attributes(cls):
        return super(EntryDetailAnalysis, cls).view_attributes() + [
            ('//group[@id="cie"]', 'states', {
                    'invisible': ~Eval('cie_fraction_type'),
                    })]

    @classmethod
    def write(cls, *args):
        super(EntryDetailAnalysis, cls).write(*args)
        actions = iter(args)
        for details, vals in zip(actions, actions):
            change_cie_data = False
            for field in ('cie_min_value', 'cie_max_value'):
                if vals.get(field):
                    change_cie_data = True
                    break
            if change_cie_data:
                for detail in details:
                    if (detail.service and detail.service.fraction and
                            detail.service.fraction.confirmed):
                        detail.update_cie_data()

    def update_cie_data(self):
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        BlindSample = pool.get('lims.blind_sample')

        nlines = NotebookLine.search([
            ('analysis_detail', '=', self.id),
            ])
        if nlines:
            blind_samples = BlindSample.search([
                ('line', 'in', [nl.id for nl in nlines]),
                ])
            if blind_samples:
                BlindSample.write(blind_samples, {
                    'min_value': self.cie_min_value,
                    'max_value': self.cie_max_value,
                    })


class ForwardAcknowledgmentOfReceipt(Wizard):
    'Forward Acknowledgment of Samples Receipt'
    __name__ = 'lims.entry.acknowledgment.forward'

    start = StateTransition()

    def transition_start(self):
        Entry = Pool().get('lims.entry')

        for active_id in Transaction().context['active_ids']:
            with Transaction().set_context(_check_access=False):
                entry = Entry(active_id)
            if entry.state != 'ongoing':
                continue
            if not entry.no_acknowledgment_of_receipt:
                printable = False
                cie_entry = False
                for sample in entry.samples:
                    if not sample.fractions:
                        break
                    for fraction in sample.fractions:
                        if fraction.cie_fraction_type:
                            cie_entry = True
                            break
                        if (fraction.confirmed and fraction.services):
                            printable = True
                            break
                if printable:
                    entry.ack_report_cache = None
                    entry.ack_report_format = None
                    entry.save()
                    if not entry.print_report():
                        entry.result_cron = 'failed_print'
                        entry.save()
                        continue
                    if not entry.mail_acknowledgment_of_receipt():
                        entry.result_cron = 'failed_send'
                        entry.save()
                        continue
                    entry.result_cron = 'sent'
                    entry.sent_date = datetime.now()
                    entry.save()
                if cie_entry:
                    entry.result_cron = 'sent'
                    entry.sent_date = datetime.now()
                    entry.save()
        return 'end'


class ChangeInvoicePartyStart(ModelView):
    'Change Invoice Party'
    __name__ = 'lims.entry.change_invoice_party.start'

    invoice_party_domain = fields.Many2Many('party.party', None, None,
        'Invoice party domain')
    invoice_party = fields.Many2One('party.party', 'Invoice party',
        domain=[('id', 'in', Eval('invoice_party_domain'))],
        depends=['invoice_party_domain'], required=True)


class ChangeInvoicePartyError(ModelView):
    'Change Invoice Party'
    __name__ = 'lims.entry.change_invoice_party.error'


class ChangeInvoiceParty(Wizard):
    'Change Invoice Party'
    __name__ = 'lims.entry.change_invoice_party'

    start_state = 'check'
    check = StateTransition()
    error = StateView('lims.entry.change_invoice_party.error',
        'lims.lims_change_invoice_party_error_view_form', [
            Button('Cancel', 'end', 'tryton-cancel', default=True),
            ])
    start = StateView('lims.entry.change_invoice_party.start',
        'lims.lims_change_invoice_party_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Change', 'change', 'tryton-ok', default=True),
            ])
    change = StateTransition()

    def transition_check(self):
        pool = Pool()
        Entry = pool.get('lims.entry')
        Service = pool.get('lims.service')
        InvoiceLine = pool.get('account.invoice.line')

        entry = Entry(Transaction().context['active_id'])

        if entry.state == 'draft':
            return 'end'

        services = Service.search([
            ('entry', '=', entry.id),
            ])
        if not services:
            return 'end'

        for s in services:
            invoiced_lines = InvoiceLine.search([
                ('origin', '=', 'lims.service,%s' % s.id),
                ('invoice', '!=', None),
                ])
            if invoiced_lines:
                return 'error'

        return 'start'

    def default_start(self, fields):
        Entry = Pool().get('lims.entry')

        entry = Entry(Transaction().context['active_id'])

        invoice_party_domain = entry.on_change_with_invoice_party_domain()
        invoice_party = None
        if len(invoice_party_domain) == 1:
            invoice_party = invoice_party_domain[0]
        return {
            'invoice_party_domain': invoice_party_domain,
            'invoice_party': invoice_party,
            }

    def transition_change(self):
        pool = Pool()
        Entry = pool.get('lims.entry')
        Service = pool.get('lims.service')
        InvoiceLine = pool.get('account.invoice.line')
        InvoiceContacts = pool.get('lims.entry.invoice_contacts')
        ReportContacts = pool.get('lims.entry.report_contacts')
        AcknowledgmentContacts = pool.get('lims.entry.acknowledgment_contacts')

        entry = Entry(Transaction().context['active_id'])

        lines_to_change = []
        services = Service.search([
            ('entry', '=', entry.id),
            ])
        for s in services:
            invoiced_lines = InvoiceLine.search([
                ('origin', '=', 'lims.service,%s' % s.id),
                ])
            for l in invoiced_lines:
                line = InvoiceLine(l.id)
                line.party = self.start.invoice_party.id
                lines_to_change.append(line)
        if lines_to_change:
            InvoiceLine.save(lines_to_change)

        if entry.invoice_party != entry.party:
            entry_contacts = InvoiceContacts.search([
                ('entry', '=', entry.id),
                ('contact.party', '=', entry.invoice_party.id),
                ])
            if entry_contacts:
                InvoiceContacts.delete(entry_contacts)
            entry_contacts = ReportContacts.search([
                ('entry', '=', entry.id),
                ('contact.party', '=', entry.invoice_party.id),
                ])
            if entry_contacts:
                ReportContacts.delete(entry_contacts)
            entry_contacts = AcknowledgmentContacts.search([
                ('entry', '=', entry.id),
                ('contact.party', '=', entry.invoice_party.id),
                ])
            if entry_contacts:
                AcknowledgmentContacts.delete(entry_contacts)
        entry.invoice_party = self.start.invoice_party.id
        entry.save()

        return 'end'


class PrintAcknowledgmentOfReceipt(Wizard):
    'Print Acknowledgment of Samples Receipt'
    __name__ = 'lims.entry.acknowledgment.print'

    start = StateTransition()
    print_ = StateReport('lims.entry.acknowledgment.report')

    def transition_start(self):
        Entry = Pool().get('lims.entry')
        data_ids = Transaction().context['active_ids'][:]
        while len(data_ids) > 0:
            data_id = data_ids.pop()
            with Transaction().set_context(_check_access=False):
                entry = Entry(data_id)
            if entry.state == 'ongoing':
                printable = False
                for sample in entry.samples:
                    if not sample.fractions:
                        continue
                    for fraction in sample.fractions:
                        if (fraction.confirmed and fraction.services and not
                                fraction.cie_fraction_type):
                            printable = True
                            break
                if printable:
                    return 'print_'
                else:
                    Transaction().context['active_ids'].remove(data_id)
            else:
                Transaction().context['active_ids'].remove(data_id)
        return 'end'

    def do_print_(self, action):
        data = {}
        data['id'] = Transaction().context['active_ids'].pop()
        data['ids'] = [data['id']]
        return action, data

    def transition_print_(self):
        if Transaction().context.get('active_ids'):
            return 'start'
        return 'end'


class AcknowledgmentOfReceipt(Report):
    'Acknowledgment of Samples Receipt'
    __name__ = 'lims.entry.acknowledgment.report'

    @classmethod
    def __setup__(cls):
        super(AcknowledgmentOfReceipt, cls).__setup__()
        cls.__rpc__['execute'] = RPC(False)

    @classmethod
    def execute(cls, ids, data):
        Entry = Pool().get('lims.entry')

        result = super(AcknowledgmentOfReceipt, cls).execute(ids, data)
        entry = Entry(ids[0])

        if entry.ack_report_cache:
            result = (entry.ack_report_format,
                entry.ack_report_cache) + result[2:]
        else:
            entry.ack_report_format, entry.ack_report_cache = result[:2]
            entry.save()
        return result

    @classmethod
    def get_context(cls, records, data):
        pool = Pool()
        Company = pool.get('company.company')
        Service = pool.get('lims.service')
        Entry = pool.get('lims.entry')

        report_context = super(AcknowledgmentOfReceipt, cls).get_context(
            records, data)
        if 'id' in data:
            entry = Entry(data['id'])
        else:
            entry = records[0]

        company = Company(Transaction().context.get('company'))
        report_context['company'] = company

        samples = []
        record = {
            'party': entry.party.rec_name,
            'samples': samples,
            }

        for sample in entry.samples:
            if not sample.fractions:
                continue
            confirmed = False
            for fraction in sample.fractions:
                if (fraction.confirmed and fraction.services and not
                        fraction.cie_fraction_type):
                    confirmed = True
                    break
            if not confirmed:
                continue
            services = {}
            sample_data = {
                'label': sample.label,
                'producer': (sample.producer.rec_name if sample.producer
                    else ''),
                'date': sample.date,
                'product_type': sample.product_type.rec_name,
                'client_description': sample.sample_client_description,
                'number': sample.number,
                'services': services,
                }
            samples.append(sample_data)

            with Transaction().set_context(_check_access=False):
                services_obj = Service.search([
                    ('sample', '=', sample.id),
                    ('fraction.confirmed', '=', True),
                    ('fraction.cie_fraction_type', '=', False),
                    ])
            for service in services_obj:
                if (service.analysis.type == 'analysis' and not
                        cls.get_analysis_reportable(sample.product_type,
                        sample.matrix, service.analysis, service.method)):
                    continue
                if service.analysis.id not in services:
                    s_methods = {}
                    services[service.analysis.id] = {
                        'code': service.analysis.code,
                        'name': service.analysis.description,
                        'methods': s_methods,
                        }

                    if service.analysis.type == 'analysis':
                        s_methods[service.method.id] = {
                            'method': service.method,
                            'analysis': [],
                            'enac': False,
                            }
                        acredited = cls.get_accreditation(
                            sample.product_type,
                            sample.matrix,
                            service.analysis,
                            service.method)
                        if acredited:
                            s_methods[service.method.id]['enac'] = True

                    else:
                        ia_methods = cls.get_included_analysis(
                            service.analysis.id, service.fraction.id)
                        for ia in ia_methods:
                            if ia['method_id'] not in s_methods:
                                s_methods[ia['method_id']] = {
                                    'method': ia['method'],
                                    'analysis': [],
                                    'enac': False,
                                    }
                            s_methods[ia['method_id']]['analysis'].append({
                                'acredited': ia['acredited'],
                                'analysis': ia['analysis'],
                                })
                            if (not s_methods[ia['method_id']]['enac'] and
                                    ia['acredited']):
                                s_methods[ia['method_id']]['enac'] = True

                    for v in s_methods.values():
                        if v['enac']:
                            v['enac_label'] = (Entry.raise_user_error(
                                'enac_acredited', raise_exception=False))
                        else:
                            v['enac_label'] = ''
                        sorted_analysis = sorted(v['analysis'],
                            key=lambda x: x['analysis'].description)
                        v['analysis'] = sorted_analysis

        report_context['records'] = [record]
        return report_context

    @classmethod
    def get_included_analysis(cls, analysis_id, fraction_id):
        pool = Pool()
        AnalysisIncluded = pool.get('lims.analysis.included')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        childs = []
        included_analysis = AnalysisIncluded.search([
            ('analysis', '=', analysis_id),
            ])
        for analysis in included_analysis:
            if analysis.included_analysis.type == 'analysis':
                analysis_detail = EntryDetailAnalysis.search([
                    ('fraction', '=', fraction_id),
                    ('analysis', '=', analysis.included_analysis.id),
                    ])
                if analysis_detail:
                    analysis_detail = analysis_detail[0]
                    if cls.get_analysis_reportable(
                            analysis_detail.sample.product_type,
                            analysis_detail.sample.matrix,
                            analysis_detail.analysis,
                            analysis_detail.method):
                        childs.append({
                            'method_id': analysis_detail.method.id,
                            'method': analysis_detail.method,
                            'analysis': analysis.included_analysis,
                            'acredited': cls.get_accreditation(
                                analysis_detail.sample.product_type,
                                analysis_detail.sample.matrix,
                                analysis_detail.analysis,
                                analysis_detail.method),
                            })
            childs.extend(cls.get_included_analysis(
                analysis.included_analysis.id, fraction_id))
        return childs

    @classmethod
    def get_accreditation(cls, product_type, matrix, analysis, method):
        pool = Pool()
        Typification = pool.get('lims.typification')

        typifications = Typification.search([
            ('product_type', '=', product_type),
            ('matrix', '=', matrix),
            ('analysis', '=', analysis),
            ('method', '=', method),
            ('valid', '=', True),
            ])
        if typifications:
            if typifications[0].technical_scope_versions:
                for version in typifications[0].technical_scope_versions:
                    certification_type = (
                        version.technical_scope.certification_type)
                    if certification_type and certification_type.report:
                        return True
        return False

    @classmethod
    def get_analysis_reportable(cls, product_type, matrix, analysis, method):
        Typification = Pool().get('lims.typification')

        if analysis.behavior == 'additional':
            return False

        typifications = Typification.search([
            ('product_type', '=', product_type),
            ('matrix', '=', matrix),
            ('analysis', '=', analysis),
            ('method', '=', method),
            ('valid', '=', True),
            ])
        if typifications:
            return typifications[0].report
        return True


class EntryDetail(Report):
    'Entry Detail'
    __name__ = 'lims.entry.detail.report'

    @classmethod
    def get_context(cls, records, data):
        report_context = super(EntryDetail, cls).get_context(records, data)
        Company = Pool().get('company.company')

        company = Company(Transaction().context.get('company'))
        report_context['company'] = company

        return report_context


class EntryLabels(Report):
    'Entry Labels'
    __name__ = 'lims.entry.labels.report'

    @classmethod
    def get_context(cls, records, data):
        report_context = super(EntryLabels, cls).get_context(records, data)
        labels = []
        for entry in records:
            for sample in entry.samples:
                for fraction in sample.fractions:
                    for i in range(fraction.packages_quantity):
                        labels.append(fraction)
        report_context['labels'] = labels

        return report_context
