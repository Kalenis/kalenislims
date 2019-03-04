# -*- coding: utf-8 -*-
# This file is part of lims_project_tas module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Eval

__all__ = ['LabWorkYear', 'LabWorkYearSequence']


class LabWorkYear(metaclass=PoolMeta):
    __name__ = 'lims.lab.workyear'

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
        return super(LabWorkYear, cls).multivalue_model(field)


class LabWorkYearSequence(metaclass=PoolMeta):
    __name__ = 'lims.lab.workyear.sequence'

    project_tas_sequence = fields.Many2One('ir.sequence.strict',
        'TAS Projects Sequence', depends=['company'], domain=[
            ('company', 'in', [Eval('company', -1), None]),
            ('code', '=', 'lims.project'),
            ])
