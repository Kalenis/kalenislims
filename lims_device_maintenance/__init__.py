# This file is part of lims_device_maintenance module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import maintenance
from . import task


def register():
    Pool.register(
        maintenance.LabDevice,
        maintenance.LabDeviceMaintenanceType,
        maintenance.LabDeviceMaintenanceActivity,
        maintenance.LabDeviceMaintenanceProgram,
        maintenance.LabDeviceMaintenance,
        maintenance.LabDeviceGenerateMaintenanceStart,
        maintenance.Cron,
        task.AdministrativeTaskTemplate,
        task.AdministrativeTask,
        module='lims_device_maintenance', type_='model')
    Pool.register(
        maintenance.LabDeviceGenerateMaintenance,
        module='lims_device_maintenance', type_='wizard')
