# This file is part of lims_board_analysis_sheet module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import board


def register():
    Pool.register(
        board.BoardLaboratory,
        board.BoardLaboratoryTemplateAnalysisSheet,
        module='lims_board_analysis_sheet', type_='model')
