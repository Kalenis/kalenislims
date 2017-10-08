# -*- coding: utf-8 -*-
# This file is part of lims_purchase module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import PoolMeta

__all__ = ['ShipmentIn', 'ShipmentOutReturn']


class ShipmentIn:
    __name__ = 'stock.shipment.in'
    __metaclass__ = PoolMeta

    @classmethod
    def _get_inventory_moves(cls, incoming_move):
        move = super(ShipmentIn, cls)._get_inventory_moves(incoming_move)
        if not move:
            return None

        # rewrite stock_product_location module behavior
        move.to_location = incoming_move.shipment.warehouse.storage_location

        if incoming_move.department:
            for l in incoming_move.product.locations:
                if (l.department == incoming_move.department and
                        l.warehouse.id == incoming_move.shipment.warehouse.id):
                    move.to_location = l.location
                    break

        move.department = incoming_move.department
        return move


class ShipmentOutReturn:
    __name__ = 'stock.shipment.out.return'
    __metaclass__ = PoolMeta

    @classmethod
    def _get_inventory_moves(cls, incoming_move):
        move = super(ShipmentOutReturn, cls)._get_inventory_moves(
            incoming_move)
        if not move:
            return None

        # rewrite stock_product_location module behavior
        move.to_location = incoming_move.shipment.warehouse.storage_location

        return move
