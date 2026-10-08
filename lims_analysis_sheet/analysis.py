# This file is part of lims_analysis_sheet module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.model import fields
from trytond.pool import PoolMeta


class Analysis(metaclass=PoolMeta):
    __name__ = 'lims.analysis'

    no_analysis_sheet = fields.Boolean('Does not use Analysis Sheets',
        help='Exempts the analysis from the analysis sheet template '
        'requirement of its laboratory, e.g. calculated analyzes.')

    @staticmethod
    def default_no_analysis_sheet():
        return False
