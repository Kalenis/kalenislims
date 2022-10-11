from trytond.model import fields
from trytond.pool import PoolMeta, Pool


class Configuration(metaclass=PoolMeta):
    __name__ = 'purchase.configuration'

    default_template = fields.Many2One('lims.report.template',
        'Default Template', domain=[
            ('report_name', '=', 'purchase.purchase'),
            ('type', 'in', [None, 'base']),
            ])