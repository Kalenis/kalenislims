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


def register():
    Pool.register(
        party.Diagnostician,
        party.Party,
        analysis.Analysis,
        analysis.ProductType,
        html_template.DiagnosisState,
        html_template.DiagnosisTemplate,
        html_template.DiagnosisTemplateState,
        html_template.ReportTemplate,
        sample.Sample,
        sample.CreateSampleStart,
        results_report.ResultsReportVersionDetail,
        results_report.ResultsReportVersionDetailSample,
        results_report.ResultsReportVersionDetailLine,
        results_report.ChangeSampleDiagnosticianStart,
        notebook.Notebook,
        notebook.NotebookLine,
        notebook.NotebookLineRepeatAnalysisStart,
        laboratory.NotebookRule,
        task.AdministrativeTaskTemplate,
        task.AdministrativeTask,
        module='lims_diagnosis', type_='model')
    Pool.register(
        sample.CreateSample,
        results_report.ChangeSampleDiagnostician,
        notebook.NotebookLineRepeatAnalysis,
        module='lims_diagnosis', type_='wizard')
