# This file is part of lims_board module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import board


def register():
    Pool.register(
        board.BoardGeneral,
        board.BoardGeneralSampleState,
        board.BoardGeneralSampleDepartment,
        board.BoardLaboratory,
        board.BoardLaboratorySampleLaboratoryDate,
        board.BoardLaboratorySampleReportDate,
        module='lims_board', type_='model')
