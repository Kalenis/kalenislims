# This file is part of lims_sale module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import logging
from io import BytesIO
from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from PyPDF2 import PdfFileMerger
from PyPDF2.utils import PdfReadError
from decimal import Decimal

from trytond.model import ModelSQL, ModelView, fields
from trytond.wizard import Wizard, StateView, StateTransition, Button
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Eval, Bool
from trytond.transaction import Transaction
from trytond.config import config
from trytond.tools import get_smtp_server
from trytond.exceptions import UserError
from trytond.i18n import gettext
from trytond.modules.lims_report_html.html_template import LimsReport
from trytond.modules.sale.exceptions import SaleValidationError

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
            ['OR', ('active', '=', True),
                ('id', '=', Eval('template'))],
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
    services_completed = fields.Function(fields.Boolean('Services completed'),
        'get_services_completed')
    services_completed_manual = fields.Boolean('Services completed',
        states={
            'invisible': Eval('invoice_method') != 'service',
            'readonly': Eval('state') != 'processing',
            },
        depends=['invoice_method', 'state'])
    completion_percentage = fields.Function(fields.Numeric('Complete',
        digits=(1, 4)), 'get_completion_percentage')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.invoice_address.domain = [('party', '=', Eval('invoice_party'))]
        cls.invoice_address.depends.append('invoice_party')
        invoice_method = ('service', 'On Entry Confirmed')
        if invoice_method not in cls.invoice_method.selection:
            cls.invoice_method.selection.append(invoice_method)
        cls.invoice_state.states['invisible'] = (
            Eval('invoice_method') == 'service')
        cls.invoice_state.depends.append('invoice_method')
        cls.shipment_state.states['invisible'] = (
            Eval('invoice_method') == 'service')
        cls.shipment_state.depends.append('invoice_method')
        cls._buttons.update({
            'load_services': {
                'invisible': (Eval('state') != 'draft'),
                },
            'load_set_group': {
                'invisible': (Eval('state') != 'draft'),
                },
            })

    @staticmethod
    def default_services_completed_manual():
        return False

    @classmethod
    def view_attributes(cls):
        return super().view_attributes() + [
            ('//group[@id="links"]/link[@name="sale.act_shipment_form"]',
                'states', {
                    'invisible': Eval('invoice_method') == 'service',
                    }),
            ('//group[@id="links"]/link[@name="sale.act_return_form"]',
                'states', {
                    'invisible': Eval('invoice_method') == 'service',
                    }),
            ]

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

    def get_services_completed(self, name=None):
        pool = Pool()
        SaleLine = pool.get('sale.line')

        if self.services_completed_manual:
            return True

        sale_lines = SaleLine.search([
            ('sale', '=', self.id),
            ('type', '=', 'line'),
            ])
        if not sale_lines:
            return False
        for line in sale_lines:
            if line.unlimited_quantity:
                return False
            if not line.quantity:
                return False
            if line.quantity > len(line.services):
                return False
        return True

    def get_completion_percentage(self, name=None):
        pool = Pool()
        SaleLine = pool.get('sale.line')
        Sale = pool.get('sale.sale')

        sale_lines = SaleLine.search([
            ('sale', '=', self.id),
            ('type', '=', 'line'),
            ])
        if not sale_lines:
            return Decimal(0)

        completed = Decimal(0)
        total = Decimal(0)
        for line in sale_lines:
            if line.unlimited_quantity:
                continue
            if not line.quantity:
                continue
            completed += (line.amount / Decimal(line.quantity) *
                len(line.services))
            total += line.amount

        digits = Sale.completion_percentage.digits[1]
        return Decimal(
            Decimal(completed) / Decimal(total)
            ).quantize(Decimal(str(10 ** -digits)))

    def check_method(self):
        super().check_method()
        if (self.shipment_method == 'invoice'
                and self.invoice_method == 'service'):
            raise SaleValidationError(
                gettext('sale.msg_sale_invalid_method',
                    invoice_method=self.invoice_method_string,
                    shipment_method=self.shipment_method_string,
                    sale=self.rec_name))

    @classmethod
    @ModelView.button_action('lims_sale.wiz_sale_load_services')
    def load_services(cls, sales):
        pass

    @classmethod
    @ModelView.button_action('lims_sale.wiz_sale_load_set_group')
    def load_set_group(cls, sales):
        pass

    @classmethod
    def quote(cls, sales):
        super().quote(sales)
        cls.send_email_party(s for s in sales if s.send_email)

    @classmethod
    def send_email_party(cls, sales):
        from_addr = config.get('email', 'from')
        if not from_addr:
            logger.error("Missing configuration to send emails")
            return

        for sale in sales:
            to_addr = 'contacto@silix.com.ar'  # sale.party.email
            if not to_addr:
                logger.error("Missing address for '%s' to send email",
                    sale.party.rec_name)
                continue
            reply_to = sale.create_uid.email

            subject, body = sale._get_subject_body()
            attachment_data = sale._get_attachment()
            msg = cls.create_msg(from_addr, to_addr, reply_to, subject,
                body, attachment_data)
            cls.send_msg(from_addr, to_addr, msg, sale.number)

    def _get_subject_body(self):
        pool = Pool()
        Config = pool.get('sale.configuration')

        config = Config(1)
        subject = str(config.email_quotation_subject)
        body = str(config.email_quotation_body)
        return subject, body

    def _get_attachment(self):
        pool = Pool()
        SaleReport = pool.get('sale.sale', type='report')
        result = SaleReport.execute([self.id], {})

        data = {
            'content': result[1],
            'format': result[0],
            'mimetype': (result[0] == 'pdf' and 'pdf' or
                'vnd.oasis.opendocument.text'),
            'filename': '%s.%s' % (str(self.number), str(result[0])),
            'name': str(self.number),
            }
        return data

    @staticmethod
    def create_msg(from_addr, to_addr, reply_to, subject, body,
            attachment_data):
        if not (from_addr or to_addr):
            return None

        msg = MIMEMultipart('mixed')
        msg['From'] = from_addr
        msg['To'] = to_addr
        msg['Reply-to'] = reply_to
        msg['Subject'] = subject

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

    @staticmethod
    def send_msg(from_addr, to_addr, msg, task_number):
        success = False
        try:
            server = get_smtp_server()
            server.sendmail(from_addr, [to_addr], msg.as_string())
            server.quit()
            success = True
        except Exception:
            logger.error(
                "Unable to deliver email for task '%s'" % (task_number))
        return success

    def create_invoice(self):
        if self.invoice_method == 'service':
            return
        return super().create_invoice()

    def is_done(self):
        if self.invoice_method != 'service':
            return super().is_done()
        return self.services_completed


class Sale2(metaclass=PoolMeta):
    __name__ = 'sale.sale'

    def get_invoices(self, name):
        invoices = super().get_invoices(name)
        lims_invoices = set()
        for line in self.lines:
            for invoice_line in line.lims_invoice_lines:
                if invoice_line.invoice:
                    lims_invoices.add(invoice_line.invoice.id)
        return invoices + list(lims_invoices)

    @classmethod
    def search_invoices(cls, name, clause):
        return ['OR',
            ('lines.invoice_lines.invoice' + clause[0].lstrip(name),) +
            tuple(clause[1:]),
            ('lines.lims_invoice_lines.invoice' + clause[0].lstrip(name),) +
            tuple(clause[1:]),
            ]


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
    services = fields.Many2Many('lims.service-sale.line',
        'sale_line', 'service', 'Services', readonly=True)
    services_available = fields.Function(fields.Float('Services available',
        digits=(16, Eval('unit_digits', 2)), depends=['unit_digits']),
        'on_change_with_services_available')
    services_completed = fields.Function(fields.Boolean('Services completed'),
        'on_change_with_services_completed')
    services_completed_icon = fields.Function(fields.Char(
        'Services completed Icon'), 'get_services_completed_icon')
    additional_origin = fields.Many2One('sale.line', 'Origin of additional')

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

    @classmethod
    def create(cls, vlist):
        sale_lines = super().create(vlist)
        cls.create_additional_services(sale_lines)
        return sale_lines

    @classmethod
    def create_additional_services(cls, sale_lines):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Typification = pool.get('lims.typification')
        Analysis = pool.get('lims.analysis')

        additional_services = {}
        for sale_line in sale_lines:
            if (not sale_line.product_type or not sale_line.matrix or
                    not sale_line.analysis):
                continue

            analysis = [(sale_line.analysis.id,
                sale_line.method and sale_line.method.id or None)]
            analysis.extend(Analysis.get_included_analysis_method(
                sale_line.analysis.id))

            for a in analysis:
                clause = [
                    ('product_type', '=', sale_line.product_type.id),
                    ('matrix', '=', sale_line.matrix.id),
                    ('analysis', '=', a[0]),
                    ('valid', '=', True),
                    ]
                if a[1]:
                    clause.append(('method', '=', a[1]))
                else:
                    clause.append(('by_default', '=', True))
                typifications = Typification.search(clause)
                if not typifications:
                    continue
                typification = typifications[0]
                key = sale_line.sale.id

                if typification.additional and typification.additional.product:
                    additional = typification.additional
                    if key not in additional_services:
                        additional_services[key] = {}
                    if additional.id not in additional_services[key]:

                        additional_services[key][additional.id] = {
                            'product': additional.product.id,
                            'quantity': sale_line.quantity,
                            'unit': additional.product.default_uom.id,
                            'product_type': sale_line.product_type.id,
                            'matrix': sale_line.matrix.id,
                            'method': None,
                            'additional_origin': sale_line.id,
                            }

                if typification.additionals:
                    if key not in additional_services:
                        additional_services[key] = {}
                    for additional in typification.additionals:
                        if not additional.product:
                            continue
                        if additional.id not in additional_services[key]:

                            cursor.execute('SELECT method '
                                'FROM "' + Typification._table + '" '
                                'WHERE product_type = %s '
                                    'AND matrix = %s '
                                    'AND analysis = %s '
                                    'AND valid IS TRUE '
                                    'AND by_default IS TRUE',
                                (sale_line.product_type.id,
                                    sale_line.matrix.id, additional.id))
                            res = cursor.fetchone()
                            method_id = res and res[0] or None

                            additional_services[key][additional.id] = {
                                'product': additional.product.id,
                                'quantity': sale_line.quantity,
                                'unit': additional.product.default_uom.id,
                                'product_type': sale_line.product_type.id,
                                'matrix': sale_line.matrix.id,
                                'method': method_id,
                                'additional_origin': sale_line.id,
                                }

        if additional_services:
            sale_lines = []
            for sale_id, analysis in additional_services.items():
                for analysis_id, service_data in analysis.items():
                    if cls.search([
                            ('sale', '=', sale_id),
                            ('analysis', '=', analysis_id),
                            ]):
                        continue
                    sale_line = cls(
                        quantity=service_data['quantity'],
                        unit=service_data['unit'],
                        product_type=service_data['product_type'],
                        matrix=service_data['matrix'],
                        analysis=analysis_id,
                        product=service_data['product'],
                        method=service_data['method'],
                        additional_origin=service_data['additional_origin'],
                        sale=sale_id,
                        )
                    sale_line.on_change_product()
                    sale_lines.append(sale_line)
            cls.save(sale_lines)

    @classmethod
    def delete(cls, sale_lines):
        cls.delete_additional_services(sale_lines)
        super().delete(sale_lines)

    @classmethod
    def delete_additional_services(cls, sale_lines):
        lines_to_delete = [l.id for l in sale_lines]
        additionals = cls.search([
            ('additional_origin', 'in', lines_to_delete),
            ])
        additionals_to_delete = [l for l in additionals
            if l.id not in lines_to_delete]
        if additionals_to_delete:
            cls.delete(additionals_to_delete)

    @classmethod
    def copy(cls, sale_lines, default=None):
        if default is None:
            default = {}
        current_default = default.copy()
        current_default['services'] = None
        current_default['additional_origin'] = None
        return super().copy(sale_lines, default=current_default)

    @fields.depends('unlimited_quantity', 'quantity', 'services')
    def on_change_with_services_available(self, name=None):
        if self.quantity is None:
            return None
        if self.unlimited_quantity:
            return None
        res = self.quantity - len(self.services)
        if res < 0:
            return 0
        return res

    @fields.depends('unlimited_quantity', 'quantity', 'services')
    def on_change_with_services_completed(self, name=None):
        if self.unlimited_quantity:
            return False
        if not self.quantity:
            return False
        if self.quantity > len(self.services):
            return False
        return True

    def get_services_completed_icon(self, name):
        if self.services_completed:
            return 'lims-red'
        return 'lims-green'


class SaleLine2(metaclass=PoolMeta):
    __name__ = 'sale.line'

    lims_invoice_lines = fields.One2Many('account.invoice.line',
        'lims_sale_line_origin', 'Invoice Lines', readonly=True)


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
