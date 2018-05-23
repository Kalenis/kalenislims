# This file is part of lims_digital_sign module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import configuration
from . import lims
from . import digital_sign


def register():
    Pool.register(
        configuration.Configuration,
        lims.ResultsReportVersionDetail,
        lims.ResultsReport,
        digital_sign.DigitalSignStart,
        digital_sign.DigitalSignSucceed,
        digital_sign.DigitalSignFailed,
        module='lims_digital_sign', type_='model')
    Pool.register(
        lims.ResultsReportAnnulation,
        digital_sign.DigitalSign,
        module='lims_digital_sign', type_='wizard')
