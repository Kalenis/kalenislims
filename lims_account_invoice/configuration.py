# -*- coding: utf-8 -*-
# This file is part of lims_account_invoice module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta

__all__ = ['Configuration']


class Configuration(metaclass=PoolMeta):
    __name__ = 'lims.configuration'

    mail_send_invoice_subject = fields.Char('Email subject of Invoice report',
        help="In the text will be added suffix with the invoice report number")
    mail_send_invoice_body = fields.Text('Email body of Invoice report')
