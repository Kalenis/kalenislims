# -*- coding: utf-8 -*-
# This file is part of lims_analytic module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from decimal import Decimal

from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction


class Move(metaclass=PoolMeta):
    __name__ = 'stock.move'

    def _get_account_stock_move_lines(self, type_):
        move_line, = super()._get_account_stock_move_lines(type_)

        if not move_line.account.type.expense:
            return [move_line]

        analytic_account = None
        if type_ in ('out_lost_found', 'out_production'):
            if self.product.account_stock_used:
                if self.product.account_stock_used.type.expense:
                    return [move_line]
            analytic_account = self.from_location.cost_center
        elif type_ == 'in_lost_found':
            if self.product.account_stock_used:
                if self.product.account_stock_used.type.expense:
                    return [move_line]
            analytic_account = self.to_location.cost_center
        elif type_ in ('in_supplier', 'out_supplier'):
            if self.department:
                analytic_account = self.department.default_location.cost_center
        if not analytic_account:
            return [move_line]

        analytic_lines = list(self._get_account_analytic_lines(move_line,
            analytic_account))
        move_line.analytic_lines = analytic_lines
        return [move_line]

    def _get_account_stock_move_line(self, amount):
        move_line = super()._get_account_stock_move_line(amount)
        if not move_line:
            return

        if not move_line.account.type.expense:
            return move_line

        type_ = self._get_account_stock_move_type()
        analytic_account = None
        if type_ in ('out_lost_found', 'out_production'):
            if self.product.account_stock_used:
                if self.product.account_stock_used.type.expense:
                    return move_line
            analytic_account = self.from_location.cost_center
        elif type_ == 'in_lost_found':
            if self.product.account_stock_used:
                if self.product.account_stock_used.type.expense:
                    return move_line
            analytic_account = self.to_location.cost_center
        elif type_ in ('in_supplier', 'out_supplier'):
            if self.department:
                analytic_account = self.department.default_location.cost_center
        if not analytic_account:
            return move_line

        analytic_lines = list(self._get_account_analytic_lines(move_line,
            analytic_account))
        move_line.analytic_lines = analytic_lines
        return move_line

    def _get_account_analytic_lines(self, line, analytic_account):
        '''
        Yield analytic lines for the accounting line
        '''
        pool = Pool()
        Date = pool.get('ir.date')
        AnalyticLine = pool.get('analytic_account.line')

        date = self.effective_date or Date.today()
        amount = line.debit or line.credit

        with Transaction().set_user(0, set_context=True):
            for account, amount in analytic_account.distribute(amount):
                analytic_line = AnalyticLine()
                analytic_line.debit = amount if line.debit else Decimal(0)
                analytic_line.credit = amount if line.credit else Decimal(0)
                analytic_line.account = account
                analytic_line.date = date
                yield analytic_line

    def _get_account_stock_move(self):
        if self.fraction:
            return
        return super()._get_account_stock_move()
