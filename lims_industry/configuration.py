# This file is part of lims_industry module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pyson import Eval
from trytond.pool import Pool, PoolMeta

__all__ = ['Configuration', 'ConfigurationSequence', 'LabWorkYear',
    'LabWorkYearSequence']


class Configuration(metaclass=PoolMeta):
    __name__ = 'lims.configuration'

    rack_sequence = fields.MultiValue(fields.Many2One(
        'ir.sequence', 'Rack Sequence', required=True,
        domain=[
            ('company', 'in',
                [Eval('context', {}).get('company', -1), None]),
            ('code', '=', 'lims.planification'),
            ]))

    @classmethod
    def default_rack_sequence(cls, **pattern):
        return cls.multivalue_model(
            'rack_sequence').default_rack_sequence()

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field == 'rack_sequence':
            return pool.get('lims.configuration.sequence')
        return super(Configuration, cls).multivalue_model(field)


class ConfigurationSequence(metaclass=PoolMeta):
    __name__ = 'lims.configuration.sequence'

    rack_sequence = fields.Many2One('ir.sequence',
        'Rack Sequence', depends=['company'], domain=[
            ('company', 'in', [Eval('company', -1), None]),
            ('code', '=', 'lims.planification'),
            ])

    @classmethod
    def default_rack_sequence(cls):
        pool = Pool()
        ModelData = pool.get('ir.model.data')
        try:
            return ModelData.get_id('lims.planification', 'seq_rack')
        except KeyError:
            return None


class LabWorkYear(metaclass=PoolMeta):
    __name__ = 'lims.lab.workyear'

    aliquot_sequence = fields.MultiValue(fields.Many2One(
        'ir.sequence', 'Aliquot Sequence', required=True,
        domain=[
            ('company', 'in',
                [Eval('context', {}).get('company', -1), None]),
            ('code', '=', 'lims.aliquot'),
            ]))

    @classmethod
    def default_aliquot_sequence(cls, **pattern):
        return cls.multivalue_model(
            'aliquot_sequence').default_aliquot_sequence()

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field == 'aliquot_sequence':
            return pool.get('lims.lab.workyear.sequence')
        return super(LabWorkYear, cls).multivalue_model(field)


class LabWorkYearSequence(metaclass=PoolMeta):
    __name__ = 'lims.lab.workyear.sequence'

    aliquot_sequence = fields.Many2One('ir.sequence',
        'Aliquot Sequence', depends=['company'], domain=[
            ('company', 'in', [Eval('company', -1), None]),
            ('code', '=', 'lims.aliquot'),
            ])

    @classmethod
    def default_aliquot_sequence(cls):
        pool = Pool()
        ModelData = pool.get('ir.model.data')
        try:
            return ModelData.get_id('lims.aliquot', 'seq_aliquot')
        except KeyError:
            return None
