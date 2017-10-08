# -*- coding: utf-8 -*-
# This file is part of lims_project_study_plan module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond import backend
from trytond.model import fields
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Eval

__all__ = ['LimsConfiguration', 'LimsConfigurationSequence',
    'LimsLabWorkYear', 'LimsLabWorkYearSequence']


class LimsConfiguration:
    __name__ = 'lims.configuration'
    __metaclass__ = PoolMeta

    sample_in_custody_sequence = fields.MultiValue(fields.Many2One(
        'ir.sequence', 'Sample in Custody Sequence', required=True,
        domain=[
            ('company', 'in',
                [Eval('context', {}).get('company', -1), None]),
            ('code', '=', 'lims.project.sample_in_custody'),
            ]))

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field == 'sample_in_custody_sequence':
            return pool.get('lims.configuration.sequence')
        return super(LimsConfiguration, cls).multivalue_model(field)

    @classmethod
    def default_sample_in_custody_sequence(cls, **pattern):
        return cls.multivalue_model(
            'sample_in_custody_sequence').default_sample_in_custody_sequence()


class LimsConfigurationSequence:
    __name__ = 'lims.configuration.sequence'
    __metaclass__ = PoolMeta

    sample_in_custody_sequence = fields.Many2One('ir.sequence',
        'Sample in Custody Sequence', depends=['company'], domain=[
            ('company', 'in', [Eval('company', -1), None]),
            ('code', '=', 'lims.project.sample_in_custody'),
            ])

    @classmethod
    def __register__(cls, module_name):
        TableHandler = backend.get('TableHandler')
        exist = TableHandler.table_exist(cls._table)
        if exist:
            table = TableHandler(cls, module_name)
            exist &= table.column_exist('sample_in_custody_sequence')

        super(LimsConfigurationSequence, cls).__register__(module_name)

        if not exist:
            # Re-migration
            cls._migrate_property([], [], [])

    @classmethod
    def _migrate_property(cls, field_names, value_names, fields):
        field_names.append('sample_in_custody_sequence')
        value_names.append('sample_in_custody_sequence')
        super(LimsConfigurationSequence, cls)._migrate_property(
            field_names, value_names, fields)

    @classmethod
    def default_sample_in_custody_sequence(cls):
        pool = Pool()
        ModelData = pool.get('ir.model.data')
        try:
            return ModelData.get_id('lims.project.sample_in_custody',
                'seq_sample_in_custody')
        except KeyError:
            return None


class LimsLabWorkYear:
    __name__ = 'lims.lab.workyear'
    __metaclass__ = PoolMeta

    project_study_plan_sequence = fields.MultiValue(fields.Many2One(
        'ir.sequence.strict', 'Study plan Projects Sequence', required=True,
        domain=[
            ('company', 'in',
                [Eval('context', {}).get('company', -1), None]),
            ('code', '=', 'lims.project'),
            ]))

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field == 'project_study_plan_sequence':
            return pool.get('lims.lab.workyear.sequence')
        return super(LimsLabWorkYear, cls).multivalue_model(field)


class LimsLabWorkYearSequence:
    __name__ = 'lims.lab.workyear.sequence'
    __metaclass__ = PoolMeta

    project_study_plan_sequence = fields.Many2One('ir.sequence.strict',
        'Study plan Projects Sequence', depends=['company'], domain=[
            ('company', 'in', [Eval('company', -1), None]),
            ('code', '=', 'lims.project'),
            ])

    @classmethod
    def __register__(cls, module_name):
        TableHandler = backend.get('TableHandler')
        exist = TableHandler.table_exist(cls._table)
        if exist:
            table = TableHandler(cls, module_name)
            exist &= table.column_exist('project_study_plan_sequence')

        super(LimsLabWorkYearSequence, cls).__register__(module_name)

        if not exist:
            # Re-migration
            cls._migrate_property([], [], [])

    @classmethod
    def _migrate_property(cls, field_names, value_names, fields):
        field_names.append('project_study_plan_sequence')
        value_names.append('project_study_plan_sequence')
        super(LimsLabWorkYearSequence, cls)._migrate_property(
            field_names, value_names, fields)
