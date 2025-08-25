# This file is part of lims_sale module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from decimal import Decimal

from trytond.model import ModelSQL, fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, Or
from trytond.transaction import Transaction
from trytond.exceptions import UserError, UserWarning
from trytond.i18n import gettext


class CreateSampleStart(metaclass=PoolMeta):
    __name__ = 'lims.create_sample.start'

    sale_lines_filter_product_type_matrix = fields.Boolean(
        'Filter Quotes by Product type and Matrix')
    sale_lines = fields.Many2Many('sale.line', None, None, 'Quotes',
        domain=[('id', 'in', Eval('sale_lines_domain'))],
        states={'readonly': Or(~Eval('product_type'), ~Eval('matrix'))},
        depends=['sale_lines_domain', 'product_type', 'matrix'])
    sale_lines_domain = fields.Function(fields.Many2Many('sale.line',
        None, None, 'Quotes domain'),
        'on_change_with_sale_lines_domain')

    @staticmethod
    def default_sale_lines_filter_product_type_matrix():
        Config = Pool().get('sale.configuration')
        return Config(1).sale_lines_filter_product_type_matrix

    @fields.depends('party', 'invoice_party', 'product_type', 'matrix',
        'sale_lines_filter_product_type_matrix')
    def on_change_with_sale_lines_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Date = pool.get('ir.date')
        SaleLine = pool.get('sale.line')
        Analysis = pool.get('lims.analysis')

        if not self.party or not self.product_type or not self.matrix:
            return []

        with Transaction().set_context(_check_sale_line=False):
            analysis_domain = self.on_change_with_analysis_domain()
        if not analysis_domain:
            return []
        analysis_ids = ', '.join(str(a) for a in analysis_domain)

        cursor.execute('SELECT DISTINCT(product) '
            'FROM "' + Analysis._table + '" '
            'WHERE id IN (' + analysis_ids + ')')
        res = cursor.fetchall()
        if not res:
            return []
        product_ids = [x[0] for x in res]

        today = Date.today()
        clause = [
            ('sale.party', 'in', [self.party.id, self.invoice_party.id]),
            ('sale.expiration_date', '>=', today),
            ('sale.state', 'in', [
                'quotation', 'confirmed', 'processing',
                ]),
            ('product.id', 'in', product_ids),
            ]
        if self.sale_lines_filter_product_type_matrix:
            clause.append(('product_type', '=', self.product_type.id))
            clause.append(('matrix', '=', self.matrix.id))

        sale_lines = SaleLine.search(clause)
        res = [sl.id for sl in sale_lines if not sl.services_completed]
        return res

    @fields.depends('party', 'product_type', 'matrix', 'sale_lines')
    def on_change_with_analysis_domain(self, name=None):
        pool = Pool()
        Analysis = pool.get('lims.analysis')
        Entry = pool.get('lims.entry')

        entry_id = Transaction().context.get('active_id', None)
        if not entry_id:
            return []
        entry = Entry(entry_id)

        analysis_domain = super().on_change_with_analysis_domain(name)

        if not Transaction().context.get('_check_sale_line', True):
            return analysis_domain

        if not self.sale_lines:
            if not entry.allow_services_without_quotation:
                return []
            else:
                return analysis_domain

        quoted_products = [sl.product.id
            for sl in self.sale_lines if sl.product]
        quoted_analysis = Analysis.search([('product', 'in', quoted_products)])
        quoted_analysis_ids = [a.id for a in quoted_analysis]
        return [a for a in analysis_domain if a in quoted_analysis_ids]

    @fields.depends('sale_lines', 'product_type', 'matrix', 'services',
        methods=['on_change_with_analysis_domain'])
    def on_change_sale_lines(self, name=None):
        if not self.sale_lines:
            return
        self.load_sale_lines_analyzes()

    def load_sale_lines_analyzes(self):
        pool = Pool()
        Analysis = pool.get('lims.analysis')
        CreateSampleService = pool.get('lims.create_sample.service')

        analysis_domain = self.on_change_with_analysis_domain()
        if not analysis_domain:
            return

        quoted_products_methods = {}
        for sl in self.sale_lines:
            if sl.product:
                quoted_products_methods[sl.product.id] = sl.method
        quoted_analysis = Analysis.search([
            ('product', 'in', list(quoted_products_methods.keys()))])
        quoted_analysis = [a for a in quoted_analysis
            if a.id in analysis_domain]
        if not quoted_analysis:
            return

        quoted_services = []
        for a in quoted_analysis:
            with Transaction().set_context(
                    product_type=self.product_type.id,
                    matrix=self.matrix.id):
                s = CreateSampleService()
                s.analysis_locked = False
                s.urgent = s.default_urgent()
                s.priority = s.default_priority()
                s.analysis = a
                s.on_change_analysis()
                if quoted_products_methods[a.product.id]:
                    s.method = quoted_products_methods[a.product.id]
                s.laboratory_date = s.on_change_with_laboratory_date()
                s.report_date = s.on_change_with_report_date()

            quoted_services.append(s)

        self.services = quoted_services


class CreateSample(metaclass=PoolMeta):
    __name__ = 'lims.create_sample'

    def _get_samples_defaults(self, entry_id):
        pool = Pool()
        Analysis = pool.get('lims.analysis')
        Entry = pool.get('lims.entry')
        Warning = pool.get('res.user.warning')

        samples_defaults = super()._get_samples_defaults(entry_id)

        if (not hasattr(self.start, 'sale_lines') or
                not hasattr(self.start, 'services')):
            return samples_defaults

        sale_lines = {}
        for sl in self.start.sale_lines:
            analysis_id = sl.analysis and sl.analysis.id
            if not analysis_id:
                product_id = sl.product and sl.product.id
                if not product_id:
                    continue
                analysis = Analysis.search([('product', '=', product_id)])
                if not analysis:
                    continue
                analysis_id = analysis[0].id
            sale_lines[analysis_id] = {
                'line': sl.id,
                'available': sl.services_available,
                }
        if not sale_lines:
            return samples_defaults

        entry = Entry(Transaction().context['active_id'])
        allow_services_without_quotation = (
            entry.allow_services_without_quotation)
        error_key = 'lims_services_without_quotation@%s' % entry.number
        error_msg = 'lims_sale.msg_services_without_quotation'
        labels_qty = len(self._get_labels_list(self.start.labels))

        for sample in samples_defaults:
            if 'fractions' not in sample:
                continue
            for fraction_defaults in sample['fractions']:
                if 'create' not in fraction_defaults[0]:
                    continue
                for fraction in fraction_defaults[1]:
                    if 'services' not in fraction:
                        continue
                    for services_defaults in fraction['services']:
                        if 'create' not in services_defaults[0]:
                            continue
                        for service in services_defaults[1]:
                            analysis_id = service['analysis']
                            if analysis_id not in sale_lines:
                                continue
                            service['sale_lines'] = [('add',
                                [sale_lines[analysis_id]['line']])]
                            if (sale_lines[analysis_id]['available'] is None or
                                    sale_lines[analysis_id]['available'] >=
                                    labels_qty):
                                continue
                            if not allow_services_without_quotation:
                                raise UserError(gettext(error_msg))
                            if Warning.check(error_key):
                                raise UserWarning(error_key,
                                    gettext(error_msg))

        return samples_defaults

    def transition_create_(self):
        res = super().transition_create_()
        self._update_entry_contacts()
        return res

    def _update_entry_contacts(self):
        pool = Pool()
        Config = pool.get('lims.configuration')
        Entry = pool.get('lims.entry')
        ServiceSaleLine = pool.get('lims.service-sale.line')
        Sale = pool.get('sale.sale')
        InvoiceContacts = pool.get('lims.entry.invoice_contacts')
        ReportContacts = pool.get('lims.entry.report_contacts')
        AcknowledgmentContacts = pool.get('lims.entry.acknowledgment_contacts')

        config_ = Config(1)
        if not config_.entry_use_sale_contacts:
            return

        entry = Entry(Transaction().context['active_id'])

        sale_lines = ServiceSaleLine.search([
            ('service.fraction.sample.entry', '=', entry.id),
            ])
        sales_ids = list(set([sl.sale_line.sale.id for sl in sale_lines]))
        if not sales_ids:
            return

        shipment_addresses = []
        invoice_addresses = []

        invoice_contacts = []
        report_contacts = []
        acknowledgment_contacts = []

        sales = Sale.browse(sales_ids)
        for sale in sales:
            if not sale.shipment_address:
                continue
            if sale.shipment_address.id in shipment_addresses:
                continue
            report_contacts.append(
                ReportContacts(contact=sale.shipment_address))
            acknowledgment_contacts.append(
                AcknowledgmentContacts(contact=sale.shipment_address))
            shipment_addresses.append(sale.shipment_address)

            if not sale.invoice_address:
                continue
            if sale.invoice_address.id in invoice_addresses:
                continue
            invoice_contacts.append(
                InvoiceContacts(contact=sale.invoice_address))
            invoice_addresses.append(sale.invoice_address.id)

        if not shipment_addresses:
            return

        entry.invoice_contacts = invoice_contacts
        entry.report_contacts = report_contacts
        entry.acknowledgment_contacts = acknowledgment_contacts
        entry.save()


class AddSampleServiceStart(metaclass=PoolMeta):
    __name__ = 'lims.sample.add_service.start'

    sale_lines_filter_product_type_matrix = fields.Boolean(
        'Filter Quotes by Product type and Matrix')
    sale_lines = fields.Many2Many('sale.line', None, None, 'Quotes',
        domain=[('id', 'in', Eval('sale_lines_domain'))],
        states={'readonly': Or(~Eval('product_type'), ~Eval('matrix'))},
        depends=['sale_lines_domain', 'product_type', 'matrix'])
    sale_lines_domain = fields.Function(fields.Many2Many('sale.line',
        None, None, 'Quotes domain'),
        'on_change_with_sale_lines_domain')

    @staticmethod
    def default_sale_lines_filter_product_type_matrix():
        Config = Pool().get('sale.configuration')
        return Config(1).sale_lines_filter_product_type_matrix

    @fields.depends('party', 'invoice_party', 'product_type', 'matrix',
        'sale_lines_filter_product_type_matrix', 'analysis_domain')
    def on_change_with_sale_lines_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Date = pool.get('ir.date')
        SaleLine = pool.get('sale.line')
        Analysis = pool.get('lims.analysis')
        Sample = pool.get('lims.sample')

        if not self.party or not self.product_type or not self.matrix:
            return []

        active_id = Transaction().context['active_ids'][0]
        if not active_id:
            return []

        sample = Sample(active_id)
        analysis_domain = sample.on_change_with_analysis_domain()
        if not analysis_domain:
            return []
        analysis_ids = ', '.join(str(a) for a in analysis_domain)

        cursor.execute('SELECT DISTINCT(product) '
            'FROM "' + Analysis._table + '" '
            'WHERE id IN (' + analysis_ids + ')')
        res = cursor.fetchall()
        if not res:
            return []
        product_ids = [x[0] for x in res]

        today = Date.today()
        clause = [
            ('sale.party', 'in', [self.party.id, self.invoice_party.id]),
            ('sale.expiration_date', '>=', today),
            ('sale.state', 'in', [
                'quotation', 'confirmed', 'processing',
                ]),
            ('product.id', 'in', product_ids),
            ]
        if self.sale_lines_filter_product_type_matrix:
            clause.append(('product_type', '=', self.product_type.id))
            clause.append(('matrix', '=', self.matrix.id))

        sale_lines = SaleLine.search(clause)
        res = [sl.id for sl in sale_lines if not sl.services_completed]
        return res

    @fields.depends('party', 'product_type', 'matrix', 'sale_lines')
    def on_change_with_analysis_domain(self, name=None):
        pool = Pool()
        Analysis = pool.get('lims.analysis')
        Sample = pool.get('lims.sample')

        active_id = Transaction().context['active_ids'][0]
        if not active_id:
            return []

        sample = Sample(active_id)
        if (not self.sale_lines and
                not sample.entry.allow_services_without_quotation):
            return []

        analysis_domain = sample.on_change_with_analysis_domain()

        if not self.sale_lines:
            return analysis_domain

        quoted_products = [sl.product.id
            for sl in self.sale_lines if sl.product]
        quoted_analysis = Analysis.search([('product', 'in', quoted_products)])
        quoted_analysis_ids = [a.id for a in quoted_analysis]
        return [a for a in analysis_domain if a in quoted_analysis_ids]

    @fields.depends('sale_lines', 'product_type', 'matrix', 'services',
        methods=['on_change_with_analysis_domain'])
    def on_change_sale_lines(self, name=None):
        if not self.sale_lines:
            return
        self.load_sale_lines_analyzes()

    def load_sale_lines_analyzes(self):
        pool = Pool()
        Analysis = pool.get('lims.analysis')
        CreateSampleService = pool.get('lims.create_sample.service')

        analysis_domain = self.on_change_with_analysis_domain()
        if not analysis_domain:
            return

        quoted_products_methods = {}
        for sl in self.sale_lines:
            if sl.product:
                quoted_products_methods[sl.product.id] = sl.method
        quoted_analysis = Analysis.search([
            ('product', 'in', list(quoted_products_methods.keys()))])
        quoted_analysis = [a for a in quoted_analysis
            if a.id in analysis_domain]
        if not quoted_analysis:
            return

        quoted_services = []
        for a in quoted_analysis:
            with Transaction().set_context(
                    product_type=self.product_type.id,
                    matrix=self.matrix.id):
                s = CreateSampleService()
                s.analysis_locked = False
                s.urgent = s.default_urgent()
                s.priority = s.default_priority()
                s.analysis = a
                s.on_change_analysis()
                if quoted_products_methods[a.product.id]:
                    s.method = quoted_products_methods[a.product.id]
                s.laboratory_date = s.on_change_with_laboratory_date()
                s.report_date = s.on_change_with_report_date()

            quoted_services.append(s)

        self.services = quoted_services


class AddSampleService(metaclass=PoolMeta):
    __name__ = 'lims.sample.add_service'

    def _get_new_service(self, service, fraction):
        pool = Pool()
        Analysis = pool.get('lims.analysis')
        Sample = pool.get('lims.sample')
        Warning = pool.get('res.user.warning')

        service_create = super()._get_new_service(service, fraction)

        if not hasattr(self.start, 'sale_lines'):
            return service_create

        sale_lines = {}
        for sl in self.start.sale_lines:
            analysis_id = sl.analysis and sl.analysis.id
            if not analysis_id:
                product_id = sl.product and sl.product.id
                if not product_id:
                    continue
                analysis = Analysis.search([('product', '=', product_id)])
                if not analysis:
                    continue
                analysis_id = analysis[0].id
            sale_lines[analysis_id] = {
                'line': sl.id,
                'available': sl.services_available,
                }
        if not sale_lines:
            return service_create

        analysis_id = service_create['analysis']
        if analysis_id not in sale_lines:
            return service_create
        service_create['sale_lines'] = [('add',
            [sale_lines[analysis_id]['line']])]
        if (sale_lines[analysis_id]['available'] is None or
                sale_lines[analysis_id]['available'] >= 1):
            return service_create

        active_id = Transaction().context['active_ids'][0]
        if not active_id:
            return service_create

        sample = Sample(active_id)
        error_key = 'lims_services_without_quotation@%s' % sample.entry.number
        error_msg = 'lims_sale.msg_party_services_without_quotation'
        warning_msg = 'lims_sale.msg_adding_services_without_quotation'
        if not sample.entry.allow_services_without_quotation:
            raise UserError(gettext(error_msg))
        if Warning.check(error_key):
            raise UserWarning(error_key, gettext(warning_msg))

        return service_create


class EditSampleService(metaclass=PoolMeta):
    __name__ = 'lims.sample.edit_service'

    def _get_new_service(self, service, fraction):
        pool = Pool()
        Sample = pool.get('lims.sample')
        Warning = pool.get('res.user.warning')

        service_create = super()._get_new_service(service, fraction)

        active_id = Transaction().context['active_ids'][0]
        if not active_id:
            return service_create

        sample = Sample(active_id)
        error_key = 'lims_services_without_quotation@%s' % sample.entry.number
        error_msg = 'lims_sale.msg_party_services_without_quotation'
        warning_msg = 'lims_sale.msg_adding_services_without_quotation'
        if not sample.entry.allow_services_without_quotation:
            raise UserError(gettext(error_msg))

        if Warning.check(error_key):
            raise UserWarning(error_key, gettext(warning_msg))

        return service_create


class EditSample(metaclass=PoolMeta):
    __name__ = 'lims.sample.edit'

    def transition_confirm(self):
        pool = Pool()
        ServiceSaleLine = pool.get('lims.service-sale.line')

        error_msg = 'lims_sale.msg_party_services_without_quotation'

        samples = self._get_filtered_samples()
        for sample in samples:
            if self.start.party and self.start.party != sample.party:
                sale_lines = ServiceSaleLine.search([
                    ('service.fraction.sample', '=', sample.id),
                    ])
                if not sale_lines:
                    continue
                if self.start.party.allow_services_without_quotation:
                    ServiceSaleLine.delete(sale_lines)
                else:
                    raise UserError(gettext(error_msg))
        return super().transition_confirm()


class Sample(metaclass=PoolMeta):
    __name__ = 'lims.sample'

    sale_lines = fields.Function(fields.Many2Many('sale.line',
        None, None, 'Quotes'), 'get_sale_lines')

    def get_sale_lines(self, name):
        pool = Pool()
        ServiceSaleLine = pool.get('lims.service-sale.line')
        sale_lines = ServiceSaleLine.search([
            ('service.fraction.sample', '=', self.id),
            ])
        return [sl.sale_line.id for sl in sale_lines]


class Service(metaclass=PoolMeta):
    __name__ = 'lims.service'

    sale_lines = fields.Many2Many('lims.service-sale.line',
        'service', 'sale_line', 'Quotes', readonly=True)
    matching_quote_removed = fields.Many2One('sale.line',
        'Matching quote removed', readonly=True)

    @classmethod
    def create(cls, vlist):
        services = super().create(vlist)
        silent = Transaction().context.get('create_sample', False)
        cls.check_services_without_quotation(services, silent)
        return services

    @classmethod
    def copy(cls, services, default=None):
        new_service = super().copy(services, default)
        silent = Transaction().context.get('create_sample', False)
        cls.check_services_without_quotation(new_service, silent)
        return new_service

    @classmethod
    def check_services_without_quotation(cls, services, silent=False):
        pool = Pool()
        Warning = pool.get('res.user.warning')

        to_unlink = []
        for service in services:
            if not service.sale_lines:
                continue

            entry = service.entry
            allow_services_without_quotation = (
                entry.allow_services_without_quotation)
            error_key = 'lims_services_without_quotation@%s' % entry.number
            error_msg = 'lims_sale.msg_services_without_quotation'

            for sl in service.sale_lines:
                if (sl.quantity is None or sl.unlimited_quantity or
                        sl.quantity >= len(sl.services)):
                    continue
                if not allow_services_without_quotation:
                    raise UserError(gettext(error_msg))
                if not silent and Warning.check(error_key):
                    raise UserWarning(error_key, gettext(error_msg))
                service.matching_quote_removed = sl.id
                service.save()
                to_unlink.append(service)
        if to_unlink:
            cls.unlink_sale_lines(to_unlink)

    @classmethod
    def write(cls, *args):
        super().write(*args)
        actions = iter(args)
        for services, vals in zip(actions, actions):
            if vals.get('annulled'):
                cls.unlink_sale_lines(services)

    @classmethod
    def unlink_sale_lines(cls, services):
        pool = Pool()
        ServiceSaleLine = pool.get('lims.service-sale.line')
        sale_lines = ServiceSaleLine.search([
            ('service', 'in', [s.id for s in services]),
            ])
        if sale_lines:
            ServiceSaleLine.delete(sale_lines)


class Service2(metaclass=PoolMeta):
    __name__ = 'lims.service'

    def get_invoice_line(self):
        pool = Pool()
        InvoiceLine = pool.get('account.invoice.line')

        invoice_line = super().get_invoice_line()
        if not invoice_line:
            return

        digits = InvoiceLine.unit_price.digits[1]
        if self.sale_lines:
            for sale_line in self.sale_lines:
                if sale_line.product.id == self.analysis.product.id:
                    invoice_line['lims_sale_line_origin'] = sale_line.id
                    invoice_line['unit_price'] = sale_line.unit_price.quantize(
                        Decimal(str(10 ** -digits)))
        return invoice_line


class ServiceSaleLine(ModelSQL):
    'Service - Sale Line'
    __name__ = 'lims.service-sale.line'
    _table = 'lims_service_sale_line'

    service = fields.Many2One('lims.service', 'Service',
        ondelete='CASCADE', select=True, required=True)
    sale_line = fields.Many2One('sale.line', 'Sale Line',
        ondelete='CASCADE', select=True, required=True)

    @classmethod
    def create(cls, vlist):
        sale_lines = super().create(vlist)
        with Transaction().set_context(_check_access=False):
            sales = set(sl.sale_line.sale for sl in sale_lines)
        if sales:
            cls.process_sale(sales)
        return sale_lines

    @classmethod
    def delete(cls, sale_lines):
        with Transaction().set_context(_check_access=False):
            sales = set(sl.sale_line.sale for sl in sale_lines)
        super().delete(sale_lines)
        if sales:
            cls.process_sale(sales)

    @classmethod
    def process_sale(cls, sales):
        pool = Pool()
        Sale = pool.get('sale.sale')
        with Transaction().set_context(_check_access=False):
            Sale.__queue__.process(sales)
