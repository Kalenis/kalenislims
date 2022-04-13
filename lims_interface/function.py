# -*- coding: utf-8 -*-
# This file is part of lims_interface module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import formulas
import numpy as np

from trytond.model import ModelView, ModelSQL, fields
from trytond.pool import Pool
from trytond.transaction import Transaction
import datetime

custom_functions = {}


def dummy_iter(alias, iteration=None):
    return alias


custom_functions['ITER'] = dummy_iter


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


def _td_to_time(td_value):
    hours, remainder = divmod(td_value.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return datetime.time(hours, minutes, seconds)


def time_diff(time_1, time_2, uom=False, return_delta=False):
    uoms = {
        'H': lambda x: x.seconds / 3600,
        'M': lambda x: x.seconds / 60,
        'S': lambda x: x.seconds,
        'MS': lambda x: x.seconds * 1000,
    }
    if not time_1 or not time_2 or time_1 < time_2:
        return None
    datetime1 = datetime.datetime.combine(datetime.date.today(), time_1)
    datetime2 = datetime.datetime.combine(datetime.date.today(), time_2)
    delta_difference = datetime1 - datetime2
    if uom:
        if uom not in uoms:
            return None
        return uoms[uom](delta_difference)
    if return_delta:
        return delta_difference
    return _td_to_time(delta_difference)


custom_functions['TIMEDIF'] = time_diff


def to_time(value, uom):
    uoms = {
        'H': lambda x: datetime.timedelta(hours=x),
        'M': lambda x: datetime.timedelta(minutes=x),
        'S': lambda x: datetime.timedelta(seconds=x),
        'MS': lambda x: datetime.timedelta(seconds=x / 1000),
    }
    if value == 0:
        return 0
    if not value or not uom or uom not in uoms:
        return None

    td = uoms[uom](value)
    return _td_to_time(td)


custom_functions['TOTIME'] = to_time


def slope(yp, xp):
    items_to_delete = []
    i = 0
    for y1 in yp:
        for y2 in y1:
            if y2 is None:
                items_to_delete.append(i)
            i += 1
    if items_to_delete:
        yp = np.delete(yp, items_to_delete, axis=1)
        xp = np.delete(xp, items_to_delete, axis=1)
    return formulas.functions.wrap_func(formulas.functions.stat.xslope)(yp, xp)


custom_functions['SLOPE'] = slope


class Function(ModelSQL, ModelView):
    'Interface Function'
    __name__ = 'lims.interface.function'

    name = fields.Char('Name', required=True)
    parameters = fields.Char('Parameters')
    help = fields.Text('Help')

    def get_rec_name(self, name):
        return '%s(%s)' % (self.name, self.parameters)
