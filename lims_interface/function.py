# -*- coding: utf-8 -*-
# This file is part of lims_interface module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import formulas
import numpy as np

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


def intercept(y, x):
    if any(val is None for y1 in y for val in y1):
        return None
    if any(val is None for x1 in x for val in x1):
        return None
    y, x = y[0].astype(float), x[0].astype(float)

    def _mean(l):
        return sum(l) / len(l)

    def _multiply(l1, l2):
        return [a * b for a, b in zip(l1, l2)]

    m = ((_mean(x) * _mean(y) - _mean(_multiply(x, y))) /
        (_mean(x) ** 2 - _mean(_multiply(x, x))))
    b = _mean(y) - m * _mean(x)
    return b


custom_functions['INTERCEPT'] = intercept


def rsq(y, x):
    if any(val is None for y1 in y for val in y1):
        return None
    if any(val is None for x1 in x for val in x1):
        return None
    y, x = y[0].astype(float), x[0].astype(float)
    zx = (x - np.mean(x)) / np.std(x, ddof=1)
    zy = (y - np.mean(y)) / np.std(y, ddof=1)
    r = np.sum(zx * zy) / (len(x) - 1)
    return r ** 2


custom_functions['RSQ'] = rsq


class Function(ModelSQL, ModelView):
    'Interface Function'
    __name__ = 'lims.interface.function'

    name = fields.Char('Name', required=True)
    parameters = fields.Char('Parameters')
    help = fields.Text('Help')

    def get_rec_name(self, name):
        return '%s(%s)' % (self.name, self.parameters)
