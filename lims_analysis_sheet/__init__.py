# This file is part of lims_analysis_sheet module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import configuration
from . import interface
from . import planification
from . import notebook


def register():
    Pool.register(
        configuration.Configuration,
        configuration.ConfigurationSequence,
        interface.TemplateAnalysisSheet,
        interface.TemplateAnalysisSheetAnalysis,
        interface.AnalysisSheet,
        interface.Compilation,
        interface.Column,
        interface.Data,
        interface.ExportAnalysisSheetFileStart,
        planification.Planification,
        planification.SearchAnalysisSheetStart,
        planification.SearchAnalysisSheetNext,
        planification.RelateTechniciansStart,
        planification.RelateTechniciansResult,
        planification.RelateTechniciansDetail4,
        notebook.NotebookLine,
        notebook.AddFractionControlStart,
        notebook.RepeatAnalysisStart,
        notebook.RepeatAnalysisStartLine,
        module='lims_analysis_sheet', type_='model')
    Pool.register(
        interface.OpenAnalysisSheetData,
        interface.ExportAnalysisSheetFile,
        planification.SearchAnalysisSheet,
        planification.RelateTechnicians,
        notebook.AddFractionControl,
        notebook.RepeatAnalysis,
        notebook.InternalRelationsCalc,
        module='lims_analysis_sheet', type_='wizard')
    Pool.register(
        interface.AnalysisSheetReport,
        module='lims_analysis_sheet', type_='report')
