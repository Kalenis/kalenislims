# This file is part of lims_report_html module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta


class Notebook(metaclass=PoolMeta):
    __name__ = 'lims.notebook'

    result_template = fields.Function(fields.Many2One(
        'lims.report.template', 'Report Template'), 'get_sample_field')
    resultrange_origin = fields.Function(fields.Many2One('lims.range.type',
        'Comparison range'), 'get_sample_field')
