# This file is part of lims_sale_industry module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelSQL, ModelView, fields
from trytond.wizard import Wizard, StateView, StateTransition, StateReport, \
    StateAction, Button
from trytond.report import Report
from trytond.pool import PoolMeta, Pool
from trytond.pyson import PYSONEncoder, Eval, And, Bool, If, Or
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.i18n import gettext

__all__ = ['Sale', 'SalePlant', 'SaleEquipment', 'SaleComponent',
    'SaleContact', 'SaleLine', 'SaleLinePlant', 'SaleLineEquipment',
    'SaleLineComponent', 'SaleAddProductKitStart', 'SaleAddProductKit',
    'SalePrintLabelStart', 'SalePrintLabel', 'SaleLabel', 'SaleLabelShipping',
    'SaleLabelReturn', 'SaleSearchLabelStart', 'SaleSearchLabel']


class Sale(metaclass=PoolMeta):
    __name__ = 'sale.sale'

    _states = {'readonly': Eval('state') != 'draft'}

    lubrication_plan = fields.Boolean('Lubrication plan',
        states=_states, depends=['state'])
    plants = fields.Many2Many('sale.sale-lims.plant',
        'sale', 'plant', 'Plants',
        domain=[('party', '=', Eval('party'))],
        states=_states, depends=['party', 'state'])
    equipments = fields.Many2Many('sale.sale-lims.equipment',
        'sale', 'equipment', 'Equipments',
        domain=[('plant', 'in', Eval('plants'))],
        states=_states, depends=['plants', 'state'])
    components = fields.Many2Many('sale.sale-lims.component',
        'sale', 'component', 'Components',
        domain=[('equipment', 'in', Eval('equipments'))],
        states=_states, depends=['equipments', 'state'])
    contacts = fields.Many2Many('sale.sale-party.address',
        'sale', 'address', 'Contacts',
        domain=[('id', 'in', Eval('contacts_domain'))],
        states=_states, depends=['contacts_domain', 'state'])
    contacts_domain = fields.Function(fields.Many2Many('party.address',
        None, None, 'Contacts domain'), 'on_change_with_contacts_domain')
    label_from = fields.Integer('Label from', readonly=True)
    label_to = fields.Integer('Label to', readonly=True)

    del _states

    @classmethod
    def __setup__(cls):
        super(Sale, cls).__setup__()
        cls.invoice_address.domain = [('party', '=', Eval('invoice_party'))]
        cls.invoice_address.depends.append('invoice_party')
        cls.lines.depends.extend(['plants', 'equipments', 'components'])
        cls._buttons.update({
            'load_services': {
                'invisible': (Eval('state') != 'draft'),
                },
            })

    @fields.depends('equipments', 'plants', 'party')
    def on_change_with_contacts_domain(self, name=None):
        pool = Pool()
        Contact = pool.get('party.address')

        contacts = []
        if self.equipments:
            contacts = Contact.search([
                ('equipment', 'in', [e.id for e in self.equipments])])
        elif self.plants:
            contacts = Contact.search([
                ('plant', 'in', [p.id for p in self.plants])])
        elif self.party:
            contacts = Contact.search([('party', '=', self.party)])
        return [c.id for c in contacts]

    @classmethod
    def confirm(cls, sales):
        pool = Pool()
        TaskTemplate = pool.get('lims.administrative.task.template')
        SaleLine = pool.get('sale.line')
        super(Sale, cls).confirm(sales)
        TaskTemplate.create_tasks('sale_purchase_order_required',
            cls._for_task_purchase_order_required(sales))
        lines = [l for s in sales for l in s.lines]
        SaleLine._confirm_lines(lines)

    @classmethod
    def _for_task_purchase_order_required(cls, sales):
        AdministrativeTask = Pool().get('lims.administrative.task')
        res = []
        for sale in sales:
            if not (sale.invoice_party.purchase_order_required and
                    not sale.purchase_order):
                continue
            if AdministrativeTask.search([
                    ('type', '=', 'sale_purchase_order_required'),
                    ('origin', '=', '%s,%s' % (cls.__name__, sale.id)),
                    ('state', 'not in', ('done', 'discarded')),
                    ]):
                continue
            res.append(sale)
        return res


class SalePlant(ModelSQL):
    'Sale - Plant'
    __name__ = 'sale.sale-lims.plant'
    _table = 'sale_sale_lims_plant'

    sale = fields.Many2One('sale.sale', 'Sale',
        ondelete='CASCADE', select=True, required=True)
    plant = fields.Many2One('lims.plant', 'Plant',
        ondelete='CASCADE', select=True, required=True)


class SaleEquipment(ModelSQL):
    'Sale - Equipment'
    __name__ = 'sale.sale-lims.equipment'
    _table = 'sale_sale_lims_equipment'

    sale = fields.Many2One('sale.sale', 'Sale',
        ondelete='CASCADE', select=True, required=True)
    equipment = fields.Many2One('lims.equipment', 'Equipment',
        ondelete='CASCADE', select=True, required=True)


class SaleComponent(ModelSQL):
    'Sale - Component'
    __name__ = 'sale.sale-lims.component'
    _table = 'sale_sale_lims_component'

    sale = fields.Many2One('sale.sale', 'Sale',
        ondelete='CASCADE', select=True, required=True)
    component = fields.Many2One('lims.component', 'Component',
        ondelete='CASCADE', select=True, required=True)


class SaleContact(ModelSQL):
    'Sale - Contact'
    __name__ = 'sale.sale-party.address'
    _table = 'sale_sale_party_address'

    sale = fields.Many2One('sale.sale', 'Sale',
        ondelete='CASCADE', select=True, required=True)
    address = fields.Many2One('party.address', 'Contact',
        ondelete='CASCADE', select=True, required=True)


class SaleLine(metaclass=PoolMeta):
    __name__ = 'sale.line'

    plants = fields.Many2Many('sale.line-lims.plant',
        'line', 'plant', 'Plants',
        states={
            'readonly': Or(Eval('sale_state') != 'draft',
                Bool(Eval('_parent_sale', {}).get('plants', False))),
            'required': And(
                Bool(Eval('_parent_sale', {}).get('lubrication_plan', False)),
                Bool(Eval('analysis')),
                ~Bool(Eval('_parent_sale', {}).get('plants', []))),
            },
        domain=[('party', '=', Eval('_parent_sale', {}).get('party', None))],
        depends=['sale', 'analysis', 'sale_state'])
    equipments = fields.Many2Many('sale.line-lims.equipment',
        'line', 'equipment', 'Equipments',
        states={
            'readonly': Or(Eval('sale_state') != 'draft',
                Bool(Eval('_parent_sale', {}).get('equipments', False))),
            'required': And(
                Bool(Eval('_parent_sale', {}).get('lubrication_plan', False)),
                Bool(Eval('analysis')),
                ~Bool(Eval('_parent_sale', {}).get('equipments', []))),
            },
        domain=[If(Bool(Eval('plants')),
            ('plant', 'in', Eval('plants')),
            ('plant', 'in', Eval('_parent_sale', {}).get('plants', [])))],
        depends=['plants', 'sale', 'analysis', 'sale_state'])
    components = fields.Many2Many('sale.line-lims.component',
        'line', 'component', 'Components',
        states={
            'readonly': Or(Eval('sale_state') != 'draft',
                Bool(Eval('_parent_sale', {}).get('components', False))),
            'required': And(
                Bool(Eval('_parent_sale', {}).get('lubrication_plan', False)),
                Bool(Eval('analysis')),
                ~Bool(Eval('_parent_sale', {}).get('components', []))),
            },
        domain=[If(Bool(Eval('equipments')),
            ('equipment', 'in', Eval('equipments')),
            ('equipment', 'in', Eval('_parent_sale', {}).get(
                'equipments', [])))],
        depends=['equipments', 'sale', 'analysis', 'sale_state'])
    label_from = fields.Integer('Label from', readonly=True,
        states={
            'invisible': ~Bool(Eval('_parent_sale', {}).get(
                'lubrication_plan', False)),
            'readonly': Eval('sale_state') != 'draft',
            },
        depends=['sale', 'sale_state'])
    label_to = fields.Integer('Label to', readonly=True,
        states={
            'invisible': ~Bool(Eval('_parent_sale', {}).get(
                'lubrication_plan', False)),
            'readonly': Eval('sale_state') != 'draft',
            },
        depends=['sale', 'sale_state'])

    @classmethod
    def __setup__(cls):
        super(SaleLine, cls).__setup__()
        cls.expiration_date.states['required'] = And(
                Bool(Eval('_parent_sale', {}).get('lubrication_plan', False)),
                Bool(Eval('analysis')))
        cls.expiration_date.depends.extend(['sale', 'analysis'])

    @classmethod
    def _confirm_lines(cls, lines):
        TaskTemplate = Pool().get('lims.administrative.task.template')
        TaskTemplate.create_tasks('product_quotation',
            cls._for_task_product_quotation(lines))

    @classmethod
    def _for_task_product_quotation(cls, lines):
        AdministrativeTask = Pool().get('lims.administrative.task')
        res = []
        for line in lines:
            if not line.product or not line.product.create_task_quotation:
                continue
            if AdministrativeTask.search([
                    ('type', '=', 'product_quotation'),
                    ('origin', '=', '%s,%s' % (cls.__name__, line.id)),
                    ('state', 'not in', ('done', 'discarded')),
                    ]):
                continue
            res.append(line)
        return res


class SaleLinePlant(ModelSQL):
    'Sale Line - Plant'
    __name__ = 'sale.line-lims.plant'
    _table = 'sale_line_lims_plant'

    line = fields.Many2One('sale.line', 'Sale Line',
        ondelete='CASCADE', select=True, required=True)
    plant = fields.Many2One('lims.plant', 'Plant',
        ondelete='CASCADE', select=True, required=True)


class SaleLineEquipment(ModelSQL):
    'Sale Line - Equipment'
    __name__ = 'sale.line-lims.equipment'
    _table = 'sale_line_lims_equipment'

    line = fields.Many2One('sale.line', 'Sale Line',
        ondelete='CASCADE', select=True, required=True)
    equipment = fields.Many2One('lims.equipment', 'Equipment',
        ondelete='CASCADE', select=True, required=True)


class SaleLineComponent(ModelSQL):
    'Sale Line - Component'
    __name__ = 'sale.line-lims.component'
    _table = 'sale_line-lims_component'

    line = fields.Many2One('sale.line', 'Sale Line',
        ondelete='CASCADE', select=True, required=True)
    component = fields.Many2One('lims.component', 'Component',
        ondelete='CASCADE', select=True, required=True)


class SaleAddProductKitStart(ModelView):
    'Add Products Kits'
    __name__ = 'sale.add_product_kit.start'


class SaleAddProductKit(Wizard):
    'Add Products Kits'
    __name__ = 'sale.add_product_kit'

    start_state = 'check'
    check = StateTransition()
    start = StateView('sale.add_product_kit.start',
        'lims_sale_industry.sale_add_product_kit_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Add', 'add', 'tryton-ok', default=True),
            ])
    add = StateTransition()

    def transition_check(self):
        pool = Pool()
        Sale = pool.get('sale.sale')

        sale = Sale(Transaction().context['active_id'])

        if sale.state != 'draft':
            return 'end'
        return 'start'

    def transition_add(self):
        pool = Pool()
        SaleLine = pool.get('sale.line')
        Product = pool.get('product.product')

        sale_id = Transaction().context['active_id']

        products = {}
        sale_lines = SaleLine.search([
            ('sale', '=', sale_id),
            ('sale.state', '=', 'draft'),
            ('analysis', '!=', None),
            ])
        for line in sale_lines:
            if line.analysis.product_kit:
                product_id = line.analysis.product_kit.id
                if product_id not in products:
                    products[product_id] = 0
                products[product_id] += line.quantity

        new_lines = []
        for product_id, qty in products.items():
            product = Product(product_id)
            sale_line = SaleLine(
                quantity=qty,
                unit=product.default_uom.id,
                product=product.id,
                description=product.rec_name,
                sale=sale_id,
                )
            sale_line.on_change_product()
            new_lines.append(sale_line)
        SaleLine.save(new_lines)
        return 'end'


class SalePrintLabelStart(ModelView):
    'Print Labels'
    __name__ = 'sale.print_label.start'

    quantity = fields.Integer('Quantity of labels', required=True)


class SalePrintLabel(Wizard):
    'Print Labels'
    __name__ = 'sale.print_label'

    start_state = 'check'
    check = StateTransition()
    start = StateView('sale.print_label.start',
        'lims_sale_industry.sale_print_label_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print', 'generate', 'tryton-print', default=True),
            ])
    generate = StateTransition()
    print_ = StateReport('sale.label.report')

    def transition_check(self):
        pool = Pool()
        Sale = pool.get('sale.sale')

        sale = Sale(Transaction().context['active_id'])

        if sale.label_from:
            return 'print_'
        if sale.lubrication_plan:
            return 'generate'
        return 'start'

    def transition_generate(self):
        pool = Pool()
        Sale = pool.get('sale.sale')
        Config = pool.get('sale.configuration')
        Sequence = pool.get('ir.sequence')

        config = Config(1)
        sequence = config.sample_label_sequence
        if not sequence:
            raise UserError(gettext(
                'lims_sale_industry.msg_no_sample_label_sequence'))

        sale = Sale(Transaction().context['active_id'])

        if sale.lubrication_plan:
            first_label = None
            last_label = None
            for line in sale.lines:
                quantity = int(line.quantity)
                if quantity < 1:
                    continue
                line.label_from = Sequence.get_id(sequence.id)
                line.label_to = line.label_from
                for x in range(1, quantity):
                    line.label_to = Sequence.get_id(sequence.id)
                if not first_label:
                    first_label = line.label_from
                if not last_label:
                    last_label = line.label_to
                line.save()
            sale.label_from = first_label
            sale.label_to = last_label
            Sale.save([sale])

        else:
            if self.start.quantity < 1:
                return 'end'
            sale.label_from = Sequence.get_id(sequence.id)
            sale.label_to = sale.label_from
            for x in range(1, self.start.quantity):
                sale.label_to = Sequence.get_id(sequence.id)
            Sale.save([sale])

        return 'print_'


class SaleLabel(Report):
    'Sale Labels'
    __name__ = 'sale.label.report'


class SaleLabelShipping(Report):
    'Shipping Labels'
    __name__ = 'sale.label_shipping.report'


class SaleLabelReturn(Report):
    'Return Labels'
    __name__ = 'sale.label_return.report'


class SaleSearchLabelStart(ModelView):
    'Search Label'
    __name__ = 'sale.search_label.start'

    label = fields.Integer('Label', required=True)


class SaleSearchLabel(Wizard):
    'Search Label'
    __name__ = 'sale.search_label'

    start = StateView('sale.search_label.start',
        'lims_sale_industry.sale_search_label_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search', 'search', 'tryton-search', default=True),
            ])
    search = StateAction('lims_sale_industry.act_sale')

    def do_search(self, action):
        pool = Pool()
        Sale = pool.get('sale.sale')

        sale = Sale.search([
            ('label_from', '<=', self.start.label),
            ('label_to', '>=', self.start.label),
            ])
        sale_id = sale and sale[0].id or None

        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', '=', sale_id),
            ])
        action['name'] += ' (%s)' % self.start.label
        return action, {}
