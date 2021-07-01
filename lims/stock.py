# -*- coding: utf-8 -*-
# This file is part of lims module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields, ModelSQL
from trytond.pyson import In, Eval, Bool, If
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction


class Location(metaclass=PoolMeta):
    __name__ = 'stock.location'

    storage_time = fields.Integer('Storage time (in months)')
    internal_shipment_to_location_restrictions =\
        fields.Many2Many('stock.location-stock.location',
                         'from_location','to_location',
                         'Internal Shipment To Location Restrictions')

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


class Move(metaclass=PoolMeta):
    __name__ = 'stock.move'

    fraction = fields.Many2One('lims.fraction', 'Fraction', select=True,
        ondelete='CASCADE', states={
            'readonly': (In(Eval('state'), ['cancel', 'assigned', 'done']) |
                Bool(Eval('fraction_readonly')))},
        domain=[
            If(~Eval('fraction'),
                ('current_location', '=', Eval('from_location')),
                ('id', '=', Eval('fraction'))),
            ],
        depends=['state', 'fraction_readonly', 'from_location'])
    fraction_readonly = fields.Function(fields.Boolean('Fraction Read Only'),
        'on_change_with_fraction_readonly')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.origin.readonly = True

    @classmethod
    def _get_origin(cls):
        models = super()._get_origin()
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
        if (self.from_location and self.to_location and
                self.from_location.type == 'storage' and
                self.to_location.type == 'storage'):
            return False
        return True

    @classmethod
    def copy(cls, moves, default=None):
        with Transaction().set_context(check_current_location=False):
            return super().copy(moves, default=default)


class ShipmentInternal(metaclass=PoolMeta):
    __name__ = 'stock.shipment.internal'

    to_location_domain = fields.Function(fields.Many2Many(
        'stock.location',None, None,
        'Internal Shipment To Location Restrictions'), 'on_change_with_to_location_domain')

    @fields.depends('from_location')
    def on_change_with_to_location_domain(self, name=None):
        if self.from_location and self.from_location.internal_shipment_to_location_restrictions:
            return [x.id for x in self.from_location.internal_shipment_to_location_restrictions]
        return []

    @classmethod
    def copy(cls, shipments, default=None):
        with Transaction().set_context(check_current_location=False):
            return super().copy(shipments, default=default)

    @classmethod
    def _sync_moves(cls, shipments):
        with Transaction().set_context(check_current_location=False):
            super()._sync_moves(shipments)

    @classmethod
    def _set_transit(cls, shipments):
        with Transaction().set_context(check_current_location=False):
            super()._set_transit(shipments)

    @classmethod
    def draft(cls, shipments):
        with Transaction().set_context(check_current_location=False):
            super().draft(shipments)

    @classmethod
    def wait(cls, shipments):
        with Transaction().set_context(check_current_location=False):
            super().wait(shipments)

    @classmethod
    def ship(cls, shipments):
        with Transaction().set_context(check_current_location=False):
            super().ship(shipments)

    @classmethod
    def done(cls, shipments):
        with Transaction().set_context(check_current_location=False):
            super().done(shipments)

    @classmethod
    def cancel(cls, shipments):
        with Transaction().set_context(check_current_location=False):
            super().cancel(shipments)

    @classmethod
    def assign_try(cls, shipments):
        with Transaction().set_context(check_current_location=False):
            return super().assign_try(shipments)

    @classmethod
    def assign_force(cls, shipments):
        with Transaction().set_context(check_current_location=False):
            super().assign_force(shipments)

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.to_location.domain = [
            [('type', 'in', ['view', 'storage', 'lost_found'])],
            [If(Eval('to_location_domain'),
                ('id','in',Eval('to_location_domain')),
                ('id','>',0))]]


class LocationShipmentInternalRestrictionLocation(ModelSQL):
    'Location restriction'
    __name__ = 'stock.location-stock.location'

    from_location =\
        fields.Many2One('stock.location', 'Input location',
            required=True, ondelete='CASCADE')
    to_location =\
        fields.Many2One('stock.location', 'Output location',
            required=True, ondelete='CASCADE')
