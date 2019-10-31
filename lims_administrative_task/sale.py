# This file is part of lims_administrative_task module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import PoolMeta, Pool

__all__ = ['Sale', 'SaleLine']


class Sale(metaclass=PoolMeta):
    __name__ = 'sale.sale'

    @classmethod
    def confirm(cls, sales):
        pool = Pool()
        TaskTemplate = pool.get('lims.administrative.task.template')
        SaleLine = pool.get('sale.line')
        super(Sale, cls).confirm(sales)
        records = cls.check_for_tasks(sales)
        TaskTemplate.create_tasks(cls.__name__, records)
        SaleLine._confirm_sale(l for s in sales for l in s.lines)

    @classmethod
    def check_for_tasks(cls, sales):
        AdministrativeTask = Pool().get('lims.administrative.task')
        res = []
        for sale in sales:
            if not (sale.invoice_party.purchase_order_required and
                    not sale.purchase_order):
                continue
            if AdministrativeTask.search([
                    ('origin', '=', '%s,%s' % (cls.__name__, sale.id)),
                    ('state', 'not in', ('done', 'discarded')),
                    ]):
                continue
            res.append(sale)
        return res


class SaleLine(metaclass=PoolMeta):
    __name__ = 'sale.line'

    @classmethod
    def _confirm_sale(cls, lines):
        TaskTemplate = Pool().get('lims.administrative.task.template')
        records = cls.check_for_tasks(lines)
        TaskTemplate.create_tasks(cls.__name__, records)

    @classmethod
    def check_for_tasks(cls, lines):
        AdministrativeTask = Pool().get('lims.administrative.task')
        res = []
        for line in lines:
            if not line.product or not line.product.create_task_quotation:
                continue
            if AdministrativeTask.search([
                    ('origin', '=', '%s,%s' % (cls.__name__, line.id)),
                    ('state', 'not in', ('done', 'discarded')),
                    ]):
                continue
            res.append(line)
        return res
