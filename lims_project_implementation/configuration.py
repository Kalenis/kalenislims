# -*- coding: utf-8 -*-
# This file is part of lims_project_implementation module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta


class Configuration(metaclass=PoolMeta):
    __name__ = 'lims.configuration'

    mpi_fraction_type = fields.Many2One('lims.fraction.type',
        'MPI fraction type')
