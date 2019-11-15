# This file is part of lims_sale module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelSQL, ModelView, fields
from trytond.pool import PoolMeta

__all__ = ['Configuration', 'Clause']


class Configuration(metaclass=PoolMeta):
    __name__ = 'sale.configuration'

    email_quotation_subject = fields.Char('Subject of the quotation email')
    email_quotation_body = fields.Text('Body of the quotation email')


class Clause(ModelSQL, ModelView):
    'Clause'
    __name__ = 'sale.clause'

    name = fields.Char('Name', required=True)
    description = fields.Text('Description', required=True)
