# This file is part of lims_administrative_task module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta, Pool

__all__ = ['Component', 'Equipment']


class Component(metaclass=PoolMeta):
    __name__ = 'lims.component'

    missing_data = fields.Boolean('Missing data')

    @classmethod
    def create(cls, vlist):
        TaskTemplate = Pool().get('lims.administrative.task.template')
        components = super(Component, cls).create(vlist)
        records = cls.check_for_tasks(components)
        TaskTemplate.create_tasks(cls.__name__, records)
        return components

    @classmethod
    def check_for_tasks(cls, components):
        AdministrativeTask = Pool().get('lims.administrative.task')
        res = []
        for component in components:
            if not component.missing_data:
                continue
            if AdministrativeTask.search([
                    ('origin', '=', '%s,%s' % (cls.__name__, component.id)),
                    ('state', 'not in', ('done', 'discarded')),
                    ]):
                continue
            res.append(component)
        return res


class Equipment(metaclass=PoolMeta):
    __name__ = 'lims.equipment'

    @classmethod
    def create(cls, vlist):
        TaskTemplate = Pool().get('lims.administrative.task.template')
        equipments = super(Equipment, cls).create(vlist)
        records = cls.check_for_tasks(equipments)
        TaskTemplate.create_tasks(cls.__name__, records)
        return equipments

    @classmethod
    def check_for_tasks(cls, equipments):
        AdministrativeTask = Pool().get('lims.administrative.task')
        res = []
        for equipment in equipments:
            if not equipment.missing_data:
                continue
            if AdministrativeTask.search([
                    ('origin', '=', '%s,%s' % (cls.__name__, equipment.id)),
                    ('state', 'not in', ('done', 'discarded')),
                    ]):
                continue
            res.append(equipment)
        return res
