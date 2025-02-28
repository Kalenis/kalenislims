# This file is part of lims_planning_automatic module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelView
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction


class Fraction(metaclass=PoolMeta):
    __name__ = 'lims.fraction'

    @classmethod
    def confirm(cls, fractions):
        Planification = Pool().get('lims.planification')
        super().confirm(fractions)
        entries = set()
        for fraction in fractions:
            if fraction.entry and fraction.entry.state in (
                    'ongoing', 'finished'):
                entries.add(fraction.entry)
        if entries:
            Planification.automatic_plan(entries=list(entries))


class CompleteServices(metaclass=PoolMeta):
    __name__ = 'lims.complete_services'

    def transition_start(self):
        pool = Pool()
        Fraction = pool.get('lims.fraction')
        Planification = pool.get('lims.planification')

        super().transition_start()

        fraction = Fraction(Transaction().context['active_id'])
        entries = set()
        if fraction.entry and fraction.entry.state in (
                'ongoing', 'finished'):
            entries.add(fraction.entry)
        if entries:
            Planification.automatic_plan(entries=list(entries))
        return 'end'
