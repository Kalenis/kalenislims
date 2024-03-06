# This file is part of lims_email module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import configuration
from . import party
from . import results_report


def register():
    Pool.register(
        configuration.Configuration,
        configuration.Cron,
        results_report.ResultsReportVersionDetail,
        results_report.RelateMailAttachmentResultsReportStart,
        results_report.ResultsReport,
        results_report.ResultsReportAttachment,
        results_report.ResultsReportMailing,
        results_report.SendResultsReportStart,
        results_report.SendResultsReportSucceed,
        results_report.SendResultsReportFailed,
        results_report.MarkResultsReportSentStart,
        results_report.ReportNameFormat,
        party.Party,
        module='lims_email', type_='model')
    Pool.register(
        results_report.RelateMailAttachmentResultsReport,
        results_report.ResultsReportAnnulation,
        results_report.SendResultsReport,
        results_report.MarkResultsReportSent,
        module='lims_email', type_='wizard')
