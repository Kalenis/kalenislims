# -*- coding: utf-8 -*-
# This file is part of lims_interface module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import datetime
import formulas
import numpy as np
from dateutil.relativedelta import relativedelta
from decimal import Decimal
import datetime
from dateutil.relativedelta import relativedelta
import pytz

from trytond.model import ModelView, ModelSQL, fields
from trytond.pool import Pool
from trytond.transaction import Transaction

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


def trunc_float(value, digits=2):
    if not isinstance(value, (float, int)) or not isinstance(digits, int):
        return value
    pow_10 = 10 ** digits
    return (float(int(value * pow_10))) / pow_10


custom_functions['TRUNC_FLOAT'] = trunc_float


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
    res = VariableValue.get_value(variable, analysis, method)
    if res:
        return res
    res = VariableValue.get_value(variable, analysis)
    if res:
        return res
    return None


custom_functions['VAR'] = get_variable


def get_constant(name, parameter1=None, parameter2=None, parameter3=None,
        value=None):
    pool = Pool()
    Constant = pool.get('lims.interface.constant')
    if not name:
        return None
    if not value:
        value = 'value1'
    if str(parameter1) == '#VALUE!':
        parameter1 = None
    if str(parameter2) == '#VALUE!':
        parameter2 = None
    if str(parameter3) == '#VALUE!':
        parameter3 = None
    return Constant.get_constant(name, parameter1, parameter2, parameter3,
        value)


custom_functions['CONSTANT'] = get_constant


def _get_column_name(alias, iteration=None):
    if not iteration:
        return alias
    parser = formulas.Parser()
    ast = parser.ast('=%s' % str(iteration))[1].compile()
    iteration = str(ast())
    return '%s_%s' % (alias, iteration)


def get_column_value(notebook_line, alias, iteration=None):
    pool = Pool()
    Data = pool.get('lims.interface.data')

    if not notebook_line or not alias:
        return None

    if not isinstance(notebook_line, int):
        notebook_line = notebook_line.id

    compilation_id = Transaction().context.get('lims_interface_compilation')
    if not compilation_id:
        return None

    lines = Data.search([
        ('compilation', '=', compilation_id),
        ('notebook_line', '=', notebook_line),
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
        'MS': lambda x: datetime.timedelta(seconds=x/1000),
    }
    res = None
    try:
        value = float(value)
    except (ValueError, TypeError):
        value = False

    if type(value) is float and value == 0:
        res = datetime.timedelta(hours=0)
    elif not value or not type(value) is float or not uom or uom not in uoms:
        res = None
    else:
        res = _td_to_time(uoms[uom](value))

    return res


custom_functions['TOTIME'] = to_time


def float_to_delta(value, uom):
    uoms = {
        'MO': lambda x: relativedelta(months=x),
        'W': lambda x: datetime.timedelta(days=x*7),
        'D': lambda x: datetime.timedelta(days=x),
        'H': lambda x: datetime.timedelta(hours=x),
        'M': lambda x: datetime.timedelta(minutes=x),
        'S': lambda x: datetime.timedelta(seconds=x),
    }
    return uoms.get(uom, lambda x: False)(value)


def date_add(base_date, value, uom):
    res = None
    try:
        value = float(value)
    except (ValueError, TypeError):
        return None

    if not type(base_date) in [datetime.date, datetime.datetime]:
        return None
    if type(base_date) is datetime.date and uom in ['H', 'M', 'S']:
        return base_date
    # Float is not allowed for month values, because its ambiguos
    if uom == 'MO':
        value = int(value)
    delta = float_to_delta(value, uom)
    res = base_date + delta if delta else None
    return res


custom_functions['DATEADD'] = date_add


def date_diff(date_1, date_2, uom, return_delta=False):
    uoms = {
        'D': lambda x: x.days,
        'W': lambda x: round((x.days / 7), 2),
        'MO': lambda x: round((x.days / 30), 2),
        'Y': lambda x: round((x.days / 365), 2),
    }
    if not date_1 or not date_2 or date_1 < date_2:
        return None
    if not type(date_1) is datetime.date or not type(date_2) is datetime.date:
        return None
    delta_difference = date_1 - date_2
    if uom:
        if uom not in uoms:
            return None
        res = uoms[uom](delta_difference)
    if return_delta:
        res = delta_difference
    return res


custom_functions['DATEDIFF'] = date_diff


def get_date_list(dates):
    date_list = []

    def isValid(date):
        return (isinstance(date, datetime.date) or
            isinstance(date, datetime.datetime))
    try:
        date_list = [date for date in dates[0] if isValid(date)]
    except IndexError:
        return date_list
    return date_list


def max_date(dates):
    res = None
    date_list = get_date_list(dates)
    if len(date_list):
        res = max(d for d in date_list)

    return res


custom_functions['MAXDATE'] = max_date


def min_date(dates):
    res = None
    date_list = get_date_list(dates)
    if len(date_list):
        res = min(d for d in date_list)

    return res


custom_functions['MINDATE'] = min_date


def now_str():
    pool = Pool()
    Company = pool.get('company.company')

    timezone = pytz.utc

    company_id = Transaction().context.get('company')
    if company_id:
        company = Company(company_id)
        if company.timezone:
            timezone = pytz.timezone(company.timezone)
    now = datetime.datetime.now(timezone)
    return now.strftime("%d/%m/%Y %H:%M:%S")


custom_functions['NOW_STR'] = now_str


def slope(yp, xp):
    items_to_delete, i = [], 0
    for y1 in yp:
        for val in y1:
            if not isinstance(val, (int, float, Decimal)):
                items_to_delete.append(i)
            i += 1
    if items_to_delete:
        yp = np.delete(yp, items_to_delete, axis=1)
        xp = np.delete(xp, items_to_delete, axis=1)
    if any(val is None for x1 in xp for val in x1):
        return None

    return formulas.functions.wrap_func(formulas.functions.stat.xslope)(yp, xp)


custom_functions['SLOPE'] = slope


def intercept(y, x):
    items_to_delete, i = [], 0
    for y1 in y:
        for val in y1:
            if not isinstance(val, (int, float, Decimal)):
                items_to_delete.append(i)
            i += 1
    if items_to_delete:
        y = np.delete(y, items_to_delete, axis=1)
        x = np.delete(x, items_to_delete, axis=1)
    if any(val is None for x1 in x for val in x1):
        return None

    y, x = y[0].astype(float), x[0].astype(float)
    if len(y) < 2 or len(x) < 2:
        return None

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
    items_to_delete, i = [], 0
    for y1 in y:
        for val in y1:
            if not isinstance(val, (int, float, Decimal)):
                items_to_delete.append(i)
            i += 1
    if items_to_delete:
        y = np.delete(y, items_to_delete, axis=1)
        x = np.delete(x, items_to_delete, axis=1)
    if any(val is None for x1 in x for val in x1):
        return None

    y, x = y[0].astype(float), x[0].astype(float)
    if len(y) < 2 or len(x) < 2:
        return None

    zx = (x - np.mean(x)) / np.std(x, ddof=1)
    zy = (y - np.mean(y)) / np.std(y, ddof=1)
    r = np.sum(zx * zy) / (len(x) - 1)
    return r ** 2


custom_functions['RSQ'] = rsq


def scientific_notation(value, decimals=2):
    res = ''
    if not value:
        return res
    try:
        res = ("{0:.%ie}" % (decimals)).format(float(value))
    except (TypeError, ValueError):
        pass
    return res


custom_functions['SCIENTIFIC_NOTATION'] = scientific_notation


class Function(ModelSQL, ModelView):
    'Interface Function'
    __name__ = 'lims.interface.function'

    name = fields.Char('Name', required=True)
    parameters = fields.Char('Parameters')
    help = fields.Text('Help')

    def get_rec_name(self, name):
        return '%s(%s)' % (self.name, self.parameters)
