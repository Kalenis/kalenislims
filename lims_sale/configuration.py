# This file is part of lims_sale module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta


class Configuration(metaclass=PoolMeta):
    __name__ = 'sale.configuration'

    email_quotation_subject = fields.Char('Subject of the quotation email')
    email_quotation_body = fields.Text('Body of the quotation email')


class Cron(metaclass=PoolMeta):
    __name__ = 'ir.cron'

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.method.selection.extend([
                ('sale.sale|cron_send_quotation',
                    "Send Quotations"),
                ])
