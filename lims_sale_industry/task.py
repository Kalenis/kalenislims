# This file is part of lims_sale_industry module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import PoolMeta
from trytond.i18n import gettext

__all__ = ['AdministrativeTaskTemplate', 'AdministrativeTask']


class AdministrativeTaskTemplate(metaclass=PoolMeta):
    __name__ = 'lims.administrative.task.template'

    @classmethod
    def get_types(cls):
        types = super().get_types()
        types.append(('sale_purchase_order_required',
            gettext('lims_sale_industry.lbl_sale_purchase_order_required')))
        types.append(('product_quotation',
            gettext('lims_sale_industry.lbl_product_quotation')))
        return types


class AdministrativeTask(metaclass=PoolMeta):
    __name__ = 'lims.administrative.task'

    @classmethod
    def _get_origin(cls):
        origins = super()._get_origin()
        origins.extend([
            'sale.sale',
            'sale.line',
            ])
        return origins
