# -*- coding: utf-8 -*-
# This file is part of lims_production module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import cups
from decimal import Decimal
from functools import partial

from trytond.model import ModelView, ModelSQL, fields
from trytond.pyson import PYSONEncoder, Eval, Equal, Bool, Not
from trytond.transaction import Transaction
from trytond.pool import PoolMeta, Pool
from trytond.wizard import Wizard, StateTransition, StateAction
from trytond.modules.product import price_digits

__all__ = ['PurityDegree', 'Brand', 'FamilyEquivalent', 'Template', 'Product',
    'UpdateCostPrice', 'LotCategory', 'Lot', 'Move', 'ShipmentIn',
    'ShipmentInLabels', 'LimsMoveProductionRelated']


class PurityDegree(ModelSQL, ModelView):
    'Purity Degree'
    __name__ = 'lims.purity.degree'

    code = fields.Char('Code', required=True)
    name = fields.Char('Name', required=True)


class Brand(ModelSQL, ModelView):
    'Brand'
    __name__ = 'lims.brand'

    code = fields.Char('Code', required=True)
    name = fields.Char('Name', required=True)


class FamilyEquivalent(ModelSQL, ModelView):
    'Family/Equivalent'
    __name__ = 'lims.family.equivalent'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)
    uom = fields.Many2One('product.uom', 'UoM', required=True,
        domain=[('category.lims_only_available', '=', False)],
        help='The UoM\'s Category selected here will determine the set '
        'of Products that can be related to this Family/Equivalent.')
    products = fields.One2Many('product.template', 'family_equivalent',
        'Products', readonly=True)

    @classmethod
    def __setup__(cls):
        super(FamilyEquivalent, cls).__setup__()
        cls._error_messages.update({
                'invalid_product_uom_category': ('The UoM\'s Category '
                    'of each Product should be the same as the UoM\'s '
                    'Category of Family/Equivalent.'),
                })

    @classmethod
    def validate(cls, family_equivalents):
        super(FamilyEquivalent, cls).validate(family_equivalents)
        for fe in family_equivalents:
            fe.check_products()

    def check_products(self):
        if self.products:
            main_category = self.uom.category
            for product in self.products:
                if main_category != product.default_uom.category:
                    self.raise_user_error('invalid_product_uom_category')

    @classmethod
    def copy(cls, family_equivalents, default=None):
        if default is None:
            default = {}
        current_default = default.copy()
        current_default['products'] = None
        return super(FamilyEquivalent, cls).copy(family_equivalents,
            default=current_default)


class Template:
    __name__ = 'product.template'
    __metaclass__ = PoolMeta

    common_name = fields.Char('Common name')
    chemical_name = fields.Char('Chemical name')
    commercial_name = fields.Char('Commercial name')
    cas_number = fields.Char('CAS number')
    commercial_brand = fields.Many2One('lims.brand', 'Commercial Brand')
    purity_degree = fields.Many2One('lims.purity.degree', 'Purity Degree')
    family_equivalent = fields.Many2One('lims.family.equivalent',
        'Family/Equivalent',
        domain=[('uom.category', '=', Eval('default_uom_category'))],
        depends=['default_uom_category'],
        help='The UoM\'s Category of Family/Equivalent which you can '
        'select here will match the UoM\'s Category of this Product.')
    controlled = fields.Boolean('Controlled')
    reference_material = fields.Boolean('Reference Material')
    certified = fields.Boolean('Certified')

    @classmethod
    def search_rec_name(cls, name, clause):
        Product = Pool().get('product.product')
        products = Product.search(['OR',
                    [('code',) + tuple(clause[1:])],
                    [('barcode',) + tuple(clause[1:])],
                    ], order=[])
        if products:
            return [('id', 'in', map(int, [product.template.id
                    for product in products]))]
        return super(Template, cls).search_rec_name(name, clause)


class Product:
    __name__ = 'product.product'
    __metaclass__ = PoolMeta

    catalog = fields.Char('Catalog', depends=['active'],
        states={'readonly': ~Eval('active', True)})
    barcode = fields.Char('Bar Code', depends=['active'],
        states={'readonly': ~Eval('active', True)})
    common_name = fields.Function(fields.Char('Common name'),
        'get_template_field', searcher='search_template_field')
    chemical_name = fields.Function(fields.Char('Chemical name'),
        'get_template_field', searcher='search_template_field')
    commercial_name = fields.Function(fields.Char('Commercial name'),
        'get_template_field', searcher='search_template_field')
    cas_number = fields.Function(fields.Char('CAS number'),
        'get_template_field', searcher='search_template_field')
    commercial_brand = fields.Function(fields.Many2One('lims.brand',
        'Commercial Brand'), 'get_template_field',
        searcher='search_template_field')
    purity_degree = fields.Function(fields.Many2One('lims.purity.degree',
        'Purity Degree'), 'get_template_field',
        searcher='search_template_field')
    family_equivalent = fields.Function(fields.Many2One(
        'lims.family.equivalent', 'Family/Equivalent'), 'get_template_field',
        searcher='search_template_field')
    controlled = fields.Function(fields.Boolean('Controlled'),
        'get_template_field', searcher='search_template_field')
    reference_material = fields.Function(fields.Boolean('Reference Material'),
        'get_template_field', searcher='search_template_field')
    certified = fields.Function(fields.Boolean('Certified'),
        'get_template_field', searcher='search_template_field')

    @classmethod
    def search_rec_name(cls, name, clause):
        res = super(Product, cls).search_rec_name(name, clause)
        return ['OR',
            res,
            [('barcode', ) + tuple(clause[1:])]
            ]

    @classmethod
    def recompute_cost_price(cls, products):
        # original function rewritten to use cost_price and
        # quantity from Template
        pool = Pool()
        Template = pool.get('product.template')

        digits = Template.cost_price.digits
        write = Template.write
        record = lambda p: p.template

        costs = defaultdict(list)
        for product in products:
            if product.type == 'service':
                continue
            cost = getattr(product,
                'recompute_cost_price_%s' % product.cost_price_method)()
            cost = cost.quantize(Decimal(str(10.0 ** -digits[1])))
            costs[cost].append(record(product))

        if not costs:
            return

        to_write = []
        for cost, records in costs.iteritems():
            to_write.append(records)
            to_write.append({'cost_price': cost})

        # Enforce check access for account_stock*
        with Transaction().set_context(_check_access=True):
            write(*to_write)

    def recompute_cost_price_average(self):
        # original function rewritten to use cost_price and
        # quantity from Template
        pool = Pool()
        Move = pool.get('stock.move')
        Currency = pool.get('currency.currency')
        Uom = pool.get('product.uom')

        context = Transaction().context

        product_clause = ('product.template', '=', self.template.id)

        moves = Move.search([
                product_clause,
                ('state', '=', 'done'),
                ('company', '=', context.get('company')),
                ['OR',
                    [
                        ('to_location.type', '=', 'storage'),
                        ('from_location.type', '!=', 'storage'),
                        ],
                    [
                        ('from_location.type', '=', 'storage'),
                        ('to_location.type', '!=', 'storage'),
                        ],
                    ],
                ], order=[('effective_date', 'ASC'), ('id', 'ASC')])

        cost_price = Decimal(0)
        quantity = 0
        for move in moves:
            qty = Uom.compute_qty(move.uom, move.quantity,
                self.template.default_uom)
            qty = Decimal(str(qty))
            if move.from_location.type == 'storage':
                qty *= -1
            if (move.from_location.type in ['supplier', 'production']
                    or move.to_location.type == 'supplier'):
                with Transaction().set_context(date=move.effective_date):
                    unit_price = Currency.compute(
                        move.currency, move.unit_price,
                        move.company.currency, round=False)
                unit_price = Uom.compute_price(move.uom, unit_price,
                    self.template.default_uom)
                if quantity + qty != 0:
                    cost_price = (
                        (cost_price * quantity) + (unit_price * qty)
                        ) / (quantity + qty)
            quantity += qty
        return cost_price

    @classmethod
    def get_template_field(cls, products, names):
        result = {}
        for name in names:
            result[name] = {}
            if name in ('commercial_brand', 'purity_degree',
                    'family_equivalent'):
                for p in products:
                    field = getattr(p.template, name, None)
                    result[name][p.id] = field.id if field else None
            else:
                for p in products:
                    result[name][p.id] = getattr(p.template, name, None)
        return result

    @classmethod
    def search_template_field(cls, name, clause):
        return [('template.' + name,) + tuple(clause[1:])]


class UpdateCostPrice:
    __name__ = 'product.update_cost_price'
    __metaclass__ = PoolMeta

    start_state = 'check'
    check = StateTransition()

    def transition_check(self):
        context = Transaction().context
        if context['active_model'] == 'product.template':
            return 'ask_price'
        return 'end'

    def default_ask_price(self, fields):
        Template = Pool().get('product.template')
        default = super(UpdateCostPrice, self).default_ask_price(fields)
        if 'template' in default:
            template = Template(default['template'])
            default['cost_price'] = template.cost_price
        return default

    def transition_update_price(self):
        Template = Pool().get('product.template')
        write = partial(Template.write, [self.ask_price.template])
        write({'cost_price': self.ask_price.cost_price})
        return 'end'


class LotCategory(ModelSQL, ModelView):
    "Lot Category"
    __name__ = "stock.lot.category"
    _rec_name = 'name'

    name = fields.Char('Name', required=True)

    @classmethod
    def __setup__(cls):
        super(LotCategory, cls).__setup__()
        cls._order.insert(0, ('name', 'ASC'))


class Lot:
    __name__ = 'stock.lot'
    __metaclass__ = PoolMeta

    category = fields.Many2One('stock.lot.category', 'Category')
    special_category = fields.Function(fields.Char('Category'),
        'on_change_with_special_category', searcher='search_special_category')

    stability = fields.Char('Stability', depends=['special_category'],
        states={
            'invisible': Not(Bool(Equal(Eval('special_category'),
                'input_prod'))),
            })
    homogeneity = fields.Char('Homogeneity', depends=['special_category'],
        states={
            'invisible': Not(Bool(Equal(Eval('special_category'),
                'input_prod'))),
            })
    concentration = fields.Char('Concentration',
        depends=['special_category'], states={
            'invisible': ~Eval('special_category').in_(
                ['input_prod', 'domestic_use']),
            })
    expiration_date = fields.Date('Expiration date')
    reception_date = fields.Date('Reception date',
        depends=['special_category'], states={
            'invisible': Not(Bool(Equal(Eval('special_category'),
                'input_prod'))),
            })
    preparation_date = fields.Date('Preparation date',
        depends=['special_category'], states={
            'invisible': Not(Bool(Equal(Eval('special_category'),
                'domestic_use'))),
            })
    common_name = fields.Function(fields.Char('Common name',
        depends=['special_category'], states={
            'invisible': Not(Bool(Equal(Eval('special_category'),
                'input_prod'))),
            }), 'get_common_name')
    chemical_name = fields.Function(fields.Char('Chemical name',
        depends=['special_category'], states={
            'invisible': Not(Bool(Equal(Eval('special_category'),
                'input_prod'))),
            }), 'get_chemical_name')
    commercial_name = fields.Function(fields.Char('Commercial name',
        depends=['special_category'], states={
            'invisible': Not(Bool(Equal(Eval('special_category'),
                'input_prod'))),
            }), 'get_commercial_name')
    cas_number = fields.Function(fields.Char('CAS number',
        depends=['special_category'], states={
            'invisible': Not(Bool(Equal(Eval('special_category'),
                'input_prod'))),
            }), 'get_cas_number')
    commercial_brand = fields.Function(fields.Many2One('lims.brand',
        'Commercial Brand', depends=['special_category'], states={
            'invisible': Not(Bool(Equal(Eval('special_category'),
                'input_prod'))),
            }), 'get_commercial_brand')
    catalog = fields.Function(fields.Char('Catalog',
        depends=['special_category'], states={
            'invisible': Not(Bool(Equal(Eval('special_category'),
                'input_prod'))),
            }), 'get_catalog')
    purity_degree = fields.Function(fields.Many2One('lims.purity.degree',
        'Purity Degree', depends=['special_category'], states={
            'invisible': Not(Bool(Equal(Eval('special_category'),
                'input_prod'))),
            }), 'get_purity_degree')
    solvent = fields.Many2One('product.product', 'Solvent',
        depends=['special_category'], states={
            'invisible': Not(Bool(Equal(Eval('special_category'),
                'domestic_use'))),
            })
    technician = fields.Many2One('lims.laboratory.professional', 'Technician',
        depends=['special_category'], states={
            'invisible': ~Eval('special_category').in_(
                ['domestic_use', 'prod_sale']),
            })

    @fields.depends('category', 'product')
    def on_change_with_special_category(self, name=None):
        Config = Pool().get('lims.configuration')
        if self.category:
            config = Config(1)
            if self.category == config.lot_category_input_prod:
                return 'input_prod'
            elif self.category == config.lot_category_prod_sale:
                return 'prod_sale'
            elif self.category == config.lot_category_prod_domestic_use:
                return 'domestic_use'
        elif self.product:
            if (self.product.purchasable and not self.product.salable):
                return 'input_prod'
            elif (not self.product.purchasable and self.product.salable):
                return 'prod_sale'
            elif (not self.product.purchasable and not self.product.salable):
                return 'domestic_use'
        else:
            return ''

    def get_common_name(self, name=None):
        if self.product:
            return self.product.common_name
        return ''

    def get_chemical_name(self, name=None):
        if self.product:
            return self.product.chemical_name
        return ''

    def get_commercial_name(self, name=None):
        if self.product:
            return self.product.commercial_name
        return ''

    def get_cas_number(self, name=None):
        if self.product:
            return self.product.cas_number
        return ''

    def get_commercial_brand(self, name=None):
        if self.product and self.product.commercial_brand:
            return self.product.commercial_brand.id
        return None

    def get_catalog(self, name=None):
        if self.product:
            return self.product.catalog
        return ''

    def get_purity_degree(self, name=None):
        if self.product and self.product.purity_degree:
            return self.product.purity_degree.id
        return None

    @classmethod
    def create(cls, vlist):
        pool = Pool()
        Product = pool.get('product.product')
        LimsConfig = pool.get('lims.configuration')

        lims_config = LimsConfig(1)
        vlist = [x.copy() for x in vlist]
        for values in vlist:
            if not values.get('category'):
                product = Product(values['product'])
                lot_category_id = None
                if (product.purchasable and not product.salable):
                    lot_category_id = (lims_config.lot_category_input_prod.id
                        if lims_config.lot_category_input_prod else None)
                elif (not product.purchasable and product.salable):
                    lot_category_id = (lims_config.lot_category_prod_sale.id
                        if lims_config.lot_category_prod_sale else None)
                elif (not product.purchasable and not product.salable):
                    lot_category_id = (
                        lims_config.lot_category_prod_domestic_use.id if
                        lims_config.lot_category_prod_domestic_use else None)
                if lot_category_id:
                    values['category'] = lot_category_id
        return super(Lot, cls).create(vlist)


class Move:
    __name__ = 'stock.move'
    __metaclass__ = PoolMeta

    label_quantity = fields.Integer("Label Quantity")
    origin_purchase_unit_price = fields.Numeric('Unit Price',
        digits=price_digits)
    origin_purchase_currency = fields.Many2One('currency.currency',
        'Currency')

    @fields.depends('quantity')
    def on_change_quantity(self):
        if self.quantity:
            self.label_quantity = int(self.quantity)

    @classmethod
    def _get_origin(cls):
        models = super(Move, cls)._get_origin()
        models.append('production')
        return models

    def _update_product_cost_price(self, direction):
        # original function rewritten to use cost_price and
        # quantity from Template
        pool = Pool()
        Uom = pool.get('product.uom')
        ProductTemplate = pool.get('product.template')
        Location = pool.get('stock.location')
        Currency = pool.get('currency.currency')
        Date = pool.get('ir.date')

        if direction == 'in':
            quantity = self.quantity
        elif direction == 'out':
            quantity = -self.quantity
        context = {}
        locations = Location.search([
                ('type', '=', 'storage'),
                ])
        context['with_childs'] = False
        context['locations'] = [l.id for l in locations]
        context['stock_date_end'] = Date.today()
        with Transaction().set_context(context):
            template = ProductTemplate(self.product.template.id)

        qty = Uom.compute_qty(self.uom, quantity, template.default_uom)
        qty = Decimal(str(qty))

        product_qty = template.quantity
        product_qty = Decimal(str(max(product_qty, 0)))
        # convert wrt currency
        with Transaction().set_context(date=self.effective_date):
            unit_price = Currency.compute(self.currency, self.unit_price,
                self.company.currency, round=False)
        # convert wrt to the uom
        unit_price = Uom.compute_price(self.uom, unit_price,
            template.default_uom)
        if product_qty + qty != Decimal('0.0'):
            new_cost_price = (
                (template.cost_price * product_qty) + (unit_price * qty)
                ) / (product_qty + qty)
        else:
            new_cost_price = template.cost_price

        digits = ProductTemplate.cost_price.digits
        write = partial(ProductTemplate.write, [template])

        new_cost_price = new_cost_price.quantize(
            Decimal(str(10.0 ** -digits[1])))

        write({'cost_price': new_cost_price})


class ShipmentIn:
    __name__ = 'stock.shipment.in'
    __metaclass__ = PoolMeta

    @classmethod
    def __setup__(cls):
        super(ShipmentIn, cls).__setup__()
        cls.inventory_moves.states['readonly'] = Eval('state').in_(
            ['draft', 'cancel'])

    @classmethod
    def _get_inventory_moves(cls, incoming_move):
        move = super(ShipmentIn, cls)._get_inventory_moves(incoming_move)
        if not move:
            return None

        move.label_quantity = move.quantity
        move.origin_purchase_currency = \
            incoming_move.origin.purchase.currency.id
        move.origin_purchase_unit_price = incoming_move.origin.unit_price
        return move


class ShipmentInLabels(Wizard):
    'Shipment In Labels'
    __name__ = 'stock.shipment.in.labels.report'

    start = StateTransition()

    def transition_start(self):
        pool = Pool()
        User = pool.get('res.user')
        Shipment = pool.get('stock.shipment.in')
        Lang = pool.get('ir.lang')

        user = User(Transaction().user)
        if not user.printer:
            return 'end'

        shipment = Shipment(Transaction().context.get('active_id'))
        if shipment.state != 'done':
            return 'end'

        lang, = Lang.search([
                ('code', '=', Transaction().language),
                ])

        s = u'\n'
        s += u'q750\n'
        s += u'I8,A\n'

        for move in shipment.inventory_moves:
            if move.label_quantity < 1:
                continue
            department = move.department and move.department.code or ''
            lot = move.lot and move.lot.number or ''
            catalog = move.product.catalog or ''
            catalog = catalog[0:30]
            desline = move.product.template.name
            if len(desline) > 52:
                line1 = desline[0:52]
                line2 = desline[52:105]
            else:
                line1 = move.product.template.name
                line2 = ''
            barcode = move.product.barcode or ''

            s += u'N\n'
            s += (u'A90,0,0,3,1,2,N,"' + catalog + '     ' + department +
                '  ' + move.to_location.code + '"\n')
            s += u'A90,40,0,2,1,2,N,"' + line1 + '"\n'
            s += u'A90,65,0,2,1,2,N,"' + line2 + '"\n'
            s += u'A90,85,0,2,1,1,N,"' + Lang.strftime(
                shipment.effective_date, lang.code, lang.date) + '"\n'
            s += u'A450,80,0,3,1,2,N,"' + lot + '"\n'
            s += u'B90,110,0,1,2,0,60,N,"' + barcode + '"\n'
            s += (u'A550,135,0,2,1,1,N,"' + move.origin_purchase_currency.code
                + ' ' + Lang.format(lang, '%.2f',
                move.origin_purchase_unit_price) + '"\n')
            s += u'P' + str(move.label_quantity) + '\n'

        labels_to_print = open('labels', 'w')
        labels_to_print.write(s.encode('cp1252', 'ignore'))
        labels_to_print.close()

        conn = cups.Connection()
        conn.printFile(user.printer.name, 'labels', 'Labels', {})
        return 'end'


class LimsMoveProductionRelated(Wizard):
    'Related Productions'
    __name__ = 'lims.move.production_related'

    start = StateAction('lims_production.act_production_related')

    def do_start(self, action):
        Move = Pool().get('stock.move')

        move = Move(Transaction().context['active_id'])

        production_id = None
        if move.production_input:
            production_id = move.production_input.id
        elif move.production_output:
            production_id = move.production_output.id

        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', '=', production_id),
            ])

        return action, {}
