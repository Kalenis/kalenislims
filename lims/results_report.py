# -*- coding: utf-8 -*-
# This file is part of lims module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from io import BytesIO
from datetime import datetime
from PyPDF2 import PdfFileMerger

from trytond.model import Workflow, ModelView, ModelSQL, fields
from trytond.wizard import Wizard, StateTransition, StateView, StateAction, \
    StateReport, Button
from trytond.pool import Pool
from trytond.pyson import PYSONEncoder, Eval, Equal, Bool, Not, Or, If
from trytond.transaction import Transaction
from trytond.report import Report
from trytond.rpc import RPC
from trytond.exceptions import UserError
from trytond.i18n import gettext
from .configuration import get_print_date
from .notebook import NotebookLineRepeatAnalysis


class ResultsReport(ModelSQL, ModelView):
    'Results Report'
    __name__ = 'lims.results_report'
    _rec_name = 'number'

    number = fields.Char('Number', select=True, readonly=True)
    versions = fields.One2Many('lims.results_report.version',
        'results_report', 'Laboratories', readonly=True)
    party = fields.Many2One('party.party', 'Party', readonly=True)
    invoice_party = fields.Function(fields.Many2One('party.party',
        'Invoice party'), 'get_entry_field',
        searcher='search_entry_field')
    entry = fields.Many2One('lims.entry', 'Entry', select=True, readonly=True)
    notebook = fields.Many2One('lims.notebook', 'Laboratory notebook')
    report_grouper = fields.Integer('Report Grouper')
    generation_type = fields.Char('Generation type')
    cie_fraction_type = fields.Boolean('QA', readonly=True)
    english_report = fields.Boolean('English report')
    single_sending_report = fields.Function(fields.Boolean(
        'Single sending'), 'get_entry_field',
        searcher='search_entry_field')
    single_sending_report_ready = fields.Function(fields.Boolean(
        'Single sending Ready'), 'get_single_sending_report_ready')
    ready_to_send = fields.Function(fields.Boolean(
        'Ready to Send'), 'get_ready_to_send',
        searcher='search_ready_to_send')
    create_date2 = fields.Function(fields.DateTime('Create Date'),
       'get_create_date2', searcher='search_create_date2')
    write_date2 = fields.DateTime('Write Date', readonly=True)
    attachments = fields.One2Many('ir.attachment', 'resource', 'Attachments')
    samples_list = fields.Function(fields.Char('Samples'),
        'get_samples_list', searcher='search_samples_list')

    # PDF Report Cache
    report_cache = fields.Binary('Report cache', readonly=True,
        file_id='report_cache_id', store_prefix='results_report')
    report_cache_id = fields.Char('Report cache id', readonly=True)
    report_format = fields.Char('Report format', readonly=True)
    report_cache_eng = fields.Binary('Report cache', readonly=True,
        file_id='report_cache_eng_id', store_prefix='results_report')
    report_cache_eng_id = fields.Char('Report cache id', readonly=True)
    report_format_eng = fields.Char('Report format', readonly=True)

    @classmethod
    def __register__(cls, module_name):
        table_h = cls.__table_handler__(module_name)
        notebook_exist = table_h.column_exist('notebook')
        entry_exist = table_h.column_exist('entry')
        super().__register__(module_name)
        if notebook_exist and not entry_exist:
            cursor = Transaction().connection.cursor()
            cursor.execute('UPDATE "lims_results_report" r '
                'SET entry = s.entry '
                'FROM "lims_sample" s '
                'INNER JOIN "lims_fraction" f ON s.id = f.sample '
                'INNER JOIN "lims_notebook" n ON f.id = n.fraction '
                'WHERE r.notebook = n.id')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order.insert(0, ('number', 'DESC'))

    @staticmethod
    def default_report_grouper():
        return 0

    @classmethod
    def create(cls, vlist):
        pool = Pool()
        LabWorkYear = pool.get('lims.lab.workyear')
        Sequence = pool.get('ir.sequence')

        workyear_id = LabWorkYear.find()
        workyear = LabWorkYear(workyear_id)
        sequence = workyear.get_sequence('results_report')
        if not sequence:
            raise UserError(gettext('lims.msg_no_sequence',
                work_year=workyear.rec_name))

        vlist = [x.copy() for x in vlist]
        for values in vlist:
            values['number'] = Sequence.get_id(sequence.id)
        return super().create(vlist)

    @classmethod
    def write(cls, *args):
        actions = iter(args)
        for reports, vals in zip(actions, actions):
            fields_check = cls._get_modified_fields()
            for field in fields_check:
                if field in vals:
                    vals['write_date2'] = datetime.now()
                    break
        super().write(*args)

    @staticmethod
    def _get_modified_fields():
        return [
            'number',
            'versions',
            'party',
            'entry',
            'notebook',
            'report_grouper',
            'generation_type',
            'cie_fraction_type',
            'english_report',
            'attachments',
            ]

    @classmethod
    def get_entry_field(cls, reports, names):
        result = {}
        for name in names:
            result[name] = {}
            if cls._fields[name]._type == 'many2one':
                for r in reports:
                    field = r.entry and getattr(r.entry, name, None) or None
                    result[name][r.id] = field.id if field else None
            elif cls._fields[name]._type == 'boolean':
                for r in reports:
                    result[name][r.id] = r.entry and getattr(
                        r.entry, name, False) or False
            else:
                for r in reports:
                    result[name][r.id] = r.entry and getattr(
                        r.entry, name, None) or None
        return result

    @classmethod
    def search_entry_field(cls, name, clause):
        return [('entry.' + name,) + tuple(clause[1:])]

    @classmethod
    def get_single_sending_report_ready(cls, reports, name):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        NotebookLine = pool.get('lims.notebook.line')
        Notebook = pool.get('lims.notebook')
        ResultsSample = pool.get('lims.results_report.version.detail.sample')
        ResultsDetail = pool.get('lims.results_report.version.detail')
        ResultsVersion = pool.get('lims.results_report.version')

        result = {}
        for r in reports:
            result[r.id] = False
            if not r.single_sending_report:
                continue
            cursor.execute('SELECT COUNT(*) '
                'FROM "' + EntryDetailAnalysis._table + '" ad '
                    'INNER JOIN "' + NotebookLine._table + '" nl '
                    'ON ad.id = nl.analysis_detail '
                    'INNER JOIN "' + Notebook._table + '" n '
                    'ON n.id = nl.notebook '
                    'INNER JOIN "' + ResultsSample._table + '" rs '
                    'ON n.id = rs.notebook '
                    'INNER JOIN "' + ResultsDetail._table + '" rd '
                    'ON rs.version_detail = rd.id '
                    'INNER JOIN "' + ResultsVersion._table + '" rv '
                    'ON rd.report_version = rv.id '
                'WHERE rv.results_report = %s '
                    'AND ad.report_grouper = %s '
                    'AND nl.report = TRUE '
                    'AND nl.annulled = FALSE '
                    'AND nl.results_report IS NULL',
                (r.id, r.report_grouper,))
            if cursor.fetchone()[0] > 0:
                continue
            result[r.id] = True
        return result

    @classmethod
    def get_ready_to_send(cls, reports, name):
        result = {}
        for r in reports:
            result[r.id] = False
            if r.single_sending_report and not r.single_sending_report_ready:
                continue
            spanish_report = r.has_report_cached(english_report=False)
            english_report = r.has_report_cached(english_report=True)
            if not spanish_report and not english_report:
                continue
            result[r.id] = True
        return result

    @classmethod
    def search_ready_to_send(cls, name, clause):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Entry = pool.get('lims.entry')
        ResultsReport = pool.get('lims.results_report')
        ResultsVersion = pool.get('lims.results_report.version')
        ResultsDetail = pool.get('lims.results_report.version.detail')

        excluded_ids = []
        cursor.execute('SELECT r.id '
            'FROM "' + ResultsReport._table + '" r '
                'INNER JOIN "' + Entry._table + '" e '
                'ON r.entry = e.id '
            'WHERE e.single_sending_report = TRUE')
        single_sending_ids = [x[0] for x in cursor.fetchall()]
        with Transaction().set_user(0):
            for report in ResultsReport.browse(single_sending_ids):
                if not report.single_sending_report_ready:
                    excluded_ids.append(report.id)
        excluded_ids = ', '.join(str(r) for r in [0] + excluded_ids)

        cursor.execute('SELECT rv.results_report '
            'FROM "' + ResultsDetail._table + '" rd '
                'INNER JOIN "' + ResultsVersion._table + '" rv '
                'ON rd.report_version = rv.id '
            'WHERE rd.valid = TRUE '
                'AND (rd.report_format = \'pdf\' '
                'OR rd.report_format_eng = \'pdf\') '
                'AND rv.results_report NOT IN (' + excluded_ids + ') ')
        ready_ids = [x[0] for x in cursor.fetchall()]

        field, op, operand = clause
        if (op, operand) in (('=', True), ('!=', False)):
            return [('id', 'in', ready_ids)]
        elif (op, operand) in (('=', False), ('!=', True)):
            return [('id', 'not in', ready_ids)]
        return []

    def get_create_date2(self, name):
        return self.create_date.replace(microsecond=0)

    @classmethod
    def search_create_date2(cls, name, clause):
        cursor = Transaction().connection.cursor()
        operator_ = clause[1:2][0]
        cursor.execute('SELECT id '
                'FROM "' + cls._table + '" '
                'WHERE create_date' + operator_ + ' %s',
                clause[2:3])
        return [('id', 'in', [x[0] for x in cursor.fetchall()])]

    @classmethod
    def order_create_date2(cls, tables):
        return cls.create_date.convert_order('create_date', tables, cls)

    def has_report_cached(self, english_report=False):
        '''
        Has Report Cached
        :english_report: boolean
        :return: boolean
        '''
        return bool(self._get_details_cached(english_report))

    def details_cached(self, english_report=False):
        '''
        Details Cached
        :english_report: boolean
        :return: list of details
        '''
        pool = Pool()
        ResultsDetail = pool.get('lims.results_report.version.detail')
        with Transaction().set_user(0):
            return ResultsDetail.browse(
                self._get_details_cached(english_report))

    def _get_details_cached(self, english_report=False):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        ResultsDetail = pool.get('lims.results_report.version.detail')
        ResultsVersion = pool.get('lims.results_report.version')

        format_field = 'report_format'
        if english_report:
            format_field = 'report_format_eng'

        cursor.execute('SELECT rd.id '
            'FROM "' + ResultsDetail._table + '" rd '
                'INNER JOIN "' + ResultsVersion._table + '" rv '
                'ON rd.report_version = rv.id '
            'WHERE rv.results_report = %s '
                'AND rd.valid = TRUE '
                'AND rd.' + format_field + ' = \'pdf\'',
            (self.id,))
        return [x[0] for x in cursor.fetchall()]

    @classmethod
    def get_samples_list(cls, reports, name):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Sample = pool.get('lims.sample')
        Fraction = pool.get('lims.fraction')
        Notebook = pool.get('lims.notebook')
        ResultsSample = pool.get('lims.results_report.version.detail.sample')
        ResultsDetail = pool.get('lims.results_report.version.detail')
        ResultsVersion = pool.get('lims.results_report.version')

        result = {}
        for r in reports:
            result[r.id] = ''
            cursor.execute('SELECT DISTINCT(s.number) '
                'FROM "' + Sample._table + '" s '
                    'INNER JOIN "' + Fraction._table + '" f '
                    'ON s.id = f.sample '
                    'INNER JOIN "' + Notebook._table + '" n '
                    'ON f.id = n.fraction '
                    'INNER JOIN "' + ResultsSample._table + '" rs '
                    'ON n.id = rs.notebook '
                    'INNER JOIN "' + ResultsDetail._table + '" rd '
                    'ON rs.version_detail = rd.id '
                    'INNER JOIN "' + ResultsVersion._table + '" rv '
                    'ON rd.report_version = rv.id '
                'WHERE rv.results_report = %s '
                    'AND rd.state != \'annulled\' '
                'ORDER BY s.number', (r.id,))
            samples = [x[0] for x in cursor.fetchall()]
            if samples:
                result[r.id] = ', '.join(samples)
        return result

    @classmethod
    def search_samples_list(cls, name, clause):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Sample = pool.get('lims.sample')
        Fraction = pool.get('lims.fraction')
        Notebook = pool.get('lims.notebook')
        ResultsSample = pool.get('lims.results_report.version.detail.sample')
        ResultsDetail = pool.get('lims.results_report.version.detail')
        ResultsVersion = pool.get('lims.results_report.version')

        value = clause[2]
        cursor.execute('SELECT rv.results_report '
            'FROM "' + Sample._table + '" s '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON s.id = f.sample '
                'INNER JOIN "' + Notebook._table + '" n '
                'ON f.id = n.fraction '
                'INNER JOIN "' + ResultsSample._table + '" rs '
                'ON n.id = rs.notebook '
                'INNER JOIN "' + ResultsDetail._table + '" rd '
                'ON rs.version_detail = rd.id '
                'INNER JOIN "' + ResultsVersion._table + '" rv '
                'ON rd.report_version = rv.id '
            'WHERE s.number ILIKE %s '
                'AND rd.state != \'annulled\'',
            (value,))
        details_ids = [x[0] for x in cursor.fetchall()]
        if not details_ids:
            return [('id', '=', -1)]
        return [('id', 'in', details_ids)]


class ResultsReportVersion(ModelSQL, ModelView):
    'Results Report Version'
    __name__ = 'lims.results_report.version'
    _rec_name = 'number'

    results_report = fields.Many2One('lims.results_report', 'Results Report',
        required=True, ondelete='CASCADE', select=True)
    number = fields.Char('Number', select=True, readonly=True)
    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        required=True, readonly=True)
    details = fields.One2Many('lims.results_report.version.detail',
        'report_version', 'Detail lines', readonly=True)
    report_type = fields.Function(fields.Char('Report type'),
        'get_report_type')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order.insert(0, ('number', 'DESC'))

    def get_report_type(self, name):
        ResultsDetail = Pool().get('lims.results_report.version.detail')
        valid_detail = ResultsDetail.search([
            ('report_version.id', '=', self.id),
            ], order=[('id', 'DESC')], limit=1)
        if valid_detail:
            return valid_detail[0].report_type
        return None

    @classmethod
    def get_number(cls, results_report_id, laboratory_id):
        pool = Pool()
        ResultsReport = pool.get('lims.results_report')
        Laboratory = pool.get('lims.laboratory')

        with Transaction().set_user(0):
            results_reports = ResultsReport.search([
                ('id', '=', results_report_id),
                ])
        report_number = results_reports[0].number

        laboratories = Laboratory.search([
            ('id', '=', laboratory_id),
            ])
        laboratory_code = laboratories[0].code

        return '%s-%s' % (report_number, laboratory_code)

    @classmethod
    def create(cls, vlist):
        vlist = [x.copy() for x in vlist]
        for values in vlist:
            values['number'] = cls.get_number(values['results_report'],
                values['laboratory'])
        return super().create(vlist)


class ResultsReportVersionDetail(Workflow, ModelSQL, ModelView):
    'Results Report Version Detail'
    __name__ = 'lims.results_report.version.detail'

    _states = {'readonly': Eval('state') != 'draft'}
    _depends = ['state']

    report_version = fields.Many2One('lims.results_report.version',
        'Report', required=True, readonly=True,
        ondelete='CASCADE', select=True)
    laboratory = fields.Function(fields.Many2One('lims.laboratory',
        'Laboratory'), 'get_version_field', searcher='search_version_field')
    number = fields.Char('Version', select=True, readonly=True)
    valid = fields.Boolean('Active', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('revised', 'Revised'),
        ('released', 'Released'),
        ('annulled', 'Annulled'),
        ], 'State', readonly=True)
    type = fields.Selection([
        ('preliminary', 'Preliminary'),
        ('final', 'Final'),
        ('complementary', 'Complementary'),
        ('corrective', 'Corrective'),
        ], 'Type', readonly=True)
    type_string = type.translated('type')
    samples = fields.One2Many('lims.results_report.version.detail.sample',
        'version_detail', 'Samples', states=_states, depends=_depends)
    party = fields.Function(fields.Many2One('party.party', 'Party'),
       'get_report_field', searcher='search_report_field')
    invoice_party = fields.Function(fields.Many2One('party.party',
        'Invoice party'), 'get_entry_field', searcher='search_entry_field')
    signer = fields.Many2One('lims.laboratory.professional', 'Signer',
        domain=[('id', 'in', Eval('signer_domain'))],
        states=_states, depends=['state', 'signer_domain'])
    signer_domain = fields.Function(fields.Many2Many(
        'lims.laboratory.professional', None, None, 'Signer domain'),
        'on_change_with_signer_domain')
    resultrange_origin = fields.Many2One('lims.range.type', 'Origin',
        domain=[('use', '=', 'result_range')],
        depends=['report_result_type', 'state'],
        states={
            'invisible': Not(Eval('report_result_type').in_([
                'result_range', 'both_range'])),
            'required': Eval('report_result_type').in_([
                'result_range', 'both_range']),
            'readonly': Eval('state') != 'draft',
            })
    comments = fields.Text('Comments', translate=True, depends=_depends,
        states={'readonly': ~Eval('state').in_(['draft', 'revised'])})
    fractions_comments = fields.Function(fields.Text('Fractions comments'),
        'get_fractions_comments')
    cie_fraction_type = fields.Function(fields.Boolean('QA'),
       'get_report_field', searcher='search_report_field')
    date = fields.Function(fields.Date('Date'), 'get_date',
        searcher='search_date')
    create_date2 = fields.Function(fields.DateTime('Create Date'),
       'get_create_date2', searcher='search_create_date2')
    write_date2 = fields.Function(fields.DateTime('Write Date'),
       'get_write_date2', searcher='search_write_date2')
    icon = fields.Function(fields.Char('Icon'), 'get_icon')
    samples_list = fields.Function(fields.Char('Samples'),
        'get_samples_list', searcher='search_samples_list')
    entry_summary = fields.Function(fields.Char('Entry / Qty. Samples'),
        'get_entry_summary', searcher='search_entry_summary')

    # State changes
    revision_uid = fields.Many2One('res.user', 'Revision user', readonly=True)
    revision_date = fields.DateTime('Revision date', readonly=True)
    release_uid = fields.Many2One('res.user', 'Release user', readonly=True)
    release_date = fields.DateTime('Release date', readonly=True)
    review_reason = fields.Text('Review reason', translate=True,
        states={'readonly': True})
    review_reason_print = fields.Boolean(
        'Print review reason in next version',
        states={'readonly': True})
    annulment_uid = fields.Many2One('res.user', 'Annulment user',
        readonly=True)
    annulment_date = fields.DateTime('Annulment date', readonly=True)
    annulment_reason = fields.Text('Annulment reason', translate=True,
        states={'readonly': Eval('state') != 'annulled'}, depends=_depends)
    annulment_reason_print = fields.Boolean('Print annulment reason',
        states={'readonly': Eval('state') != 'annulled'}, depends=_depends)

    # Report format
    report_section = fields.Function(fields.Char('Section'),
        'get_report_section')
    report_type_forced = fields.Selection([
        ('none', 'None'),
        ('normal', 'Normal'),
        ('polisample', 'Polisample'),
        ], 'Forced Report type', sort=False,
        states=_states, depends=_depends)
    report_type = fields.Function(fields.Selection([
        ('normal', 'Normal'),
        ('polisample', 'Polisample'),
        ], 'Report type', sort=False), 'on_change_with_report_type')
    report_result_type_forced = fields.Selection([
        ('none', 'None'),
        ('result', 'Result'),
        ('both', 'Both'),
        ('result_range', 'Result and Ranges'),
        ('both_range', 'Both and Ranges'),
        ], 'Forced Result type', sort=False,
        states=_states, depends=_depends)
    report_result_type = fields.Function(fields.Selection([
        ('result', 'Result'),
        ('both', 'Both'),
        ('result_range', 'Result and Ranges'),
        ('both_range', 'Both and Ranges'),
        ], 'Result type', sort=False), 'on_change_with_report_result_type')
    english_report = fields.Function(fields.Boolean('English report'),
        'get_report_field', searcher='search_report_field')

    # PDF Report Cache
    report_cache = fields.Binary('Report cache', readonly=True,
        file_id='report_cache_id', store_prefix='results_report')
    report_cache_id = fields.Char('Report cache id', readonly=True)
    report_format = fields.Char('Report format', readonly=True)
    report_cache_eng = fields.Binary('Report cache', readonly=True,
        file_id='report_cache_eng_id', store_prefix='results_report')
    report_cache_eng_id = fields.Char('Report cache id', readonly=True)
    report_format_eng = fields.Char('Report format', readonly=True)

    # ODT Report Cache
    report_cache_odt = fields.Binary('Transcription Report cache',
        readonly=True, file_id='report_cache_odt_id',
        store_prefix='results_report')
    report_cache_odt_id = fields.Char('Transcription Report cache id',
        readonly=True)
    report_format_odt = fields.Char('Transcription Report format',
        readonly=True)
    report_cache_odt_eng = fields.Binary('Transcription Report cache',
        readonly=True, file_id='report_cache_odt_eng_id',
        store_prefix='results_report')
    report_cache_odt_eng_id = fields.Char('Transcription Report cache id',
        readonly=True)
    report_format_odt_eng = fields.Char('Transcription Report format',
        readonly=True)

    del _states, _depends

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order.insert(0, ('report_version', 'DESC'))
        cls._order.insert(1, ('number', 'DESC'))
        cls._transitions = set((
            ('draft', 'revised'),
            ('revised', 'draft'),
            ('revised', 'released'),
            ('released', 'annulled'),
            ))
        cls._buttons.update({
            'draft': {
                'invisible': Eval('state') != 'revised',
                'depends': ['state'],
                },
            'revise': {
                'invisible': Eval('state') != 'draft',
                'depends': ['state'],
                },
            'release': {
                'invisible': Eval('state') != 'revised',
                'depends': ['state'],
                },
            'release_all_lang': {
                'invisible': If(Bool(Eval('english_report')),
                    Bool(Or(
                        Eval('state') != 'released',
                        Bool(Eval('report_cache_eng')),
                        Bool(Eval('report_cache_eng_id')),
                        )),
                    Bool(Or(
                        Eval('state') != 'released',
                        Bool(Eval('report_cache')),
                        Bool(Eval('report_cache_id')),
                        )),
                    ),
                'depends': ['english_report', 'state',
                    'report_cache', 'report_cache_id',
                    'report_cache_eng', 'report_cache_eng_id'],
                },
            'annul': {
                'invisible': Or(Eval('state') != 'released', ~Eval('valid')),
                'depends': ['state', 'valid'],
                },
            'new_version': {
                'invisible': Or(Eval('state') != 'released', ~Eval('valid')),
                'depends': ['state', 'valid'],
                },
            })

    @classmethod
    def __register__(cls, module_name):
        cursor = Transaction().connection.cursor()
        super().__register__(module_name)
        cursor.execute('UPDATE "' + cls._table + '" '
            'SET state = \'released\' '
            'WHERE state = \'revised\' '
                'AND (report_cache_id IS NOT NULL OR '
                'report_cache_eng_id IS NOT NULL)')

    @staticmethod
    def default_valid():
        return False

    @staticmethod
    def default_state():
        return 'draft'

    @staticmethod
    def default_type():
        return 'final'

    @staticmethod
    def default_annulment_reason_print():
        return True

    @staticmethod
    def default_report_type_forced():
        return 'none'

    @staticmethod
    def default_report_result_type_forced():
        return 'none'

    @classmethod
    def get_next_number(cls, report_version_id, d_count):
        detail_number = cls.search_count([
            ('report_version', '=', report_version_id),
            ])
        detail_number += d_count
        return '%s' % detail_number

    @classmethod
    def create(cls, vlist):
        vlist = [x.copy() for x in vlist]
        d_count = {}
        for values in vlist:
            key = values['report_version']
            if key not in d_count:
                d_count[key] = 0
            d_count[key] += 1
            values['number'] = cls.get_next_number(key, d_count[key])
        return super().create(vlist)

    def get_rec_name(self, name):
        return '%s-%s' % (self.report_version.number, self.number)

    def get_report_section(self, name):
        if self.laboratory:
            return self.laboratory.section
        return None

    @fields.depends('samples', 'report_type_forced')
    def on_change_with_report_type(self, name=None):
        if len(self.samples) > 1:
            return 'polisample'
        if self.report_type_forced != 'none':
            return self.report_type_forced
        report_type = {
            'normal': 0,
            'polisample': 0,
            }
        cursor = Transaction().connection.cursor()

        cursor.execute('SELECT COUNT(*), t.report_type '
            'FROM lims_results_report_version_detail_sample sd, '
            'lims_results_report_version_detail_l d, '
            'lims_notebook_line l, lims_typification t, '
            'lims_notebook n, lims_fraction f, lims_sample s '
            'WHERE sd.version_detail = %s '
                'AND d.detail_sample = sd.id '
                'AND d.notebook_line = l.id '
                'AND s.product_type = t.product_type '
                'AND s.matrix = t.matrix '
                'AND l.analysis = t.analysis '
                'AND l.method = t.method '
                'AND t.valid = true '
                'AND l.notebook = n.id '
                'AND n.fraction = f.id '
                'AND f.sample = s.id '
            'GROUP BY t.report_type',
            (self.id, ))
        res = cursor.fetchall()
        for type_ in res:
            if type_[0]:
                report_type[type_[1]] = type_[0]

        if report_type['polisample'] > report_type['normal']:
            return 'polisample'
        return 'normal'

    @fields.depends('report_result_type_forced')
    def on_change_with_report_result_type(self, name=None):
        if self.report_result_type_forced != 'none':
            return self.report_result_type_forced
        report_res_type = {
            'result': 0,
            'both': 0,
            }
        cursor = Transaction().connection.cursor()

        cursor.execute('SELECT COUNT(*), t.report_result_type '
            'FROM lims_results_report_version_detail_sample sd, '
            'lims_results_report_version_detail_l d, '
            'lims_notebook_line l, lims_typification t, '
            'lims_notebook n, lims_fraction f, lims_sample s '
            'WHERE sd.version_detail = %s '
                'AND d.detail_sample = sd.id '
                'AND d.notebook_line = l.id '
                'AND s.product_type = t.product_type '
                'AND s.matrix = t.matrix '
                'AND l.analysis = t.analysis '
                'AND l.method = t.method '
                'AND t.valid = true '
                'AND l.notebook = n.id '
                'AND n.fraction = f.id '
                'AND f.sample = s.id '
            'GROUP BY t.report_result_type',
            (self.id, ))
        res = cursor.fetchall()
        for type_ in res:
            if type_[0]:
                report_res_type[type_[1]] = type_[0]

        if report_res_type['both'] > report_res_type['result']:
            return 'both'
        return 'result'

    @fields.depends('report_result_type_forced', 'resultrange_origin')
    def on_change_report_result_type_forced(self):
        pool = Pool()
        RangeType = pool.get('lims.range.type')

        if ((self.report_result_type_forced == 'result_range' or
                self.report_result_type_forced == 'both_range') and
                not self.resultrange_origin):
            ranges = RangeType.search([
                ('use', '=', 'result_range'),
                ('by_default', '=', True),
                ])
            if ranges:
                self.resultrange_origin = ranges[0].id

    @fields.depends('laboratory')
    def on_change_with_signer_domain(self, name=None):
        pool = Pool()
        UserLaboratory = pool.get('lims.user-laboratory')
        LaboratoryProfessional = pool.get('lims.laboratory.professional')

        if not self.laboratory:
            return []
        users = UserLaboratory.search([
            ('laboratory', '=', self.laboratory.id),
            ])
        if not users:
            return []
        professionals = LaboratoryProfessional.search([
            ('party.lims_user', 'in', [u.user.id for u in users]),
            ('role', '!=', ''),
            ])
        if not professionals:
            return []
        return [p.id for p in professionals]

    @classmethod
    @ModelView.button
    @Workflow.transition('draft')
    def draft(cls, details):
        pass

    @classmethod
    @ModelView.button
    @Workflow.transition('revised')
    def revise(cls, details):
        cls.write(details, {
            'revision_uid': int(Transaction().user),
            'revision_date': datetime.now(),
            })

    @classmethod
    @ModelView.button
    @Workflow.transition('released')
    def release(cls, details):
        ResultsSample = Pool().get('lims.results_report.version.detail.sample')
        for detail in details:
            # delete samples from previous valid version
            old_samples = ResultsSample.search([
                ('version_detail.report_version', '=',
                    detail.report_version.id),
                ('version_detail.valid', '=', True),
                ])
            ResultsSample.delete(old_samples)

            # invalidate previous valid version
            valid_details = cls.search([
                ('report_version', '=', detail.report_version.id),
                ('valid', '=', True),
                ])
            cls.write(valid_details, {'valid': False})

            cls.write([detail], {
                'valid': True,
                'release_uid': int(Transaction().user),
                'release_date': datetime.now(),
                })
        cls.do_release(details)

    @classmethod
    def do_release(cls, details):
        Sample = Pool().get('lims.sample')
        cls.link_notebook_lines(details)
        for detail in details:
            detail.generate_report()
            sample_ids = list(set(s.notebook.fraction.sample.id for
                s in detail.samples))
            Sample.update_samples_state(sample_ids)

    @classmethod
    def link_notebook_lines(cls, details):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        ResultsSample = pool.get('lims.results_report.version.detail.sample')
        ResultsLine = pool.get('lims.results_report.version.detail.line')
        NotebookLine = pool.get('lims.notebook.line')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        for detail in details:
            if detail.type == 'preliminary':
                continue
            linked_lines = []
            linked_entry_details = []
            cursor.execute('SELECT nl.id, nl.analysis_detail '
                'FROM "' + NotebookLine._table + '" nl '
                    'INNER JOIN "' + ResultsLine._table + '" rl '
                    'ON nl.id = rl.notebook_line '
                    'INNER JOIN "' + ResultsSample._table + '" rs '
                    'ON rl.detail_sample = rs.id '
                'WHERE rs.version_detail = %s',
                (detail.id,))
            for x in cursor.fetchall():
                linked_lines.append(x[0])
                linked_entry_details.append(x[1])

            notebook_lines = NotebookLine.search([
                ('id', 'in', linked_lines),
                ])
            if notebook_lines:
                NotebookLine.write(notebook_lines, {
                    'results_report': detail.report_version.results_report.id,
                    })

            entry_details = EntryDetailAnalysis.search([
                ('id', 'in', linked_entry_details),
                ])
            if entry_details:
                EntryDetailAnalysis.write(entry_details, {
                    'state': 'reported',
                    })

    @classmethod
    def update_from_valid_version(cls, details):
        ResultsSample = Pool().get('lims.results_report.version.detail.sample')

        for detail in details:
            valid_details = cls.search([
                ('id', '!=', detail.id),
                ('report_version', '=', detail.report_version.id),
                ('valid', '=', True),
                ], limit=1)
            if not valid_details:
                continue
            valid_detail = valid_details[0]

            detail_default = cls._get_fields_from_detail(valid_detail)
            if detail.type == 'final' and valid_detail.type != 'preliminary':
                detail_default['type'] = 'complementary'
            cls.write([detail], detail_default)

            # copy samples from previous valid version
            only_accepted = (detail.type != 'preliminary')
            for valid_sample in valid_detail.samples:
                sample_default = ResultsSample._get_fields_from_sample(
                    valid_sample, only_accepted)
                existing_sample = ResultsSample.search([
                    ('version_detail', '=', detail.id),
                    ('notebook', '=', valid_sample.notebook.id),
                    ], limit=1)
                if not existing_sample:
                    sample_default['version_detail'] = detail.id
                    sample_default['notebook'] = valid_sample.notebook.id
                    ResultsSample.create([sample_default])
                else:
                    ResultsSample.write(existing_sample, sample_default)

    @classmethod
    def _get_fields_from_detail(cls, detail):
        detail_default = {}
        detail_default['report_type_forced'] = detail.report_type_forced
        detail_default['report_result_type_forced'] = (
            detail.report_result_type_forced)
        if detail.signer:
            detail_default['signer'] = detail.signer.id
        if detail.resultrange_origin:
            detail_default['resultrange_origin'] = detail.resultrange_origin.id
        detail_default['comments'] = str(detail.comments or '')
        return detail_default

    @classmethod
    @ModelView.button
    def release_all_lang(cls, details):
        for detail in details:
            detail.generate_report()

    def generate_report(self):
        pool = Pool()
        ResultReport = pool.get('lims.result_report', type='report')
        ResultReportTranscription = pool.get(
            'lims.result_report.transcription', type='report')

        ResultReport.execute([self.id], {
            'english_report': self.english_report,
            })
        ResultReportTranscription.execute([self.id], {
            'english_report': self.english_report,
            })

    @classmethod
    @ModelView.button_action('lims.wiz_lims_results_report_annulation')
    def annul(cls, details):
        pass

    @classmethod
    def unlink_notebook_lines(cls, details):
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        for detail in details:
            unlinked_lines = []
            unlinked_entry_details = []
            for sample in detail.samples:
                for nline in sample.notebook_lines:
                    if not nline.notebook_line:
                        continue
                    unlinked_lines.append(nline.notebook_line.id)
                    unlinked_entry_details.append(
                        nline.notebook_line.analysis_detail.id)

            notebook_lines = NotebookLine.search([
                ('id', 'in', unlinked_lines),
                ('results_report', '=',
                    detail.report_version.results_report.id),
                ])
            if notebook_lines:
                NotebookLine.write(notebook_lines, {
                    'results_report': None,
                    })

            entry_details = EntryDetailAnalysis.search([
                ('id', 'in', unlinked_entry_details),
                ])
            if entry_details:
                EntryDetailAnalysis.write(entry_details, {
                    'state': 'done',
                    })

    @classmethod
    @ModelView.button_action(
        'lims.wiz_results_report_version_detail_new_version')
    def new_version(cls, details):
        pass

    def get_date(self, name):
        pool = Pool()
        Company = pool.get('company.company')

        date = self.write_date if self.write_date else self.create_date
        company_id = Transaction().context.get('company')
        if company_id:
            date = Company(company_id).convert_timezone_datetime(date)
        return date.date()

    @classmethod
    def search_date(cls, name, clause):
        pool = Pool()
        Company = pool.get('company.company')
        cursor = Transaction().connection.cursor()

        timezone = None
        company_id = Transaction().context.get('company')
        if company_id:
            timezone = Company(company_id).timezone
        timezone_datetime = ('COALESCE(write_date, create_date)::timestamp'
            ' AT TIME ZONE \'UTC\'')
        if timezone:
            timezone_datetime += ' AT TIME ZONE \'' + timezone + '\''

        operator_ = clause[1:2][0]
        cursor.execute('SELECT id '
                'FROM "' + cls._table + '" '
                'WHERE (' + timezone_datetime + ')::date ' +
                operator_ + ' %s::date', clause[2:3])
        return [('id', 'in', [x[0] for x in cursor.fetchall()])]

    @classmethod
    def get_version_field(cls, details, names):
        result = {}
        for name in names:
            result[name] = {}
            for d in details:
                field = getattr(d.report_version, name, None)
                result[name][d.id] = field.id if field else None
        return result

    @classmethod
    def search_version_field(cls, name, clause):
        return [('report_version.' + name,) + tuple(clause[1:])]

    @classmethod
    def get_report_field(cls, details, names):
        result = {}
        for name in names:
            result[name] = {}
            if name in ('cie_fraction_type', 'english_report'):
                for d in details:
                    field = getattr(d.report_version.results_report, name,
                        False)
                    result[name][d.id] = field
            else:
                for d in details:
                    field = getattr(d.report_version.results_report, name,
                        None)
                    result[name][d.id] = field.id if field else None
        return result

    @classmethod
    def search_report_field(cls, name, clause):
        return [('report_version.results_report.' + name,) + tuple(clause[1:])]

    @classmethod
    def get_entry_field(cls, details, names):
        result = {}
        for name in names:
            result[name] = {}
            if cls._fields[name]._type == 'many2one':
                for d in details:
                    field = (d.report_version.results_report.entry and
                        getattr(d.report_version.results_report.entry,
                            name, None) or None)
                    result[name][d.id] = field.id if field else None
            elif cls._fields[name]._type == 'boolean':
                    field = (d.report_version.results_report.entry and
                        getattr(d.report_version.results_report.entry,
                            name, False) or False)
                    result[name][d.id] = field
            else:
                for d in details:
                    field = (d.report_version.results_report.entry and
                        getattr(d.report_version.results_report.entry,
                            name, None) or None)
                    result[name][d.id] = field
        return result

    @classmethod
    def search_entry_field(cls, name, clause):
        return [('report_version.results_report.entry.' + name,) +
            tuple(clause[1:])]

    @classmethod
    def get_create_date2(cls, details, name):
        result = {}
        for d in details:
            create_date = getattr(d, 'create_date', None)
            result[d.id] = (create_date.replace(microsecond=0)
                if create_date else None)
        return result

    @classmethod
    def search_create_date2(cls, name, clause):
        cursor = Transaction().connection.cursor()
        operator_ = clause[1:2][0]
        cursor.execute('SELECT id '
                'FROM "' + cls._table + '" '
                'WHERE create_date' + operator_ + ' %s',
                clause[2:3])
        return [('id', 'in', [x[0] for x in cursor.fetchall()])]

    @classmethod
    def order_create_date2(cls, tables):
        return cls.create_date.convert_order('create_date', tables, cls)

    @classmethod
    def get_write_date2(cls, details, name):
        result = {}
        for d in details:
            write_date = getattr(d, 'write_date', None)
            result[d.id] = (write_date.replace(microsecond=0)
                if write_date else None)
        return result

    @classmethod
    def search_write_date2(cls, name, clause):
        cursor = Transaction().connection.cursor()
        operator_ = clause[1:2][0]
        cursor.execute('SELECT id '
                'FROM "' + cls._table + '" '
                'WHERE write_date' + operator_ + ' %s',
                clause[2:3])
        return [('id', 'in', [x[0] for x in cursor.fetchall()])]

    @classmethod
    def order_write_date2(cls, tables):
        return cls.write_date.convert_order('write_date', tables, cls)

    @classmethod
    def delete(cls, details):
        cls.check_delete(details)
        super().delete(details)

    @classmethod
    def check_delete(cls, details):
        for detail in details:
            if detail.state != 'draft':
                raise UserError(gettext('lims.msg_delete_detail_not_draft'))

    @classmethod
    def get_fractions_comments(cls, details, name):
        result = {}
        for d in details:
            comments = []
            for sample in d.samples:
                fraction_comments = sample.notebook.fraction_comments
                if fraction_comments:
                    comments.append(fraction_comments)
            result[d.id] = comments and '\n'.join(comments) or None
        return result

    def get_icon(self, name):
        if self.fractions_comments:
            return 'lims-blue'
        return 'lims-white'

    @classmethod
    def _get_fields_from_samples(cls, samples):
        detail_default = {}
        if len(samples) > 1:
            detail_default['report_type_forced'] = 'polisample'
        else:
            detail_default['report_type_forced'] = 'normal'
        return detail_default

    @classmethod
    def _get_fields_not_overwrite(cls):
        fields = ['type', 'signer', 'samples']
        return fields

    @classmethod
    def get_samples_list(cls, details, name):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Sample = pool.get('lims.sample')
        Fraction = pool.get('lims.fraction')
        Notebook = pool.get('lims.notebook')
        ResultsSample = pool.get('lims.results_report.version.detail.sample')

        result = {}
        for d in details:
            result[d.id] = ''
            cursor.execute('SELECT DISTINCT(s.number) '
                'FROM "' + Sample._table + '" s '
                    'INNER JOIN "' + Fraction._table + '" f '
                    'ON s.id = f.sample '
                    'INNER JOIN "' + Notebook._table + '" n '
                    'ON f.id = n.fraction '
                    'INNER JOIN "' + ResultsSample._table + '" rs '
                    'ON n.id = rs.notebook '
                'WHERE rs.version_detail = %s '
                'ORDER BY s.number', (d.id,))
            samples = [x[0] for x in cursor.fetchall()]
            if samples:
                result[d.id] = ', '.join(samples)
        return result

    @classmethod
    def search_samples_list(cls, name, clause):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Sample = pool.get('lims.sample')
        Fraction = pool.get('lims.fraction')
        Notebook = pool.get('lims.notebook')
        ResultsSample = pool.get('lims.results_report.version.detail.sample')

        value = clause[2]
        cursor.execute('SELECT rs.version_detail '
            'FROM "' + Sample._table + '" s '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON s.id = f.sample '
                'INNER JOIN "' + Notebook._table + '" n '
                'ON f.id = n.fraction '
                'INNER JOIN "' + ResultsSample._table + '" rs '
                'ON n.id = rs.notebook '
            'WHERE s.number ILIKE %s',
            (value,))
        details_ids = [x[0] for x in cursor.fetchall()]
        if not details_ids:
            return [('id', '=', -1)]
        return [('id', 'in', details_ids)]

    @classmethod
    def get_entry_summary(cls, details, name):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Entry = pool.get('lims.entry')
        Sample = pool.get('lims.sample')
        Fraction = pool.get('lims.fraction')
        Notebook = pool.get('lims.notebook')
        ResultsSample = pool.get('lims.results_report.version.detail.sample')

        result = {}
        for d in details:
            result[d.id] = ''

            cursor.execute('SELECT DISTINCT(s.entry) '
                'FROM "' + Sample._table + '" s '
                    'INNER JOIN "' + Fraction._table + '" f '
                    'ON s.id = f.sample '
                    'INNER JOIN "' + Notebook._table + '" n '
                    'ON f.id = n.fraction '
                    'INNER JOIN "' + ResultsSample._table + '" rs '
                    'ON n.id = rs.notebook '
                'WHERE rs.version_detail = %s', (d.id,))
            entry_ids = [x[0] for x in cursor.fetchall()]
            if not entry_ids:
                continue
            entry_ids = ', '.join(str(e) for e in entry_ids)

            cursor.execute('SELECT e.number, count(s.id) '
                'FROM "' + Entry._table + '" e '
                    'INNER JOIN "' + Sample._table + '" s '
                    'ON e.id = s.entry '
                'WHERE e.id IN (' + entry_ids + ') '
                'GROUP BY e.number')
            res = cursor.fetchone()
            if not res:
                continue
            result[d.id] = '%s/%s' % (res[0], res[1])
        return result

    @classmethod
    def search_entry_summary(cls, name, clause):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Entry = pool.get('lims.entry')
        Sample = pool.get('lims.sample')
        Fraction = pool.get('lims.fraction')
        Notebook = pool.get('lims.notebook')
        ResultsSample = pool.get('lims.results_report.version.detail.sample')

        value = clause[2]
        cursor.execute('SELECT rs.version_detail '
            'FROM "' + Entry._table + '" e '
                'INNER JOIN "' + Sample._table + '" s '
                'ON e.id = s.entry '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON s.id = f.sample '
                'INNER JOIN "' + Notebook._table + '" n '
                'ON f.id = n.fraction '
                'INNER JOIN "' + ResultsSample._table + '" rs '
                'ON n.id = rs.notebook '
            'WHERE e.number ILIKE %s',
            (value,))
        details_ids = [x[0] for x in cursor.fetchall()]
        if not details_ids:
            return [('id', '=', -1)]
        return [('id', 'in', details_ids)]


class ResultsReportVersionDetailSample(ModelSQL, ModelView):
    'Results Report Version Detail Sample'
    __name__ = 'lims.results_report.version.detail.sample'

    version_detail = fields.Many2One('lims.results_report.version.detail',
        'Report Detail', required=True, ondelete='CASCADE', select=True)
    notebook = fields.Many2One('lims.notebook', 'Notebook', required=True,
        readonly=True)
    notebook_lines = fields.One2Many('lims.results_report.version.detail.line',
        'detail_sample', 'Analysis')
    party = fields.Function(fields.Many2One('party.party', 'Party'),
        'get_notebook_field')
    invoice_party = fields.Function(fields.Many2One('party.party',
        'Invoice Party'), 'get_notebook_field')
    label = fields.Function(fields.Char('Label'), 'get_notebook_field')
    product_type = fields.Function(fields.Many2One('lims.product.type',
        'Product type'), 'get_notebook_field')
    matrix = fields.Function(fields.Many2One('lims.matrix', 'Matrix'),
        'get_notebook_field')
    sample_comments = fields.Function(fields.Text('Sample Comments'),
        'get_notebook_field')
    lines_not_reported = fields.Function(fields.One2Many(
        'lims.notebook.line', None, 'Not reported Lines'),
        'get_lines_not_reported')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order.insert(0, ('notebook', 'ASC'))

    def get_rec_name(self, name):
        return self.notebook.rec_name

    @classmethod
    def get_notebook_field(cls, samples, names):
        result = {}
        for name in names:
            result[name] = {}
            if cls._fields[name]._type == 'many2one':
                for s in samples:
                    field = getattr(s.notebook, name, None)
                    result[name][s.id] = field.id if field else None
            else:
                for s in samples:
                    result[name][s.id] = getattr(s.notebook, name, None)
        return result

    def get_lines_not_reported(self, name=None):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')

        cursor.execute('SELECT id '
            'FROM "' + NotebookLine._table + '" '
            'WHERE notebook = %s '
            'AND (report = FALSE OR annulled = TRUE)',
            (self.notebook.id,))
        return [x[0] for x in cursor.fetchall()]

    @classmethod
    def _get_fields_from_sample(cls, sample, only_accepted=True):
        sample_default = {}
        notebook_lines = []
        for nline in sample.notebook_lines:
            if not nline.notebook_line:
                continue
            if only_accepted and not nline.notebook_line.accepted:
                continue
            notebook_lines.append({
                'notebook_line': nline.notebook_line.id,
                'hide': nline.hide,
                'corrected': nline.corrected,
                })
        if notebook_lines:
            sample_default['notebook_lines'] = [('create', notebook_lines)]
        return sample_default

    @classmethod
    def create(cls, vlist):
        Sample = Pool().get('lims.sample')
        samples = super().create(vlist)
        sample_ids = list(set(s.notebook.fraction.sample.id for s in samples))
        Sample.update_samples_state(sample_ids)
        return samples

    @classmethod
    def delete(cls, samples):
        Sample = Pool().get('lims.sample')
        sample_ids = list(set(s.notebook.fraction.sample.id for s in samples))
        super().delete(samples)
        Sample.update_samples_state(sample_ids)


class ResultsReportVersionDetailLine(ModelSQL, ModelView):
    'Results Report Version Detail Line'
    __name__ = 'lims.results_report.version.detail.line'
    _table = 'lims_results_report_version_detail_l'

    detail_sample = fields.Many2One(
        'lims.results_report.version.detail.sample', 'Sample Detail',
        required=True, ondelete='CASCADE', select=True)
    notebook_line = fields.Many2One('lims.notebook.line', 'Notebook Line',
        readonly=True, select=True)
    hide = fields.Boolean('Hide in Report', select=True)
    corrected = fields.Boolean('Corrected')
    analysis_origin = fields.Function(fields.Char('Analysis origin'),
        'get_nline_field')
    analysis = fields.Function(fields.Many2One('lims.analysis', 'Analysis'),
        'get_nline_field')
    repetition = fields.Function(fields.Integer('Repetition'),
        'get_nline_field')
    start_date = fields.Function(fields.Date('Start date'), 'get_nline_field')
    end_date = fields.Function(fields.Date('End date'), 'get_nline_field')
    method = fields.Function(fields.Many2One('lims.lab.method', 'Method'),
        'get_nline_field')
    device = fields.Function(fields.Many2One('lims.lab.device', 'Device'),
        'get_nline_field')
    urgent = fields.Function(fields.Boolean('Urgent'), 'get_nline_field')
    priority = fields.Function(fields.Integer('Priority'), 'get_nline_field')
    report_date = fields.Function(fields.Date('Date agreed for result'),
        'get_nline_field')
    result = fields.Function(fields.Char('Result'), 'get_result')
    initial_unit = fields.Function(fields.Many2One('product.uom',
        'Initial unit'), 'get_nline_field')
    converted_result = fields.Function(fields.Char('Converted result'),
        'get_converted_result')
    final_unit = fields.Function(fields.Many2One('product.uom',
        'Final unit'), 'get_nline_field')
    reference = fields.Function(fields.Char('Reference'), 'get_reference')
    comments = fields.Function(fields.Text('Entry comments'),
        'get_nline_field')

    @classmethod
    def __register__(cls, module_name):
        table_h = cls.__table_handler__(module_name)
        super().__register__(module_name)
        if table_h.column_exist('report_version_detail'):
            cls._migrate_lines()
            table_h.drop_column('report_version_detail')

    @classmethod
    def _migrate_lines(cls):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        ResultsSample = pool.get('lims.results_report.version.detail.sample')

        cursor.execute('SELECT '
                'DISTINCT(dl.report_version_detail, nl.notebook) '
            'FROM "' + cls._table + '" dl '
                'INNER JOIN "' + NotebookLine._table + '" nl '
                'ON dl.notebook_line = nl.id')
        for x in cursor.fetchall():
            r = x[0].split(',')
            detail_sample = ResultsSample(
                version_detail=int(r[0][1:]),
                notebook=int(r[1][:-1]))
            detail_sample.save()
            cursor.execute('UPDATE "' + cls._table + '" dl '
                'SET detail_sample = %s '
                'FROM "' + NotebookLine._table + '" nl '
                'WHERE dl.notebook_line = nl.id '
                    'AND dl.report_version_detail = %s '
                    'AND nl.notebook = %s',
                (detail_sample.id, detail_sample.version_detail.id,
                 detail_sample.notebook.id))

    @staticmethod
    def default_hide():
        return False

    @staticmethod
    def default_corrected():
        return False

    @classmethod
    def get_nline_field(cls, details, names):
        result = {}
        for name in names:
            result[name] = {}
            if cls._fields[name]._type == 'many2one':
                for d in details:
                    if d.notebook_line:
                        field = getattr(d.notebook_line, name, None)
                        result[name][d.id] = field.id if field else None
                    else:
                        result[name][d.id] = None
            else:
                for d in details:
                    result[name][d.id] = (d.notebook_line and
                        getattr(d.notebook_line, name, None) or None)
        return result

    @classmethod
    def get_result(cls, details, name):
        result = {}
        for d in details:
            result[d.id] = (d.notebook_line and
                d.notebook_line.get_formated_result() or None)
        return result

    @classmethod
    def get_converted_result(cls, details, name):
        result = {}
        for d in details:
            result[d.id] = (d.notebook_line and
                d.notebook_line.get_formated_converted_result() or None)
        return result

    @classmethod
    def get_reference(cls, details, name):
        result = {}
        for d in details:
            result[d.id] = (d.notebook_line and
                cls._get_reference(d.notebook_line, d.detail_sample) or None)
        return result

    @classmethod
    def _get_reference(cls, notebook_line, detail_sample):
        Range = Pool().get('lims.range')

        if not detail_sample.version_detail.resultrange_origin:
            return ''

        ranges = Range.search([
            ('range_type', '=',
                detail_sample.version_detail.resultrange_origin.id),
            ('analysis', '=', notebook_line.analysis.id),
            ('product_type', '=', notebook_line.product_type.id),
            ('matrix', '=', notebook_line.matrix.id),
            ])
        if not ranges:
            return ''

        range_ = ranges[0]

        if range_.reference:
            return range_.reference

        res = ''
        if range_.min:
            resf = float(range_.min)
            resd = abs(resf) - abs(int(resf))
            if resd > 0:
                res1 = str(round(range_.min, 2))
            else:
                res1 = str(int(range_.min))
            res = gettext('lims.msg_caa_min', min=res1)

        if range_.max:
            if res:
                res += ' - '
            resf = float(range_.max)
            resd = abs(resf) - abs(int(resf))
            if resd > 0:
                res1 = str(round(range_.max, 2))
            else:
                res1 = str(int(range_.max))

            res += gettext('lims.msg_caa_max', max=res1)
        return res

    @classmethod
    def get_draft_lines_ids(cls, laboratory_id=None, notebook_id=None):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        ResultsSample = pool.get('lims.results_report.version.detail.sample')
        ResultsDetail = pool.get('lims.results_report.version.detail')
        ResultsVersion = pool.get('lims.results_report.version')

        laboratory_clause = ''
        if laboratory_id:
            laboratory_clause = 'AND rv.laboratory = %s ' % laboratory_id
        notebook_clause = ''
        if notebook_id:
            notebook_clause = 'AND rs.notebook = %s ' % notebook_id

        cursor.execute('SELECT rl.notebook_line '
            'FROM "' + cls._table + '" rl '
                'INNER JOIN "' + ResultsSample._table + '" rs '
                'ON rl.detail_sample = rs.id '
                'INNER JOIN "' + ResultsDetail._table + '" rd '
                'ON rs.version_detail = rd.id '
                'INNER JOIN "' + ResultsVersion._table + '" rv '
                'ON rd.report_version = rv.id '
            'WHERE rl.notebook_line IS NOT NULL '
                'AND rd.state NOT IN (\'released\', \'annulled\') '
                'AND rd.type != \'preliminary\' ' +
                laboratory_clause + notebook_clause)
        return [x[0] for x in cursor.fetchall()]


class ResultsLineRepeatAnalysis(NotebookLineRepeatAnalysis):
    'Repeat Analysis'
    __name__ = 'lims.results_report.version.detail.line.repeat_analysis'

    def _get_notebook_line_id(self):
        ResultsLine = Pool().get('lims.results_report.version.detail.line')
        line = ResultsLine(Transaction().context['active_id'])
        return line.notebook_line and line.notebook_line.id or None

    def default_start(self, fields):
        line_id = self._get_notebook_line_id()
        if not line_id:
            return {}
        return super().default_start(fields)


class DivideReportsResult(ModelView):
    'Divide Reports'
    __name__ = 'lims.divide_reports.result'

    services = fields.Many2Many('lims.service', None, None, 'Services')
    total = fields.Integer('Total')
    index = fields.Integer('Index')


class DivideReportsDetail(ModelSQL, ModelView):
    'Analysis Detail'
    __name__ = 'lims.divide_reports.detail'

    detail_id = fields.Integer('Detail ID')
    analysis_origin = fields.Char('Analysis origin', readonly=True)
    analysis = fields.Many2One('lims.analysis', 'Analysis', readonly=True)
    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        readonly=True)
    report_grouper = fields.Integer('Report Grouper')
    session_id = fields.Integer('Session ID')

    @classmethod
    def __register__(cls, module_name):
        super().__register__(module_name)
        cursor = Transaction().connection.cursor()
        cursor.execute('DELETE FROM "' + cls._table + '"')


class DivideReportsProcess(ModelView):
    'Divide Reports'
    __name__ = 'lims.divide_reports.process'

    fraction = fields.Many2One('lims.fraction', 'Fraction', readonly=True)
    service = fields.Many2One('lims.service', 'Service', readonly=True)
    analysis = fields.Many2One('lims.analysis', 'Analysis', readonly=True)
    analysis_detail = fields.One2Many('lims.divide_reports.detail',
        None, 'Analysis detail')


class DivideReports(Wizard):
    'Divide Reports'
    __name__ = 'lims.divide_reports'

    start_state = 'search'
    search = StateTransition()
    result = StateView('lims.divide_reports.result',
        'lims.lims_divide_reports_result_view_form', [])
    next_ = StateTransition()
    process = StateView('lims.divide_reports.process',
        'lims.lims_divide_reports_process_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Next', 'next_', 'tryton-forward', default=True),
            ])
    confirm = StateTransition()

    def transition_search(self):
        Service = Pool().get('lims.service')

        services = Service.search([
            ('entry', '=', Transaction().context['active_id']),
            ('divide', '=', True),
            ('annulled', '=', False),
            ])
        if services:
            self.result.services = services
            self.result.total = len(self.result.services)
            self.result.index = 0
            return 'next_'
        return 'end'

    def transition_next_(self):
        has_prev = (hasattr(self.process, 'analysis_detail') and
            getattr(self.process, 'analysis_detail'))
        if has_prev:
            for detail in self.process.analysis_detail:
                detail.save()

        if self.result.index < self.result.total:
            service = self.result.services[self.result.index]
            self.process.service = service.id
            self.process.analysis_detail = None
            self.result.index += 1
            return 'process'
        return 'confirm'

    def default_process(self, fields):
        DivideReportsDetail = Pool().get(
            'lims.divide_reports.detail')

        if not self.process.service:
            return {}

        default = {}
        default['fraction'] = self.process.service.fraction.id
        default['service'] = self.process.service.id
        default['analysis'] = self.process.service.analysis.id
        details = DivideReportsDetail.create([{
            'detail_id': d.id,
            'analysis_origin': d.analysis_origin,
            'analysis': d.analysis.id,
            'laboratory': d.laboratory.id,
            'report_grouper': d.report_grouper,
            'session_id': self._session_id,
            } for d in self.process.service.analysis_detail])
        if details:
            default['analysis_detail'] = [d.id for d in details]
        return default

    def transition_confirm(self):
        pool = Pool()
        DivideReportsDetail = pool.get(
            'lims.divide_reports.detail')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        details = DivideReportsDetail.search([
            ('session_id', '=', self._session_id),
            ])
        for detail in details:
            analysis_detail = EntryDetailAnalysis(detail.detail_id)
            analysis_detail.report_grouper = detail.report_grouper
            analysis_detail.save()
        return 'end'


# TODO: remove
class GenerateResultsReportStart(ModelView):
    'Generate Results Report'
    __name__ = 'lims.generate_results_report.start'

    date_from = fields.Date('Date from', required=True)
    date_to = fields.Date('Date to', required=True)
    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        required=True)
    party = fields.Many2One('party.party', 'Party')
    generation_type = fields.Selection([
        ('aut', 'Automatic'),
        ('man', 'Manual'),
        ], 'Generation type', sort=False)


# TODO: remove
class GenerateResultsReportEmpty(ModelView):
    'Generate Results Report'
    __name__ = 'lims.generate_results_report.empty'


# TODO: remove
class GenerateResultsReportResultAut(ModelView):
    'Generate Results Report'
    __name__ = 'lims.generate_results_report.result_aut'

    notebooks = fields.One2Many(
        'lims.generate_results_report.aut.notebook', None, 'Results',
        readonly=True)
    notebook_lines = fields.Many2Many('lims.notebook.line', None, None,
        'Results', readonly=True)
    excluded_notebooks = fields.One2Many(
        'lims.generate_results_report.aut.excluded_notebook', None,
        'Excluded Fractions', readonly=True)
    reports_details = fields.One2Many('lims.results_report.version.detail',
        None, 'Reports details')


# TODO: remove
class GenerateResultsReportResultAutNotebook(ModelSQL, ModelView):
    'Notebook'
    __name__ = 'lims.generate_results_report.aut.notebook'

    notebook = fields.Many2One('lims.notebook', 'Notebook', readonly=True)
    fraction = fields.Function(fields.Many2One('lims.fraction', 'Fraction'),
        'get_notebook_field')
    product_type = fields.Function(fields.Many2One('lims.product.type',
        'Product type'), 'get_notebook_field')
    matrix = fields.Function(fields.Many2One('lims.matrix', 'Matrix'),
        'get_notebook_field')
    party = fields.Function(fields.Many2One('party.party', 'Party'),
        'get_notebook_field')
    label = fields.Function(fields.Char('Label'), 'get_notebook_field')
    fraction_type = fields.Function(fields.Many2One('lims.fraction.type',
        'Fraction type'), 'get_notebook_field')
    date = fields.Function(fields.DateTime('Date'), 'get_notebook_field')
    lines = fields.Many2Many(
        'lims.generate_results_report.aut.notebook-line', 'notebook',
        'line', 'Lines', readonly=True)
    session_id = fields.Integer('Session ID')

    @classmethod
    def __register__(cls, module_name):
        super().__register__(module_name)
        cursor = Transaction().connection.cursor()
        cursor.execute('DELETE FROM "' + cls._table + '"')

    @classmethod
    def get_notebook_field(cls, notebooks, names):
        result = {}
        for name in names:
            result[name] = {}
            if name in ('label', 'date'):
                for n in notebooks:
                    result[name][n.id] = getattr(n.notebook, name, None)
            else:
                for n in notebooks:
                    field = getattr(n.notebook, name, None)
                    result[name][n.id] = field.id if field else None
        return result


# TODO: remove
class GenerateResultsReportResultAutNotebookLine(ModelSQL, ModelView):
    'Notebook Line'
    __name__ = 'lims.generate_results_report.aut.notebook-line'

    notebook = fields.Many2One(
        'lims.generate_results_report.aut.notebook', 'Notebook',
        ondelete='CASCADE', select=True, required=True)
    line = fields.Many2One('lims.notebook.line', 'Notebook Line',
        ondelete='CASCADE', select=True, required=True)


# TODO: remove
class GenerateResultsReportResultAutExcludedNotebook(ModelSQL, ModelView):
    'Excluded Notebook'
    __name__ = 'lims.generate_results_report.aut.excluded_notebook'
    _table = 'lims_generate_results_report_aut_excluded_nb'

    notebook = fields.Many2One('lims.notebook', 'Notebook', readonly=True)
    fraction = fields.Function(fields.Many2One('lims.fraction', 'Fraction'),
        'get_notebook_field')
    product_type = fields.Function(fields.Many2One('lims.product.type',
        'Product type'), 'get_notebook_field')
    matrix = fields.Function(fields.Many2One('lims.matrix', 'Matrix'),
        'get_notebook_field')
    party = fields.Function(fields.Many2One('party.party', 'Party'),
        'get_notebook_field')
    label = fields.Function(fields.Char('Label'), 'get_notebook_field')
    fraction_type = fields.Function(fields.Many2One('lims.fraction.type',
        'Fraction type'), 'get_notebook_field')
    date = fields.Function(fields.DateTime('Date'), 'get_notebook_field')
    lines = fields.Many2Many(
        'lims.generate_results_report.aut.excluded_notebook-line', 'notebook',
        'line', 'Lines', readonly=True)
    session_id = fields.Integer('Session ID')

    @classmethod
    def __register__(cls, module_name):
        super().__register__(module_name)
        cursor = Transaction().connection.cursor()
        cursor.execute('DELETE FROM "' + cls._table + '"')

    @classmethod
    def get_notebook_field(cls, notebooks, names):
        result = {}
        for name in names:
            result[name] = {}
            if name in ('label', 'date'):
                for n in notebooks:
                    result[name][n.id] = getattr(n.notebook, name, None)
            else:
                for n in notebooks:
                    field = getattr(n.notebook, name, None)
                    result[name][n.id] = field.id if field else None
        return result


# TODO: remove
class GenerateResultsReportResultAutExcludedNotebookLine(ModelSQL,
        ModelView):
    'Excluded Notebook Line'
    __name__ = 'lims.generate_results_report.aut.excluded_notebook-line'
    _table = 'lims_generate_results_report_aut_excluded_nb-line'

    notebook = fields.Many2One(
        'lims.generate_results_report.aut.excluded_notebook',
        'Notebook', ondelete='CASCADE', select=True, required=True)
    line = fields.Many2One('lims.notebook.line', 'Notebook Line',
        ondelete='CASCADE', select=True, required=True)


# TODO: remove
class GenerateResultsReportResultMan(ModelView):
    'Generate Results Report'
    __name__ = 'lims.generate_results_report.result_man'

    notebook_lines = fields.Many2Many('lims.notebook.line', None, None,
        'Results', required=True, depends=['notebook_lines_domain', 'party',
        'report_type', 'notebook', 'report_grouper', 'cie_fraction_type'],
        domain=[('id', 'in', Eval('notebook_lines_domain')),
            If(Bool(Eval('party')),
                ('notebook.party', '=', Eval('party')), ('id', '!=', -1)),
            If(Bool(Equal(Eval('report_type'), 'normal')),
                ('notebook', '=', Eval('notebook')), ('id', '!=', -1)),
            If(Bool(Eval('report_grouper')),
                ('analysis_detail.report_grouper', '=',
                Eval('report_grouper')), ('id', '!=', -1)),
            If(Bool(Eval('cie_fraction_type')),
                ('notebook.fraction.cie_fraction_type', '=',
                Eval('cie_fraction_type')), ('id', '!=', -1)),
                ])
    notebook_lines_domain = fields.One2Many('lims.notebook.line', None,
        'Results domain', readonly=True)
    report = fields.Many2One('lims.results_report', 'Report',
        states={'readonly': Bool(Eval('notebook_lines'))},
        domain=[('id', 'in', Eval('report_domain'))],
        depends=['notebook_lines', 'report_domain'])
    report_domain = fields.One2Many('lims.results_report', None,
        'Reports domain')
    report_type_forced = fields.Selection([
        ('none', 'None'),
        ('normal', 'Normal'),
        ('polisample', 'Polisample'),
        ], 'Force report type', sort=False, depends=['report'],
        states={'invisible': Bool(Eval('report'))})
    party = fields.Many2One('party.party', 'Party')
    notebook = fields.Many2One('lims.notebook', 'Laboratory notebook')
    report_grouper = fields.Integer('Report Grouper')
    report_type = fields.Char('Report type')
    cie_fraction_type = fields.Boolean('QA')
    laboratory = fields.Many2One('lims.laboratory', 'Laboratory')
    reports_details = fields.One2Many('lims.results_report.version.detail',
        None, 'Reports details')

    @fields.depends('report', '_parent_report.party')
    def on_change_with_party(self, name=None):
        if self.report:
            return self.report.party.id
        return None

    @fields.depends('report', '_parent_report.notebook')
    def on_change_with_notebook(self, name=None):
        if self.report and self.report.notebook:
            return self.report.notebook.id
        return None

    @fields.depends('report', '_parent_report.report_grouper')
    def on_change_with_report_grouper(self, name=None):
        if self.report:
            return self.report.report_grouper
        return None

    @fields.depends('report', 'laboratory')
    def on_change_with_report_type(self, name=None):
        if self.report:
            ResultsVersion = Pool().get('lims.results_report.version')
            version = ResultsVersion.search([
                ('results_report.id', '=', self.report.id),
                ('laboratory.id', '=', self.laboratory.id),
                ], limit=1)
            if version:
                return version[0].report_type
            version = ResultsVersion.search([
                ('results_report.id', '=', self.report.id),
                ], order=[('id', 'DESC')], limit=1)
            if version:
                return version[0].report_type
        return None

    @fields.depends('report', '_parent_report.cie_fraction_type')
    def on_change_with_cie_fraction_type(self, name=None):
        if self.report:
            with Transaction().set_context(_check_access=False):
                return self.report.cie_fraction_type
        return False


# TODO: remove
class GenerateResultsReport(Wizard):
    'Generate Results Report'
    __name__ = 'lims.generate_results_report'

    start = StateView('lims.generate_results_report.start',
        'lims.lims_generate_results_report_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search', 'search', 'tryton-forward', default=True),
            ])
    search = StateTransition()
    empty = StateView('lims.generate_results_report.empty',
        'lims.lims_generate_results_report_empty_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search again', 'start', 'tryton-forward', default=True),
            ])
    result_aut = StateView('lims.generate_results_report.result_aut',
        'lims.lims_generate_results_report_result_aut_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Generate', 'generate', 'tryton-ok', default=True),
            ])
    result_man = StateView('lims.generate_results_report.result_man',
        'lims.lims_generate_results_report_result_man_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Generate', 'generate', 'tryton-ok', default=True),
            ])
    generate = StateTransition()
    open = StateAction('lims.act_lims_results_report_version_detail')

    def default_start(self, fields):
        res = {}
        for field in ('date_from', 'date_to', 'generation_type'):
            if (hasattr(self.start, field) and getattr(self.start, field)):
                res[field] = getattr(self.start, field)
        for field in ('laboratory', 'party'):
            if (hasattr(self.start, field) and getattr(self.start, field)):
                res[field] = getattr(self.start, field).id
        if 'generation_type' not in res:
            res['generation_type'] = 'aut'
        if 'laboratory' not in res:
            res['laboratory'] = Transaction().context.get('laboratory', None)
        return res

    def transition_search(self):
        if self.start.generation_type == 'aut':
            return self._search_aut()
        return self._search_man()

    def _get_notebook_lines(self, generation_type, excluded_notebooks=[]):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        ResultsLine = pool.get('lims.results_report.version.detail.line')
        NotebookLine = pool.get('lims.notebook.line')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        draft_lines_ids = ResultsLine.get_draft_lines_ids(
            self.start.laboratory.id)

        clause = [
            ('notebook.date2', '>=', self.start.date_from),
            ('notebook.date2', '<=', self.start.date_to),
            ('laboratory', '=', self.start.laboratory.id),
            ('notebook.fraction.type.report', '=', True),
            ('report', '=', True),
            ('annulled', '=', False),
            ('results_report', '=', None),
            ('id', 'not in', draft_lines_ids),
            ]
        if self.start.party:
            clause.append(('notebook.party', '=', self.start.party.id))

        clause.append(('accepted', '=', True))

        if generation_type == 'aut':
            for n_id, grouper in excluded_notebooks:
                cursor.execute('SELECT nl.id '
                    'FROM "' + NotebookLine._table + '" nl '
                        'INNER JOIN "' + EntryDetailAnalysis._table + '" d '
                        'ON d.id = nl.analysis_detail '
                    'WHERE nl.notebook = %s AND d.report_grouper = %s',
                    (n_id, grouper))
                excluded_notebook_lines = [x[0] for x in cursor.fetchall()]
                clause.append(('id', 'not in', excluded_notebook_lines))
        return NotebookLine.search(clause)

    def _get_excluded_notebooks(self):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        Notebook = pool.get('lims.notebook')
        Fraction = pool.get('lims.fraction')
        Sample = pool.get('lims.sample')
        Entry = pool.get('lims.entry')
        FractionType = pool.get('lims.fraction.type')

        party_clause = ''
        if self.start.party:
            party_clause = 'AND e.party = ' + str(self.start.party.id)

        cursor.execute('SELECT nl.notebook, nl.analysis, nl.method, '
                'd.report_grouper, nl.accepted '
            'FROM "' + NotebookLine._table + '" nl '
                'INNER JOIN "' + EntryDetailAnalysis._table + '" d '
                'ON d.id = nl.analysis_detail '
                'INNER JOIN "' + Notebook._table + '" n '
                'ON n.id = nl.notebook '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON f.id = n.fraction '
                'INNER JOIN "' + Sample._table + '" s '
                'ON s.id = f.sample '
                'INNER JOIN "' + Entry._table + '" e '
                'ON e.id = s.entry '
                'INNER JOIN "' + FractionType._table + '" ft '
                'ON ft.id = f.type '
            'WHERE ft.report = TRUE '
                'AND s.date::date >= %s::date '
                'AND s.date::date <= %s::date '
                'AND nl.laboratory = %s '
                'AND nl.report = TRUE '
                'AND nl.annulled = FALSE ' +
                party_clause,
            (self.start.date_from, self.start.date_to,
                self.start.laboratory.id,))
        notebook_lines = cursor.fetchall()

        # Check repetitions
        oks, to_check = [], []
        accepted_notebooks = []
        for line in notebook_lines:
            key = (line[0], line[1], line[2], line[3])
            if not line[4]:
                to_check.append(key)
            else:
                oks.append(key)
                accepted_notebooks.append(line[0])

        to_check = list(set(to_check) - set(oks))
        accepted_notebooks = list(set(accepted_notebooks))

        excluded_notebooks = {}
        for n_id, a_id, m_id, grouper in to_check:
            if n_id not in accepted_notebooks:
                continue
            key = (n_id, grouper)
            if key not in excluded_notebooks:
                excluded_notebooks[key] = []
            excluded_notebooks[key].append(a_id)
        return excluded_notebooks

    def _search_aut(self):
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        GenerateResultsReportResultAutNotebook = pool.get(
            'lims.generate_results_report.aut.notebook')
        GenerateResultsReportResultAutExcludedNotebook = pool.get(
            'lims.generate_results_report.aut.excluded_notebook')

        self.result_aut.excluded_notebooks = None
        self.result_aut.notebooks = None
        self.result_aut.notebook_lines = None

        excluded_notebooks = self._get_excluded_notebooks()
        if excluded_notebooks:
            notebooks = {}
            for (n_id, grouper), a_ids in excluded_notebooks.items():
                clause = [
                    ('notebook.id', '=', n_id),
                    ('analysis_detail.report_grouper', '=', grouper),
                    ('analysis', 'in', a_ids),
                    ('laboratory', '=', self.start.laboratory.id),
                    ('report', '=', True),
                    ('annulled', '=', False),
                    ]
                excluded_lines = NotebookLine.search(clause)
                if excluded_lines:
                    notebooks[n_id] = [line.id for line in excluded_lines]

            to_create = [{
                'session_id': self._session_id,
                'notebook': k,
                'lines': [('add', v)],
                } for k, v in notebooks.items()]
            self.result_aut.excluded_notebooks = (
                GenerateResultsReportResultAutExcludedNotebook.create(
                    to_create))

        notebook_lines = self._get_notebook_lines('aut',
            list(excluded_notebooks.keys()))
        if notebook_lines:
            notebooks = {}
            for line in notebook_lines:
                if line.notebook.id not in notebooks:
                    notebooks[line.notebook.id] = []
                notebooks[line.notebook.id].append(line.id)

            to_create = []
            for k, v in notebooks.items():
                to_create.append({
                    'session_id': self._session_id,
                    'notebook': k,
                    'lines': [('add', v)],
                    })
            self.result_aut.notebooks = (
                GenerateResultsReportResultAutNotebook.create(to_create))
            self.result_aut.notebook_lines = [l.id for l in
                notebook_lines]
        if notebook_lines or excluded_notebooks:
            return 'result_aut'
        return 'empty'

    def default_result_aut(self, fields):
        ret = {
            'notebooks': [],
            'notebook_lines': [],
            'excluded_notebooks': [],
            }
        if self.result_aut.notebooks:
            ret['notebooks'] = [n.id for n in self.result_aut.notebooks]
        if self.result_aut.notebook_lines:
            ret['notebook_lines'] = [l.id for l in
                self.result_aut.notebook_lines]
        if self.result_aut.excluded_notebooks:
            sorted_notebooks = sorted(self.result_aut.excluded_notebooks,
                key=lambda n: n.fraction.number)
            ret['excluded_notebooks'] = [n.id for n in sorted_notebooks]
        self.result_aut.notebooks = None
        self.result_aut.excluded_notebooks = None
        return ret

    def _search_man(self):
        ResultsReport = Pool().get('lims.results_report')

        notebook_lines = self._get_notebook_lines('man')
        if notebook_lines:
            self.result_man.notebook_lines_domain = [l.id for l in
                notebook_lines]

            self.result_man.report_domain = []
            clause = [
                ('generation_type', '=', 'man'),
                ]
            if self.start.party:
                clause.append(('party', '=', self.start.party.id))
            reports = ResultsReport.search(clause)
            if reports:
                self.result_man.report_domain = [r.id for r in reports]
            return 'result_man'
        return 'empty'

    def default_result_man(self, fields):
        notebook_lines = [l.id for l in self.result_man.notebook_lines_domain]
        self.result_man.notebook_lines_domain = None
        reports = []
        if self.result_man.report_domain:
            reports = [r.id for r in self.result_man.report_domain]
        return {
            'notebook_lines': [],
            'notebook_lines_domain': notebook_lines,
            'report': None,
            'report_domain': reports,
            'report_type_forced': 'none',
            'laboratory': self.start.laboratory.id,
            }

    def transition_generate(self):
        if self.start.generation_type == 'aut':
            if self.result_aut.notebook_lines:
                return self._generate_aut()
            else:
                return 'empty'
        return self._generate_man()

    def _generate_aut(self):
        notebooks = {}
        for line in self.result_aut.notebook_lines:
            if line.notebook.id not in notebooks:
                notebooks[line.notebook.id] = {
                    'party': line.notebook.party.id,
                    'entry': line.notebook.fraction.entry.id,
                    'notebook': line.notebook.id,
                    'english_report': (
                        line.notebook.fraction.entry.english_report),
                    'cie_fraction_type': (
                        line.notebook.fraction.cie_fraction_type),
                    'lines': [],
                    }
            notebooks[line.notebook.id]['lines'].append(line)

        reports_details = []
        for notebook in notebooks.values():
            grouped_reports = {}
            for line in notebook['lines']:
                report_grouper = line.analysis_detail.report_grouper
                if report_grouper not in grouped_reports:
                    grouped_reports[report_grouper] = []
                grouped_reports[report_grouper].append(line)

            for grouper, nlines in grouped_reports.items():
                notebook_lines = [{'notebook_line': line.id}
                    for line in nlines]
                samples = [{
                    'notebook': notebook['notebook'],
                    'notebook_lines': [('create', notebook_lines)],
                    }]
                details = {
                    'signer': self.start.laboratory.default_signer.id,
                    'samples': [('create', samples)],
                    }
                versions = {
                    'laboratory': self.start.laboratory.id,
                    'details': [('create', [details])],
                    }
                reports = {
                    'party': notebook['party'],
                    'entry': notebook['entry'],
                    'notebook': notebook['notebook'],
                    'report_grouper': grouper,
                    'generation_type': 'aut',
                    'cie_fraction_type': notebook['cie_fraction_type'],
                    'english_report': notebook['english_report'],
                    'versions': [('create', [versions])],
                    }
                report_detail = self._get_results_report(reports, versions,
                    details, samples)
                reports_details.extend(report_detail)

        self.result_aut.reports_details = reports_details
        return 'open'

    def _generate_man(self):
        pool = Pool()
        ResultsVersion = pool.get('lims.results_report.version')
        ResultsDetail = pool.get('lims.results_report.version.detail')
        ResultsSample = pool.get('lims.results_report.version.detail.sample')

        if self.result_man.report:  # Result report selected
            report_type_forced = self.result_man.report_type
            if report_type_forced == 'polisample':  # Polisample report

                notebooks = {}
                for line in self.result_man.notebook_lines:
                    if line.notebook.id not in notebooks:
                        notebooks[line.notebook.id] = {
                            'notebook': line.notebook.id,
                            'lines': [],
                            }
                    notebooks[line.notebook.id]['lines'].append(line)

                samples = []
                for notebook in notebooks.values():
                    notebook_lines = [{'notebook_line': line.id}
                        for line in notebook['lines']]
                    samples.append({
                        'notebook': notebook['notebook'],
                        'notebook_lines': [('create', notebook_lines)],
                        })
                details = {
                    'report_type_forced': 'polisample',
                    'signer': self.start.laboratory.default_signer.id,
                    'samples': [('create', samples)],
                    }
                actual_version = ResultsVersion.search([
                    ('results_report', '=', self.result_man.report.id),
                    ('laboratory', '=', self.start.laboratory.id),
                    ], limit=1)
                if not actual_version:
                    version, = ResultsVersion.create([{
                        'results_report': self.result_man.report.id,
                        'laboratory': self.start.laboratory.id,
                        'details': [('create', [details])],
                        }])
                    reports_details = [d.id for d in version.details]
                else:
                    actual_version = actual_version[0]
                    draft_detail = ResultsDetail.search([
                        ('report_version', '=', actual_version.id),
                        ('state', '=', 'draft'),
                        ], limit=1)
                    if not draft_detail:
                        details['report_version'] = actual_version.id
                        detail, = ResultsDetail.create([details])
                        ResultsDetail.update_from_valid_version([detail])
                        reports_details = [detail.id]
                    else:
                        draft_detail = draft_detail[0]
                        for sample in samples:
                            existing_sample = ResultsSample.search([
                                ('version_detail', '=', draft_detail.id),
                                ('notebook', '=', sample['notebook']),
                                ], limit=1)
                            if not existing_sample:
                                sample['version_detail'] = draft_detail.id
                                ResultsSample.create([sample])
                            else:
                                del sample['notebook']
                                ResultsSample.write(existing_sample, sample)

                        del details['signer']
                        del details['samples']
                        ResultsDetail.write([draft_detail], details)
                        reports_details = [draft_detail.id]

            else:  # Normal report

                notebooks = {}
                for line in self.result_man.notebook_lines:
                    if line.notebook.id not in notebooks:
                        notebooks[line.notebook.id] = {
                            'notebook': line.notebook.id,
                            'lines': [],
                            }
                    notebooks[line.notebook.id]['lines'].append(line)

                samples = []
                for notebook in notebooks.values():
                    notebook_lines = [{'notebook_line': line.id}
                        for line in notebook['lines']]
                    samples.append({
                        'notebook': notebook['notebook'],
                        'notebook_lines': [('create', notebook_lines)],
                        })
                details = {
                    'signer': self.start.laboratory.default_signer.id,
                    'samples': [('create', samples)],
                    }
                actual_version = ResultsVersion.search([
                    ('results_report', '=', self.result_man.report.id),
                    ('laboratory', '=', self.start.laboratory.id),
                    ], limit=1)
                if not actual_version:
                    version, = ResultsVersion.create([{
                        'results_report': self.result_man.report.id,
                        'laboratory': self.start.laboratory.id,
                        'details': [('create', [details])],
                        }])
                    reports_details = [d.id for d in version.details]
                else:
                    actual_version = actual_version[0]
                    draft_detail = ResultsDetail.search([
                        ('report_version', '=', actual_version.id),
                        ('state', '=', 'draft'),
                        ], limit=1)
                    if not draft_detail:
                        details['report_version'] = actual_version.id
                        detail, = ResultsDetail.create([details])
                        ResultsDetail.update_from_valid_version([detail])
                        reports_details = [detail.id]
                    else:
                        draft_detail = draft_detail[0]
                        for sample in samples:
                            existing_sample = ResultsSample.search([
                                ('version_detail', '=', draft_detail.id),
                                ('notebook', '=', sample['notebook']),
                                ], limit=1)
                            if not existing_sample:
                                sample['version_detail'] = draft_detail.id
                                ResultsSample.create([sample])
                            else:
                                del sample['notebook']
                                ResultsSample.write(existing_sample, sample)

                        #del details['signer']
                        #del details['samples']
                        #ResultsDetail.write([draft_detail], details)
                        reports_details = [draft_detail.id]

            self.result_man.reports_details = reports_details

        else:  # Not Result report selected
            report_type_forced = self.result_man.report_type_forced
            if report_type_forced == 'polisample':  # Polisample report

                parties = {}
                for line in self.result_man.notebook_lines:
                    key = (line.notebook.party.id,
                        line.notebook.fraction.cie_fraction_type)
                    if key not in parties:
                        parties[key] = {
                            'party': line.notebook.party.id,
                            'entry': line.notebook.fraction.entry.id,
                            'english_report': (
                                line.notebook.fraction.entry.english_report),
                            'cie_fraction_type': (
                                line.notebook.fraction.cie_fraction_type),
                            'lines': [],
                            }
                    parties[key]['lines'].append(line)

                reports_details = []
                for party in parties.values():
                    grouped_reports = {}
                    for line in party['lines']:
                        report_grouper = line.analysis_detail.report_grouper
                        if report_grouper not in grouped_reports:
                            grouped_reports[report_grouper] = []
                        grouped_reports[report_grouper].append(line)

                    for grouper, nlines in grouped_reports.items():
                        notebooks = {}
                        for line in nlines:
                            if line.notebook.id not in notebooks:
                                notebooks[line.notebook.id] = {
                                    'notebook': line.notebook.id,
                                    'lines': [],
                                    }
                            notebooks[line.notebook.id]['lines'].append(line)

                        samples = []
                        for notebook in notebooks.values():
                            notebook_lines = [{'notebook_line': line.id}
                                for line in notebook['lines']]
                            samples.append({
                                'notebook': notebook['notebook'],
                                'notebook_lines': [('create', notebook_lines)],
                                })
                        details = {
                            'report_type_forced': report_type_forced,
                            'signer': self.start.laboratory.default_signer.id,
                            'samples': [('create', samples)],
                            }
                        versions = {
                            'laboratory': self.start.laboratory.id,
                            'details': [('create', [details])],
                            }
                        reports = {
                            'party': party['party'],
                            'entry': party['entry'],
                            'notebook': None,
                            'report_grouper': grouper,
                            'generation_type': 'man',
                            'cie_fraction_type': party['cie_fraction_type'],
                            'english_report': party['english_report'],
                            'versions': [('create', [versions])],
                            }
                        report_detail = self._get_results_report(reports,
                            versions, details, samples, append=False)
                        reports_details.extend(report_detail)

            else:  # Normal report

                notebooks = {}
                for line in self.result_man.notebook_lines:
                    if line.notebook.id not in notebooks:
                        notebooks[line.notebook.id] = {
                            'party': line.notebook.party.id,
                            'entry': line.notebook.fraction.entry.id,
                            'notebook': line.notebook.id,
                            'english_report': (
                                line.notebook.fraction.entry.english_report),
                            'cie_fraction_type': (
                                line.notebook.fraction.cie_fraction_type),
                            'lines': [],
                            }
                    notebooks[line.notebook.id]['lines'].append(line)

                reports_details = []
                for notebook in notebooks.values():
                    grouped_reports = {}
                    for line in notebook['lines']:
                        report_grouper = (
                            line.analysis_detail.report_grouper)
                        if report_grouper not in grouped_reports:
                            grouped_reports[report_grouper] = []
                        grouped_reports[report_grouper].append(line)

                    for grouper, nlines in grouped_reports.items():
                        notebook_lines = [{'notebook_line': line.id}
                            for line in nlines]
                        samples = [{
                            'notebook': notebook['notebook'],
                            'notebook_lines': [('create', notebook_lines)],
                            }]
                        details = {
                            'report_type_forced': report_type_forced,
                            'signer': (
                                self.start.laboratory.default_signer.id),
                            'samples': [('create', samples)],
                            }
                        versions = {
                            'laboratory': self.start.laboratory.id,
                            'details': [('create', [details])],
                            }
                        reports = {
                            'party': notebook['party'],
                            'entry': notebook['entry'],
                            'notebook': notebook['notebook'],
                            'report_grouper': grouper,
                            'generation_type': 'man',
                            'cie_fraction_type': (
                                notebook['cie_fraction_type']),
                            'english_report': notebook['english_report'],
                            'versions': [('create', [versions])],
                            }
                        report_detail = self._get_results_report(reports,
                            versions, details, samples, append=False)
                        reports_details.extend(report_detail)

            self.result_man.reports_details = reports_details
        return 'open'

    def _get_results_report(self, reports, versions, details, samples,
            append=True):
        pool = Pool()
        ResultsReport = pool.get('lims.results_report')
        ResultsVersion = pool.get('lims.results_report.version')
        ResultsDetail = pool.get('lims.results_report.version.detail')
        ResultsSample = pool.get('lims.results_report.version.detail.sample')

        if not append:
            report, = ResultsReport.create([reports])
            reports_details = [d.id for d in report.versions[0].details]
            return reports_details

        existing_details = ResultsDetail.search([
            ('laboratory', '=', self.start.laboratory.id),
            ('samples.notebook', '=', samples[0]['notebook']),
            ])
        if existing_details:
            current_reports = [d.report_version.results_report.id
                for d in existing_details]
        else:
            existing_details = ResultsDetail.search([
                ('samples.notebook', '=', samples[0]['notebook']),
                ])
            if existing_details:
                current_reports = [d.report_version.results_report.id
                    for d in existing_details]
            else:
                report, = ResultsReport.create([reports])
                reports_details = [d.id for d in report.versions[0].details]
                return reports_details

        actual_report = ResultsReport.search([
            ('id', 'in', current_reports),
            ('report_grouper', '=', reports['report_grouper']),
            ('cie_fraction_type', '=', reports['cie_fraction_type']),
            ], limit=1)
        if not actual_report:
            report, = ResultsReport.create([reports])
            reports_details = [d.id for d in report.versions[0].details]
            return reports_details

        actual_report = actual_report[0]
        actual_version = ResultsVersion.search([
            ('results_report', '=', actual_report.id),
            ('laboratory', '=', self.start.laboratory.id),
            ], limit=1)
        if not actual_version:
            version, = ResultsVersion.create([{
                'results_report': actual_report.id,
                'laboratory': self.start.laboratory.id,
                'details': [('create', [details])],
                }])
            reports_details = [d.id for d in version.details]
            return reports_details

        actual_version = actual_version[0]
        draft_detail = ResultsDetail.search([
            ('report_version', '=', actual_version.id),
            ('state', '=', 'draft'),
            ], limit=1)
        if not draft_detail:
            details['report_version'] = actual_version.id
            detail, = ResultsDetail.create([details])
            ResultsDetail.update_from_valid_version([detail])
            reports_details = [detail.id]
            return reports_details

        draft_detail = draft_detail[0]
        for sample in samples:
            existing_sample = ResultsSample.search([
                ('version_detail', '=', draft_detail.id),
                ('notebook', '=', sample['notebook']),
                ], limit=1)
            if not existing_sample:
                sample['version_detail'] = draft_detail.id
                ResultsSample.create([sample])
            else:
                del sample['notebook']
                ResultsSample.write(existing_sample, sample)

        reports_details = [draft_detail.id]
        return reports_details

    def do_open(self, action):
        if self.start.generation_type == 'aut':
            action['pyson_domain'] = PYSONEncoder().encode([
                ('id', 'in', [r.id for r in self.result_aut.reports_details]),
                ])
            self.result_aut.reports_details = None
        else:
            action['pyson_domain'] = PYSONEncoder().encode([
                ('id', 'in', [r.id for r in self.result_man.reports_details]),
                ])
            self.result_man.reports_details = None
        return action, {}


class OpenSamplesPendingReportingStart(ModelView):
    'Samples Pending Reporting'
    __name__ = 'lims.samples_pending_reporting.start'

    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        required=True)

    @staticmethod
    def default_laboratory():
        return Transaction().context.get('laboratory', None)


class OpenSamplesPendingReporting(Wizard):
    'Samples Pending Reporting'
    __name__ = 'lims.samples_pending_reporting'

    start = StateView('lims.samples_pending_reporting.start',
        'lims.open_samples_pending_reporting_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Open', 'open_', 'tryton-ok', default=True),
            ])
    open_ = StateAction('lims.act_lims_samples_pending_reporting')

    def do_open_(self, action):
        laboratory = self.start.laboratory
        action['pyson_context'] = PYSONEncoder().encode({
            'samples_pending_reporting': True,
            'samples_pending_reporting_laboratory': laboratory.id,
            })
        action['pyson_domain'] = PYSONEncoder().encode([
            ('lines.laboratory', '=', laboratory.id),
            ])
        action['name'] += ' (%s)' % laboratory.rec_name
        return action, {}

    def transition_open_(self):
        return 'end'


class GenerateReportStart(ModelView):
    'Generate Results Report'
    __name__ = 'lims.notebook.generate_results_report.start'

    notebooks = fields.One2Many('lims.notebook', None, 'Samples',
        readonly=True)
    report = fields.Many2One('lims.results_report', 'Target Report',
        states={'readonly': Bool(Eval('report_readonly'))},
        domain=[('id', 'in', Eval('report_domain'))],
        depends=['report_readonly', 'report_domain'])
    report_readonly = fields.Boolean('Target Report readonly')
    report_domain = fields.One2Many('lims.results_report', None,
        'Target Report domain')
    type = fields.Selection([
        ('preliminary', 'Preliminary'),
        ('final', 'Final'),
        ('complementary', 'Complementary'),
        ('corrective', 'Corrective'),
        ], 'Type', states={'readonly': True})
    preliminary = fields.Boolean('Preliminary')
    corrective = fields.Boolean('Corrective',
        states={'invisible': ~Eval('type').in_([
            'complementary', 'corrective'])},
        depends=['type'])
    reports_created = fields.One2Many('lims.results_report.version.detail',
        None, 'Reports created')
    group_samples = fields.Boolean('Group samples in the same report',
        states={'readonly': Bool(Eval('report'))},
        depends=['report'])
    append_samples = fields.Boolean('Append samples to existing reports',
        states={'readonly': Bool(Eval('report'))},
        depends=['report'])

    @fields.depends('report', 'preliminary', 'corrective')
    def on_change_with_type(self, name=None):
        if self.preliminary:
            return 'preliminary'
        report_state = self._get_report_state()
        if report_state == 'draft':
            return 'final'
        if self.corrective:
            return 'corrective'
        return 'complementary'

    def _get_report_state(self):
        pool = Pool()
        ResultsDetail = pool.get('lims.results_report.version.detail')
        if not self.report:
            return 'draft'
        report_id = self.report.id
        laboratory_id = Transaction().context.get(
            'samples_pending_reporting_laboratory', None)
        if not laboratory_id:
            return 'draft'
        last_detail = ResultsDetail.search([
            ('report_version.results_report', '=', report_id),
            ('report_version.laboratory', '=', laboratory_id),
            ('type', '!=', 'preliminary'),
            ], order=[('id', 'DESC')], limit=1)
        if last_detail:
            return last_detail[0].state
        return 'draft'


class GenerateReport(Wizard):
    'Generate Results Report'
    __name__ = 'lims.notebook.generate_results_report'

    start = StateView('lims.notebook.generate_results_report.start',
        'lims.notebook_generate_results_report_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Generate', 'generate', 'tryton-ok', default=True),
            ])
    generate = StateTransition()
    open_ = StateAction('lims.act_lims_results_report_version_detail')

    def default_start(self, fields):
        pool = Pool()
        Notebook = pool.get('lims.notebook')
        ResultsReport = pool.get('lims.results_report')
        ResultsDetail = pool.get('lims.results_report.version.detail')

        laboratory_id = Transaction().context.get(
            'samples_pending_reporting_laboratory', None)

        res = {
            'notebooks': [],
            'report': None,
            'report_readonly': False,
            'report_domain': [],
            'type': 'final',
            'preliminary': False,
            'corrective': False,
            'group_samples': False,
            'append_samples': True,
            }

        party = None
        entry = None
        report_grouper = None
        cie_fraction_type = None
        current_reports = []

        for notebook in Notebook.browse(Transaction().context['active_ids']):
            res['notebooks'].append(notebook.id)
            if not res['report_readonly']:
                if not entry:
                    entry = notebook.fraction.sample.entry.id
                elif entry != notebook.fraction.sample.entry.id:
                    entry = -1
                # same party
                if not party:
                    party = notebook.party.id
                elif party != notebook.party.id:
                    res['report_readonly'] = True
                # same report_grouper
                for line in notebook._get_lines_for_reporting(
                        laboratory_id, 'complete'):
                    if not report_grouper:
                        report_grouper = line.analysis_detail.report_grouper
                    elif report_grouper != line.analysis_detail.report_grouper:
                        res['report_readonly'] = True
                        break
                # same cie_fraction_type
                if cie_fraction_type is None:
                    cie_fraction_type = notebook.fraction.cie_fraction_type
                elif cie_fraction_type != notebook.fraction.cie_fraction_type:
                    res['report_readonly'] = True
                # same current_report
                existing_details = ResultsDetail.search([
                    ('laboratory', '=', laboratory_id),
                    ('samples.notebook', '=', notebook.id),
                    ])
                if existing_details:
                    existing_reports = [d.report_version.results_report.id
                        for d in existing_details]
                    if not current_reports:
                        current_reports = existing_reports
                    elif current_reports != existing_reports:
                        res['report_readonly'] = True

            if notebook.state != 'complete':
                res['preliminary'] = True
                res['type'] = 'preliminary'

        if not res['report_readonly']:
            if res['preliminary']:
                last_detail = ResultsDetail.search([
                    ('party', '=', party),
                    ('laboratory', '=', laboratory_id),
                    ], order=[('id', 'DESC')], limit=1)
                if last_detail and last_detail[0].state == 'preliminary':
                    res['report_domain'] = [
                        last_detail[0].report_version.results_report.id]
            else:
                if current_reports:
                    clause = [('id', 'in', current_reports)]
                else:
                    clause = [
                        ('party', '=', party),
                        ('report_grouper', '=', report_grouper),
                        ('cie_fraction_type', '=', cie_fraction_type),
                        ]
                reports = ResultsReport.search(clause)
                if reports:
                    res['report_domain'] = [r.id for r in reports]

        if res['report_domain'] and entry != -1:
            draft_detail = ResultsDetail.search([
                ('report_version.results_report.id', 'in',
                    res['report_domain']),
                ('state', '=', 'draft'),
                ])
            if draft_detail and len(draft_detail) == 1:
                res['report'] = (
                    draft_detail[0].report_version.results_report.id)

        return res

    def transition_generate(self):
        pool = Pool()
        Laboratory = pool.get('lims.laboratory')
        ResultsVersion = pool.get('lims.results_report.version')
        ResultsDetail = pool.get('lims.results_report.version.detail')
        ResultsSample = pool.get('lims.results_report.version.detail.sample')

        laboratory_id = Transaction().context.get(
            'samples_pending_reporting_laboratory', None)
        signer = Laboratory(laboratory_id).default_signer.id

        reports_created = []

        state = ('in_progress' if self.start.type == 'preliminary' else
            'complete')
        corrected = self.start.corrective

        if self.start.report:  # Result report selected
            samples = []
            for notebook in self.start.notebooks:
                lines = notebook._get_lines_for_reporting(laboratory_id,
                    state)
                notebook_lines = [{
                    'notebook_line': line.id,
                    'corrected': corrected,
                    } for line in lines]
                samples.append({
                    'notebook': notebook.id,
                    'notebook_lines': [('create', notebook_lines)],
                    })
            details = {
                'type': self.start.type,
                'signer': signer,
                'samples': [('create', samples)],
                }
            details.update(ResultsDetail._get_fields_from_samples(samples))

            actual_version = ResultsVersion.search([
                ('results_report', '=', self.start.report.id),
                ('laboratory', '=', laboratory_id),
                ], limit=1)
            if not actual_version:
                version, = ResultsVersion.create([{
                    'results_report': self.start.report.id,
                    'laboratory': laboratory_id,
                    'details': [('create', [details])],
                    }])
                reports_details = [d.id for d in version.details]
            else:
                actual_version = actual_version[0]
                draft_detail = ResultsDetail.search([
                    ('report_version', '=', actual_version.id),
                    ('state', '=', 'draft'),
                    ], limit=1)
                if not draft_detail:
                    if ResultsDetail.search_count([
                            ('report_version', '=', actual_version.id),
                            ('state', 'not in', ['released', 'annulled']),
                            ]) > 0:
                        raise UserError(gettext(
                            'lims.msg_invalid_report_state'))

                    details['report_version'] = actual_version.id
                    detail, = ResultsDetail.create([details])
                    ResultsDetail.update_from_valid_version([detail])
                    reports_details = [detail.id]
                else:
                    draft_detail = draft_detail[0]
                    for sample in samples:
                        existing_sample = ResultsSample.search([
                            ('version_detail', '=', draft_detail.id),
                            ('notebook', '=', sample['notebook']),
                            ], limit=1)
                        if not existing_sample:
                            sample['version_detail'] = draft_detail.id
                            ResultsSample.create([sample])
                        else:
                            del sample['notebook']
                            ResultsSample.write(existing_sample, sample)

                    # do not overwrite some fields of the draft detail
                    for field in ResultsDetail._get_fields_not_overwrite():
                        if field in details:
                            del details[field]
                    ResultsDetail.write([draft_detail], details)
                    reports_details = [draft_detail.id]

            reports_created.extend(reports_details)

        else:  # Not Result report selected

            parties = {}
            for notebook in self.start.notebooks:
                key = notebook.id
                if self.start.group_samples:
                    key = (notebook.party.id,
                        notebook.fraction.cie_fraction_type)
                if key not in parties:
                    parties[key] = {
                        'party': notebook.party.id,
                        'entry': notebook.fraction.entry.id,
                        'cie_fraction_type': (
                            notebook.fraction.cie_fraction_type),
                        'english_report': (
                            notebook.fraction.entry.english_report),
                        'lines': [],
                        }
                lines = notebook._get_lines_for_reporting(laboratory_id,
                    state)
                parties[key]['lines'].extend(lines)

            reports_details = []
            for party in parties.values():
                grouped_reports = {}
                for line in party['lines']:
                    report_grouper = line.analysis_detail.report_grouper
                    if report_grouper not in grouped_reports:
                        grouped_reports[report_grouper] = []
                    grouped_reports[report_grouper].append(line)

                for grouper, nlines in grouped_reports.items():
                    notebooks = {}
                    for line in nlines:
                        if line.notebook.id not in notebooks:
                            notebooks[line.notebook.id] = {
                                'notebook': line.notebook.id,
                                'lines': [],
                                }
                        notebooks[line.notebook.id]['lines'].append(line)

                    samples = []
                    for notebook in notebooks.values():
                        notebook_lines = [{
                            'notebook_line': line.id,
                            'corrected': corrected,
                            }
                            for line in notebook['lines']]
                        samples.append({
                            'notebook': notebook['notebook'],
                            'notebook_lines': [('create', notebook_lines)],
                            })
                    details = {
                        'type': self.start.type,
                        'signer': signer,
                        'samples': [('create', samples)],
                        }
                    details.update(ResultsDetail._get_fields_from_samples(
                        samples))
                    versions = {
                        'laboratory': laboratory_id,
                        'details': [('create', [details])],
                        }
                    reports = {
                        'party': party['party'],
                        'entry': party['entry'],
                        'notebook': None,
                        'report_grouper': grouper,
                        'cie_fraction_type': party['cie_fraction_type'],
                        'english_report': party['english_report'],
                        'versions': [('create', [versions])],
                        }
                    report_detail = self._get_results_report(laboratory_id,
                        reports, versions, details, samples,
                        self.start.append_samples)
                    reports_details.extend(report_detail)

            reports_created.extend(reports_details)

        self.start.reports_created = reports_created
        return 'open_'

    def _get_results_report(self, laboratory_id, reports, versions, details,
            samples, append=False):
        pool = Pool()
        ResultsReport = pool.get('lims.results_report')
        ResultsVersion = pool.get('lims.results_report.version')
        ResultsDetail = pool.get('lims.results_report.version.detail')
        ResultsSample = pool.get('lims.results_report.version.detail.sample')

        if not append:
            report, = ResultsReport.create([reports])
            reports_details = [d.id for d in report.versions[0].details]
            return reports_details

        existing_details = ResultsDetail.search([
            ('laboratory', '=', laboratory_id),
            ('samples.notebook', '=', samples[0]['notebook']),
            ])
        if existing_details:
            current_reports = [d.report_version.results_report.id
                for d in existing_details]
        else:
            existing_details = ResultsDetail.search([
                ('samples.notebook', '=', samples[0]['notebook']),
                ])
            if existing_details:
                current_reports = [d.report_version.results_report.id
                    for d in existing_details]
            else:
                report, = ResultsReport.create([reports])
                reports_details = [d.id for d in report.versions[0].details]
                return reports_details

        actual_report = ResultsReport.search([
            ('id', 'in', current_reports),
            ('report_grouper', '=', reports['report_grouper']),
            ('cie_fraction_type', '=', reports['cie_fraction_type']),
            ], limit=1)
        if not actual_report:
            report, = ResultsReport.create([reports])
            reports_details = [d.id for d in report.versions[0].details]
            return reports_details

        actual_report = actual_report[0]
        actual_version = ResultsVersion.search([
            ('results_report', '=', actual_report.id),
            ('laboratory', '=', laboratory_id),
            ], limit=1)
        if not actual_version:
            version, = ResultsVersion.create([{
                'results_report': actual_report.id,
                'laboratory': laboratory_id,
                'details': [('create', [details])],
                }])
            reports_details = [d.id for d in version.details]
            return reports_details

        actual_version = actual_version[0]
        draft_detail = ResultsDetail.search([
            ('report_version', '=', actual_version.id),
            ('state', '=', 'draft'),
            ], limit=1)
        if not draft_detail:
            if ResultsDetail.search_count([
                    ('report_version', '=', actual_version.id),
                    ('state', 'not in', ['released', 'annulled']),
                    ]) > 0:
                raise UserError(gettext(
                    'lims.msg_invalid_report_state'))

            details['report_version'] = actual_version.id
            detail, = ResultsDetail.create([details])
            ResultsDetail.update_from_valid_version([detail])
            reports_details = [detail.id]
            return reports_details

        draft_detail = draft_detail[0]
        for sample in samples:
            existing_sample = ResultsSample.search([
                ('version_detail', '=', draft_detail.id),
                ('notebook', '=', sample['notebook']),
                ], limit=1)
            if not existing_sample:
                sample['version_detail'] = draft_detail.id
                ResultsSample.create([sample])
            else:
                del sample['notebook']
                ResultsSample.write(existing_sample, sample)

        reports_details = [draft_detail.id]
        return reports_details

    def do_open_(self, action):
        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', 'in', [r.id for r in self.start.reports_created]),
            ])
        self.start.reports_created = None
        return action, {}

    def transition_open_(self):
        return 'end'

    def end(self):
        return 'reload'


class OpenSampleEntry(Wizard):
    'Sample Entry'
    __name__ = 'lims.notebook.open_entry'

    start = StateAction('lims.act_lims_entry_list')

    def do_start(self, action):
        Notebook = Pool().get('lims.notebook')

        active_ids = Transaction().context['active_ids']
        notebooks = Notebook.browse(active_ids)

        entries_ids = [n.fraction.sample.entry.id for n in notebooks]

        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', 'in', entries_ids),
            ])
        action['name'] += ' (%s)' % ', '.join(n.rec_name for n in notebooks)
        return action, {}


class ServiceResultsReport(Wizard):
    'Service Results Report'
    __name__ = 'lims.service.results_report'

    start = StateAction('lims.act_lims_results_report_list')

    def do_start(self, action):
        pool = Pool()
        Service = pool.get('lims.service')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        service = Service(Transaction().context['active_id'])

        results_report_ids = []
        details = EntryDetailAnalysis.search([
            ('service', '=', service.id),
            ])
        if details:
            results_report_ids = [d.results_report.id for d in details
                if d.results_report]

        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', 'in', results_report_ids),
            ])
        action['name'] += ' (%s)' % service.rec_name
        return action, {}


class FractionResultsReport(Wizard):
    'Fraction Results Report'
    __name__ = 'lims.fraction.results_report'

    start = StateAction('lims.act_lims_results_report_list')

    def do_start(self, action):
        pool = Pool()
        Fraction = pool.get('lims.fraction')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        fraction = Fraction(Transaction().context['active_id'])

        results_report_ids = []
        details = EntryDetailAnalysis.search([
            ('fraction', '=', fraction.id),
            ])
        if details:
            results_report_ids = [d.results_report.id for d in details
                if d.results_report]

        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', 'in', results_report_ids),
            ])
        action['name'] += ' (%s)' % fraction.rec_name
        return action, {}


class SampleResultsReport(Wizard):
    'Sample Results Report'
    __name__ = 'lims.sample.results_report'

    start = StateAction('lims.act_lims_results_report_list')

    @classmethod
    def check_access(cls):
        pass

    def do_start(self, action):
        pool = Pool()
        Sample = pool.get('lims.sample')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        active_ids = Transaction().context['active_ids']
        samples = Sample.browse(active_ids)

        results_report_ids = []
        details = EntryDetailAnalysis.search([('sample', 'in', active_ids)])
        if details:
            results_report_ids = [d.results_report.id for d in details
                if d.results_report]

        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', 'in', results_report_ids),
            ])
        action['name'] += ' (%s)' % ', '.join(
            s.rec_name for s in samples)
        return action, {}


class SampleResultsReportInProgress(Wizard):
    'Sample Results Report in progress'
    __name__ = 'lims.sample.results_report.in_progress'

    start = StateAction('lims.act_lims_results_report_version_detail')

    @classmethod
    def check_access(cls):
        pass

    def do_start(self, action):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Sample = pool.get('lims.sample')
        Fraction = pool.get('lims.fraction')
        Notebook = pool.get('lims.notebook')
        ResultsSample = pool.get('lims.results_report.version.detail.sample')
        ResultsDetail = pool.get('lims.results_report.version.detail')

        active_ids = Transaction().context['active_ids']
        sample_ids = ', '.join(str(r) for r in active_ids)
        samples = Sample.browse(active_ids)

        cursor.execute('SELECT rd.id '
            'FROM "' + ResultsDetail._table + '" rd '
                'INNER JOIN "' + ResultsSample._table + '" rs '
                'ON rd.id = rs.version_detail '
                'INNER JOIN "' + Notebook._table + '" n '
                'ON n.id = rs.notebook '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON f.id = n.fraction '
            'WHERE f.sample IN (' + sample_ids + ') '
                'AND rd.state NOT IN (\'released\', \'annulled\')')
        details_ids = [x[0] for x in cursor.fetchall()]

        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', 'in', details_ids),
            ])
        action['name'] += ' (%s)' % ', '.join(
            s.rec_name for s in samples)
        return action, {}


class OpenResultsReportSample(Wizard):
    'Results Report Sample'
    __name__ = 'lims.results_report.open_sample'

    start = StateAction('lims.act_lims_sample_list')

    def do_start(self, action):
        pool = Pool()
        ResultsReport = pool.get('lims.results_report')
        ResultsSample = pool.get('lims.results_report.version.detail.sample')

        active_ids = Transaction().context['active_ids']
        results_reports = ResultsReport.browse(active_ids)

        samples = ResultsSample.search([
            ('version_detail.report_version.results_report', 'in', active_ids),
            ])
        samples_ids = [s.notebook.fraction.sample.id for s in samples]

        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', 'in', samples_ids),
            ])
        action['name'] += ' (%s)' % ', '.join(
            r.rec_name for r in results_reports)
        return action, {}


class OpenResultsDetailEntry(Wizard):
    'Results Report Entry'
    __name__ = 'lims.results_report.version.detail.open_entry'

    start = StateAction('lims.act_lims_entry_list')

    def do_start(self, action):
        pool = Pool()
        ResultsDetail = pool.get('lims.results_report.version.detail')
        ResultsSample = pool.get('lims.results_report.version.detail.sample')

        active_ids = Transaction().context['active_ids']
        details = ResultsDetail.browse(active_ids)

        samples = ResultsSample.search([
            ('version_detail', 'in', active_ids),
            ])
        entries_ids = [s.notebook.fraction.sample.entry.id for s in samples]

        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', 'in', entries_ids),
            ])
        action['name'] += ' (%s)' % ', '.join(d.rec_name for d in details)
        return action, {}


class OpenResultsDetailAttachment(Wizard):
    'Results Report Attachment'
    __name__ = 'lims.results_report.version.detail.open_attachment'

    start = StateAction('lims.act_attachment')

    def do_start(self, action):
        ResultsDetail = Pool().get('lims.results_report.version.detail')

        active_ids = Transaction().context['active_ids']
        details = ResultsDetail.browse(active_ids)

        resources = self.get_resource(details)

        action['pyson_domain'] = PYSONEncoder().encode([
            ('resource', 'in', resources),
            ])
        action['name'] += ' (%s)' % ', '.join(d.rec_name for d in details)
        return action, {}

    def get_resource(self, details):
        res = []
        for detail in details:
            res.append(self._get_resource(detail))
            for sample in detail.samples:
                res.append(self._get_resource(sample))
                res.append(self._get_resource(sample.notebook))
                res.append(self._get_resource(sample.notebook.fraction))
                res.append(self._get_resource(
                    sample.notebook.fraction.sample))
                res.append(self._get_resource(
                    sample.notebook.fraction.sample.entry))
                for line in sample.notebook_lines:
                    if not line.notebook_line:
                        continue
                    res.append(self._get_resource(line))
                    res.append(self._get_resource(line.notebook_line))
        return res

    def _get_resource(self, obj):
        return '%s,%s' % (obj.__name__, obj.id)


class ResultsReportRelease(Wizard):
    'Release Report'
    __name__ = 'lims.results_report_release'

    start = StateTransition()

    def transition_start(self):
        ResultsDetail = Pool().get('lims.results_report.version.detail')
        details_to_release = []
        for active_id in Transaction().context['active_ids']:
            detail = ResultsDetail(active_id)
            if detail.state != 'revised':
                continue
            details_to_release.append(detail)
        if details_to_release:
            ResultsDetail.release(details_to_release)
        return 'end'

    def end(self):
        return 'reload'


class ResultsReportAnnulationStart(ModelView):
    'Report Annulation'
    __name__ = 'lims.results_report_annulation.start'

    annulment_reason = fields.Text('Annulment reason', required=True,
        translate=True)
    annulment_reason_print = fields.Boolean(
        'Print annulment reason in next version')

    @staticmethod
    def default_annulment_reason_print():
        return True


class ResultsReportAnnulation(Wizard):
    'Report Annulation'
    __name__ = 'lims.results_report_annulation'

    start = StateView('lims.results_report_annulation.start',
        'lims.lims_results_report_annulation_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Annul', 'annul', 'tryton-ok', default=True),
            ])
    annul = StateTransition()

    def transition_annul(self):
        ResultsDetail = Pool().get('lims.results_report.version.detail')

        details = ResultsDetail.search([
            ('id', 'in', Transaction().context['active_ids']),
            ])
        if details:
            ResultsDetail.unlink_notebook_lines(details)
            ResultsDetail.write(details, {
                'state': 'annulled',
                'valid': False,
                'report_cache': None,
                'report_format': None,
                'report_cache_eng': None,
                'report_format_eng': None,
                'annulment_uid': int(Transaction().user),
                'annulment_date': datetime.now(),
                'annulment_reason': self.start.annulment_reason,
                'annulment_reason_print': self.start.annulment_reason_print,
                })
        return 'end'


class NewResultsReportVersionStart(ModelView):
    'New Results Report Version'
    __name__ = 'lims.results_report.version.detail.new_version.start'

    type = fields.Selection([
        ('preliminary', 'Preliminary'),
        ('complementary', 'Complementary'),
        ('corrective', 'Corrective'),
        ], 'Type', states={'readonly': True})
    preliminary = fields.Boolean('Preliminary')
    corrective = fields.Boolean('Corrective',
        states={'invisible': ~Eval('type').in_([
            'complementary', 'corrective'])},
        depends=['type'])
    review_reason = fields.Text('Review reason', required=True,
        translate=True)
    review_reason_print = fields.Boolean(
        'Print review reason in next version')
    report_created = fields.Many2One('lims.results_report.version.detail',
        'Report created')

    @staticmethod
    def default_review_reason_print():
        return False

    @fields.depends('preliminary', 'corrective')
    def on_change_with_type(self, name=None):
        if self.preliminary:
            return 'preliminary'
        if self.corrective:
            return 'corrective'
        return 'complementary'


class NewResultsReportVersion(Wizard):
    'New Results Report Version'
    __name__ = 'lims.results_report.version.detail.new_version'

    start = StateView('lims.results_report.version.detail.new_version.start',
        'lims.results_report_version_detail_new_version_start_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Generate', 'generate', 'tryton-ok', default=True),
            ])
    generate = StateTransition()
    open_ = StateAction('lims.act_lims_results_report_version_detail')

    def default_start(self, fields):
        ResultsDetail = Pool().get('lims.results_report.version.detail')

        res = {
            'type': 'complementary',
            'preliminary': False,
            'corrective': False,
            }
        valid_detail = ResultsDetail(Transaction().context['active_id'])
        if valid_detail.type == 'preliminary':
            res['preliminary'] = True
            res['type'] = 'preliminary'
        return res

    def transition_generate(self):
        ResultsDetail = Pool().get('lims.results_report.version.detail')

        valid_detail = ResultsDetail(Transaction().context['active_id'])
        defaults = {
            'report_version': valid_detail.report_version.id,
            'type': self.start.type,
            }
        new_version, = ResultsDetail.create([defaults])
        ResultsDetail.update_from_valid_version([new_version])
        self.start.report_created = new_version

        ResultsDetail.write([valid_detail], {
            'review_reason': self.start.review_reason,
            'review_reason_print': self.start.review_reason_print,
            })
        return 'open_'

    def do_open_(self, action):
        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', '=', self.start.report_created.id),
            ])
        return action, {}

    def transition_open_(self):
        return 'end'


class PrintResultReport(Wizard):
    'Print Results Report'
    __name__ = 'lims.print_result_report'

    start = StateTransition()
    print_ = StateReport('lims.result_report')

    def transition_start(self):
        return 'print_'

    def do_print_(self, action):
        data = {}
        data['id'] = Transaction().context['active_ids'].pop()
        data['ids'] = [data['id']]
        return action, data

    def transition_print_(self):
        if Transaction().context['active_ids']:
            return 'print_'
        return 'end'


class ResultReport(Report):
    'Results Report'
    __name__ = 'lims.result_report'

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.__rpc__['execute'] = RPC(False)

    @classmethod
    def execute(cls, ids, data):
        ResultsDetail = Pool().get('lims.results_report.version.detail')
        if len(ids) > 1:
            raise UserError(gettext('lims.msg_multiple_reports'))

        results_report = ResultsDetail(ids[0])
        if results_report.state == 'annulled':
            raise UserError(gettext('lims.msg_annulled_report'))

        if data is None:
            data = {}
        current_data = data.copy()
        current_data['alt_lang'] = None
        result_orig = super().execute(ids, current_data)
        current_data['alt_lang'] = 'en'
        result_eng = super().execute(ids, current_data)

        save = False
        if results_report.english_report:
            if results_report.report_cache_eng:
                result = (results_report.report_format_eng,
                    results_report.report_cache_eng) + result_eng[2:]
            else:
                result = result_eng
                if ('english_report' in current_data and
                        current_data['english_report']):
                    results_report.report_format_eng, \
                        results_report.report_cache_eng = result_eng[:2]
                    save = True
        else:
            if results_report.report_cache:
                result = (results_report.report_format,
                    results_report.report_cache) + result_orig[2:]
            else:
                result = result_orig
                if ('english_report' in current_data and
                        not current_data['english_report']):
                    results_report.report_format, \
                        results_report.report_cache = result_orig[:2]
                    save = True
        if save:
            results_report.save()

        return result

    @classmethod
    def get_context(cls, records, data):
        pool = Pool()
        Company = pool.get('company.company')
        ResultsDetail = pool.get('lims.results_report.version.detail')
        ResultsLine = pool.get('lims.results_report.version.detail.line')
        NotebookLine = pool.get('lims.notebook.line')
        Sample = pool.get('lims.sample')
        RangeType = pool.get('lims.range.type')

        report_context = super().get_context(records, data)

        if data.get('alt_lang'):
            lang_code = data['alt_lang']
        elif report_context['user'].language:
            lang_code = report_context['user'].language.code
        else:
            lang_code = None
        report_context['alt_lang'] = lang_code

        with Transaction().set_context(language=lang_code):
            if 'id' in data:
                report = ResultsDetail(data['id'])
            else:
                report = ResultsDetail(records[0].id)
        report_context['obj'] = report
        report_context['get_grouped_lines'] = cls.get_grouped_lines
        report_context['get_value'] = cls.get_value

        company = Company(Transaction().context.get('company'))
        report_context['company'] = company

        report_context['number'] = report.rec_name
        report_context['replace_number'] = ''
        if report.number != '1':
            with Transaction().set_context(language=lang_code):
                prev_number = "%s-%s" % (report.report_version.number,
                    int(report.number) - 1)
                report_context['replace_number'] = (
                    gettext('lims.msg_replace_number', report=prev_number))
        report_context['print_date'] = get_print_date()
        report_context['party'] = (
            report.report_version.results_report.party.rec_name)
        try:
            party_address = (
                report.report_version.results_report.party.address_get(
                    type='invoice'))
        except AttributeError:
            party_address = (
                report.report_version.results_report.party.address_get())

        report_context['party_address'] = party_address.full_address.replace(
            '\n', ' - ')

        report_context['report_section'] = report.report_section
        report_context['report_type'] = report.report_type
        report_context['report_result_type'] = report.report_result_type
        group_field = ('final_concentration' if
            report.report_result_type in ('both', 'both_range') else
            'initial_concentration')

        report_context['signer'] = ''
        report_context['signer_role'] = ''
        report_context['signature'] = None
        report_context['headquarters'] = report.laboratory.headquarters

        if report.signer:
            report_context['signer'] = report.signer.rec_name
            report_context['signer_role'] = report.signer.role
            if report.signer.signature:
                report_context['signature'] = report.signer.signature

        enac = False
        enac_all_acredited = True

        initial_unit = None

        min_start_date = None
        max_end_date = None
        min_confirmation_date = None

        obs_ql = False
        obs_dl = False
        obs_uncert = False
        obs_result_range = False
        report_context['range_title'] = ''
        if report.report_result_type in ('result_range', 'both_range'):
            obs_result_range = True
            with Transaction().set_context(language=lang_code):
                range_type = RangeType(report.resultrange_origin.id)
            report_context['range_title'] = range_type.resultrange_title
        obs_rm_c_f = False

        tas_project = False
        stp_project = False
        stp_polisample_project = False
        water_project = False
        alcohol = False
        dry_matter = False

        comments = {}
        fractions = {}
        methods = {}
        pnt_methods = {}
        notebook_lines = ResultsLine.search([
            ('detail_sample.version_detail.id', '=', report.id),
            ('hide', '=', False),
            ('notebook_line', '!=', None),
            ], order=[('detail_sample', 'ASC')])
        if not notebook_lines:
            raise UserError(gettext('lims.msg_empty_report'))

        with Transaction().set_context(language=lang_code):
            reference_sample = Sample(
                notebook_lines[0].notebook_line.fraction.sample.id)
        if (report_context['report_section'] == 'rp' and
                hasattr(reference_sample.entry, 'project_type') and
                getattr(reference_sample.entry, 'project_type') ==
                'study_plan'):
            if report.report_type == 'normal' and not stp_project:
                stp_project = True
            if (report.report_type == 'polisample' and not
                    stp_polisample_project):
                stp_polisample_project = True
        if (hasattr(reference_sample.entry, 'project_type') and
                getattr(reference_sample.entry, 'project_type') ==
                'tas'):
            tas_project = True
        if (hasattr(reference_sample.entry, 'project_type') and
                getattr(reference_sample.entry, 'project_type') ==
                'water'):
            water_project = True

        for line in notebook_lines:
            with Transaction().set_context(language=lang_code):
                t_line = NotebookLine(line.notebook_line.id)
                sample = Sample(line.notebook_line.fraction.sample.id)

            key = t_line.fraction.id
            if key not in fractions:
                fractions[key] = {
                    'obj': line.detail_sample,
                    'fraction': sample.number,
                    'date': sample.date2,
                    'client_description': (
                        sample.sample_client_description),
                    'number': sample.number,
                    'label': '(%s - %s)' % (sample.number,
                        sample.label),
                    'packages_quantity': sample.packages_quantity,
                    'package_type': (sample.package_type.description
                        if sample.package_type else ''),
                    'package_state': (
                        sample.package_state.description
                        if sample.package_state else ''),
                    'producer': (sample.producer.rec_name
                        if sample.producer else
                        gettext('lims.msg_data_not_specified')),
                    'obj_description': (sample.obj_description.description
                        if sample.obj_description else
                        sample.obj_description_manual),
                    'concentrations': {},
                    }
                if (report.report_section == 'rp' and
                        report.report_type == 'polisample'):
                    fractions[key]['label'] = sample.label
                if stp_polisample_project:
                    fractions[key]['stp_code'] = sample.entry.project.code
                    fractions[key]['stp_application_date'] = (
                        sample.application_date)
                    fractions[key]['stp_sampling_date'] = sample.sampling_date
                    fractions[key]['stp_zone'] = (sample.cultivation_zone
                        if sample.cultivation_zone else '')
                    fractions[key]['stp_after_application_days'] = (
                        sample.after_application_days)
                    fractions[key]['stp_treatment'] = sample.treatment
                    fractions[key]['stp_dosis'] = sample.dosis
                    fractions[key]['stp_repetition'] = sample.glp_repetitions
                    fractions[key]['stp_z_senasa_protocol'] = (
                        sample.z_senasa_protocol)
                    fractions[key]['stp_variety'] = (
                        sample.variety.description if
                        sample.variety else '')
                if water_project:
                    if sample.sampling_datetime:
                        fractions[key]['water_sampling_date'] = (
                            cls.format_date(sample.sampling_datetime.date(),
                                report_context['user'].language))
                    else:
                        fractions[key]['water_sampling_date'] = gettext(
                            'lims.msg_not_done')

            record = {
                'obj': line,
                'order': t_line.analysis.order or 9999,
                'acredited': cls.get_accreditation(
                    t_line.notebook.product_type,
                    t_line.notebook.matrix,
                    t_line.analysis,
                    t_line.method),
                'pnt': t_line.method.pnt,
                }
            record['analysis'] = cls.get_analysis(
                report_context['report_section'], t_line, language=lang_code)
            record['result'], obs_ql = cls.get_result(
                report_context['report_section'], t_line, obs_ql,
                language=lang_code)
            record['rp_order'] = float(2)
            try:
                record['rp_order'] = float(record['result']) * -1
            except (TypeError, ValueError):
                try:
                    if str(record['result']).startswith('<'):
                        record['rp_order'] = float(1)
                except UnicodeEncodeError:
                    pass
            record['converted_result'], obs_ql = cls.get_converted_result(
                report_context['report_section'],
                report_context['report_result_type'], t_line, obs_ql,
                language=lang_code)
            record['initial_unit'], obs_dl, obs_uncert = cls.get_initial_unit(
                report_context['report_section'],
                report_context['report_result_type'], t_line, obs_dl,
                obs_uncert, language=lang_code)
            record['final_unit'], obs_dl, obs_uncert = cls.get_final_unit(
                report_context['report_section'],
                report_context['report_result_type'], t_line, obs_dl,
                obs_uncert, language=lang_code)
            record['detection_limit'] = cls.get_detection_limit(
                report_context['report_section'],
                report_context['report_result_type'],
                report_context['report_type'], t_line,
                language=lang_code)
            record['reference'] = ''
            if obs_result_range:
                record['reference'] = str(cls.get_reference(range_type,
                    t_line, lang_code, report_context['report_section']))
            if (t_line.rm_correction_formula and (record['result'] or
                    (record['converted_result'] and
                    report_context['report_result_type'] in (
                        'both', 'both_range')))):
                obs_rm_c_f = True
                record['corrected'] = ''
            else:
                record['corrected'] = ''

            conc = getattr(t_line, group_field)
            if conc not in fractions[key]['concentrations']:
                fractions[key]['concentrations'][conc] = []
            fractions[key]['concentrations'][conc].append(record)

            if not enac and record['acredited'] == 'True':
                enac = True
            if enac_all_acredited and record['acredited'] == 'False':
                enac_all_acredited = False

            if not initial_unit and t_line.initial_unit:
                initial_unit = t_line.initial_unit.rec_name

            entry_id = t_line.fraction.sample.entry.id
            if entry_id not in comments:
                comments[entry_id] = {
                    'report_comments': (
                        t_line.fraction.sample.entry.report_comments),
                    'samples': {},
                    }
            if sample.id not in comments[entry_id]['samples']:
                comments[entry_id]['samples'][sample.id] = (
                    sample.report_comments)

            method_id = t_line.method.id
            if method_id not in methods:
                methods[method_id] = {
                    'method': t_line.method.name,
                    'analysis': [],
                    }
            methods[method_id]['analysis'].append(record['analysis'])

            if record['pnt'] not in pnt_methods:
                pnt_methods[record['pnt']] = {
                    'pnt': record['pnt'],
                    'method': t_line.method.name,
                    }

            if not reference_sample or sample.date < reference_sample.date:
                with Transaction().set_context(language=lang_code):
                    reference_sample = Sample(sample.id)

            if (t_line.start_date and (not min_start_date or
                    t_line.start_date < min_start_date)):
                min_start_date = t_line.start_date
            if (t_line.end_date and (not max_end_date or
                    t_line.end_date > max_end_date)):
                max_end_date = t_line.end_date
            if (not min_confirmation_date or
                    (t_line.analysis_detail.confirmation_date and
                    t_line.analysis_detail.confirmation_date <
                    min_confirmation_date)):
                min_confirmation_date = (
                    t_line.analysis_detail.confirmation_date)

        with Transaction().set_context(language=lang_code):
            report_context['sample_producer'] = (
                reference_sample.producer.rec_name if reference_sample.producer
                else gettext('lims.msg_data_not_specified'))
            report_context['sample_obj_description'] = (
                reference_sample.obj_description.description
                if reference_sample.obj_description
                else reference_sample.obj_description_manual)
        report_context['sample_date'] = reference_sample.date2
        report_context['sample_confirmation_date'] = min_confirmation_date
        report_context['min_start_date'] = min_start_date
        report_context['max_end_date'] = max_end_date
        report_context['sample_packages_quantity'] = (
            reference_sample.packages_quantity)
        report_context['sample_package_type'] = (
            reference_sample.package_type.description
            if reference_sample.package_type else '')
        report_context['sample_package_state'] = (
            reference_sample.package_state.description
            if reference_sample.package_state else '')
        if report.report_type == 'normal':
            report_context['sample_label'] = (
                reference_sample.label)
            report_context['sample_client_description'] = (
                reference_sample.sample_client_description)
            report_context['sample_number'] = reference_sample.number
            if report_context['report_section'] == 'for':
                report_context['sample_prodct_type'] = (
                    reference_sample.product_type.description)
                report_context['sample_matrix'] = (
                    reference_sample.matrix.description)

        if tas_project:
            report_context['tas_code'] = reference_sample.entry.project.code
        if stp_project:
            report_context['stp_code'] = reference_sample.entry.project.code
            report_context['stp_application_date'] = (
                reference_sample.application_date)
            report_context['stp_sampling_date'] = (
                reference_sample.sampling_date)
            report_context['stp_zone'] = (reference_sample.cultivation_zone
                if reference_sample.cultivation_zone else '')
            report_context['stp_after_application_days'] = (
                reference_sample.after_application_days)
            report_context['stp_treatment'] = reference_sample.treatment
            report_context['stp_dosis'] = reference_sample.dosis
            report_context['stp_repetition'] = reference_sample.glp_repetitions
            report_context['stp_z_senasa_protocol'] = (
                reference_sample.z_senasa_protocol)
            report_context['stp_variety'] = (
                reference_sample.variety.description if
                reference_sample.variety else '')
        if stp_polisample_project:
            report_context['stp_code'] = reference_sample.entry.project.code
        if water_project:
            if reference_sample.sampling_datetime:
                report_context['water_sampling_date'] = (
                    cls.format_date(reference_sample.sampling_datetime.date(),
                        report_context['user'].language))
            else:
                report_context['water_sampling_date'] = gettext(
                    'lims.msg_not_done')

        report_context['tas_project'] = 'True' if tas_project else 'False'
        report_context['stp_project'] = 'True' if stp_project else 'False'
        report_context['stp_polisample_project'] = ('True' if
            stp_polisample_project else 'False')
        report_context['water_project'] = 'True' if water_project else 'False'

        if 'VINO' in reference_sample.product_type.code:
            alcohol = True
        if (report_context['report_section'] in ('amb', 'sq') and
                reference_sample.matrix.code in ('SUELO', 'LODO')):
            dry_matter = True

        sorted_fractions = sorted(list(fractions.values()),
            key=lambda x: x['fraction'])
        with Transaction().set_context(language=lang_code):
            for fraction in sorted_fractions:
                for conc, lines in fraction['concentrations'].items():
                    if report_context['report_section'] == 'rp':
                        sorted_lines = sorted(lines, key=lambda x: (
                            x['rp_order'], x['analysis']))
                    else:
                        sorted_lines = sorted(lines, key=lambda x: (
                            x['order'], x['analysis']))
                    fraction['concentrations'][conc] = {
                        'label': '',
                        'unit_label': '',
                        'lines': sorted_lines,
                        }

                    conc_is_numeric = True
                    try:
                        numeric_conc = float(conc)
                    except (TypeError, ValueError):
                        conc_is_numeric = False
                    hide_concentration_label = (
                        report_context['report_section'] in ('amb', 'sq') and
                        report_context['report_result_type'] in (
                            'both', 'both_range'))
                    if conc and conc != '-' and not hide_concentration_label:
                        if conc == 'Muestra Recibida':
                            fraction['concentrations'][conc]['label'] = ''
                        elif conc_is_numeric and numeric_conc < 100:
                            fraction['concentrations'][conc]['label'] = (
                                gettext(
                                    'lims.msg_concentration_label_2',
                                    concentration=conc
                                    ))
                        else:
                            fraction['concentrations'][conc]['label'] = (
                                gettext(
                                    'lims.msg_concentration_label_3',
                                    concentration=conc
                                    ))

                    show_unit_label = False
                    for line in sorted_lines:
                        if line['converted_result']:
                            show_unit_label = True
                            break
                    if show_unit_label:
                        if dry_matter:
                            fraction['concentrations'][conc][
                                    'unit_label'] = (
                                gettext('lims.msg_final_unit_label_4'))
                        else:
                            if conc_is_numeric:
                                if alcohol:
                                    fraction['concentrations'][conc][
                                            'unit_label'] = (
                                        gettext(
                                            'lims.msg_final_unit_label_1',
                                            concentration=conc))
                                else:
                                    fraction['concentrations'][conc][
                                            'unit_label'] = (
                                        gettext(
                                            'lims.msg_final_unit_label_3',
                                            concentration=conc))
                            else:
                                fraction['concentrations'][conc][
                                        'unit_label'] = (
                                    gettext(
                                        'lims.msg_final_unit_label_2',
                                        concentration=conc))

        report_context['fractions'] = sorted_fractions

        report_context['methods'] = []
        for method in methods.values():
            concat_lines = ', '.join(list(set(method['analysis'])))
            method['analysis'] = concat_lines
            report_context['methods'].append(method)

        report_context['pnt_methods'] = [m for m in pnt_methods.values()]

        report_context['enac'] = 'True' if enac else 'False'
        if enac:
            with Transaction().set_context(language=lang_code):
                if enac_all_acredited:
                    report_context['enac_label'] = (
                        gettext('lims.msg_enac_all_acredited'))
                else:
                    report_context['enac_label'] = gettext(
                        'lims.msg_enac_acredited')
        else:
            report_context['enac_label'] = ''

        report_context['initial_unit'] = initial_unit

        report_context['comments'] = ''
        for entry_comment in comments.values():
            if entry_comment['report_comments']:
                if report_context['comments']:
                    report_context['comments'] += '\n'
                report_context['comments'] += entry_comment['report_comments']
            for sample_comment in entry_comment['samples'].values():
                if sample_comment:
                    if report_context['comments']:
                        report_context['comments'] += '\n'
                    report_context['comments'] += sample_comment

        if report.comments:
            if report_context['comments']:
                report_context['comments'] += '\n'
            report_context['comments'] += report.comments

        if obs_ql and report_context['report_section']:
            with Transaction().set_context(language=lang_code):
                if report_context['comments']:
                    report_context['comments'] += '\n'
                report_context['comments'] += gettext('lims.msg_obs_ql')
        if obs_dl and report_context['report_section']:
            with Transaction().set_context(language=lang_code):
                if report_context['comments']:
                    report_context['comments'] += '\n'
                report_context['comments'] += gettext('lims.msg_obs_dl')
        if obs_uncert:
            with Transaction().set_context(language=lang_code):
                if report_context['comments']:
                    report_context['comments'] += '\n'
                report_context['comments'] += gettext('lims.msg_obs_uncert')
        if obs_result_range and range_type.resultrange_comments:
            if report_context['comments']:
                report_context['comments'] += '\n'
            report_context['comments'] += range_type.resultrange_comments
        if obs_rm_c_f:
            with Transaction().set_context(language=lang_code):
                if report_context['comments']:
                    report_context['comments'] += '\n'
                report_context['comments'] += gettext('lims.msg_obs_rm_c_f')

        report_context['annulment_reason'] = ''
        report_context['review_reason'] = ''
        if report.number != '1':
            with Transaction().set_context(language=lang_code):
                prev_report = ResultsDetail.search([
                    ('report_version', '=', report.report_version.id),
                    ('number', '=', str(int(report.number) - 1)),
                    ])
                if prev_report:
                    if prev_report[0].annulment_reason_print:
                        report_context['annulment_reason'] = (
                            prev_report[0].annulment_reason)
                    if prev_report[0].review_reason_print:
                        report_context['review_reason'] = (
                            prev_report[0].review_reason)

        return report_context

    @classmethod
    def get_accreditation(cls, product_type, matrix, analysis, method):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Typification = pool.get('lims.typification')
        TechnicalScopeVersionLine = pool.get(
            'lims.technical.scope.version.line')
        TechnicalScopeVersion = pool.get('lims.technical.scope.version')
        TechnicalScope = pool.get('lims.technical.scope')
        CertificationType = pool.get('lims.certification.type')

        cursor.execute('SELECT ct.report '
            'FROM "' + Typification._table + '" t '
                'INNER JOIN "' + TechnicalScopeVersionLine._table + '" svl '
                'ON t.id = svl.typification '
                'INNER JOIN "' + TechnicalScopeVersion._table + '" sv '
                'ON svl.version = sv.id '
                'INNER JOIN "' + TechnicalScope._table + '" s '
                'ON sv.technical_scope = s.id '
                'INNER JOIN "' + CertificationType._table + '" ct '
                'ON s.certification_type = ct.id '
            'WHERE sv.valid IS TRUE '
                'AND t.product_type = %s '
                'AND t.matrix = %s '
                'AND t.analysis = %s '
                'AND t.method = %s '
                'AND t.valid IS TRUE',
            (product_type.id, matrix.id, analysis.id, method.id))
        for x in cursor.fetchall():
            if x[0]:
                return 'True'
        return 'False'

    @classmethod
    def get_analysis(cls, report_section, notebook_line, language):
        pool = Pool()
        Analysis = pool.get('lims.analysis')
        with Transaction().set_context(language=language):
            analysis = Analysis(notebook_line.analysis.id)
        res = analysis.description
        if report_section == 'mi':
            if analysis.gender_species:
                res = analysis.gender_species
        return res

    @classmethod
    def get_result(cls, report_section, notebook_line, obs_ql, language):
        literal_result = notebook_line.literal_result
        result = notebook_line.result
        decimals = notebook_line.decimals
        result_modifier = notebook_line.result_modifier

        with Transaction().set_context(language=language):
            res = ''
            if report_section in ('amb', 'for', 'rp', 'sq'):
                if literal_result:
                    res = literal_result
                else:
                    if result:
                        res = round(float(result), decimals)
                        if decimals == 0:
                            res = int(res)
                    else:
                        res = ''
                    if result_modifier == 'eq':
                        res = res
                    elif result_modifier == 'low':
                        res = gettext('lims.msg_quantification_limit', loq=res)
                        obs_ql = True
                    elif result_modifier == 'd':
                        res = gettext('lims.msg_d')
                    elif result_modifier == 'nd':
                        res = gettext('lims.msg_nd')
                    elif result_modifier == 'ni':
                        res = ''
                    elif result_modifier == 'pos':
                        res = gettext('lims.msg_pos')
                    elif result_modifier == 'neg':
                        res = gettext('lims.msg_neg')
                    elif result_modifier == 'pre':
                        res = gettext('lims.msg_pre')
                    elif result_modifier == 'abs':
                        res = gettext('lims.msg_abs')
                    else:
                        res = result_modifier
            elif report_section == 'mi':
                if literal_result:
                    res = literal_result
                else:
                    if result:
                        res = round(float(result), decimals)
                        if decimals == 0:
                            res = int(res)
                    else:
                        res = ''
                    if result_modifier == 'eq':
                        res = res
                    elif result_modifier == 'low':
                        res = '< %s' % res
                    elif result_modifier == 'd':
                        res = gettext('lims.msg_d')
                    elif result_modifier == 'nd':
                        res = gettext('lims.msg_nd')
                    elif result_modifier == 'pos':
                        res = gettext('lims.msg_pos')
                    elif result_modifier == 'neg':
                        res = gettext('lims.msg_neg')
                    elif result_modifier == 'pre':
                        res = gettext('lims.msg_pre')
                    elif result_modifier == 'abs':
                        res = gettext('lims.msg_abs')
            return res, obs_ql

    @classmethod
    def get_converted_result(cls, report_section, report_result_type,
            notebook_line, obs_ql, language):
        if (report_section in ('for', 'mi', 'rp') or
                report_result_type not in ('both', 'both_range')):
            return '', obs_ql

        literal_result = notebook_line.literal_result
        converted_result = notebook_line.converted_result
        analysis = notebook_line.analysis.code
        decimals = notebook_line.decimals
        converted_result_modifier = notebook_line.converted_result_modifier

        with Transaction().set_context(language=language):
            res = ''
            if analysis != '0001' and not literal_result:
                if converted_result_modifier == 'neg':
                    res = gettext('lims.msg_neg')
                elif converted_result_modifier == 'pos':
                    res = gettext('lims.msg_pos')
                elif converted_result_modifier == 'pre':
                    res = gettext('lims.msg_pre')
                elif converted_result_modifier == 'abs':
                    res = gettext('lims.msg_abs')
                elif converted_result_modifier == 'd':
                    res = gettext('lims.msg_d')
                elif converted_result_modifier == 'nd':
                    res = gettext('lims.msg_nd')
                else:
                    if converted_result and converted_result_modifier != 'ni':
                        res = round(float(converted_result), decimals)
                        if decimals == 0:
                            res = int(res)
                        if converted_result_modifier == 'low':
                            res = gettext(
                                'lims.msg_quantification_limit', loq=res)
                            obs_ql = True
            return res, obs_ql

    @classmethod
    def get_initial_unit(cls, report_section, report_result_type,
            notebook_line, obs_dl, obs_uncert, language):
        if not notebook_line.initial_unit:
            return '', obs_dl, obs_uncert

        initial_unit = notebook_line.initial_unit.rec_name
        literal_result = notebook_line.literal_result
        result_modifier = notebook_line.result_modifier
        detection_limit = notebook_line.detection_limit
        converted_result = notebook_line.converted_result
        uncertainty = notebook_line.uncertainty
        decimals = notebook_line.decimals

        with Transaction().set_context(language=language):
            if report_section == 'rp':
                res = ''
                if (not literal_result and result_modifier == 'eq' and
                        uncertainty and float(uncertainty) != 0):
                    res = round(float(uncertainty), decimals)
                    if decimals == 0:
                        res = int(res)
                    res = gettext(
                        'lims.msg_uncertainty', res=res, initial_unit='')
                    obs_uncert = True
            else:
                res = initial_unit
                if (literal_result or initial_unit == '-' or
                        result_modifier in ('pos', 'neg', 'ni')):
                    res = ''
                else:
                    if result_modifier in ('nd', 'low'):
                        if report_section == 'mi':
                            res = initial_unit
                        else:
                            if (not detection_limit or detection_limit in (
                                    '0', '0.0')):
                                res = initial_unit
                            else:
                                res = gettext('lims.msg_detection_limit',
                                    detection_limit=detection_limit,
                                    initial_unit=initial_unit)
                                obs_dl = True
                    else:
                        if (not converted_result and uncertainty and
                                float(uncertainty) != 0):
                            res = round(float(uncertainty), decimals)
                            if decimals == 0:
                                res = int(res)
                            res = gettext('lims.msg_uncertainty',
                                res=res, initial_unit=initial_unit)
                            obs_uncert = True
            return res, obs_dl, obs_uncert

    @classmethod
    def get_final_unit(cls, report_section, report_result_type,
            notebook_line, obs_dl, obs_uncert, language):
        if (report_section in ('for', 'mi', 'rp') or
                report_result_type not in ('both', 'both_range')):
            return '', obs_dl, obs_uncert
        if not notebook_line.final_unit:
            return '', obs_dl, obs_uncert

        final_unit = notebook_line.final_unit.rec_name
        analysis = notebook_line.analysis.code
        literal_result = notebook_line.literal_result
        converted_result_modifier = notebook_line.converted_result_modifier
        detection_limit = notebook_line.detection_limit
        converted_result = notebook_line.converted_result
        uncertainty = notebook_line.uncertainty
        decimals = notebook_line.decimals

        with Transaction().set_context(language=language):
            res = final_unit
            if (analysis == '0001' or literal_result or final_unit == '-' or
                    converted_result_modifier in ('pos', 'neg', 'ni')):
                res = ''
            else:
                if converted_result_modifier in ('nd', 'low'):
                    if (not detection_limit or detection_limit in (
                            '0', '0.0')):
                        res = final_unit
                    else:
                        res = gettext('lims.msg_detection_limit',
                            detection_limit=detection_limit,
                            initial_unit=final_unit)
                        obs_dl = True
                else:
                    if not converted_result:
                        res = ''
                    else:
                        if uncertainty and float(uncertainty) != 0:
                            res = round(float(uncertainty), decimals)
                            if decimals == 0:
                                res = int(res)
                            res = gettext('lims.msg_uncertainty',
                                res=res, initial_unit=final_unit)
                            obs_uncert = True
            return res, obs_dl, obs_uncert

    @classmethod
    def get_detection_limit(cls, report_section, report_result_type,
            report_type, notebook_line, language):
        detection_limit = notebook_line.detection_limit
        literal_result = notebook_line.literal_result
        result_modifier = notebook_line.result_modifier

        if report_section in ('amb', 'sq'):
            res = ''
            if report_type == 'polisample' and result_modifier == 'nd':
                with Transaction().set_context(language=language):
                    res = gettext('lims.msg_detection_limit_2',
                        detection_limit=detection_limit)
        else:
            if (not detection_limit or detection_limit in ('0', '0.0') or
                    literal_result):
                res = '-'
            else:
                res = detection_limit
        return res

    @classmethod
    def get_reference(cls, range_type, notebook_line, language,
            report_section):
        pool = Pool()
        Range = pool.get('lims.range')

        with Transaction().set_context(language=language):
            ranges = Range.search([
                ('range_type', '=', range_type.id),
                ('analysis', '=', notebook_line.analysis.id),
                ('product_type', '=', notebook_line.product_type.id),
                ('matrix', '=', notebook_line.matrix.id),
                ])
        if not ranges:
            return ''

        range_ = ranges[0]

        if range_.reference:
            return range_.reference
        elif report_section == 'mi':
            return ''

        res = ''
        if range_.min:
            with Transaction().set_context(language=language):
                resf = float(range_.min)
                resd = abs(resf) - abs(int(resf))
                if resd > 0:
                    res1 = str(round(range_.min, 2))
                else:
                    res1 = str(int(range_.min))
                res = gettext('lims.msg_caa_min', min=res1)

        if range_.max:
            if res:
                res += ' - '
            with Transaction().set_context(language=language):
                resf = float(range_.max)
                resd = abs(resf) - abs(int(resf))
                if resd > 0:
                    res1 = str(round(range_.max, 2))
                else:
                    res1 = str(int(range_.max))

                res += gettext('lims.msg_caa_max', max=res1)
        return res

    @classmethod
    def get_value(cls, obj, path):
        if not obj or not path:
            return ''

        path = path.split('.')
        value = obj
        try:
            while path:
                field = path.pop(0)
                value = getattr(value, field, None)
                if isinstance(value, dict):
                    dict_key = path.pop(0)
                    if dict_key not in value:
                        return ''
                    value = value[dict_key]
        except AttributeError:
            value = None
        return value or ''

    @classmethod
    def get_grouped_lines(cls, sample, grouped_by=None):
        if not sample:
            return []
        if not grouped_by:
            grouped_by = 'none'
        try:
            return getattr(cls,
                '_get_lines_grouped_by_%s' % grouped_by)(sample)
        except AttributeError:
            return []

    @classmethod
    def _get_lines_grouped_by_none(cls, sample):
        res = sample.notebook_lines
        return res

    @classmethod
    def _get_lines_grouped_by_origin(cls, sample):
        all_lines = {}
        for nl in sample.notebook_lines:
            key = nl.notebook_line.analysis_origin
            if key not in all_lines:
                all_lines[key] = {
                    'name': key,
                    'lines': [],
                    }
            all_lines[key]['lines'].append(nl)
        return all_lines.values()


class ResultReportTranscription(ResultReport):
    'Transcription Results Report'
    __name__ = 'lims.result_report.transcription'

    @classmethod
    def execute(cls, ids, data):
        ResultsDetail = Pool().get('lims.results_report.version.detail')
        if len(ids) > 1:
            raise UserError(gettext('lims.msg_multiple_reports'))

        results_report = ResultsDetail(ids[0])
        if results_report.state == 'annulled':
            raise UserError(gettext('lims.msg_annulled_report'))

        if data is None:
            data = {}
        current_data = data.copy()
        current_data['alt_lang'] = None
        result_orig = super(ResultReport, cls).execute(ids, current_data)
        current_data['alt_lang'] = 'en'
        result_eng = super(ResultReport, cls).execute(ids, current_data)

        save = False
        if results_report.english_report:
            if results_report.report_cache_odt_eng:
                result = (results_report.report_format_odt_eng,
                    results_report.report_cache_odt_eng) + result_eng[2:]
            else:
                result = result_eng
                if ('english_report' in current_data and
                        current_data['english_report']):
                    results_report.report_format_odt_eng, \
                        results_report.report_cache_odt_eng = result_eng[:2]
                    save = True
        else:
            if results_report.report_cache_odt:
                result = (results_report.report_format_odt,
                    results_report.report_cache_odt) + result_orig[2:]
            else:
                result = result_orig
                if ('english_report' in current_data and
                        not current_data['english_report']):
                    results_report.report_format_odt, \
                        results_report.report_cache_odt = result_orig[:2]
                    save = True
        if save:
            results_report.save()

        return result


class PrintGlobalResultReport(Wizard):
    'Print Global Results Report'
    __name__ = 'lims.print_global_result_report'

    start = StateTransition()
    print_ = StateReport('lims.global_result_report')

    @classmethod
    def check_access(cls):
        pass

    def transition_start(self):
        pool = Pool()
        ResultsReport = pool.get('lims.results_report')

        for active_id in Transaction().context['active_ids']:
            results_report = ResultsReport(active_id)
            details = results_report.details_cached(
                results_report.english_report)
            if not details:
                raise UserError(gettext('lims.msg_empty_report'))

            if results_report.english_report:
                cache = self._get_global_report(details, True)
                if not cache:
                    raise UserError(gettext('lims.msg_empty_report'))
                results_report.report_cache_eng = cache
                results_report.report_format_eng = 'pdf'
            else:
                cache = self._get_global_report(details, False)
                if not cache:
                    raise UserError(gettext('lims.msg_empty_report'))
                results_report.report_cache = cache
                results_report.report_format = 'pdf'
            results_report.save()
        return 'print_'

    def _get_global_report(self, details, english_report=False):
        all_cache = []
        if english_report:
            for detail in details:
                if detail.report_cache_eng:
                    all_cache.append(detail.report_cache_eng)
        else:
            for detail in details:
                if detail.report_cache:
                    all_cache.append(detail.report_cache)
        if not all_cache:
            return False

        merger = PdfFileMerger(strict=False)
        for cache in all_cache:
            filedata = BytesIO(cache)
            merger.append(filedata)
        output = BytesIO()
        merger.write(output)
        return bytearray(output.getvalue())

    def do_print_(self, action):
        data = {}
        data['id'] = Transaction().context['active_ids'].pop()
        data['ids'] = [data['id']]
        return action, data

    def transition_print_(self):
        if Transaction().context['active_ids']:
            return 'print_'
        return 'end'


class GlobalResultReport(Report):
    'Global Results Report'
    __name__ = 'lims.global_result_report'

    @classmethod
    def execute(cls, ids, data):
        ResultsReport = Pool().get('lims.results_report')

        result = super().execute(ids, data)

        results_report = ResultsReport(ids[0])
        if results_report.english_report:
            if results_report.report_cache_eng:
                result = (results_report.report_format_eng,
                    results_report.report_cache_eng) + result[2:]
        else:
            if results_report.report_cache:
                result = (results_report.report_format,
                    results_report.report_cache) + result[2:]

        report_name = '%s %s' % (result[3], results_report.number)
        result = result[:3] + (report_name,)

        return result
