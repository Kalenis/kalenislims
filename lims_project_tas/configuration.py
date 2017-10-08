# -*- coding: utf-8 -*-
# This file is part of lims_project_tas module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond import backend
from trytond.model import fields
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Eval

__all__ = ['LimsLabWorkYear', 'LimsLabWorkYearSequence']


class LimsLabWorkYear:
    __name__ = 'lims.lab.workyear'
    __metaclass__ = PoolMeta

    project_tas_sequence = fields.MultiValue(fields.Many2One(
        'ir.sequence.strict', 'TAS Projects Sequence', required=True,
        domain=[
            ('company', 'in',
                [Eval('context', {}).get('company', -1), None]),
            ('code', '=', 'lims.project'),
            ]))

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field == 'project_tas_sequence':
            return pool.get('lims.lab.workyear.sequence')
        return super(LimsLabWorkYear, cls).multivalue_model(field)


class LimsLabWorkYearSequence:
    __name__ = 'lims.lab.workyear.sequence'
    __metaclass__ = PoolMeta

    project_tas_sequence = fields.Many2One('ir.sequence.strict',
        'TAS Projects Sequence', depends=['company'], domain=[
            ('company', 'in', [Eval('company', -1), None]),
            ('code', '=', 'lims.project'),
            ])

    @classmethod
    def __register__(cls, module_name):
        TableHandler = backend.get('TableHandler')
        exist = TableHandler.table_exist(cls._table)
        if exist:
            table = TableHandler(cls, module_name)
            exist &= table.column_exist('project_tas_sequence')

        super(LimsLabWorkYearSequence, cls).__register__(module_name)

        if not exist:
            # Re-migration
            cls._migrate_property([], [], [])

    @classmethod
    def _migrate_property(cls, field_names, value_names, fields):
        field_names.append('project_tas_sequence')
        value_names.append('project_tas_sequence')
        super(LimsLabWorkYearSequence, cls)._migrate_property(
            field_names, value_names, fields)
