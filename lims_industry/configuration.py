# This file is part of lims_industry module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import PoolMeta


class Configuration(metaclass=PoolMeta):
    __name__ = 'lims.configuration'

    @classmethod
    def __setup__(cls):
        super().__setup__()
        for option in [('plant', 'Plant'), ('equipment', 'Equipment')]:
            if option not in cls.mail_ack_report_grouping.selection:
                cls.mail_ack_report_grouping.selection.append(option)
