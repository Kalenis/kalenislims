# -*- coding: utf-8 -*-
# This file is part of lims_account_invoice module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import PoolMeta


class Invoice(metaclass=PoolMeta):
    __name__ = 'account.invoice'

    def get_mail_subject_values(self):
        values = super().get_mail_subject_values()
        if self.invoice_type:
            values['invoice_type_code'] = self.invoice_type.invoice_type
            name = self.invoice_type.rec_name.rsplit(' ', 1)
            values['invoice_type'] = name[0]
            values['letter'] = name[1] if len(name) > 1 else ''
        if self.pos:
            values['pos'] = str(self.pos.number)
        if self.number and '-' in self.number:
            values['voucher_number'] = self.number.split('-', 1)[1]
        return values
