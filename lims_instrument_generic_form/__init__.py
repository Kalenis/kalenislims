# This file is part of lims_instrument_generic_form module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from .resultsimport import *


def register():
    Pool.register(
        LimsResultsImport,
        module='lims_instrument_generic_form', type_='model')
