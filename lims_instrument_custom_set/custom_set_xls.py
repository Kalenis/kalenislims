# -*- coding: utf-8 -*-
# This file is part of lims_instrument_custom_set module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import io
import xlrd

from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.modules.lims.formula_parser import FormulaParser

IGNORE_SHEET = '###'
ANALYSIS_CODE = 'Analysis Code'
DATA_HEADER = 'Data Header'
FORMULA = 'Formula'


def getControllerName():
    if Transaction().language in ('es', 'es_419'):
        return 'Planilla personalizada - XLS'
    else:
        return 'Custom Set - XLS'


def parse(self, infile):
    LabWorkYear = Pool().get('lims.lab.workyear')

    filedata = io.StringIO(infile)
    workbook = xlrd.open_workbook(file_contents=filedata.getvalue())
    worksheets = workbook.sheet_names()
    for worksheet_name in worksheets:
        worksheet = workbook.sheet_by_name(worksheet_name)
        if worksheet.cell_value(0, 0) == IGNORE_SHEET:
            continue
        self.analysis_code = None
        self.formula = None
        self.header = []
        num_rows = worksheet.nrows - 1
        curr_row = -1
        header_found = False
        while curr_row < num_rows:
            curr_row += 1
            row = worksheet.row(curr_row)
            if not self.analysis_code:
                self.getAnalysisCode(row)
            if not self.formula:
                self.getFormula(row)
            if not self.header:
                curr_row += self.getDataHeader(worksheet, curr_row)

            if self.analysis_code and self.formula and self.header:
                row = [cell for cell in row
                    if cell.ctype != xlrd.XL_CELL_EMPTY]
                row = row[:len(self.header)]
                if header_found is False:
                    row = [cell.value for cell in row]
                    if row == self.header:
                        header_found = True
                    continue

                # Start reading data:
                # they must be numbers and as many as header elements
                for cell in row:
                    if cell.ctype != xlrd.XL_CELL_NUMBER:
                        header_found = False
                        continue
                row = [cell.value for cell in row]
                if len(row) < len(self.header):
                    header_found = False
                    continue

                workyear = LabWorkYear.search(
                    ['code', '=', str(int(row[1]))
                    ])
                padding = None
                if workyear and workyear[0] and workyear[0].sample_sequence:
                    padding = workyear[0].sample_sequence.padding
                if padding:
                    sample = '%%0%sd' % padding % int(row[0])
                    fraction = str(int(row[1])) + '/' + sample + \
                        '-' + str(int(row[2]))
                    repetition = int(row[3])
                    values = {}
                    remaining_header = self.header[4:]
                    i = 4
                    for h in remaining_header:
                        # remove whitespaces and dots
                        h = ''.join(h.split())
                        h = ''.join(h.split('.'))
                        values[h] = row[i]
                        i += 1
                    formulaParser = FormulaParser(self.formula, values)
                    values['result'] = formulaParser.getValue()
                    values['row_number'] = curr_row + 1
                    if fraction in self.rawresults:
                        if self.analysis_code in self.rawresults[fraction]:
                            self.rawresults[fraction][self.analysis_code][
                                repetition] = values
                        else:
                            self.rawresults[fraction][self.analysis_code] = {
                                    repetition: values,
                                }
                    else:
                        self.rawresults[fraction] = {
                            self.analysis_code: {
                                repetition: values,
                                },
                            }


def getAnalysisCode(self, row):
    found = False
    for cell in row:
        if found and cell.ctype == xlrd.XL_CELL_TEXT:
            self.analysis_code = cell.value
            return
        if cell.value == ANALYSIS_CODE:
            found = True


def getDataHeader(self, worksheet, curr_row):
    row = worksheet.row(curr_row)
    for cell in row:
        if cell.value == DATA_HEADER:
            curr_row += 1
            if curr_row < (worksheet.nrows - 1):
                # Look up in the next row
                next_row = worksheet.row(curr_row)
                for c in next_row:
                    if c.ctype == xlrd.XL_CELL_TEXT:
                        self.header.append(c.value)
                return 1
        return 0


def getFormula(self, row):
    found = False
    for cell in row:
        if found and cell.ctype == xlrd.XL_CELL_TEXT:
            # remove whitespaces and dots
            value = ''.join(cell.value.split())
            self.formula = ''.join(value.split('.'))
            return
        if cell.value == FORMULA:
            found = True
