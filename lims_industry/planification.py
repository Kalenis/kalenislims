# This file is part of lims_industry module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import PoolMeta
from .sample import WarnDangerousProduct


class TechniciansQualification(WarnDangerousProduct, metaclass=PoolMeta):
    __name__ = 'lims.planification.technicians_qualification'

    start_state = 'start'

    def transition_confirm(self):
        super().transition_confirm()
        return 'check_dangerous_products'
