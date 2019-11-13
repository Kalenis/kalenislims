# This file is part of lims_industry module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelSQL, ModelView, DictSchemaMixin, fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval

__all__ = ['SampleAttributeSet', 'SampleAttribute',
    'SampleAttributeAttributeSet', 'SamplingType', 'ProductType',
    'AliquotType', 'AliquotTypeProductType', 'Analysis']


class SampleAttributeSet(ModelSQL, ModelView):
    'Sample Attribute Set'
    __name__ = 'lims.sample.attribute.set'

    name = fields.Char('Name', required=True)
    attributes = fields.Many2Many('lims.sample.attribute-attribute.set',
        'attribute_set', 'attribute', 'Attributes')


class SampleAttribute(DictSchemaMixin, ModelSQL, ModelView):
    'Sample Attribute'
    __name__ = 'lims.sample.attribute'

    sets = fields.Many2Many('lims.sample.attribute-attribute.set',
        'attribute', 'attribute_set', 'Sets')


class SampleAttributeAttributeSet(ModelSQL):
    'Sample Attribute - Set'
    __name__ = 'lims.sample.attribute-attribute.set'
    _table = 'lims_sample_attribute_attribute_set'

    attribute = fields.Many2One('lims.sample.attribute', 'Attribute',
        required=True, ondelete='CASCADE', select=True)
    attribute_set = fields.Many2One('lims.sample.attribute.set', 'Set',
        required=True, ondelete='CASCADE', select=True)


class SamplingType(ModelSQL, ModelView):
    'Sampling Type'
    __name__ = 'lims.sampling.type'

    name = fields.Char('Name', required=True)
    description = fields.Char('Description', required=True)


class ProductType(metaclass=PoolMeta):
    __name__ = 'lims.product.type'

    attribute_set = fields.Many2One('lims.sample.attribute.set',
        'Attribute Set')


class AliquotType(ModelSQL, ModelView):
    'Aliquot Type'
    __name__ = 'lims.aliquot.type'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)
    ind_volume = fields.Float('Required volume')
    uom = fields.Many2One('product.uom', 'UoM')
    kind = fields.Selection([
        ('int', 'Internal'),
        ('ext', 'External'),
        ('rack', 'Rack'),
        ], 'Kind', sort=False, required=True)
    product_types = fields.Many2Many('lims.aliquot.type-product.type',
        'aliquot_type', 'product_type', 'Product types',
        depends=['kind'], states={
            'invisible': Eval('kind') != 'rack',
            'required': Eval('kind') == 'rack',
            })
    laboratory = fields.Many2One('party.party', 'Destination Laboratory',
        depends=['kind'], states={
            'invisible': Eval('kind') != 'ext',
            'required': Eval('kind') == 'ext',
            })
    preparation = fields.Boolean('Preparation',
        depends=['kind'], states={
            'invisible': Eval('kind') != 'int',
            })


class AliquotTypeProductType(ModelSQL):
    'Equipment Template - Component Type'
    __name__ = 'lims.aliquot.type-product.type'
    _table = 'lims_aliquot_type_product_type'

    aliquot_type = fields.Many2One('lims.aliquot.type', 'Aliquot type',
        required=True, ondelete='CASCADE', select=True)
    product_type = fields.Many2One('lims.product.type', 'Product type',
        required=True, ondelete='CASCADE', select=True)


class Analysis(metaclass=PoolMeta):
    __name__ = 'lims.analysis'

    aliquot_type = fields.Many2One('lims.aliquot.type', 'Aliquot type')
    ind_volume = fields.Float('Required volume')

    @fields.depends('aliquot_type')
    def on_change_aliquot_type(self):
        if self.aliquot_type:
            self.ind_volume = self.aliquot_type.ind_volume
