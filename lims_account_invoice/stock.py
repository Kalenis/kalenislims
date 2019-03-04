# -*- coding: utf-8 -*-
# This file is part of lims module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import Pool, PoolMeta

__all__ = ['InventoryLine']


class InventoryLine(metaclass=PoolMeta):
    __name__ = 'stock.inventory.line'

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
