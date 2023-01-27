# This file is part of lims_planning_automatic module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import planification
from . import laboratory
from . import entry
from . import sheet
from . import quality
from . import sample
from . import notebook


def register():
    Pool.register(
        planification.Planification,
        laboratory.Laboratory,
        laboratory.NotebookRule,
        entry.Entry,
        sample.Sample,
        module='lims_planning_automatic', type_='model')
    Pool.register(
        sheet.AnalysisSheet,
        module='lims_planning_automatic', type_='model',
        depends=['lims_analysis_sheet'])
    Pool.register(
        quality.QualityTest,
        module='lims_planning_automatic', type_='model',
        depends=['lims_quality_control'])
    Pool.register(
        entry.ManageServices,
        entry.AddSampleService,
        entry.EditSampleService,
        notebook.NotebookRepeatAnalysis,
        notebook.NotebookLineRepeatAnalysis,
        module='lims_planning_automatic', type_='wizard')
