# This file is part of lims_report_html module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction


class ActionReport(metaclass=PoolMeta):
    __name__ = 'ir.action.report'

    lims_template = fields.Many2One('lims.report.template', 'Report Template',
        domain=[
            ('report_name', '=', Eval('report_name')),
            ('type', 'in', [None, 'base']),
            ],
        states={'invisible': Eval('template_extension') != 'lims'},
        depends=['report_name', 'template_extension'])

    @classmethod
    def __setup__(cls):
        super().__setup__()
        lims_option = ('lims', 'Lims Report')
        if lims_option not in cls.template_extension.selection:
            cls.template_extension.selection.append(lims_option)

    @classmethod
    def __register__(cls, module_name):
        cursor = Transaction().connection.cursor()
        table = cls.__table__()
        super().__register__(module_name)
        cursor.execute(*table.update([table.template_extension], ['lims'],
            where=(table.template_extension == 'results')))


class ReportTranslationSet(metaclass=PoolMeta):
    __name__ = 'ir.translation.set'

    def extract_report_lims(self, content):
        return []
