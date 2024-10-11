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

    def process_new_services(self, services):
        Planification = Pool().get('lims.planification')
        entries = set()
        for service in services:
            entries.add(service.entry)
        if entries:
            Planification.automatic_plan(entries=list(entries))


class AddSampleService(metaclass=PoolMeta):
    __name__ = 'lims.sample.add_service'

    def process_new_services(self, services):
        Planification = Pool().get('lims.planification')
        entries = set()
        for service in services:
            if service.entry and service.entry.state in (
                    'ongoing', 'finished'):
                entries.add(service.entry)
        if entries:
            Planification.automatic_plan(entries=list(entries))


class EditSampleService(metaclass=PoolMeta):
    __name__ = 'lims.sample.edit_service'

    def process_new_services(self, services):
        Planification = Pool().get('lims.planification')
        entries = set()
        for service in services:
            if service.entry and service.entry.state in (
                    'ongoing', 'finished'):
                entries.add(service.entry)
        if entries:
            Planification.automatic_plan(entries=list(entries))
