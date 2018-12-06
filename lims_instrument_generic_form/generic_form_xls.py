# -*- coding: utf-8 -*-
# This file is part of lims_instrument_generic_form module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import xlrd
from io import BytesIO
from datetime import date

from trytond.pool import Pool
from trytond.transaction import Transaction


COL = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8,
    'J': 9, 'K': 10, 'L': 11, 'M': 12}
STATUS_COLUMN = 10


def getControllerName():
    if Transaction().language in ('es', 'es_419'):
        return 'Formulario genérico - XLS'
    else:
        return 'Generic Form - XLS'


def parse(self, infile):
    LabWorkYear = Pool().get('lims.lab.workyear')

    filedata = BytesIO(infile)
    workbook = xlrd.open_workbook(file_contents=filedata.getvalue())
    worksheets = workbook.sheet_names()
    for worksheet_name in worksheets:
        worksheet = workbook.sheet_by_name(worksheet_name)

        num_rows = worksheet.nrows - 1
        curr_row = 0
        while curr_row < num_rows:
            # We start reading at the second row
            curr_row += 1
            row = worksheet.row(curr_row)
            # We must have at least 11 columns
            if len(row) < 11:
                continue

            analysis_code_raw = row[COL['A']].value
            if not analysis_code_raw:
                continue
            if row[COL['A']].ctype == xlrd.XL_CELL_NUMBER:
                analysis_code = str(int(analysis_code_raw))
            elif row[COL['A']].ctype == xlrd.XL_CELL_TEXT:
                analysis_code = analysis_code_raw
            else:
                continue
            if analysis_code:
                analysis_code = analysis_code.strip()
            sample = int(row[COL['E']].value) if (
                row[COL['E']].ctype == xlrd.XL_CELL_NUMBER) else None
            year = int(row[COL['F']].value) if (
                row[COL['F']].ctype == xlrd.XL_CELL_NUMBER) else None
            workyear = LabWorkYear.search(
                ['code', '=', str(year)])
            padding = None
            if workyear and workyear[0] and workyear[0].sample_sequence:
                padding = workyear[0].sample_sequence.padding
            if padding and sample:
                sample = '%%0%sd' % padding % sample
            else:
                continue
            fraction = int(row[COL['G']].value) if (
                row[COL['G']].ctype == xlrd.XL_CELL_NUMBER) else None
            if fraction and year:
                fraction = str(year) + '/' + sample + '-' + str(fraction)
            repetition = int(row[COL['H']].value) if (
                row[COL['H']].ctype == xlrd.XL_CELL_NUMBER) else None
            if not analysis_code or not fraction or repetition is None:
                continue

            values = {}
            result = row[COL['I']].value if (
                row[COL['I']].ctype == xlrd.XL_CELL_NUMBER) else None
            end_date_raw = row[COL['B']].value
            if row[COL['B']].ctype == xlrd.XL_CELL_TEXT:
                try:
                    dt = end_date_raw.split('/')
                    end_date = date(int(dt[2]), int(dt[1]), int(dt[0]))
                except:
                    end_date = None
            elif row[COL['B']].ctype == xlrd.XL_CELL_DATE:
                dt = xlrd.xldate_as_tuple(end_date_raw, workbook.datemode)
                end_date = date(dt[0], dt[1], dt[2])
            else:
                end_date = None
            professionals = row[COL['D']].value if (
                row[COL['D']].ctype == xlrd.XL_CELL_TEXT) else None
            chromatogram = row[COL['J']].value if (
                row[COL['J']].ctype == xlrd.XL_CELL_TEXT) else None
            device = None
            if row[COL['C']].ctype == xlrd.XL_CELL_NUMBER:
                device = str(int(row[COL['C']].value))
            elif row[COL['C']].ctype == xlrd.XL_CELL_TEXT:
                device = row[COL['C']].value
            inj_date_raw = row[COL['L']].value
            if row[COL['L']].ctype == xlrd.XL_CELL_TEXT:
                try:
                    it = inj_date_raw.split('/')
                    inj_date = date(int(it[2]), int(it[1]), int(it[0]))
                except:
                    inj_date = None
            elif row[COL['L']].ctype == xlrd.XL_CELL_DATE:
                it = xlrd.xldate_as_tuple(inj_date_raw, workbook.datemode)
                inj_date = date(it[0], it[1], it[2])
            else:
                inj_date = None

            if result is not None:
                values['result'] = result
                # Where to save final status: [sheet number, row, column]
                values['status_cell'] = [
                    worksheet.number, curr_row, STATUS_COLUMN]
            if end_date:
                values['end_date'] = end_date
            if inj_date:
                values['injection_date'] = inj_date
            if professionals:
                values['professionals'] = professionals
            if chromatogram:
                values['chromatogram'] = chromatogram
            if device:
                values['device'] = device
            values['row_number'] = curr_row + 1

            if fraction in self.rawresults:
                if analysis_code in self.rawresults[fraction]:
                    self.rawresults[fraction][analysis_code][
                        repetition] = values
                else:
                    self.rawresults[fraction][analysis_code] = {
                        repetition: values,
                        }
            else:
                self.rawresults[fraction] = {
                    analysis_code: {
                        repetition: values,
                        },
                    }
