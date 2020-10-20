# This file is part of lims_email module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import configuration
from . import results_report


def register():
    Pool.register(
        configuration.Configuration,
        configuration.Cron,
        results_report.ResultsReportVersionDetail,
        results_report.ResultsReport,
        results_report.SendResultsReportStart,
        results_report.SendResultsReportSucceed,
        results_report.SendResultsReportFailed,
        module='lims_email', type_='model')
    Pool.register(
        results_report.ResultsReportAnnulation,
        results_report.SendResultsReport,
        module='lims_email', type_='wizard')
