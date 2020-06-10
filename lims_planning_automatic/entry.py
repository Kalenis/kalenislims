# This file is part of lims_planning_automatic module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool, PoolMeta

__all__ = ['Entry']


class Entry(metaclass=PoolMeta):
    __name__ = 'lims.entry'

    @classmethod
    def confirm(cls, entries):
        Planification = Pool().get('lims.planification')
        super(Entry, cls).confirm(entries)
        Planification.automatic_plan(entries=entries)
