# This file is part of lims_analysis_sheet module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction


class EditFractionService(metaclass=PoolMeta):
    __name__ = 'lims.fraction.edit_service'

    def transition_confirm(self):
        result = super().transition_confirm()
        pool = Pool()
        Fraction = pool.get('lims.fraction')
        AnalysisSheet = pool.get('lims.analysis_sheet')
        for fraction in Fraction.browse(
                Transaction().context['active_ids']):
            AnalysisSheet.sync_fraction_after_service_change(fraction)
        return result


class EditSampleService(metaclass=PoolMeta):
    __name__ = 'lims.sample.edit_service'

    def transition_confirm(self):
        result = super().transition_confirm()
        pool = Pool()
        Sample = pool.get('lims.sample')
        AnalysisSheet = pool.get('lims.analysis_sheet')
        for sample in Sample.browse(
                Transaction().context['active_ids']):
            for fraction in sample.fractions:
                AnalysisSheet.sync_fraction_after_service_change(fraction)
        return result
