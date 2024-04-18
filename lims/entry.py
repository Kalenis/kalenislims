# -*- coding: utf-8 -*-
# This file is part of lims module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import logging
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sql import Literal

from trytond.model import Workflow, Model, ModelView, ModelSQL, fields, \
    Unique, Index
from trytond.wizard import Wizard, StateTransition, StateView, StateReport, \
    Button
from trytond.pool import Pool
from trytond.pyson import Eval, Equal, Bool, Not, If
from trytond.transaction import Transaction
from trytond.tools import get_smtp_server
from trytond.config import config as tconfig
from trytond.report import Report
from trytond.rpc import RPC
from trytond.exceptions import UserError, UserWarning
from trytond.i18n import gettext, lazy_gettext
from .analysis import ANALYSIS_TYPES

logger = logging.getLogger(__name__)

ENTRY_STATES = [
    ('draft', 'Draft'),
    ('cancelled', 'Cancelled'),
    ('ongoing', 'Ongoing'),
    ('pending', 'Administration pending'),
    ('finished', 'Finished'),
    ]


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

    number = fields.Char('Number', readonly=True)
    create_date2 = fields.Function(fields.DateTime('Create Date'),
       'get_create_date2', searcher='search_create_date2')
    date = fields.DateTime('Date')
    date2 = fields.Function(fields.Date('Date'), 'get_date',
        searcher='search_date')
    party = fields.Many2One('party.party', 'Party',
        states={
            'required': ~Eval('multi_party'),
            'invisible': Bool(Eval('multi_party')),
            'readonly': ((Eval('state') != 'draft')
                | (Eval('samples', [0]))),
            })
    invoice_party = fields.Many2One('party.party', 'Invoice party',
        states={
            'required': True,
            'readonly': Eval('state') != 'draft',
            },
        domain=[If(~Eval('multi_party'), ['OR',
            ('id', '=', Eval('invoice_party', -1)),
            ('id', 'in', Eval('invoice_party_domain'))], [])])
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
    single_sending_report = fields.Boolean(
        'Single sending of report per Sample')
    entry_single_sending_report = fields.Boolean(
        'Single sending of report per Entry')
    report_language = fields.Many2One('ir.lang',
        'Results Report Language', required=True,
        domain=[('translatable', '=', True)])
    no_acknowledgment_of_receipt = fields.Boolean(
        'No acknowledgment of receipt')
    samples = fields.One2Many('lims.sample', 'entry', 'Samples',
        readonly=True, context={'from_entry': True,
            'entry': Eval('id'), 'party': Eval('party')},
        depends={'party'})
    invoice_comments = fields.Text('Invoice comments')
    report_comments = fields.Text('Report comments', translate=True)
    transfer_comments = fields.Text('Transfer comments')
    comments = fields.Text('Comments')
    pending_reason = fields.Many2One('lims.entry.suspension.reason',
        'Pending reason', states={
            'invisible': Not(Bool(Equal(Eval('state'), 'pending'))),
            'required': Bool(Equal(Eval('state'), 'pending')),
            })
    cancellation_reason = fields.Many2One('lims.entry.cancellation.reason',
        'Cancellation reason', states={
            'invisible': Not(Bool(Equal(Eval('state'), 'cancelled'))),
            'required': Bool(Equal(Eval('state'), 'cancelled')),
            })
    cancellation_comments = fields.Text('Cancellation comments',
        states={'readonly': Eval('state') != 'cancelled'})
    state = fields.Selection(ENTRY_STATES, 'State',
        required=True, readonly=True)
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
    block_entry_confirmation = fields.Function(fields.Boolean(
        'Block Entry Confirmation'), 'get_block_entry_confirmation')
    multi_party = fields.Boolean('Multi Party', readonly=True)
    pre_assigned_samples = fields.Function(fields.Integer(
        'Pre-Assigned Samples'), 'get_pre_assigned_samples')
    contract_number = fields.Char('Contract Number')

    @classmethod
    def __setup__(cls):
        cls.number.search_unaccented = False
        cls.state.search_unaccented = False
        super().__setup__()
        cls._order.insert(0, ('number', 'DESC'))
        cls._transitions |= set((
            ('draft', 'cancelled'),
            ('draft', 'pending'),
            ('draft', 'ongoing'),
            ('pending', 'cancelled'),
            ('pending', 'ongoing'),
            ('ongoing', 'cancelled'),
            ('ongoing', 'finished'),
            ))
        cls._buttons.update({
            'pre_assign_sample': {
                'invisible': ~Eval('state').in_(['draft']),
                'depends': ['state'],
                },
            'create_sample': {
                'invisible': ~Eval('state').in_(['draft']),
                'depends': ['state'],
                },
            'confirm': {
                'invisible': ~Eval('state').in_(['draft', 'pending']),
                'readonly': Bool(Eval('block_entry_confirmation')),
                'depends': ['state', 'block_entry_confirmation'],
                },
            'on_hold': {
                'invisible': ~Eval('state').in_(['draft']),
                'depends': ['state'],
                },
            'cancel': {
                'invisible': ~Eval('state').in_(
                    ['draft', 'pending', 'ongoing']),
                'depends': ['state'],
                },
            })
        cls.__rpc__.update({
            'update_entries_state': RPC(readonly=False, instantiate=0),
            })
        t = cls.__table__()
        #cls._sql_indexes.update({
            #Index(t, (t.number, Index.Similarity())),
            #Index(t, (t.state, Index.Similarity())),
            #Index(t, (t.single_sending_report, Index.Equality())),
            #Index(t, (t.entry_single_sending_report, Index.Equality())),
            #Index(t, (t.multi_party, Index.Equality())),
            #})

    @classmethod
    def __register__(cls, module_name):
        entry_h = cls.__table_handler__(module_name)
        english_report_exist = entry_h.column_exist('english_report')
        super().__register__(module_name)
        if english_report_exist:
            cls._migrate_english_report()
            entry_h.drop_column('english_report')

    @classmethod
    def _migrate_english_report(cls):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Configuration = pool.get('lims.configuration')
        Lang = pool.get('ir.lang')

        entry_table = cls.__table__()
        configuration_table = Configuration.__table__()
        lang_table = Lang.__table__()

        cursor.execute(*configuration_table.select(
            configuration_table.results_report_language,
            where=Literal(True)))
        default_language = cursor.fetchone()
        if default_language:
            cursor.execute(*entry_table.update(
                [entry_table.report_language], [default_language[0]],
                where=(entry_table.english_report == Literal(False))))

        cursor.execute(*lang_table.select(
            lang_table.id,
            where=lang_table.code == Literal('en')))
        english_language = cursor.fetchone()
        if english_language:
            cursor.execute(*entry_table.update(
                [entry_table.report_language], [english_language[0]],
                where=(entry_table.english_report == Literal(True))))

    @staticmethod
    def default_multi_party():
        return Transaction().context.get('multi_party', False)

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
        Config = pool.get('lims.configuration')
        ReportContacts = pool.get('lims.entry.report_contacts')
        AcknowledgmentContacts = pool.get('lims.entry.acknowledgment_contacts')

        config_ = Config(1)

        report_language = None
        email = False
        single_sending = False
        entry_single_sending = False
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
            report_language = self.party.report_language
            email = self.party.email_report
            single_sending = self.party.single_sending_report
            entry_single_sending = self.party.entry_single_sending_report
            no_ack = self.party.no_acknowledgment_of_receipt

            if self.party.addresses:
                if config_.entry_default_contacts == 'party':
                    for c in self.party.addresses:
                        if (c.report_contact_default and c not
                                in a_report_contacts):
                            report_contacts.append(
                                ReportContacts(contact=c))
                        if (c.acknowledgment_contact_default and c not
                                in a_acknowledgment_contacts):
                            acknowledgment_contacts.append(
                                AcknowledgmentContacts(contact=c))

        if report_language:
            self.report_language = report_language
        self.email_report = email
        self.single_sending_report = single_sending
        self.entry_single_sending_report = entry_single_sending
        self.no_acknowledgment_of_receipt = no_ack

        self.invoice_contacts = invoice_contacts
        self.report_contacts = report_contacts
        self.acknowledgment_contacts = acknowledgment_contacts

        if not self.party:
            self.invoice_party = None
            self.on_change_invoice_party()
        elif not self.invoice_party:
            invoice_party_domain = self.on_change_with_invoice_party_domain()
            if len(invoice_party_domain) == 1:
                self.invoice_party = invoice_party_domain[0]
                self.on_change_invoice_party()

    @fields.depends('party', 'invoice_party', 'invoice_contacts',
        'report_contacts', 'acknowledgment_contacts')
    def on_change_invoice_party(self):
        pool = Pool()
        Config = pool.get('lims.configuration')
        InvoiceContacts = pool.get('lims.entry.invoice_contacts')
        ReportContacts = pool.get('lims.entry.report_contacts')
        AcknowledgmentContacts = pool.get('lims.entry.acknowledgment_contacts')

        config_ = Config(1)

        a_invoice_contacts = []
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
                    a_invoice_contacts.append(c.contact)
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

        if self.invoice_party:
            if self.invoice_party.addresses:
                if config_.entry_default_contacts == 'invoice_party':
                    for c in self.invoice_party.addresses:
                        if (c.invoice_contact_default and c not
                                in a_invoice_contacts):
                            invoice_contacts.append(
                                InvoiceContacts(contact=c))
                        if (c.report_contact_default and c not
                                in a_report_contacts):
                            report_contacts.append(
                                ReportContacts(contact=c))
                        if (c.acknowledgment_contact_default and c not
                                in a_acknowledgment_contacts):
                            acknowledgment_contacts.append(
                                AcknowledgmentContacts(contact=c))
                else:
                    for c in self.invoice_party.addresses:
                        if (c.invoice_contact_default and c not
                                in a_invoice_contacts):
                            invoice_contacts.append(
                                InvoiceContacts(contact=c))
        else:
            invoice_contacts = []
            if config_.entry_default_contacts == 'invoice_party':
                report_contacts = []
                acknowledgment_contacts = []

        self.invoice_contacts = invoice_contacts
        self.report_contacts = report_contacts
        self.acknowledgment_contacts = acknowledgment_contacts

    @fields.depends('party', '_parent_party.relations')
    def on_change_with_invoice_party_domain(self, name=None):
        Config = Pool().get('lims.configuration')
        config_ = Config(1)
        parties = []
        if self.party:
            parties.append(self.party.id)
            if config_.invoice_party_relation_type:
                parties.extend([r.to.id for r in self.party.relations
                    if r.type == config_.invoice_party_relation_type])
        return list(set(parties))

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

        workyear_id = LabWorkYear.find()
        workyear = LabWorkYear(workyear_id)
        sequence = workyear.get_sequence('entry')
        if not sequence:
            raise UserError(gettext('lims.msg_no_entry_sequence',
                work_year=workyear.rec_name))

        vlist = [x.copy() for x in vlist]
        for values in vlist:
            values['number'] = sequence.get()
            if values.get('party', None) is None:
                values['party'] = values['invoice_party']
        return super().create(vlist)

    @classmethod
    def write(cls, *args):
        Sample = Pool().get('lims.sample')
        super().write(*args)
        actions = iter(args)
        for entries, vals in zip(actions, actions):
            if 'party' in vals:
                single_party_entries = [e for e in entries
                    if not e.multi_party]
                Sample.write([s for e in single_party_entries
                    for s in e.samples],
                    {'party': vals.get('party')})
            if 'invoice_party' in vals:
                multi_party_entries = [e for e in entries
                    if e.multi_party]
                cls.write(multi_party_entries,
                    {'party': vals.get('invoice_party')})

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

            new_entry, = super().copy([entry],
                default=current_default)
            new_entries.append(new_entry)
        return new_entries

    @classmethod
    @ModelView.button_action('lims.wiz_lims_pre_assign_sample')
    def pre_assign_sample(cls, entries):
        pass

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
            entry.warn_foreign_report()
            entry._confirm()

    @classmethod
    def cron_acknowledgment_of_receipt(cls):
        '''
        Cron - Acknowledgment Of Receipt (Samples)
        '''
        logger.info('Cron - Acknowledgment Of Receipt (Samples): INIT')
        pool = Pool()
        Entry = pool.get('lims.entry')
        ForwardAcknowledgmentOfReceipt = pool.get(
            'lims.entry.acknowledgment.forward', type='wizard')

        entries = Entry.search([
            ('result_cron', '!=', 'sent'),
            ('no_acknowledgment_of_receipt', '=', False),
            ('state', '=', 'ongoing'),
            ])

        session_id, _, _ = ForwardAcknowledgmentOfReceipt.create()
        acknowledgment_forward = ForwardAcknowledgmentOfReceipt(session_id)
        with Transaction().set_context(active_ids=[entry.id
                for entry in entries]):
            data = acknowledgment_forward.transition_start()
            if data:
                logger.info('data: %s' % data)  # debug

        logger.info('Cron - Acknowledgment Of Receipt (Samples): END')

    @classmethod
    @ModelView.button
    def on_hold(cls, entries):
        pool = Pool()
        Fraction = pool.get('lims.fraction')
        EntrySuspensionReason = pool.get('lims.entry.suspension.reason')

        for entry in entries:
            entry.check_contacts()
            entry.warn_foreign_report()

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
    @ModelView.button
    def cancel(cls, entries):
        pool = Pool()
        EntryCancellationReason = pool.get('lims.entry.cancellation.reason')

        for entry in entries:
            entry.check_entry_cancellation()
            entry.cancel_entry()

        default_cancellation_reason = None
        reasons = EntryCancellationReason.search([('by_default', '=', True)])
        if reasons:
            default_cancellation_reason = reasons[0].id
        cls.cancellation_reason.states['required'] = False
        cls.write(entries, {
            'state': 'cancelled',
            'cancellation_reason': default_cancellation_reason,
            })
        cls.cancellation_reason.states['required'] = (
            Bool(Equal(Eval('state'), 'pending')))

    @classmethod
    @Workflow.transition('finished')
    def finish(cls, entries):
        pass

    def check_contacts(self):
        if (not self.invoice_contacts or
                not self.report_contacts or
                not self.acknowledgment_contacts):
            raise UserError(gettext(
                'lims.msg_missing_entry_contacts', entry=self.rec_name))

    def warn_foreign_report(self):
        pool = Pool()
        Config = pool.get('lims.configuration')
        Warning = pool.get('res.user.warning')

        default_language = Config(1).results_report_language
        if self.report_language != default_language:
            key = 'lims_foreign_report@%s' % self.number
            if Warning.check(key):
                raise UserWarning(key, gettext('lims.msg_foreign_report',
                    lang=self.report_language.name))

    def check_entry_cancellation(self):
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')

        if NotebookLine.search_count([
                ('service.fraction.sample.entry', '=', self.id),
                ('accepted', '=', True),
                ]) > 0:
            raise UserError(gettext(
                'lims.msg_entry_cancellation_analysis_accepted'))
        if NotebookLine.search_count([
                ('service.fraction.sample.entry', '=', self.id),
                ('start_date', '!=', None),
                ]) > 0:
            raise UserError(gettext(
                'lims.msg_entry_cancellation_analysis_planned'))

    def cancel_entry(self):
        pool = Pool()
        Sample = pool.get('lims.sample')
        Service = pool.get('lims.service')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        NotebookLine = pool.get('lims.notebook.line')

        with Transaction().set_user(0, set_context=True):
            services = Service.search([
                ('fraction.sample.entry', '=', self),
                ])
            if services:
                Service.write(services, {'annulled': True})

            details = EntryDetailAnalysis.search([
                ('service.fraction.sample.entry', '=', self),
                ])
            if details:
                EntryDetailAnalysis.write(details, {'state': 'annulled'})

            notebook_lines = NotebookLine.search([
                ('service.fraction.sample.entry', '=', self),
                ])
            if notebook_lines:
                NotebookLine.write(notebook_lines, {
                    'annulled': True,
                    'annulment_date': datetime.now(),
                    'accepted': False,
                    'acceptance_date': None,
                    'report': False,
                    })

            to_update = self.samples
            Sample.__queue__.update_samples_state(to_update)

    @classmethod
    def update_entries_state(cls, entry_ids):
        entries_states = ['ongoing', 'finished']
        entries_exclude = cls._get_update_entries_state_exclude()

        entries_to_save = []
        entries = cls.search([
            ('id', 'in', list(set(entry_ids) - set(entries_exclude))),
            ('state', 'in', entries_states),
            ])
        for entry in entries:
            state = 'finished'
            for sample in entry.samples:
                if sample.state != 'report_released':
                    state = 'ongoing'
                    break
            if entry.state != state:
                entry.state = state
                entries_to_save.append(entry)
        if entries_to_save:
            cls.save(entries_to_save)

    @classmethod
    def _get_update_entries_state_exclude(cls):
        pool = Pool()
        LabWorkYear = pool.get('lims.lab.workyear')

        res = []

        workyear_id = LabWorkYear.find()
        workyear = LabWorkYear(workyear_id)
        if workyear.default_entry_control:
            res.append(workyear.default_entry_control.id)
        return res

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
            logger.error(
                'Unable to print report Acknowledgment of receipt for '
                'Entry:%s' % (self.number))
        return success

    def mail_acknowledgment_of_receipt(self):
        pool = Pool()
        Config = pool.get('lims.configuration')

        if not self.ack_report_cache:
            return

        config_ = Config(1)
        smtp_server = config_.mail_ack_smtp
        from_addr = (smtp_server and smtp_server.smtp_email or
            tconfig.get('email', 'from'))
        to_addrs = [c.contact.email for c in self.acknowledgment_contacts]
        if not (from_addr and to_addrs):
            return

        reply_to = smtp_server and smtp_server.smtp_reply_to or from_addr
        hide_recipients = config_.mail_ack_hide_recipients
        subject, body = self.subject_body()
        attachment_data = self.attachment()

        msg = self.create_msg(from_addr, to_addrs, subject,
            body, reply_to, hide_recipients, attachment_data)
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
            subject = str('%s %s' % (config_.mail_ack_subject,
                    self.number)).strip()
            body = str(config_.mail_ack_body)

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

    def create_msg(self, from_addr, to_addrs, subject, body,
            reply_to, hide_recipients, attachment_data):
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
            logger.error('Unable to deliver mail for entry %s' % self.number)
            logger.error(str(e))
            if server is not None:
                server.quit()
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
                raise UserError(gettext(
                    'lims.msg_not_fraction', entry=self.rec_name))
        Fraction.confirm(fractions)

    @classmethod
    def check_delete(cls, entries):
        for entry in entries:
            if entry.state != 'draft':
                raise UserError(gettext(
                    'lims.msg_delete_entry', entry=entry.rec_name))

    @classmethod
    def delete(cls, entries):
        cls.check_delete(entries)
        super().delete(entries)

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

    def get_block_entry_confirmation(self, name=None):
        return (self.invoice_party and
            self.invoice_party.block_entry_confirmation or False)

    def get_pre_assigned_samples(self, name=None):
        pool = Pool()
        EntryPreAssignedSample = pool.get('lims.entry.pre_assigned_sample')
        return EntryPreAssignedSample.search_count([('entry', '=', self.id)])


class EntryContactMixin(Model):
    __slots__ = ()

    @classmethod
    def get_contact_field(cls, contacts, names):
        result = {}
        for name in names:
            field_name = name[8:]
            result[name] = {}
            if cls._fields[name]._type == 'many2one':
                for c in contacts:
                    field = getattr(c.contact, field_name, None)
                    result[name][c.id] = field.id if field else None
            elif cls._fields[name]._type == 'boolean':
                for c in contacts:
                    result[name][c.id] = getattr(c.contact, field_name, False)
            else:
                for c in contacts:
                    result[name][c.id] = getattr(c.contact, field_name, None)
        return result


def _order_entry_contact_field(name):
    def order_field(tables):
        Contact = Pool().get('party.address')
        field = Contact._fields[name]
        table, _ = tables[None]
        contact_tables = tables.get('contact')
        if contact_tables is None:
            contact = Contact.__table__()
            contact_tables = {
                None: (contact, contact.id == table.contact),
                }
            tables['contact'] = contact_tables
        return field.convert_order(name, contact_tables, Contact)
    return staticmethod(order_field)


class EntryInvoiceContact(EntryContactMixin, ModelSQL, ModelView):
    'Entry Invoice Contact'
    __name__ = 'lims.entry.invoice_contacts'

    entry = fields.Many2One('lims.entry', 'Entry',
        ondelete='CASCADE', required=True)
    contact = fields.Many2One('party.address', 'Contact', required=True,
        domain=[
            ('party', 'in', [Eval('_parent_entry', {}).get('party', -1),
                Eval('_parent_entry', {}).get('invoice_party', -1)]),
            ('invoice_contact', '=', True),
        ])
    contact_email = fields.Function(fields.Char('Email'),
        'get_contact_field')
    contact_invoice_contact = fields.Function(fields.Boolean(
        'Invoice contact'), 'get_contact_field')
    contact_invoice_contact_default = fields.Function(fields.Boolean(
        'Invoice contact by default'), 'get_contact_field')
    contact_active = fields.Function(fields.Boolean(
        lazy_gettext('ir.msg_active')), 'get_contact_field')

    order_contact_email = _order_entry_contact_field('email')
    order_contact_invoice_contact = _order_entry_contact_field(
        'invoice_contact')
    order_contact_invoice_contact_default = _order_entry_contact_field(
        'invoice_contact_default')
    order_contact_active = _order_entry_contact_field('active')


class EntryReportContact(EntryContactMixin, ModelSQL, ModelView):
    'Entry Report Contact'
    __name__ = 'lims.entry.report_contacts'

    entry = fields.Many2One('lims.entry', 'Entry',
        ondelete='CASCADE', required=True)
    contact = fields.Many2One('party.address', 'Contact', required=True,
        domain=[
            ('party', 'in', [Eval('_parent_entry', {}).get('party', -1),
                Eval('_parent_entry', {}).get('invoice_party', -1)]),
            ('report_contact', '=', True),
        ])
    contact_email = fields.Function(fields.Char('Email'),
        'get_contact_field')
    contact_report_contact = fields.Function(fields.Boolean(
        'Report contact'), 'get_contact_field')
    contact_report_contact_default = fields.Function(fields.Boolean(
        'Report contact by default'), 'get_contact_field')
    contact_active = fields.Function(fields.Boolean(
        lazy_gettext('ir.msg_active')), 'get_contact_field')

    order_contact_email = _order_entry_contact_field('email')
    order_contact_report_contact = _order_entry_contact_field(
        'report_contact')
    order_contact_report_contact_default = _order_entry_contact_field(
        'report_contact_default')
    order_contact_active = _order_entry_contact_field('active')


class EntryAcknowledgmentContact(EntryContactMixin, ModelSQL, ModelView):
    'Entry Acknowledgment Contact'
    __name__ = 'lims.entry.acknowledgment_contacts'

    entry = fields.Many2One('lims.entry', 'Entry',
        ondelete='CASCADE', required=True)
    contact = fields.Many2One('party.address', 'Contact', required=True,
        domain=[
            ('party', 'in', [Eval('_parent_entry', {}).get('party', -1),
                Eval('_parent_entry', {}).get('invoice_party', -1)]),
            ('acknowledgment_contact', '=', True),
        ])
    contact_email = fields.Function(fields.Char('Email'),
        'get_contact_field')
    contact_acknowledgment_contact = fields.Function(fields.Boolean(
        'Acknowledgment contact'), 'get_contact_field')
    contact_acknowledgment_contact_default = fields.Function(fields.Boolean(
        'Acknowledgment contact by default'), 'get_contact_field')
    contact_active = fields.Function(fields.Boolean(
        lazy_gettext('ir.msg_active')), 'get_contact_field')

    order_contact_email = _order_entry_contact_field('email')
    order_contact_acknowledgment_contact = _order_entry_contact_field(
        'acknowledgment_contact')
    order_contact_acknowledgment_contact_default = _order_entry_contact_field(
        'acknowledgment_contact_default')
    order_contact_active = _order_entry_contact_field('active')


class EntryPreAssignedSample(ModelSQL):
    'Entry Pre-Assigned Sample'
    __name__ = 'lims.entry.pre_assigned_sample'

    entry = fields.Many2One('lims.entry', 'Entry',
        ondelete='CASCADE', required=True)
    number = fields.Char('Number')
    used = fields.Boolean('Used')

    @staticmethod
    def default_used():
        return False

    @classmethod
    def get_next_number(cls, entry_id):
        next_number = cls.search([
            ('entry', '=', entry_id),
            ('used', '=', False),
            ], order=[('number', 'ASC')], limit=1)
        if next_number:
            cls.write(next_number, {'used': True})
            return next_number[0].number
        return None


class PreAssignSampleStart(ModelView):
    'Pre-Assign Sample'
    __name__ = 'lims.entry.pre_assign_sample.start'

    quantity = fields.Integer('Samples quantity', required=True)


class PreAssignSample(Wizard):
    'Pre-Assign Sample'
    __name__ = 'lims.entry.pre_assign_sample'

    start_state = 'check'
    check = StateTransition()
    start = StateView('lims.entry.pre_assign_sample.start',
        'lims.lims_pre_assign_sample_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Pre-Assign', 'confirm', 'tryton-ok', default=True),
            ])
    confirm = StateTransition()

    def transition_check(self):
        EntryPreAssignedSample = Pool().get('lims.entry.pre_assigned_sample')

        entry_id = Transaction().context['active_id']

        if EntryPreAssignedSample.search_count([
                ('entry', '=', entry_id)
                ]) > 0:
            return 'end'
        return 'start'

    def transition_confirm(self):
        pool = Pool()
        LabWorkYear = pool.get('lims.lab.workyear')
        EntryPreAssignedSample = pool.get('lims.entry.pre_assigned_sample')

        workyear_id = LabWorkYear.find()
        workyear = LabWorkYear(workyear_id)
        sequence = workyear.get_sequence('sample')
        if not sequence:
            raise UserError(gettext('lims.msg_no_sample_sequence',
                work_year=workyear.rec_name))

        entry_id = Transaction().context['active_id']
        records = []
        for i in range(self.start.quantity):
            records.append({
                'entry': entry_id,
                'number': sequence.get(),
                'used': False,
                })
        EntryPreAssignedSample.create(records)
        return 'end'


class EntrySuspensionReason(ModelSQL, ModelView):
    'Entry Suspension Reason'
    __name__ = 'lims.entry.suspension.reason'
    _rec_name = 'description'

    code = fields.Char('Code', required=True)
    description = fields.Char('Description', required=True)
    by_default = fields.Boolean('By default')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code),
                'lims.msg_suspension_reason_unique_id'),
            ]

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
        super().validate(reasons)
        for sr in reasons:
            sr.check_default()

    def check_default(self):
        if self.by_default:
            reasons = self.search([
                ('by_default', '=', True),
                ('id', '!=', self.id),
                ])
            if reasons:
                raise UserError(gettext('lims.msg_default_suspension_reason'))


class EntryCancellationReason(ModelSQL, ModelView):
    'Entry Cancellation Reason'
    __name__ = 'lims.entry.cancellation.reason'
    _rec_name = 'description'

    code = fields.Char('Code', required=True)
    description = fields.Char('Description', required=True)
    by_default = fields.Boolean('By default')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code),
                'lims.msg_cancellation_reason_unique_id'),
            ]

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
        super().validate(reasons)
        for sr in reasons:
            sr.check_default()

    def check_default(self):
        if self.by_default:
            reasons = self.search([
                ('by_default', '=', True),
                ('id', '!=', self.id),
                ])
            if reasons:
                raise UserError(gettext(
                    'lims.msg_default_cancellation_reason'))


class EntryDetailAnalysis(ModelSQL, ModelView):
    'Entry Detail Analysis'
    __name__ = 'lims.entry.detail.analysis'

    service = fields.Many2One('lims.service', 'Service', required=True,
        ondelete='CASCADE', readonly=True)
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
    analysis_type = fields.Function(fields.Selection(
        [(None, '')] + ANALYSIS_TYPES, 'Type', sort=False),
        'on_change_with_analysis_type')
    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        states={'readonly': True})
    method = fields.Many2One('lims.lab.method', 'Method',
        states={'readonly': True})
    method_version = fields.Many2One('lims.lab.method.version',
        'Method version', readonly=True)
    device = fields.Many2One('lims.lab.device', 'Device',
        states={'readonly': True})
    analysis_origin = fields.Char('Analysis origin',
        states={'readonly': True})
    confirmation_date = fields.Date('Confirmation date', readonly=True)
    report_grouper = fields.Integer('Report Grouper',
        states={'readonly': Bool(Eval('report_grouper_readonly'))})
    report_grouper_readonly = fields.Function(fields.Boolean(
        'Report Grouper readonly'), 'get_report_grouper_readonly')
    results_report = fields.Function(fields.Many2One('lims.results_report',
        'Results Report'), 'get_results_report')
    report = fields.Boolean('Report', states={'readonly': True})
    state = fields.Selection([
        ('draft', 'Draft'),
        ('unplanned', 'Unplanned'),
        ('planned', 'Planned'),
        ('referred', 'Referred'),
        ('done', 'Done'),
        ('reported', 'Reported'),
        ('annulled', 'Annulled'),
        ], 'State', readonly=True)
    cie_min_value = fields.Char('Minimum value')
    cie_max_value = fields.Char('Maximum value')
    cie_fraction_type = fields.Function(fields.Boolean('Blind Sample'),
        'get_cie_fraction_type')
    plannable = fields.Boolean('Plannable')
    referable = fields.Boolean('Referred by default')
    referral = fields.Many2One('lims.referral', 'Referral',
        states={'readonly': True})
    referral_date = fields.Function(fields.Date('Referral date'),
        'get_referral_date', searcher='search_referral_date')
    label = fields.Function(fields.Char('Label'),
        'get_sample_field', searcher='search_sample_field')

    @classmethod
    def __register__(cls, module_name):
        table_h = cls.__table_handler__(module_name)
        plannable_exist = table_h.column_exist('plannable')
        super().__register__(module_name)
        if not plannable_exist:
            cursor = Transaction().connection.cursor()
            pool = Pool()
            Service = pool.get('lims.service')
            Fraction = pool.get('lims.fraction')
            FractionType = pool.get('lims.fraction.type')
            cursor.execute('UPDATE "' + cls._table + '" d '
                'SET plannable = ft.plannable FROM '
                '"' + Service._table + '" srv, '
                '"' + Fraction._table + '" frc, '
                '"' + FractionType._table + '" ft '
                'WHERE srv.id = d.service '
                'AND frc.id = srv.fraction '
                'AND ft.id = frc.type')

    @classmethod
    def __setup__(cls):
        cls.state.search_unaccented = False
        super().__setup__()
        cls._order.insert(0, ('service', 'DESC'))
        t = cls.__table__()
        #cls._sql_indexes.update({
            #Index(t, (t.state, Index.Similarity())),
            #Index(t, (t.analysis, Index.Equality())),
            #Index(t, (t.plannable, Index.Equality())),
            #Index(t, (t.referable, Index.Equality())),
            #})

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
    def default_state():
        return 'draft'

    @staticmethod
    def default_report():
        return True

    @staticmethod
    def default_report_grouper():
        return 0

    @staticmethod
    def default_referable():
        return False

    def _get_default_laboratory(self):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        AnalysisLaboratory = pool.get('lims.analysis-laboratory')
        Typification = pool.get('lims.typification')

        cursor.execute('SELECT laboratory '
            'FROM "' + Typification._table + '" '
            'WHERE product_type = %s '
                'AND matrix = %s '
                'AND analysis = %s '
                'AND valid IS TRUE '
                'AND by_default IS TRUE '
                'AND laboratory IS NOT NULL',
            (self.service.fraction.product_type.id,
                self.service.fraction.matrix.id,
                self.analysis.id))
        res = cursor.fetchone()
        if res:
            return res[0]

        cursor.execute('SELECT laboratory '
            'FROM "' + AnalysisLaboratory._table + '" '
            'WHERE analysis = %s '
                'AND by_default = TRUE '
            'ORDER BY id', (self.analysis.id,))
        res = cursor.fetchone()
        if res:
            return res[0]

        return None

    @classmethod
    def view_attributes(cls):
        return super().view_attributes() + [
            ('//group[@id="cie"]', 'states', {
                    'invisible': ~Eval('cie_fraction_type'),
                    }),
            ]

    @classmethod
    def create(cls, vlist):
        pool = Pool()
        LabMethod = pool.get('lims.lab.method')

        vlist = [x.copy() for x in vlist]
        for values in vlist:
            values['plannable'] = cls._get_plannable(values)
            # set method version
            if 'method' in values and values['method'] is not None:
                values['method_version'] = LabMethod(
                    values['method']).get_current_version()

        details = super().create(vlist)

        cls._set_referable(details)
        return details

    @classmethod
    def copy(cls, details, default=None):
        if default is None:
            default = {}
        current_default = default.copy()
        current_default['confirmation_date'] = None
        for detail in details:
            if (detail.laboratory and
                    detail.laboratory.id !=
                    detail._get_default_laboratory()):
                raise UserError(gettext('lims.msg_service_default_laboratory',
                    analysis=detail.analysis.rec_name,
                    laboratory=detail.laboratory.rec_name))
        return super().copy(details, default=current_default)

    @classmethod
    def check_delete(cls, details):
        for detail in details:
            if detail.fraction and detail.fraction.confirmed:
                raise UserError(gettext('lims.msg_delete_detail'))

    @classmethod
    def delete(cls, details):
        if Transaction().user != 0:
            cls.check_delete(details)
        super().delete(details)

    @classmethod
    def create_notebook_lines(cls, details, fraction):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Typification = pool.get('lims.typification')
        Method = pool.get('lims.lab.method')
        WaitingTime = pool.get('lims.lab.method.results_waiting')
        AnalysisLaboratory = pool.get('lims.analysis-laboratory')
        ProductType = pool.get('lims.product.type')
        Notebook = pool.get('lims.notebook')
        NotebookLine = pool.get('lims.notebook.line')
        Config = pool.get('lims.configuration')

        with Transaction().set_user(0):
            notebooks = Notebook.search([('fraction', '=', fraction.id)])
            if not notebooks:
                return
            notebook = notebooks[0]

        warn_invalid_typification = cls._warn_invalid_typification()
        lines_to_create = []
        for detail in details:
            t = Typification.get_valid_typification(
                fraction.product_type.id, fraction.matrix.id,
                detail.analysis.id, detail.method.id)

            if t:
                repetitions = t.default_repetitions
                initial_concentration = t.initial_concentration
                final_concentration = t.final_concentration
                literal_final_concentration = t.literal_final_concentration
                initial_unit = t.start_uom and t.start_uom.id or None
                final_unit = t.end_uom and t.end_uom.id or None
                detection_limit = (str(t.detection_limit) if
                    t.detection_limit is not None else None)
                quantification_limit = (str(t.quantification_limit) if
                    t.quantification_limit is not None else None)
                lower_limit = (str(t.lower_limit) if
                    t.lower_limit is not None else None)
                upper_limit = (str(t.upper_limit) if
                    t.upper_limit is not None else None)
                decimals = t.calc_decimals
                significant_digits = t.significant_digits
                scientific_notation = t.scientific_notation
                result_decimals = t.result_decimals
                converted_result_decimals = t.converted_result_decimals
                report = t.report
                department = t.department and t.department.id or None
            elif warn_invalid_typification:
                raise UserError(gettext('lims.msg_not_typification',
                    analysis=detail.analysis.rec_name,
                    method=detail.method.rec_name,
                    product_type=fraction.product_type.rec_name,
                    matrix=fraction.matrix.rec_name))
            else:
                repetitions = 0
                initial_concentration = None
                final_concentration = None
                literal_final_concentration = None
                initial_unit = None
                final_unit = None
                detection_limit = None
                quantification_limit = None
                lower_limit = None
                upper_limit = None
                decimals = 2
                significant_digits = None
                scientific_notation = False
                result_decimals = None
                converted_result_decimals = None
                report = False
                department = None

            results_estimated_waiting = None
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
                if res:
                    results_estimated_waiting = res[0]

            if not department:
                cursor.execute('SELECT department '
                    'FROM "' + AnalysisLaboratory._table + '" '
                    'WHERE analysis = %s '
                        'AND laboratory = %s '
                    'ORDER BY by_default DESC',
                    (detail.analysis.id, detail.laboratory.id))
                res = cursor.fetchone()
                if res and res[0]:
                    department = res[0]
                else:
                    cursor.execute('SELECT department '
                        'FROM "' + ProductType._table + '" '
                        'WHERE id = %s', (fraction.product_type.id,))
                    res = cursor.fetchone()
                    if res and res[0]:
                        department = res[0]

            for i in range(0, repetitions + 1):
                notebook_line = {
                    'notebook': notebook.id,
                    'analysis_detail': detail.id,
                    'service': detail.service.id,
                    'analysis': detail.analysis.id,
                    'analysis_origin': detail.analysis_origin,
                    'urgent': detail.service.urgent,
                    'repetition': i,
                    'laboratory': detail.laboratory.id,
                    'method': detail.method.id,
                    'device': detail.device and detail.device.id or None,
                    'initial_concentration': initial_concentration,
                    'final_concentration': final_concentration,
                    'literal_final_concentration': literal_final_concentration,
                    'initial_unit': initial_unit,
                    'final_unit': final_unit,
                    'detection_limit': detection_limit,
                    'quantification_limit': quantification_limit,
                    'lower_limit': lower_limit,
                    'upper_limit': upper_limit,
                    'decimals': decimals,
                    'significant_digits': significant_digits,
                    'scientific_notation': scientific_notation,
                    'result_decimals': result_decimals,
                    'converted_result_decimals': converted_result_decimals,
                    'report': report,
                    'results_estimated_waiting': results_estimated_waiting,
                    'department': department,
                    }
                lines_to_create.append(notebook_line)

        with Transaction().set_user(0):
            lines = NotebookLine.create(lines_to_create)

            # copy translated fields from typification
            default_language = Config(1).results_report_language
            for line in lines:
                t = Typification.get_valid_typification(
                    line.product_type.id, line.matrix.id,
                    line.analysis.id, line.method.id)
                if not t:
                    continue
                for field in ['initial_concentration', 'final_concentration',
                        'literal_final_concentration']:
                    cursor.execute("SELECT lang, src, value "
                        "FROM ir_translation "
                        "WHERE name = %s "
                            "AND res_id = %s "
                            "AND type = 'model' "
                            "AND lang != %s",
                        ('lims.typification,' + field, str(t.id),
                            default_language.code))
                    for x in cursor.fetchall():
                        cursor.execute("INSERT INTO ir_translation "
                            "(name, res_id, type, lang, src, value) "
                            "VALUES (%s, %s, 'model', %s, %s, %s)",
                            ('lims.notebook.line,' + field, str(line.id),
                                x[0], x[1], x[2]))

    @classmethod
    def _warn_invalid_typification(cls):
        return False

    @staticmethod
    def default_service_view():
        if (Transaction().context.get('service', 0) > 0):
            return Transaction().context.get('service')
        return None

    @fields.depends('service', '_parent_service.id')
    def on_change_with_service_view(self, name=None):
        if self.service:
            return self.service.id
        return None

    @fields.depends('analysis', '_parent_analysis.type')
    def on_change_with_analysis_type(self, name=None):
        return self.analysis and self.analysis.type or None

    @classmethod
    def get_service_field(cls, details, names):
        result = {}
        for name in names:
            result[name] = {}
            if cls._fields[name]._type == 'many2one':
                for d in details:
                    field = getattr(d.service, name, None)
                    result[name][d.id] = field.id if field else None
            else:
                for d in details:
                    result[name][d.id] = getattr(d.service, name, None)
        return result

    @classmethod
    def search_service_field(cls, name, clause):
        return [('service.' + name,) + tuple(clause[1:])]

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
    def order_create_date2(cls, tables):
        return cls.create_date.convert_order('create_date', tables, cls)

    @classmethod
    def get_report_grouper_readonly(cls, details, name):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        ResultsLine = pool.get('lims.results_report.version.detail.line')
        ResultsSample = pool.get('lims.results_report.version.detail.sample')
        ResultsDetail = pool.get('lims.results_report.version.detail')

        result = {}
        for d in details:
            cursor.execute('SELECT rd.id '
                'FROM "' + ResultsDetail._table + '" rd '
                    'INNER JOIN "' + ResultsSample._table + '" rs '
                    'ON rd.id = rs.version_detail '
                    'INNER JOIN "' + ResultsLine._table + '" rl '
                    'ON rl.detail_sample = rs.id '
                    'INNER JOIN "' + NotebookLine._table + '" nl '
                    'ON nl.id = rl.notebook_line '
                'WHERE nl.analysis_detail = %s '
                    'AND rd.state IN (\'released\', \'annulled\')',
                (str(d.id),))
            reports_ids = [x[0] for x in cursor.fetchall()]
            result[d.id] = True if reports_ids else False
        return result

    @classmethod
    def get_results_report(cls, details, name):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')

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

    def get_cie_fraction_type(self, name=None):
        if (self.service and self.service.fraction and
                self.service.fraction.cie_fraction_type and
                not self.service.fraction.cie_original_fraction):
            return True
        return False

    @classmethod
    def get_referral_date(cls, details, name):
        result = {}
        for d in details:
            result[d.id] = d.referral and d.referral.date or None
        return result

    @classmethod
    def search_referral_date(cls, name, clause):
        return [('referral.date',) + tuple(clause[1:])]

    @classmethod
    def get_sample_field(cls, details, names):
        result = {}
        for name in names:
            result[name] = {}
            if cls._fields[name]._type == 'many2one':
                for d in details:
                    field = getattr(d.sample, name, None)
                    result[name][d.id] = field.id if field else None
            else:
                for d in details:
                    result[name][d.id] = getattr(d.sample, name, None)
        return result

    @classmethod
    def search_sample_field(cls, name, clause):
        return [('service.fraction.sample.' + name,) + tuple(clause[1:])]

    @classmethod
    def write(cls, *args):
        pool = Pool()
        LabMethod = pool.get('lims.lab.method')

        actions = iter(args)
        args = []
        for details, values in zip(actions, actions):
            # set method version
            if 'method' in values and values['method'] is not None:
                values['method_version'] = LabMethod(
                    values['method']).get_current_version()
            args.extend((details, values))

        super().write(*args)

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

    @classmethod
    def _get_plannable(cls, values):
        Service = Pool().get('lims.service')
        service_id = values.get('service', None)
        if not service_id:
            return False
        return Service(service_id).fraction.type.plannable

    @classmethod
    def _set_referable(cls, details):
        cursor = Transaction().connection.cursor()
        Typification = Pool().get('lims.typification')

        details_to_write = []
        for detail in details:
            cursor.execute('SELECT referable '
                'FROM "' + Typification._table + '" '
                'WHERE product_type = %s '
                    'AND matrix = %s '
                    'AND analysis = %s '
                    'AND method = %s '
                    'AND valid',
                (detail.fraction.product_type.id, detail.fraction.matrix.id,
                    detail.analysis.id, detail.method.id))
            typifications = cursor.fetchall()
            typification = (typifications[0] if len(typifications) == 1
                else None)
            if typification and typification[0]:
                details_to_write.append(detail)

        if details_to_write:
            cls.write(details_to_write, {
                'referable': True,
                'plannable': False,
                })

    def _get_dict_for_fast_copy(self):
        def _many2one(value):
            if value:
                return str(value.id)
            return "NULL"

        def _string(value):
            if value:
                return "'%s'" % str(value)
            return "NULL"

        def _integer(value):
            if value is not None:
                return str(value)
            return "NULL"

        def _boolean(value):
            if value:
                return "TRUE"
            return "FALSE"

        res = {
            'create_uid': _many2one(self.create_uid),
            'create_date': _string(self.create_date),
            'analysis': _many2one(self.analysis),
            'laboratory': _many2one(self.laboratory),
            'method': _many2one(self.method),
            'device': _many2one(self.device),
            'analysis_origin': _string(self.analysis_origin),
            'report_grouper': _integer(self.report_grouper),
            'report': _boolean(self.report),
            'state': _string(self.state),
            'plannable': _boolean(self.plannable),
            'referable': _boolean(self.referable),
            }
        return res


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
            if entry.no_acknowledgment_of_receipt:
                continue

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
        domain=[('id', 'in', Eval('invoice_party_domain'))], required=True)


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
        super().__setup__()
        cls.__rpc__['execute'] = RPC(False)

    @classmethod
    def execute(cls, ids, data):
        Entry = Pool().get('lims.entry')

        result = super().execute(ids, data)
        entry = Entry(ids[0])

        if entry.ack_report_cache:
            result = (entry.ack_report_format,
                entry.ack_report_cache) + result[2:]
        else:
            entry.ack_report_format, entry.ack_report_cache = result[:2]
            entry.save()
        return result

    @classmethod
    def get_context(cls, records, header, data):
        pool = Pool()
        Company = pool.get('company.company')
        Service = pool.get('lims.service')
        Entry = pool.get('lims.entry')

        report_context = super().get_context(records, header, data)
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
                'date': company.convert_timezone_datetime(sample.date),
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
                    ('annulled', '=', False),
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
                            v['enac_label'] = gettext(
                                'lims.msg_enac_acredited')
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
    def execute(cls, ids, data):
        if 'ids' in data:
            ids = data['ids']
        return super().execute(ids, data)

    @classmethod
    def get_context(cls, records, header, data):
        Company = Pool().get('company.company')

        report_context = super().get_context(records, header, data)

        company = Company(Transaction().context.get('company'))
        report_context['company'] = company
        return report_context


class EntryLabels(Report):
    'Entry Labels'
    __name__ = 'lims.entry.labels.report'

    @classmethod
    def get_context(cls, records, header, data):
        report_context = super().get_context(records, header, data)
        labels = []
        for entry in records:
            for sample in entry.samples:
                for package in sample.packages:
                    for i in range(package.quantity):
                        for fraction in sample.fractions:
                            labels.append(fraction)
        report_context['labels'] = labels
        return report_context
