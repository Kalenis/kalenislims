# This file is part of lims_project_interlaboratory module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from .project import *


def register():
    Pool.register(
        LimsProject,
        LimsEntry,
        module='lims_project_interlaboratory', type_='model')
