# This file is part of lims_industry module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import industry
from . import sample
from . import party
from . import task


def register():
    Pool.register(
        industry.Plant,
        industry.EquipmentType,
        industry.Brand,
        industry.ComponentType,
        industry.EquipmentTemplate,
        industry.EquipmentTemplateComponentType,
        industry.Equipment,
        industry.Component,
        sample.Entry,
        sample.Sample,
        party.Party,
        party.Address,
        task.AdministrativeTaskTemplate,
        task.AdministrativeTask,
        module='lims_industry', type_='model')
