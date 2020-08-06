# This file is part of lims_planning_automatic module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool, PoolMeta


class QualityTest(metaclass=PoolMeta):
    __name__ = 'lims.quality.test'

    @classmethod
    def confirm(cls, tests):
        Planification = Pool().get('lims.planification')
        super().confirm(tests)
        Planification.automatic_plan(tests=tests)
