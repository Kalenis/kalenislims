# This file is part of lims_digital_sign module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import results_report


def register():
    Pool.register(
        results_report.ResultsReportVersionDetail,
        results_report.ResultsReport,
        module='lims_digital_sign', type_='model')
    Pool.register(
        results_report.ResultsReportAnnulation,
        module='lims_digital_sign', type_='wizard')
