# -*- coding: utf-8 -*-
# This file is part of lims_purchase module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.transaction import Transaction
from trytond.pyson import Eval
from trytond.pool import Pool, PoolMeta

__all__ = ['PurchaseRequest', 'CreatePurchase']


class PurchaseRequest:
    __name__ = 'purchase.request'
    __metaclass__ = PoolMeta

    create_date2 = fields.Function(fields.DateTime('Create Date'),
       'get_create_date2', searcher='search_create_date2')
    department = fields.Many2One('company.department', 'Department',
        required=True, domain=['OR', ('id', '=', Eval('department')),
            ('id', 'in', Eval('department_domain'))],
        states={'readonly': Eval('state') != 'draft'},
        depends=['department_domain', 'state'])
    department_domain = fields.Function(fields.Many2Many('company.department',
        None, None, 'Department domain'), 'get_department_domain')
    note = fields.Char('Note')

    @classmethod
    def __setup__(cls):
        super(PurchaseRequest, cls).__setup__()
        cls.product.readonly = False
        cls.product.states['readonly'] = Eval('state') != 'draft'
        if 'state' not in cls.product.depends:
            cls.product.depends.append('state')
        cls.company.readonly = False
        cls.company.states['readonly'] = Eval('state') != 'draft'
        if 'state' not in cls.company.depends:
            cls.company.depends.append('state')
        cls.warehouse.readonly = False
        cls.warehouse.states['readonly'] = Eval('state') != 'draft'
        if 'state' not in cls.warehouse.depends:
            cls.warehouse.depends.append('state')
        cls.warehouse.states['required'] = True
        cls.uom.states['readonly'] = True

    @staticmethod
    def default_state():
        return 'draft'

    @staticmethod
    def default_origin():
        return 'stock.order_point,-1'

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

    @classmethod
    def copy(cls, requests, default=None):
        if default is None:
            default = {}

        new_requests = []
        for request in requests:
            current_default = default.copy()
            current_default['party'] = None
            current_default['purchase_line'] = None

            new_request, = super(PurchaseRequest, cls).copy([request],
                default=current_default)
            new_requests.append(new_request)
        return new_requests

    def get_create_date2(self, name):
        return self.create_date.replace(microsecond=0)

    @classmethod
    def search_create_date2(cls, name, clause):
        cursor = Transaction().connection.cursor()
        operator_ = clause[1:2][0]
        cursor.execute('SELECT id '
                'FROM "' + cls._table + '" '
                'WHERE create_date' + operator_ + ' %s',
                clause[2:3])
        return [('id', 'in', [x[0] for x in cursor.fetchall()])]

    def get_department_domain(self, name=None):
        return self.default_department_domain()

    @fields.depends('product', 'warehouse', 'location', 'uom')
    def on_change_product(self):
        uom = None
        if self.product:
            uom = self.product.default_uom and \
                self.product.default_uom.id or None
            if not uom:
                uom = self.product.purchase_uom and \
                    self.product.purchase_uom.id or self.product.default_uom.id
        self.uom = uom


class CreatePurchase:
    __name__ = 'purchase.request.create_purchase'
    __metaclass__ = PoolMeta

    def _group_purchase_line_key(self, request):
        keys = list(super(CreatePurchase,
            self)._group_purchase_line_key(request))
        keys.append(('department', request.department))
        return keys

    @classmethod
    def compute_purchase_line(cls, key, requests, purchase):
        line = super(CreatePurchase, cls).compute_purchase_line(key,
            requests, purchase)
        line.note = ' - '.join(r.note for r in requests)
        return line
