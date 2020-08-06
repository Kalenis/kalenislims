# This file is part of lims_sale_industry module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Eval


class Configuration(metaclass=PoolMeta):
    __name__ = 'sale.configuration'

    sample_label_sequence = fields.MultiValue(fields.Many2One(
        'ir.sequence', 'Label Sequence', required=True,
        domain=[
            ('company', 'in',
                [Eval('context', {}).get('company', -1), None]),
            ('code', '=', 'lims.sample.label'),
            ]))

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field == 'sample_label_sequence':
            return pool.get('sale.configuration.sequence')
        return super().multivalue_model(field)

    @classmethod
    def default_sample_label_sequence(cls, **pattern):
        return cls.multivalue_model(
            'sample_label_sequence').default_sample_label_sequence()


class ConfigurationSequence(metaclass=PoolMeta):
    __name__ = 'sale.configuration.sequence'

    sample_label_sequence = fields.Many2One('ir.sequence',
        'Label Sequence', depends=['company'], domain=[
            ('company', 'in', [Eval('company', -1), None]),
            ('code', '=', 'lims.sample.label'),
            ])

    @classmethod
    def default_sample_label_sequence(cls):
        pool = Pool()
        ModelData = pool.get('ir.model.data')
        try:
            return ModelData.get_id('lims_sale_industry',
                'sample_label_sequence')
        except KeyError:
            return None
