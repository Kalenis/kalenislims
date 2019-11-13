# This file is part of lims_administrative_task module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import task
from . import department
from . import user
from . import configuration


def register():
    Pool.register(
        task.AdministrativeTaskTemplate,
        task.AdministrativeTask,
        task.EditAdministrativeTaskStart,
        department.Department,
        user.User,
        configuration.Configuration,
        configuration.ConfigurationSequence,
        module='lims_administrative_task', type_='model')
    Pool.register(
        task.EditAdministrativeTask,
        module='lims_administrative_task', type_='wizard')
