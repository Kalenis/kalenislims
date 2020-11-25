# This file is part of lims_quality_control module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool
from . import configuration
from . import quality
from . import product
from . import lims
from . import sample


def register():
    Pool.register(
        configuration.Configuration,
        product.Template,
        lims.Configuration,
        lims.Method,
        lims.Typification,
        lims.Analysis,
        lims.NotebookLine,
        lims.EntryDetailAnalysis,
        lims.NotebookLoadResultsManualLine,
        sample.LabWorkYear,
        sample.Sample,
        sample.TakeSampleStart,
        sample.TakeSampleResult,
        sample.CountersampleCreateStart,
        quality.QualitativeValue,
        quality.Template,
        quality.QualityTest,
        quality.CreateQualityTestStart,
        quality.TemplateAddServiceStart,
        module='lims_quality_control', type_='model')
    Pool.register(
        lims.NotebookLoadResultsManual,
        sample.TakeSample,
        sample.CountersampleCreate,
        quality.CreateQualityTest,
        quality.TemplateAddService,
        quality.TestResultsReport,
        quality.OpenTestAttachment,
        quality.PrintTest,
        module='lims_quality_control', type_='wizard')
    Pool.register(
        sample.SampleLabels,
        lims.ResultReport,
        quality.TestReport,
        quality.TestAttachmentReport,
        module='lims_quality_control', type_='report')
