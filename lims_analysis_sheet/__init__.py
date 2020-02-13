# This file is part of lims_analysis_sheet module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import configuration
from . import interface


def register():
    Pool.register(
        configuration.Configuration,
        configuration.ConfigurationSequence,
        interface.TemplateAnalysisSheet,
        interface.TemplateAnalysisSheetAnalysis,
        interface.AnalysisSheet,
        module='lims_analysis_sheet', type_='model')
    Pool.register(
        interface.OpenAnalysisSheetData,
        module='lims_analysis_sheet', type_='wizard')
