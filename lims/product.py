# -*- coding: utf-8 -*-
# This file is part of lims module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields, Unique
from trytond.pool import PoolMeta

__all__ = ['Uom', 'UomCategory', 'Template']


class Uom:
    __name__ = 'product.uom'
    __metaclass__ = PoolMeta

    maximum_concentration = fields.Char('Maximum concentration')
    rsd_horwitz = fields.Char('% RSD Horwitz')

    @classmethod
    def __setup__(cls):
        super(Uom, cls).__setup__()
        cls.symbol.size = 30
        t = cls.__table__()
        cls._sql_constraints += [
            ('symbol_uniq', Unique(t, t.symbol),
                'UoM symbol must be unique'),
            ]

    def get_rec_name(self, name):
        return self.symbol


class UomCategory:
    __name__ = 'product.uom.category'
    __metaclass__ = PoolMeta

    lims_only_available = fields.Boolean('Only available in Lims')

    @staticmethod
    def default_lims_only_available():
        return False


class Template:
    __name__ = "product.template"
    __metaclass__ = PoolMeta

    @classmethod
    def __setup__(cls):
        super(Template, cls).__setup__()
        new_domain = [('category.lims_only_available', '!=', True)]
        cls.default_uom.domain = new_domain
