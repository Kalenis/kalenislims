# This file is part of lims_sale module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta


class LimsConfiguration(metaclass=PoolMeta):
    __name__ = 'lims.configuration'

    entry_use_sale_contacts = fields.Boolean(
        'Use the sales contacts in entries')

    @staticmethod
    def default_entry_use_sale_contacts():
        return False


class SaleConfiguration(metaclass=PoolMeta):
    __name__ = 'sale.configuration'

    email_quotation_subject = fields.Char('Subject of the quotation email')
    email_quotation_body = fields.Text('Body of the quotation email')
    allow_services_without_quotation = fields.Boolean(
        'Allow services without quotation')

    @staticmethod
    def default_allow_services_without_quotation():
        return True


class Cron(metaclass=PoolMeta):
    __name__ = 'ir.cron'

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.method.selection.extend([
                ('sale.sale|update_expired_sales_status',
                    'Update Expired Sales Status'),
                ])
