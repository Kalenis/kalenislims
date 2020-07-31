# This file is part of lims_sale module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import logging
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.header import Header

from trytond.model import ModelSQL, ModelView, fields
from trytond.wizard import Wizard, StateView, StateTransition, Button
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Eval, Bool
from trytond.transaction import Transaction
from trytond.config import config
from trytond.tools import get_smtp_server

__all__ = ['Sale', 'SaleClause', 'SaleLine', 'SaleLoadServicesStart',
    'SaleLoadServices', 'SaleLoadAnalysisStart', 'SaleLoadAnalysis']
logger = logging.getLogger(__name__)


class Sale(metaclass=PoolMeta):
    __name__ = 'sale.sale'

    invoice_party = fields.Many2One('party.party', 'Invoice party',
        required=True, select=True,
        domain=[('id', 'in', Eval('invoice_party_domain'))],
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
    clauses = fields.Many2Many('sale.sale-sale.clause', 'sale', 'clause',
        'Clauses',
        states={'readonly': Eval('state') != 'draft'},
        depends=['state'])
    send_email = fields.Boolean('Send automatically by Email',
        states={'readonly': Eval('state') != 'draft'},
        depends=['state'])

    @classmethod
    def __setup__(cls):
        super(Sale, cls).__setup__()
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

    @fields.depends('party', 'invoice_party')
    def on_change_party(self):
        super(Sale, self).on_change_party()
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
        super(Sale, cls).quote(sales)
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

        msg = MIMEMultipart()
        msg['From'] = from_addr
        msg['To'] = to_addr
        msg['Reply-to'] = reply_to
        msg['Subject'] = Header(subject, 'utf-8')

        msg_body = MIMEBase('text', 'plain')
        msg_body.set_payload(body.encode('UTF-8'), 'UTF-8')
        msg.attach(msg_body)

        attachment = MIMEApplication(attachment_data['content'],
            Name=attachment_data['filename'], _subtype="pdf")
        attachment.add_header('content-disposition', 'attachment',
            filename=('utf-8', '', attachment_data['filename']))
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


class SaleClause(ModelSQL):
    'Sale - Clause'
    __name__ = 'sale.sale-sale.clause'
    _table = 'sale_sale_sale_clause'

    sale = fields.Many2One('sale.sale', 'Sale',
        ondelete='CASCADE', select=True, required=True)
    clause = fields.Many2One('sale.clause', 'Clause',
        ondelete='CASCADE', select=True, required=True)


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
            if analysis.included_analysis:
                for ia in analysis.included_analysis:
                    if not ia.included_analysis.product:
                        continue
                    if ia.included_analysis.id not in sale_services.keys():
                        if ia.included_analysis.type != 'set':
                            sale_services[ia.included_analysis.id] = {
                                'quantity': 1,
                                'unit':
                                    ia.included_analysis.product.default_uom.id,
                                'product': ia.included_analysis.product.id,
                                'method': ia.method.id if ia.method else None,
                                'description': ia.included_analysis.rec_name,
                                }
                        sale_services = get_sale_services(
                            ia.included_analysis, sale_services)
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
