# This file is part of lims_planning_automatic module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction


class Entry(metaclass=PoolMeta):
    __name__ = 'lims.entry'

    @classmethod
    def confirm(cls, entries):
        pool = Pool()
        Planification = pool.get('lims.planification')

        super().confirm(entries)
        Planification.automatic_plan(entries=entries)


class ManageServices(metaclass=PoolMeta):
    __name__ = 'lims.manage_services'

    def process_new_services(self, services):
        pool = Pool()
        Planification = pool.get('lims.planification')

        entries = set()
        for service in services:
            entries.add(service.entry)
        if entries:
            with Transaction().set_context(within_an_entry=True):
                Planification.automatic_plan(entries=list(entries))


class AddSampleService(metaclass=PoolMeta):
    __name__ = 'lims.sample.add_service'

    def process_new_services(self, services):
        pool = Pool()
        Planification = pool.get('lims.planification')

        entries = set()
        for service in services:
            if service.entry and service.entry.state in (
                    'ongoing', 'finished'):
                entries.add(service.entry)
        if entries:
            with Transaction().set_context(within_an_entry=True):
                Planification.automatic_plan(entries=list(entries))


class EditSampleService(metaclass=PoolMeta):
    __name__ = 'lims.sample.edit_service'

    def process_new_services(self, services):
        pool = Pool()
        Planification = pool.get('lims.planification')

        entries = set()
        for service in services:
            if service.entry and service.entry.state in (
                    'ongoing', 'finished'):
                entries.add(service.entry)
        if entries:
            with Transaction().set_context(within_an_entry=True):
                Planification.automatic_plan(entries=list(entries))
