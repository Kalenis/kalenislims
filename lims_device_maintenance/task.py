# This file is part of lims_device_maintenance module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import PoolMeta
from trytond.i18n import gettext

__all__ = ['AdministrativeTaskTemplate', 'AdministrativeTask']


class AdministrativeTaskTemplate(metaclass=PoolMeta):
    __name__ = 'lims.administrative.task.template'

    @classmethod
    def get_types(cls):
        types = super(AdministrativeTaskTemplate, cls).get_types()
        types.append(('device_maintenance',
            gettext('lims_device_maintenance.lbl_device_maintenance')))
        return types


class AdministrativeTask(metaclass=PoolMeta):
    __name__ = 'lims.administrative.task'

    @classmethod
    def _get_origin(cls):
        origins = super(AdministrativeTask, cls)._get_origin()
        origins.append('lims.lab.device.maintenance')
        return origins
