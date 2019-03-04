# -*- coding: utf-8 -*-
# This file is part of lims_production module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelSQL, fields
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Eval
from trytond.modules.company.model import CompanyValueMixin

__all__ = ['ProductionConfiguration', 'ProductionConfigurationLotSequence',
    'Configuration', 'ConfigurationSolvents']


class ProductionConfiguration(metaclass=PoolMeta):
    __name__ = 'production.configuration'

    lot_sequence = fields.MultiValue(fields.Many2One(
        'ir.sequence', 'Lot Sequence', required=True,
        domain=[
            ('company', 'in',
                [Eval('context', {}).get('company', -1), None]),
            ('code', '=', 'stock.lot'),
            ]))

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field == 'lot_sequence':
            return pool.get('production.configuration.lot_sequence')
        return super(ProductionConfiguration, cls).multivalue_model(field)

    @classmethod
    def default_lot_sequence(cls, **pattern):
        return cls.multivalue_model(
            'lot_sequence').default_lot_sequence()


class ProductionConfigurationLotSequence(ModelSQL, CompanyValueMixin):
    'Production Configuration Lot Sequence'
    __name__ = 'production.configuration.lot_sequence'

    lot_sequence = fields.Many2One('ir.sequence',
        'Lot Sequence', depends=['company'], domain=[
            ('company', 'in', [Eval('company', -1), None]),
            ('code', '=', 'stock.lot'),
            ])

    @classmethod
    def default_lot_sequence(cls):
        pool = Pool()
        ModelData = pool.get('ir.model.data')
        try:
            return ModelData.get_id('stock.lot', 'seq_lot')
        except KeyError:
            return None


class Configuration(metaclass=PoolMeta):
    __name__ = 'lims.configuration'

    solvents = fields.Many2Many('lims.configuration.solvents',
        'configuration', 'category', 'Solvents')
    lot_category_prod_sale = fields.Many2One('stock.lot.category',
        'Production for sale')
    lot_category_prod_domestic_use = fields.Many2One('stock.lot.category',
        'Production for domestic use')
    lot_category_input_prod = fields.Many2One('stock.lot.category',
        'Input for production')

    def get_solvents(self):
        res = []
        if self.solvents:
            for r in self.solvents:
                res.append(r.id)
                res.extend(self.get_solvent_childs(r.id))
        return res

    def get_solvent_childs(self, solvent_id):
        Category = Pool().get('product.category')

        res = []
        categories = Category.search([
            ('parent', '=', solvent_id),
            ])
        if categories:
            for c in categories:
                res.append(c.id)
                res.extend(self.get_solvent_childs(c.id))
        return res


class ConfigurationSolvents(ModelSQL):
    'Configuration - Solvents'
    __name__ = 'lims.configuration.solvents'

    configuration = fields.Many2One('lims.configuration', 'Configuration',
        ondelete='CASCADE', select=True, required=True)
    category = fields.Many2One('product.category', 'Category',
        ondelete='CASCADE', select=True, required=True)
