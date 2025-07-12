# This file is part of lims_industry module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelSQL, ModelView, fields
from trytond.pool import PoolMeta


class SampleAttributeSet(ModelSQL, ModelView):
    'Sample Attribute Set'
    __name__ = 'lims.sample.attribute.set'

    name = fields.Char('Name', required=True)
    attributes = fields.Many2Many('lims.sample.attribute-attribute.set',
        'attribute_set', 'attribute', 'Attributes')


class SampleAttribute(metaclass=PoolMeta):
    __name__ = 'lims.sample.attribute'

    sets = fields.Many2Many('lims.sample.attribute-attribute.set',
        'attribute', 'attribute_set', 'Sets')


class SampleAttributeAttributeSet(ModelSQL):
    'Sample Attribute - Set'
    __name__ = 'lims.sample.attribute-attribute.set'
    _table = 'lims_sample_attribute_attribute_set'

    attribute = fields.Many2One('lims.sample.attribute', 'Attribute',
        required=True, ondelete='CASCADE')
    attribute_set = fields.Many2One('lims.sample.attribute.set', 'Set',
        required=True, ondelete='CASCADE')


class SamplingType(ModelSQL, ModelView):
    'Sampling Type'
    __name__ = 'lims.sampling.type'

    name = fields.Char('Name', required=True)
    description = fields.Char('Description', required=True, translate=True)


class ProductType(metaclass=PoolMeta):
    __name__ = 'lims.product.type'

    attribute_set = fields.Many2One('lims.sample.attribute.set',
        'Attribute Set')


class Analysis(metaclass=PoolMeta):
    __name__ = 'lims.analysis'

    ind_volume = fields.Float('Required volume')
    ind_volume_uom = fields.Many2One('product.uom', 'Required volume UoM')
