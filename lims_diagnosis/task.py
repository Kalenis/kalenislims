# This file is part of lims_diagnosis module for Tryton.
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
        types.append(('line_acceptance',
            gettext('lims_diagnosis.lbl_line_acceptance')))
        return types


class AdministrativeTask(metaclass=PoolMeta):
    __name__ = 'lims.administrative.task'

    @classmethod
    def _get_origin(cls):
        origins = super()._get_origin()
        origins.append('lims.notebook.line')
        return origins
