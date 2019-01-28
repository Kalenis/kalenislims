# -*- coding: utf-8 -*-
# This file is part of lims_instrument module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO
import traceback
import xlrd
from xlutils.copy import copy
from datetime import datetime

from trytond.model import ModelView, ModelSQL, fields, Unique
from trytond.wizard import Wizard, StateView, StateTransition, Button
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction


__all__ = ['NotebookLine', 'ResultsImport', 'NotebookLoadResultsFileStart',
    'NotebookLoadResultsFileEmpty',
    'NotebookLoadResultsFileResult', 'NotebookLoadResultsFileWarning',
    'NotebookLoadResultsFileExport', 'NotebookLoadResultsFile']


class NotebookLine:
    __name__ = 'lims.notebook.line'
    __metaclass__ = PoolMeta

    imported_result = fields.Char('Result')
    imported_literal_result = fields.Char('Literal result')
    imported_end_date = fields.Date('End date')
    imported_professionals = fields.Char('Professionals')
    imported_chromatogram = fields.Char('Chromatogram')
    imported_device = fields.Many2One('lims.lab.device', 'Device')
    imported_dilution_factor = fields.Float('Dilution factor')
    imported_rm_correction_formula = fields.Char('RM Correction Formula')
    imported_inj_date = fields.Date('Inject date')


class ResultsImport(ModelSQL, ModelView):
    'Results Import'
    __name__ = 'lims.resultsimport'
    _rec_name = 'description'

    name = fields.Selection([], 'Name', required=True, sort=False,
        depends=['description'])
    description = fields.Char('Description', required=True)
    controller = None
    _infile = None
    header = []
    rawresults = {}
    mimetype = None
    numline = 0

    @classmethod
    def __setup__(cls):
        super(ResultsImport, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('name_uniq', Unique(t, t.name),
                'The results importer name must be unique'),
            ]
        cls._error_messages.update({
            'not_module': 'No module for importer type "%s"',
            'not_implemented': ('The function "%s" is not implemented for'
                ' this importer'),
            })

    @fields.depends('name')
    def on_change_with_description(self, name=None):
        description = None
        if self.name:
            self.loadController()
        if self.controller:
            try:
                description = self.controller.getControllerName()
            except AttributeError:
                self.raise_user_error('not_implemented',
                    ('getControllerName',))
        return description

    def loadController(self):
        self.raise_user_error('not_module', (self.name,))

    def getInputFile(self):
        return self._infile

    def setInputFile(self, infile):
        self._infile = infile

    def parse(self, infile):
        if not self.controller:
            self.loadController()
        try:
            return self.controller.parse(self, infile)
        except AttributeError:
            traceback.print_exc()
            self.raise_user_error('not_implemented', ('parse',))

    def exportResults(self):
        '''
        This function defines whether the importer
        export results to a file at the end of the process.
        Default is False
        '''
        if not self.controller:
            self.loadController()
        try:
            return self.controller.exportResults(self)
        except AttributeError:
            return False


class NotebookLoadResultsFileStart(ModelView):
    'Load Results from File'
    __name__ = 'lims.notebook.load_results_file.start'

    results_importer = fields.Many2One('lims.resultsimport',
        'Results importer', required=True)
    infile_01 = fields.Binary('File 01', filename='name_01')
    name_01 = fields.Char('Name 01', readonly=True)
    infile_02 = fields.Binary('File 02', filename='name_02')
    name_02 = fields.Char('Name 02', readonly=True)
    infile_03 = fields.Binary('File 03', filename='name_03')
    name_03 = fields.Char('Name 03', readonly=True)
    infile_04 = fields.Binary('File 04', filename='name_04')
    name_04 = fields.Char('Name 04', readonly=True)
    infile_05 = fields.Binary('File 05', filename='name_05')
    name_05 = fields.Char('Name 05', readonly=True)
    infile_06 = fields.Binary('File 06', filename='name_06')
    name_06 = fields.Char('Name 06', readonly=True)
    infile_07 = fields.Binary('File 07', filename='name_07')
    name_07 = fields.Char('Name 07', readonly=True)
    infile_08 = fields.Binary('File 08', filename='name_08')
    name_08 = fields.Char('Name 08', readonly=True)
    infile_09 = fields.Binary('File 09', filename='name_09')
    name_09 = fields.Char('Name 09', readonly=True)
    infile_10 = fields.Binary('File 10', filename='name_10')
    name_10 = fields.Char('Name 10', readonly=True)
    infile_11 = fields.Binary('File 11', filename='name_11')
    name_11 = fields.Char('Name 11', readonly=True)
    infile_12 = fields.Binary('File 12', filename='name_12')
    name_12 = fields.Char('Name 12', readonly=True)
    infile_13 = fields.Binary('File 13', filename='name_13')
    name_13 = fields.Char('Name 13', readonly=True)
    infile_14 = fields.Binary('File 14', filename='name_14')
    name_14 = fields.Char('Name 14', readonly=True)
    infile_15 = fields.Binary('File 15', filename='name_15')
    name_15 = fields.Char('Name 15', readonly=True)
    infile_16 = fields.Binary('File 16', filename='name_16')
    name_16 = fields.Char('Name 16', readonly=True)
    infile_17 = fields.Binary('File 17', filename='name_17')
    name_17 = fields.Char('Name 17', readonly=True)
    infile_18 = fields.Binary('File 18', filename='name_18')
    name_18 = fields.Char('Name 18', readonly=True)
    infile_19 = fields.Binary('File 19', filename='name_19')
    name_19 = fields.Char('Name 19', readonly=True)
    infile_20 = fields.Binary('File 20', filename='name_20')
    name_20 = fields.Char('Name 20', readonly=True)


class NotebookLoadResultsFileEmpty(ModelView):
    'Load Results from File Empty'
    __name__ = 'lims.notebook.load_results_file.empty'


class NotebookLoadResultsFileResult(ModelView):
    'Process Results from File'
    __name__ = 'lims.notebook.load_results_file.result'

    result_lines = fields.One2Many('lims.notebook.line', None, 'Lines',
        readonly=True)


class NotebookLoadResultsFileWarning(ModelView):
    'Load Results from File Warning'
    __name__ = 'lims.notebook.load_results_file.warning'

    msg = fields.Text('Message')


class NotebookLoadResultsFileExport(ModelView):
    "Export Results from File"
    __name__ = 'lims.notebook.load_results_file.export'

    file = fields.Binary('File', readonly=True)


class NotebookLoadResultsFile(Wizard):
    'Load Results from File'
    __name__ = 'lims.notebook.load_results_file'

    start = StateView('lims.notebook.load_results_file.start',
        'lims_instrument.lims_load_results_file_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Collect', 'collect', 'tryton-forward', default=True),
            ])
    collect = StateTransition()
    empty = StateView('lims.notebook.load_results_file.empty',
        'lims_instrument.lims_load_results_file_empty_view_form', [
            Button('Try again', 'start', 'tryton-forward'),
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
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Fraction = pool.get('lims.fraction')
        Notebook = pool.get('lims.notebook')
        NotebookLine = pool.get('lims.notebook.line')
        Analysis = pool.get('lims.analysis')

        lines = []
        for fline in [str(item).zfill(2) for item in range(1, 21)]:
            file_ = getattr(self.start, 'infile_%s' % fline)
            if not file_:
                continue
            self.start.results_importer.rawresults = {}
            self.start.results_importer.parse(file_)
            raw_results = self.start.results_importer.rawresults
            fractions_numbers = list(raw_results.keys())
            if not fractions_numbers:
                continue

            numbers = '\', \''.join(str(n) for n in fractions_numbers)
            cursor.execute('SELECT id, number '
                'FROM "' + Fraction._table + '" '
                'WHERE number IN (\'' + numbers + '\') '
                'ORDER BY number ASC')

            for f in cursor.fetchall():
                cursor.execute('SELECT id '
                    'FROM "' + Notebook._table + '" '
                    'WHERE fraction = %s '
                    'LIMIT 1', (f[0],))
                notebook = cursor.fetchone()
                if not notebook:
                    continue

                for analysis in raw_results[f[1]].keys():
                    cursor.execute('SELECT id '
                        'FROM "' + Analysis._table + '" '
                        'WHERE code = %s '
                            'AND automatic_acquisition = TRUE '
                        'LIMIT 1', (analysis,))
                    if not cursor.fetchone():
                        continue

                    for rep in raw_results[f[1]][analysis].keys():
                        clause = [
                            ('notebook', '=', notebook[0]),
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
                        line = NotebookLine.search(clause)
                        if line:
                            data = raw_results[f[1]][analysis][rep]
                            res = self.get_results(line[0], data)
                            if res:
                                NotebookLine.write([line[0]], res)
                                lines.append(line[0])

        if lines:
            self.result.result_lines = [l.id for l in lines]
            return 'result'
        return 'empty'

    def get_results(self, line, data):
        pool = Pool()
        Device = pool.get('lims.lab.device')

        res = {}
        if 'result' in data or 'literal_result' in data:
            if 'result' in data:
                res['imported_result'] = unicode(float(data['result']))
            if 'literal_result' in data:
                res['imported_literal_result'] = data['literal_result']
            res['imported_end_date'] = (data['end_date'] if 'end_date' in data
                else line.end_date)
            res['imported_inj_date'] = (data['injection_date']
                if 'injection_date' in data else None)
            if 'professionals' in data:
                res['imported_professionals'] = data['professionals']
            if 'chromatogram' in data:
                res['imported_chromatogram'] = data['chromatogram']
            device = data['device'] if 'device' in data else None
            if device:
                dev = Device.search([('code', '=', device)])
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
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Professional = pool.get('lims.laboratory.professional')

        res = []
        professionals = ''.join(professionals_codes.split())
        professionals = professionals.split(',')
        for professional in professionals:
            cursor.execute('SELECT id, code '
                'FROM "' + Professional._table + '" '
                'WHERE code = %s '
                'LIMIT 1', (professional,))
            prof = cursor.fetchone()
            if prof:
                res.append(prof)
        return res

    def check_professionals(self, professionals, method):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LabProfessionalMethod = pool.get('lims.lab.professional.method')

        validated = False
        msg = ''
        for professional in professionals:
            cursor.execute('SELECT state '
                'FROM "' + LabProfessionalMethod._table + '" '
                'WHERE professional = %s '
                    'AND method = %s '
                    'AND type = \'analytical\' '
                'LIMIT 1', (professional[0], method.id))
            qualification = cursor.fetchone()
            if not qualification:
                validated = False
                msg += '%s not qualified for method: %s' % (
                    professional[1], method.code)
                return validated, msg
            elif qualification[0] == 'training':
                if not validated:
                    msg += '%s in training for method: %s. ' \
                        'Add qualified professional' % (
                            professional[1], method.code)
            elif (qualification[0] in ('qualified', 'requalified')):
                validated = True

        return validated, msg

    def transition_confirm(self):
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')

        NOW = datetime.now()
        warnings = False
        messages = ''
        # Write Results to Notebook lines
        for line in self.result.result_lines:
            notebook_line_write = {
                'imported_result': None,
                'imported_literal_result': None,
                'imported_end_date': None,
                'imported_professionals': None,
                'imported_chromatogram': None,
                'imported_device': None,
                'imported_dilution_factor': None,
                'imported_rm_correction_formula': None,
                'imported_inj_date': None,
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
                    notebook_line_write['annulment_date'] = NOW
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
            if line.injection_date != line.imported_inj_date:
                if line.imported_result != '-1000.0':
                    if (line.start_date and
                            line.start_date <= line.imported_inj_date):
                        notebook_line_write['injection_date'] = (
                            line.imported_inj_date)
                    else:
                        prevent_line = True
                        outcome = \
                            'Injection date cannot be lower than Start date'
                else:
                    notebook_line_write['injection_date'] = None
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
                        professionals = [{'professional': p[0]}
                            for p in profs]
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
                    NotebookLine.write([line], notebook_line_write)
                except Exception as e:
                    prevent_line = True
                    outcome = unicode(e)
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
                        'injection_date': line.injection_date,
                        }
                    NotebookLine.write(
                        [line], notebook_line_original_values)
                else:
                    outcome = 'OK'

            # Update rawresults
            row_num = 0
            if self.start.results_importer.exportResults() or prevent_line:
                rawresults = self.start.results_importer.rawresults
                number = line.fraction.number
                if number in rawresults:
                    code = line.analysis.code
                    if code in rawresults[number]:
                        rep = line.repetition
                        if rep in rawresults[number][code]:
                            rawresults[number][code][rep]['outcome'] = outcome
                            row_num = rawresults[number][code][rep][
                                'row_number']

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
        NotebookLine = Pool().get('lims.notebook.line')
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
            'imported_inj_date': None,
            }
        NotebookLine.write(
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
