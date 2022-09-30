# This file is part of lims_purchase_html module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import html_template
from . import purchase


def register():
    Pool.register(
        html_template.PurchaseClauseTemplate,
        html_template.PurchaseReportTemplate,
        purchase.Purchase,
        purchase.PurchaseSection,
        module='lims_purchase_html', type_='model')
    Pool.register(
        purchase.PurchaseReport,
        module='lims_purchase_html', type_='report')
