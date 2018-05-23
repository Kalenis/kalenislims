# This file is part of lims_instrument module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import resultsimport


def register():
    Pool.register(
        resultsimport.NotebookLine,
        resultsimport.ResultsImport,
        resultsimport.NotebookLoadResultsFileStart,
        resultsimport.NotebookLoadResultsFileStartLine,
        resultsimport.NotebookLoadResultsFileEmpty,
        resultsimport.NotebookLoadResultsFileResult,
        resultsimport.NotebookLoadResultsFileWarning,
        resultsimport.NotebookLoadResultsFileExport,
        module='lims_instrument', type_='model')
    Pool.register(
        resultsimport.NotebookLoadResultsFile,
        module='lims_instrument', type_='wizard')
