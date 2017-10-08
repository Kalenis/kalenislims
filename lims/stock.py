# -*- coding: utf-8 -*-
# This file is part of lims module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pyson import In, Eval, Bool
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction

__all__ = ['Location', 'Move', 'ShipmentInternal', 'InventoryLine']


class Location:
    __name__ = 'stock.location'
    __metaclass__ = PoolMeta

    storage_time = fields.Integer('Storage time (in months)')

    @classmethod
    def search_rec_name(cls, name, clause):
        field = None
        for field in ('code', 'name'):
            records = cls.search([(field,) + tuple(clause[1:])], limit=1)
            if records:
                break
        if records:
            return [(field,) + tuple(clause[1:])]
        return [(cls._rec_name,) + tuple(clause[1:])]


class Move:
    __name__ = 'stock.move'
    __metaclass__ = PoolMeta

    fraction = fields.Many2One('lims.fraction', 'Fraction', select=True,
        ondelete='CASCADE', states={
            'readonly': (In(Eval('state'), ['cancel', 'assigned', 'done'])
                | Bool(Eval('fraction_readonly')))},
        domain=['OR',
            ('current_location', '=', Eval('from_location')),
            ('id', '=', Eval('fraction')),
            ],
        depends=['state', 'fraction_readonly', 'from_location'])
    fraction_readonly = fields.Function(fields.Boolean('Fraction Read Only'),
        'on_change_with_fraction_readonly')

    @classmethod
    def __setup__(cls):
        super(Move, cls).__setup__()
        cls.origin.readonly = True

    @classmethod
    def _get_origin(cls):
        models = super(Move, cls)._get_origin()
        models.append('lims.fraction')
        return models

    @fields.depends('from_location', 'to_location', 'product')
    def on_change_with_fraction_readonly(self, name=None):
        Config = Pool().get('lims.configuration')

        config = Config(1)
        if not config.fraction_product:
            return True
        if not self.product or self.product != config.fraction_product:
            return True
        if (self.from_location and self.to_location
                and self.from_location.type == 'storage'
                and self.to_location.type == 'storage'):
            return False
        return True

    @classmethod
    def copy(cls, moves, default=None):
        with Transaction().set_context(check_current_location=False):
            return super(Move, cls).copy(moves, default=default)


class ShipmentInternal:
    __name__ = 'stock.shipment.internal'
    __metaclass__ = PoolMeta

    @classmethod
    def copy(cls, shipments, default=None):
        with Transaction().set_context(check_current_location=False):
            return super(ShipmentInternal, cls).copy(shipments,
                default=default)

    @classmethod
    def draft(cls, shipments):
        with Transaction().set_context(check_current_location=False):
            super(ShipmentInternal, cls).draft(shipments)

    @classmethod
    def wait(cls, shipments):
        with Transaction().set_context(check_current_location=False):
            super(ShipmentInternal, cls).wait(shipments)

    @classmethod
    def done(cls, shipments):
        with Transaction().set_context(check_current_location=False):
            super(ShipmentInternal, cls).done(shipments)

    @classmethod
    def cancel(cls, shipments):
        with Transaction().set_context(check_current_location=False):
            super(ShipmentInternal, cls).cancel(shipments)

    @classmethod
    def assign_try(cls, shipments):
        with Transaction().set_context(check_current_location=False):
            return super(ShipmentInternal, cls).assign_try(shipments)

    @classmethod
    def assign_force(cls, shipments):
        with Transaction().set_context(check_current_location=False):
            super(ShipmentInternal, cls).assign_force(shipments)


class InventoryLine:
    __name__ = 'stock.inventory.line'
    __metaclass__ = PoolMeta

    account_move = fields.Function(fields.Many2One('account.move',
        'Account Move'), 'get_account_move')

    def get_account_move_id(self, account_move):
        if not account_move:
            return None
        if not account_move.origin:
            return None
        AccountMove = Pool().get('account.move')
        account_move_origin = '%s,%s' % (account_move.origin.__name__,
                account_move.origin.id)
        account_move, = AccountMove.search([
            'origin', '=', account_move_origin,
            ])
        return account_move.id

    def get_account_move(self, name):
        for move in self.moves:
            account_move = move._get_account_stock_move()
            return self.get_account_move_id(account_move)
        return None
