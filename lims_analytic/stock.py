# -*- coding: utf-8 -*-
# This file is part of lims_analytic module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from decimal import Decimal
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction

__all__ = ['Move']


class Move(metaclass=PoolMeta):
    __name__ = 'stock.move'

    def _get_account_stock_move_lines(self, type_):
        move_line, = super(Move, self)._get_account_stock_move_lines(type_)

        if move_line.account.kind != 'expense':
            return [move_line]

        analytic_account = None
        if type_ in ('out_lost_found', 'out_production'):
            if self.product.account_stock_used:
                if self.product.account_stock_used.kind == 'expense':
                    return [move_line]
            analytic_account = self.from_location.cost_center
        elif type_ == 'in_lost_found':
            if self.product.account_stock_used:
                if self.product.account_stock_used.kind == 'expense':
                    return [move_line]
            analytic_account = self.to_location.cost_center
        elif type_ in ('in_supplier', 'out_supplier'):
            if self.department:
                analytic_account = self.department.default_location.cost_center

        if not analytic_account:
            return [move_line]

        analytic_line = self._get_account_analytic_line(
            move_line, analytic_account)

        move_line.analytic_lines = [analytic_line]
        return [move_line]

    def _get_account_stock_move_line(self, amount, type_):
        '''
        Return counterpart move line value for stock move
        '''
        pool = Pool()
        AccountMoveLine = pool.get('account.move.line')
        move_line = AccountMoveLine(
            account=self.product.account_stock_used,
            )
        if not amount:
            return
        if amount >= Decimal('0.0'):
            move_line.debit = Decimal('0.0')
            move_line.credit = amount
        else:
            move_line.debit = - amount
            move_line.credit = Decimal('0.0')

        if move_line.account.kind != 'expense':
            return move_line

        analytic_account = None
        if type_ in ('out_lost_found', 'out_production'):
            if self.product.account_stock_used:
                if self.product.account_stock_used.kind == 'expense':
                    return move_line
            analytic_account = self.from_location.cost_center
        elif type_ == 'in_lost_found':
            if self.product.account_stock_used:
                if self.product.account_stock_used.kind == 'expense':
                    return move_line
            analytic_account = self.to_location.cost_center
        elif type_ in ('in_supplier', 'out_supplier'):
            if self.department:
                analytic_account = self.department.default_location.cost_center

        if not analytic_account:
            return move_line

        analytic_line = self._get_account_analytic_line(
            move_line, analytic_account)

        move_line.analytic_lines = [analytic_line]

        return move_line

    def _get_account_analytic_line(self, move_line, analytic_account):
        '''
        Return analytic line value for account move line
        '''
        pool = Pool()
        Date = pool.get('ir.date')
        AnalyticLine = pool.get('analytic_account.line')
        date = self.effective_date or Date.today()

        with Transaction().set_user(0, set_context=True):
            analytic_line = AnalyticLine(
                debit=move_line.debit,
                credit=move_line.credit,
                account=analytic_account.id,
                date=date,
                )
        return analytic_line

    def _get_account_stock_move(self):
        '''
        Return account move for stock move
        '''
        pool = Pool()
        AccountMove = pool.get('account.move')
        Date = pool.get('ir.date')
        Period = pool.get('account.period')
        AccountConfiguration = pool.get('account.configuration')

        if self.fraction:
            return

        if self.product.type != 'goods':
            return

        date = self.effective_date or Date.today()
        period_id = Period.find(self.company.id, date=date)
        period = Period(period_id)
        if not period.fiscalyear.account_stock_method:
            return

        type_ = self._get_account_stock_move_type()
        if not type_:
            return
        if type_ == 'supplier_customer':
            account_move_lines = self._get_account_stock_move_lines(
                'in_supplier')
            account_move_lines.extend(self._get_account_stock_move_lines(
                    'out_customer'))
        elif type_ == 'customer_supplier':
            account_move_lines = self._get_account_stock_move_lines(
                'in_customer')
            account_move_lines.extend(self._get_account_stock_move_lines(
                    'out_supplier'))
        else:
            account_move_lines = self._get_account_stock_move_lines(type_)

        amount = Decimal('0.0')
        for line in account_move_lines:
            amount += line.debit - line.credit
        move_line = self._get_account_stock_move_line(amount, type_)
        if move_line:
            account_move_lines.append(move_line)

        account_configuration = AccountConfiguration(1)
        return AccountMove(
            journal=account_configuration.stock_journal,
            period=period_id,
            date=date,
            origin=self,
            lines=account_move_lines,
            )
