# -*- coding: utf-8 -*-
# This file is part of lims_quality_control module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool

custom_functions = {}


def get_qualitative_value_id(analysis, value):
    QualitativeValue = Pool().get('lims.quality.qualitative.value')
    if analysis and value:
        values = QualitativeValue.search([
            ('name', '=', value),
            ('analysis.code', '=', analysis[:analysis.find(' - ')]),
            ])
        if values:
            return values[0].id
    return None


custom_functions['QV'] = get_qualitative_value_id
