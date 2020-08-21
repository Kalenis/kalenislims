# -*- coding: utf-8 -*-
# This file is part of lims_production module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from decimal import Decimal

from trytond.model import fields
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Eval, Bool
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.i18n import gettext


class BOM(metaclass=PoolMeta):
    __name__ = 'production.bom'

    divide_lots = fields.Boolean('Divide lots')


class Production(metaclass=PoolMeta):
    __name__ = 'production'

    concentration = fields.Char('Concentration',
        depends=['salable_product', 'state'], states={
            'invisible': Bool(Eval('salable_product')),
            'readonly': ~Eval('state').in_(['request', 'draft']),
            })
    preparation_date = fields.Date('Preparation date',
        depends=['salable_product', 'state'], states={
            'invisible': Bool(Eval('salable_product')),
            'readonly': ~Eval('state').in_(['request', 'draft']),
            })
    expiration_date = fields.Date('Expiration date',
        depends=['state'], states={
            'readonly': ~Eval('state').in_(['request', 'draft']),
            })
    technician = fields.Many2One('lims.laboratory.professional',
        'Technician', depends=['state'], states={
            'readonly': ~Eval('state').in_(['request', 'draft']),
            })
    solvent = fields.Function(fields.Many2One('product.product',
        'Solvent', depends=['salable_product', 'state'], states={
            'invisible': Bool(Eval('salable_product')),
            'readonly': ~Eval('state').in_(['request', 'draft']),
            }), 'on_change_with_solvent')
    salable_product = fields.Function(fields.Boolean('Salable',
        depends=['product']),
        'on_change_with_salable_product')
    comments = fields.Text('Comments')

    @fields.depends('product', '_parent_product.salable')
    def on_change_with_salable_product(self, name=None):
        if self.product:
            return self.product.salable
        return False

    @fields.depends('inputs')
    def on_change_with_solvent(self, name=None):
        Config = Pool().get('lims.configuration')

        config = Config(1)
        solvent_domain = config.get_solvents()
        if not solvent_domain:
            return None

        for input_ in self.inputs:
            if (input_.product and input_.product.account_category and
                    (input_.product.account_category.id in solvent_domain)):
                return input_.product.id
        return None

    def explode_bom(self):
        pool = Pool()
        Template = pool.get('product.template')
        Product = pool.get('product.product')

        super().explode_bom()
        if not (self.bom and self.product and self.uom):
            return

        if not self.bom.divide_lots:
            return

        if self.quantity:
            quantity = 0.0
            for output in self.bom.outputs:
                quantity += output.quantity
            if not (self.quantity % quantity == 0):
                raise UserError(
                    gettext('lims_production.msg_quantity_multiple_required'))

        if self.warehouse:
            storage_location = self.warehouse.storage_location
        else:
            storage_location = None
        factor = self.bom.compute_factor(self.product, self.quantity or 0,
            self.uom)
        if hasattr(Product, 'cost_price'):
            digits = Product.cost_price.digits
        else:
            digits = Template.cost_price.digits

        outputs = []
        for output in self.bom.outputs:
            quantity = output.compute_quantity(factor)
            line_qty = output.quantity
            lines = int(quantity / line_qty)
            for q in range(lines):
                move = self._explode_move_values(self.location,
                    storage_location, self.company, output, line_qty)
                if move:
                    move.unit_price = Decimal(0)
                    if output.product == move.product and quantity:
                        move.unit_price = Decimal(
                            self.cost / Decimal(str(quantity))
                            ).quantize(Decimal(str(10 ** -digits[1])))
                    outputs.append(move)
        self.outputs = outputs

    @classmethod
    def run(cls, productions):
        cls.update_inputs_origin(productions)
        super().run(productions)

    @classmethod
    def update_inputs_origin(cls, productions):
        for p in productions:
            for m in p.inputs:
                m.origin = p
                m.save()

    @classmethod
    def done(cls, productions):
        cls.update_outputs_origin(productions)
        cls.update_outputs_costs(productions)
        cls.create_lot(productions)
        super().done(productions)

    @classmethod
    def update_outputs_origin(cls, productions):
        for p in productions:
            for m in p.outputs:
                m.origin = p
                m.save()

    @classmethod
    def update_outputs_costs(cls, productions):
        pool = Pool()
        Template = pool.get('product.template')
        Product = pool.get('product.product')
        if hasattr(Product, 'cost_price'):
            digits = Product.cost_price.digits
        else:
            digits = Template.cost_price.digits
        for production in productions:
            if production.bom:
                divide_lots = production.bom.divide_lots
                factor = production.bom.compute_factor(production.product,
                    production.quantity or 0, production.uom)
            else:
                divide_lots = False
            cost_price = production.cost
            for output in production.outputs:
                if divide_lots:
                    quantity = output.uom.round(output.quantity * factor)
                else:
                    quantity = output.uom.round(output.quantity)
                if quantity:
                    output.unit_price = Decimal(0)
                    output.unit_price = Decimal(
                        cost_price / Decimal(str(quantity))
                        ).quantize(Decimal(str(10 ** -digits[1])))
                    output.save()

    @classmethod
    def create_lot(cls, productions):
        pool = Pool()
        Config = pool.get('production.configuration')
        Sequence = pool.get('ir.sequence')
        Lot = pool.get('stock.lot')
        Move = pool.get('stock.move')

        config = Config(1)
        for production in productions:
            for move in production.outputs:
                number = Sequence.get_id(config.lot_sequence.id)
                lot = Lot(
                    number=number,
                    product=move.product,
                    concentration=production.concentration,
                    preparation_date=production.preparation_date,
                    expiration_date=production.expiration_date,
                    technician=(production.technician.id if
                        production.technician else None),
                    solvent=(production.solvent.id if production.solvent
                        else None),
                    )
                if lot:
                    lot.save()
                    Move.write([move], {'lot': lot})

    def _explode_move_values(self, from_location, to_location, company,
            bom_io, quantity):
        User = Pool().get('res.user')
        product_location = None
        for d in User(Transaction().user).departments:
            if d.default:
                for l in bom_io.product.locations:
                    if l.department == d.department:
                        product_location = l.location
                        break
                break

        if product_location:
            if from_location == self.location:
                to_location = product_location
            else:
                from_location = product_location
        return super()._explode_move_values(from_location, to_location,
            company, bom_io, quantity)
