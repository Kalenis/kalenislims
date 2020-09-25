# This file is part of lims_planning_automatic module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool, PoolMeta
from trytond.exceptions import UserError
from trytond.i18n import gettext


class AnalysisSheet(metaclass=PoolMeta):
    __name__ = 'lims.analysis_sheet'

    @classmethod
    def activate(cls, sheets):
        LaboratoryProfessional = Pool().get('lims.laboratory.professional')

        super().activate(sheets)
        professional_id = LaboratoryProfessional.get_lab_professional()
        if not professional_id:
            raise UserError(gettext('lims_rack.msg_user_no_professional'))

        for s in sheets:
            s.professional = professional_id
            s.save()
