# -*- coding: utf-8 -*-
# This file is part of lims_account_invoice module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import PoolMeta


__all__ = ['LimsManageServices']


class LimsManageServices:
    __name__ = 'lims.manage_services'
    __metaclass__ = PoolMeta

    def create_service(self, service, fraction):
        new_service = super(LimsManageServices, self).create_service(service,
            fraction)
        new_service.create_invoice_line('out')
        return new_service
