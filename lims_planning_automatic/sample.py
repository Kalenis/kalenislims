# This file is part of lims_diagnosis module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields, ModelView
from trytond.pool import Pool, PoolMeta

class Sample(metaclass=PoolMeta):
    __name__ = 'lims.sample'

    @classmethod
    @ModelView.button
    def confirm(cls, samples):
        Planification = Pool().get('lims.planification')
        super().confirm(samples)
        for sample in samples:
            if sample.entry and sample.entry.state == 'ongoing':
                Planification.automatic_plan(entries=[sample.entry])
