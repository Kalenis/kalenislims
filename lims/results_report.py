# -*- coding: utf-8 -*-
# This file is part of lims module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from io import BytesIO
from datetime import datetime
from PyPDF2 import PdfFileMerger
from sql import Literal, Null

from trytond.model import (Workflow, ModelView, ModelSQL, Unique, fields,
    sequence_ordered)
from trytond.wizard import Wizard, StateTransition, StateView, StateAction, \
    StateReport, Button
from trytond.pool import Pool
from trytond.pyson import PYSONEncoder, Eval, Bool, Not, Or
from trytond.transaction import Transaction
from trytond.report import Report
from trytond.rpc import RPC
from trytond.exceptions import UserError
from trytond.i18n import gettext
from trytond import backend
from .configuration import get_print_date
from .notebook import NotebookLineRepeatAnalysis


class ResultsReport(ModelSQL, ModelView):
    'Results Report'
    __name__ = 'lims.results_report'
    _rec_name = 'number'

    number = fields.Char('Number', select=True, readonly=True)
    versions = fields.One2Many('lims.results_report.version',
        'results_report', 'Laboratories', readonly=True)
    party = fields.Many2One('party.party', 'Party', required=True,
        readonly=True)
    invoice_party = fields.Function(fields.Many2One('party.party',
        'Invoice party'), 'get_entry_field',
        searcher='search_entry_field')
    entry = fields.Many2One('lims.entry', 'Entry', select=True, readonly=True)
    notebook = fields.Many2One('lims.notebook', 'Laboratory notebook')
    report_grouper = fields.Integer('Report Grouper')
    generation_type = fields.Char('Generation type')
    cie_fraction_type = fields.Boolean('QA', readonly=True)
    report_language = fields.Many2One('ir.lang', 'Language', required=True,
        domain=[('translatable', '=', True)])
    single_sending_report = fields.Function(fields.Boolean(
        'Single sending per Sample'), 'get_entry_field',
        searcher='search_entry_field')
    single_sending_report_ready = fields.Function(fields.Boolean(
        'Single sending per Sample Ready'),
        'get_single_sending_report_ready')
    entry_single_sending_report = fields.Function(fields.Boolean(
        'Single sending per Entry'), 'get_entry_field',
        searcher='search_entry_field')
    entry_single_sending_report_ready = fields.Function(fields.Boolean(
        'Single sending per Entry Ready'),
        'get_entry_single_sending_report_ready')
    ready_to_send = fields.Function(fields.Boolean(
        'Ready to Send'), 'get_ready_to_send',
        searcher='search_ready_to_send')
    create_date2 = fields.Function(fields.DateTime('Create Date'),
       'get_create_date2', searcher='search_create_date2')
    write_date2 = fields.DateTime('Write Date', readonly=True)
    attachments = fields.One2Many('ir.attachment', 'resource', 'Attachments')
    samples_list = fields.Function(fields.Char('Samples'),
        'get_samples_list', searcher='search_samples_list')
    report_cache = fields.Binary('Report cache', readonly=True,
        file_id='report_cache_id', store_prefix='results_report')
    report_cache_id = fields.Char('Report cache id', readonly=True)
    report_format = fields.Char('Report format', readonly=True)

    @classmethod
    def __register__(cls, module_name):
        cursor = Transaction().connection.cursor()

        table_h = cls.__table_handler__(module_name)
        notebook_exist = table_h.column_exist('notebook')
        entry_exist = table_h.column_exist('entry')
        english_report_exist = table_h.column_exist('english_report')

        super().__register__(module_name)

        if notebook_exist and not entry_exist:
            cursor.execute('UPDATE "lims_results_report" r '
                'SET entry = s.entry '
                'FROM "lims_sample" s '
                'INNER JOIN "lims_fraction" f ON s.id = f.sample '
                'INNER JOIN "lims_notebook" n ON f.id = n.fraction '
                'WHERE r.notebook = n.id')

        if english_report_exist:
            cls._migrate_english_report()
            table_h.drop_column('english_report')
            table_h.drop_column('report_cache_eng')
            table_h.drop_column('report_cache_eng_id')
            table_h.drop_column('report_format_eng')

    @classmethod
    def _migrate_english_report(cls):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Configuration = pool.get('lims.configuration')
        Lang = pool.get('ir.lang')

        report_table = cls.__table__()
        configuration_table = Configuration.__table__()
        lang_table = Lang.__table__()

        cursor.execute(*configuration_table.select(
            configuration_table.results_report_language,
            where=Literal(True)))
        default_language = cursor.fetchone()
        if default_language:
            cursor.execute(*report_table.update(
                [report_table.report_language], [default_language[0]],
                where=(report_table.english_report == Literal(False))))

        cursor.execute(*lang_table.select(
            lang_table.id,
            where=lang_table.code == Literal('en')))
        english_language = cursor.fetchone()
        if english_language:
            cursor.execute(*report_table.update(
                [report_table.report_language], [english_language[0]],
                where=(report_table.english_report == Literal(True))))

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

        workyear_id = LabWorkYear.find()
        workyear = LabWorkYear(workyear_id)
        sequence = workyear.get_sequence('results_report')
        if not sequence:
            raise UserError(gettext('lims.msg_no_sequence',
                work_year=workyear.rec_name))

        vlist = [x.copy() for x in vlist]
        for values in vlist:
            values['number'] = sequence.get()
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
            'report_language',
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
        nested = clause[0].lstrip(name)
        return [('entry.' + name + nested,) + tuple(clause[1:])]

    def _order_entry_field(name):
        def order_field(tables):
            Entry = Pool().get('lims.entry')
            field = Entry._fields[name]
            table, _ = tables[None]
            entry_tables = tables.get('entry')
            if entry_tables is None:
                entry = Entry.__table__()
                entry_tables = {
                    None: (entry, entry.id == table.entry),
                    }
                tables['entry'] = entry_tables
            return field.convert_order(name, entry_tables, Entry)
        return staticmethod(order_field)
    order_invoice_party = _order_entry_field('invoice_party')

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
    def get_entry_single_sending_report_ready(cls, reports, name):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        NotebookLine = pool.get('lims.notebook.line')
        Service = pool.get('lims.service')
        Fraction = pool.get('lims.fraction')
        Sample = pool.get('lims.sample')

        result = {}
        for r in reports:
            result[r.id] = False
            if not r.entry_single_sending_report:
                continue
            cursor.execute('SELECT COUNT(*) '
                'FROM "' + EntryDetailAnalysis._table + '" ad '
                    'INNER JOIN "' + NotebookLine._table + '" nl '
                    'ON ad.id = nl.analysis_detail '
                    'INNER JOIN "' + Service._table + '" srv '
                    'ON srv.id = nl.service '
                    'INNER JOIN "' + Fraction._table + '" f '
                    'ON f.id = srv.fraction '
                    'INNER JOIN "' + Sample._table + '" s '
                    'ON s.id = f.sample '
                'WHERE s.entry = %s '
                    'AND ad.report_grouper = %s '
                    'AND nl.report = TRUE '
                    'AND nl.annulled = FALSE '
                    'AND nl.results_report IS NULL',
                (r.entry.id, r.report_grouper,))
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
            if (r.entry_single_sending_report and
                    not r.entry_single_sending_report_ready):
                continue
            if not r.has_report_cached(r.report_language):
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
        CachedReport = pool.get('lims.results_report.cached_report')

        excluded_ids = []
        cursor.execute('SELECT r.id '
            'FROM "' + ResultsReport._table + '" r '
                'INNER JOIN "' + Entry._table + '" e '
                'ON r.entry = e.id '
            'WHERE e.single_sending_report = TRUE '
                'OR e.entry_single_sending_report = TRUE')
        single_sending_ids = [x[0] for x in cursor.fetchall()]
        with Transaction().set_user(0):
            for r in ResultsReport.browse(single_sending_ids):
                if (r.single_sending_report and
                        not r.single_sending_report_ready):
                    excluded_ids.append(r.id)
                if (r.entry_single_sending_report and
                        not r.entry_single_sending_report_ready):
                    excluded_ids.append(r.id)
        excluded_ids = ', '.join(str(r) for r in [0] + excluded_ids)

        cursor.execute('SELECT rr.id '
            'FROM "' + CachedReport._table + '" cr '
                'INNER JOIN "' + ResultsDetail._table + '" rd '
                'ON cr.version_detail = rd.id '
                'INNER JOIN "' + ResultsVersion._table + '" rv '
                'ON rd.report_version = rv.id '
                'INNER JOIN "' + ResultsReport._table + '" rr '
                'ON rv.results_report = rr.id '
            'WHERE rv.results_report NOT IN (' + excluded_ids + ') '
                'AND rd.valid = TRUE '
                'AND cr.report_language = rr.report_language '
                'AND cr.report_format = \'pdf\'')
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

    def _get_details_cached(self, language):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        CachedReport = pool.get('lims.results_report.cached_report')
        ResultsDetail = pool.get('lims.results_report.version.detail')
        ResultsVersion = pool.get('lims.results_report.version')

        cursor.execute('SELECT rd.id '
            'FROM "' + CachedReport._table + '" cr '
                'INNER JOIN "' + ResultsDetail._table + '" rd '
                'ON cr.version_detail = rd.id '
                'INNER JOIN "' + ResultsVersion._table + '" rv '
                'ON rd.report_version = rv.id '
            'WHERE rv.results_report = %s '
                'AND rd.valid = TRUE '
                'AND cr.report_language = %s '
                'AND cr.report_format = \'pdf\'',
            (self.id, language.id))
        return [x[0] for x in cursor.fetchall()]

    def has_report_cached(self, language):
        return bool(self._get_details_cached(language))

    def details_cached(self, language):
        pool = Pool()
        ResultsDetail = pool.get('lims.results_report.version.detail')
        with Transaction().set_user(0):
            return ResultsDetail.browse(self._get_details_cached(language))

    def build_report(self, language):
        details = self.details_cached(language)
        if not details:
            raise UserError(gettext('lims.msg_global_report_cache',
                    language=language.name))

        cache = self._get_global_report(details, language)
        if not cache:
            raise UserError(gettext('lims.msg_global_report_build'))

        #self.report_cache = cache
        #self.report_format = 'pdf'
        #self.save()
        return cache

    def _get_global_report(self, details, language):
        pool = Pool()
        CachedReport = pool.get('lims.results_report.cached_report')

        all_cache = []
        for detail in details:
            cached_reports = CachedReport.search([
                ('version_detail', '=', detail.id),
                ('report_language', '=', language.id),
                ('report_format', '=', 'pdf'),
                ])
            if cached_reports:
                all_cache.append(cached_reports[0].report_cache)
        if not all_cache:
            return False

        merger = PdfFileMerger(strict=False)
        for cache in all_cache:
            filedata = BytesIO(cache)
            merger.append(filedata)
        output = BytesIO()
        merger.write(output)
        return bytearray(output.getvalue())

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
    party = fields.Function(fields.Many2One('party.party', 'Party'),
       'get_report_field', searcher='search_report_field')

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

    @classmethod
    def get_report_field(cls, versions, names):
        result = {}
        for name in names:
            result[name] = {}
            if cls._fields[name]._type == 'many2one':
                for v in versions:
                    field = getattr(v.results_report, name, None)
                    result[name][v.id] = field.id if field else None
            elif cls._fields[name]._type == 'boolean':
                for v in versions:
                    field = getattr(v.results_report, name, False)
                    result[name][v.id] = field
            else:
                for v in versions:
                    field = getattr(v.results_report, name, None)
                    result[name][v.id] = field
        return result

    @classmethod
    def search_report_field(cls, name, clause):
        return [('results_report.' + name,) + tuple(clause[1:])]

    def _order_report_field(name):
        def order_field(tables):
            ResultsReport = Pool().get('lims.results_report')
            field = ResultsReport._fields[name]
            table, _ = tables[None]
            report_tables = tables.get('results_report')
            if report_tables is None:
                results_report = ResultsReport.__table__()
                report_tables = {
                    None: (results_report,
                        results_report.id == table.results_report),
                    }
                tables['results_report'] = report_tables
            return field.convert_order(name, report_tables, ResultsReport)
        return staticmethod(order_field)
    order_party = _order_report_field('party')


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
        ('waiting', 'Waiting'),
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
    signatories = fields.One2Many('lims.results_report.version.detail.signer',
        'version_detail', 'Signatories', states=_states, depends=_depends)
    resultrange_origin = fields.Many2One('lims.range.type', 'Origin',
        domain=['OR', ('id', '=', Eval('resultrange_origin')),
            ('id', 'in', Eval('resultrange_origin_domain'))],
        depends=['resultrange_origin_domain', 'report_result_type', 'state'],
        states={
            'invisible': Not(Eval('report_result_type').in_([
                'result_range', 'both_range'])),
            'required': Eval('report_result_type').in_([
                'result_range', 'both_range']),
            'readonly': Eval('state') != 'draft',
            })
    resultrange_origin_domain = fields.Function(fields.Many2Many(
        'lims.range.type', None, None, 'Origin domain'),
        'on_change_with_resultrange_origin_domain')
    comments = fields.Function(fields.Text('Comments',
        states={'readonly': Bool(Eval('comments_readonly'))},
        depends=['comments_readonly']), 'get_comments', setter='set_comments')
    comments_readonly = fields.Function(fields.Boolean(
        'Comments readonly'), 'get_comments_readonly')
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
    trace_report = fields.Boolean('Trace report')

    # State changes
    revision_uid = fields.Many2One('res.user', 'Revision user', readonly=True)
    revision_date = fields.DateTime('Revision date', readonly=True)
    release_uid = fields.Many2One('res.user', 'Release user', readonly=True)
    release_date = fields.DateTime('Release date', readonly=True)
    review_reason = fields.Text('Review reason', translate=True,
        states={
            'readonly': Or(Bool(Eval('valid')), Eval('state') != 'released'),
            },
        depends=['state', 'valid'])
    review_reason_print = fields.Boolean(
        'Print review reason in next version',
        states={
            'readonly': Or(Bool(Eval('valid')), Eval('state') != 'released'),
            },
        depends=['state', 'valid'])
    annulment_uid = fields.Many2One('res.user', 'Annulment user',
        readonly=True)
    annulment_date = fields.DateTime('Annulment date', readonly=True)
    annulment_reason = fields.Text('Annulment reason', translate=True,
        states={'readonly': Eval('state') != 'annulled'}, depends=_depends)
    annulment_reason_print = fields.Boolean('Print annulment reason',
        states={'readonly': Eval('state') != 'annulled'}, depends=_depends)
    waiting_reason = fields.Text('Waiting reason', readonly=True)

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
    report_language = fields.Function(fields.Many2One('ir.lang', 'Language'),
        'get_report_field', searcher='search_report_field')
    cached_reports = fields.One2Many('lims.results_report.cached_report',
        'version_detail', 'Cached Reports', readonly=True)
    report_language_cached = fields.Function(fields.Boolean(
        'Report cached'), 'get_report_language_cached')

    del _states, _depends

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order.insert(0, ('report_version', 'DESC'))
        cls._order.insert(1, ('number', 'DESC'))
        cls._transitions = set((
            ('draft', 'waiting'),
            ('waiting', 'draft'),
            ('draft', 'revised'),
            ('revised', 'draft'),
            ('revised', 'released'),
            ('released', 'annulled'),
            ))
        cls._buttons.update({
            'draft': {
                'invisible': ~Eval('state').in_(['waiting', 'revised']),
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
                'invisible': Or(
                    Eval('state') != 'released',
                    Bool(Eval('report_language_cached')),
                    ),
                'depends': ['state', 'report_language_cached'],
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
        TableHandler = backend.TableHandler

        table_h = cls.__table_handler__(module_name)
        report_cache_exist = table_h.column_exist('report_cache_id')
        cached_report_table_exist = TableHandler.table_exist(
            'lims_results_report_cached_report')

        super().__register__(module_name)

        if report_cache_exist:
            cursor.execute('UPDATE "' + cls._table + '" '
                'SET state = \'released\' '
                'WHERE state = \'revised\' '
                    'AND (report_cache_id IS NOT NULL OR '
                    'report_cache_eng_id IS NOT NULL)')

        if report_cache_exist and cached_report_table_exist:
            cls._migrate_report_cache()
            table_h.drop_column('report_cache')
            table_h.drop_column('report_cache_id')
            table_h.drop_column('report_format')
            table_h.drop_column('report_cache_eng')
            table_h.drop_column('report_cache_eng_id')
            table_h.drop_column('report_format_eng')
            table_h.drop_column('report_cache_odt')
            table_h.drop_column('report_cache_odt_id')
            table_h.drop_column('report_format_odt')
            table_h.drop_column('report_cache_odt_eng')
            table_h.drop_column('report_cache_odt_eng_id')
            table_h.drop_column('report_format_odt_eng')

    @classmethod
    def _migrate_report_cache(cls):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Configuration = pool.get('lims.configuration')
        Lang = pool.get('ir.lang')
        CachedReport = pool.get('lims.results_report.cached_report')

        report_table = cls.__table__()
        configuration_table = Configuration.__table__()
        lang_table = Lang.__table__()
        cached_report_table = CachedReport.__table__()

        cursor.execute(*configuration_table.select(
            configuration_table.results_report_language,
            where=Literal(True)))
        default_language = cursor.fetchone()

        cursor.execute(*lang_table.select(
            lang_table.id,
            where=lang_table.code == Literal('en')))
        english_language = cursor.fetchone()

        cursor.execute(*report_table.select(
            report_table.id,
            report_table.report_cache,
            report_table.report_cache_id,
            report_table.report_format,
            report_table.report_cache_eng,
            report_table.report_cache_eng_id,
            report_table.report_format_eng,
            report_table.report_cache_odt,
            report_table.report_cache_odt_id,
            report_table.report_format_odt,
            report_table.report_cache_odt_eng,
            report_table.report_cache_odt_eng_id,
            report_table.report_format_odt_eng,
            where=Literal(True)))
        for x in cursor.fetchall():
            vals = []
            if x[1] or x[2] or x[7] or x[8]:
                vals.append([x[0], default_language[0],
                    x[1], x[2], x[3], x[7], x[8], x[9]])
            if x[4] or x[5] or x[10] or x[11]:
                vals.append([x[0], english_language[0],
                    x[4], x[5], x[6], x[10], x[11], x[12]])
            if not vals:
                continue
            cursor.execute(*cached_report_table.insert([
                    cached_report_table.version_detail,
                    cached_report_table.report_language,
                    cached_report_table.report_cache,
                    cached_report_table.report_cache_id,
                    cached_report_table.report_format,
                    cached_report_table.transcription_report_cache,
                    cached_report_table.transcription_report_cache_id,
                    cached_report_table.transcription_report_format,
                    ], vals))

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
    def view_attributes(cls):
        return super().view_attributes() + [
            ('//page[@id="waiting"]', 'states', {
                    'invisible': Eval('state') != 'waiting',
                    }),
            ('//page[@id="annulation"]', 'states', {
                    'invisible': Eval('state') != 'annulled',
                    }),
            ]

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

    @fields.depends('samples')
    def on_change_with_resultrange_origin_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Range = pool.get('lims.range')
        RangeType = pool.get('lims.range.type')

        if not self.samples:
            return []

        product_type_id = self.samples[0].product_type.id
        matrix_id = self.samples[0].matrix.id
        cursor.execute('SELECT DISTINCT(rt.id) '
            'FROM "' + RangeType._table + '" rt '
                'INNER JOIN "' + Range._table + '" r '
                'ON rt.id = r.range_type '
            'WHERE rt.use = \'result_range\' '
                'AND r.product_type = %s '
                'AND r.matrix = %s',
            (product_type_id, matrix_id))
        return [x[0] for x in cursor.fetchall()]

    def get_report_language_cached(self, name=None):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        CachedReport = pool.get('lims.results_report.cached_report')
        cursor.execute('SELECT cr.id '
            'FROM "' + CachedReport._table + '" cr '
            'WHERE cr.version_detail = %s '
                'AND cr.report_language = %s',
            (self.id, self.report_language.id))
        return bool(cursor.fetchone())

    def get_comments(self, name):
        pool = Pool()
        ReportComment = pool.get('lims.results_report.comment')

        comments = ReportComment.search([
            ('version_detail', '=', self.id),
            ('report_language', '=', self.report_language.id),
            ])
        if comments:
            return comments[0].comments
        return None

    @classmethod
    def set_comments(cls, details, name, value):
        pool = Pool()
        ReportComment = pool.get('lims.results_report.comment')

        detail_id = details[0].id
        report_language_id = details[0].report_language.id

        comments = ReportComment.search([
            ('version_detail', '=', detail_id),
            ('report_language', '=', report_language_id),
            ])
        ReportComment.delete(comments)
        if not value:
            return
        ReportComment.create([{
            'version_detail': detail_id,
            'report_language': report_language_id,
            'comments': value,
            }])

    def get_comments_readonly(self, name):
        return self.get_report_language_cached()

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
                #('type', '!=', 'preliminary'),
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
        if detail.signatories:
            detail_default['signatories'] = [('create', [{
                'sequence': c.sequence,
                'type': c.type,
                'professional': c.professional.id,
                } for c in detail.signatories])]
        if detail.resultrange_origin:
            detail_default['resultrange_origin'] = detail.resultrange_origin.id
        detail_default['comments'] = str(detail.comments or '')
        return detail_default

    @classmethod
    def update_review_reason(cls, detail, review_reason,
            review_reason_print):
        valid_detail = cls.search([
            ('report_version', '=', detail.report_version.id),
            ('valid', '=', True),
            ('type', '!=', 'preliminary'),
            ], limit=1)
        if valid_detail:
            cls.write(valid_detail, {
                'review_reason': review_reason,
                'review_reason_print': review_reason_print,
                })

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

        ResultReport.execute([self.id], {'save_cache': True})
        ResultReportTranscription.execute([self.id], {'save_cache': True})

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
            if cls._fields[name]._type == 'many2one':
                for d in details:
                    field = getattr(d.report_version, name, None)
                    result[name][d.id] = field.id if field else None
            elif cls._fields[name]._type == 'boolean':
                for d in details:
                    field = getattr(d.report_version, name, False)
                    result[name][d.id] = field
            else:
                for d in details:
                    field = getattr(d.report_version, name, None)
                    result[name][d.id] = field
        return result

    @classmethod
    def search_version_field(cls, name, clause):
        return [('report_version.' + name,) + tuple(clause[1:])]

    def _order_version_field(name):
        def order_field(tables):
            ResultsVersion = Pool().get('lims.results_report.version')
            field = ResultsVersion._fields[name]
            table, _ = tables[None]
            version_tables = tables.get('report_version')
            if version_tables is None:
                report_version = ResultsVersion.__table__()
                version_tables = {
                    None: (report_version,
                        report_version.id == table.report_version),
                    }
                tables['report_version'] = version_tables
            return field.convert_order(name, version_tables, ResultsVersion)
        return staticmethod(order_field)
    order_laboratory = _order_version_field('laboratory')

    @classmethod
    def get_report_field(cls, details, names):
        result = {}
        for name in names:
            result[name] = {}
            if cls._fields[name]._type == 'many2one':
                for d in details:
                    field = getattr(d.report_version.results_report, name,
                        None)
                    result[name][d.id] = field.id if field else None
            elif cls._fields[name]._type == 'boolean':
                for d in details:
                    field = getattr(d.report_version.results_report, name,
                        False)
                    result[name][d.id] = field
            else:
                for d in details:
                    field = getattr(d.report_version.results_report, name,
                        None)
                    result[name][d.id] = field
        return result

    @classmethod
    def search_report_field(cls, name, clause):
        return [('report_version.results_report.' + name,) + tuple(clause[1:])]

    def _order_report_field(name):
        def order_field(tables):
            pool = Pool()
            ResultsReport = pool.get('lims.results_report')
            ResultsVersion = pool.get('lims.results_report.version')
            field = ResultsReport._fields[name]
            table, _ = tables[None]
            version_tables = tables.get('report_version')
            if version_tables is None:
                report_version = ResultsVersion.__table__()
                version_tables = {
                    None: (report_version,
                        report_version.id == table.report_version),
                    }
                tables['report_version'] = version_tables
            return field.convert_order(name, version_tables, ResultsVersion)
        return staticmethod(order_field)
    order_party = _order_report_field('party')

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
                for d in details:
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
        with Transaction().set_context(check_signer=False):
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
    def _get_fields_from_samples(cls, samples, generate_report_form=None):
        pool = Pool()
        Notebook = pool.get('lims.notebook')

        detail_default = {}
        if len(samples) > 1:
            detail_default['report_type_forced'] = 'polisample'
        else:
            detail_default['report_type_forced'] = 'normal'

        detail_default['trace_report'] = False
        for sample in samples:
            nb = Notebook(sample['notebook'])
            if nb.fraction.sample.trace_report:
                detail_default['trace_report'] = True

        return detail_default

    @classmethod
    def _get_fields_not_overwrite(cls):
        fields = ['type', 'signatories', 'samples']
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


class ResultsReportCachedReport(ModelSQL):
    'Cached Results Report'
    __name__ = 'lims.results_report.cached_report'

    version_detail = fields.Many2One('lims.results_report.version.detail',
        'Report Detail', required=True, ondelete='CASCADE', select=True)
    report_language = fields.Many2One('ir.lang', 'Language', required=True)
    report_cache = fields.Binary('Report cache', readonly=True,
        file_id='report_cache_id', store_prefix='results_report')
    report_cache_id = fields.Char('Report cache id', readonly=True)
    report_format = fields.Char('Report format', readonly=True)
    transcription_report_cache = fields.Binary(
        'Transcription Report cache', readonly=True,
        file_id='transcription_report_cache_id',
        store_prefix='results_report')
    transcription_report_cache_id = fields.Char(
        'Transcription Report cache id', readonly=True)
    transcription_report_format = fields.Char(
        'Transcription Report format', readonly=True)

    @classmethod
    def __setup__(cls):
        super().__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('detail_language_report_uniq', Unique(t,
                t.version_detail, t.report_language, t.report_format),
                'lims.msg_detail_language_unique_id'),
            ]


class ResultsReportComment(ModelSQL):
    'Results Report Comment'
    __name__ = 'lims.results_report.comment'

    version_detail = fields.Many2One('lims.results_report.version.detail',
        'Report Detail', ondelete='CASCADE', select=True, required=True)
    report_language = fields.Many2One('ir.lang', 'Language', required=True)
    comments = fields.Text('Comments')

    @classmethod
    def __register__(cls, module_name):
        TableHandler = backend.TableHandler
        ResultsDetail = Pool().get('lims.results_report.version.detail')

        comments_table_exist = TableHandler.table_exist(cls._table)
        detail_table_h = ResultsDetail.__table_handler__(module_name)
        comments_exist = detail_table_h.column_exist('comments')

        super().__register__(module_name)
        if comments_exist and not comments_table_exist:
            cls._migrate_report_comment()

    @classmethod
    def _migrate_report_comment(cls):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        ResultsReport = pool.get('lims.results_report')
        ResultsVersion = pool.get('lims.results_report.version')
        ResultsDetail = pool.get('lims.results_report.version.detail')

        table = cls.__table__()

        cursor.execute('SELECT rd.id, rr.report_language, rd.comments '
            'FROM "' + ResultsDetail._table + '" rd '
                'INNER JOIN "' + ResultsVersion._table + '" rv '
                'ON rd.report_version = rv.id '
                'INNER JOIN "' + ResultsReport._table + '" rr '
                'ON rv.results_report = rr.id '
            'WHERE rd.comments IS NOT NULL')
        res = cursor.fetchall()
        if res:
            cursor.execute(*table.insert([
                    table.version_detail,
                    table.report_language,
                    table.comments,
                    ], res))


class ResultsReportVersionDetailSigner(sequence_ordered(),
        ModelSQL, ModelView):
    'Results Report Version Detail Signer'
    __name__ = 'lims.results_report.version.detail.signer'

    version_detail = fields.Many2One('lims.results_report.version.detail',
        'Report Detail', required=True, ondelete='CASCADE', select=True)
    type = fields.Selection([
        ('signer', 'Signer'),
        ('manager', 'Manager'),
        ('responsible', 'Responsible'),
        ], 'Type', sort=False, required=True)
    professional = fields.Many2One('lims.laboratory.professional',
        'Professional', required=True)
        #domain=[('id', 'in', Eval('professional_domain'))],
        #depends=['professional_domain'])
    professional_domain = fields.Function(fields.Many2Many(
        'lims.laboratory.professional', None, None, 'Professional domain'),
        'on_change_with_professional_domain')

    @classmethod
    def __register__(cls, module_name):
        TableHandler = backend.TableHandler
        ResultsDetail = Pool().get('lims.results_report.version.detail')

        signer_table_exist = TableHandler.table_exist(
            'lims_results_report_version_detail_signer')
        detail_table_h = ResultsDetail.__table_handler__(module_name)
        signer_exist = detail_table_h.column_exist('signer')

        super().__register__(module_name)

        if signer_exist and not signer_table_exist:
            cls._migrate_signer()

    @classmethod
    def _migrate_signer(cls):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        ResultsDetail = pool.get('lims.results_report.version.detail')

        report_table = ResultsDetail.__table__()
        signer_table = cls.__table__()

        cursor.execute(*report_table.select(
            report_table.id,
            Literal('signer').as_('type'),
            report_table.signer,
            where=report_table.signer != Null))
        res = cursor.fetchall()
        if res:
            cursor.execute(*signer_table.insert([
                    signer_table.version_detail,
                    signer_table.type,
                    signer_table.professional,
                    ], res))

    @staticmethod
    def default_type():
        return 'signer'

    @classmethod
    def create(cls, vlist):
        new_list = []
        counter = set()
        for x in vlist:
            key = (x['version_detail'], x['professional'])
            if key in counter:
                continue
            if cls.search_count([
                    ('version_detail', '=', key[0]),
                    ('professional', '=', key[1]),
                    ]) > 0:
                continue
            counter.add(key)
            new_list.append(x.copy())
        return super().create(new_list)

    @classmethod
    def delete(cls, signatories):
        if Transaction().context.get('check_signer', True):
            cls.check_delete(signatories)
        super().delete(signatories)

    @classmethod
    def check_delete(cls, signatories):
        to_check = {}
        for signer in signatories:
            key = signer.version_detail.id
            if key not in to_check:
                to_check[key] = []
            to_check[key].append(signer.id)
        for k, v in to_check.items():
            if cls.search_count([
                    ('version_detail', '=', k),
                    ('type', 'in', ['manager', 'responsible']),
                    ('id', 'not in', v),
                    ]) == 0:
                raise UserError(gettext('lims.msg_delete_signatories'))

    @fields.depends('_parent_version_detail.laboratory')
    def on_change_with_professional_domain(self, name=None):
        pool = Pool()
        UserLaboratory = pool.get('lims.user-laboratory')
        LaboratoryProfessional = pool.get('lims.laboratory.professional')

        laboratory = self.version_detail.laboratory
        res = [laboratory.default_signer.id]
        if laboratory.default_manager:
            res.append(laboratory.default_manager.id)
        users = UserLaboratory.search([
            ('laboratory', '=', laboratory.id),
            ])
        if not users:
            return res
        professionals = LaboratoryProfessional.search([
            ('party.lims_user', 'in', [u.user.id for u in users]),
            ('role', '!=', ''),
            ])
        if not professionals:
            return res
        return res + [p.id for p in professionals]


class ResultsReportVersionDetailSample(
        sequence_ordered(), ModelSQL, ModelView):
    'Results Report Version Detail Sample'
    __name__ = 'lims.results_report.version.detail.sample'

    version_detail = fields.Many2One('lims.results_report.version.detail',
        'Report Detail', required=True, ondelete='CASCADE', select=True)
    notebook = fields.Many2One('lims.notebook', 'Notebook', required=True,
        readonly=True, select=True)
    notebook_lines = fields.One2Many('lims.results_report.version.detail.line',
        'detail_sample', 'Analysis')
    party = fields.Function(fields.Many2One('party.party', 'Party'),
        'get_notebook_field')
    comments = fields.Text('Comments')
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
        cls._order.insert(1, ('notebook.fraction', 'ASC'))

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
        # avoid copying lines from preliminary reports
        if sample.version_detail.type == 'preliminary':
            return sample_default
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
        sample_default['comments'] = sample.comments
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
    uncertainty = fields.Function(fields.Char('Uncertainty'),
        'get_uncertainty')
    final_unit = fields.Function(fields.Many2One('product.uom',
        'Final unit'), 'get_nline_field')
    reference = fields.Function(fields.Char('Reference'), 'get_reference')
    comments = fields.Function(fields.Text('Entry comments'),
        'get_nline_field')
    trace_report = fields.Function(fields.Boolean('Trace report'),
        'get_nline_field')
    analysis_order = fields.Function(fields.Integer('Order'),
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

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order.insert(0, ('analysis_order', 'ASC'))

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
            elif cls._fields[name]._type == 'boolean':
                for d in details:
                    result[name][d.id] = (d.notebook_line and
                        getattr(d.notebook_line, name, False) or False)
            else:
                for d in details:
                    result[name][d.id] = (d.notebook_line and
                        getattr(d.notebook_line, name, None) or None)
        return result

    def _order_nline_field(name):
        def order_field(tables):
            NotebookLine = Pool().get('lims.notebook.line')
            field = NotebookLine._fields[name]
            table, _ = tables[None]
            nline_tables = tables.get('notebook_line')
            if nline_tables is None:
                notebook_line = NotebookLine.__table__()
                nline_tables = {
                    None: (notebook_line,
                        notebook_line.id == table.notebook_line),
                    }
                tables['notebook_line'] = nline_tables
            return field.convert_order(name, nline_tables, NotebookLine)
        return staticmethod(order_field)
    order_trace_report = _order_nline_field('trace_report')

    @staticmethod
    def order_analysis_order(tables):
        pool = Pool()
        Analysis = pool.get('lims.analysis')
        NotebookLine = pool.get('lims.notebook.line')

        field = Analysis._fields['order']
        table, _ = tables[None]
        nline_tables = tables.get('notebook_line')
        if nline_tables is None:
            notebook_line = NotebookLine.__table__()
            analysis = Analysis.__table__()
            nline_tables = {
                None: (notebook_line,
                    notebook_line.id == table.notebook_line),
                'analysis': {
                    None: (analysis,
                        analysis.id == notebook_line.analysis),
                    },
                }
            tables['notebook_line'] = nline_tables
        return field.convert_order('order',
            nline_tables['analysis'], Analysis)

    @classmethod
    def get_result(cls, details, name):
        result = {}
        for d in details:
            result[d.id] = (d.notebook_line and
                d.notebook_line.formated_result or None)
        return result

    @classmethod
    def get_converted_result(cls, details, name):
        result = {}
        for d in details:
            result[d.id] = (d.notebook_line and
                d.notebook_line.formated_converted_result or None)
        return result

    @classmethod
    def get_uncertainty(cls, details, name):
        result = {}
        for d in details:
            result[d.id] = (d.notebook_line and d.notebook_line._format_result(
                d.notebook_line.uncertainty, d.notebook_line.decimals,
                d.notebook_line.significant_digits) or None)
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


class DivideReportsStart(ModelView):
    'Divide Reports'
    __name__ = 'lims.divide_reports.start'

    report_grouper = fields.Integer('Report Grouper')
    analysis_detail = fields.Many2Many('lims.entry.detail.analysis',
        None, None, 'Analysis detail',
        domain=[('id', 'in', Eval('analysis_detail_domain'))],
        depends=['analysis_detail_domain'])
    analysis_detail_domain = fields.One2Many('lims.entry.detail.analysis',
        None, 'Analysis detail domain')


class DivideReports(Wizard):
    'Divide Reports'
    __name__ = 'lims.divide_reports'

    start = StateView('lims.divide_reports.start',
        'lims.lims_divide_reports_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Ok', 'ok', 'tryton-ok', default=True),
            Button('Ok and Continue', 'continue_', 'tryton-ok'),
            ])
    ok = StateTransition()
    continue_ = StateTransition()

    def default_start(self, fields):
        EntryDetailAnalysis = Pool().get('lims.entry.detail.analysis')

        default = {
            'report_grouper': 0,
            'analysis_detail': [],
            'analysis_detail_domain': [],
            }

        context = Transaction().context
        model = context.get('active_model', None)

        if model == 'lims.entry':
            analysis_detail = EntryDetailAnalysis.search([
                ('entry', '=', context['active_id']),
                ('service.divide', '=', True),
                ('service.annulled', '=', False),
                ('report_grouper', '=', 0),
                ])
            default['analysis_detail_domain'] = [e.id for e in analysis_detail
                if not e.report_grouper_readonly]

        elif model == 'lims.entry.detail.analysis':
            analysis_detail = EntryDetailAnalysis.search([
                ('id', 'in', context['active_ids']),
                ])
            default['analysis_detail_domain'] = [e.id for e in analysis_detail
                if not e.report_grouper_readonly]
            default['analysis_detail'] = default['analysis_detail_domain']

        return default

    def transition_ok(self):
        EntryDetailAnalysis = Pool().get('lims.entry.detail.analysis')
        EntryDetailAnalysis.write(list(self.start.analysis_detail),
            {'report_grouper': self.start.report_grouper})
        return 'end'

    def transition_continue_(self):
        self.transition_ok()
        return 'start'


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
    review_reason = fields.Text('Review reason',
        states={'invisible': ~Eval('type').in_([
            'complementary', 'corrective'])},
        depends=['type'])
    review_reason_print = fields.Boolean(
        'Print review reason in next version',
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

        party_key = None
        entry = None
        report_grouper = None
        cie_fraction_type = None
        current_reports = []
        default_report_only_current = True

        for notebook in Notebook.browse(Transaction().context['active_ids']):
            res['notebooks'].append(notebook.id)
            if not res['report_readonly']:
                if not entry:
                    entry = notebook.fraction.sample.entry.id
                elif entry != notebook.fraction.sample.entry.id:
                    entry = -1
                # same party and invoice party
                if not party_key:
                    party_key = (notebook.party.id, notebook.invoice_party.id)
                elif (party_key !=
                        (notebook.party.id, notebook.invoice_party.id)):
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
                    ('party', '=', party_key[0]),
                    ('invoice_party', '=', party_key[1]),
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
                        ('party', '=', party_key[0]),
                        ('invoice_party', '=', party_key[1]),
                        ('report_grouper', '=', report_grouper),
                        ('cie_fraction_type', '=', cie_fraction_type),
                        ]
                reports = ResultsReport.search(clause)
                if reports:
                    res['report_domain'] = [r.id for r in reports]

        if res['report_domain'] and entry != -1:
            if current_reports:
                clause = [
                    ('report_version.results_report.id', 'in',
                        res['report_domain']),
                    ('state', '=', 'draft'),
                    ]
            elif not default_report_only_current:
                clause = [
                    ('report_version.results_report.id', 'in',
                        res['report_domain']),
                    ('state', '=', 'draft'),
                    ('laboratory', '=', laboratory_id),
                    ]
            else:
                clause = [('id', '=', -1)]
            draft_detail = ResultsDetail.search(clause)
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
        laboratory = Laboratory(laboratory_id)

        signatories = [{'type': 'signer',
            'professional': laboratory.default_signer.id}]
        if laboratory.default_manager:
            signatories.append({'type': 'manager',
                'professional': laboratory.default_manager.id})

        reports_created = []

        state = ('in_progress' if self.start.type == 'preliminary' else
            'complete')
        corrected = self.start.corrective

        if self.start.report:  # Result report selected
            samples = []
            extra_signers = set()
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
                extra_signers.update(self._get_lines_signer(
                    lines, signatories))
            extra_signatories = [{'type': 'responsible',
                'professional': signer_id,
                } for signer_id in extra_signers]
            details = {
                'type': self.start.type,
                'signatories': [('create',
                    signatories + extra_signatories)],
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
                    ResultsDetail.update_review_reason(detail,
                        self.start.review_reason,
                        self.start.review_reason_print)
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
                    key = (notebook.party.id, notebook.invoice_party.id,
                        notebook.fraction.cie_fraction_type)
                if key not in parties:
                    parties[key] = {
                        'party': notebook.party.id,
                        'entry': notebook.fraction.entry.id,
                        'comments': notebook.fraction.entry.report_comments,
                        'cie_fraction_type': (
                            notebook.fraction.cie_fraction_type),
                        'report_language': (
                            notebook.fraction.entry.report_language.id),
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
                    extra_signers = set()
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
                        extra_signers.update(self._get_lines_signer(
                            notebook['lines'], signatories))
                    extra_signatories = [{'type': 'responsible',
                        'professional': signer_id,
                        } for signer_id in extra_signers]
                    details = {
                        'type': self.start.type,
                        'signatories': [('create',
                            signatories + extra_signatories)],
                        'samples': [('create', samples)],
                        'comments': party['comments'],
                        }
                    details.update(ResultsDetail._get_fields_from_samples(
                        samples, self.start))
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
                        'report_language': party['report_language'],
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
            ResultsDetail.update_review_reason(detail,
                self.start.review_reason,
                self.start.review_reason_print)
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

    def _get_lines_signer(self, lines, excluded_signatories):
        pool = Pool()
        Department = pool.get('company.department')

        signers = set()

        departments = Department.search([
            ('id', 'in', list(set(l.department.id
                for l in lines if l.department))),
            ('responsible', '!=', None),
            ])
        for d in departments:
            signers.add(d.laboratory_professional.id)

        for s in excluded_signatories:
            if s['professional'] in signers:
                signers.remove(s['professional'])

        return signers

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
        for active_id in Transaction().context['active_ids']:
            detail = ResultsDetail(active_id)
            if detail.state in ['released', 'annulled']:
                continue
            self._process_transitions(detail)
        return 'end'

    def _process_transitions(self, detail):
        ResultsDetail = Pool().get('lims.results_report.version.detail')
        if detail.state == 'waiting':
            ResultsDetail.draft([detail])
        elif detail.state == 'draft':
            ResultsDetail.revise([detail])
        elif detail.state == 'revised':
            ResultsDetail.release([detail])
        # if not final state process again
        if detail.state != 'released':
            self._process_transitions(detail)

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
        pool = Pool()
        ResultsDetail = pool.get('lims.results_report.version.detail')
        CachedReport = pool.get('lims.results_report.cached_report')

        details = ResultsDetail.search([
            ('id', 'in', Transaction().context['active_ids']),
            ])
        if details:
            ResultsDetail.unlink_notebook_lines(details)
            ResultsDetail.write(details, {
                'state': 'annulled',
                'valid': False,
                'annulment_uid': int(Transaction().user),
                'annulment_date': datetime.now(),
                'annulment_reason': self.start.annulment_reason,
                'annulment_reason_print': self.start.annulment_reason_print,
                })
            cached_reports = CachedReport.search([
                ('version_detail', 'in', [d.id for d in details]),
                ])
            if cached_reports:
                CachedReport.delete(cached_reports)
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
    reports_created = fields.Many2Many('lims.results_report.version.detail',
        None, None, 'Reports created')

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

    start_state = 'check'
    check = StateTransition()
    start = StateView('lims.results_report.version.detail.new_version.start',
        'lims.results_report_version_detail_new_version_start_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Generate', 'generate', 'tryton-ok', default=True),
            ])
    generate = StateTransition()
    open_ = StateAction('lims.act_lims_results_report_version_detail')

    def transition_check(self):
        ResultsDetail = Pool().get('lims.results_report.version.detail')

        valid_details = ResultsDetail.search([
            ('id', 'in', Transaction().context['active_ids']),
            ('state', '=', 'released'),
            ('valid', '=', True),
            ])
        if valid_details:
            return 'start'
        return 'end'

    def default_start(self, fields):
        ResultsDetail = Pool().get('lims.results_report.version.detail')

        res = {
            'type': 'complementary',
            'preliminary': False,
            'corrective': False,
            }
        valid_details = ResultsDetail.search([
            ('id', 'in', Transaction().context['active_ids']),
            ('state', '=', 'released'),
            ('valid', '=', True),
            ])
        for valid_detail in valid_details:
            if valid_detail.type == 'preliminary':
                res['preliminary'] = True
                res['type'] = 'preliminary'
        return res

    def transition_generate(self):
        ResultsDetail = Pool().get('lims.results_report.version.detail')

        reports_created = []

        valid_details = ResultsDetail.search([
            ('id', 'in', Transaction().context['active_ids']),
            ('state', '=', 'released'),
            ('valid', '=', True),
            ])
        for valid_detail in valid_details:
            defaults = {
                'report_version': valid_detail.report_version.id,
                'type': self.start.type,
                }
            new_version, = ResultsDetail.create([defaults])
            ResultsDetail.update_from_valid_version([new_version])
            reports_created.append(new_version.id)

        ResultsDetail.write(valid_details, {
            'review_reason': self.start.review_reason,
            'review_reason_print': self.start.review_reason_print,
            })
        self.start.reports_created = reports_created
        return 'open_'

    def do_open_(self, action):
        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', 'in', [r.id for r in self.start.reports_created]),
            ])
        return action, {}

    def transition_open_(self):
        return 'end'

    def end(self):
        return 'reload'


class ResultsReportWaitingStart(ModelView):
    'Results Report Waiting'
    __name__ = 'lims.results_report_waiting.start'

    waiting_reason = fields.Text('Waiting reason', required=True)


class ResultsReportWaiting(Wizard):
    'Results Report Waiting'
    __name__ = 'lims.results_report_waiting'

    start_state = 'check'
    check = StateTransition()
    start = StateView('lims.results_report_waiting.start',
        'lims.lims_results_report_waiting_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Confirm', 'confirm', 'tryton-ok', default=True),
            ])
    confirm = StateTransition()

    def transition_check(self):
        ResultsDetail = Pool().get('lims.results_report.version.detail')

        details = ResultsDetail.search([
            ('id', 'in', Transaction().context['active_ids']),
            ('state', '=', 'draft'),
            ])
        if details:
            return 'start'
        return 'end'

    def transition_confirm(self):
        ResultsDetail = Pool().get('lims.results_report.version.detail')

        details = ResultsDetail.search([
            ('id', 'in', Transaction().context['active_ids']),
            ('state', '=', 'draft'),
            ])
        if details:
            ResultsDetail.write(details, {
                'state': 'waiting',
                'waiting_reason': self.start.waiting_reason,
                })
        return 'end'

    def end(self):
        return 'reload'


class PrintResultReport(Wizard):
    'Print Results Report'
    __name__ = 'lims.print_result_report'

    start = StateTransition()
    print_ = StateReport('lims.result_report')

    def transition_start(self):
        if Transaction().context['active_ids']:
            return 'print_'
        return 'end'

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
        if len(ids) > 1:
            raise UserError(gettext('lims.msg_multiple_reports'))

        pool = Pool()
        ResultsDetail = pool.get('lims.results_report.version.detail')
        CachedReport = pool.get('lims.results_report.cached_report')

        results_report = ResultsDetail(ids[0])
        if results_report.state == 'annulled':
            raise UserError(gettext('lims.msg_annulled_report'))

        if data is None:
            data = {}
        current_data = data.copy()
        current_data['alt_lang'] = results_report.report_language.code
        result = super().execute(ids, current_data)

        cached_reports = CachedReport.search([
            ('version_detail', '=', results_report.id),
            ('report_language', '=', results_report.report_language.id),
            ['OR',
                ('report_cache', '!=', None),
                ('report_cache_id', '!=', None)],
            ])
        if cached_reports:
            result = (cached_reports[0].report_format,
                cached_reports[0].report_cache) + result[2:]

        else:
            if current_data.get('save_cache', False):
                cached_reports = CachedReport.search([
                    ('version_detail', '=', results_report.id),
                    ('report_language', '=',
                        results_report.report_language.id),
                    ])
                if cached_reports:
                    CachedReport.write(cached_reports, {
                        'report_cache': result[1],
                        'report_format': result[0],
                        })
                else:
                    CachedReport.create([{
                        'version_detail': results_report.id,
                        'report_language': results_report.report_language.id,
                        'report_cache': result[1],
                        'report_format': result[0],
                        }])

        return result

    @classmethod
    def get_context(cls, records, header, data):
        pool = Pool()
        Company = pool.get('company.company')
        ResultsDetail = pool.get('lims.results_report.version.detail')
        ResultsLine = pool.get('lims.results_report.version.detail.line')
        NotebookLine = pool.get('lims.notebook.line')
        Sample = pool.get('lims.sample')
        RangeType = pool.get('lims.range.type')

        report_context = super().get_context(records, header, data)

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
        report_context['print_date'] = get_print_date().date()
        report_context['party'] = report.party.rec_name
        party_address = report.party.get_results_report_address()

        report_context['party_address'] = party_address.full_address.replace(
            '\n', ' - ')

        report_context['report_section'] = report.report_section
        report_context['report_type'] = report.report_type
        report_context['report_result_type'] = report.report_result_type
        group_field = ('literal_final_concentration' if
            report.report_result_type in ('both', 'both_range') else
            'initial_concentration')

        report_context['headquarters'] = report.laboratory.headquarters
        report_context['signatories'] = []
        for signer in report.signatories:
            report_context['signatories'].append({
                'signer': signer.professional.rec_name,
                'role': signer.professional.role,
                'signature': signer.professional.signature,
                })

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
        methods_by_hq = {}
        pnt_methods = {}
        pnt_methods_by_hq = {}
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
            record['literal_final_concentration'] = (
                t_line.literal_final_concentration)

            conc = getattr(t_line, group_field)
            if not conc and group_field == 'literal_final_concentration':
                conc = getattr(t_line, 'final_concentration')
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

            headquarters = t_line.department and t_line.department.headquarters
            hq_id = headquarters and headquarters.id or None
            if hq_id not in methods_by_hq:
                methods_by_hq[hq_id] = {
                    'headquarters': headquarters and headquarters.name or '',
                    'methods': {},
                    }
            if method_id not in methods_by_hq[hq_id]['methods']:
                methods_by_hq[hq_id]['methods'][method_id] = {
                    'method': t_line.method.name,
                    'analysis': [],
                    }
            methods_by_hq[hq_id]['methods'][method_id]['analysis'].append(
                record['analysis'])

            if hq_id not in pnt_methods_by_hq:
                pnt_methods_by_hq[hq_id] = {
                    'headquarters': headquarters and headquarters.name or '',
                    'methods': {},
                    }
            if record['pnt'] not in pnt_methods_by_hq[hq_id]['methods']:
                pnt_methods_by_hq[hq_id]['methods'][record['pnt']] = {
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
                    literal_final_concentration = None
                    for line in sorted_lines:
                        if (literal_final_concentration is None and
                                line['literal_final_concentration']):
                            literal_final_concentration = line[
                                'literal_final_concentration']
                        if line['converted_result']:
                            show_unit_label = True
                            break
                    if show_unit_label:
                        if literal_final_concentration is not None:
                            fraction['concentrations'][conc][
                                    'unit_label'] = (
                                literal_final_concentration)
                        else:
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

        report_context['methods_by_hq'] = []
        for hq in methods_by_hq.values():
            record = {
                'name': hq['headquarters'],
                'methods': [],
                }
            for method in hq['methods'].values():
                concat_lines = ', '.join(list(set(method['analysis'])))
                method['analysis'] = concat_lines
                record['methods'].append(method)
            report_context['methods_by_hq'].append(record)

        report_context['pnt_methods_by_hq'] = []
        for hq in pnt_methods_by_hq.values():
            record = {
                'name': hq['headquarters'],
                'methods': [m for m in hq['methods'].values()],
                }
            report_context['pnt_methods_by_hq'].append(record)

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
        res = notebook_line.formated_result
        if (report_section in ('amb', 'for', 'rp', 'sq') and
                notebook_line.result_modifier and
                notebook_line.result_modifier.code == 'low'):
            obs_ql = True
        return res, obs_ql

    @classmethod
    def get_converted_result(cls, report_section, report_result_type,
            notebook_line, obs_ql, language):
        res = notebook_line.formated_converted_result
        if (notebook_line.analysis.code != '0001' and
                not notebook_line.literal_result and
                notebook_line.converted_result_modifier and
                notebook_line.converted_result_modifier.code == 'low'):
            obs_ql = True
        return res, obs_ql

    @classmethod
    def get_initial_unit(cls, report_section, report_result_type,
            notebook_line, obs_dl, obs_uncert, language):
        if not notebook_line.initial_unit:
            return '', obs_dl, obs_uncert

        initial_unit = notebook_line.initial_unit.rec_name
        literal_result = notebook_line.literal_result
        result_modifier = (notebook_line.result_modifier and
            notebook_line.result_modifier.code)
        detection_limit = notebook_line.detection_limit
        converted_result = notebook_line.converted_result
        uncertainty = notebook_line.uncertainty
        decimals = notebook_line.decimals

        with Transaction().set_context(language=language):
            if report_section == 'rp':
                res = ''
                if (not literal_result and not result_modifier and
                        uncertainty and float(uncertainty) != 0):
                    res = round(float(uncertainty), decimals)
                    res = format(res, '.{}f'.format(decimals))
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
                                    '0', '0.0', '0.00')):
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
                            res = format(res, '.{}f'.format(decimals))
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
        converted_result_modifier = (notebook_line.converted_result_modifier
            and notebook_line.converted_result_modifier.code)
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
                            '0', '0.0', '0.00')):
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
                            res = format(res, '.{}f'.format(decimals))
                            res = gettext('lims.msg_uncertainty',
                                res=res, initial_unit=final_unit)
                            obs_uncert = True
            return res, obs_dl, obs_uncert

    @classmethod
    def get_detection_limit(cls, report_section, report_result_type,
            report_type, notebook_line, language):
        detection_limit = notebook_line.detection_limit
        literal_result = notebook_line.literal_result
        result_modifier = (notebook_line.result_modifier and
            notebook_line.result_modifier.code)

        if report_section in ('amb', 'sq'):
            res = ''
            if report_type == 'polisample' and result_modifier == 'nd':
                with Transaction().set_context(language=language):
                    res = gettext('lims.msg_detection_limit_2',
                        detection_limit=detection_limit)
        else:
            if (not detection_limit or detection_limit in (
                    '0', '0.0', '0.00') or literal_result):
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
    def get_grouped_lines(cls, sample, grouped_by=None, lang=None):
        if not sample:
            return []
        if not grouped_by:
            grouped_by = 'none'
        try:
            return getattr(cls,
                '_get_lines_grouped_by_%s' % grouped_by)(sample, lang)
        except AttributeError:
            return []

    @classmethod
    def _get_lines_grouped_by_none(cls, sample, lang=None):
        res = sample.notebook_lines
        return res

    @classmethod
    def _get_lines_grouped_by_origin(cls, sample, lang=None):
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
        if len(ids) > 1:
            raise UserError(gettext('lims.msg_multiple_reports'))

        pool = Pool()
        ResultsDetail = pool.get('lims.results_report.version.detail')
        CachedReport = pool.get('lims.results_report.cached_report')

        results_report = ResultsDetail(ids[0])
        if results_report.state == 'annulled':
            raise UserError(gettext('lims.msg_annulled_report'))

        if data is None:
            data = {}
        current_data = data.copy()
        current_data['alt_lang'] = results_report.report_language.code
        result = super(ResultReport, cls).execute(ids, current_data)

        cached_reports = CachedReport.search([
            ('version_detail', '=', results_report.id),
            ('report_language', '=', results_report.report_language.id),
            ('transcription_report_cache', '!=', None),
            ])
        if cached_reports:
            result = (cached_reports[0].transcription_report_format,
                cached_reports[0].transcription_report_cache) + result[2:]

        else:
            if current_data.get('save_cache', False):
                cached_reports = CachedReport.search([
                    ('version_detail', '=', results_report.id),
                    ('report_language', '=',
                        results_report.report_language.id),
                    ])
                if cached_reports:
                    CachedReport.write(cached_reports, {
                        'transcription_report_cache': result[1],
                        'transcription_report_format': result[0],
                        })
                else:
                    CachedReport.create([{
                        'version_detail': results_report.id,
                        'report_language': results_report.report_language.id,
                        'transcription_report_cache': result[1],
                        'transcription_report_format': result[0],
                        }])

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
        ResultsReport = Pool().get('lims.results_report')

        if not Transaction().context['active_ids']:
            return 'end'

        for active_id in Transaction().context['active_ids']:
            results_report = ResultsReport(active_id)

            details = results_report.details_cached(
                results_report.report_language)
            if not details:
                raise UserError(gettext('lims.msg_global_report_cache',
                        language=results_report.report_language.name))

            cache = results_report._get_global_report(details,
                results_report.report_language)
            if not cache:
                raise UserError(gettext('lims.msg_global_report_build'))

            results_report.report_cache = cache
            results_report.report_format = 'pdf'
            results_report.save()

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


class GlobalResultReport(Report):
    'Global Results Report'
    __name__ = 'lims.global_result_report'

    @classmethod
    def execute(cls, ids, data):
        pool = Pool()
        ResultsReport = pool.get('lims.results_report')

        result = super().execute(ids, data)

        results_report = ResultsReport(ids[0])
        result = (results_report.report_format,
            results_report.report_cache) + result[2:]

        report_name = '%s %s' % (result[3], results_report.number)
        result = result[:3] + (report_name,)
        return result
