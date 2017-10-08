# This file is part of lims_instrument module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from .resultsimport import *
from wizard import *


def register():
    Pool.register(
        LimsNotebookLine,
        LimsResultsImport,
        LimsNotebookLoadResultsFileStart,
        LimsNotebookLoadResultsFileStartLine,
        LimsNotebookLoadResultsFileEmpty,
        LimsNotebookLoadResultsFileResult,
        LimsNotebookLoadResultsFileWarning,
        LimsNotebookLoadResultsFileExport,
        module='lims_instrument', type_='model')
    Pool.register(
        LimsNotebookLoadResultsFile,
        module='lims_instrument', type_='wizard')
