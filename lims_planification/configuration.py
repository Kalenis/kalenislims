# -*- coding: utf-8 -*-
# This file is part of lims_planification module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond import backend
from trytond.model import ModelSQL, fields
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Eval
from trytond.tools.multivalue import migrate_property
from trytond.modules.company.model import (
    CompanyMultiValueMixin, CompanyValueMixin)

__all__ = ['LimsConfiguration', 'LimsConfigurationSequence',
    'LimsLabWorkYear', 'LimsConfigurationProductCategory']


class LimsConfiguration(CompanyMultiValueMixin):
    __name__ = 'lims.configuration'
    __metaclass__ = PoolMeta

    planification_sequence = fields.MultiValue(fields.Many2One(
        'ir.sequence', 'Planification Sequence', required=True,
        domain=[
            ('company', 'in',
                [Eval('context', {}).get('company', -1), None]),
            ('code', '=', 'lims.planification'),
            ]))
    mcl_fraction_type = fields.Many2One('lims.fraction.type',
        'MCL fraction type')
    con_fraction_type = fields.Many2One('lims.fraction.type',
        'Control fraction type')
    bmz_fraction_type = fields.Many2One('lims.fraction.type',
        'BMZ fraction type')
    rm_fraction_type = fields.Many2One('lims.fraction.type',
        'RM fraction type')
    bre_fraction_type = fields.Many2One('lims.fraction.type',
        'BRE fraction type')
    mrt_fraction_type = fields.Many2One('lims.fraction.type',
        'MRT fraction type')
    coi_fraction_type = fields.Many2One('lims.fraction.type',
        'COI fraction type')
    mrc_fraction_type = fields.Many2One('lims.fraction.type',
        'MRC fraction type')
    sla_fraction_type = fields.Many2One('lims.fraction.type',
        'SLA fraction type')
    itc_fraction_type = fields.Many2One('lims.fraction.type',
        'ITC fraction type')
    itl_fraction_type = fields.Many2One('lims.fraction.type',
        'ITL fraction type')
    reagents = fields.Many2Many('lims.configuration-product.category',
        'configuration', 'category', 'Reagents')
    planification_process_background = fields.Boolean(
        'Process Planifications in Background')

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field == 'planification_sequence':
            return pool.get('lims.configuration.sequence')
        return super(LimsConfiguration, cls).multivalue_model(field)

    @classmethod
    def default_planification_sequence(cls, **pattern):
        return cls.multivalue_model(
            'planification_sequence').default_planification_sequence()

    @staticmethod
    def default_planification_process_background():
        return False

    def get_reagents(self):
        res = []
        if self.reagents:
            for r in self.reagents:
                res.append(r.id)
                res.extend(self.get_reagent_childs(r.id))
        return res

    def get_reagent_childs(self, reagent_id):
        Category = Pool().get('product.category')

        res = []
        categories = Category.search([
            ('parent', '=', reagent_id),
            ])
        if categories:
            for c in categories:
                res.append(c.id)
                res.extend(self.get_reagent_childs(c.id))
        return res


class LimsConfigurationSequence(ModelSQL, CompanyValueMixin):
    'Configuration Sequence'
    __name__ = 'lims.configuration.sequence'

    planification_sequence = fields.Many2One('ir.sequence',
        'Planification Sequence', depends=['company'], domain=[
            ('company', 'in', [Eval('company', -1), None]),
            ('code', '=', 'lims.planification'),
            ])

    @classmethod
    def __register__(cls, module_name):
        TableHandler = backend.get('TableHandler')
        exist = TableHandler.table_exist(cls._table)

        super(LimsConfigurationSequence, cls).__register__(module_name)

        if not exist:
            cls._migrate_property([], [], [])

    @classmethod
    def _migrate_property(cls, field_names, value_names, fields):
        field_names.append('planification_sequence')
        value_names.append('planification_sequence')
        fields.append('company')
        migrate_property(
            'lims.configuration', field_names, cls, value_names,
            fields=fields)

    @classmethod
    def default_planification_sequence(cls):
        pool = Pool()
        ModelData = pool.get('ir.model.data')
        try:
            return ModelData.get_id('lims.planification', 'seq_planification')
        except KeyError:
            return None


class LimsConfigurationProductCategory(ModelSQL):
    'Configuration - Product Category'
    __name__ = 'lims.configuration-product.category'

    configuration = fields.Many2One('lims.configuration', 'Configuration',
        ondelete='CASCADE', select=True, required=True)
    category = fields.Many2One('product.category', 'Category',
        ondelete='CASCADE', select=True, required=True)


class LimsLabWorkYear:
    __name__ = 'lims.lab.workyear'
    __metaclass__ = PoolMeta

    default_entry_control = fields.Many2One('lims.entry',
        'Default entry control')
