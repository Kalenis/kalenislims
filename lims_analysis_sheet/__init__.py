# This file is part of lims_analysis_sheet module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import configuration
from . import sheet
from . import interface
from . import planification
from . import notebook
from . import laboratory


def register():
    Pool.register(
        configuration.Configuration,
        configuration.ConfigurationSequence,
        sheet.TemplateAnalysisSheet,
        sheet.TemplateAnalysisSheetAnalysis,
        sheet.TemplateAnalysisSheetAnalysisExpression,
        sheet.AnalysisSheet,
        sheet.PrintAnalysisSheetReportAsk,
        sheet.ExportAnalysisSheetFileStart,
        sheet.ImportAnalysisSheetFileStart,
        interface.Compilation,
        interface.Column,
        interface.Interface,
        interface.Table,
        interface.Data,
        planification.Planification,
        planification.SearchAnalysisSheetStart,
        planification.SearchAnalysisSheetNext,
        planification.RelateTechniciansStart,
        planification.RelateTechniciansResult,
        planification.RelateTechniciansDetail4,
        planification.LaboratoryProfessional,
        planification.PlanificationProfessional,
        planification.PlanificationProfessionalContext,
        planification.PlanificationProfessionalLine,
        planification.SamplesPendingPlanning,
        planification.SamplesPendingPlanningContext,
        notebook.NotebookLine,
        notebook.AddControlStart,
        notebook.RepeatAnalysisStart,
        notebook.RepeatAnalysisStartLine,
        notebook.ResultsVerificationStart,
        notebook.EditGroupedDataStart,
        notebook.EditMultiSampleDataStart,
        notebook.MultiSampleData,
        laboratory.NotebookRule,
        laboratory.NotebookRuleCondition,
        module='lims_analysis_sheet', type_='model')
    Pool.register(
        sheet.OpenAnalysisSheetData,
        sheet.ExportAnalysisSheetFile,
        sheet.PrintAnalysisSheetReport,
        sheet.ImportAnalysisSheetFile,
        sheet.OpenAnalysisSheetSample,
        planification.SearchAnalysisSheet,
        planification.RelateTechnicians,
        planification.OpenSheetSample,
        planification.OpenPendingPlanningSample,
        notebook.AddControl,
        notebook.RepeatAnalysis,
        notebook.CalculateExpressions,
        notebook.ResultsVerification,
        notebook.LimitsValidation,
        notebook.EvaluateRules,
        notebook.EditGroupedData,
        notebook.EditMultiSampleData,
        module='lims_analysis_sheet', type_='wizard')
    Pool.register(
        sheet.AnalysisSheetReport,
        module='lims_analysis_sheet', type_='report')
