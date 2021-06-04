# -*- coding: utf-8 -*-
# This file is part of lims_interface module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import formulas

from trytond.model import ModelView, ModelSQL, fields
from trytond.pool import Pool
from trytond.transaction import Transaction

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


def _get_column_name(alias, iteration=None):
    if not iteration:
        return alias
    parser = formulas.Parser()
    ast = parser.ast('=%s' % str(iteration))[1].compile()
    iteration = str(ast())
    return '%s_%s' % (alias, iteration)


def get_column_value(notebook_line, alias, iteration=None):
    pool = Pool()
    NotebookLine = pool.get('lims.notebook.line')
    Data = pool.get('lims.interface.data')

    if not notebook_line or not alias:
        return None

    if isinstance(notebook_line, int):
        notebook_line = NotebookLine(notebook_line)

    compilation_id = Transaction().context.get('lims_interface_compilation')
    if not compilation_id:
        return None

    lines = Data.search([
        ('compilation', '=', compilation_id),
        ('notebook_line', '=', notebook_line.id),
        ], limit=1)
    target_line = lines and lines[0] or None
    if not target_line:
        return None

    target_field = _get_column_name(alias, iteration)
    if not hasattr(target_line, target_field):
        return None

    return getattr(target_line, target_field)


custom_functions['V'] = get_column_value


class Function(ModelSQL, ModelView):
    'Interface Function'
    __name__ = 'lims.interface.function'

    name = fields.Char('Name', required=True)
    parameters = fields.Char('Parameters')
    help = fields.Text('Help')

    def get_rec_name(self, name):
        return '%s(%s)' % (self.name, self.parameters)
