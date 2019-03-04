# -*- coding: utf-8 -*-
# This file is part of lims_instrument module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
try:
    import io as StringIO
except ImportError:
    import io
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


class NotebookLine(metaclass=PoolMeta):
    __name__ = 'lims.notebook.line'

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
    infile_21 = fields.Binary('File 21', filename='name_21')
    name_21 = fields.Char('Name 21', readonly=True)
    infile_22 = fields.Binary('File 22', filename='name_22')
    name_22 = fields.Char('Name 22', readonly=True)
    infile_23 = fields.Binary('File 23', filename='name_23')
    name_23 = fields.Char('Name 23', readonly=True)
    infile_24 = fields.Binary('File 24', filename='name_24')
    name_24 = fields.Char('Name 24', readonly=True)
    infile_25 = fields.Binary('File 25', filename='name_25')
    name_25 = fields.Char('Name 25', readonly=True)
    infile_26 = fields.Binary('File 26', filename='name_26')
    name_26 = fields.Char('Name 26', readonly=True)
    infile_27 = fields.Binary('File 27', filename='name_27')
    name_27 = fields.Char('Name 27', readonly=True)
    infile_28 = fields.Binary('File 28', filename='name_28')
    name_28 = fields.Char('Name 28', readonly=True)
    infile_29 = fields.Binary('File 29', filename='name_29')
    name_29 = fields.Char('Name 29', readonly=True)
    infile_30 = fields.Binary('File 30', filename='name_30')
    name_30 = fields.Char('Name 30', readonly=True)
    infile_31 = fields.Binary('File 31', filename='name_31')
    name_31 = fields.Char('Name 31', readonly=True)
    infile_32 = fields.Binary('File 32', filename='name_32')
    name_32 = fields.Char('Name 32', readonly=True)
    infile_33 = fields.Binary('File 33', filename='name_33')
    name_33 = fields.Char('Name 33', readonly=True)
    infile_34 = fields.Binary('File 34', filename='name_34')
    name_34 = fields.Char('Name 34', readonly=True)
    infile_35 = fields.Binary('File 35', filename='name_35')
    name_35 = fields.Char('Name 35', readonly=True)
    infile_36 = fields.Binary('File 36', filename='name_36')
    name_36 = fields.Char('Name 36', readonly=True)
    infile_37 = fields.Binary('File 37', filename='name_37')
    name_37 = fields.Char('Name 37', readonly=True)
    infile_38 = fields.Binary('File 38', filename='name_38')
    name_38 = fields.Char('Name 38', readonly=True)
    infile_39 = fields.Binary('File 39', filename='name_39')
    name_39 = fields.Char('Name 39', readonly=True)
    infile_40 = fields.Binary('File 40', filename='name_40')
    name_40 = fields.Char('Name 40', readonly=True)
    infile_41 = fields.Binary('File 41', filename='name_41')
    name_41 = fields.Char('Name 41', readonly=True)
    infile_42 = fields.Binary('File 42', filename='name_42')
    name_42 = fields.Char('Name 42', readonly=True)
    infile_43 = fields.Binary('File 43', filename='name_43')
    name_43 = fields.Char('Name 43', readonly=True)
    infile_44 = fields.Binary('File 44', filename='name_44')
    name_44 = fields.Char('Name 44', readonly=True)
    infile_45 = fields.Binary('File 45', filename='name_45')
    name_45 = fields.Char('Name 45', readonly=True)
    infile_46 = fields.Binary('File 46', filename='name_46')
    name_46 = fields.Char('Name 46', readonly=True)
    infile_47 = fields.Binary('File 47', filename='name_47')
    name_47 = fields.Char('Name 47', readonly=True)
    infile_48 = fields.Binary('File 48', filename='name_48')
    name_48 = fields.Char('Name 48', readonly=True)
    infile_49 = fields.Binary('File 49', filename='name_49')
    name_49 = fields.Char('Name 49', readonly=True)
    infile_50 = fields.Binary('File 50', filename='name_50')
    name_50 = fields.Char('Name 50', readonly=True)
    infile_51 = fields.Binary('File 51', filename='name_51')
    name_51 = fields.Char('Name 51', readonly=True)
    infile_52 = fields.Binary('File 52', filename='name_52')
    name_52 = fields.Char('Name 52', readonly=True)
    infile_53 = fields.Binary('File 53', filename='name_53')
    name_53 = fields.Char('Name 53', readonly=True)
    infile_54 = fields.Binary('File 54', filename='name_54')
    name_54 = fields.Char('Name 54', readonly=True)
    infile_55 = fields.Binary('File 55', filename='name_55')
    name_55 = fields.Char('Name 55', readonly=True)
    infile_56 = fields.Binary('File 56', filename='name_56')
    name_56 = fields.Char('Name 56', readonly=True)
    infile_57 = fields.Binary('File 57', filename='name_57')
    name_57 = fields.Char('Name 57', readonly=True)
    infile_58 = fields.Binary('File 58', filename='name_58')
    name_58 = fields.Char('Name 58', readonly=True)
    infile_59 = fields.Binary('File 59', filename='name_59')
    name_59 = fields.Char('Name 59', readonly=True)
    infile_60 = fields.Binary('File 60', filename='name_60')
    name_60 = fields.Char('Name 60', readonly=True)


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

    @classmethod
    def __setup__(cls):
        super(NotebookLoadResultsFile, cls).__setup__()
        cls._error_messages.update({
            'end_date': 'End date cannot be empty',
            'end_date_start_date': 'End date cannot be lower than Start date',
            'inj_date_start_date': ('Injection date cannot be lower than '
                'Start date'),
            'inj_date_end_date': ('Injection date cannot be upper than '
                'End date'),
            'professionals': 'Professional(s) with code %s not identified',
            })

    def transition_collect(self):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Fraction = pool.get('lims.fraction')
        Notebook = pool.get('lims.notebook')
        NotebookLine = pool.get('lims.notebook.line')
        Analysis = pool.get('lims.analysis')

        lines = []
        for fline in [str(item).zfill(2) for item in range(1, 61)]:
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

                for analysis in list(raw_results[f[1]].keys()):
                    cursor.execute('SELECT id '
                        'FROM "' + Analysis._table + '" '
                        'WHERE code = %s '
                            'AND automatic_acquisition = TRUE '
                        'LIMIT 1', (analysis,))
                    if not cursor.fetchone():
                        continue

                    for rep in list(raw_results[f[1]][analysis].keys()):
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
                res['imported_result'] = str(float(data['result']))
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
        AnalyticProfessional = pool.get('lims.notebook.line.professional')

        NOW = datetime.now()
        warnings = False
        messages = ''
        export_results = self.start.results_importer.exportResults()

        previous_professionals = []
        lines_to_update = []
        for line in self.result.result_lines:
            prevent_line = False
            outcome = 'OK'

            if line.imported_result != '-1000.0':
                if not line.imported_end_date:
                    prevent_line = True
                    outcome = self.raise_user_error('end_date',
                        raise_exception=False)
                elif (line.imported_end_date and line.start_date and
                        line.start_date > line.imported_end_date):
                    prevent_line = True
                    outcome = self.raise_user_error('end_date_start_date',
                        raise_exception=False)
                elif (line.imported_inj_date and line.start_date and
                        line.start_date > line.imported_inj_date):
                    prevent_line = True
                    outcome = self.raise_user_error('inj_date_start_date',
                        raise_exception=False)
                elif (line.imported_end_date and line.imported_inj_date and
                        line.imported_inj_date > line.imported_end_date):
                    prevent_line = True
                    outcome = self.raise_user_error('inj_date_end_date',
                        raise_exception=False)
                else:
                    line.result = line.imported_result
                    line.end_date = line.imported_end_date
                    line.injection_date = line.imported_inj_date

            else:
                line.result = None
                line.result_modifier = 'na'
                line.report = False
                line.annulled = True
                line.annulment_date = NOW
                line.end_date = None
                line.injection_date = None

            line.literal_result = line.imported_literal_result
            line.chromatogram = line.imported_chromatogram
            line.device = line.imported_device
            line.dilution_factor = line.imported_dilution_factor
            line.rm_correction_formula = line.imported_rm_correction_formula

            line_previous_professionals = []
            if line.imported_professionals:
                profs = self.get_professionals(line.imported_professionals)
                if profs:
                    validated, msg = self.check_professionals(
                        profs, line.method)
                    if validated:
                        line_previous_professionals = [p for p in
                            line.professionals]
                        new_professionals = [
                            AnalyticProfessional(professional=p[0])
                            for p in profs]
                        line.professionals = new_professionals
                    else:
                        prevent_line = True
                        outcome = msg
                else:
                    prevent_line = True
                    outcome = self.raise_user_error('professionals',
                        (str(line.imported_professionals),),
                        raise_exception=False)

            if prevent_line:
                warnings = True
                message = '%s [%s] (%s): %s\n' % (
                    line.fraction.number, line.analysis.code, line.repetition,
                    outcome)
                messages += message

                # Update rawresults
                if export_results:
                    rawresults = self.start.results_importer.rawresults
                    number = line.fraction.number
                    if number in rawresults:
                        code = line.analysis.code
                        if code in rawresults[number]:
                            rep = line.repetition
                            if rep in rawresults[number][code]:
                                rawresults[number][code][rep]['outcome'] = (
                                    outcome)

            else:
                previous_professionals.extend(line_previous_professionals)
                line.imported_result = None
                line.imported_literal_result = None
                line.imported_end_date = None
                line.imported_professionals = None
                line.imported_chromatogram = None
                line.imported_device = None
                line.imported_dilution_factor = None
                line.imported_rm_correction_formula = None
                line.imported_inj_date = None
                lines_to_update.append(line)

        # Write Results to Notebook lines
        AnalyticProfessional.delete(previous_professionals)
        NotebookLine.save(lines_to_update)

        if warnings:
            self.warning.msg = messages
            return 'warning'
        else:
            if export_results:
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
        filedata = io.StringIO(self.start.infile)  # TODO: refactoring
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
        output = io.StringIO()
        wb_copy.save(output)
        return {'file': bytearray(output.getvalue())}
