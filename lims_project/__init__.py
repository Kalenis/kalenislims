# This file is part of lims_project module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from .project import *


def register():
    Pool.register(
        LimsProject,
        LimsEntry,
        LimsSample,
        LimsCreateSampleStart,
        module='lims_project', type_='model')
    Pool.register(
        LimsCreateSample,
        module='lims_project', type_='wizard')
