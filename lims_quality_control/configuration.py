# This file is part of lims_quality_control module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelView, ModelSQL, fields, ModelSingleton
from trytond.pyson import Id


class Configuration(ModelSingleton, ModelSQL, ModelView):
    'Quality configuration'
    __name__ = 'lims.quality.configuration'

    sample_location = fields.Many2One('stock.location', 'Sample Location',
        domain=[('type', '=', 'storage')])
    quality_sequence = fields.Many2One('ir.sequence',
        'Quality Sequence', required=True,
        domain=[
            ('sequence_type', '=',
                Id('lims_quality_control', 'sequence_type_quality')),
            ])
