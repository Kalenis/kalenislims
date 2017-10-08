# This file is part of lims_project_tas module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from .project import *
from .configuration import *


def register():
    Pool.register(
        LimsTasType,
        LimsProject,
        LimsEntry,
        LimsLabWorkYear,
        LimsLabWorkYearSequence,
        module='lims_project_tas', type_='model')
