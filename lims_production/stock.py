# -*- coding: utf-8 -*-
# This file is part of lims_production module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelView, ModelSQL, fields
from trytond.wizard import Wizard, StateAction
from trytond.pool import PoolMeta, Pool
from trytond.pyson import PYSONEncoder, Eval, Equal, Bool, Not
from trytond.transaction import Transaction
from trytond.modules.product import price_digits


class Template(metaclass=PoolMeta):
    __name__ = 'product.template'

    common_name = fields.Char('Common name')
    chemical_name = fields.Char('Chemical name')
    commercial_name = fields.Char('Commercial name')
    cas_number = fields.Char('CAS number')
    commercial_brand = fields.Many2One('lims.brand', 'Commercial Brand')
    purity_degree = fields.Many2One('lims.purity.degree', 'Purity Degree')
    family_equivalent = fields.Many2One('lims.family.equivalent',
        'Family/Equivalent',
        domain=[('uom.category', '=', Eval('default_uom_category'))],
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
            return [('id', 'in', list(map(int, [product.template.id
                    for product in products])))]
        return super().search_rec_name(name, clause)


class Product(metaclass=PoolMeta):
    __name__ = 'product.product'

    catalog = fields.Char('Catalog',
        states={'readonly': ~Eval('active', True)})
    barcode = fields.Char('Bar Code',
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
        res = super().search_rec_name(name, clause)
        return ['OR',
            res,
            [('barcode', ) + tuple(clause[1:])]
            ]

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


class LotCategory(ModelSQL, ModelView):
    "Lot Category"
    __name__ = "stock.lot.category"
    _rec_name = 'name'

    name = fields.Char('Name', required=True)

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order.insert(0, ('name', 'ASC'))


class Lot(metaclass=PoolMeta):
    __name__ = 'stock.lot'

    category = fields.Many2One('stock.lot.category', 'Category')
    special_category = fields.Function(fields.Char('Category'),
        'on_change_with_special_category')
    stability = fields.Char('Stability',
        states={
            'invisible': Not(Bool(Equal(Eval('special_category'),
                'input_prod'))),
            })
    homogeneity = fields.Char('Homogeneity',
        states={
            'invisible': Not(Bool(Equal(Eval('special_category'),
                'input_prod'))),
            })
    concentration = fields.Char('Concentration',
        states={
            'invisible': ~Eval('special_category').in_(
                ['input_prod', 'domestic_use']),
            })
    reception_date = fields.Date('Reception date',
        states={
            'invisible': Not(Bool(Equal(Eval('special_category'),
                'input_prod'))),
            })
    preparation_date = fields.Date('Preparation date',
        states={
            'invisible': Not(Bool(Equal(Eval('special_category'),
                'domestic_use'))),
            })
    common_name = fields.Function(fields.Char('Common name',
        states={
            'invisible': Not(Bool(Equal(Eval('special_category'),
                'input_prod'))),
            }), 'get_common_name')
    chemical_name = fields.Function(fields.Char('Chemical name',
        states={
            'invisible': Not(Bool(Equal(Eval('special_category'),
                'input_prod'))),
            }), 'get_chemical_name')
    commercial_name = fields.Function(fields.Char('Commercial name',
        states={
            'invisible': Not(Bool(Equal(Eval('special_category'),
                'input_prod'))),
            }), 'get_commercial_name')
    cas_number = fields.Function(fields.Char('CAS number',
        states={
            'invisible': Not(Bool(Equal(Eval('special_category'),
                'input_prod'))),
            }), 'get_cas_number', searcher='search_cas_number')
    commercial_brand = fields.Function(fields.Many2One('lims.brand',
        'Commercial Brand', states={
            'invisible': Not(Bool(Equal(Eval('special_category'),
                'input_prod'))),
            }), 'get_commercial_brand')
    catalog = fields.Function(fields.Char('Catalog',
        states={
            'invisible': Not(Bool(Equal(Eval('special_category'),
                'input_prod'))),
            }), 'get_catalog')
    purity_degree = fields.Function(fields.Many2One('lims.purity.degree',
        'Purity Degree', states={
            'invisible': Not(Bool(Equal(Eval('special_category'),
                'input_prod'))),
            }), 'get_purity_degree')
    solvent = fields.Many2One('product.product', 'Solvent',
        states={
            'invisible': Not(Bool(Equal(Eval('special_category'),
                'domestic_use'))),
            })
    technician = fields.Many2One('lims.laboratory.professional', 'Technician',
        states={
            'invisible': ~Eval('special_category').in_(
                ['domestic_use', 'prod_sale']),
            })
    account_category = fields.Function(fields.Many2One('product.category',
        'Account Category', states={
            'invisible': Not(Bool(Equal(Eval('special_category'),
                'input_prod'))),
            }), 'get_account_category', searcher='search_account_category')
    exclusive_glp = fields.Boolean('Exclusive use GLP',
        states={
            'invisible': Not(Bool(Equal(Eval('special_category'),
                'input_prod')))})
    production = fields.Many2One('production', 'Production origin',
        readonly=True)

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.expiration_date.states['invisible'] = False

    @staticmethod
    def default_exclusive_glp():
        return False

    @fields.depends('category', 'product', '_parent_product.purchasable',
        '_parent_product.salable')
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

    @classmethod
    def search_cas_number(cls, name, clause):
        return [('product.cas_number',) + tuple(clause[1:])]

    def get_commercial_brand(self, name=None):
        if self.product and self.product.commercial_brand:
            return self.product.commercial_brand
        return None

    def get_catalog(self, name=None):
        if self.product:
            return self.product.catalog
        return ''

    def get_purity_degree(self, name=None):
        if self.product and self.product.purity_degree:
            return self.product.purity_degree
        return None

    def get_account_category(self, name=None):
        if self.product:
            return self.product.account_category
        return None

    @classmethod
    def create(cls, vlist):
        pool = Pool()
        Product = pool.get('product.product')
        Config = pool.get('lims.configuration')

        config = Config(1)
        vlist = [x.copy() for x in vlist]
        for values in vlist:
            if not values.get('category'):
                product = Product(values['product'])
                lot_category_id = None
                if (hasattr(product, 'purchasable') and
                        product.purchasable and not product.salable):
                    lot_category_id = (config.lot_category_input_prod.id
                        if config.lot_category_input_prod else None)
                elif (not product.purchasable and product.salable):
                    lot_category_id = (config.lot_category_prod_sale.id
                        if config.lot_category_prod_sale else None)
                elif (not product.purchasable and not product.salable):
                    lot_category_id = (
                        config.lot_category_prod_domestic_use.id if
                        config.lot_category_prod_domestic_use else None)
                if lot_category_id:
                    values['category'] = lot_category_id
        return super().create(vlist)

    @classmethod
    def search_account_category(cls, name, clause):
        return [('product.' + name,) + tuple(clause[1:])]


class Move(metaclass=PoolMeta):
    __name__ = 'stock.move'

    label_quantity = fields.Float("Label Quantity")
    origin_purchase_unit_price = fields.Numeric('Unit Price',
        digits=price_digits)
    origin_purchase_currency = fields.Many2One('currency.currency',
        'Currency')

    @fields.depends('quantity')
    def on_change_quantity(self):
        if self.quantity:
            self.label_quantity = self.quantity

    @classmethod
    def _get_origin(cls):
        models = super()._get_origin()
        models.append('production')
        return models


class ShipmentIn(metaclass=PoolMeta):
    __name__ = 'stock.shipment.in'

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.inventory_moves.states['readonly'] = Eval('state').in_(
            ['draft', 'cancel'])

    def _get_inventory_move(self, incoming_move):
        move = super()._get_inventory_move(incoming_move)
        if not move:
            return None

        if not incoming_move.origin:
            return None

        move.label_quantity = move.quantity
        move.origin_purchase_currency = \
            incoming_move.origin.purchase.currency.id
        move.origin_purchase_unit_price = incoming_move.origin.unit_price
        return move


class MoveProductionRelated(Wizard):
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
