# -*- coding: utf-8 -*-
# This file is part of lims_project_tas module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval

__all__ = ['Invoice']


class Invoice(metaclass=PoolMeta):
    __name__ = 'account.invoice'

    lims_project = fields.Many2One('lims.project', 'TAS Project',
        domain=[('type', '=', 'tas')],
        states={
            'readonly': Eval('state') != 'draft',
            'invisible': Eval('type').in_(['in'])
            })
