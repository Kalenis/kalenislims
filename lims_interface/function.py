# -*- coding: utf-8 -*-
# This file is part of lims_interface module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelView, ModelSQL, fields
from trytond.pool import Pool

custom_functions = {}


def to_str(value):
    return value and str(value) or ''


custom_functions['STR'] = to_str


def concat(*args):
    return ''.join([a if isinstance(a, str) else '' for a in args])


custom_functions['CONCAT'] = concat


def get_variable(notebook_line, variable):
    pool = Pool()
    NotebookLine = pool.get('lims.notebook.line')
    VariableValue = pool.get('lims.interface.variable.value')

    if not notebook_line or not variable:
        return None

    if isinstance(notebook_line, int):
        notebook_line = NotebookLine(notebook_line)

    analysis = notebook_line.analysis
    product_type = notebook_line.product_type
    matrix = notebook_line.matrix
    method = notebook_line.method

    res = VariableValue.get_value(variable, analysis, product_type, matrix,
        method)
    if res:
        return res
    res = VariableValue.get_value(variable, analysis, product_type, matrix)
    if res:
        return res
    res = VariableValue.get_value(variable, analysis, product_type)
    if res:
        return res
    res = VariableValue.get_value(variable, analysis)
    if res:
        return res
    return None


custom_functions['VAR'] = get_variable


class Function(ModelSQL, ModelView):
    'Interface Function'
    __name__ = 'lims.interface.function'

    name = fields.Char('Name', required=True)
    parameters = fields.Char('Parameters')
    help = fields.Text('Help')

    def get_rec_name(self, name):
        return '%s(%s)' % (self.name, self.parameters)
