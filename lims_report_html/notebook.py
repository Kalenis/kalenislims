# This file is part of lims_report_html module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import Pool, PoolMeta


class Notebook(metaclass=PoolMeta):
    __name__ = 'lims.notebook'

    result_template = fields.Function(fields.Many2One(
        'lims.result_report.template', 'Report Template'), 'get_sample_field')
    resultrange_origin = fields.Function(fields.Many2One('lims.range.type',
        'Comparison range'), 'get_sample_field')

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
    order_result_template = _order_sample_field('result_template')
