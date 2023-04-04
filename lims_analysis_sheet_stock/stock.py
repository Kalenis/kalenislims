# This file is part of lims_analysis_sheet_stock module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelSQL, ModelView, fields, DictSchemaMixin
from trytond.pool import PoolMeta
from trytond.pyson import Eval


class LotAttributeType(ModelSQL, ModelView):
    'Lot Attribute Type'
    __name__ = 'stock.lot.attribute.type'

    name = fields.Char('Name', required=True)
    attributes = fields.One2Many('stock.lot.attribute', 'type',
        'Attributes')


class LotAttribute(DictSchemaMixin, ModelSQL, ModelView):
    'Lot Attribute'
    __name__ = 'stock.lot.attribute'
    _rec_name = 'name'

    type = fields.Many2One('stock.lot.attribute.type', 'Type',
        required=True, ondelete='CASCADE')

    @staticmethod
    def default_type_():
        return 'char'


class ProductCategory(metaclass=PoolMeta):
    __name__ = 'product.category'

    lot_attribute_types = fields.Many2Many(
        'product.category-stock.lot.attribute.type',
        'category', 'attribute_type', 'Lot Attribute Types')


class ProductCategoryLotAttributeType(ModelSQL):
    'Product Category - Lot Attribute Type'
    __name__ = 'product.category-stock.lot.attribute.type'
    _table = 'product_category_stock_lot_attribute_type'

    category = fields.Many2One('product.category',
        'Product Category', required=True, ondelete='CASCADE')
    attribute_type = fields.Many2One('stock.lot.attribute.type',
        'Lot Attribute Type', required=True, ondelete='CASCADE')


class Lot(metaclass=PoolMeta):
    __name__ = 'stock.lot'

    attributes = fields.Dict('stock.lot.attribute', 'Attributes',
        domain=[('type', 'in', Eval('attribute_types_domain'))])
    attributes_string = attributes.translated('attributes')
    attribute_types_domain = fields.Function(fields.Many2Many(
        'stock.lot.attribute.type', None, None, 'Attribute Types domain'),
        'on_change_with_attribute_types_domain')

    @fields.depends('product', '_parent_product.template')
    def on_change_with_attribute_types_domain(self, name=None):
        a_types = []
        if self.product and self.product.template.categories:
            for cat in self.product.template.categories:
                for a_type in cat.lot_attribute_types:
                    a_types.append(a_type.id)
        return a_types


class Move(metaclass=PoolMeta):
    __name__ = 'stock.move'

    @classmethod
    def _get_origin(cls):
        models = super()._get_origin()
        models.append('lims.analysis_sheet')
        return models
