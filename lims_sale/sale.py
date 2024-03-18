# This file is part of lims_sale module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import logging
from io import BytesIO
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from PyPDF2 import PdfFileMerger
from PyPDF2.utils import PdfReadError

from trytond.model import ModelSQL, ModelView, fields
from trytond.wizard import Wizard, StateView, StateTransition, Button
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Eval, Bool
from trytond.transaction import Transaction
from trytond.config import config as tconfig
from trytond.tools import get_smtp_server
from trytond.exceptions import UserError
from trytond.i18n import gettext
from trytond.modules.lims_report_html.html_template import LimsReport

logger = logging.getLogger(__name__)


class Sale(metaclass=PoolMeta):
    __name__ = 'sale.sale'

    invoice_party = fields.Many2One('party.party', 'Invoice party',
        required=True, select=True,
        domain=['OR', ('id', '=', Eval('invoice_party')),
            ('id', 'in', Eval('invoice_party_domain'))],
        states={
            'readonly': ((Eval('state') != 'draft') |
                (Eval('lines', [0]) & Eval('party'))),
            },
        depends=['invoice_party_domain', 'state'])
    invoice_party_domain = fields.Function(fields.Many2Many('party.party',
        None, None, 'Invoice party domain'),
        'on_change_with_invoice_party_domain')
    purchase_order = fields.Char('Purchase order')
    expiration_date = fields.Date('Expiration date', required=True,
        states={'readonly': ~Eval('state').in_(['draft', 'quotation'])},
        depends=['state'])
    template = fields.Many2One('lims.report.template',
        'Sale Template', domain=[
            ('report_name', '=', 'sale.sale'),
            ('type', 'in', [None, 'base']),
            ],
        states={'readonly': Eval('state') != 'draft'},
        depends=['state'])
    clause_template = fields.Many2One('sale.clause.template',
        'Clauses Template', depends=['state'],
        states={'readonly': Eval('state') != 'draft'})
    sections = fields.One2Many('sale.sale.section', 'sale', 'Sections')
    previous_sections = fields.Function(fields.One2Many(
        'sale.sale.section', 'sale', 'Previous Sections',
        domain=[('position', '=', 'previous')]),
        'get_previous_sections', setter='set_previous_sections')
    following_sections = fields.Function(fields.One2Many(
        'sale.sale.section', 'sale', 'Following Sections',
        domain=[('position', '=', 'following')]),
        'get_following_sections', setter='set_following_sections')
    clauses = fields.Text('Clauses',
        states={'readonly': Eval('state') != 'draft'},
        depends=['state'])
    send_email = fields.Boolean('Send automatically by Email',
        states={'readonly': ~Eval('state').in_(['draft', 'quotation'])},
        depends=['state'])
    sent = fields.Boolean('Sent', readonly=True)
    sent_date = fields.DateTime('Sent date', readonly=True)
    mailings = fields.One2Many('sale.sale.mailing',
        'sale', 'Mailings', readonly=True)

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.invoice_address.domain = [('party', '=', Eval('invoice_party'))]
        cls.invoice_address.depends.append('invoice_party')
        cls._buttons.update({
            'load_services': {
                'invisible': (Eval('state') != 'draft'),
                },
            'load_set_group': {
                'invisible': (Eval('state') != 'draft'),
                },
            })

    @classmethod
    def view_attributes(cls):
        attributes = super().view_attributes()
        if Transaction().context.get('modify_header'):
            attributes.extend([
                ('//group[@id="lims_buttons"]', 'states', {'invisible': True}),
                ('//page[@id="lims_report"]', 'states', {'invisible': True}),
                ('//page[@id="lims_email"]', 'states', {'invisible': True}),
                ])
        return attributes

    @fields.depends('party', 'invoice_party')
    def on_change_party(self):
        super().on_change_party()
        self.invoice_party = None
        if self.party:
            invoice_party_domain = self.on_change_with_invoice_party_domain()
            if len(invoice_party_domain) == 1:
                self.invoice_party = invoice_party_domain[0]

    @fields.depends('party', '_parent_party.relations')
    def on_change_with_invoice_party_domain(self, name=None):
        pool = Pool()
        Config = pool.get('lims.configuration')

        config_ = Config(1)
        parties = []
        if self.party:
            parties.append(self.party.id)
            if config_.invoice_party_relation_type:
                parties.extend([r.to.id for r in self.party.relations
                    if r.type == config_.invoice_party_relation_type])
        return parties

    @fields.depends('invoice_party')
    def on_change_invoice_party(self):
        self.invoice_address = None
        if self.invoice_party:
            self.invoice_address = self.invoice_party.address_get(
                type='invoice')

    @fields.depends('template', '_parent_template.sections', 'sections',
        '_parent_template.clause_template',
        methods=['on_change_clause_template'])
    def on_change_template(self):
        if self.template and self.template.sections:
            sections = {}
            for s in self.sections + self.template.sections:
                sections[s.name] = {
                    'name': s.name,
                    'data': s.data,
                    'data_id': s.data_id,
                    'position': s.position,
                    'order': s.order,
                    }
            self.sections = sections.values()
        if self.template and self.template.clause_template:
            self.clause_template = self.template.clause_template
            self.on_change_clause_template()

    @fields.depends('clause_template', '_parent_clause_template.content')
    def on_change_clause_template(self):
        if self.clause_template:
            self.clauses = self.clause_template.content

    def get_previous_sections(self, name):
        return [s.id for s in self.sections if s.position == 'previous']

    @classmethod
    def set_previous_sections(cls, sections, name, value):
        if not value:
            return
        cls.write(sections, {'sections': value})

    def get_following_sections(self, name):
        return [s.id for s in self.sections if s.position == 'following']

    @classmethod
    def set_following_sections(cls, sections, name, value):
        if not value:
            return
        cls.write(sections, {'sections': value})

    @classmethod
    @ModelView.button_action('lims_sale.wiz_sale_load_services')
    def load_services(cls, sales):
        pass

    @classmethod
    @ModelView.button_action('lims_sale.wiz_sale_load_set_group')
    def load_set_group(cls, sales):
        pass

    @classmethod
    def cron_send_quotation(cls):
        '''
        Cron - Send Quotation
        '''
        logger.info('Cron - Send Quotation: INIT')
        SendQuotation = Pool().get('lims_sale.send_quotation',
            type='wizard')

        sales = cls.search([
            ('state', 'in', ['quotation', 'confirmed', 'processing']),
            ('send_email', '=', True),
            ('sent', '=', False),
            ])

        session_id, _, _ = SendQuotation.create()
        send_quotation = SendQuotation(session_id)
        with Transaction().set_context(active_ids=[sale.id
                for sale in sales]):
            send_quotation.transition_send()

        logger.info('Cron - Send Quotation: END')
        return True

    def get_attached_report(self):
        pool = Pool()
        SaleReport = pool.get('sale.sale', type='report')
        report = SaleReport.execute([self.id], {})

        data = {
            'content': report[1],
            'format': report[0],
            'mimetype': (report[0] == 'pdf' and 'pdf' or
                'vnd.oasis.opendocument.text'),
            'filename': '%s.%s' % (str(self.number), str(report[0])),
            'name': str(self.number),
            }
        return data


class SaleMailing(ModelSQL, ModelView):
    'Sale Mailing'
    __name__ = 'sale.sale.mailing'

    sale = fields.Many2One('sale.sale', 'Sale',
        required=True, ondelete='CASCADE', select=True)
    date = fields.Function(fields.DateTime('Date'),
       'get_date', searcher='search_date')
    addresses = fields.Char('Addresses', readonly=True)

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order.insert(0, ('date', 'DESC'))

    def get_date(self, name):
        return self.create_date.replace(microsecond=0)

    @classmethod
    def search_date(cls, name, clause):
        cursor = Transaction().connection.cursor()
        operator_ = clause[1:2][0]
        cursor.execute('SELECT id '
            'FROM "' + cls._table + '" '
            'WHERE create_date' + operator_ + ' %s',
            clause[2:3])
        return [('id', 'in', [x[0] for x in cursor.fetchall()])]

    @classmethod
    def order_date(cls, tables):
        return cls.create_date.convert_order('create_date', tables, cls)


class SaleSection(ModelSQL, ModelView):
    'Sale Section'
    __name__ = 'sale.sale.section'
    _order_name = 'order'

    sale = fields.Many2One('sale.sale', 'Sale',
        ondelete='CASCADE', select=True, required=True)
    name = fields.Char('Name', required=True)
    data = fields.Binary('File', filename='name', required=True,
        file_id='data_id', store_prefix='sale_section')
    data_id = fields.Char('File ID', readonly=True)
    position = fields.Selection([
        ('previous', 'Previous'),
        ('following', 'Following'),
        ], 'Position', required=True)
    order = fields.Integer('Order')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order.insert(0, ('order', 'ASC'))

    @classmethod
    def validate(cls, sections):
        super().validate(sections)
        merger = PdfFileMerger(strict=False)
        for section in sections:
            filedata = BytesIO(section.data)
            try:
                merger.append(filedata)
            except PdfReadError:
                raise UserError(gettext('lims_report_html.msg_section_pdf'))


class SaleLine(metaclass=PoolMeta):
    __name__ = 'sale.line'

    purchase_order = fields.Char('PO Nº')
    product_type = fields.Many2One('lims.product.type', 'Product type',
        domain=['OR', ('id', '=', Eval('product_type')),
            ('id', 'in', Eval('product_type_domain'))],
        states={
            'readonly': Eval('sale_state') != 'draft',
            'invisible': Eval('type') != 'line',
            },
        depends=['product_type_domain', 'sale_state', 'type'])
    product_type_domain = fields.Function(fields.Many2Many('lims.product.type',
        None, None, 'Product type domain'),
        'on_change_with_product_type_domain')
    matrix = fields.Many2One('lims.matrix', 'Matrix',
        domain=['OR', ('id', '=', Eval('matrix')),
            ('id', 'in', Eval('matrix_domain'))],
        states={
            'readonly': Eval('sale_state') != 'draft',
            'invisible': Eval('type') != 'line',
            },
        depends=['matrix_domain', 'sale_state', 'type'])
    matrix_domain = fields.Function(fields.Many2Many('lims.matrix',
        None, None, 'Matrix domain'), 'on_change_with_matrix_domain')
    analysis = fields.Many2One('lims.analysis', 'Service',
        domain=['OR', ('id', '=', Eval('analysis')),
            ('id', 'in', Eval('analysis_domain'))],
        states={
            'readonly': Eval('sale_state') != 'draft',
            'invisible': Eval('type') != 'line',
            },
        depends=['analysis_domain', 'sale_state', 'type'])
    analysis_domain = fields.Function(fields.Many2Many('lims.analysis',
        None, None, 'Analysis domain'), 'on_change_with_analysis_domain')
    method = fields.Many2One('lims.lab.method', 'Method',
        domain=['OR', ('id', '=', Eval('method')),
            ('id', 'in', Eval('method_domain'))],
        states={
            'invisible': Bool(Eval('method_invisible')),
            'readonly': Eval('sale_state') != 'draft',
            },
        depends=['method_domain', 'method_invisible', 'sale_state'])
    method_invisible = fields.Function(fields.Boolean('Method invisible'),
        'on_change_with_method_invisible')
    method_domain = fields.Function(fields.Many2Many('lims.lab.method',
        None, None, 'Method domain'), 'on_change_with_method_domain')
    expiration_date = fields.Date('Expiration date',
        states={'readonly': Eval('sale_state') != 'draft'},
        depends=['sale_state'])
    print_price = fields.Boolean('Print price on quotation',
        states={'readonly': Eval('sale_state') != 'draft'},
        depends=['sale_state'])
    print_service_detail = fields.Boolean('Print service detail',
        states={
            'invisible': Bool(Eval('print_service_detail_invisible')),
            'readonly': Eval('sale_state') != 'draft',
            },
        depends=['print_service_detail_invisible', 'sale_state'])
    print_service_detail_invisible = fields.Function(fields.Boolean(
        'Print service detail invisible'),
        'on_change_with_print_service_detail_invisible')
    unlimited_quantity = fields.Boolean('Unlimited quantity',
        states={'readonly': Eval('sale_state') != 'draft'},
        depends=['sale_state'])
    samples = fields.Many2Many('lims.sample-sale.line',
        'sale_line', 'sample', 'Samples', readonly=True)

    @staticmethod
    def default_product_type_domain():
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Typification = pool.get('lims.typification')

        cursor.execute('SELECT DISTINCT(product_type) '
            'FROM "' + Typification._table + '" '
            'WHERE valid')
        res = cursor.fetchall()
        if not res:
            return []
        return [x[0] for x in res]

    def on_change_with_product_type_domain(self, name=None):
        return self.default_product_type_domain()

    @fields.depends('product_type', 'matrix', 'matrix_domain')
    def on_change_product_type(self):
        matrix_domain = []
        matrix = None
        if self.product_type:
            matrix_domain = self.on_change_with_matrix_domain()
            if len(matrix_domain) == 1:
                matrix = matrix_domain[0]
        self.matrix_domain = matrix_domain
        self.matrix = matrix

    @fields.depends('product_type')
    def on_change_with_matrix_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Typification = pool.get('lims.typification')

        if not self.product_type:
            return []

        cursor.execute('SELECT DISTINCT(matrix) '
            'FROM "' + Typification._table + '" '
            'WHERE product_type = %s '
            'AND valid',
            (self.product_type.id,))
        res = cursor.fetchall()
        if not res:
            return []
        return [x[0] for x in res]

    @fields.depends('product_type', 'matrix')
    def on_change_with_analysis_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Typification = pool.get('lims.typification')
        CalculatedTypification = pool.get('lims.typification.calculated')
        Analysis = pool.get('lims.analysis')

        if not self.product_type or not self.matrix:
            return []

        cursor.execute('SELECT DISTINCT(analysis) '
            'FROM "' + Typification._table + '" '
            'WHERE product_type = %s '
                'AND matrix = %s '
                'AND valid',
            (self.product_type.id, self.matrix.id))
        typified_analysis = [a[0] for a in cursor.fetchall()]
        if not typified_analysis:
            return []

        cursor.execute('SELECT id '
            'FROM "' + Analysis._table + '" '
            'WHERE type = \'analysis\' '
                'AND behavior IN (\'normal\', \'internal_relation\') '
                'AND disable_as_individual IS TRUE '
                'AND state = \'active\'')
        disabled_analysis = [a[0] for a in cursor.fetchall()]
        if disabled_analysis:
            typified_analysis = list(set(typified_analysis) -
                set(disabled_analysis))

        cursor.execute('SELECT DISTINCT(analysis) '
            'FROM "' + CalculatedTypification._table + '" '
            'WHERE product_type = %s '
                'AND matrix = %s',
            (self.product_type.id, self.matrix.id))
        typified_sets_groups = [a[0] for a in cursor.fetchall()]

        cursor.execute('SELECT id '
            'FROM "' + Analysis._table + '" '
            'WHERE behavior = \'additional\' '
                'AND state = \'active\'')
        additional_analysis = [a[0] for a in cursor.fetchall()]

        return typified_analysis + typified_sets_groups + additional_analysis

    @fields.depends('product', 'analysis', '_parent_analysis.methods')
    def on_change_with_method_domain(self, name=None):
        Analysis = Pool().get('lims.analysis')
        if self.analysis:
            return [m.id for m in self.analysis.methods]
        if self.product:
            res = Analysis.search([
                ('product', '=', self.product.id),
                ('type', '=', 'analysis'),
                ])
            if res:
                return [m.id for m in res[0].methods]
        return []

    @staticmethod
    def default_method_invisible():
        return True

    @fields.depends('product', 'analysis', '_parent_analysis.type')
    def on_change_with_method_invisible(self, name=None):
        Analysis = Pool().get('lims.analysis')
        if self.analysis and self.analysis.type == 'analysis':
            return False
        if (self.product and Analysis.search_count([
                    ('product', '=', self.product.id),
                    ('type', '=', 'analysis'),
                    ]) > 0):
                return False
        return True

    @staticmethod
    def default_print_service_detail_invisible():
        return True

    @fields.depends('product', 'analysis', '_parent_analysis.type')
    def on_change_with_print_service_detail_invisible(self, name=None):
        Analysis = Pool().get('lims.analysis')
        if self.analysis and self.analysis.type in ('set', 'group'):
            return False
        if (self.product and Analysis.search_count([
                    ('product', '=', self.product.id),
                    ('type', 'in', ('set', 'group')),
                    ]) > 0):
                return False
        return True

    @fields.depends('analysis')
    def on_change_analysis(self):
        product = None
        if self.analysis and self.analysis.product:
            product = self.analysis.product.id
        self.product = product
        self.on_change_product()


class SaleLoadServicesStart(ModelView):
    'Load Services from Entry'
    __name__ = 'sale.load_services.start'

    entry = fields.Many2One('lims.entry', 'Entry', required=True,
        domain=[('invoice_party', '=', Eval('party'))], depends=['party'])
    party = fields.Many2One('party.party', 'Party')


class SaleLoadServices(Wizard):
    'Load Services from Entry'
    __name__ = 'sale.load_services'

    start = StateView('sale.load_services.start',
        'lims_sale.sale_load_services_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Load', 'load', 'tryton-ok', default=True),
            ])
    load = StateTransition()

    def default_start(self, fields):
        pool = Pool()
        Sale = pool.get('sale.sale')
        sale = Sale(Transaction().context['active_id'])
        return {
            'party': sale.party.id,
            }

    def transition_load(self):
        pool = Pool()
        Service = pool.get('lims.service')
        SaleLine = pool.get('sale.line')

        sale_id = Transaction().context['active_id']

        sale_services = {}
        with Transaction().set_context(_check_access=False):
            services = Service.search([
                ('entry', '=', self.start.entry.id),
                ('fraction.cie_fraction_type', '=', False),
                ('annulled', '=', False),
                ])
        for service in services:
            if hasattr(service.fraction.type, 'invoiceable') and (
                    not service.fraction.type.invoiceable):
                continue
            if not service.analysis.product:
                continue
            if service.analysis.id not in sale_services:
                sale_services[service.analysis.id] = {
                    'quantity': 0,
                    'unit': service.analysis.product.default_uom.id,
                    'product': service.analysis.product.id,
                    'description': service.analysis.rec_name,
                    }
            sale_services[service.analysis.id]['quantity'] += 1

        sale_lines = []
        for service in sale_services.values():
            sale_line = SaleLine(
                quantity=service['quantity'],
                unit=service['unit'],
                product=service['product'],
                description=service['description'],
                sale=sale_id,
                )
            sale_line.on_change_product()
            sale_lines.append(sale_line)
        SaleLine.save(sale_lines)
        return 'end'


class SaleLoadAnalysisStart(ModelView):
    'Load Analysis from Set/Group'
    __name__ = 'sale.load_set_group.start'

    analysis = fields.Many2One('lims.analysis', 'Set/Group', required=True,
        domain=[('type', 'in', ['set', 'group'])])


class SaleLoadAnalysis(Wizard):
    'Load Analysis from Set/Group'
    __name__ = 'sale.load_set_group'

    start = StateView('sale.load_set_group.start',
        'lims_sale.sale_load_set_group_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Load', 'load', 'tryton-ok', default=True),
            ])
    load = StateTransition()

    def transition_load(self):
        pool = Pool()
        SaleLine = pool.get('sale.line')

        sale_id = Transaction().context['active_id']

        def get_sale_services(analysis, sale_services={}):
            if not analysis.included_analysis:
                return sale_services
            for ia in analysis.included_analysis:
                included = ia.included_analysis
                if not included.product:
                    continue
                if included.id not in sale_services.keys():
                    if included.type != 'set':
                        sale_services[included.id] = {
                            'quantity': 1,
                            'unit': included.product.default_uom.id,
                            'product': included.product.id,
                            'method': ia.method.id if ia.method else None,
                            'description': included.rec_name,
                            }
                    sale_services = get_sale_services(included, sale_services)
            return sale_services

        sale_services = get_sale_services(self.start.analysis)

        sale_lines = []
        for service in sale_services.values():
            sale_line = SaleLine(
                quantity=service['quantity'],
                unit=service['unit'],
                product=service['product'],
                method=service['method'],
                sale=sale_id,
                )
            sale_line.on_change_product()
            sale_lines.append(sale_line)
        SaleLine.save(sale_lines)
        return 'end'


class SendQuotationStart(ModelView):
    'Send Quotation'
    __name__ = 'lims_sale.send_quotation.start'

    summary = fields.Text('Summary', readonly=True)


class SendQuotationSucceed(ModelView):
    'Send Quotation'
    __name__ = 'lims_sale.send_quotation.succeed'


class SendQuotationFailed(ModelView):
    'Send Quotation'
    __name__ = 'lims_sale.send_quotation.failed'

    sales_not_sent = fields.Many2Many('sale.sale',
        None, None, 'Quotations not sent', readonly=True)


class SendQuotation(Wizard):
    'Send Quotation'
    __name__ = 'lims_sale.send_quotation'

    start = StateView('lims_sale.send_quotation.start',
        'lims_sale.send_quotation_start_view', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Send', 'send', 'tryton-ok', default=True),
            ])
    send = StateTransition()
    succeed = StateView('lims_sale.send_quotation.succeed',
        'lims_sale.send_quotation_succeed_view', [
            Button('Ok', 'end', 'tryton-ok', default=True),
            ])
    failed = StateView('lims_sale.send_quotation.failed',
        'lims_sale.send_quotation_failed_view', [
            Button('Ok', 'end', 'tryton-ok', default=True),
            ])

    def default_start(self, fields):
        Sale = Pool().get('sale.sale')

        summary = ''

        context = Transaction().context
        model = context.get('active_model', None)
        if model and model == 'ir.ui.menu':
            # If it was executed from `menu item`, then search ids
            sales = Sale.search([
                ('state', 'in', ['quotation', 'confirmed', 'processing']),
                ('send_email', '=', True),
                ('sent', '=', False),
                ])
        else:
            # If it was executed from `actions`, then use context ids
            sales = Sale.browse(context['active_ids'])

        for group in self.get_grouped_sales(sales).values():
            group['sales_ready'] = []
            group['to_addrs'] = {}

            for sale in group['records']:
                if sale.state in ['draft']:
                    continue
                group['sales_ready'].append(sale)
                group['to_addrs'].update(self.get_sale_addrs(sale))

            if not group['sales_ready']:
                continue

            addresses = ['"%s" <%s>' % (v, k)
                for k, v in group['to_addrs'].items()]
            summary += '%s\n - TO: %s\n\n' % (
                ', '.join([r.number for r in group['sales_ready']]),
                ', '.join(addresses))

        default = {'summary': summary}
        return default

    def transition_send(self):
        logger.info('Send Quotation: INIT')
        Sale = Pool().get('sale.sale')

        from_addr = tconfig.get('email', 'from')
        if not from_addr:
            logger.warning('Send Quotation: FAILED')
            self.failed.sales_not_sent = []
            return 'failed'

        context = Transaction().context
        model = context.get('active_model', None)
        if model and model == 'ir.ui.menu':
            # If it was executed from `menu item`, then search ids
            sales = Sale.search([
                ('state', 'in', ['quotation', 'confirmed', 'processing']),
                ('send_email', '=', True),
                ('sent', '=', False),
                ])
            logger.info('Send Quotation: '
                'Processing all Quotations')
        else:
            # If it was executed from `actions` or `cron`, then use context ids
            sales = Sale.browse(context['active_ids'])
            logger.info('Send Quotation: '
                'Processing context Quotations')

        sales_not_sent = []
        for group in self.get_grouped_sales(sales).values():
            group['sales_ready'] = []
            group['to_addrs'] = {}
            group['reply_to'] = []

            for sale in group['records']:
                logger.info('Send Quotation: %s', sale.number)
                if sale.state in ['draft']:
                    continue
                group['sales_ready'].append(sale)
                group['to_addrs'].update(self.get_sale_addrs(sale))
                group['reply_to'].append(sale.create_uid.email)

            if not group['sales_ready']:
                continue

            # Email sending
            to_addrs = list(set(group['to_addrs'].keys()))
            if not to_addrs:
                sales_not_sent.extend(group['sales_ready'])
                logger.warning('Send Quotation: Missing addresses')
                continue
            logger.info('Send Quotation: To addresses: %s',
                ', '.join(to_addrs))

            reply_to = list(set(group['reply_to']))
            subject, body = self._get_subject_body()

            attachments_data = []
            for r in group['sales_ready']:
                attachments_data.append(r.get_attached_report())

            msg = self._create_msg(from_addr, to_addrs, reply_to, subject,
                body, attachments_data)
            sent = self._send_msg(from_addr, to_addrs, msg)
            if not sent:
                sales_not_sent.extend(group['sales_ready'])
                logger.warning('Send Quotation: Not sent')
                continue
            logger.info('Send Quotation: Sent')

            addresses = ', '.join(['"%s" <%s>' % (v, k)
                    for k, v in group['to_addrs'].items()])
            Sale.write(group['sales_ready'], {
                'sent': True, 'sent_date': datetime.now(),
                'mailings': [('create', [{'addresses': addresses}])],
                })
            Transaction().commit()

        if sales_not_sent:
            logger.warning('Send Quotation: FAILED')
            self.failed.sales_not_sent = sales_not_sent
            return 'failed'

        logger.info('Send Quotation: SUCCEED')
        return 'succeed'

    def get_grouped_sales(self, sales):
        res = {}
        for sale in sales:
            key = sale.party.id
            if key not in res:
                res[key] = {
                    'records': [],
                    }
            res[key]['records'].append(sale)
        return res

    def get_sale_addrs(self, sale):
        to_addrs = {}
        for contact in sale.party.addresses:
            if contact.invoice_contact:
                to_addrs[contact.email] = contact.party_full_name
        return to_addrs

    def _get_subject_body(self):
        pool = Pool()
        Config = pool.get('sale.configuration')
        User = pool.get('res.user')
        Lang = pool.get('ir.lang')

        config = Config(1)

        lang = User(Transaction().user).language
        if not lang:
            lang, = Lang.search([
                    ('code', '=', 'en'),
                    ], limit=1)

        with Transaction().set_context(language=lang.code):
            subject = str(config.email_quotation_subject)
            body = str(config.email_quotation_body)
        return subject, body

    def _create_msg(self, from_addr, to_addrs, reply_to, subject, body,
            attachments_data=[]):
        if not to_addrs:
            return None

        msg = MIMEMultipart('mixed')
        msg['From'] = from_addr
        msg['Reply-to'] = ', '.join(reply_to)
        msg['To'] = ', '.join(to_addrs)
        msg['Subject'] = subject

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

    def _send_msg(self, from_addr, to_addrs, msg):
        to_addrs = list(set(to_addrs))
        success = False
        try:
            server = get_smtp_server()
            server.sendmail(from_addr, to_addrs, msg.as_string())
            server.quit()
            success = True
        except Exception as e:
            logger.error('Send Quotation: Unable to deliver mail')
            logger.error(str(e))
        return success

    def default_failed(self, fields):
        default = {
            'sales_not_sent': [f.id for f in self.failed.sales_not_sent],
            }
        return default


class SaleReport(LimsReport, metaclass=PoolMeta):
    __name__ = 'sale.sale'

    @classmethod
    def execute(cls, ids, data):
        Sale = Pool().get('sale.sale')

        if data is None:
            data = {}
        current_data = data.copy()

        if len(ids) > 1:
            raise UserError(gettext(
                'lims_report_html.msg_print_multiple_record'))

        sale = Sale(ids[0])
        template = sale.template
        if template and template.type == 'base':  # HTML
            result = cls.execute_html_lims_report(ids, current_data)
        else:
            current_data['action_id'] = None
            if template and template.report:
                current_data['action_id'] = template.report.id
            result = cls.execute_custom_lims_report(ids, current_data)

        return result
