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
        planification.Planification,
        planification.SearchAnalysisSheetStart,
        planification.SearchAnalysisSheetNext,
        planification.RelateTechniciansStart,
        planification.RelateTechniciansResult,
        planification.RelateTechniciansDetail4,
        notebook.NotebookLine,
        module='lims_analysis_sheet', type_='model')
    Pool.register(
        interface.OpenAnalysisSheetData,
        planification.SearchAnalysisSheet,
        planification.RelateTechnicians,
        module='lims_analysis_sheet', type_='wizard')
