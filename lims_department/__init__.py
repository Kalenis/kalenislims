# This file is part of lims_department module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from .lims import *
from .production import *


def register():
    Pool.register(
        Department,
        User,
        UserDepartment,
        Production,
        module='lims_department', type_='model')
