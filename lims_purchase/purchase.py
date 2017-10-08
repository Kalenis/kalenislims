# -*- coding: utf-8 -*-
# This file is part of lims_purchase module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateAction, StateView, Button
from trytond.transaction import Transaction
from trytond.pyson import Eval, If, Bool
from trytond.pool import Pool, PoolMeta

__all__ = ['Purchase', 'PurchaseLine', 'ReturnPurchaseStart', 'ReturnPurchase',
    'LimsUserRole']


class Purchase:
    __name__ = 'purchase.purchase'
    __metaclass__ = PoolMeta

    @classmethod
    def __setup__(cls):
        super(Purchase, cls).__setup__()
        cls._error_messages.update({
                'amount_not_allowed': ('You are not allow to confirm '
                    'Purchase "%s" for the stated total amount.'),
                })

    @classmethod
    def confirm(cls, purchases):
        pool = Pool()
        User = pool.get('res.user')
        Currency = pool.get('currency.currency')

        user = User(Transaction().user)
        for p in purchases:
            purchase_amount_allowed = False
            if user.role and user.role.maximum_purchase_amount:
                amount = p.total_amount
                if p.currency != p.company.currency:
                    with Transaction().set_context(date=p.purchase_date):
                        amount = Currency.compute(p.currency, amount,
                            p.company.currency)
                if user.role.maximum_purchase_amount >= amount:
                    purchase_amount_allowed = True
            if not purchase_amount_allowed:
                cls.raise_user_error('amount_not_allowed', (p.rec_name,))
        super(Purchase, cls).confirm(purchases)

    def _get_return_shipment(self):
        return_shipment = super(Purchase, self)._get_return_shipment()
        return_shipment.from_location = self.warehouse.input_location
        return return_shipment


class PurchaseLine:
    __name__ = 'purchase.line'
    __metaclass__ = PoolMeta

    department = fields.Many2One('company.department', 'Department',
        domain=['OR', ('id', '=', Eval('department')),
            ('id', 'in', Eval('department_domain'))],
        depends=['department_domain'])
    department_domain = fields.Function(fields.Many2Many('company.department',
        None, None, 'Department domain'), 'get_department_domain')

    @classmethod
    def __setup__(cls):
        super(PurchaseLine, cls).__setup__()
        cls.delivery_date = fields.Date('Delivery Date',
                states={
                    'invisible': ((Eval('type') != 'line')
                        | (If(Bool(Eval('quantity')), Eval('quantity', 0), 0)
                            <= 0)),
                    },
                depends=['type', 'quantity'])

    @staticmethod
    def default_department():
        User = Pool().get('res.user')
        for d in User(Transaction().user).departments:
            if d.default:
                return d.department.id
        return None

    @staticmethod
    def default_department_domain():
        User = Pool().get('res.user')
        res = []
        for d in User(Transaction().user).departments:
            res.append(d.department.id)
        return res

    def get_department_domain(self, name=None):
        return self.default_department_domain()

    def get_move(self, move_type):
        move = super(PurchaseLine, self).get_move(move_type)
        if not move:
            return
        move.department = self.department
        return move

    def get_from_location(self, name):
        if self.quantity >= 0:
            return self.purchase.party.supplier_location.id
        elif self.purchase.warehouse:
            return self.purchase.warehouse.input_location.id


class ReturnPurchaseStart(ModelView):
    'Return Purchase'
    __name__ = 'purchase.return_purchase.start'


class ReturnPurchase(Wizard):
    'Return Purchase'
    __name__ = 'purchase.return_purchase'

    start = StateView('purchase.return_purchase.start',
        'lims_purchase.return_purchase_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Return', 'return_', 'tryton-ok', default=True),
            ])
    return_ = StateAction('purchase.act_purchase_form')

    def do_return_(self, action):
        Purchase = Pool().get('purchase.purchase')

        purchases = Purchase.browse(Transaction().context['active_ids'])
        return_purchases = Purchase.copy(purchases)
        for return_purchase in return_purchases:
            for line in return_purchase.lines:
                if line.type == 'line':
                    line.quantity *= -1
            return_purchase.lines = return_purchase.lines  # Force saving
        Purchase.save(return_purchases)

        data = {'res_id': [s.id for s in return_purchases]}
        if len(return_purchases) == 1:
            action['views'].reverse()
        return action, data


class LimsUserRole:
    __name__ = 'lims.user.role'
    __metaclass__ = PoolMeta

    maximum_purchase_amount = fields.Numeric('Maximum Purchase Amount')
