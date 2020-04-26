# This file is part of lims_diagnosis module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import party
from . import analysis
from . import sample
from . import results_report
from . import notebook
from . import laboratory


def register():
    Pool.register(
        party.Diagnostician,
        party.Party,
        analysis.Analysis,
        analysis.ProductType,
        sample.Sample,
        sample.CreateSampleStart,
        results_report.ResultsReportVersionDetail,
        notebook.NotebookLine,
        laboratory.NotebookRule,
        module='lims_diagnosis', type_='model')
    Pool.register(
        sample.CreateSample,
        module='lims_diagnosis', type_='wizard')
