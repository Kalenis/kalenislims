# -*- coding: utf-8 -*-
# This file is part of lims_project_study_plan module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Eval, Id


class Configuration(metaclass=PoolMeta):
    __name__ = 'lims.configuration'

    sample_in_custody_sequence = fields.MultiValue(fields.Many2One(
        'ir.sequence', 'Sample in Custody Sequence', required=True,
        domain=[
            ('sequence_type', '=',
                Id('lims_project_study_plan', 'seq_type_sample_in_custody')),
            ('company', 'in',
                [Eval('context', {}).get('company', -1), None]),
            ]))

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field == 'sample_in_custody_sequence':
            return pool.get('lims.configuration.sequence')
        return super().multivalue_model(field)

    @classmethod
    def default_sample_in_custody_sequence(cls, **pattern):
        return cls.multivalue_model(
            'sample_in_custody_sequence').default_sample_in_custody_sequence()


class ConfigurationSequence(metaclass=PoolMeta):
    __name__ = 'lims.configuration.sequence'

    sample_in_custody_sequence = fields.Many2One('ir.sequence',
        'Sample in Custody Sequence', depends=['company'], domain=[
            ('sequence_type', '=',
                Id('lims_project_study_plan', 'seq_type_sample_in_custody')),
            ('company', 'in', [Eval('company', -1), None]),
            ])

    @classmethod
    def default_sample_in_custody_sequence(cls):
        pool = Pool()
        ModelData = pool.get('ir.model.data')
        try:
            return ModelData.get_id('lims.project.sample_in_custody',
                'seq_sample_in_custody')
        except KeyError:
            return None


class LabWorkYear(metaclass=PoolMeta):
    __name__ = 'lims.lab.workyear'

    project_study_plan_sequence = fields.MultiValue(fields.Many2One(
        'ir.sequence.strict', 'Study plan Projects Sequence', required=True,
        domain=[
            ('sequence_type', '=',
                Id('lims_project_study_plan', 'seq_type_stp_project')),
            ('company', 'in',
                [Eval('context', {}).get('company', -1), None]),
            ]))

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field == 'project_study_plan_sequence':
            return pool.get('lims.lab.workyear.sequence')
        return super().multivalue_model(field)


class LabWorkYearSequence(metaclass=PoolMeta):
    __name__ = 'lims.lab.workyear.sequence'

    project_study_plan_sequence = fields.Many2One('ir.sequence.strict',
        'Study plan Projects Sequence', depends=['company'], domain=[
            ('sequence_type', '=',
                Id('lims_project_study_plan', 'seq_type_stp_project')),
            ('company', 'in', [Eval('company', -1), None]),
            ])
