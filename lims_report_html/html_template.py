# This file is part of lims_report_html module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelSQL, ModelView, fields

__all__ = ['ReportTemplate']


class ReportTemplate(ModelSQL, ModelView):
    'Results Report Template'
    __name__ = 'lims.result_report.template'

    name = fields.Char('Name', required=True)
    content = fields.Text('Content', required=True)
