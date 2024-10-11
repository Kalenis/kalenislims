# This file is part of lims_planning_automatic module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelView
from trytond.pool import Pool, PoolMeta


class Sample(metaclass=PoolMeta):
    __name__ = 'lims.sample'

    @classmethod
    @ModelView.button
    def confirm(cls, samples):
        Planification = Pool().get('lims.planification')
        super().confirm(samples)
        entries = set()
        for sample in samples:
            if sample.entry and sample.entry.state in (
                    'ongoing', 'finished'):
                entries.add(sample.entry)
        if entries:
            Planification.automatic_plan(entries=list(entries))
