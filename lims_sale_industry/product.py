# -*- coding: utf-8 -*-
# This file is part of lims_sale module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta

__all__ = ['Template']


class Template(metaclass=PoolMeta):
    __name__ = 'product.template'

    create_task_quotation = fields.Boolean(
        'Generate administrative task with quotation')
