# -*- coding: utf-8 -*-
# This file is part of lims_analysis_sheet module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from trytond.transaction import Transaction

custom_functions = {}


def _get_result_column():
    pool = Pool()
    ModelField = pool.get('ir.model.field')
    Field = pool.get('lims.interface.table.field')

    table_id = Transaction().context.get('lims_interface_table')
    if not table_id:
        return None
    nl_result_field, = ModelField.search([
        ('model.model', '=', 'lims.notebook.line'),
        ('name', '=', 'result'),
        ])
    result_column = Field.search([
        ('table', '=', table_id),
        ('transfer_field', '=', True),
        ('related_line_field', '=', nl_result_field),
        ])
    if not result_column:
        return None
    return result_column[0].name


def device_correction(device_id, value):
    LabDevice = Pool().get('lims.lab.device')
    if device_id and value:
        device = LabDevice(device_id)
        if device:
            return device.get_correction(value)
    return value


custom_functions['DEVICE_CORRECTION'] = device_correction


def get_analysis(analysis_code, alias=None):
    Data = Pool().get('lims.interface.data')

    compilation_id = Transaction().context.get('lims_interface_compilation')
    if not compilation_id:
        return None

    notebook_id = Transaction().context.get('lims_analysis_notebook')
    if not notebook_id:
        return None

    alias = alias or _get_result_column()
    if not alias:
        return None

    target_line = None
    lines = Data.search([('compilation', '=', compilation_id)])
    for line in lines:
        if (not line.annulled and
                line.notebook_line.notebook.id == notebook_id and
                line.notebook_line.analysis.code == analysis_code):
            target_line = line
            break

    if not target_line:
        return None
    return getattr(target_line, alias)


custom_functions['A'] = get_analysis


def convert_brix_to_density(value=None):
    VolumeConversion = Pool().get('lims.volume.conversion')
    try:
        brix = float(value)
    except (TypeError, ValueError):
        return None
    return VolumeConversion.brixToDensity(brix)


custom_functions['D'] = convert_brix_to_density


def convert_brix_to_soluble_solids(value=None):
    VolumeConversion = Pool().get('lims.volume.conversion')
    try:
        brix = float(value)
    except (TypeError, ValueError):
        return None
    return VolumeConversion.brixToSolubleSolids(brix)


custom_functions['T'] = convert_brix_to_soluble_solids
