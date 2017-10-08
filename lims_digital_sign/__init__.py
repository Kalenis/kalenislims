# This file is part of lims_digital_sign module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from .configuration import *
from .lims import *
from wizard import *


def register():
    Pool.register(
        LimsConfiguration,
        LimsResultsReportVersionDetail,
        LimsResultsReport,
        DigitalSignStart,
        DigitalSignSucceed,
        DigitalSignFailed,
        module='lims_digital_sign', type_='model')
    Pool.register(
        LimsResultsReportAnnulation,
        DigitalSign,
        module='lims_digital_sign', type_='wizard')
