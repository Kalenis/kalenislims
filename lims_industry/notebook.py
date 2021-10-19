# This file is part of lims_industry module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import Pool, PoolMeta


class Notebook(metaclass=PoolMeta):
    __name__ = 'lims.notebook'

    plant = fields.Function(fields.Many2One('lims.plant', 'Plant'),
        'get_sample_field', searcher='search_sample_field')
    equipment = fields.Function(fields.Many2One('lims.equipment', 'Equipment'),
        'get_sample_field', searcher='search_sample_field')
    equipment_template = fields.Function(fields.Many2One(
        'lims.equipment.template', 'Equipment Template'),
        'get_sample_field')
    equipment_model = fields.Function(fields.Char('Equipment Model'),
        'get_sample_field')
    equipment_serial_number = fields.Function(fields.Char(
        'Equipment Serial Number'), 'get_sample_field')
    equipment_name = fields.Function(fields.Char(
        'Equipment Name'), 'get_sample_field')
    component = fields.Function(fields.Many2One('lims.component', 'Component'),
        'get_sample_field', searcher='search_sample_field')
    comercial_product = fields.Function(fields.Many2One(
        'lims.comercial.product', 'Comercial Product'),
        'get_sample_field', searcher='search_sample_field')
    ind_component = fields.Function(fields.Integer('Hs/Km Component'),
        'get_sample_field', searcher='search_sample_field')

    def _order_sample_field(name):
        def order_field(tables):
            pool = Pool()
            Sample = pool.get('lims.sample')
            Fraction = pool.get('lims.fraction')
            field = Sample._fields[name]
            table, _ = tables[None]
            fraction_tables = tables.get('fraction')
            if fraction_tables is None:
                fraction = Fraction.__table__()
                fraction_tables = {
                    None: (fraction, fraction.id == table.fraction),
                    }
                tables['fraction'] = fraction_tables
            return field.convert_order(name, fraction_tables, Fraction)
        return staticmethod(order_field)
    order_equipment = _order_sample_field('equipment')
    order_component = _order_sample_field('component')
    order_comercial_product = _order_sample_field('comercial_product')
    order_ind_component = _order_sample_field('ind_component')
