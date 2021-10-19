# This file is part of lims_diagnosis module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import party
from . import analysis
from . import html_template
from . import sample
from . import results_report
from . import notebook
from . import laboratory
from . import task
from . import industry


def register():
    Pool.register(
        party.Diagnostician,
        party.Party,
        analysis.Analysis,
        analysis.ProductType,
        html_template.DiagnosisState,
        html_template.DiagnosisStateImage,
        html_template.DiagnosisTemplate,
        html_template.DiagnosisTemplateState,
        html_template.ReportTemplate,
        sample.Fraction,
        sample.Sample,
        sample.CreateSampleStart,
        results_report.ResultsReportVersionDetail,
        results_report.ResultsReportVersionDetailSample,
        results_report.ResultsReportVersionDetailLine,
        results_report.ChangeSampleDiagnosticianStart,
        results_report.OpenSamplesComparatorAsk,
        results_report.SamplesComparator,
        results_report.SamplesComparatorLine,
        results_report.Cron,
        notebook.Notebook,
        notebook.NotebookLine,
        notebook.NotebookRepeatAnalysisStart,
        notebook.NotebookLineRepeatAnalysisStart,
        laboratory.NotebookRule,
        task.AdministrativeTaskTemplate,
        task.AdministrativeTask,
        module='lims_diagnosis', type_='model')
    Pool.register(
        industry.Plant,
        module='lims_diagnosis', type_='model', depends=['lims_industry'])
    Pool.register(
        sample.CreateSample,
        results_report.ChangeSampleDiagnostician,
        results_report.OpenSamplesComparator,
        notebook.NotebookRepeatAnalysis,
        notebook.NotebookLineRepeatAnalysis,
        module='lims_diagnosis', type_='wizard')
    Pool.register(
        results_report.ResultReport,
        module='lims_report_html', type_='report')
