# This file is part of lims_report_html module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import action
from . import html_template
from . import sample
from . import results_report


def register():
    Pool.register(
        action.ActionReport,
        html_template.ReportTemplate,
        html_template.ReportTemplateTranslation,
        sample.Sample,
        sample.CreateSampleStart,
        results_report.ResultsReportVersionDetail,
        module='lims_report_html', type_='model')
    Pool.register(
        action.ReportTranslationSet,
        sample.CreateSample,
        module='lims_report_html', type_='wizard')
    Pool.register(
        results_report.ResultReport,
        module='lims_report_html', type_='report')
