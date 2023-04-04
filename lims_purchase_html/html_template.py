# This file is part of lims_purchase_html module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelSQL, ModelView, fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval


class PurchaseClauseTemplate(ModelSQL, ModelView):
    'Purchase Clause Template'
    __name__ = 'purchase.clause.template'

    name = fields.Char('Name', required=True)
    content = fields.Text('Content', required=True)


class PurchaseReportTemplate(metaclass=PoolMeta):
    __name__ = 'lims.report.template'

    clause_template = fields.Many2One('purchase.clause.template',
        'Clauses Template',
        states={'invisible': Eval('type') != 'base'})
