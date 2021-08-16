# This file is part of lims_planning_automatic module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool, PoolMeta


class Entry(metaclass=PoolMeta):
    __name__ = 'lims.entry'

    @classmethod
    def confirm(cls, entries):
        Planification = Pool().get('lims.planification')
        super().confirm(entries)
        Planification.automatic_plan(entries=entries)


class ManageServices(metaclass=PoolMeta):
    __name__ = 'lims.manage_services'

    def create_service(self, service, fraction):
        Planification = Pool().get('lims.planification')
        new_service = super().create_service(service, fraction)
        Planification.automatic_plan(entries=[new_service.entry])
        return new_service


class AddSampleService(metaclass=PoolMeta):
    __name__ = 'lims.sample.add_service'

    def create_service(self, service, fraction):
        Planification = Pool().get('lims.planification')
        new_service = super().create_service(service, fraction)
        Planification.automatic_plan(entries=[new_service.entry])
        return new_service

class EditSampleService(metaclass=PoolMeta):
    __name__ = 'lims.sample.edit_service'

    def create_service(self, service, fraction):
        Planification = Pool().get('lims.planification')
        new_service = super().create_service(service, fraction)
        Planification.automatic_plan(entries=[new_service.entry])
        return new_service
