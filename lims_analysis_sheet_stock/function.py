# -*- coding: utf-8 -*-
# This file is part of lims_analysis_sheet_stock module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from trytond.transaction import Transaction

custom_functions = {}


def get_m2o_field(m2o_field, m2o_name, field_name, dict_key=None):
    pool = Pool()
    Field = pool.get('lims.interface.table.field')

    if not m2o_field or not m2o_name or not field_name:
        return None

    if isinstance(m2o_field, int):
        table_id = Transaction().context.get('lims_interface_table')
        column = Field.search([
            ('table', '=', table_id),
            ('name', '=', m2o_name),
            ('related_model', '!=', None),
            ])
        if not column:
            return None
        Target = Pool().get(column[0].related_model.model)
        m2o_field = Target(m2o_field)

    if not hasattr(m2o_field, field_name):
        return None

    value = getattr(m2o_field, field_name, None)
    if isinstance(value, dict):
        if not dict_key or dict_key not in value:
            return None
        value = value[dict_key]
    return value


custom_functions['M2O'] = get_m2o_field
