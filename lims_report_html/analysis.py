# This file is part of lims_report_html module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval


class Analysis(metaclass=PoolMeta):
    __name__ = 'lims.analysis'

    result_template = fields.Many2One('lims.result_report.template',
        'Report Template', domain=[('type', 'in', [None, 'base'])],
        states={'readonly': Eval('type') != 'group'},
        depends=['type'])
