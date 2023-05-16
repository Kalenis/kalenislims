# -*- coding: utf-8 -*-
# This file is part of lims_instrument module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import io
import traceback
import xlrd
from xlutils.copy import copy
from datetime import datetime
from sql import Null, Literal

from trytond.model import ModelView, ModelSQL, fields, Unique
from trytond.wizard import Wizard, StateView, StateTransition, Button
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.i18n import gettext


class NotebookLine(metaclass=PoolMeta):
    __name__ = 'lims.notebook.line'

    imported_result = fields.Char('Imported Result')
    imported_literal_result = fields.Char('Imported Literal result')
    imported_end_date = fields.Date('Imported End date')
    imported_professionals = fields.Char('Imported Professionals')
    imported_chromatogram = fields.Char('Imported Chromatogram')
    imported_device = fields.Many2One('lims.lab.device', 'Imported Device')
    imported_dilution_factor = fields.Float('Imported Dilution factor')
    imported_rm_correction_formula = fields.Char(
        'Imported RM Correction Formula')
    imported_inj_date = fields.Date('Imported Inject date')
    imported_trace_report = fields.Boolean('Imported Trace report')


class BaseImport(object):
    __slots__ = ('__dict__',)

    def __init__(self, id=None, **kwargs):
        self.controller = None
        self.infile = None
        self.rawresults = {}
        self.mimetype = None
        self.numline = 0
        self.analysis_code = None
        self.formula = None
        self.header = []
        super().__init__(id, **kwargs)

    def getInputFile(self):
        return self.infile

    def setInputFile(self, infile):
        self.infile = infile

    def loadController(self):
        self.controller = None

    def parse(self, infile):
        self.rawresults = {}
        if not self.controller:
            self.loadController()
        try:
            return self.controller.parse(self, infile)
        except AttributeError:
            traceback.print_exc()
            raise UserError(gettext('lims_instrument.msg_not_implemented',
                function='parse'))

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


class ResultsImport(BaseImport, ModelSQL, ModelView):
    'Results Import'
    __name__ = 'lims.resultsimport'
    _rec_name = 'description'

    name = fields.Selection([], 'Name', required=True, sort=False)
    description = fields.Char('Description', required=True)

    @classmethod
    def __setup__(cls):
        super().__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('name_uniq', Unique(t, t.name),
                'lims_instrument.msg_results_importer_unique_id'),
            ]

    @fields.depends('name')
    def on_change_with_description(self, name=None):
        description = None
        if self.name:
            self.loadController()
        if self.controller:
            try:
                description = self.controller.getControllerName()
            except AttributeError:
                raise UserError(gettext('lims_instrument.msg_not_implemented',
                    function='getControllerName'))
        return description

    def loadController(self):
        raise UserError(gettext('lims_instrument.msg_not_module',
            module=self.name))


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

    result_lines = fields.One2Many('lims.notebook.line', None, 'Lines')


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
        for fline in [str(item).zfill(2) for item in range(1, 61)]:
            file_ = getattr(self.start, 'infile_%s' % fline)
            if not file_:
                continue
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
                            ('start_date', '!=', None),
                            ('result', 'in', [None, '']),
                            ('converted_result', 'in', [None, '']),
                            ('literal_result', 'in', [None, '']),
                            ['OR', ('result_modifier', '=', None),
                                ('result_modifier.code', 'not in',
                                ['d', 'nd', 'pos', 'neg', 'ni', 'abs',
                                    'pre', 'na'])],
                            ['OR', ('converted_result_modifier', '=', None),
                                ('converted_result_modifier.code', 'not in',
                                ['d', 'nd', 'pos', 'neg', 'ni', 'abs',
                                    'pre'])],
                            ]
                        line = NotebookLine.search(clause, limit=1)
                        if not line:
                            continue
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
            if 'trace_report' in data:
                res['imported_trace_report'] = data['trace_report']
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
            if not prof:
                return []
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
        cursor = Transaction().connection.cursor()
        pool = Pool()
        ModelData = pool.get('ir.model.data')
        NotebookLine = pool.get('lims.notebook.line')
        AnalyticProfessional = pool.get('lims.notebook.line.professional')
        sql_table = NotebookLine.__table__()

        NOW = datetime.now()
        warnings = False
        messages = ''
        export_results = self.start.results_importer.exportResults()
        result_modifier_na = ModelData.get_id('lims', 'result_modifier_na')

        previous_professionals = []
        new_professionals = []
        for line in self.result.result_lines:
            columns = []
            values = []
            prevent_line = False
            outcome = 'OK'

            if line.imported_result != '-1000.0':
                if not line.imported_end_date:
                    prevent_line = True
                    outcome = gettext('lims_instrument.msg_end_date')
                elif (line.imported_end_date and line.start_date and
                        line.start_date > line.imported_end_date):
                    prevent_line = True
                    outcome = gettext(
                        'lims_instrument.msg_end_date_start_date')
                elif (line.imported_inj_date and line.start_date and
                        line.start_date > line.imported_inj_date):
                    prevent_line = True
                    outcome = gettext(
                        'lims_instrument.msg_inj_date_start_date')
                elif (line.imported_end_date and line.imported_inj_date and
                        line.imported_inj_date > line.imported_end_date):
                    prevent_line = True
                    outcome = gettext('lims_instrument.msg_inj_date_end_date')
                else:
                    columns.append(sql_table.result)
                    values.append(line.imported_result)
                    columns.append(sql_table.end_date)
                    values.append(line.imported_end_date)
                    columns.append(sql_table.injection_date)
                    values.append(line.imported_inj_date)

            else:
                columns.append(sql_table.result)
                values.append(Null)
                columns.append(sql_table.result_modifier)
                values.append(result_modifier_na)
                columns.append(sql_table.report)
                values.append(Literal(False))
                columns.append(sql_table.annulled)
                values.append(Literal(True))
                columns.append(sql_table.annulment_date)
                values.append(NOW)
                columns.append(sql_table.end_date)
                values.append(Null)
                columns.append(sql_table.injection_date)
                values.append(Null)

            columns.append(sql_table.literal_result)
            values.append(line.imported_literal_result)
            columns.append(sql_table.chromatogram)
            values.append(line.imported_chromatogram)
            columns.append(sql_table.device)
            values.append(line.imported_device and
                line.imported_device.id or Null)
            columns.append(sql_table.dilution_factor)
            values.append(line.imported_dilution_factor)
            columns.append(sql_table.rm_correction_formula)
            values.append(line.imported_rm_correction_formula)
            columns.append(sql_table.trace_report)
            values.append(line.imported_trace_report)

            line_previous_professionals = []
            if line.imported_professionals:
                profs = self.get_professionals(line.imported_professionals)
                if profs:
                    validated, msg = self.check_professionals(
                        profs, line.method)
                    if validated:
                        line_previous_professionals = [p for p in
                            line.professionals]
                        line_new_professionals = [{
                            'notebook_line': line.id,
                            'professional': p[0],
                            } for p in profs]
                    else:
                        prevent_line = True
                        outcome = msg
                else:
                    prevent_line = True
                    outcome = gettext('lims_instrument.msg_professionals',
                        code=str(line.imported_professionals))

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
                new_professionals.extend(line_new_professionals)
                columns.append(sql_table.imported_result)
                values.append(Null)
                columns.append(sql_table.imported_literal_result)
                values.append(Null)
                columns.append(sql_table.imported_end_date)
                values.append(Null)
                columns.append(sql_table.imported_professionals)
                values.append(Null)
                columns.append(sql_table.imported_chromatogram)
                values.append(Null)
                columns.append(sql_table.imported_device)
                values.append(Null)
                columns.append(sql_table.imported_dilution_factor)
                values.append(Null)
                columns.append(sql_table.imported_rm_correction_formula)
                values.append(Null)
                columns.append(sql_table.imported_inj_date)
                values.append(Null)
                columns.append(sql_table.imported_trace_report)
                values.append(Literal(False))
                # Write Results to Notebook lines
                cursor.execute(*sql_table.update(
                    columns, values,
                    where=(sql_table.id == line.id)))

        # Update Professionals
        AnalyticProfessional.delete(previous_professionals)
        AnalyticProfessional.create(new_professionals)

        if warnings:
            self.warning.msg = messages
            return 'warning'
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
            'imported_trace_report': False,
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
