# This file is part of lims_report_html module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import PoolMeta

__all__ = ['ActionReport', 'ReportTranslationSet']


class ActionReport(metaclass=PoolMeta):
    __name__ = 'ir.action.report'

    @classmethod
    def __setup__(cls):
        super().__setup__()
        results_option = ('results', 'Results Report')
        if results_option not in cls.template_extension.selection:
            cls.template_extension.selection.append(results_option)


class ReportTranslationSet(metaclass=PoolMeta):
    __name__ = 'ir.translation.set'

    def extract_report_results(self, content):
        return []
