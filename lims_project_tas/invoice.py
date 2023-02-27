# -*- coding: utf-8 -*-
# This file is part of lims_project_tas module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction


class Invoice(metaclass=PoolMeta):
    __name__ = 'account.invoice'

    lims_project_tas = fields.Many2One('lims.project', 'TAS Project',
        domain=[('type', '=', 'tas')],
        states={
            'readonly': Eval('state') != 'draft',
            'invisible': Eval('type').in_(['in'])
            })

    @classmethod
    def __register__(cls, module_name):
        cursor = Transaction().connection.cursor()
        invoice_table = cls.__table__()

        table_h = cls.__table_handler__(module_name)
        lims_project_exist = table_h.column_exist('lims_project')
        lims_project_tas_exist = table_h.column_exist('lims_project_tas')

        super().__register__(module_name)

        if lims_project_exist and not lims_project_tas_exist:
            cursor.execute(*invoice_table.update(
                [invoice_table.lims_project_tas],
                [invoice_table.lims_project]))
            table_h.drop_column('lims_project')
