# -*- coding: utf-8 -*-
# This file is part of lims_account_invoice module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from time import time
from datetime import datetime
from logging import getLogger

from trytond.model import ModelView
from trytond.wizard import Wizard, StateTransition, StateView, Button
from trytond.pool import Pool
from trytond.transaction import Transaction


__all__ = ['PopulateInvoiceContactsStart', 'PopulateInvoiceContacts',
    'SendOfInvoice']

logger = getLogger('lims_account_invoice')


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
        LimsEntry = pool.get('lims.entry')

        invoice = Invoice(Transaction().context['active_id'])

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
        entries = LimsEntry.search([('id', 'in', entry_ids)],
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

        entry_invoice_contacts = EntryInvoiceContacts.search([
            ('entry', 'in', entry_ids),
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
