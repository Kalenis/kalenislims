# -*- coding: utf-8 -*-
# This file is part of lims_analysis_sheet module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import formulas
import schedula
from itertools import chain
from decimal import Decimal

from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.modules.lims_interface.data import ALLOWED_RESULT_TYPES

custom_functions = {}


def device_correction(device_id, value):
    pool = Pool()
    LabDevice = pool.get('lims.lab.device')
    if device_id and value:
        device = LabDevice(device_id)
        if device:
            return device.get_correction(value)
    return value


custom_functions['DEVICE_CORRECTION'] = device_correction


def get_device_constant(device_id, name, value=None):
    pool = Pool()
    LabDevice = pool.get('lims.lab.device')
    if not device_id or not name:
        return None
    if not value:
        value = 'value1'
    device = LabDevice(device_id)
    return device.get_constant(name, value)


custom_functions['DEVICE_CONSTANT'] = get_device_constant


def _get_result_column(table_id=None):
    pool = Pool()
    Field = pool.get('lims.interface.table.field')

    if not table_id:
        table_id = Transaction().context.get('lims_interface_table')
    if not table_id:
        return None

    result_column = Field.search([
        ('table', '=', table_id),
        ('transfer_field', '=', True),
        ('related_line_field.name', '=', 'result'),
        ])
    if not result_column:
        return None
    return result_column[0].name


def get_analysis(analysis_code, alias=None):
    pool = Pool()
    Data = pool.get('lims.interface.data')

    compilation_id = Transaction().context.get('lims_interface_compilation')
    if not compilation_id:
        return None

    notebook_id = Transaction().context.get('lims_analysis_notebook')
    if not notebook_id:
        return None

    lines = Data.search([
        ('compilation', '=', compilation_id),
        ('notebook_line.notebook.id', '=', notebook_id),
        ('notebook_line.analysis.code', '=', analysis_code),
        ('annulled', '=', False),
        ], limit=1)
    target_line = lines and lines[0] or None
    if not target_line:
        return None

    target_field = alias or _get_result_column()
    if not hasattr(target_line, target_field):
        return None

    return getattr(target_line, target_field)


custom_functions['A'] = get_analysis


def get_nline_analysis(analysis_code, alias=None, notebook_line=None,
        method_code=None):
    pool = Pool()
    NotebookLine = pool.get('lims.notebook.line')

    notebook_id = Transaction().context.get('lims_analysis_notebook')
    if not notebook_id:
        if not notebook_line:
            return None
        if isinstance(notebook_line, int):
            notebook_line = NotebookLine(notebook_line)
        notebook_id = notebook_line.notebook.id

    variables = Transaction().context.get('lims_analysis_variables', {})

    target_line = None
    if analysis_code in variables:
        selected_lines = NotebookLine.search([
            ('notebook', '=', notebook_id),
            ('analysis.code', '=', analysis_code),
            ('repetition', '=', variables[analysis_code]),
            ])
        for selected_line in selected_lines:
            if not method_code:
                target_line = selected_line
                break
            if method_code == selected_line.method.code.replace(' ', ''):
                target_line = selected_line
                break
    else:
        accepted_lines = NotebookLine.search([
            ('notebook', '=', notebook_id),
            ('analysis.code', '=', analysis_code),
            ('accepted', '=', True),
            ])
        for accepted_line in accepted_lines:
            if not method_code:
                target_line = accepted_line
                break
            if method_code == accepted_line.method.code.replace(' ', ''):
                target_line = accepted_line
                break

        if not target_line:
            last_repetition_lines = NotebookLine.search([
                ('notebook', '=', notebook_id),
                ('analysis.code', '=', analysis_code),
                ('annulled', '=', False),
                ], order=[('repetition', 'DESC')])
            for last_repetition_line in last_repetition_lines:
                if not method_code:
                    target_line = last_repetition_line
                    break
                if method_code == last_repetition_line.method.code.replace(
                        ' ', ''):
                    target_line = last_repetition_line
                    break

    if not target_line:
        return None

    alias = alias or 'result'
    if not hasattr(target_line, alias):
        return None

    return getattr(target_line, alias)


custom_functions['NL'] = get_nline_analysis


def get_sheet_analysis(analysis_code, alias=None, notebook_line=None,
        method_code=None):
    pool = Pool()
    NotebookLine = pool.get('lims.notebook.line')
    AnalysisSheet = pool.get('lims.analysis_sheet')
    Data = pool.get('lims.interface.data')

    notebook_id = Transaction().context.get('lims_analysis_notebook')
    if not notebook_id:
        if not notebook_line:
            return None
        if isinstance(notebook_line, int):
            notebook_line = NotebookLine(notebook_line)
        notebook_id = notebook_line.notebook.id

    nline = None
    accepted_lines = NotebookLine.search([
        ('notebook', '=', notebook_id),
        ('analysis.code', '=', analysis_code),
        ('accepted', '=', True),
        ])
    for accepted_line in accepted_lines:
        if not method_code:
            nline = accepted_line
            break
        if method_code == accepted_line.method.code.replace(' ', ''):
            nline = accepted_line
            break

    if not nline:
        last_repetition_lines = NotebookLine.search([
            ('notebook', '=', notebook_id),
            ('analysis.code', '=', analysis_code),
            ('annulled', '=', False),
            ], order=[('repetition', 'DESC')])
        for last_repetition_line in last_repetition_lines:
            if not method_code:
                nline = last_repetition_line
                break
            if method_code == last_repetition_line.method.code.replace(
                    ' ', ''):
                nline = last_repetition_line
                break

    if not nline:
        return None

    if nline.analysis_sheet:
        sheets = [nline.analysis_sheet]
    else:
        template_id = nline.get_analysis_sheet_template()
        if not template_id:
            return None
        sheets = AnalysisSheet.search([
            ('template', '=', template_id),
            ('state', 'in', ['draft', 'active', 'validated'])
            ], order=[('id', 'DESC')])
    for s in sheets:
        with Transaction().set_context(
                lims_interface_table=s.compilation.table.id):
            lines = Data.search([
                ('compilation', '=', s.compilation.id),
                ('notebook_line', '=', nline.id),
                ], limit=1)
            target_line = lines and lines[0] or None
            if not target_line:
                continue

            target_field = alias or _get_result_column(
                s.compilation.table.id)
            if not hasattr(target_line, target_field):
                return None

            return getattr(target_line, target_field)

    return None


custom_functions['XS_A'] = get_sheet_analysis


def get_nline_relation(analysis_code, notebook_line=None, round_=True):
    pool = Pool()
    NotebookLine = pool.get('lims.notebook.line')

    notebook_id = Transaction().context.get('lims_analysis_notebook')
    if not notebook_id:
        if not notebook_line:
            return None
        if isinstance(notebook_line, int):
            notebook_line = NotebookLine(notebook_line)
        notebook_id = notebook_line.notebook.id

    target_line = None
    accepted_line = NotebookLine.search([
        ('notebook', '=', notebook_id),
        ('analysis.code', '=', analysis_code),
        ('accepted', '=', True),
        ])
    if accepted_line:
        target_line = accepted_line[0]
    else:
        last_repetition_line = NotebookLine.search([
            ('notebook', '=', notebook_id),
            ('analysis.code', '=', analysis_code),
            ('annulled', '=', False),
            ], order=[('repetition', 'DESC')], limit=1)
        if last_repetition_line:
            target_line = last_repetition_line[0]

    if not target_line:
        return None

    formula = target_line.analysis.result_formula
    if not formula:
        return None

    if not formula.startswith('='):
        formula = '=' + formula

    parser = formulas.Parser()
    with Transaction().set_context(
            lims_analysis_notebook=target_line.notebook.id):
        try:
            ast = parser.ast(formula)[1].compile()
        except Exception as e:
            return None

        inputs = []
        try:
            value = ast(*inputs)
        except schedula.utils.exc.DispatcherError as e:
            raise UserError(e.args[0] % e.args[1:])

        if value == '':
            value = None
        if isinstance(value, list):
            value = str(value)
        elif not isinstance(value, ALLOWED_RESULT_TYPES):
            value = value.tolist()
        if isinstance(value, formulas.tokens.operand.XlError):
            value = None
        elif isinstance(value, list):
            for x in chain(*value):
                if isinstance(x,
                        formulas.tokens.operand.XlError):
                    value = None

        if value is not None:
            if int(value) == value:
                value = int(value)
            else:
                epsilon = 0.0000000001
                if int(value + epsilon) != int(value):
                    value = int(value + epsilon)
                elif int(value - epsilon) != int(value):
                    value = int(value)
                else:
                    value = float(value)
            if round_:
                value = round(value, target_line.decimals)

    return value


custom_functions['R'] = get_nline_relation


def convert_brix_to_density(value=None):
    pool = Pool()
    VolumeConversion = pool.get('lims.volume.conversion')
    try:
        brix = float(value)
    except (TypeError, ValueError):
        return None
    return VolumeConversion.brixToDensity(brix)


custom_functions['D'] = convert_brix_to_density


def convert_brix_to_soluble_solids(value=None):
    pool = Pool()
    VolumeConversion = pool.get('lims.volume.conversion')
    try:
        brix = float(value)
    except (TypeError, ValueError):
        return None
    return VolumeConversion.brixToSolubleSolids(brix)


custom_functions['T'] = convert_brix_to_soluble_solids


def get_reference_value(fraction_type=None, product_type=None, matrix=None,
        analysis=None, target_field=None, device=None):
    cursor = Transaction().connection.cursor()
    pool = Pool()
    Date = pool.get('ir.date')
    NotebookLine = pool.get('lims.notebook.line')
    Analysis = pool.get('lims.analysis')
    Notebook = pool.get('lims.notebook')
    Fraction = pool.get('lims.fraction')
    Sample = pool.get('lims.sample')
    FractionType = pool.get('lims.fraction.type')
    ProductType = pool.get('lims.product.type')
    Matrix = pool.get('lims.matrix')
    AnalysisSheet = pool.get('lims.analysis_sheet')
    Data = pool.get('lims.interface.data')

    if (not fraction_type or not product_type or not matrix or not analysis
            or not target_field):
        return None

    device_clause = ''
    if device:
        if not isinstance(device, int):
            device = device.id
        device_clause = 'AND nl.device = ' + str(device) + ' '

    today = Date.today()

    cursor.execute('SELECT f.id, nl.result, nl.analysis_sheet, nl.id '
        'FROM "' + NotebookLine._table + '" nl '
            'INNER JOIN "' + Analysis._table + '" a '
            'ON a.id = nl.analysis '
            'INNER JOIN "' + Notebook._table + '" n '
            'ON n.id = nl.notebook '
            'INNER JOIN "' + Fraction._table + '" f '
            'ON f.id = n.fraction '
            'INNER JOIN "' + FractionType._table + '" ft '
            'ON ft.id = f.type '
            'INNER JOIN "' + Sample._table + '" s '
            'ON s.id = f.sample '
            'INNER JOIN "' + ProductType._table + '" pt '
            'ON pt.id = s.product_type '
            'INNER JOIN "' + Matrix._table + '" m '
            'ON m.id = s.matrix '
        'WHERE ft.code = %s '
            'AND pt.code = %s '
            'AND m.code = %s '
            'AND a.code = %s '
            'AND (f.expiry_date IS NULL OR f.expiry_date::date > %s::date) '
            'AND nl.accepted = TRUE '
            + device_clause +
        'ORDER BY s.date DESC LIMIT 1',
        (fraction_type, product_type, matrix, analysis, today,))
    reference_line = cursor.fetchall()
    if not reference_line:
        return None
    reference_line = reference_line[0]

    if target_field == 'id':
        return reference_line[0]
    if target_field == 'result':
        return reference_line[1]

    sheet_id = reference_line[2]
    if not sheet_id:
        return None
    sheet = AnalysisSheet(sheet_id)

    with Transaction().set_context(
            lims_interface_table=sheet.compilation.table.id):
        lines = Data.search([
            ('compilation', '=', sheet.compilation.id),
            ('notebook_line', '=', reference_line[3]),
            ], limit=1)
        target_line = lines and lines[0] or None
        if not target_line:
            return None

        if not hasattr(target_line, target_field):
            return None

        return getattr(target_line, target_field)


custom_functions['REFERENCE_VALUE'] = get_reference_value


def scientific2decimal(value=None, decimals=2):
    if value in [None, '', '#VALUE!']:
        return None
    try:
        res = Decimal(str(value)).quantize(Decimal(str(10 ** -decimals)))
    except (TypeError, ValueError):
        return None
    return res


custom_functions['SCIENTIFIC2DECIMAL'] = scientific2decimal


def decimal2scientific(value=None, decimals=2, exponent=None):
    if value in [None, '', '#VALUE!']:
        return None
    try:
        if exponent is not None:
            significand = value / 10 ** exponent
            exponent_sign = '+' if exponent >= 0 else '-'
            res = f'{significand:.{decimals}f}e{exponent_sign}{exponent:02d}'
        else:
            res = ("{0:.%ie}" % (decimals)).format(float(value))
    except (TypeError, ValueError):
        return None
    return res


custom_functions['DECIMAL2SCIENTIFIC'] = decimal2scientific
