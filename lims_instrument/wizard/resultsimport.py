# -*- coding: utf-8 -*-
# This file is part of lims_instrument module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO
import xlrd
from xlutils.copy import copy

from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateView, StateTransition, Button
from trytond.pool import Pool
from datetime import datetime

__all__ = ['LimsNotebookLoadResultsFileStart',
    'LimsNotebookLoadResultsFileStartLine', 'LimsNotebookLoadResultsFileEmpty',
    'LimsNotebookLoadResultsFileResult', 'LimsNotebookLoadResultsFileWarning',
    'LimsNotebookLoadResultsFileExport', 'LimsNotebookLoadResultsFile']


class LimsNotebookLoadResultsFileStart(ModelView):
    'Load Results from File'
    __name__ = 'lims.notebook.load_results_file.start'

    results_importer = fields.Many2One('lims.resultsimport',
        'Results importer', required=True)
    lines = fields.One2Many('lims.notebook.load_results_file.start.line',
        None, 'Files', required=True)


class LimsNotebookLoadResultsFileStartLine(ModelView):
    'Load Results from File'
    __name__ = 'lims.notebook.load_results_file.start.line'

    infile = fields.Binary('File', required=True, filename='name')
    name = fields.Char('Name', readonly=True)


class LimsNotebookLoadResultsFileEmpty(ModelView):
    'Load Results from File Empty'
    __name__ = 'lims.notebook.load_results_file.empty'


class LimsNotebookLoadResultsFileResult(ModelView):
    'Process Results from File'
    __name__ = 'lims.notebook.load_results_file.result'

    result_lines = fields.One2Many('lims.notebook.line', None, 'Lines',
        readonly=True)


class LimsNotebookLoadResultsFileWarning(ModelView):
    'Load Results from File Warning'
    __name__ = 'lims.notebook.load_results_file.warning'

    msg = fields.Text('Message')


class LimsNotebookLoadResultsFileExport(ModelView):
    "Export Results from File"
    __name__ = 'lims.notebook.load_results_file.export'

    file = fields.Binary('File', readonly=True)


class LimsNotebookLoadResultsFile(Wizard):
    'Load Results from File'
    __name__ = 'lims.notebook.load_results_file'

    start = StateView('lims.notebook.load_results_file.start',
        'lims_instrument.lims_load_results_file_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Collect', 'collect', 'tryton-go-next', default=True),
            ])
    collect = StateTransition()
    empty = StateView('lims.notebook.load_results_file.empty',
        'lims_instrument.lims_load_results_file_empty_view_form', [
            Button('Try again', 'start', 'tryton-go-next'),
            Button('Close', 'end', 'tryton-close', default=True),
            ])
    result = StateView('lims.notebook.load_results_file.result',
        'lims_instrument.lims_load_results_file_result_view_form', [
            Button('Cancel', 'cancel', 'tryton-cancel'),
            Button('Confirm', 'confirm', 'tryton-ok', default=True),
            ])
    confirm = StateTransition()
    cancel = StateTransition()
    warning = StateView('lims.notebook.load_results_file.warning',
        'lims_instrument.lims_load_results_file_warning_view_form', [
            Button('Ok', 'close', 'tryton-ok'),
            ])
    close = StateTransition()
    export = StateView('lims.notebook.load_results_file.export',
        'lims_instrument.lims_load_results_file_export_view_form', [
            Button('Done', 'end', 'tryton-close', default=True),
            ])

    def transition_collect(self):
        pool = Pool()
        LimsFraction = pool.get('lims.fraction')
        LimsNotebook = pool.get('lims.notebook')
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsAnalysis = pool.get('lims.analysis')

        lines = []
        for fline in self.start.lines:
            self.start.results_importer.rawresults = {}
            self.start.results_importer.parse(fline.infile)
            raw_results = self.start.results_importer.rawresults
            fractions_numbers = list(raw_results.keys())

            fractions = LimsFraction.search([
                ('number', 'in', fractions_numbers),
                ], order=[('number', 'ASC')])
            for f in fractions:
                notebook = LimsNotebook.search([('fraction', '=', f.id)])
                if not notebook:
                    continue
                for analysis in raw_results[f.number].keys():
                    auto_acquisition_analysis = LimsAnalysis.search([
                        ('code', '=', analysis),
                        ('automatic_acquisition', '=', True),
                        ])
                    if not auto_acquisition_analysis:
                        continue
                    for rep in raw_results[f.number][analysis].keys():
                        clause = [
                            ('notebook', '=', notebook[0].id),
                            ('analysis', '=', analysis),
                            ('repetition', '=', rep),
                            ('result', 'in', [None, '']),
                            ('converted_result', 'in', [None, '']),
                            ('literal_result', 'in', [None, '']),
                            ('result_modifier', 'not in', ['nd', 'pos', 'neg',
                                'ni', 'abs', 'pre', 'na']),
                            ('converted_result_modifier', 'not in',
                                ['nd', 'pos', 'neg', 'ni', 'abs', 'pre']),
                            ]
                        line = LimsNotebookLine.search(clause)
                        if line:
                            data = raw_results[f.number][analysis][rep]
                            res = self.get_results(line[0], data)
                            if res:
                                LimsNotebookLine.write([line[0]], res)
                                lines.append(line[0])

        if lines:
            self.result.result_lines = [l.id for l in lines]
            return 'result'
        return 'empty'

    def get_results(self, line, data):
        LimsDevice = Pool().get('lims.lab.device')

        res = {}
        if 'result' in data or 'literal_result' in data:
            if 'result' in data:
                res['imported_result'] = unicode(float(data['result']))
            if 'literal_result' in data:
                res['imported_literal_result'] = data['literal_result']
            res['imported_end_date'] = (data['end_date'] if 'end_date' in data
                else line.end_date)
            if 'professionals' in data:
                res['imported_professionals'] = data['professionals']
            if 'chromatogram' in data:
                res['imported_chromatogram'] = data['chromatogram']
            device = data['device'] if 'device' in data else None
            if device:
                dev = LimsDevice.search([('code', '=', device)])
                if dev:
                    res['imported_device'] = dev[0].id
            if 'dilution_factor' in data:
                res['imported_dilution_factor'] = data['dilution_factor']
            if 'rm_correction_formula' in data:
                res['imported_rm_correction_formula'] = (
                    data['rm_correction_formula'])
        return res

    def default_result(self, fields):
        default = {}
        default['result_lines'] = [l.id for l in self.result.result_lines]
        return default

    def get_professionals(self, professionals_codes):
        '''
        This function gets a string with one or more professionals codes,
        separated by commas, like: 'ABC' or 'JLB, ABC'
        It returns the professionals
        '''
        Professional = Pool().get('lims.laboratory.professional')
        res = []
        professionals = ''.join(professionals_codes.split())
        professionals = professionals.split(',')
        for professional in professionals:
            prof = Professional.search([('code', '=', professional)])
            if prof:
                res.append(prof[0])
        return res

    def check_professionals(self, professionals, method):
        LimsLabProfessionalMethod = Pool().get('lims.lab.professional.method')

        validated = False
        msg = ''
        for professional in professionals:
            qualifications = LimsLabProfessionalMethod.search([
                ('professional', '=', professional.id),
                ('method', '=', method.id),
                ('type', '=', 'analytical'),
                ])

            if not qualifications:
                validated = False
                msg += '%s not qualified for method: %s' % (
                    professional.code, method.code)
                return validated, msg
            elif qualifications[0].state == 'training':
                if not validated:
                    msg += '%s in training for method: %s. ' \
                        'Add qualified professional' % (
                            professional.code, method.code)
            elif (qualifications[0].state in ('qualified', 'requalified')):
                validated = True

        return validated, msg

    def transition_confirm(self):
        pool = Pool()
        LimsNotebookLine = pool.get('lims.notebook.line')

        warnings = False
        messages = ''
        # Write Results to Notebook lines
        for line in self.result.result_lines:
            original_profs = [{'professional': p.professional}
                    for p in line.professionals]
            notebook_line_original_values = {
                'result': line.result,
                'literal_result': line.literal_result,
                'end_date': line.end_date,
                'professionals': (
                    [('delete', [p.id for p in line.professionals])]
                    + [('create', original_profs,)]),
                'chromatogram': line.chromatogram,
                'device': line.device,
                'dilution_factor': line.dilution_factor,
                'rm_correction_formula': line.rm_correction_formula,
                }
            notebook_line_write = {
                'imported_result': None,
                'imported_literal_result': None,
                'imported_end_date': None,
                'imported_professionals': None,
                'imported_chromatogram': None,
                'imported_device': None,
                'imported_dilution_factor': None,
                'imported_rm_correction_formula': None,
                }

            prevent_line = False
            outcome = ''
            if line.result != line.imported_result:
                if line.imported_result != '-1000.0':
                    notebook_line_write['result'] = line.imported_result
                else:
                    notebook_line_write['result'] = None
                    notebook_line_write['result_modifier'] = 'na'
                    notebook_line_write['report'] = False
                    notebook_line_write['annulled'] = True
                    notebook_line_write['annulment_date'] = datetime.now()
            if line.literal_result != line.imported_literal_result:
                notebook_line_write['literal_result'] = (
                    line.imported_literal_result)
            if line.end_date != line.imported_end_date:
                if line.imported_result != '-1000.0':
                    if (line.start_date and
                            line.start_date <= line.imported_end_date):
                        notebook_line_write['end_date'] = (
                            line.imported_end_date)
                    else:
                        prevent_line = True
                        outcome = 'End date cannot be lower than Start date'
                else:
                    notebook_line_write['end_date'] = None
            if line.chromatogram != line.imported_chromatogram:
                notebook_line_write['chromatogram'] = (
                    line.imported_chromatogram)
            if line.device != line.imported_device:
                notebook_line_write['device'] = line.imported_device
            if line.dilution_factor != line.imported_dilution_factor:
                notebook_line_write['dilution_factor'] = (
                    line.imported_dilution_factor)
            if (line.rm_correction_formula !=
                    line.imported_rm_correction_formula):
                notebook_line_write['rm_correction_formula'] = (
                    line.imported_rm_correction_formula)

            if line.imported_professionals:
                profs = self.get_professionals(line.imported_professionals)
                if profs:
                    validated, msg = self.check_professionals(
                        profs, line.method)
                    if validated:
                        professionals = [{'professional': p.id} for p in profs]
                        notebook_line_write['professionals'] = (
                            [('delete', [p.id for p in line.professionals])]
                            + [('create', professionals)])
                    else:
                        prevent_line = True
                        outcome = msg
                else:
                    prevent_line = True
                    outcome = ('Professional(s) with code '
                        + unicode(line.imported_professionals)
                        + ' not identified')

            if not prevent_line:
                try:
                    LimsNotebookLine.write([line], notebook_line_write)
                except Exception as e:
                    prevent_line = True
                    outcome = unicode(e)
                    LimsNotebookLine.write(
                        [line], notebook_line_original_values)
                else:
                    outcome = 'OK'

            # Update rawresults
            rawresults = self.start.results_importer.rawresults
            number = line.fraction.number
            row_num = 0
            if number in rawresults:
                code = line.analysis.code
                if code in rawresults[number]:
                    rep = line.repetition
                    if rep in rawresults[number][code]:
                        rawresults[number][code][rep]['outcome'] = outcome
                        row_num = rawresults[number][code][rep]['row_number']

            if prevent_line:
                warnings = True
                messages += str(row_num) + ': ' + outcome + '\n'

        if warnings:
            self.warning.msg = messages
            return 'warning'
        else:
            if self.start.results_importer.exportResults():
                return 'end'  # 'export'
        return 'end'

    def transition_cancel(self):
        LimsNotebookLine = Pool().get('lims.notebook.line')
        # Clean results froms Notebook lines
        notebook_line_clean = {
            'imported_result': None,
            'imported_literal_result': None,
            'imported_end_date': None,
            'imported_professionals': None,
            'imported_chromatogram': None,
            'imported_device': None,
            'imported_dilution_factor': None,
            'imported_rm_correction_formula': None,
            }
        LimsNotebookLine.write(
            list(self.result.result_lines), notebook_line_clean)
        return 'end'

    def default_warning(self, fields):
        defaults = {}
        if self.warning.msg:
            defaults['msg'] = self.warning.msg
        return defaults

    def transition_close(self):
        if self.start.results_importer.exportResults():
            return 'end'  # 'export'
        return 'end'

    def default_export(self, fields):
        rawresults = self.start.results_importer.rawresults
        filedata = StringIO.StringIO(self.start.infile)  # TODO: refactoring
        workbook = xlrd.open_workbook(file_contents=filedata.getvalue(),
                formatting_info=True)
        wb_copy = copy(workbook)
        for fraction in rawresults:
            for analysis in rawresults[fraction]:
                for rep in rawresults[fraction][analysis]:
                    repetition = rawresults[fraction][analysis][rep]
                    if 'outcome' in repetition and 'status_cell' in repetition:
                        sheet, row, col = repetition['status_cell']
                        wb_sheet = wb_copy.get_sheet(sheet)
                        wb_sheet.write(row, col, repetition['outcome'])
        output = StringIO.StringIO()
        wb_copy.save(output)
        return {'file': bytearray(output.getvalue())}
