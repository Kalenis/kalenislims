# This file is part of lims_email module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta


class Entry(metaclass=PoolMeta):
    __name__ = 'lims.entry'

    email_report = fields.Boolean('Automatic sending of Report by Email')

    @staticmethod
    def default_email_report():
        return False

    @fields.depends('party')
    def on_change_party(self):
        super().on_change_party()
        email = False
        if self.party:
            email = self.party.email_report
        self.email_report = email
