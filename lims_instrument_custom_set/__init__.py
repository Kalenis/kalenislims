# This file is part of lims_instrument_custom_set module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import resultsimport


def register():
    Pool.register(
        resultsimport.ResultsImport,
        module='lims_instrument_custom_set', type_='model')
