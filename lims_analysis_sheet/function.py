# -*- coding: utf-8 -*-
# This file is part of lims_analysis_sheet module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from trytond.transaction import Transaction

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


def get_nline_analysis(analysis_code, alias=None, notebook_line=None):
    pool = Pool()
    NotebookLine = pool.get('lims.notebook.line')

    notebook_id = Transaction().context.get('lims_analysis_notebook')
    if not notebook_id:
        if not notebook_line:
            return None
        if isinstance(notebook_line, int):
            notebook_line = NotebookLine(notebook_line)
        notebook_id = notebook_line.notebook.id

    lines = NotebookLine.search([
        ('notebook', '=', notebook_id),
        ('analysis.code', '=', analysis_code),
        ('annulled', '=', False),
        ])
    target_line = lines and lines[0] or None
    if not target_line:
        return None

    alias = alias or 'result'
    if not hasattr(target_line, alias):
        return None

    return getattr(target_line, alias)


custom_functions['NL'] = get_nline_analysis


def get_sheet_analysis(analysis_code, alias=None, notebook_line=None):
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

    lines = NotebookLine.search([
        ('notebook', '=', notebook_id),
        ('analysis.code', '=', analysis_code),
        ('annulled', '=', False),
        ])
    nline = lines and lines[0] or None
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
