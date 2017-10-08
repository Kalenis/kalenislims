# This file is part of lims_project_water module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from .project import *
from report import *


def register():
    Pool.register(
        LimsProject,
        LimsEntry,
        LimsSample,
        LimsCreateSampleStart,
        module='lims_project_water', type_='model')
    Pool.register(
        LimsCreateSample,
        module='lims_project_water', type_='wizard')
    Pool.register(
        LimsProjectWaterSampling,
        module='lims_project_water', type_='report')
