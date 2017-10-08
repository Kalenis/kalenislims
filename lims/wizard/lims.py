# -*- coding: utf-8 -*-
# This file is part of lims module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import sys
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO
import logging
from math import sqrt
from datetime import datetime
from decimal import Decimal
from dateutil.relativedelta import relativedelta

from trytond.model import ModelView, ModelSQL, fields
from trytond.wizard import Wizard, StateTransition, StateView, StateAction, \
    Button
from trytond.pyson import PYSONEncoder, Eval, Equal, Bool, If
from trytond.pool import Pool
from trytond.transaction import Transaction
from ..formula_parser import FormulaParser


__all__ = ['LimsDuplicateSampleStart', 'LimsDuplicateSample',
    'LimsDuplicateSampleFromEntryStart', 'LimsDuplicateSampleFromEntry',
    'LimsForwardAcknowledgmentOfReceipt', 'LimsCopyTypificationStart',
    'LimsCopyTypification', 'LimsCopyCalculatedTypificationStart',
    'LimsCopyCalculatedTypification', 'LimsRelateAnalysisStart',
    'LimsRelateAnalysis', 'LimsManageServices', 'LimsCompleteServices',
    'LimsNotebookInitialConcentrationCalcStart',
    'LimsNotebookInitialConcentrationCalc',
    'LimsNotebookLineInitialConcentrationCalc',
    'LimsNotebookResultsConversionStart', 'LimsNotebookResultsConversion',
    'LimsNotebookLineResultsConversion', 'LimsNotebookLimitsValidationStart',
    'LimsNotebookLimitsValidation', 'LimsNotebookLineLimitsValidation',
    'LimsNotebookInternalRelationsCalc1Start',
    'LimsNotebookInternalRelationsCalc1Relation',
    'LimsNotebookInternalRelationsCalc1Variable',
    'LimsNotebookInternalRelationsCalc1',
    'LimsNotebookLineInternalRelationsCalc1',
    'LimsNotebookInternalRelationsCalc2Start',
    'LimsNotebookInternalRelationsCalc2Result',
    'LimsNotebookInternalRelationsCalc2Relation',
    'LimsNotebookInternalRelationsCalc2Variable',
    'LimsNotebookInternalRelationsCalc2Process',
    'LimsNotebookInternalRelationsCalc2',
    'LimsNotebookLineInternalRelationsCalc2',
    'LimsNotebookLoadResultsFormulaStart',
    'LimsNotebookLoadResultsFormulaEmpty',
    'LimsNotebookLoadResultsFormulaResult',
    'LimsNotebookLoadResultsFormulaLine',
    'LimsNotebookLoadResultsFormulaAction',
    'LimsNotebookLoadResultsFormulaProcess',
    'LimsNotebookLoadResultsFormulaVariable',
    'LimsNotebookLoadResultsFormulaBeginning',
    'LimsNotebookLoadResultsFormulaConfirm',
    'LimsNotebookLoadResultsFormulaSit1', 'LimsNotebookLoadResultsFormulaSit2',
    'LimsNotebookLoadResultsFormulaSit2Detail',
    'LimsNotebookLoadResultsFormulaSit2DetailLine',
    'LimsNotebookLoadResultsFormula', 'LimsNotebookLoadResultsManualStart',
    'LimsNotebookLoadResultsManualEmpty',
    'LimsNotebookLoadResultsManualResult', 'LimsNotebookLoadResultsManualLine',
    'LimsNotebookLoadResultsManualSit1', 'LimsNotebookLoadResultsManualSit2',
    'LimsNotebookLoadResultsManual', 'LimsNotebookAddInternalRelationsStart',
    'LimsNotebookAddInternalRelations', 'LimsNotebookLineRepeatAnalysisStart',
    'LimsNotebookLineRepeatAnalysis', 'LimsNotebookAcceptLinesStart',
    'LimsNotebookAcceptLines', 'LimsNotebookLineAcceptLines',
    'LimsNotebookLineUnacceptLines', 'FractionsByLocationsStart',
    'FractionsByLocations', 'LimsNotebookResultsVerificationStart',
    'LimsNotebookResultsVerification', 'LimsNotebookLineResultsVerification',
    'LimsUncertaintyCalcStart', 'LimsUncertaintyCalc',
    'LimsNotebookLineUncertaintyCalc', 'LimsNotebookPrecisionControlStart',
    'LimsNotebookPrecisionControl', 'LimsNotebookLinePrecisionControl',
    'LimsMeansDeviationsCalcStart', 'LimsMeansDeviationsCalcEmpty',
    'LimsMeansDeviationsCalcResult', 'LimsControlResultLine',
    'LimsControlResultLineDetail', 'LimsMeansDeviationsCalcResult2',
    'LimsMeansDeviationsCalc', 'LimsTendenciesAnalysisStart',
    'LimsTendenciesAnalysisResult', 'LimsTendenciesAnalysis',
    'LimsDivideReportsResult', 'LimsDivideReportsDetail',
    'LimsDivideReportsProcess', 'LimsDivideReports',
    'LimsGenerateResultsReportStart', 'LimsGenerateResultsReportEmpty',
    'LimsGenerateResultsReportResultAut', 'LimsGenerateResultsReportResultMan',
    'LimsGenerateResultsReportResultAutNotebook',
    'LimsGenerateResultsReportResultAutNotebookLine',
    'LimsGenerateResultsReportResultAutExcludedNotebook',
    'LimsGenerateResultsReportResultAutExcludedNotebookLine',
    'LimsGenerateResultsReport', 'LimsPrintResultsReport',
    'LimsDuplicateAnalysisFamilyStart', 'LimsDuplicateAnalysisFamily',
    'LimsServiceResultsReport', 'LimsFractionResultsReport',
    'LimsSampleResultsReport', 'LimsResultsReportSample',
    'LimsResultsReportAnnulationStart', 'LimsResultsReportAnnulation',
    'LimsCountersampleStorageStart', 'LimsCountersampleStorageEmpty',
    'LimsCountersampleStorageResult', 'LimsCountersampleStorage',
    'LimsCountersampleStorageRevertStart',
    'LimsCountersampleStorageRevertEmpty',
    'LimsCountersampleStorageRevertResult', 'LimsCountersampleStorageRevert',
    'LimsCountersampleDischargeStart', 'LimsCountersampleDischargeEmpty',
    'LimsCountersampleDischargeResult', 'LimsCountersampleDischarge',
    'LimsFractionDischargeStart', 'LimsFractionDischargeEmpty',
    'LimsFractionDischargeResult', 'LimsFractionDischarge',
    'LimsFractionDischargeRevertStart', 'LimsFractionDischargeRevertEmpty',
    'LimsFractionDischargeRevertResult', 'LimsFractionDischargeRevert',
    'LimsCreateSampleStart', 'LimsCreateSampleService', 'LimsCreateSample',
    'OpenNotebookLines', 'LimsCreateAnalysisProduct',
    'LimsChangeInvoicePartyStart', 'LimsChangeInvoicePartyError',
    'LimsChangeInvoiceParty', 'OpenTypifications', 'AddTypificationsStart',
    'AddTypifications', 'RemoveTypificationsStart', 'RemoveTypifications',
    'ChangeEstimatedDaysForResultsStart', 'ChangeEstimatedDaysForResults']

HAS_PDFMERGER = False
try:
    from PyPDF2 import PdfFileMerger
    HAS_PDFMERGER = True
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning(
        'Unable to import PyPDF2. PDF merge disabled.',
        exc_info=True)


class LimsDuplicateSampleStart(ModelView):
    'Copy Sample'
    __name__ = 'lims.sample.duplicate.start'

    sample = fields.Many2One('lims.sample', 'Sample', readonly=True)
    date = fields.DateTime('Date', required=True)
    labels = fields.Text('Labels')


class LimsDuplicateSample(Wizard):
    'Copy Sample'
    __name__ = 'lims.sample.duplicate'

    start = StateView('lims.sample.duplicate.start',
        'lims.lims_duplicate_sample_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Copy', 'duplicate', 'tryton-ok', default=True),
            ])
    duplicate = StateTransition()

    def default_start(self, fields):
        LimsSample = Pool().get('lims.sample')
        sample = LimsSample(Transaction().context['active_id'])
        return {
            'sample': sample.id,
            'date': sample.date,
            }

    def transition_duplicate(self):
        LimsSample = Pool().get('lims.sample')

        sample = self.start.sample
        date = self.start.date
        labels_list = self._get_labels_list(self.start.labels)
        for label in labels_list:
            LimsSample.copy([sample], default={
                'label': label,
                'date': date,
                })
        return 'end'

    def _get_labels_list(self, labels=None):
        if not labels:
            return [None]
        return labels.split('\n')


class LimsDuplicateSampleFromEntryStart(ModelView):
    'Copy Sample'
    __name__ = 'lims.entry.duplicate_sample.start'

    entry = fields.Many2One('lims.entry', 'Entry')
    sample = fields.Many2One('lims.sample', 'Sample', required=True,
        domain=[('entry', '=', Eval('entry'))], depends=['entry'])
    date = fields.DateTime('Date', required=True)
    labels = fields.Text('Labels')

    @fields.depends('sample')
    def on_change_with_date(self, name=None):
        if self.sample:
            return self.sample.date
        return False


class LimsDuplicateSampleFromEntry(Wizard):
    'Copy Sample'
    __name__ = 'lims.entry.duplicate_sample'

    start = StateView('lims.entry.duplicate_sample.start',
        'lims.lims_duplicate_sample_from_entry_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Copy', 'duplicate', 'tryton-ok', default=True),
            ])
    duplicate = StateTransition()

    def default_start(self, fields):
        return {
            'entry': Transaction().context['active_id'],
            }

    def transition_duplicate(self):
        LimsSample = Pool().get('lims.sample')

        sample = self.start.sample
        date = self.start.date
        labels_list = self._get_labels_list(self.start.labels)
        for label in labels_list:
            LimsSample.copy([sample], default={
                'label': label,
                'date': date,
                })
        return 'end'

    def _get_labels_list(self, labels=None):
        if not labels:
            return [None]
        return labels.split('\n')


class LimsForwardAcknowledgmentOfReceipt(Wizard):
    'Forward Acknowledgment of Samples Receipt'
    __name__ = 'lims.entry.acknowledgment.forward'

    start = StateTransition()

    def transition_start(self):
        LimsEntry = Pool().get('lims.entry')

        for active_id in Transaction().context['active_ids']:
            entry = LimsEntry(active_id)
            if entry.state != 'ongoing':
                continue
            if not entry.no_acknowledgment_of_receipt:
                printable = False
                cie_entry = False
                for sample in entry.samples:
                    if not sample.fractions:
                        break
                    for fraction in sample.fractions:
                        if fraction.cie_fraction_type:
                            cie_entry = True
                            break
                        if (fraction.confirmed and fraction.services):
                            printable = True
                            break
                if printable:
                    entry.ack_report_cache = None
                    entry.ack_report_format = None
                    entry.save()
                    if not entry.print_report():
                        entry.result_cron = 'failed_print'
                        entry.save()
                        continue
                    if not entry.mail_acknowledgment_of_receipt():
                        entry.result_cron = 'failed_send'
                        entry.save()
                        continue
                    entry.result_cron = 'sent'
                    entry.sent_date = datetime.now()
                    entry.save()
                if cie_entry:
                    entry.result_cron = 'sent'
                    entry.sent_date = datetime.now()
                    entry.save()
        return 'end'


class LimsCopyTypificationStart(ModelView):
    'Copy/Move Typification'
    __name__ = 'lims.typification.copy.start'

    origin_product_type = fields.Many2One('lims.product.type', 'Product type',
        required=True)
    origin_matrix = fields.Many2One('lims.matrix', 'Matrix', required=True)
    origin_analysis = fields.Many2One('lims.analysis', 'Analysis',
        domain=[
            ('state', '=', 'active'),
            ('type', '=', 'analysis'),
            ('behavior', '!=', 'additional'),
            ])
    origin_method = fields.Many2One('lims.lab.method', 'Method',
        states={'required': Bool(Eval('destination_method'))},
        depends=['destination_method'])
    destination_product_type = fields.Many2One('lims.product.type',
        'Product type', required=True)
    destination_matrix = fields.Many2One('lims.matrix', 'Matrix',
        required=True)
    destination_method = fields.Many2One('lims.lab.method', 'Method')
    action = fields.Selection([
        ('copy', 'Copy'),
        ('move', 'Move'),
        ], 'Action', required=True,
        help='If choose <Move>, the origin typifications will be deactivated')

    @staticmethod
    def default_action():
        return 'copy'


class LimsCopyTypification(Wizard):
    'Copy/Move Typification'
    __name__ = 'lims.typification.copy'

    start = StateView('lims.typification.copy.start',
        'lims.lims_copy_typification_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Confirm', 'confirm', 'tryton-ok', default=True),
            ])
    confirm = StateTransition()

    def transition_confirm(self):
        LimsTypification = Pool().get('lims.typification')

        clause = [
            ('product_type', '=', self.start.origin_product_type.id),
            ('matrix', '=', self.start.origin_matrix.id),
            ('valid', '=', True),
            ]
        if self.start.origin_analysis:
            clause.append(('analysis', '=', self.start.origin_analysis.id))
        if self.start.origin_method:
            clause.append(('method', '=', self.start.origin_method.id))

        product_type_id = self.start.destination_product_type.id
        matrix_id = self.start.destination_matrix.id
        method_id = (self.start.destination_method.id if
            self.start.destination_method else None)

        origins = LimsTypification.search(clause)
        if origins and self.start.action == 'move':
            LimsTypification.write(origins, {
                'valid': False,
                'by_default': False,
                })

        to_copy_1 = []
        to_copy_2 = []
        for origin in origins:
            if LimsTypification.search_count([
                    ('product_type', '=', product_type_id),
                    ('matrix', '=', matrix_id),
                    ('analysis', '=', origin.analysis.id),
                    ('method', '=', method_id or origin.method.id)
                    ]) != 0:
                continue
            if LimsTypification.search_count([
                    ('valid', '=', True),
                    ('product_type', '=', product_type_id),
                    ('matrix', '=', matrix_id),
                    ('analysis', '=', origin.analysis.id),
                    ('by_default', '=', True),
                    ]) != 0:
                to_copy_1.append(origin)
            else:
                to_copy_2.append(origin)

        if to_copy_1:
            default = {
                'valid': True,
                'product_type': product_type_id,
                'matrix': matrix_id,
                'by_default': False,
                }
            if method_id:
                default['method'] = method_id
                for r in to_copy_1:
                    method_domain = [m.id for m in r.analysis.methods]
                    if method_id not in method_domain:
                        to_copy_1.remove(r)
            LimsTypification.copy(to_copy_1, default=default)
        if to_copy_2:
            default = {
                'valid': True,
                'product_type': product_type_id,
                'matrix': matrix_id,
                'by_default': True,
                }
            if method_id:
                default['method'] = method_id
                for r in to_copy_2:
                    method_domain = [m.id for m in r.analysis.methods]
                    if method_id not in method_domain:
                        to_copy_2.remove(r)
            LimsTypification.copy(to_copy_2, default=default)
        return 'end'


class LimsCopyCalculatedTypificationStart(ModelView):
    'Copy Typification'
    __name__ = 'lims.typification.calculated.copy.start'

    origin_product_type = fields.Many2One('lims.product.type', 'Product type',
        required=True)
    origin_matrix = fields.Many2One('lims.matrix', 'Matrix', required=True)
    origin_analysis = fields.Many2One('lims.analysis', 'Set/Group',
        required=True, domain=[
            ('state', '=', 'active'),
            ('type', 'in', ('set', 'group')),
            ])
    destination_product_type = fields.Many2One('lims.product.type',
        'Product type', required=True)
    destination_matrix = fields.Many2One('lims.matrix', 'Matrix',
        required=True)


class LimsCopyCalculatedTypification(Wizard):
    'Copy Typification'
    __name__ = 'lims.typification.calculated.copy'

    start = StateView('lims.typification.calculated.copy.start',
        'lims.lims_copy_calculated_typification_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Confirm', 'confirm', 'tryton-ok', default=True),
            ])
    confirm = StateTransition()

    def transition_confirm(self):
        pool = Pool()
        LimsAnalysis = pool.get('lims.analysis')
        LimsTypification = pool.get('lims.typification')

        included_analysis_ids = LimsAnalysis.get_included_analysis_analysis(
            self.start.origin_analysis.id)
        if not included_analysis_ids:
            return 'end'

        clause = [
            ('product_type', '=', self.start.origin_product_type.id),
            ('matrix', '=', self.start.origin_matrix.id),
            ('valid', '=', True),
            ('analysis', 'in', included_analysis_ids),
            ]

        product_type_id = self.start.destination_product_type.id
        matrix_id = self.start.destination_matrix.id

        origins = LimsTypification.search(clause)

        to_copy_1 = []
        to_copy_2 = []
        for origin in origins:
            if LimsTypification.search_count([
                    ('product_type', '=', product_type_id),
                    ('matrix', '=', matrix_id),
                    ('analysis', '=', origin.analysis.id),
                    ('method', '=', origin.method.id)
                    ]) != 0:
                continue
            if LimsTypification.search_count([
                    ('valid', '=', True),
                    ('product_type', '=', product_type_id),
                    ('matrix', '=', matrix_id),
                    ('analysis', '=', origin.analysis.id),
                    ('by_default', '=', True),
                    ]) != 0:
                to_copy_1.append(origin)
            else:
                to_copy_2.append(origin)

        if to_copy_1:
            default = {
                'valid': True,
                'product_type': product_type_id,
                'matrix': matrix_id,
                'by_default': False,
                }
            LimsTypification.copy(to_copy_1, default=default)
        if to_copy_2:
            default = {
                'valid': True,
                'product_type': product_type_id,
                'matrix': matrix_id,
                'by_default': True,
                }
            LimsTypification.copy(to_copy_2, default=default)
        return 'end'


class LimsRelateAnalysisStart(ModelView):
    'Relate Analysis'
    __name__ = 'lims.relate_analysis.start'

    analysis = fields.Many2Many('lims.analysis', None, None,
        'Analysis', required=True,
        domain=[('id', 'in', Eval('analysis_domain'))],
        depends=['analysis_domain'])
    analysis_domain = fields.One2Many('lims.analysis', None,
        'Analysis domain')


class LimsRelateAnalysis(Wizard):
    'Relate Analysis'
    __name__ = 'lims.relate_analysis'

    start = StateView('lims.relate_analysis.start',
        'lims.lims_relate_analysis_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Relate', 'relate', 'tryton-ok', default=True),
            ])
    relate = StateTransition()

    @classmethod
    def __setup__(cls):
        super(LimsRelateAnalysis, cls).__setup__()
        cls._error_messages.update({
            'not_set_laboratory': 'No Laboratory loaded for the Set',
            })

    def default_start(self, fields):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsAnalysis = pool.get('lims.analysis')
        LimsAnalysisLaboratory = pool.get('lims.analysis-laboratory')

        analysis = LimsAnalysis(Transaction().context['active_id'])
        default = {
            'analysis_domain': [],
            }
        if len(analysis.laboratories) != 1:
            self.raise_user_error('not_set_laboratory')
            #return default

        cursor.execute('SELECT DISTINCT(al.analysis) '
            'FROM "' + LimsAnalysisLaboratory._table + '" al '
                'INNER JOIN "' + LimsAnalysis._table + '" a '
                'ON a.id = al.analysis '
            'WHERE al.laboratory = %s '
                'AND a.state = \'active\' '
                'AND a.type = \'analysis\' '
                'AND a.end_date IS NULL '
                'AND al.analysis != %s',
            (analysis.laboratories[0].laboratory.id, analysis.id,))
        res = cursor.fetchall()
        if res:
            default['analysis_domain'] = [x[0] for x in res]
        return default

    def transition_relate(self):
        LimsAnalysis = Pool().get('lims.analysis')
        analysis = LimsAnalysis(Transaction().context['active_id'])

        to_create = [{
            'analysis': analysis.id,
            'included_analysis': al.id,
            'laboratory': analysis.laboratories[0].laboratory.id,
            } for al in self.start.analysis]
        LimsAnalysis.write([analysis], {
            'included_analysis': [('create', to_create)],
            })
        return 'end'


class LimsManageServices(Wizard):
    'Manage Services'
    __name__ = 'lims.manage_services'

    start_state = 'check'
    check = StateTransition()
    start = StateView('lims.fraction',
        'lims.lims_manage_services_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Ok', 'ok', 'tryton-ok', default=True),
            ])
    ok = StateTransition()

    @classmethod
    def __setup__(cls):
        super(LimsManageServices, cls).__setup__()
        cls._error_messages.update({
            'counter_sample_date':
                'Reverse counter sample storage to enter the service ',
            })

    def default_start(self, fields):
        LimsFraction = Pool().get('lims.fraction')

        fraction = LimsFraction(Transaction().context['active_id'])
        if not fraction:
            return {}

        not_planned_services_ids = [s.id for s in fraction.services if
            s.manage_service_available]
        analysis_domain_ids = fraction.on_change_with_analysis_domain()
        typification_domain_ids = fraction.on_change_with_typification_domain()

        default = {
            'id': fraction.id,
            'sample': fraction.sample.id,
            'entry': fraction.entry.id,
            'party': fraction.party.id,
            'services': not_planned_services_ids,
            'analysis_domain': analysis_domain_ids,
            'typification_domain': typification_domain_ids,
            'product_type': fraction.product_type.id,
            'matrix': fraction.matrix.id,
            }
        return default

    def transition_check(self):
        LimsFraction = Pool().get('lims.fraction')

        fraction = LimsFraction(Transaction().context['active_id'])
        if fraction.countersample_date is None:
            return 'start'
        else:
            self.raise_user_error('counter_sample_date')
        return 'end'

    def transition_ok(self):
        pool = Pool()
        LimsEntry = pool.get('lims.entry')
        LimsFraction = pool.get('lims.fraction')

        delete_ack_report_cache = False
        fraction = LimsFraction(Transaction().context['active_id'])

        original_services = [s for s in fraction.services if
            s.manage_service_available]
        actual_services = self.start.services

        for service in original_services:
            if service not in actual_services:
                self.delete_service(service)
                delete_ack_report_cache = True

        for service in actual_services:
            if service not in original_services:
                self.create_service(service, fraction)
                delete_ack_report_cache = True

        for original_service in original_services:
            for actual_service in actual_services:
                if original_service == actual_service:
                    for field in self._get_comparison_fields():
                        if (getattr(original_service, field) !=
                                getattr(actual_service, field)):
                            self.update_service(original_service,
                                actual_service, fraction, field)
                            delete_ack_report_cache = True
                            break

        if delete_ack_report_cache:
            entry = LimsEntry(fraction.entry.id)
            entry.ack_report_format = None
            entry.ack_report_cache = None
            entry.save()

        return 'end'

    def create_service(self, service, fraction):
        pool = Pool()
        LimsService = pool.get('lims.service')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        service_create = [{
            'fraction': fraction.id,
            'sample': service.sample.id,
            'analysis': service.analysis.id,
            'urgent': service.urgent,
            'priority': service.priority,
            'report_date': service.report_date,
            'laboratory': (service.laboratory.id if service.laboratory
                else None),
            'method': service.method.id if service.method else None,
            'device': service.device.id if service.device else None,
            'comments': service.comments,
            'divide': service.divide,
            }]
        with Transaction().set_context(manage_service=True):
            new_service, = LimsService.create(service_create)

        LimsService.copy_analysis_comments([new_service])
        LimsService.set_confirmation_date([new_service])
        analysis_detail = EntryDetailAnalysis.search([
            ('service', '=', new_service.id)])
        if analysis_detail:
            EntryDetailAnalysis.create_notebook_lines(analysis_detail,
                fraction)

        return new_service

    def delete_service(self, service):
        LimsService = Pool().get('lims.service')
        with Transaction().set_user(0, set_context=True):
            LimsService.delete([service])

    def update_service(self, original_service, actual_service, fraction,
            field_changed):
        pool = Pool()
        LimsService = pool.get('lims.service')
        LimsNotebookLine = pool.get('lims.notebook.line')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        service_write = {}
        service_write[field_changed] = getattr(actual_service, field_changed)
        LimsService.write([original_service], service_write)

        update_details = True if field_changed in ('analysis', 'laboratory',
            'method', 'device') else False

        if update_details:
            notebook_lines = LimsNotebookLine.search([
                ('service', '=', original_service.id),
                ])
            if notebook_lines:
                LimsNotebookLine.delete(notebook_lines)

            analysis_detail = EntryDetailAnalysis.search([
                ('service', '=', original_service.id)])
            if analysis_detail:
                EntryDetailAnalysis.create_notebook_lines(analysis_detail,
                    fraction)

    def _get_comparison_fields(self):
        return ('analysis', 'laboratory', 'method', 'device', 'urgent',
            'priority', 'report_date', 'comments', 'divide')


class LimsCompleteServices(Wizard):
    'Complete Services'
    __name__ = 'lims.complete_services'

    start = StateTransition()

    def transition_start(self):
        LimsFraction = Pool().get('lims.fraction')
        fraction = LimsFraction(Transaction().context['active_id'])
        for service in fraction.services:
            if service.analysis.behavior != 'additional':
                self.complete_analysis_detail(service)
        return 'end'

    def complete_analysis_detail(self, service):
        'Similar to LimsService.update_analysis_detail(services)'
        pool = Pool()
        LimsService = pool.get('lims.service')
        LimsEntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        analysis_data = []
        if service.analysis.type == 'analysis':
            laboratory_id = service.laboratory.id
            method_id = service.method.id if service.method else None
            device_id = service.device.id if service.device else None

            analysis_data.append({
                'id': service.analysis.id,
                'origin': service.analysis.code,
                'laboratory': laboratory_id,
                'method': method_id,
                'device': device_id,
                })
        else:
            service_context = {
                'product_type': service.fraction.product_type.id,
                'matrix': service.fraction.matrix.id,
                }

            analysis_data.extend(LimsService._get_included_analysis(
                service.analysis, service.analysis.code,
                service_context))

        to_create = []
        for analysis in analysis_data:
            if LimsEntryDetailAnalysis.search_count([
                    ('service', '=', service.id),
                    ('analysis', '=', analysis['id']),
                    ]) != 0:
                continue
            values = {}
            values['service'] = service.id
            values['analysis'] = analysis['id']
            values['analysis_origin'] = analysis['origin']
            values['laboratory'] = analysis['laboratory']
            values['method'] = analysis['method']
            values['device'] = analysis['device']
            values['confirmation_date'] = service.confirmation_date
            # from lims_planification
            if 'trytond.modules.lims_planification' in sys.modules:
                values['state'] = 'unplanned'
            to_create.append(values)

        if to_create:
            with Transaction().set_user(0, set_context=True):
                analysis_detail = LimsEntryDetailAnalysis.create(to_create)
            if analysis_detail:
                LimsEntryDetailAnalysis.create_notebook_lines(analysis_detail,
                    service.fraction)


class LimsNotebookInitialConcentrationCalcStart(ModelView):
    'Initial Concentration Calculation'
    __name__ = 'lims.notebook.initial_concentration_calc.start'


class LimsNotebookInitialConcentrationCalc(Wizard):
    'Initial Concentration Calculation'
    __name__ = 'lims.notebook.initial_concentration_calc'

    start_state = 'ok'
    start = StateView('lims.notebook.initial_concentration_calc.start',
        'lims.lims_notebook_initial_concentration_calc_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Ok', 'ok', 'tryton-ok', default=True),
            ])
    ok = StateTransition()

    def transition_ok(self):
        LimsNotebook = Pool().get('lims.notebook')

        for active_id in Transaction().context['active_ids']:
            notebook = LimsNotebook(active_id)
            if not notebook.lines:
                continue
            self.lines_initial_concentration_calc(notebook.lines)
        return 'end'

    def lines_initial_concentration_calc(self, notebook_lines):
        LimsNotebookLine = Pool().get('lims.notebook.line')

        lines_to_save = []
        for notebook_line in notebook_lines:
            if notebook_line.accepted:
                continue
            ic = notebook_line.initial_concentration
            if not ic:
                continue
            if ic[0] == 'A':
                analysis_code = ic[1:]
                result = self._get_analysis_result(analysis_code,
                    notebook_line.notebook)
                if result is not None:
                    notebook_line.initial_concentration = str(result)
                    lines_to_save.append(notebook_line)
            elif ic[0] == 'R':
                analysis_code = ic[1:]
                result = self._get_relation_result(analysis_code,
                    notebook_line.notebook)
                if result is not None:
                    notebook_line.initial_concentration = str(result)
                    lines_to_save.append(notebook_line)
            else:
                continue
        if lines_to_save:
            LimsNotebookLine.save(lines_to_save)

    def _get_analysis_result(self, analysis_code, notebook, round_=False):
        LimsNotebookLine = Pool().get('lims.notebook.line')

        with Transaction().set_user(0):
            notebook_lines = LimsNotebookLine.search([
                ('notebook', '=', notebook.id),
                ('analysis.code', '=', analysis_code),
                ('annulment_date', '=', None),
                ])
        if not notebook_lines:
            return None

        try:
            res = float(notebook_lines[0].result)
        except (TypeError, ValueError):
            return None
        if not round_:
            return res
        return round(res, notebook_lines[0].decimals)

    def _get_relation_result(self, analysis_code, notebook, round_=False):
        pool = Pool()
        LimsAnalysis = pool.get('lims.analysis')
        LimsNotebookLine = pool.get('lims.notebook.line')

        internal_relations = LimsAnalysis.search([
            ('code', '=', analysis_code),
            ])
        if not internal_relations:
            return None
        formula = internal_relations[0].result_formula
        if not formula:
            return None
        for i in (' ', '\t', '\n', '\r'):
            formula = formula.replace(i, '')
        variables = self._get_variables(formula, notebook)
        if not variables:
            return None

        parser = FormulaParser(formula, variables)
        value = parser.getValue()

        if int(value) == value:
            res = int(value)
        else:
            epsilon = 0.0000000001
            if int(value + epsilon) != int(value):
                res = int(value + epsilon)
            elif int(value - epsilon) != int(value):
                res = int(value)
            else:
                res = float(value)
        if not round_:
            return res

        with Transaction().set_user(0):
            notebook_lines = LimsNotebookLine.search([
                ('notebook', '=', notebook.id),
                ('analysis.code', '=', analysis_code),
                ('repetition', '=', 0),
                ('annulment_date', '=', None),
                ])
        if not notebook_lines:
            return None
        return round(res, notebook_lines[0].decimals)

    def _get_variables(self, formula, notebook):
        LimsVolumeConversion = Pool().get('lims.volume.conversion')

        variables = {}
        for prefix in ('A', 'D', 'T', 'Y', 'R'):
            while True:
                idx = formula.find(prefix)
                if idx >= 0:
                    var = formula[idx:idx + 5]
                    variables[var] = None
                    formula = formula.replace(var, '_')
                else:
                    break
        for var in variables.iterkeys():
            if var[0] == 'A':
                analysis_code = var[1:]
                result = self._get_analysis_result(analysis_code, notebook,
                    round_=True)
                if result is not None:
                    variables[var] = result
            elif var[0] == 'D':
                analysis_code = var[1:]
                result = self._get_analysis_result(analysis_code, notebook,
                    round_=True)
                if result is not None:
                    result = LimsVolumeConversion.brixToDensity(result)
                    if result is not None:
                        variables[var] = result
            elif var[0] == 'T':
                analysis_code = var[1:]
                result = self._get_analysis_result(analysis_code, notebook,
                    round_=True)
                if result is not None:
                    result = LimsVolumeConversion.brixToSolubleSolids(result)
                    if result is not None:
                        variables[var] = result
            elif var[0] == 'R':
                analysis_code = var[1:]
                result = self._get_relation_result(analysis_code, notebook,
                    round_=True)
                if result is not None:
                    result = LimsVolumeConversion.brixToSolubleSolids(result)
                    if result is not None:
                        variables[var] = result
            elif var[0] == 'Y':
                analysis_code = var[1:]
                result = self._get_relation_result(analysis_code, notebook,
                    round_=True)
                if result is not None:
                    result = LimsVolumeConversion.brixToDensity(result)
                    if result is not None:
                        variables[var] = result
        for var in variables.itervalues():
            if var is None:
                return None
        return variables


class LimsNotebookLineInitialConcentrationCalc(
        LimsNotebookInitialConcentrationCalc):
    'Initial Concentration Calculation'
    __name__ = 'lims.notebook_line.initial_concentration_calc'

    def transition_ok(self):
        LimsNotebookLine = Pool().get('lims.notebook.line')

        notebook_lines = LimsNotebookLine.browse(
            Transaction().context['active_ids'])
        if not notebook_lines:
            return 'end'

        self.lines_initial_concentration_calc(notebook_lines)
        return 'end'


class LimsNotebookResultsConversionStart(ModelView):
    'Results Conversion'
    __name__ = 'lims.notebook.results_conversion.start'


class LimsNotebookResultsConversion(Wizard):
    'Results Conversion'
    __name__ = 'lims.notebook.results_conversion'

    start_state = 'ok'
    start = StateView('lims.notebook.results_conversion.start',
        'lims.lims_notebook_results_conversion_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Ok', 'ok', 'tryton-ok', default=True),
            ])
    ok = StateTransition()

    def transition_ok(self):
        LimsNotebook = Pool().get('lims.notebook')

        for active_id in Transaction().context['active_ids']:
            notebook = LimsNotebook(active_id)
            if not notebook.lines:
                continue
            self.lines_results_conversion(notebook.lines)
        return 'end'

    def lines_results_conversion(self, notebook_lines):
        pool = Pool()
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsUomConversion = pool.get('lims.uom.conversion')
        LimsVolumeConversion = pool.get('lims.volume.conversion')

        lines_to_save = []
        for notebook_line in notebook_lines:
            if notebook_line.accepted:
                continue
            if (notebook_line.converted_result or not notebook_line.result
                    or notebook_line.result_modifier != 'eq'):
                continue
            iu = notebook_line.initial_unit
            if not iu:
                continue
            fu = notebook_line.final_unit
            if not fu:
                continue
            try:
                ic = float(notebook_line.initial_concentration)
            except (TypeError, ValueError):
                continue
            try:
                fc = float(notebook_line.final_concentration)
            except (TypeError, ValueError):
                continue
            try:
                result = float(notebook_line.result)
            except (TypeError, ValueError):
                continue

            if (iu == fu and ic == fc):
                converted_result = result
                notebook_line.converted_result = str(converted_result)
                notebook_line.converted_result_modifier = 'eq'
                lines_to_save.append(notebook_line)
            elif (iu != fu and ic == fc):
                formula = LimsUomConversion.get_conversion_formula(iu, fu)
                if not formula:
                    continue
                variables = self._get_variables(formula, notebook_line)
                parser = FormulaParser(formula, variables)
                formula_result = parser.getValue()

                converted_result = result * formula_result
                notebook_line.converted_result = str(converted_result)
                notebook_line.converted_result_modifier = 'eq'
                lines_to_save.append(notebook_line)
            elif (iu == fu and ic != fc):
                converted_result = result * (fc / ic)
                notebook_line.converted_result = str(converted_result)
                notebook_line.converted_result_modifier = 'eq'
                lines_to_save.append(notebook_line)
            else:
                formula = None
                conversions = LimsUomConversion.search([
                    ('initial_uom', '=', iu),
                    ('final_uom', '=', fu),
                    ])
                if conversions:
                    formula = conversions[0].conversion_formula
                if not formula:
                    continue

                initial_uom_volume = conversions[0].initial_uom_volume
                final_uom_volume = conversions[0].final_uom_volume
                variables = self._get_variables(formula, notebook_line,
                    initial_uom_volume, final_uom_volume)
                parser = FormulaParser(formula, variables)
                formula_result = parser.getValue()

                if initial_uom_volume and final_uom_volume:
                    d_ic = LimsVolumeConversion.brixToDensity(ic)
                    d_fc = LimsVolumeConversion.brixToDensity(fc)
                    converted_result = (result * (fc / ic) * (d_fc / d_ic)
                        * formula_result)
                    notebook_line.converted_result = str(converted_result)
                    notebook_line.converted_result_modifier = 'eq'
                    lines_to_save.append(notebook_line)
                else:
                    converted_result = result * (fc / ic) * formula_result
                    notebook_line.converted_result = str(converted_result)
                    notebook_line.converted_result_modifier = 'eq'
                    lines_to_save.append(notebook_line)
        if lines_to_save:
            LimsNotebookLine.save(lines_to_save)

    def _get_variables(self, formula, notebook_line,
            initial_uom_volume=False, final_uom_volume=False):
        LimsVolumeConversion = Pool().get('lims.volume.conversion')

        variables = {}
        for var in ('DI',):
            while True:
                idx = formula.find(var)
                if idx >= 0:
                    variables[var] = 0
                    formula = formula.replace(var, '_')
                else:
                    break
        for var in variables.iterkeys():
            if var == 'DI':
                if initial_uom_volume:
                    c = float(notebook_line.initial_concentration)
                    result = LimsVolumeConversion.brixToDensity(c)
                    if result:
                        variables[var] = result
                elif final_uom_volume:
                    c = float(notebook_line.final_concentration)
                    result = LimsVolumeConversion.brixToDensity(c)
                    if result:
                        variables[var] = result
        return variables


class LimsNotebookLineResultsConversion(LimsNotebookResultsConversion):
    'Results Conversion'
    __name__ = 'lims.notebook_line.results_conversion'

    def transition_ok(self):
        LimsNotebookLine = Pool().get('lims.notebook.line')

        notebook_lines = LimsNotebookLine.browse(
            Transaction().context['active_ids'])
        if not notebook_lines:
            return 'end'

        self.lines_results_conversion(notebook_lines)
        return 'end'


class LimsNotebookLimitsValidationStart(ModelView):
    'Limits Validation'
    __name__ = 'lims.notebook.limits_validation.start'


class LimsNotebookLimitsValidation(Wizard):
    'Limits Validation'
    __name__ = 'lims.notebook.limits_validation'

    start_state = 'ok'
    start = StateView('lims.notebook.limits_validation.start',
        'lims.lims_notebook_limits_validation_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Ok', 'ok', 'tryton-ok', default=True),
            ])
    ok = StateTransition()

    def transition_ok(self):
        LimsNotebook = Pool().get('lims.notebook')

        for active_id in Transaction().context['active_ids']:
            notebook = LimsNotebook(active_id)
            if not notebook.lines:
                continue
            self.lines_limits_validation(notebook.lines)
        return 'end'

    def lines_limits_validation(self, notebook_lines):
        LimsNotebookLine = Pool().get('lims.notebook.line')

        lines_to_save = []
        for notebook_line in notebook_lines:
            if notebook_line.accepted:
                continue
            try:
                dl = float(notebook_line.detection_limit)
                ql = float(notebook_line.quantification_limit)
            except (TypeError, ValueError):
                continue

            if (notebook_line.result and (
                    notebook_line.check_result_limits or
                    not notebook_line.converted_result)):
                if notebook_line.result_modifier != 'eq':
                    continue
                try:
                    value = float(notebook_line.result)
                except ValueError:
                    continue
                if dl < value and value < ql:
                    notebook_line.result = str(ql)
                    notebook_line.result_modifier = 'low'
                    notebook_line.converted_result = None
                    notebook_line.converted_result_modifier = 'eq'
                    notebook_line.rm_correction_formula = None
                elif value < dl:
                    notebook_line.result = None
                    notebook_line.result_modifier = 'nd'
                    notebook_line.converted_result = None
                    notebook_line.converted_result_modifier = 'eq'
                    notebook_line.rm_correction_formula = None
                elif value == dl:
                    notebook_line.result = str(ql)
                    notebook_line.result_modifier = 'low'
                    notebook_line.converted_result = None
                    notebook_line.converted_result_modifier = 'eq'
                    notebook_line.rm_correction_formula = None
                notebook_line.backup = str(value)
                lines_to_save.append(notebook_line)

            elif notebook_line.converted_result:
                if notebook_line.converted_result_modifier != 'eq':
                    continue
                try:
                    value = float(notebook_line.converted_result)
                except ValueError:
                    continue
                if dl < value and value < ql:
                    notebook_line.converted_result = str(ql)
                    notebook_line.converted_result_modifier = 'low'
                    notebook_line.result_modifier = 'ni'
                    notebook_line.rm_correction_formula = None
                elif value < dl:
                    notebook_line.converted_result = None
                    notebook_line.converted_result_modifier = 'nd'
                    notebook_line.result_modifier = 'ni'
                    notebook_line.rm_correction_formula = None
                elif value == dl:
                    notebook_line.converted_result = str(ql)
                    notebook_line.converted_result_modifier = 'low'
                    notebook_line.result_modifier = 'ni'
                    notebook_line.rm_correction_formula = None
                notebook_line.backup = str(value)
                lines_to_save.append(notebook_line)

            else:
                continue

        if lines_to_save:
            LimsNotebookLine.save(lines_to_save)


class LimsNotebookLineLimitsValidation(LimsNotebookLimitsValidation):
    'Limits Validation'
    __name__ = 'lims.notebook_line.limits_validation'

    def transition_ok(self):
        LimsNotebookLine = Pool().get('lims.notebook.line')

        notebook_lines = LimsNotebookLine.browse(
            Transaction().context['active_ids'])
        if not notebook_lines:
            return 'end'

        self.lines_limits_validation(notebook_lines)
        return 'end'


class LimsNotebookInternalRelationsCalc1Start(ModelView):
    'Internal Relations Calculation'
    __name__ = 'lims.notebook.internal_relations_calc_1.start'


class LimsNotebookInternalRelationsCalc1Relation(ModelSQL):
    'Internal Relations Calculation'
    __name__ = 'lims.notebook.internal_relations_calc_1.relation'
    _table = 'lims_notebook_internal_relations_c_1_rel'

    notebook = fields.Many2One('lims.notebook', 'Laboratory notebook')
    internal_relation = fields.Many2One('lims.analysis', 'Internal relation')
    variables = fields.One2Many(
        'lims.notebook.internal_relations_calc_1.variable', 'relation',
        'Variables')
    session_id = fields.Integer('Session ID')

    @classmethod
    def __register__(cls, module_name):
        super(LimsNotebookInternalRelationsCalc1Relation,
            cls).__register__(module_name)
        cursor = Transaction().connection.cursor()
        cursor.execute('DELETE FROM "' + cls._table + '"')


class LimsNotebookInternalRelationsCalc1Variable(ModelSQL):
    'Formula Variable'
    __name__ = 'lims.notebook.internal_relations_calc_1.variable'

    relation = fields.Many2One(
        'lims.notebook.internal_relations_calc_1.relation', 'Relation',
        ondelete='CASCADE', readonly=True)
    line = fields.Many2One('lims.notebook.line', 'Line')
    analysis = fields.Many2One('lims.analysis', 'Analysis', readonly=True)
    repetition = fields.Integer('Repetition', readonly=True)
    use = fields.Boolean('Use')


class LimsNotebookInternalRelationsCalc1(Wizard):
    'Internal Relations Calculation'
    __name__ = 'lims.notebook.internal_relations_calc_1'

    start_state = 'search'
    start = StateView('lims.notebook.internal_relations_calc_1.start',
        'lims.lims_notebook_internal_relations_calc_1_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search', 'search', 'tryton-go-next', default=True),
            ])
    search = StateTransition()
    confirm = StateTransition()

    def transition_search(self):
        LimsNotebook = Pool().get('lims.notebook')

        notebook = LimsNotebook(Transaction().context['active_id'])
        if not notebook.lines:
            return 'end'

        if self.get_relations(notebook.lines):
            return 'confirm'
        return 'end'

    def get_relations(self, notebook_lines):
        LimsNotebookInternalRelationsCalc1Relation = Pool().get(
            'lims.notebook.internal_relations_calc_1.relation')

        relations = {}
        for notebook_line in notebook_lines:
            if notebook_line.accepted:
                continue
            analysis_code = notebook_line.analysis.code
            if (not analysis_code or notebook_line.analysis.behavior
                    != 'internal_relation'):
                continue
            if notebook_line.result or notebook_line.converted_result:
                continue

            formulas = notebook_line.analysis.result_formula
            formulas += ("+" +
                notebook_line.analysis.converted_result_formula)
            for i in (' ', '\t', '\n', '\r'):
                formulas = formulas.replace(i, '')
            variables = self._get_variables_list(formulas,
                notebook_line.notebook, {})
            if not variables:
                continue
            has_repetition_zero = False
            for var in variables:
                if var['use']:
                    has_repetition_zero = True
            if not has_repetition_zero:
                continue

            relations[notebook_line.analysis.id] = {
                'notebook': notebook_line.notebook.id,
                'internal_relation': notebook_line.analysis.id,
                'variables': [('create', variables)],
                'session_id': self._session_id,
                }
        if relations:
            LimsNotebookInternalRelationsCalc1Relation.create(
                [ir for ir in relations.itervalues()])
            return True
        return False

    def _get_variables_list(self, formula, notebook, analysis={}):
        pool = Pool()
        LimsAnalysis = pool.get('lims.analysis')
        LimsNotebookLine = pool.get('lims.notebook.line')

        variables = {}
        for prefix in ('A', 'D', 'T', 'Y', 'R'):
            while True:
                idx = formula.find(prefix)
                if idx >= 0:
                    var = formula[idx:idx + 5]
                    variables[var] = None
                    formula = formula.replace(var, '_')
                else:
                    break
        for var in variables.iterkeys():
            if var[0] in ('A', 'D', 'T'):
                analysis_code = var[1:]
                with Transaction().set_user(0):
                    notebook_lines = LimsNotebookLine.search([
                        ('notebook', '=', notebook.id),
                        ('analysis.code', '=', analysis_code),
                        ('annulment_date', '=', None),
                        ])
                if not notebook_lines:
                    continue
                for nl in notebook_lines:
                    analysis[nl.id] = {
                        'line': nl.id,
                        'analysis': nl.analysis.id,
                        'repetition': nl.repetition,
                        'use': True if nl.repetition == 0 else False,
                        }
            elif var[0] in ('Y', 'R'):
                analysis_code = var[1:]
                internal_relations = LimsAnalysis.search([
                    ('code', '=', analysis_code),
                    ])
                if not internal_relations:
                    continue
                more_formulas = internal_relations[0].converted_result_formula
                more_formulas += "+" + internal_relations[0].result_formula
                for i in (' ', '\t', '\n', '\r'):
                    more_formulas = more_formulas.replace(i, '')
                self._get_variables_list(more_formulas, notebook, analysis)

        return [v for v in analysis.itervalues()]

    def transition_confirm(self):
        pool = Pool()
        Date = pool.get('ir.date')
        LimsNotebookInternalRelationsCalc1Relation = pool.get(
            'lims.notebook.internal_relations_calc_1.relation')
        LimsNotebookLine = pool.get('lims.notebook.line')

        date = Date.today()

        relations = LimsNotebookInternalRelationsCalc1Relation.search([
            ('session_id', '=', self._session_id),
            ])
        notebook_lines_to_save = []
        for relation in relations:
            notebook_lines = LimsNotebookLine.search([
                ('notebook', '=', relation.notebook.id),
                ('analysis', '=', relation.internal_relation.id)
                ])
            if len(notebook_lines) != 1:
                continue

            analysis_code = relation.internal_relation.code
            result = self._get_relation_result(analysis_code,
                relation.notebook, analysis_code)
            converted_result = self._get_relation_result(analysis_code,
                relation.notebook, analysis_code, converted=True)

            notebook_line = notebook_lines[0]
            if result is not None:
                notebook_line.result = str(result)
            if converted_result is not None:
                notebook_line.converted_result = str(converted_result)
            if result is not None or converted_result is not None:
                notebook_line.start_date = date
                notebook_line.end_date = date
                notebook_lines_to_save.append(notebook_line)
        LimsNotebookLine.save(notebook_lines_to_save)
        return 'end'

    def _get_analysis_result(self, analysis_code, notebook, relation_code,
            converted=False):
        LimsNotebookInternalRelationsCalc1Variable = Pool().get(
            'lims.notebook.internal_relations_calc_1.variable')

        variables = LimsNotebookInternalRelationsCalc1Variable.search([
            ('relation.session_id', '=', self._session_id),
            ('relation.notebook', '=', notebook.id),
            ('relation.internal_relation.code', '=', relation_code),
            ('analysis.code', '=', analysis_code),
            ('use', '=', True),
            ])
        if not variables:
            return None

        notebook_line = variables[0].line
        if not notebook_line:
            return None

        try:
            if converted:
                res = float(notebook_line.converted_result)
            else:
                res = float(notebook_line.result)
        except (TypeError, ValueError):
            return None
        return round(res, notebook_line.decimals)

    def _get_relation_result(self, analysis_code, notebook, relation_code,
            converted=False, round_=False):
        pool = Pool()
        LimsAnalysis = pool.get('lims.analysis')
        LimsNotebookLine = pool.get('lims.notebook.line')

        internal_relations = LimsAnalysis.search([
            ('code', '=', analysis_code),
            ])
        if not internal_relations:
            return None
        if converted:
            formula = internal_relations[0].converted_result_formula
        else:
            formula = internal_relations[0].result_formula
        if not formula:
            return None
        for i in (' ', '\t', '\n', '\r'):
            formula = formula.replace(i, '')
        variables = self._get_variables(formula, notebook, relation_code,
            converted)
        if not variables:
            return None

        parser = FormulaParser(formula, variables)
        value = parser.getValue()

        if int(value) == value:
            res = int(value)
        else:
            epsilon = 0.0000000001
            if int(value + epsilon) != int(value):
                res = int(value + epsilon)
            elif int(value - epsilon) != int(value):
                res = int(value)
            else:
                res = float(value)
        if not round_:
            return res

        with Transaction().set_user(0):
            notebook_lines = LimsNotebookLine.search([
                ('notebook', '=', notebook.id),
                ('analysis.code', '=', analysis_code),
                ('repetition', '=', 0),
                ('annulment_date', '=', None),
                ])
        if not notebook_lines:
            return None
        return round(res, notebook_lines[0].decimals)

    def _get_variables(self, formula, notebook, relation_code,
            converted=False):
        LimsVolumeConversion = Pool().get('lims.volume.conversion')

        variables = {}
        for prefix in ('A', 'D', 'T', 'Y', 'R'):
            while True:
                idx = formula.find(prefix)
                if idx >= 0:
                    var = formula[idx:idx + 5]
                    variables[var] = None
                    formula = formula.replace(var, '_')
                else:
                    break
        for var in variables.iterkeys():
            if var[0] == 'A':
                analysis_code = var[1:]
                result = self._get_analysis_result(analysis_code, notebook,
                    relation_code, converted)
                if result is not None:
                    variables[var] = result
            elif var[0] == 'D':
                analysis_code = var[1:]
                result = self._get_analysis_result(analysis_code, notebook,
                    relation_code, converted)
                if result is not None:
                    result = LimsVolumeConversion.brixToDensity(result)
                    if result is not None:
                        variables[var] = result
            elif var[0] == 'T':
                analysis_code = var[1:]
                result = self._get_analysis_result(analysis_code, notebook,
                    relation_code, converted)
                if result is not None:
                    result = LimsVolumeConversion.brixToSolubleSolids(result)
                    if result is not None:
                        variables[var] = result
            elif var[0] == 'R':
                analysis_code = var[1:]
                result = self._get_relation_result(analysis_code, notebook,
                    relation_code, converted, round_=True)
                if result is not None:
                    result = LimsVolumeConversion.brixToSolubleSolids(result)
                    if result is not None:
                        variables[var] = result
            elif var[0] == 'Y':
                analysis_code = var[1:]
                result = self._get_relation_result(analysis_code, notebook,
                    relation_code, converted, round_=True)
                if result is not None:
                    result = LimsVolumeConversion.brixToDensity(result)
                    if result is not None:
                        variables[var] = result
        for var in variables.itervalues():
            if var is None:
                return None
        return variables


class LimsNotebookLineInternalRelationsCalc1(
        LimsNotebookInternalRelationsCalc1):
    'Internal Relations Calculation'
    __name__ = 'lims.notebook_line.internal_relations_calc_1'

    def transition_search(self):
        LimsNotebookLine = Pool().get('lims.notebook.line')

        notebook_lines = LimsNotebookLine.browse(
            Transaction().context['active_ids'])
        if not notebook_lines:
            return 'end'

        if self.get_relations(notebook_lines):
            return 'confirm'
        return 'end'


class LimsNotebookInternalRelationsCalc2Start(ModelView):
    'Internal Relations Calculation'
    __name__ = 'lims.notebook.internal_relations_calc_2.start'


class LimsNotebookInternalRelationsCalc2Result(ModelView):
    'Internal Relations Calculation'
    __name__ = 'lims.notebook.internal_relations_calc_2.result'

    relations = fields.Many2Many(
        'lims.notebook.internal_relations_calc_2.relation', None, None,
        'Relation')
    total = fields.Integer('Total')
    index = fields.Integer('Index')


class LimsNotebookInternalRelationsCalc2Relation(ModelSQL, ModelView):
    'Internal Relations Calculation'
    __name__ = 'lims.notebook.internal_relations_calc_2.relation'
    _table = 'lims_notebook_internal_relations_c_2_rel'

    notebook = fields.Many2One('lims.notebook', 'Laboratory notebook')
    internal_relation = fields.Many2One('lims.analysis', 'Internal relation')
    variables = fields.One2Many(
        'lims.notebook.internal_relations_calc_2.variable', 'relation',
        'Variables')
    session_id = fields.Integer('Session ID')

    @classmethod
    def __register__(cls, module_name):
        super(LimsNotebookInternalRelationsCalc2Relation,
            cls).__register__(module_name)
        cursor = Transaction().connection.cursor()
        cursor.execute('DELETE FROM "' + cls._table + '"')


class LimsNotebookInternalRelationsCalc2Variable(ModelSQL, ModelView):
    'Formula Variable'
    __name__ = 'lims.notebook.internal_relations_calc_2.variable'

    relation = fields.Many2One(
        'lims.notebook.internal_relations_calc_2.relation', 'Relation',
        ondelete='CASCADE', readonly=True)
    line = fields.Many2One('lims.notebook.line', 'Line')
    analysis = fields.Many2One('lims.analysis', 'Analysis', readonly=True)
    repetition = fields.Integer('Repetition', readonly=True)
    result_modifier = fields.Function(fields.Selection([
        ('eq', '='),
        ('low', '<'),
        ('nd', 'nd'),
        ('na', 'na'),
        ('pos', 'Positive'),
        ('neg', 'Negative'),
        ('ni', 'ni'),
        ('abs', 'Absence'),
        ('pre', 'Presence'),
        ], 'Result modifier'), 'get_line_field')
    result = fields.Function(fields.Char('Result'), 'get_line_field')
    initial_unit = fields.Function(fields.Many2One('product.uom',
        'Initial unit'), 'get_line_field')
    initial_concentration = fields.Function(fields.Char(
        'Initial concentration'), 'get_line_field')
    converted_result_modifier = fields.Function(fields.Selection([
        ('eq', '='),
        ('low', '<'),
        ('nd', 'nd'),
        ('na', 'na'),
        ('pos', 'Positive'),
        ('neg', 'Negative'),
        ('ni', 'ni'),
        ], 'Converted result modifier'), 'get_line_field')
    converted_result = fields.Function(fields.Char('Converted result'),
        'get_line_field')
    final_unit = fields.Function(fields.Many2One('product.uom', 'Final unit'),
        'get_line_field')
    final_concentration = fields.Function(fields.Char('Final concentration'),
        'get_line_field')
    use = fields.Boolean('Use')

    @classmethod
    def __setup__(cls):
        super(LimsNotebookInternalRelationsCalc2Variable, cls).__setup__()
        cls._order.insert(0, ('relation', 'ASC'))
        cls._order.insert(1, ('analysis', 'ASC'))
        cls._order.insert(2, ('repetition', 'ASC'))

    @classmethod
    def get_line_field(cls, variables, names):
        result = {}
        for name in names:
            result[name] = {}
            if name in ('initial_unit', 'final_unit'):
                for v in variables:
                    field = getattr(v.line, name, None)
                    result[name][v.id] = field.id if field else None
            else:
                for v in variables:
                    result[name][v.id] = getattr(v.line, name, None)
        return result


class LimsNotebookInternalRelationsCalc2Process(ModelView):
    'Internal Relations Calculation'
    __name__ = 'lims.notebook.internal_relations_calc_2.process'

    notebook = fields.Many2One('lims.notebook', 'Laboratory notebook',
        readonly=True)
    internal_relation = fields.Many2One('lims.analysis', 'Internal relation',
        readonly=True)
    variables = fields.One2Many(
        'lims.notebook.internal_relations_calc_2.variable', None,
        'Variables')


class LimsNotebookInternalRelationsCalc2(Wizard):
    'Internal Relations Calculation'
    __name__ = 'lims.notebook.internal_relations_calc_2'

    start_state = 'search'
    start = StateView('lims.notebook.internal_relations_calc_2.start',
        'lims.lims_notebook_internal_relations_calc_2_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search', 'search', 'tryton-go-next', default=True),
            ])
    search = StateTransition()
    result = StateView('lims.notebook.internal_relations_calc_2.result',
        'lims.lims_notebook_internal_relations_calc_2_result_view_form', [])
    next_ = StateTransition()
    process = StateView('lims.notebook.internal_relations_calc_2.process',
        'lims.lims_notebook_internal_relations_calc_2_process_view_form', [
            Button('Next', 'check_variables', 'tryton-go-next', default=True),
            ])
    check_variables = StateTransition()
    confirm = StateTransition()

    def transition_search(self):
        LimsNotebook = Pool().get('lims.notebook')

        for active_id in Transaction().context['active_ids']:
            notebook = LimsNotebook(active_id)
            if not notebook.lines:
                continue

            if self.get_relations(notebook.lines):
                return 'next_'
        return 'end'

    def get_relations(self, notebook_lines):
        LimsNotebookInternalRelationsCalc2Relation = Pool().get(
            'lims.notebook.internal_relations_calc_2.relation')

        relations = {}
        for notebook_line in notebook_lines:
            if notebook_line.accepted:
                continue
            analysis_code = notebook_line.analysis.code
            if (not analysis_code or notebook_line.analysis.behavior
                    != 'internal_relation'):
                continue
            if notebook_line.result or notebook_line.converted_result:
                continue

            formulas = notebook_line.analysis.result_formula
            formulas += ("+" +
                notebook_line.analysis.converted_result_formula)
            for i in (' ', '\t', '\n', '\r'):
                formulas = formulas.replace(i, '')
            variables = self._get_variables_list(formulas,
                notebook_line.notebook, {})
            if not variables:
                continue
            has_repetitions = False
            for var in variables:
                if var['repetition'] > 0:
                    has_repetitions = True
            if not has_repetitions:
                continue

            relations[notebook_line.analysis.id] = {
                'notebook': notebook_line.notebook.id,
                'internal_relation': notebook_line.analysis.id,
                'variables': [('create', variables)],
                'session_id': self._session_id,
                }

        if relations:
            res_lines = LimsNotebookInternalRelationsCalc2Relation.create(
                [ir for ir in relations.itervalues()])
            self.result.relations = res_lines
            self.result.total = len(self.result.relations)
            self.result.index = 0
            return True
        return False

    def transition_next_(self):
        if self.result.index < self.result.total:
            relation = self.result.relations[self.result.index]
            self.process.notebook = relation.notebook.id
            self.process.internal_relation = relation.internal_relation.id
            self.process.variables = None
            self.result.index += 1
            return 'process'
        return 'confirm'

    def default_process(self, fields):
        LimsNotebookInternalRelationsCalc2Variable = Pool().get(
            'lims.notebook.internal_relations_calc_2.variable')

        if not self.process.internal_relation:
            return {}

        default = {}
        default['notebook'] = self.process.notebook.id
        default['internal_relation'] = self.process.internal_relation.id
        if self.process.variables:
            default['variables'] = [v.id for v in self.process.variables]
        else:
            variables = LimsNotebookInternalRelationsCalc2Variable.search([
                ('relation.session_id', '=', self._session_id),
                ('relation.notebook', '=', self.process.notebook.id),
                ('relation.internal_relation', '=',
                    self.process.internal_relation.id),
                ])
            if variables:
                default['variables'] = [v.id for v in variables]
        return default

    def _get_variables_list(self, formula, notebook, analysis={}):
        pool = Pool()
        LimsAnalysis = pool.get('lims.analysis')
        LimsNotebookLine = pool.get('lims.notebook.line')

        variables = {}
        for prefix in ('A', 'D', 'T', 'Y', 'R'):
            while True:
                idx = formula.find(prefix)
                if idx >= 0:
                    var = formula[idx:idx + 5]
                    variables[var] = None
                    formula = formula.replace(var, '_')
                else:
                    break
        for var in variables.iterkeys():
            if var[0] in ('A', 'D', 'T'):
                analysis_code = var[1:]
                with Transaction().set_user(0):
                    notebook_lines = LimsNotebookLine.search([
                        ('notebook', '=', notebook.id),
                        ('analysis.code', '=', analysis_code),
                        ('annulment_date', '=', None),
                        ])
                if not notebook_lines:
                    continue
                for nl in notebook_lines:
                    analysis[nl.id] = {
                        'line': nl.id,
                        'analysis': nl.analysis.id,
                        'repetition': nl.repetition,
                        'use': True if nl.repetition == 0 else False,
                        }
            elif var[0] in ('R', 'Y'):
                analysis_code = var[1:]
                internal_relations = LimsAnalysis.search([
                    ('code', '=', analysis_code),
                    ])
                if not internal_relations:
                    continue
                more_formulas = internal_relations[0].converted_result_formula
                more_formulas += "+" + internal_relations[0].result_formula
                for i in (' ', '\t', '\n', '\r'):
                    more_formulas = more_formulas.replace(i, '')
                self._get_variables_list(more_formulas, notebook, analysis)

        return [v for v in analysis.itervalues()]

    def transition_check_variables(self):
        variables = {}
        for var in self.process.variables:
            analysis_code = var.analysis.code
            if analysis_code not in variables:
                variables[analysis_code] = False
            if var.use:
                if variables[analysis_code]:
                    variables[analysis_code] = False
                else:
                    variables[analysis_code] = True
            var.save()

        for var in variables.itervalues():
            if not var:
                return 'process'
        return 'next_'

    def transition_confirm(self):
        pool = Pool()
        Date = pool.get('ir.date')
        LimsNotebookInternalRelationsCalc2Relation = pool.get(
            'lims.notebook.internal_relations_calc_2.relation')
        LimsNotebookLine = pool.get('lims.notebook.line')

        date = Date.today()

        relations = LimsNotebookInternalRelationsCalc2Relation.search([
            ('session_id', '=', self._session_id),
            ])
        notebook_lines_to_save = []
        for relation in relations:
            notebook_lines = LimsNotebookLine.search([
                ('notebook', '=', relation.notebook.id),
                ('analysis', '=', relation.internal_relation.id)
                ])
            if len(notebook_lines) != 1:
                continue

            analysis_code = relation.internal_relation.code
            result = self._get_relation_result(analysis_code,
                relation.notebook, analysis_code)
            converted_result = self._get_relation_result(analysis_code,
                relation.notebook, analysis_code, converted=True)

            notebook_line = notebook_lines[0]
            if result is not None:
                notebook_line.result = str(result)
            if converted_result is not None:
                notebook_line.converted_result = str(converted_result)
            if result is not None or converted_result is not None:
                notebook_line.start_date = date
                notebook_line.end_date = date
                notebook_lines_to_save.append(notebook_line)
        LimsNotebookLine.save(notebook_lines_to_save)

        return 'end'

    def _get_analysis_result(self, analysis_code, notebook, relation_code,
            converted=False):
        LimsNotebookInternalRelationsCalc2Variable = Pool().get(
            'lims.notebook.internal_relations_calc_2.variable')

        variables = LimsNotebookInternalRelationsCalc2Variable.search([
            ('relation.session_id', '=', self._session_id),
            ('relation.notebook', '=', notebook.id),
            ('relation.internal_relation.code', '=', relation_code),
            ('analysis.code', '=', analysis_code),
            ('use', '=', True),
            ])
        if not variables:
            return None

        notebook_line = variables[0].line
        if not notebook_line:
            return None

        try:
            if converted:
                res = float(notebook_line.converted_result)
            else:
                res = float(notebook_line.result)
        except (TypeError, ValueError):
            return None
        return round(res, notebook_line.decimals)

    def _get_relation_result(self, analysis_code, notebook, relation_code,
            converted=False, round_=False):
        pool = Pool()
        LimsAnalysis = pool.get('lims.analysis')
        LimsNotebookLine = pool.get('lims.notebook.line')

        internal_relations = LimsAnalysis.search([
            ('code', '=', analysis_code),
            ])
        if not internal_relations:
            return None
        if converted:
            formula = internal_relations[0].converted_result_formula
        else:
            formula = internal_relations[0].result_formula
        if not formula:
            return None
        for i in (' ', '\t', '\n', '\r'):
            formula = formula.replace(i, '')
        variables = self._get_variables(formula, notebook, relation_code,
            converted)
        if not variables:
            return None

        parser = FormulaParser(formula, variables)
        value = parser.getValue()

        if int(value) == value:
            res = int(value)
        else:
            epsilon = 0.0000000001
            if int(value + epsilon) != int(value):
                res = int(value + epsilon)
            elif int(value - epsilon) != int(value):
                res = int(value)
            else:
                res = float(value)
        if not round_:
            return res

        with Transaction().set_user(0):
            notebook_lines = LimsNotebookLine.search([
                ('notebook', '=', notebook.id),
                ('analysis.code', '=', analysis_code),
                ('repetition', '=', 0),
                ('annulment_date', '=', None),
                ])
        if not notebook_lines:
            return None
        return round(res, notebook_lines[0].decimals)

    def _get_variables(self, formula, notebook, relation_code,
            converted=False):
        LimsVolumeConversion = Pool().get('lims.volume.conversion')

        variables = {}
        for prefix in ('A', 'D', 'T', 'Y', 'R'):
            while True:
                idx = formula.find(prefix)
                if idx >= 0:
                    var = formula[idx:idx + 5]
                    variables[var] = None
                    formula = formula.replace(var, '_')
                else:
                    break
        for var in variables.iterkeys():
            if var[0] == 'A':
                analysis_code = var[1:]
                result = self._get_analysis_result(analysis_code, notebook,
                    relation_code, converted)
                if result is not None:
                    variables[var] = result
            elif var[0] == 'D':
                analysis_code = var[1:]
                result = self._get_analysis_result(analysis_code, notebook,
                    relation_code, converted)
                if result is not None:
                    result = LimsVolumeConversion.brixToDensity(result)
                    if result is not None:
                        variables[var] = result
            elif var[0] == 'T':
                analysis_code = var[1:]
                result = self._get_analysis_result(analysis_code, notebook,
                    relation_code, converted)
                if result is not None:
                    result = LimsVolumeConversion.brixToSolubleSolids(result)
                    if result is not None:
                        variables[var] = result
            elif var[0] == 'R':
                analysis_code = var[1:]
                result = self._get_relation_result(analysis_code, notebook,
                    relation_code, converted, round_=True)
                if result is not None:
                    result = LimsVolumeConversion.brixToSolubleSolids(result)
                    if result is not None:
                        variables[var] = result
            elif var[0] == 'Y':
                analysis_code = var[1:]
                result = self._get_relation_result(analysis_code, notebook,
                    relation_code, converted, round_=True)
                if result is not None:
                    result = LimsVolumeConversion.brixToDensity(result)
                    if result is not None:
                        variables[var] = result
        for var in variables.itervalues():
            if var is None:
                return None
        return variables


class LimsNotebookLineInternalRelationsCalc2(
        LimsNotebookInternalRelationsCalc2):
    'Internal Relations Calculation'
    __name__ = 'lims.notebook_line.internal_relations_calc_2'

    def transition_search(self):
        LimsNotebookLine = Pool().get('lims.notebook.line')

        notebook_lines = LimsNotebookLine.browse(
            Transaction().context['active_ids'])
        if not notebook_lines:
            return 'end'

        if self.get_relations(notebook_lines):
            return 'next_'
        return 'end'


class LimsNotebookLoadResultsFormulaStart(ModelView):
    'Load Results by Formula'
    __name__ = 'lims.notebook.load_results_formula.start'

    analysis = fields.Many2One('lims.analysis', 'Analysis',
        domain=[('state', '=', 'active'), ('formula', '!=', None)])
    method = fields.Many2One('lims.lab.method', 'Method')
    start_date = fields.Date('Start date', required=True)


class LimsNotebookLoadResultsFormulaEmpty(ModelView):
    'Load Results by Formula'
    __name__ = 'lims.notebook.load_results_formula.empty'


class LimsNotebookLoadResultsFormulaResult(ModelView):
    'Load Results by Formula'
    __name__ = 'lims.notebook.load_results_formula.result'

    lines = fields.Many2Many('lims.notebook.load_results_formula.line',
        None, None, 'Lines')
    total = fields.Integer('Total')
    index = fields.Integer('Index')


class LimsNotebookLoadResultsFormulaLine(ModelSQL, ModelView):
    'Load Results by Formula'
    __name__ = 'lims.notebook.load_results_formula.line'

    index = fields.Integer('Index')
    line = fields.Many2One('lims.notebook.line', 'Line')
    session_id = fields.Integer('Session ID')

    @classmethod
    def __register__(cls, module_name):
        super(LimsNotebookLoadResultsFormulaLine,
            cls).__register__(module_name)
        cursor = Transaction().connection.cursor()
        cursor.execute('DELETE FROM "' + cls._table + '"')


class LimsNotebookLoadResultsFormulaAction(ModelSQL):
    'Load Results by Formula'
    __name__ = 'lims.notebook.load_results_formula.action'

    line = fields.Many2One('lims.notebook.line', 'Line')
    result = fields.Char('Result')
    result_modifier = fields.Selection([
        ('eq', '='),
        ('low', '<'),
        ('nd', 'nd'),
        ('na', 'na'),
        ('pos', 'Positive'),
        ('neg', 'Negative'),
        ('ni', 'ni'),
        ('abs', 'Absence'),
        ('pre', 'Presence'),
        ], 'Result modifier', sort=False)
    end_date = fields.Date('End date')
    professional = fields.Many2One('lims.laboratory.professional',
        'Laboratory professional')
    chromatogram = fields.Char('Chromatogram')
    initial_concentration = fields.Char('Initial concentration')
    comments = fields.Text('Comments')
    formula = fields.Many2One('lims.formula', 'Formula')
    variables = fields.One2Many('lims.notebook.load_results_formula.variable',
        'action', 'Variables')
    session_id = fields.Integer('Session ID')

    @classmethod
    def __register__(cls, module_name):
        super(LimsNotebookLoadResultsFormulaAction,
            cls).__register__(module_name)
        cursor = Transaction().connection.cursor()
        cursor.execute('DELETE FROM "' + cls._table + '"')


class LimsNotebookLoadResultsFormulaProcess(ModelView):
    'Load Results by Formula'
    __name__ = 'lims.notebook.load_results_formula.process'

    line = fields.Many2One('lims.notebook.line', 'Line', readonly=True)
    repetition = fields.Integer('Repetition', readonly=True)
    fraction = fields.Many2One('lims.fraction', 'Fraction', readonly=True)
    product_type = fields.Many2One('lims.product.type', 'Product type',
        readonly=True)
    matrix = fields.Many2One('lims.matrix', 'Matrix', readonly=True)
    formula = fields.Many2One('lims.formula', 'Formula', readonly=True)
    formula_formula = fields.Function(fields.Char('Formula'),
        'on_change_with_formula_formula')
    variables = fields.One2Many('lims.notebook.load_results_formula.variable',
        None, 'Variables')
    result = fields.Char('Result', required=True)
    result_modifier = fields.Selection([
        ('eq', '='),
        ('low', '<'),
        ('nd', 'nd'),
        ('na', 'na'),
        ('pos', 'Positive'),
        ('neg', 'Negative'),
        ('ni', 'ni'),
        ('abs', 'Absence'),
        ('pre', 'Presence'),
        ], 'Result modifier', sort=False, required=True)
    end_date = fields.Date('End date')
    end_date_copy = fields.Boolean('Field copy')
    professional = fields.Many2One('lims.laboratory.professional',
        'Laboratory professional', required=True, readonly=True)
    chromatogram = fields.Char('Chromatogram')
    chromatogram_copy = fields.Boolean('Field copy')
    initial_concentration = fields.Char('Initial concentration')
    initial_concentration_copy = fields.Boolean('Field copy')
    comments = fields.Text('Comments')
    comments_copy = fields.Boolean('Field copy')

    @fields.depends('formula', 'variables')
    def on_change_with_result(self, name=None):
        if not self.formula or not self.variables:
            return None

        formula = self.formula.formula
        variables = {}
        for variable in self.variables:
            if not variable.value:
                return ''
            variables[variable.number] = variable.value

        parser = FormulaParser(formula, variables)
        value = parser.getValue()

        return str(value)

    @fields.depends('formula')
    def on_change_with_formula_formula(self, name=None):
        if self.formula:
            formula = self.formula.formula
            variables = {}
            for variable in self.variables:
                variables[variable.number] = variable.description
            for k, v in variables.iteritems():
                formula = formula.replace(k, v)
            return formula
        return ''


class LimsNotebookLoadResultsFormulaVariable(ModelSQL, ModelView):
    'Formula Variable'
    __name__ = 'lims.notebook.load_results_formula.variable'

    action = fields.Many2One('lims.notebook.load_results_formula.action',
        'Action', ondelete='CASCADE')
    number = fields.Char('Number', readonly=True)
    description = fields.Char('Description', readonly=True)
    value = fields.Char('Value')


class LimsNotebookLoadResultsFormulaBeginning(ModelView):
    'Load Results by Formula'
    __name__ = 'lims.notebook.load_results_formula.beginning'


class LimsNotebookLoadResultsFormulaConfirm(ModelView):
    'Load Results by Formula'
    __name__ = 'lims.notebook.load_results_formula.confirm'


class LimsNotebookLoadResultsFormulaSit1(ModelView):
    'Professionals Control'
    __name__ = 'lims.notebook.load_results_formula.sit1'

    msg = fields.Text('Message')


class LimsNotebookLoadResultsFormulaSit2(ModelView):
    'Professionals Control'
    __name__ = 'lims.notebook.load_results_formula.sit2'

    details = fields.One2Many('lims.notebook.load_results_formula.sit2.detail',
        None, 'Supervisors')


class LimsNotebookLoadResultsFormulaSit2Detail(ModelSQL, ModelView):
    'Supervisor'
    __name__ = 'lims.notebook.load_results_formula.sit2.detail'
    _table = 'lims_notebook_load_results_formula_s2_detail'

    professional = fields.Many2One('lims.laboratory.professional',
        'Professional', readonly=True)
    method = fields.Many2One('lims.lab.method', 'Method', readonly=True)
    supervisor = fields.Many2One('lims.laboratory.professional',
        'Supervisor', depends=['supervisor_domain'],
        domain=[('id', 'in', Eval('supervisor_domain'))])
    supervisor_domain = fields.Function(fields.Many2Many(
        'lims.laboratory.professional', None, None, 'Supervisor domain'),
        'get_supervisor_domain')
    lines = fields.Many2Many(
        'lims.notebook.load_results_formula.sit2.detail.line',
        'load_results', 'notebook_line', 'Lines')
    session_id = fields.Integer('Session ID')

    @classmethod
    def __register__(cls, module_name):
        super(LimsNotebookLoadResultsFormulaSit2Detail,
            cls).__register__(module_name)
        cursor = Transaction().connection.cursor()
        cursor.execute('DELETE FROM "' + cls._table + '"')

    def get_supervisor_domain(self, name=None):
        LimsLabProfessionalMethod = Pool().get('lims.lab.professional.method')

        res = []
        qualifications = LimsLabProfessionalMethod.search([
            ('method', '=', self.method.id),
            ('type', '=', 'analytical'),
            ('state', 'in', ('qualified', 'requalified')),
            ])
        if qualifications:
            res = [q.professional.id for q in qualifications]
        return res


class LimsNotebookLoadResultsFormulaSit2DetailLine(ModelSQL):
    'Notebook Line'
    __name__ = 'lims.notebook.load_results_formula.sit2.detail.line'
    _table = 'lims_notebook_load_results_formula_sit2_d_l'

    load_results = fields.Many2One(
        'lims.notebook.load_results_formula.sit2.detail', 'Load Results',
        ondelete='CASCADE', select=True, required=True)
    notebook_line = fields.Many2One('lims.notebook.line', 'Notebook Line',
        ondelete='CASCADE', select=True, required=True)


class LimsNotebookLoadResultsFormula(Wizard):
    'Load Results by Formula'
    __name__ = 'lims.notebook.load_results_formula'

    start = StateView('lims.notebook.load_results_formula.start',
        'lims.lims_notebook_load_results_formula_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search', 'search', 'tryton-go-next', default=True),
            ])
    search = StateTransition()
    empty = StateView('lims.notebook.load_results_formula.empty',
        'lims.lims_notebook_load_results_formula_empty_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search again', 'start', 'tryton-go-next', default=True),
            ])
    result = StateView('lims.notebook.load_results_formula.result',
        'lims.lims_notebook_load_results_formula_result_view_form', [])
    next_ = StateTransition()
    prev_ = StateTransition()
    process = StateView('lims.notebook.load_results_formula.process',
        'lims.lims_notebook_load_results_formula_process_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Previous', 'prev_', 'tryton-go-previous'),
            Button('Next', 'next_', 'tryton-go-next', default=True),
            ])
    beginning = StateView('lims.notebook.load_results_formula.beginning',
        'lims.lims_notebook_load_results_formula_beginning_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Next', 'next_', 'tryton-go-next', default=True),
            ])
    confirm = StateView('lims.notebook.load_results_formula.confirm',
        'lims.lims_notebook_load_results_formula_confirm_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Previous', 'prev_', 'tryton-go-previous'),
            Button('Confirm', 'check_professional', 'tryton-ok', default=True),
            ])
    check_professional = StateTransition()
    sit1 = StateView('lims.notebook.load_results_formula.sit1',
        'lims.lims_notebook_load_results_formula_sit1_view_form', [
            Button('Cancel', 'end', 'tryton-cancel', default=True),
            ])
    sit2 = StateView('lims.notebook.load_results_formula.sit2',
        'lims.lims_notebook_load_results_formula_sit2_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Confirm', 'sit2_ok', 'tryton-ok', default=True),
            ])
    sit2_ok = StateTransition()
    confirm_ = StateTransition()

    def transition_search(self):
        pool = Pool()
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsNotebookLoadResultsFormulaLine = pool.get(
            'lims.notebook.load_results_formula.line')

        clause = [
            ('start_date', '=', self.start.start_date),
            ('end_date', '=', None),
            ('analysis.formula', '!=', None),
            ]
        if self.start.analysis:
            clause.append(('analysis', '=', self.start.analysis.id))
        if self.start.method:
            clause.append(('method', '=', self.start.method.id))

        lines = LimsNotebookLine.search(clause, order=[
            ('analysis_order', 'ASC'), ('id', 'ASC')])
        if lines:
            res_lines = []
            count = 1
            for line in lines:
                res_line, = LimsNotebookLoadResultsFormulaLine.create([{
                    'session_id': self._session_id,
                    'index': count,
                    'line': line.id,
                    }])
                res_lines.append(res_line.id)
                count += 1

            self.result.lines = res_lines
            self.result.total = len(res_lines)
            self.result.index = 0
            return 'next_'
        return 'empty'

    def transition_next_(self):
        pool = Pool()
        LimsNotebookLoadResultsFormulaAction = pool.get(
            'lims.notebook.load_results_formula.action')
        LimsNotebookLoadResultsFormulaLine = pool.get(
            'lims.notebook.load_results_formula.line')
        LimsLaboratoryProfessional = pool.get('lims.laboratory.professional')

        has_prev = (hasattr(self.process, 'line') and
            getattr(self.process, 'line'))
        if has_prev:
            defaults = {
                'session_id': self._session_id,
                'line': self.process.line.id,
                'result': self.process.result,
                'result_modifier': self.process.result_modifier,
                'end_date': self.process.end_date,
                'professional': self.process.professional.id,
                'chromatogram': self.process.chromatogram,
                'initial_concentration': self.process.initial_concentration,
                'comments': self.process.comments,
                'formula': (self.process.formula.id if
                    self.process.formula else None),
                }
            variables = []
            for var in self.process.variables:
                variables.append({
                    'number': var.number,
                    'description': var.description,
                    'value': var.value,
                    })
            defaults['variables'] = [('create', variables)]

            action = LimsNotebookLoadResultsFormulaAction.search([
                ('session_id', '=', self._session_id),
                ('line', '=', self.process.line.id),
                ])
            if action:
                defaults['variables'] = [(
                    'delete', [v.id for a in action for v in a.variables],
                    )] + defaults['variables']
                LimsNotebookLoadResultsFormulaAction.write(action, defaults)
            else:
                LimsNotebookLoadResultsFormulaAction.create([defaults])

        self.result.index += 1
        if self.result.index <= self.result.total:

            line = LimsNotebookLoadResultsFormulaLine.search([
                ('session_id', '=', self._session_id),
                ('index', '=', self.result.index),
                ])
            self.process.line = line[0].line.id

            action = LimsNotebookLoadResultsFormulaAction.search([
                ('session_id', '=', self._session_id),
                ('line', '=', line[0].line.id),
                ])
            if action:
                self.process.result = action[0].result
                self.process.result_modifier = action[0].result_modifier
                self.process.end_date = action[0].end_date
                self.process.professional = action[0].professional.id
                self.process.chromatogram = action[0].chromatogram
                self.process.initial_concentration = (
                    action[0].initial_concentration)
                self.process.comments = action[0].comments
                self.process.formula = action[0].formula
                self.process.variables = [v.id for v in action[0].variables]
            elif has_prev:
                self.process.result = None
                self.process.result_modifier = 'eq'
                if not self.process.end_date_copy:
                    self.process.end_date = None
                if not self.process.chromatogram_copy:
                    self.process.chromatogram = None
                if not self.process.initial_concentration_copy:
                    self.process.initial_concentration = None
                if not self.process.comments_copy:
                    self.process.comments = None
                self.process.formula = None
                self.process.variables = None
            else:
                professional_id = (
                    LimsLaboratoryProfessional.get_lab_professional())
                self.process.professional = professional_id

            return 'process'
        return 'confirm'

    def transition_prev_(self):
        pool = Pool()
        LimsNotebookLoadResultsFormulaAction = pool.get(
            'lims.notebook.load_results_formula.action')
        LimsNotebookLoadResultsFormulaLine = pool.get(
            'lims.notebook.load_results_formula.line')

        self.result.index -= 1
        if self.result.index >= 1:
            line = LimsNotebookLoadResultsFormulaLine.search([
                ('session_id', '=', self._session_id),
                ('index', '=', self.result.index),
                ])
            self.process.line = line[0].line.id

            action = LimsNotebookLoadResultsFormulaAction.search([
                ('session_id', '=', self._session_id),
                ('line', '=', line[0].line.id),
                ])
            if action:
                self.process.result = action[0].result
                self.process.result_modifier = action[0].result_modifier
                self.process.end_date = action[0].end_date
                self.process.professional = action[0].professional.id
                self.process.chromatogram = action[0].chromatogram
                self.process.initial_concentration = (
                    action[0].initial_concentration)
                self.process.comments = action[0].comments
                self.process.formula = action[0].formula
                self.process.variables = [v.id for v in action[0].variables]
            else:
                self.process.result = None
                self.process.result_modifier = 'eq'
                self.process.end_date = None
                self.process.professional = None
                self.process.chromatogram = None
                self.process.initial_concentration = None
                self.process.comments = None
                self.process.formula = None
                self.process.variables = None

            return 'process'

        self.process.line = None
        return 'beginning'

    def default_process(self, fields):
        if not self.process.line:
            return {}

        default = {}
        default['line'] = self.process.line.id
        default['fraction'] = self.process.line.notebook.fraction.id
        default['repetition'] = self.process.line.repetition
        default['product_type'] = (
            self.process.line.notebook.product_type.id)
        default['matrix'] = self.process.line.notebook.matrix.id

        if (hasattr(self.process, 'formula')
                and getattr(self.process, 'formula')):
            formula = self.process.formula
            default['formula'] = formula.id
            variables = []
            variables_desc = {}
            for var in self.process.variables:
                variables.append({
                    'number': var.number,
                    'description': var.description,
                    'value': var.value,
                    })
                variables_desc[var.number] = var.description
            default['variables'] = variables
            formula_formula = formula.formula
            for k, v in variables_desc.iteritems():
                formula_formula = formula_formula.replace(k, v)
            default['formula_formula'] = formula_formula

            default['result'] = self.process.result
            default['result_modifier'] = self.process.result_modifier

            default['initial_concentration'] = (
                self.process.initial_concentration)
            default['comments'] = self.process.comments
            default['professional'] = self.process.professional.id
            default['end_date'] = self.process.end_date
            default['chromatogram'] = self.process.chromatogram

        else:
            formula = self.process.line.analysis.formula
            if formula:
                default['formula'] = formula.id
                variables = []
                variables_desc = {}
                for var in formula.variables:
                    variables.append({
                        'number': var.number,
                        'description': var.description,
                        'value': var.constant,
                        })
                    variables_desc[var.number] = var.description
                default['variables'] = variables
                formula_formula = formula.formula
                for k, v in variables_desc.iteritems():
                    formula_formula = formula_formula.replace(k, v)
                default['formula_formula'] = formula_formula
            default['result_modifier'] = 'eq'

            for field in ('initial_concentration', 'comments'):
                if (hasattr(self.process, field + '_copy')
                        and getattr(self.process, field + '_copy')):
                    default[field] = getattr(self.process, field)
                    default[field + '_copy'] = getattr(self.process,
                        field + '_copy')
                else:
                    default[field] = getattr(self.process.line, field)
            for field in ('professional',):
                if (hasattr(self.process, field)
                        and getattr(self.process, field)):
                    default[field] = getattr(self.process, field).id
            for field in ('end_date', 'chromatogram'):
                if (hasattr(self.process, field)
                        and getattr(self.process, field)):
                    default[field] = getattr(self.process, field)
            for field in ('end_date_copy', 'chromatogram_copy'):
                if (hasattr(self.process, field)
                        and getattr(self.process, field)):
                    default[field] = getattr(self.process, field)

        return default

    def transition_check_professional(self):
        pool = Pool()
        LimsNotebookLoadResultsFormulaAction = pool.get(
            'lims.notebook.load_results_formula.action')
        LimsLabProfessionalMethod = pool.get('lims.lab.professional.method')
        LimsLaboratoryProfessional = pool.get('lims.laboratory.professional')
        LimsLabMethod = pool.get('lims.lab.method')
        LimsNotebookLoadResultsFormulaSit2Detail = pool.get(
            'lims.notebook.load_results_formula.sit2.detail')

        actions = LimsNotebookLoadResultsFormulaAction.search([
            ('session_id', '=', self._session_id),
            ])

        situations = {}
        prof_lines = {}
        for data in actions:
            key = (data.professional.id, data.line.method.id)
            if key not in situations:
                situations[key] = 0
            if key not in prof_lines:
                prof_lines[key] = []
            prof_lines[key].append(data.line.id)

        situation_1 = []
        for key in situations.iterkeys():
            qualifications = LimsLabProfessionalMethod.search([
                ('professional', '=', key[0]),
                ('method', '=', key[1]),
                ('type', '=', 'analytical'),
                ])
            if not qualifications:
                situations[key] = 1
                situation_1.append(key)
            elif qualifications[0].state == 'training':
                situations[key] = 2
            elif (qualifications[0].state in ('qualified', 'requalified')):
                situations[key] = 3
        if situation_1:
            msg = ''
            for key in situation_1:
                professional = LimsLaboratoryProfessional(key[0])
                method = LimsLabMethod(key[1])
                msg += '%s: %s\n' % (professional.rec_name, method.code)
            self.sit1.msg = msg
            return 'sit1'

        situation_2 = []
        for key, sit in situations.iteritems():
            if sit == 2:
                situation_2.append({
                    'session_id': self._session_id,
                    'professional': key[0],
                    'method': key[1],
                    'lines': [('add', prof_lines[key])],
                    })
        if situation_2:
            details = LimsNotebookLoadResultsFormulaSit2Detail.create(
                situation_2)
            self.sit2.details = details
            return 'sit2'

        return 'confirm_'

    def default_sit1(self, fields):
        defaults = {}
        if self.sit1.msg:
            defaults['msg'] = self.sit1.msg
        return defaults

    def default_sit2(self, fields):
        defaults = {}
        if self.sit2.details:
            defaults['details'] = [d.id for d in self.sit2.details]
        return defaults

    def transition_sit2_ok(self):
        for detail in self.sit2.details:
            if not detail.supervisor:
                return 'sit2'
        return 'confirm_'

    def transition_confirm_(self):
        pool = Pool()
        LimsNotebookLoadResultsFormulaAction = pool.get(
            'lims.notebook.load_results_formula.action')
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsLabProfessionalMethod = pool.get('lims.lab.professional.method')
        LimsLabProfessionalMethodRequalification = pool.get(
            'lims.lab.professional.method.requalification')
        Date = pool.get('ir.date')

        # Write Results to Notebook lines
        actions = LimsNotebookLoadResultsFormulaAction.search([
            ('session_id', '=', self._session_id),
            ])
        for data in actions:
            notebook_line = LimsNotebookLine(data.line.id)
            if not notebook_line:
                continue
            notebook_line_write = {
                'result': data.result,
                'result_modifier': data.result_modifier,
                'end_date': data.end_date,
                'chromatogram': data.chromatogram,
                'initial_concentration': data.initial_concentration,
                'comments': data.comments,
                'converted_result': None,
                'converted_result_modifier': 'eq',
                'backup': None,
                'verification': None,
                'uncertainty': None,
                }
            if data.result_modifier == 'na':
                notebook_line_write['annulled'] = True
                notebook_line_write['annulment_date'] = datetime.now()
                notebook_line_write['report'] = False
            professionals = [{'professional': data.professional.id}]
            notebook_line_write['professionals'] = (
                [('delete', [p.id for p in notebook_line.professionals])]
                + [('create', professionals)])
            LimsNotebookLine.write([notebook_line], notebook_line_write)

        # Write Supervisors to Notebook lines
        supervisor_lines = {}
        if hasattr(self.sit2, 'details'):
            for detail in self.sit2.details:
                if detail.supervisor.id not in supervisor_lines:
                    supervisor_lines[detail.supervisor.id] = []
                supervisor_lines[detail.supervisor.id].extend([
                    l.id for l in detail.lines])
        for prof_id, lines in supervisor_lines.iteritems():
            notebook_lines = LimsNotebookLine.search([
                ('id', 'in', lines),
                ])
            if notebook_lines:
                professionals = [{'professional': prof_id}]
                notebook_line_write = {
                    'professionals': [('create', professionals)],
                    }
                LimsNotebookLine.write(notebook_lines, notebook_line_write)

        # Write the execution of method
        all_prof = {}
        for data in actions:
            key = (data.professional.id, data.line.method.id)
            if key not in all_prof:
                all_prof[key] = []
        if hasattr(self.sit2, 'details'):
            for detail in self.sit2.details:
                key = (detail.supervisor.id, detail.method.id)
                if key not in all_prof:
                    all_prof[key] = []
                key = (detail.professional.id, detail.method.id)
                if detail.supervisor.id not in all_prof[key]:
                    all_prof[key].append(detail.supervisor.id)

        today = Date.today()
        for key, sup in all_prof.iteritems():
            professional_method, = LimsLabProfessionalMethod.search([
                ('professional', '=', key[0]),
                ('method', '=', key[1]),
                ('type', '=', 'analytical'),
                ])
            if professional_method.state == 'training':
                history = LimsLabProfessionalMethodRequalification.search([
                    ('professional_method', '=', professional_method.id),
                    ('type', '=', 'training'),
                    ])
                if history:
                    prev_supervisors = [s.supervisor.id for s in
                        history[0].supervisors]
                    supervisors = [{'supervisor': s} for s in sup
                        if s not in prev_supervisors]
                    LimsLabProfessionalMethodRequalification.write(history, {
                        'last_execution_date': today,
                        'supervisors': [('create', supervisors)],
                        })
                else:
                    supervisors = [{'supervisor': s} for s in sup]
                    to_create = [{
                        'professional_method': professional_method.id,
                        'type': 'training',
                        'date': today,
                        'last_execution_date': today,
                        'supervisors': [('create', supervisors)],
                        }]
                    LimsLabProfessionalMethodRequalification.create(to_create)

            elif professional_method.state == 'qualified':
                history = LimsLabProfessionalMethodRequalification.search([
                    ('professional_method', '=', professional_method.id),
                    ('type', '=', 'qualification'),
                    ])
                if history:
                    LimsLabProfessionalMethodRequalification.write(history, {
                        'last_execution_date': today,
                        })
                else:
                    to_create = [{
                        'professional_method': professional_method.id,
                        'type': 'qualification',
                        'date': today,
                        'last_execution_date': today,
                        }]
                    LimsLabProfessionalMethodRequalification.create(to_create)

            else:
                history = LimsLabProfessionalMethodRequalification.search([
                    ('professional_method', '=', professional_method.id),
                    ('type', '=', 'requalification'),
                    ])
                if history:
                    LimsLabProfessionalMethodRequalification.write(history, {
                        'last_execution_date': today,
                        })
                else:
                    to_create = [{
                        'professional_method': professional_method.id,
                        'type': 'requalification',
                        'date': today,
                        'last_execution_date': today,
                        }]
                    LimsLabProfessionalMethodRequalification.create(to_create)

        return 'end'


class LimsNotebookLoadResultsManualStart(ModelView):
    'Load Results Manually'
    __name__ = 'lims.notebook.load_results_manual.start'

    method = fields.Many2One('lims.lab.method', 'Method', required=True)
    start_date = fields.Date('Start date', required=True)


class LimsNotebookLoadResultsManualEmpty(ModelView):
    'Load Results Manually'
    __name__ = 'lims.notebook.load_results_manual.empty'


class LimsNotebookLoadResultsManualResult(ModelView):
    'Load Results Manually'
    __name__ = 'lims.notebook.load_results_manual.result'

    method = fields.Many2One('lims.lab.method', 'Method', readonly=True)
    start_date = fields.Date('Start date', readonly=True)
    professional = fields.Many2One('lims.laboratory.professional',
        'Laboratory professional', required=True, readonly=True)
    lines = fields.One2Many('lims.notebook.load_results_manual.line',
        None, 'Lines')


class LimsNotebookLoadResultsManualLine(ModelSQL, ModelView):
    'Load Results Manually'
    __name__ = 'lims.notebook.load_results_manual.line'

    line = fields.Many2One('lims.notebook.line', 'Analysis', readonly=True)
    repetition = fields.Integer('Repetition', readonly=True)
    fraction = fields.Many2One('lims.fraction', 'Fraction', readonly=True)
    result = fields.Char('Result')
    result_modifier = fields.Selection([
        ('eq', '='),
        ('low', '<'),
        ('nd', 'nd'),
        ('na', 'na'),
        ('pos', 'Positive'),
        ('neg', 'Negative'),
        ('ni', 'ni'),
        ('abs', 'Absence'),
        ('pre', 'Presence'),
        ], 'Result modifier', sort=False)
    end_date = fields.Date('End date')
    chromatogram = fields.Char('Chromatogram')
    initial_unit = fields.Many2One('product.uom', 'Initial unit',
        domain=[('category.lims_only_available', '=', True)])
    comments = fields.Text('Comments')
    literal_result = fields.Char('Literal result')
    fraction_type = fields.Many2One('lims.fraction.type', 'Fraction type',
        readonly=True)
    session_id = fields.Integer('Session ID')

    @classmethod
    def __register__(cls, module_name):
        super(LimsNotebookLoadResultsManualLine,
            cls).__register__(module_name)
        cursor = Transaction().connection.cursor()
        cursor.execute('DELETE FROM "' + cls._table + '"')

    @fields.depends('result', 'literal_result', 'result_modifier', 'end_date')
    def on_change_with_end_date(self):
        pool = Pool()
        Date = pool.get('ir.date')
        if self.end_date:
            return self.end_date
        if (self.result or self.literal_result or
                self.result_modifier not in ('eq', 'low')):
            return Date.today()
        return None


class LimsNotebookLoadResultsManualSit1(ModelView):
    'Professionals Control'
    __name__ = 'lims.notebook.load_results_manual.sit1'

    msg = fields.Text('Message')


class LimsNotebookLoadResultsManualSit2(ModelView):
    'Professionals Control'
    __name__ = 'lims.notebook.load_results_manual.sit2'

    supervisor = fields.Many2One('lims.laboratory.professional',
        'Supervisor', depends=['supervisor_domain'],
        domain=[('id', 'in', Eval('supervisor_domain'))], required=True)
    supervisor_domain = fields.Many2Many('lims.laboratory.professional',
        None, None, 'Supervisor domain')
    lines = fields.Many2Many('lims.notebook.line', None, None, 'Lines')


class LimsNotebookLoadResultsManual(Wizard):
    'Load Results Manually'
    __name__ = 'lims.notebook.load_results_manual'

    start = StateView('lims.notebook.load_results_manual.start',
        'lims.lims_notebook_load_results_manual_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search', 'search', 'tryton-go-next', default=True),
            ])
    search = StateTransition()
    empty = StateView('lims.notebook.load_results_manual.empty',
        'lims.lims_notebook_load_results_manual_empty_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search again', 'start', 'tryton-go-next', default=True),
            ])
    result = StateView('lims.notebook.load_results_manual.result',
        'lims.lims_notebook_load_results_manual_result_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Confirm', 'check_professional', 'tryton-ok', default=True),
            ])
    check_professional = StateTransition()
    sit1 = StateView('lims.notebook.load_results_manual.sit1',
        'lims.lims_notebook_load_results_manual_sit1_view_form', [
            Button('Cancel', 'end', 'tryton-cancel', default=True),
            ])
    sit2 = StateView('lims.notebook.load_results_manual.sit2',
        'lims.lims_notebook_load_results_manual_sit2_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Confirm', 'confirm_', 'tryton-ok', default=True),
            ])
    confirm_ = StateTransition()

    def transition_search(self):
        pool = Pool()
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsLaboratoryProfessional = pool.get('lims.laboratory.professional')
        LimsNotebookLoadResultsManualLine = pool.get(
            'lims.notebook.load_results_manual.line')

        clause = [
            ('end_date', '=', None),
            ('method', '=', self.start.method.id),
            ('start_date', '=', self.start.start_date),
            ]

        lines = LimsNotebookLine.search(clause, order=[
            ('analysis_order', 'ASC'), ('id', 'ASC')])
        if lines:
            res_lines = []
            for line in lines:
                res_line, = LimsNotebookLoadResultsManualLine.create([{
                    'session_id': self._session_id,
                    'line': line.id,
                    'repetition': line.repetition,
                    'result': line.result,
                    'result_modifier': line.result_modifier,
                    'end_date': line.end_date,
                    'chromatogram': line.chromatogram,
                    'initial_unit': (line.initial_unit.id if
                        line.initial_unit else None),
                    'comments': line.comments,
                    'fraction': line.fraction.id,
                    'fraction_type': line.fraction_type.id,
                    'literal_result': line.literal_result,
                    }])
                res_lines.append(res_line.id)

            professional_id = LimsLaboratoryProfessional.get_lab_professional()
            self.result.method = self.start.method.id
            self.result.start_date = self.start.start_date
            self.result.professional = professional_id
            self.result.lines = res_lines
            if line.result_modifier == 'na':
                self.result.annulled = True
                self.result.annulment_date = datetime.now()
                self.result.report = False
            return 'result'
        return 'empty'

    def default_result(self, fields):
        default = {}
        default['method'] = self.result.method.id
        default['start_date'] = self.result.start_date
        default['professional'] = (self.result.professional.id
            if self.result.professional else None)
        default['lines'] = [l.id for l in self.result.lines]
        return default

    def transition_check_professional(self):
        pool = Pool()
        LimsNotebookLoadResultsManualLine = pool.get(
            'lims.notebook.load_results_manual.line')
        LimsLabProfessionalMethod = pool.get('lims.lab.professional.method')

        lines_to_save = []
        for line in self.result.lines:
            if line.line:  # Avoid empty lines created with ENTER key
                lines_to_save.append(line)
        LimsNotebookLoadResultsManualLine.save(lines_to_save)

        professional = self.result.professional
        method = self.result.method

        qualifications = LimsLabProfessionalMethod.search([
            ('professional', '=', professional.id),
            ('method', '=', method.id),
            ('type', '=', 'analytical'),
            ])
        if not qualifications:
            msg = '%s: %s' % (professional.rec_name, method.code)
            self.sit1.msg = msg
            return 'sit1'
        elif qualifications[0].state == 'training':
            situation_2_lines = [l.line.id for l in lines_to_save]
            supervisor_domain = []
            qualifications = LimsLabProfessionalMethod.search([
                ('method', '=', method.id),
                ('type', '=', 'analytical'),
                ('state', 'in', ('qualified', 'requalified')),
                ])
            if qualifications:
                supervisor_domain = [q.professional.id for q in qualifications]

            self.sit2.lines = situation_2_lines
            self.sit2.supervisor_domain = supervisor_domain
            return 'sit2'

        return 'confirm_'

    def default_sit1(self, fields):
        defaults = {}
        if self.sit1.msg:
            defaults['msg'] = self.sit1.msg
        return defaults

    def default_sit2(self, fields):
        defaults = {}
        if self.sit2.supervisor_domain:
            defaults['supervisor_domain'] = [p.id for p in
                self.sit2.supervisor_domain]
        if self.sit2.lines:
            defaults['lines'] = [l.id for l in self.sit2.lines]
        return defaults

    def transition_confirm_(self):
        pool = Pool()
        LimsNotebookLoadResultsManualLine = pool.get(
            'lims.notebook.load_results_manual.line')
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsLabProfessionalMethod = pool.get('lims.lab.professional.method')
        LimsLabProfessionalMethodRequalification = pool.get(
            'lims.lab.professional.method.requalification')
        Date = pool.get('ir.date')

        # Write Results to Notebook lines
        actions = LimsNotebookLoadResultsManualLine.search([
            ('session_id', '=', self._session_id),
            ])

        for data in actions:
            notebook_line = LimsNotebookLine(data.line.id)
            if not notebook_line:
                continue
            notebook_line_write = {
                'result': data.result,
                'result_modifier': data.result_modifier,
                'end_date': data.end_date,
                'chromatogram': data.chromatogram,
                'initial_unit': (data.initial_unit.id if
                    data.initial_unit else None),
                'comments': data.comments,
                'literal_result': data.literal_result,
                'converted_result': None,
                'converted_result_modifier': 'eq',
                'backup': None,
                'verification': None,
                'uncertainty': None,
                }
            if data.result_modifier == 'na':
                notebook_line_write['annulled'] = True
                notebook_line_write['annulment_date'] = datetime.now()
                notebook_line_write['report'] = False
            professionals = [{'professional': self.result.professional.id}]
            notebook_line_write['professionals'] = (
                [('delete', [p.id for p in notebook_line.professionals])]
                + [('create', professionals)])
            LimsNotebookLine.write([notebook_line], notebook_line_write)

        # Write Supervisors to Notebook lines
        supervisor_lines = {}
        if hasattr(self.sit2, 'supervisor'):
            supervisor_lines[self.sit2.supervisor.id] = [
                l.id for l in self.sit2.lines]
        for prof_id, lines in supervisor_lines.iteritems():
            notebook_lines = LimsNotebookLine.search([
                ('id', 'in', lines),
                ])
            if notebook_lines:
                professionals = [{'professional': prof_id}]
                notebook_line_write = {
                    'professionals': [('create', professionals)],
                    }
                LimsNotebookLine.write(notebook_lines, notebook_line_write)

        # Write the execution of method
        all_prof = {}
        key = (self.result.professional.id, self.result.method.id)
        all_prof[key] = []
        if hasattr(self.sit2, 'supervisor'):
            for detail in self.sit2.lines:
                key = (self.sit2.supervisor.id, detail.method.id)
                if key not in all_prof:
                    all_prof[key] = []
                key = (self.result.professional.id, detail.method.id)
                if self.sit2.supervisor.id not in all_prof[key]:
                    all_prof[key].append(self.sit2.supervisor.id)

        today = Date.today()
        for key, sup in all_prof.iteritems():
            professional_method, = LimsLabProfessionalMethod.search([
                ('professional', '=', key[0]),
                ('method', '=', key[1]),
                ('type', '=', 'analytical'),
                ])
            if professional_method.state == 'training':
                history = LimsLabProfessionalMethodRequalification.search([
                    ('professional_method', '=', professional_method.id),
                    ('type', '=', 'training'),
                    ])
                if history:
                    prev_supervisors = [s.supervisor.id for s in
                        history[0].supervisors]
                    supervisors = [{'supervisor': s} for s in sup
                        if s not in prev_supervisors]
                    LimsLabProfessionalMethodRequalification.write(history, {
                        'last_execution_date': today,
                        'supervisors': [('create', supervisors)],
                        })
                else:
                    supervisors = [{'supervisor': s} for s in sup]
                    to_create = [{
                        'professional_method': professional_method.id,
                        'type': 'training',
                        'date': today,
                        'last_execution_date': today,
                        'supervisors': [('create', supervisors)],
                        }]
                    LimsLabProfessionalMethodRequalification.create(to_create)

            elif professional_method.state == 'qualified':
                history = LimsLabProfessionalMethodRequalification.search([
                    ('professional_method', '=', professional_method.id),
                    ('type', '=', 'qualification'),
                    ])
                if history:
                    LimsLabProfessionalMethodRequalification.write(history, {
                        'last_execution_date': today,
                        })
                else:
                    to_create = [{
                        'professional_method': professional_method.id,
                        'type': 'qualification',
                        'date': today,
                        'last_execution_date': today,
                        }]
                    LimsLabProfessionalMethodRequalification.create(to_create)

            else:
                history = LimsLabProfessionalMethodRequalification.search([
                    ('professional_method', '=', professional_method.id),
                    ('type', '=', 'requalification'),
                    ])
                if history:
                    LimsLabProfessionalMethodRequalification.write(history, {
                        'last_execution_date': today,
                        })
                else:
                    to_create = [{
                        'professional_method': professional_method.id,
                        'type': 'requalification',
                        'date': today,
                        'last_execution_date': today,
                        }]
                    LimsLabProfessionalMethodRequalification.create(to_create)

        return 'end'


class LimsNotebookAddInternalRelationsStart(ModelView):
    'Add Internal Relations'
    __name__ = 'lims.notebook.add_internal_relations.start'

    analysis = fields.Many2Many('lims.analysis', None, None,
        'Internal relations', required=True,
        domain=[('id', 'in', Eval('analysis_domain'))],
        depends=['analysis_domain'])
    analysis_domain = fields.One2Many('lims.analysis', None,
        'Internal relations domain')


class LimsNotebookAddInternalRelations(Wizard):
    'Add Internal Relations'
    __name__ = 'lims.notebook.add_internal_relations'

    start = StateView('lims.notebook.add_internal_relations.start',
        'lims.lims_notebook_add_internal_relations_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Add', 'add', 'tryton-ok', default=True),
            ])
    add = StateTransition()

    def default_start(self, fields):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsNotebook = pool.get('lims.notebook')
        LimsAnalysis = pool.get('lims.analysis')
        LimsTypification = pool.get('lims.typification')

        notebook = LimsNotebook(Transaction().context['active_id'])
        default = {
            'analysis_domain': [],
            }
        if not notebook.lines:
            return default

        notebook_analysis = []
        for notebook_line in notebook.lines:
            notebook_analysis.append(notebook_line.analysis.code)
        notebook_analysis_codes = '\', \''.join(str(a) for a
            in notebook_analysis)

        cursor.execute('SELECT DISTINCT(a.id, a.result_formula) '
            'FROM "' + LimsAnalysis._table + '" a '
                'INNER JOIN "' + LimsTypification._table + '" t '
                'ON a.id = t.analysis '
            'WHERE t.product_type = %s '
                'AND t.matrix = %s '
                'AND t.valid '
                'AND a.behavior = \'internal_relation\' '
                'AND a.code NOT IN (\'' + notebook_analysis_codes + '\')',
            (notebook.fraction.product_type.id,
            notebook.fraction.matrix.id))
        internal_relations = cursor.fetchall()
        if not internal_relations:
            return default

        for internal_relation in internal_relations:
            formula = internal_relation[0].split(',')[1][:-1]
            if not formula:
                continue
            for i in (' ', '\t', '\n', '\r'):
                formula = formula.replace(i, '')
            variables = self._get_variables(formula)

            available = True
            if variables:
                for v in variables:
                    if v not in notebook_analysis:
                        available = False
                        break
            if available:
                ir_id = int(internal_relation[0].split(',')[0][1:])
                default['analysis_domain'].append(ir_id)

        return default

    def _get_variables(self, formula):
        variables = []
        for prefix in ('A', 'D', 'T', 'Y', 'R'):
            while True:
                idx = formula.find(prefix)
                if idx >= 0:
                    var = formula[idx:idx + 5]
                    formula = formula.replace(var, '_')
                    variables.append(var[1:])
                else:
                    break
        return variables

    def transition_add(self):
        LimsNotebook = Pool().get('lims.notebook')
        notebook = LimsNotebook(Transaction().context['active_id'])
        for analysis in self.start.analysis:
            self._create_service(analysis, notebook.fraction)
        return 'end'

    def _create_service(self, analysis, fraction):
        pool = Pool()
        LimsTypification = pool.get('lims.typification')
        LimsService = pool.get('lims.service')
        LimsEntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        divide, report_grouper = self._get_report_grouper(analysis)

        laboratory_id = (analysis.laboratories[0].laboratory.id if
            analysis.laboratories else None)
        typifications = LimsTypification.search([
            ('product_type', '=', fraction.product_type.id),
            ('matrix', '=', fraction.matrix.id),
            ('analysis', '=', analysis.id),
            ('by_default', '=', True),
            ('valid', '=', True),
            ])
        method_id = (typifications[0].method.id if typifications
            else None)

        service_create = [{
            'fraction': fraction.id,
            'analysis': analysis.id,
            'laboratory': laboratory_id,
            'method': method_id,
            'device': None,
            'divide': divide,
            }]
        new_service, = LimsService.create(service_create)
        analysis_detail = list(new_service.analysis_detail)
        if report_grouper != 0:
            LimsEntryDetailAnalysis.write(analysis_detail, {
                'report_grouper': report_grouper,
                })

        LimsEntryDetailAnalysis.create_notebook_lines(analysis_detail,
            fraction)
        LimsEntryDetailAnalysis.write(analysis_detail, {
            'state': 'unplanned',
            })

    def _get_report_grouper(self, analysis):
        pool = Pool()
        LimsNotebook = pool.get('lims.notebook')

        divide = False
        report_grouper = 0

        notebook = LimsNotebook(Transaction().context['active_id'])
        notebook_analysis = {}
        for notebook_line in notebook.lines:
            notebook_analysis[notebook_line.analysis.code] = notebook_line

        formula = analysis.result_formula
        for i in (' ', '\t', '\n', '\r'):
            formula = formula.replace(i, '')
        variables = self._get_variables(formula)
        for v in variables:
            if v in notebook_analysis:
                divide = notebook_analysis[v].service.divide
                report_grouper = (
                    notebook_analysis[v].analysis_detail.report_grouper)
                break
        return divide, report_grouper


class LimsNotebookLineRepeatAnalysisStart(ModelView):
    'Repeat Analysis'
    __name__ = 'lims.notebook.line.repeat_analysis.start'

    analysis = fields.Many2One('lims.analysis', 'Analysis', required=True,
        domain=[('id', 'in', Eval('analysis_domain'))],
        depends=['analysis_domain'])
    analysis_domain = fields.One2Many('lims.analysis', None,
        'Analysis domain')


class LimsNotebookLineRepeatAnalysis(Wizard):
    'Repeat Analysis'
    __name__ = 'lims.notebook.line.repeat_analysis'

    start = StateView('lims.notebook.line.repeat_analysis.start',
        'lims.lims_notebook_line_repeat_analysis_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Repeat', 'repeat', 'tryton-ok', default=True),
            ])
    repeat = StateTransition()

    def default_start(self, fields):
        pool = Pool()
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsAnalysis = pool.get('lims.analysis')

        notebook_line = LimsNotebookLine(Transaction().context['active_id'])

        analysis_origin = notebook_line.analysis_origin
        analysis_origin_list = analysis_origin.split(' > ')

        analysis_code = notebook_line.analysis.code
        analysis_origin_list.append(analysis_code)

        analysis = LimsAnalysis.search([
            ('code', 'in', analysis_origin_list),
            ('behavior', '=', 'normal'),
            ])
        notebook_analysis = [a.id for a in analysis]
        default = {
            'analysis_domain': notebook_analysis,
            }
        if len(notebook_analysis) == 1:
            default['analysis'] = notebook_analysis[0]
        return default

    def transition_repeat(self):
        pool = Pool()
        LimsAnalysis = pool.get('lims.analysis')
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsNotebook = pool.get('lims.notebook')
        LimsEntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        Config = pool.get('lims.configuration')

        analysis = self.start.analysis
        if analysis.type == 'analysis':
            analysis_to_repeat = [analysis.id]
        else:
            analysis_to_repeat = LimsAnalysis.get_included_analysis_analysis(
                analysis.id)

        notebook_line = LimsNotebookLine(Transaction().context['active_id'])
        notebook = LimsNotebook(notebook_line.notebook.id)

        rm_type = (notebook.fraction.special_type == 'rm')
        if rm_type:
            config = Config(1)
            rm_start_uom = (config.rm_start_uom.id if config.rm_start_uom
                else None)

        to_create = []
        details_to_update = []
        for analysis_id in analysis_to_repeat:
            nlines = LimsNotebookLine.search([
                ('notebook', '=', notebook.id),
                ('analysis', '=', analysis_id),
                ('analysis.behavior', '=', 'normal'),
                ])
            if not nlines:
                continue
            nline_to_repeat = nlines[0]
            for nline in nlines:
                if nline.repetition > nline_to_repeat.repetition:
                    nline_to_repeat = nline

            detail_id = nline_to_repeat.analysis_detail.id
            defaults = {
                'analysis_detail': detail_id,
                'service': nline_to_repeat.service.id,
                'analysis': analysis_id,
                'analysis_origin': nline_to_repeat.analysis_origin,
                'repetition': nline_to_repeat.repetition + 1,
                'laboratory': nline_to_repeat.laboratory.id,
                'method': nline_to_repeat.method.id,
                'device': (nline_to_repeat.device.id if nline_to_repeat.device
                    else None),
                'initial_concentration': nline_to_repeat.initial_concentration,
                'decimals': nline_to_repeat.decimals,
                'report': nline_to_repeat.report,
                'concentration_level': (nline_to_repeat.concentration_level.id
                    if nline_to_repeat.concentration_level else None),
                'results_estimated_waiting': (
                    nline_to_repeat.results_estimated_waiting),
                'department': nline_to_repeat.department,
                }
            if rm_type:
                defaults['final_concentration'] = None
                defaults['initial_unit'] = rm_start_uom
                defaults['final_unit'] = None
                defaults['detection_limit'] = None
                defaults['quantification_limit'] = None
            else:
                defaults['final_concentration'] = (
                    nline_to_repeat.final_concentration)
                defaults['initial_unit'] = (nline_to_repeat.initial_unit.id if
                    nline_to_repeat.initial_unit else None)
                defaults['final_unit'] = (nline_to_repeat.final_unit.id if
                    nline_to_repeat.final_unit else None)
                defaults['detection_limit'] = nline_to_repeat.detection_limit
                defaults['quantification_limit'] = (
                    nline_to_repeat.quantification_limit)
            to_create.append(defaults)
            details_to_update.append(detail_id)

        LimsNotebook.write([notebook], {
            'lines': [('create', to_create)],
            })

        details = LimsEntryDetailAnalysis.search([
            ('id', 'in', details_to_update),
            ])
        if details:
            LimsEntryDetailAnalysis.write(details, {
                'state': 'unplanned',
                })

        return 'end'


class LimsNotebookAcceptLinesStart(ModelView):
    'Accept Lines'
    __name__ = 'lims.notebook.accept_lines.start'


class LimsNotebookAcceptLines(Wizard):
    'Accept Lines'
    __name__ = 'lims.notebook.accept_lines'

    start_state = 'ok'
    start = StateView('lims.notebook.accept_lines.start',
        'lims.lims_notebook_accept_lines_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Ok', 'ok', 'tryton-ok', default=True),
            ])
    ok = StateTransition()

    def transition_ok(self):
        pool = Pool()
        LimsNotebook = pool.get('lims.notebook')
        LimsNotebookLine = pool.get('lims.notebook.line')

        for active_id in Transaction().context['active_ids']:
            notebook = LimsNotebook(active_id)
            if not notebook.lines:
                continue

            repeated_analysis = []
            repetitions = LimsNotebookLine.search([
                ('notebook', '=', notebook.id),
                ('repetition', '>', 0),
                ])
            if repetitions:
                repeated_analysis = [l.analysis.id for l in repetitions]
            notebook_lines = [l for l in notebook.lines
                if l.analysis.id not in repeated_analysis]

            self.lines_accept(notebook_lines)
        return 'end'

    def lines_accept(self, notebook_lines):
        LimsNotebookLine = Pool().get('lims.notebook.line')

        accepted_analysis = {}
        lines_to_write = []
        for notebook_line in notebook_lines:
            if notebook_line.accepted:
                continue
            if not notebook_line.report:
                continue
            if notebook_line.annulled:
                continue
            if not notebook_line.end_date:
                continue
            if not (notebook_line.result or notebook_line.converted_result
                    or notebook_line.literal_result
                    or notebook_line.result_modifier in
                    ('nd', 'pos', 'neg', 'ni', 'abs', 'pre')
                    or notebook_line.converted_result_modifier in
                    ('nd', 'pos', 'neg', 'ni', 'abs', 'pre')):
                continue
            if (notebook_line.converted_result and
                    notebook_line.converted_result_modifier
                    not in ('ni', 'eq', 'low')):
                continue
            if (notebook_line.result and notebook_line.result_modifier
                    not in ('ni', 'eq', 'low')):
                continue

            notebook_id = notebook_line.notebook.id
            if notebook_id not in accepted_analysis:
                accepted_lines = LimsNotebookLine.search([
                    ('notebook', '=', notebook_id),
                    ('accepted', '=', True),
                    ])
                accepted_analysis[notebook_id] = [l.analysis.id
                    for l in accepted_lines]
            if notebook_line.analysis.id in accepted_analysis[notebook_id]:
                continue

            accepted_analysis[notebook_id].append(notebook_line.analysis.id)
            lines_to_write.append(notebook_line)

        if lines_to_write:
            acceptance_date = datetime.now()
            LimsNotebookLine.write(lines_to_write, {
                'accepted': True,
                'acceptance_date': acceptance_date,
                })


class LimsNotebookLineAcceptLines(LimsNotebookAcceptLines):
    'Accept Lines'
    __name__ = 'lims.notebook_line.accept_lines'

    def transition_ok(self):
        LimsNotebookLine = Pool().get('lims.notebook.line')

        notebook_lines = LimsNotebookLine.browse(
            Transaction().context['active_ids'])
        if not notebook_lines:
            return 'end'

        self.lines_accept(notebook_lines)
        return 'end'


class LimsNotebookLineUnacceptLines(Wizard):
    'Unaccept Lines'
    __name__ = 'lims.notebook_line.unaccept_lines'

    start_state = 'ok'
    ok = StateTransition()

    def transition_ok(self):
        LimsNotebookLine = Pool().get('lims.notebook.line')

        notebook_lines = LimsNotebookLine.browse(
            Transaction().context['active_ids'])
        if not notebook_lines:
            return 'end'

        self.lines_unaccept(notebook_lines)
        return 'end'

    def lines_unaccept(self, notebook_lines):
        pool = Pool()
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsResultsReportVersionDetailLine = pool.get(
            'lims.results_report.version.detail.line')

        lines_to_write = []
        for notebook_line in notebook_lines:
            if not notebook_line.accepted:
                continue
            report_lines = LimsResultsReportVersionDetailLine.search([
                ('notebook_line', '=', notebook_line.id),
                ('report_version_detail.state', '!=', 'annulled'),
                ])
            if report_lines:
                continue

            lines_to_write.append(notebook_line)

        if lines_to_write:
            LimsNotebookLine.write(lines_to_write, {
                'accepted': False,
                'acceptance_date': None,
                })


class FractionsByLocationsStart(ModelView):
    'Fractions by Locations'
    __name__ = 'lims.fractions_by_locations.start'

    location = fields.Many2One('stock.location', 'Location',
        required=True)

    @classmethod
    def default_location(cls):
        Location = Pool().get('stock.location')
        locations = Location.search([('type', '=', 'warehouse')])
        if len(locations) == 1:
            return locations[0].id


class FractionsByLocations(Wizard):
    'Fractions by Locations'
    __name__ = 'lims.fractions_by_locations'

    start = StateView('lims.fractions_by_locations.start',
        'lims.fractions_by_locations_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Open', 'open', 'tryton-ok', True),
            ])
    open = StateAction('lims.act_lims_fractions_by_locations')

    def do_open(self, action):
        Location = Pool().get('stock.location')

        childs = Location.search([
            ('parent', 'child_of', [self.start.location.id]),
            ])
        locations = [l.id for l in childs]
        action['pyson_domain'] = PYSONEncoder().encode([
            ('current_location', 'in', locations),
            ])
        action['name'] += ' (%s)' % self.start.location.rec_name
        return action, {}


class LimsNotebookResultsVerificationStart(ModelView):
    'Results Verification'
    __name__ = 'lims.notebook.results_verification.start'

    range_type = fields.Many2One('lims.range.type', 'Origin', required=True,
        domain=[('use', '=', 'results_verification')])


class LimsNotebookResultsVerification(Wizard):
    'Results Verification'
    __name__ = 'lims.notebook.results_verification'

    start = StateView('lims.notebook.results_verification.start',
        'lims.lims_notebook_results_verification_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Ok', 'ok', 'tryton-ok', default=True),
            ])
    ok = StateTransition()

    @classmethod
    def __setup__(cls):
        super(LimsNotebookResultsVerification, cls).__setup__()
        cls._error_messages.update({
            'ok': 'OK',
            'ok*': 'OK*',
            'out': 'Out of Range',
            })

    def default_start(self, fields):
        LimsRangeType = Pool().get('lims.range.type')

        default = {}
        default_range_type = LimsRangeType.search([
            ('use', '=', 'results_verification'),
            ('by_default', '=', True),
            ])
        if default_range_type:
            default['range_type'] = default_range_type[0].id
        return default

    def transition_ok(self):
        LimsNotebook = Pool().get('lims.notebook')

        for active_id in Transaction().context['active_ids']:
            notebook = LimsNotebook(active_id)
            if not notebook.lines:
                continue
            self.lines_results_verification(notebook.lines)
        return 'end'

    def lines_results_verification(self, notebook_lines):
        pool = Pool()
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsRange = pool.get('lims.range')
        LimsUomConversion = pool.get('lims.uom.conversion')
        LimsVolumeConversion = pool.get('lims.volume.conversion')

        verifications = self._get_verifications()

        lines_to_save = []
        for notebook_line in notebook_lines:
            if notebook_line.accepted:
                continue
# Se comentan segun mantis 1095
#           iu = notebook_line.final_unit
#           if not iu:
#               continue
#           try:
#               ic = float(notebook_line.final_concentration)
#           except (TypeError, ValueError):
#               continue

            result = notebook_line.converted_result
            if not result:
                result = notebook_line.result
                iu = notebook_line.initial_unit
                if not iu:
                    continue
                try:
                    ic = float(notebook_line.initial_concentration)
                except (TypeError, ValueError):
                    continue
            else:
                iu = notebook_line.final_unit
                if not iu:
                    continue
                try:
                    ic = float(notebook_line.final_concentration)
                except (TypeError, ValueError):
                    continue

            try:
                result = float(result)
            except (TypeError, ValueError):
                continue

            ranges = LimsRange.search([
                ('range_type', '=', self.start.range_type),
                ('analysis', '=', notebook_line.analysis.id),
                ('product_type', '=', notebook_line.notebook.product_type.id),
                ('matrix', '=', notebook_line.notebook.matrix.id),
                ])
            if not ranges:
                continue
            fu = ranges[0].uom
            try:
                fc = float(ranges[0].concentration)
            except (TypeError, ValueError):
                continue

            if fu and fu.rec_name != '-':
                converted_result = None
                if (iu == fu and ic == fc):
                    converted_result = result
                elif (iu != fu and ic == fc):
                    formula = LimsUomConversion.get_conversion_formula(iu,
                        fu)
                    if not formula:
                        continue
                    variables = self._get_variables(formula, notebook_line)
                    parser = FormulaParser(formula, variables)
                    formula_result = parser.getValue()

                    converted_result = result * formula_result
                elif (iu == fu and ic != fc):
                    converted_result = result * (fc / ic)
                else:
                    formula = None
                    conversions = LimsUomConversion.search([
                        ('initial_uom', '=', iu),
                        ('final_uom', '=', fu),
                        ])
                    if conversions:
                        formula = conversions[0].conversion_formula
                    if not formula:
                        continue
                    variables = self._get_variables(formula, notebook_line)
                    parser = FormulaParser(formula, variables)
                    formula_result = parser.getValue()

                    if (conversions[0].initial_uom_volume
                            and conversions[0].final_uom_volume):
                        d_ic = LimsVolumeConversion.brixToDensity(ic)
                        d_fc = LimsVolumeConversion.brixToDensity(fc)
                        converted_result = (result * (fc / ic) *
                            (d_fc / d_ic) * formula_result)
                    else:
                        converted_result = (result * (fc / ic) *
                            formula_result)
                result = float(converted_result)

            verification = self._verificate_result(result, ranges[0])
            notebook_line.verification = verifications.get(verification)
            lines_to_save.append(notebook_line)
        if lines_to_save:
            LimsNotebookLine.save(lines_to_save)

    def _get_variables(self, formula, notebook_line):
        LimsVolumeConversion = Pool().get('lims.volume.conversion')

        variables = {}
        for var in ('DI',):
            while True:
                idx = formula.find(var)
                if idx >= 0:
                    variables[var] = 0
                    formula = formula.replace(var, '_')
                else:
                    break
        for var in variables.iterkeys():
            if var == 'DI':
                ic = float(notebook_line.final_concentration)
                result = LimsVolumeConversion.brixToDensity(ic)
                if result:
                    variables[var] = result
        return variables

    def _verificate_result(self, result, range_):
        if range_.min95 and range_.max95:
            if result < range_.min:
                return 'out'
            elif result < range_.min95:
                return 'ok*'
            elif result <= range_.max95:
                return 'ok'
            elif result <= range_.max:
                return 'ok*'
            else:
                return 'out'
        else:
            if result < range_.min:
                return 'out'
            elif result <= range_.max:
                return 'ok'
            else:
                return 'out'

    def _get_verifications(self):
        pool = Pool()
        User = pool.get('res.user')
        Lang = pool.get('ir.lang')

        lang = User(Transaction().user).language
        if not lang:
            lang, = Lang.search([
                    ('code', '=', 'en'),
                    ], limit=1)

        verifications = {}
        with Transaction().set_context(language=lang.code):
            verifications['ok'] = self.raise_user_error('ok',
                raise_exception=False)
            verifications['ok*'] = self.raise_user_error('ok*',
                raise_exception=False)
            verifications['out'] = self.raise_user_error('out',
                raise_exception=False)

        return verifications


class LimsNotebookLineResultsVerification(LimsNotebookResultsVerification):
    'Results Verification'
    __name__ = 'lims.notebook_line.results_verification'

    def transition_ok(self):
        LimsNotebookLine = Pool().get('lims.notebook.line')

        notebook_lines = LimsNotebookLine.browse(
            Transaction().context['active_ids'])
        if not notebook_lines:
            return 'end'

        self.lines_results_verification(notebook_lines)
        return 'end'


class LimsUncertaintyCalcStart(ModelView):
    'Uncertainty Calculation'
    __name__ = 'lims.notebook.uncertainty_calc.start'

    range_type = fields.Many2One('lims.range.type', 'Origin', required=True,
        domain=[('use', '=', 'uncertainty_calc')])


class LimsUncertaintyCalc(Wizard):
    'Uncertainty Calculation'
    __name__ = 'lims.notebook.uncertainty_calc'

    start_state = 'check'
    check = StateTransition()
    start = StateView('lims.notebook.uncertainty_calc.start',
        'lims.lims_notebook_uncertainty_calc_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Ok', 'ok', 'tryton-ok', default=True),
            ])
    ok = StateTransition()

    def transition_check(self):
        LimsRangeType = Pool().get('lims.range.type')

        default_range_type = LimsRangeType.search([
            ('use', '=', 'uncertainty_calc'),
            ('by_default', '=', True),
            ])
        if default_range_type:
            self.start.range_type = default_range_type[0].id
            return 'ok'
        return 'start'

    def default_start(self, fields):
        LimsRangeType = Pool().get('lims.range.type')

        default = {}
        default_range_type = LimsRangeType.search([
            ('use', '=', 'uncertainty_calc'),
            ('by_default', '=', True),
            ])
        if default_range_type:
            default['range_type'] = default_range_type[0].id
        return default

    def transition_ok(self):
        LimsNotebook = Pool().get('lims.notebook')

        for active_id in Transaction().context['active_ids']:
            notebook = LimsNotebook(active_id)
            if not notebook.lines:
                continue
            self.lines_uncertainty_calc(notebook.lines)
        return 'end'

    def lines_uncertainty_calc(self, notebook_lines):
        pool = Pool()
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsRange = pool.get('lims.range')

        lines_to_save = []
        for notebook_line in notebook_lines:
            if notebook_line.accepted:
                continue
            result = notebook_line.converted_result
            if not result:
                result = notebook_line.result
            try:
                result = float(result)
            except (TypeError, ValueError):
                continue

            ranges = LimsRange.search([
                ('range_type', '=', self.start.range_type),
                ('analysis', '=', notebook_line.analysis.id),
                ('product_type', '=', notebook_line.notebook.product_type.id),
                ('matrix', '=', notebook_line.notebook.matrix.id),
                ])
            if not ranges:
                continue

            uncertainty = self._get_uncertainty(result, notebook_line,
                ranges[0])
            if uncertainty is None:
                continue
            notebook_line.uncertainty = str(uncertainty)
            lines_to_save.append(notebook_line)
        if lines_to_save:
            LimsNotebookLine.save(lines_to_save)

    def _get_uncertainty(self, result, notebook_line, range_):
        dilution_factor = notebook_line.dilution_factor
        if not dilution_factor or dilution_factor == 0.0:
            dilution_factor = 1.0
        diluted_result = result / dilution_factor
        try:
            factor = range_.factor or 1.0
            low_level = range_.low_level or 0.0 * factor
            middle_level = range_.middle_level or 0.0 * factor
            high_level = range_.high_level or 0.0 * factor
        except TypeError:
            return None

        uncertainty = 0.0
        if (range_.low_level_value and
                not (range_.middle_level_value and range_.high_level_value)
                and (diluted_result > low_level)):
            uncertainty = range_.low_level_value
        elif (range_.low_level_value and range_.middle_level_value
                and range_.high_level_value):
            if (low_level <= diluted_result
                    and diluted_result < middle_level):
                uncertainty = range_.low_level_value
            elif (middle_level <= diluted_result
                    and diluted_result < high_level):
                uncertainty = range_.middle_level_value
            elif diluted_result >= high_level:
                uncertainty = range_.high_level_value
        if (range_.low_level_value and range_.middle_level_value
                and not range_.high_level_value):
            if (low_level <= diluted_result
                    and diluted_result < middle_level):
                uncertainty = range_.low_level_value
            elif (middle_level <= diluted_result
                    and diluted_result < high_level):
                uncertainty = range_.middle_level_value

        if uncertainty > 0.0:
            uncertainty = result * uncertainty / 100

        return uncertainty


class LimsNotebookLineUncertaintyCalc(LimsUncertaintyCalc):
    'Uncertainty Calculation'
    __name__ = 'lims.notebook_line.uncertainty_calc'

    def transition_ok(self):
        LimsNotebookLine = Pool().get('lims.notebook.line')

        notebook_lines = LimsNotebookLine.browse(
            Transaction().context['active_ids'])
        if not notebook_lines:
            return 'end'

        self.lines_uncertainty_calc(notebook_lines)
        return 'end'


class LimsNotebookPrecisionControlStart(ModelView):
    'Precision Control'
    __name__ = 'lims.notebook.precision_control.start'

    range_type = fields.Many2One('lims.range.type', 'Origin', required=True,
        domain=[('use', '=', 'repeatability_calc')])
    product_type = fields.Many2One('lims.product.type', 'Product type',
        required=True)
    matrix = fields.Many2One('lims.matrix', 'Matrix', required=True,
        domain=[
            ('id', 'in', Eval('matrix_domain')),
            ], depends=['matrix_domain'])
    matrix_domain = fields.Function(fields.Many2Many('lims.matrix',
        None, None, 'Matrix domain'),
        'on_change_with_matrix_domain')
    factor = fields.Float('Factor', required=True)

    @fields.depends('product_type')
    def on_change_with_matrix_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        LimsTypification = Pool().get('lims.typification')

        if not self.product_type:
            return []

        cursor.execute('SELECT DISTINCT(matrix) '
            'FROM "' + LimsTypification._table + '" '
            'WHERE product_type = %s '
            'AND valid',
            (self.product_type.id,))
        res = cursor.fetchall()
        if not res:
            return []
        return [x[0] for x in res]


class LimsNotebookPrecisionControl(Wizard):
    'Precision Control'
    __name__ = 'lims.notebook.precision_control'

    start_state = 'check'
    check = StateTransition()
    start = StateView('lims.notebook.precision_control.start',
        'lims.lims_notebook_precision_control_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Ok', 'ok', 'tryton-ok', default=True),
            ])
    ok = StateTransition()

    @classmethod
    def __setup__(cls):
        super(LimsNotebookPrecisionControl, cls).__setup__()
        cls._error_messages.update({
            'acceptable': 'Acceptable / Factor: %s - CV: %s',
            'unacceptable': 'Unacceptable / Factor: %s - CV: %s',
            })

    def transition_check(self):
        LimsNotebook = Pool().get('lims.notebook')

        notebook = LimsNotebook(Transaction().context['active_id'])
        if notebook.fraction.special_type in ('rm', 'con'):
            return 'start'
        return 'end'

    def default_start(self, fields):
        pool = Pool()
        LimsNotebook = pool.get('lims.notebook')
        LimsRangeType = pool.get('lims.range.type')

        notebook = LimsNotebook(Transaction().context['active_id'])
        default = {
            'product_type': notebook.product_type.id,
            'matrix': notebook.matrix.id,
            'factor': 2,
            }
        default_range_type = LimsRangeType.search([
            ('use', '=', 'repeatability_calc'),
            ('by_default', '=', True),
            ])
        if default_range_type:
            default['range_type'] = default_range_type[0].id
        return default

    def transition_ok(self):
        LimsNotebook = Pool().get('lims.notebook')

        notebook = LimsNotebook(Transaction().context['active_id'])
        if not notebook.lines:
            return 'end'

        self.lines_precision_control(notebook.lines)
        return 'end'

    def lines_precision_control(self, notebook_lines):
        pool = Pool()
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsRange = pool.get('lims.range')

        lines_to_save = []
        for notebook_line in notebook_lines:
            if notebook_line.verification:
                continue
            concentration_level = notebook_line.concentration_level
            if not concentration_level:
                continue

            ranges = LimsRange.search([
                ('range_type', '=', self.start.range_type.id),
                ('analysis', '=', notebook_line.analysis.id),
                ('product_type', '=', self.start.product_type.id),
                ('matrix', '=', self.start.matrix.id),
                ])
            if not ranges:
                continue

            if concentration_level.code == 'NC':
                cv = ranges[0].low_level_coefficient_variation
            elif concentration_level.code == 'NM':
                cv = ranges[0].middle_level_coefficient_variation
            elif concentration_level.code == 'NA':
                cv = ranges[0].high_level_coefficient_variation
            else:
                continue
            if not cv:
                continue

            try:
                if notebook_line.repetition == 0:
                    rep_0 = float(notebook_line.result)
                    rep_1 = float(self._get_repetition_result(notebook_line,
                        1))
                elif notebook_line.repetition == 1:
                    rep_0 = float(self._get_repetition_result(notebook_line,
                        0))
                    rep_1 = float(notebook_line.result)
                else:
                    continue
            except (TypeError, ValueError):
                continue

            if not rep_0 or not rep_1:
                continue

            average = (rep_0 + rep_1) / 2
            error = abs(rep_0 - rep_1) / average * 100

            if error < (cv * self.start.factor):
                res = self.raise_user_error('acceptable', (
                    self.start.factor, cv), raise_exception=False)
            else:
                res = self.raise_user_error('unacceptable', (
                    self.start.factor, cv), raise_exception=False)
            notebook_line.verification = res
            lines_to_save.append(notebook_line)
        if lines_to_save:
            LimsNotebookLine.save(lines_to_save)

    def _get_repetition_result(self, notebook_line, repetition):
        LimsNotebookLine = Pool().get('lims.notebook.line')

        repetition = LimsNotebookLine.search([
            ('notebook', '=', notebook_line.notebook.id),
            ('analysis', '=', notebook_line.analysis.id),
            ('repetition', '=', repetition),
            ])
        if not repetition:
            return None
        return repetition[0].result


class LimsNotebookLinePrecisionControl(LimsNotebookPrecisionControl):
    'Precision Control'
    __name__ = 'lims.notebook_line.precision_control'

    def transition_check(self):
        LimsNotebookLine = Pool().get('lims.notebook.line')

        reference_line = LimsNotebookLine(Transaction().context['active_id'])
        if reference_line.notebook.fraction.special_type in ('rm', 'con'):
            return 'start'
        return 'end'

    def default_start(self, fields):
        LimsNotebookLine = Pool().get('lims.notebook.line')

        reference_line = LimsNotebookLine(Transaction().context['active_id'])
        with Transaction().set_context(active_id=reference_line.notebook.id):
            return super(LimsNotebookLinePrecisionControl,
                self).default_start(fields)

    def transition_ok(self):
        LimsNotebookLine = Pool().get('lims.notebook.line')

        reference_line = LimsNotebookLine(Transaction().context['active_id'])

        notebook_lines = LimsNotebookLine.browse(
            Transaction().context['active_ids'])
        notebook_lines = [l for l in notebook_lines
            if l.notebook.id == reference_line.notebook.id]
        if not notebook_lines:
            return 'end'

        self.lines_precision_control(notebook_lines)
        return 'end'


class LimsMeansDeviationsCalcStart(ModelView):
    'Calculation of Means and Deviations'
    __name__ = 'lims.control.means_deviations_calc.start'

    date_from = fields.Date('Date from', required=True)
    date_to = fields.Date('Date to', required=True)
    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        required=True)
    family = fields.Many2One('lims.analysis.family', 'Family')
    product_type = fields.Many2One('lims.product.type', 'Product type',
        domain=[('id', 'in', Eval('product_type_domain'))],
        depends=['product_type_domain'])
    product_type_domain = fields.Function(fields.Many2Many(
        'lims.product.type', None, None, 'Product type domain'),
        'on_change_with_product_type_domain')
    matrix = fields.Many2One('lims.matrix', 'Matrix',
        domain=[('id', 'in', Eval('matrix_domain'))],
        depends=['matrix_domain'])
    matrix_domain = fields.Function(fields.Many2Many('lims.matrix',
        None, None, 'Matrix domain'), 'on_change_with_matrix_domain')
    fraction_type = fields.Many2One('lims.fraction.type', 'Fraction type',
        domain=[('control_charts', '=', True)], required=True)

    @staticmethod
    def default_product_type_domain():
        cursor = Transaction().connection.cursor()
        LimsTypification = Pool().get('lims.typification')

        cursor.execute('SELECT DISTINCT(product_type) '
            'FROM "' + LimsTypification._table + '" '
            'WHERE valid')
        return [x[0] for x in cursor.fetchall()]

    @fields.depends('family')
    def on_change_with_product_type_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        LimsAnalysisFamilyCertificant = Pool().get(
            'lims.analysis.family.certificant')

        if not self.family:
            return self.default_product_type_domain()

        cursor.execute('SELECT DISTINCT(product_type) '
            'FROM "' + LimsAnalysisFamilyCertificant._table + '" '
            'WHERE family = %s',
            (self.family.id,))
        return [x[0] for x in cursor.fetchall()]

    @fields.depends('product_type', 'family')
    def on_change_with_matrix_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsAnalysisFamilyCertificant = pool.get(
            'lims.analysis.family.certificant')
        LimsTypification = pool.get('lims.typification')

        if not self.product_type:
            return []

        if not self.family:
            cursor.execute('SELECT DISTINCT(matrix) '
                'FROM "' + LimsTypification._table + '" '
                'WHERE product_type = %s '
                'AND valid',
                (self.product_type.id,))
            return [x[0] for x in cursor.fetchall()]
        else:
            cursor.execute('SELECT DISTINCT(matrix) '
                'FROM "' + LimsAnalysisFamilyCertificant._table + '" '
                'WHERE product_type = %s '
                'AND family = %s',
                (self.product_type.id, self.family.id))
            return [x[0] for x in cursor.fetchall()]


class LimsMeansDeviationsCalcEmpty(ModelView):
    'Calculation of Means and Deviations'
    __name__ = 'lims.control.means_deviations_calc.empty'


class LimsMeansDeviationsCalcResult(ModelView):
    'Calculation of Means and Deviations'
    __name__ = 'lims.control.means_deviations_calc.result'

    lines = fields.One2Many('lims.control.result_line', None, 'Results')


class LimsControlResultLine(ModelSQL, ModelView):
    'Control Chart Result Line'
    __name__ = 'lims.control.result_line'

    product_type = fields.Many2One('lims.product.type', 'Product type',
        readonly=True)
    matrix = fields.Many2One('lims.matrix', 'Matrix', readonly=True)
    fraction_type = fields.Many2One('lims.fraction.type', 'Fraction type',
        readonly=True)
    analysis = fields.Many2One('lims.analysis', 'Analysis', readonly=True)
    concentration_level = fields.Many2One('lims.concentration.level',
        'Concentration level', readonly=True)
    mean = fields.Float('Mean', readonly=True)
    deviation = fields.Float('Standard Deviation', readonly=True)
    one_sd = fields.Function(fields.Float('1 SD', depends=['deviation']),
        'get_one_sd')
    two_sd = fields.Function(fields.Float('2 SD', depends=['deviation']),
        'get_two_sd')
    three_sd = fields.Function(fields.Float('3 SD', depends=['deviation']),
        'get_three_sd')
    cv = fields.Function(fields.Float('CV (%)', depends=['deviation',
        'mean']), 'get_cv')
    prev_mean = fields.Function(fields.Float('Previous Mean', depends=[
        'product_type', 'matrix', 'fraction_type', 'analysis',
        'concentration_level', ]), 'get_prev_mean')
    prev_one_sd = fields.Function(fields.Float('Previous 1 SD', depends=[
        'product_type', 'matrix', 'fraction_type', 'analysis',
        'concentration_level', ]), 'get_prev_one_sd')
    prev_two_sd = fields.Function(fields.Float('Previous 2 SD', depends=[
        'product_type', 'matrix', 'fraction_type', 'analysis',
        'concentration_level', ]), 'get_prev_two_sd')
    prev_three_sd = fields.Function(fields.Float('Previous 3 SD', depends=[
        'product_type', 'matrix', 'fraction_type', 'analysis',
        'concentration_level', ]), 'get_prev_three_sd')
    prev_cv = fields.Function(fields.Float('Previous CV (%)', depends=[
        'product_type', 'matrix', 'fraction_type', 'analysis',
        'concentration_level', ]), 'get_prev_cv')
    details = fields.One2Many('lims.control.result_line.detail', 'line',
        'Details', readonly=True)
    update = fields.Boolean('Update')
    session_id = fields.Integer('Session ID')

    @classmethod
    def __register__(cls, module_name):
        super(LimsControlResultLine,
            cls).__register__(module_name)
        cursor = Transaction().connection.cursor()
        cursor.execute('DELETE FROM "' + cls._table + '"')

    @classmethod
    def __setup__(cls):
        super(LimsControlResultLine, cls).__setup__()
        cls._order.insert(0, ('product_type', 'ASC'))
        cls._order.insert(1, ('matrix', 'ASC'))
        cls._order.insert(2, ('analysis', 'ASC'))
        cls._order.insert(3, ('concentration_level', 'ASC'))

    @staticmethod
    def default_update():
        return False

    def get_one_sd(self, name=None):
        return self.deviation

    def get_two_sd(self, name=None):
        return self.deviation * 2

    def get_three_sd(self, name=None):
        return self.deviation * 3

    def get_cv(self, name=None):
        if self.mean:
            return (self.deviation / self.mean) * 100

    def get_prev_mean(self, name=None):
        LimsControlTendency = Pool().get('lims.control.tendency')
        tendency = LimsControlTendency.search([
            ('product_type', '=', self.product_type.id),
            ('matrix', '=', self.matrix.id),
            ('fraction_type', '=', self.fraction_type.id),
            ('analysis', '=', self.analysis.id),
            ('concentration_level', '=', self.concentration_level),
            ])
        if tendency:
            return tendency[0].mean
        return 0.00

    def get_prev_one_sd(self, name=None):
        LimsControlTendency = Pool().get('lims.control.tendency')
        tendency = LimsControlTendency.search([
            ('product_type', '=', self.product_type.id),
            ('matrix', '=', self.matrix.id),
            ('fraction_type', '=', self.fraction_type.id),
            ('analysis', '=', self.analysis.id),
            ('concentration_level', '=', self.concentration_level),
            ])
        if tendency:
            return tendency[0].one_sd
        return 0.00

    def get_prev_two_sd(self, name=None):
        LimsControlTendency = Pool().get('lims.control.tendency')
        tendency = LimsControlTendency.search([
            ('product_type', '=', self.product_type.id),
            ('matrix', '=', self.matrix.id),
            ('fraction_type', '=', self.fraction_type.id),
            ('analysis', '=', self.analysis.id),
            ('concentration_level', '=', self.concentration_level),
            ])
        if tendency:
            return tendency[0].two_sd
        return 0.00

    def get_prev_three_sd(self, name=None):
        LimsControlTendency = Pool().get('lims.control.tendency')
        tendency = LimsControlTendency.search([
            ('product_type', '=', self.product_type.id),
            ('matrix', '=', self.matrix.id),
            ('fraction_type', '=', self.fraction_type.id),
            ('analysis', '=', self.analysis.id),
            ('concentration_level', '=', self.concentration_level),
            ])
        if tendency:
            return tendency[0].three_sd
        return 0.00

    def get_prev_cv(self, name=None):
        LimsControlTendency = Pool().get('lims.control.tendency')
        tendency = LimsControlTendency.search([
            ('product_type', '=', self.product_type.id),
            ('matrix', '=', self.matrix.id),
            ('fraction_type', '=', self.fraction_type.id),
            ('analysis', '=', self.analysis.id),
            ('concentration_level', '=', self.concentration_level),
            ])
        if tendency:
            return tendency[0].cv
        return 0.00


class LimsControlResultLineDetail(ModelSQL, ModelView):
    'Control Chart Result Line Detail'
    __name__ = 'lims.control.result_line.detail'

    line = fields.Many2One('lims.control.result_line', 'Line',
        ondelete='CASCADE', select=True, required=True)
    date = fields.Date('Date')
    fraction = fields.Many2One('lims.fraction', 'Fraction')
    device = fields.Many2One('lims.lab.device', 'Device')
    result = fields.Float('Result')

    @classmethod
    def __setup__(cls):
        super(LimsControlResultLineDetail, cls).__setup__()
        cls._order.insert(0, ('date', 'ASC'))
        cls._order.insert(1, ('fraction', 'ASC'))
        cls._order.insert(2, ('device', 'ASC'))


class LimsMeansDeviationsCalcResult2(ModelView):
    'Calculation of Means and Deviations'
    __name__ = 'lims.control.means_deviations_calc.result2'

    tendencies = fields.One2Many('lims.control.tendency', None, 'Tendencies',
        readonly=True)


class LimsMeansDeviationsCalc(Wizard):
    'Calculation of Means and Deviations'
    __name__ = 'lims.control.means_deviations_calc'

    start = StateView('lims.control.means_deviations_calc.start',
        'lims.lims_control_means_deviations_calc_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search', 'search', 'tryton-go-next', default=True),
            ])
    search = StateTransition()
    empty = StateView('lims.control.means_deviations_calc.empty',
        'lims.lims_control_means_deviations_calc_empty_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search again', 'start', 'tryton-go-next', default=True),
            ])
    result = StateView('lims.control.means_deviations_calc.result',
        'lims.lims_control_means_deviations_calc_result_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Update', 'update', 'tryton-go-next', default=True),
            ])
    update = StateTransition()
    result2 = StateView('lims.control.means_deviations_calc.result2',
        'lims.lims_control_means_deviations_calc_result2_view_form', [])
    open = StateAction('lims.act_lims_control_tendency2')

    def default_start(self, fields):
        res = {}
        for field in ('date_from', 'date_to'):
            if (hasattr(self.start, field) and getattr(self.start, field)):
                res[field] = getattr(self.start, field)
        for field in ('family', 'laboratory', 'product_type', 'matrix',
                'fraction_type'):
            if (hasattr(self.start, field) and getattr(self.start, field)):
                res[field] = getattr(self.start, field).id
        for field in ('product_type_domain', 'matrix_domain'):
            if (hasattr(self.start, field) and getattr(self.start, field)):
                res[field] = [f.id for f in getattr(self.start, field)]

        return res

    def transition_search(self):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsControlResultLine = pool.get('lims.control.result_line')
        LimsAnalysisFamilyCertificant = pool.get(
            'lims.analysis.family.certificant')
        LimsNotebookLine = pool.get('lims.notebook.line')

        clause = [
            ('laboratory', '=', self.start.laboratory.id),
            ('end_date', '>=', self.start.date_from),
            ('end_date', '<=', self.start.date_to),
            ('notebook.fraction.type', '=', self.start.fraction_type.id),
            ('analysis.behavior', '=', 'normal'),
            ('result', 'not in', [None, '']),
            ]
        if self.start.product_type:
            clause.append(('notebook.product_type', '=',
                self.start.product_type.id))
        if self.start.matrix:
            clause.append(('notebook.matrix', '=', self.start.matrix.id))
        check_family = False
        if self.start.family:
            check_family = True
            families = []
            cursor.execute('SELECT product_type, matrix '
                'FROM "' + LimsAnalysisFamilyCertificant._table + '" '
                'WHERE family = %s',
                (self.start.family.id,))
            res = cursor.fetchall()
            if res:
                families = [(x[0], x[1]) for x in res]

        lines = LimsNotebookLine.search(clause)
        if lines:
            records = {}
            for line in lines:
                try:
                    result = float(line.result or None)
                except (TypeError, ValueError):
                    continue

                if check_family:
                    family_key = (line.notebook.product_type.id,
                        line.notebook.matrix.id)
                    if family_key not in families:
                        continue

                product_type_id = line.notebook.product_type.id
                matrix_id = line.notebook.matrix.id
                fraction_type_id = line.notebook.fraction_type.id
                analysis_id = line.analysis.id
                concentration_level_id = (line.concentration_level.id if
                    line.concentration_level else None)

                key = (product_type_id, matrix_id, analysis_id,
                    concentration_level_id)
                if key not in records:
                    records[key] = {
                        'product_type': product_type_id,
                        'matrix': matrix_id,
                        'fraction_type': fraction_type_id,
                        'analysis': analysis_id,
                        'concentration_level': concentration_level_id,
                        'details': {},
                        }
                records[key]['details'][line.id] = {
                    'date': line.end_date,
                    'fraction': line.notebook.fraction.id,
                    'device': line.device.id if line.device else None,
                    'result': result,
                    }
            if records:
                to_create = []
                for record in records.itervalues():
                    details = [d for d in record['details'].itervalues()]
                    to_create.append({
                        'session_id': self._session_id,
                        'product_type': record['product_type'],
                        'matrix': record['matrix'],
                        'fraction_type': record['fraction_type'],
                        'analysis': record['analysis'],
                        'concentration_level': record['concentration_level'],
                        'details': [('create', details)],
                        })
                if to_create:
                    res_lines = LimsControlResultLine.create(to_create)

                    to_save = []
                    for line in res_lines:
                        count = 0.00
                        total = 0.00
                        for detail in line.details:
                            count += 1
                            total += detail.result
                        mean = round(total / count, 2)
                        total = 0.00
                        for detail in line.details:
                            total += (detail.result - mean) ** 2
                        # Se toma correcion poblacional Bessel n-1
                        if count > 1:
                            deviation = round(sqrt(total / (count - 1)), 2)
                        else:
                            deviation = 0.00
                        line.mean = mean
                        line.deviation = deviation
                        to_save.append(line)
                    LimsControlResultLine.save(to_save)

                    self.result.lines = res_lines
                    return 'result'
        return 'empty'

    def default_result(self, fields):
        lines = [l.id for l in self.result.lines]
        self.result.lines = None
        return {
            'lines': lines,
            }

    def transition_update(self):
        pool = Pool()
        LimsControlResultLine = pool.get('lims.control.result_line')
        LimsControlTendency = pool.get('lims.control.tendency')
        LimsLaboratoryCVCorrection = pool.get('lims.laboratory.cv_correction')

        res_lines_ids = [rl.id for rl in self.result.lines if rl.update]
        self.result.lines = None
        res_lines = LimsControlResultLine.search([
            ('session_id', '=', self._session_id),
            ('id', 'in', res_lines_ids),
            ])
        if not res_lines:
            return 'empty'

        cv_correction = LimsLaboratoryCVCorrection.search([
            ('laboratory', '=', self.start.laboratory.id),
            ('fraction_type', '=', self.start.fraction_type.id),
            ])
        if cv_correction:
            min_cv = cv_correction[0].min_cv or 1
            max_cv = cv_correction[0].max_cv or 1
            min_cv_corr_fact = cv_correction[0].min_cv_corr_fact or 1
            max_cv_corr_fact = cv_correction[0].max_cv_corr_fact or 1
        else:
            min_cv = 1
            max_cv = 1
            min_cv_corr_fact = 1
            max_cv_corr_fact = 1

        tendencies = []
        for line in res_lines:
            concentration_level_id = (line.concentration_level.id if
                line.concentration_level else None)
            tendency = LimsControlTendency.search([
                ('product_type', '=', line.product_type.id),
                ('matrix', '=', line.matrix.id),
                ('fraction_type', '=', line.fraction_type.id),
                ('analysis', '=', line.analysis.id),
                ('concentration_level', '=', concentration_level_id),
                ])
            if tendency:
                LimsControlTendency.write(tendency, {
                    'mean': line.mean,
                    'deviation': line.deviation,
                    'min_cv': min_cv,
                    'max_cv': max_cv,
                    'min_cv_corr_fact': min_cv_corr_fact,
                    'max_cv_corr_fact': max_cv_corr_fact,
                    'rule_1_count': 0,
                    'rule_2_count': 0,
                    'rule_3_count': 0,
                    'rule_4_count': 0,
                    })
                tendencies.extend(tendency)
            else:
                tendency, = LimsControlTendency.create([{
                    'product_type': line.product_type.id,
                    'matrix': line.matrix.id,
                    'fraction_type': line.fraction_type.id,
                    'analysis': line.analysis.id,
                    'concentration_level': concentration_level_id,
                    'mean': line.mean,
                    'deviation': line.deviation,
                    'min_cv': min_cv,
                    'max_cv': max_cv,
                    'min_cv_corr_fact': min_cv_corr_fact,
                    'max_cv_corr_fact': max_cv_corr_fact,
                    }])
                tendencies.append(tendency)
        self.result2.tendencies = tendencies
        return 'open'

    def do_open(self, action):
        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', 'in', [t.id for t in self.result2.tendencies]),
            ])
        action['pyson_context'] = PYSONEncoder().encode({
            'readonly': True,
            })
        self.result2.tendencies = None
        return action, {}


class LimsTendenciesAnalysisStart(ModelView):
    'Tendencies Analysis'
    __name__ = 'lims.control.tendencies_analysis.start'

    date_from = fields.Date('Date from', required=True)
    date_to = fields.Date('Date to', required=True)
    family = fields.Many2One('lims.analysis.family', 'Family')
    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        required=True)
    product_type = fields.Many2One('lims.product.type', 'Product type',
        domain=[('id', 'in', Eval('product_type_domain'))],
        depends=['product_type_domain'])
    product_type_domain = fields.Function(fields.Many2Many(
        'lims.product.type', None, None, 'Product type domain'),
        'on_change_with_product_type_domain')
    matrix = fields.Many2One('lims.matrix', 'Matrix',
        domain=[('id', 'in', Eval('matrix_domain'))],
        depends=['matrix_domain'])
    matrix_domain = fields.Function(fields.Many2Many('lims.matrix',
        None, None, 'Matrix domain'), 'on_change_with_matrix_domain')
    fraction_type = fields.Many2One('lims.fraction.type', 'Fraction type',
        domain=[('control_charts', '=', True)], required=True)

    @staticmethod
    def default_product_type_domain():
        cursor = Transaction().connection.cursor()
        LimsTypification = Pool().get('lims.typification')

        cursor.execute('SELECT DISTINCT(product_type) '
            'FROM "' + LimsTypification._table + '" '
            'WHERE valid')
        return [x[0] for x in cursor.fetchall()]

    @fields.depends('family')
    def on_change_with_product_type_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        LimsAnalysisFamilyCertificant = Pool().get(
            'lims.analysis.family.certificant')

        if not self.family:
            return self.default_product_type_domain()

        cursor.execute('SELECT DISTINCT(product_type) '
            'FROM "' + LimsAnalysisFamilyCertificant._table + '" '
            'WHERE family = %s',
            (self.family.id,))
        return [x[0] for x in cursor.fetchall()]

    @fields.depends('product_type', 'family')
    def on_change_with_matrix_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsAnalysisFamilyCertificant = pool.get(
            'lims.analysis.family.certificant')
        LimsTypification = pool.get('lims.typification')

        if not self.product_type:
            return []

        if not self.family:
            cursor.execute('SELECT DISTINCT(matrix) '
                'FROM "' + LimsTypification._table + '" '
                'WHERE product_type = %s '
                'AND valid',
                (self.product_type.id,))
            return [x[0] for x in cursor.fetchall()]
        else:
            cursor.execute('SELECT DISTINCT(matrix) '
                'FROM "' + LimsAnalysisFamilyCertificant._table + '" '
                'WHERE product_type = %s '
                'AND family = %s',
                (self.product_type.id, self.family.id))
            return [x[0] for x in cursor.fetchall()]


class LimsTendenciesAnalysisResult(ModelView):
    'Tendencies Analysis'
    __name__ = 'lims.control.tendencies_analysis.result'

    tendencies = fields.One2Many('lims.control.tendency', None, 'Tendencies',
        readonly=True)


class LimsTendenciesAnalysis(Wizard):
    'Tendencies Analysis'
    __name__ = 'lims.control.tendencies_analysis'

    start = StateView('lims.control.tendencies_analysis.start',
        'lims.lims_control_tendencies_analysis_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Open', 'search', 'tryton-ok', True),
            ])
    search = StateTransition()
    result = StateView('lims.control.tendencies_analysis.result',
        'lims.lims_control_tendencies_analysis_result_view_form', [])
    open = StateAction('lims.act_lims_control_tendency3')

    def transition_search(self):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsControlTendency = pool.get('lims.control.tendency')
        LimsControlTendencyDetail = pool.get('lims.control.tendency.detail')
        LimsAnalysisFamilyCertificant = pool.get(
            'lims.analysis.family.certificant')
        LimsNotebookLine = pool.get('lims.notebook.line')

        tendency_result = []

        clause = [
            ('fraction_type', '=', self.start.fraction_type.id),
            ]
        if self.start.product_type:
            clause.append(('product_type', '=', self.start.product_type.id))
        if self.start.matrix:
            clause.append(('matrix', '=', self.start.matrix.id))

        tendencies = LimsControlTendency.search(clause)
        if tendencies:
            check_family = False
            if self.start.family:
                check_family = True
                families = []
                cursor.execute('SELECT product_type, matrix '
                    'FROM "' + LimsAnalysisFamilyCertificant._table + '" '
                    'WHERE family = %s',
                    (self.start.family.id,))
                res = cursor.fetchall()
                if res:
                    families = [(x[0], x[1]) for x in res]

            for tendency in tendencies:
                if check_family:
                    family_key = (tendency.product_type.id, tendency.matrix.id)
                    if family_key not in families:
                        continue

                old_details = LimsControlTendencyDetail.search([
                    ('tendency', '=', tendency.id),
                    ])
                if old_details:
                    LimsControlTendencyDetail.delete(old_details)

                concentration_level_id = (tendency.concentration_level.id if
                    tendency.concentration_level else None)
                clause = [
                    ('laboratory', '=', self.start.laboratory.id),
                    ('notebook.fraction.type', '=', tendency.fraction_type.id),
                    ('notebook.product_type', '=', tendency.product_type.id),
                    ('notebook.matrix', '=', tendency.matrix.id),
                    ('analysis', '=', tendency.analysis.id),
                    ('concentration_level', '=', concentration_level_id),
                    ('result', '!=', None),
                    ]

                rule_1_count = 0
                rule_2_count = 0
                rule_3_count = 0
                rule_4_count = 0
                lines = LimsNotebookLine.search(clause + [
                        ('end_date', '>=', self.start.date_from),
                        ('end_date', '<=', self.start.date_to),
                    ], order=[('end_date', 'ASC'), ('id', 'ASC')])
                if lines:
                    results = []
                    prevs = 8 - len(lines)  # Qty of previous results required
                    if prevs > 0:
                        prev_lines = LimsNotebookLine.search(clause + [
                                ('end_date', '<', self.start.date_from),
                            ], order=[('end_date', 'ASC'), ('id', 'ASC')],
                            limit=prevs)
                        if prev_lines:
                            for line in prev_lines:
                                result = float(line.result if
                                    line.result else None)
                                results.append(result)

                    to_create = []
                    for line in lines:
                        try:
                            result = float(line.result if
                                line.result else None)
                            results.append(result)
                        except(TypeError, ValueError):
                            continue
                        rules = self.get_rules(results, tendency)
                        rules_to_create = []
                        for r in rules:
                            if r == '':
                                continue
                            rules_to_create.append({'rule': r})
                            if r == '1':
                                rule_1_count += 1
                            elif r == '2':
                                rule_2_count += 1
                            elif r == '3':
                                rule_3_count += 1
                            elif r == '4':
                                rule_4_count += 1

                        record = {
                            'notebook_line': line.id,
                            'tendency': tendency.id,
                            'date': line.end_date,
                            'fraction': line.notebook.fraction.id,
                            'device': line.device.id if line.device else None,
                            'result': result,
                            'rule': rules[0],
                            }
                        if rules_to_create:
                            record['rules'] = [('create', rules_to_create)]
                        to_create.append(record)

                    LimsControlTendencyDetail.create(to_create)
                    tendency_result.append(tendency)

                LimsControlTendency.write([tendency], {
                    'rule_1_count': rule_1_count,
                    'rule_2_count': rule_2_count,
                    'rule_3_count': rule_3_count,
                    'rule_4_count': rule_4_count,
                    })

            if tendency_result:
                self.result.tendencies = tendency_result
                return 'open'
        return 'end'

    def get_rules(self, results, tendency):

        rules = []

        # Check rule 4
        # 1 value above or below the mean +/- 3 SD
        upper_parameter = tendency.mean + tendency.three_sd_adj
        lower_parameter = tendency.mean - tendency.three_sd_adj
        occurrences = 1
        total = 1
        if self._check_rule(results, upper_parameter, lower_parameter,
                occurrences, total):
            rules.append('4')

        # Check rule 3
        # 2 of 3 consecutive values above or below the mean +/- 2 SD
        upper_parameter = tendency.mean + tendency.two_sd_adj
        lower_parameter = tendency.mean - tendency.two_sd_adj
        occurrences = 2
        total = 3
        if self._check_rule(results, upper_parameter, lower_parameter,
                occurrences, total):
            rules.append('3')

        # Check rule 2
        # 4 of 5 consecutive values above or below the mean +/- 1 SD
        upper_parameter = tendency.mean + tendency.one_sd_adj
        lower_parameter = tendency.mean - tendency.one_sd_adj
        occurrences = 4
        total = 5
        if self._check_rule(results, upper_parameter, lower_parameter,
                occurrences, total):
            rules.append('2')

        # Check rule 1
        # 8 consecutive values above or below the mean
        upper_parameter = tendency.mean
        lower_parameter = tendency.mean
        occurrences = 8
        total = 8
        if self._check_rule(results, upper_parameter, lower_parameter,
                occurrences, total):
            rules.append('1')

        if not rules:
            rules.append('')

        return rules

    def _check_rule(self, results, upper_parameter, lower_parameter,
            occurrences, total):

        if len(results) < total:
            return False

        total_counter = 0
        upper_counter = 0
        lower_counter = 0
        for result in reversed(results):

            total_counter += 1
            if result > upper_parameter:
                upper_counter += 1
                if total_counter == total:
                    if (upper_counter >= occurrences or
                            lower_counter >= occurrences):
                        return True
                    return False
                lower_counter = 0
            elif result < lower_parameter:
                lower_counter += 1
                if total_counter == total:
                    if (lower_counter >= occurrences or
                            upper_counter >= occurrences):
                        return True
                    return False
                upper_counter = 0
            else:
                if total_counter == total:
                    if (upper_counter >= occurrences or
                            lower_counter >= occurrences):
                        return True
                    return False
                upper_counter = 0
                lower_counter = 0
        return False

    def do_open(self, action):
        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', 'in', [t.id for t in self.result.tendencies]),
            ])
        action['pyson_context'] = PYSONEncoder().encode({
            'readonly': True,
            'print_available': True,
            })
        self.result.tendencies = None
        return action, {}


class LimsDivideReportsResult(ModelView):
    'Divide Reports'
    __name__ = 'lims.divide_reports.result'

    services = fields.Many2Many('lims.service', None, None, 'Services')
    total = fields.Integer('Total')
    index = fields.Integer('Index')


class LimsDivideReportsDetail(ModelSQL, ModelView):
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
        super(LimsDivideReportsDetail,
            cls).__register__(module_name)
        cursor = Transaction().connection.cursor()
        cursor.execute('DELETE FROM "' + cls._table + '"')


class LimsDivideReportsProcess(ModelView):
    'Divide Reports'
    __name__ = 'lims.divide_reports.process'

    fraction = fields.Many2One('lims.fraction', 'Fraction', readonly=True)
    service = fields.Many2One('lims.service', 'Service', readonly=True)
    analysis = fields.Many2One('lims.analysis', 'Analysis', readonly=True)
    analysis_detail = fields.One2Many('lims.divide_reports.detail',
        None, 'Analysis detail')


class LimsDivideReports(Wizard):
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
            Button('Next', 'next_', 'tryton-go-next', default=True),
            ])
    confirm = StateTransition()

    def transition_search(self):
        LimsService = Pool().get('lims.service')

        services = LimsService.search([
            ('entry', '=', Transaction().context['active_id']),
            ('divide', '=', True),
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
        LimsDivideReportsDetail = Pool().get(
            'lims.divide_reports.detail')

        if not self.process.service:
            return {}

        default = {}
        default['fraction'] = self.process.service.fraction.id
        default['service'] = self.process.service.id
        default['analysis'] = self.process.service.analysis.id
        details = LimsDivideReportsDetail.create([{
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
        LimsDivideReportsDetail = pool.get(
            'lims.divide_reports.detail')
        LimsEntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        details = LimsDivideReportsDetail.search([
            ('session_id', '=', self._session_id),
            ])
        for detail in details:
            analysis_detail = LimsEntryDetailAnalysis(detail.detail_id)
            analysis_detail.report_grouper = detail.report_grouper
            analysis_detail.save()
        return 'end'


class LimsGenerateResultsReportStart(ModelView):
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


class LimsGenerateResultsReportEmpty(ModelView):
    'Generate Results Report'
    __name__ = 'lims.generate_results_report.empty'


class LimsGenerateResultsReportResultAut(ModelView):
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


class LimsGenerateResultsReportResultAutNotebook(ModelSQL, ModelView):
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
        super(LimsGenerateResultsReportResultAutNotebook,
            cls).__register__(module_name)
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


class LimsGenerateResultsReportResultAutNotebookLine(ModelSQL, ModelView):
    'Notebook Line'
    __name__ = 'lims.generate_results_report.aut.notebook-line'

    notebook = fields.Many2One(
        'lims.generate_results_report.aut.notebook', 'Notebook',
        ondelete='CASCADE', select=True, required=True)
    line = fields.Many2One('lims.notebook.line', 'Notebook Line',
        ondelete='CASCADE', select=True, required=True)


class LimsGenerateResultsReportResultAutExcludedNotebook(ModelSQL, ModelView):
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
        super(LimsGenerateResultsReportResultAutExcludedNotebook,
            cls).__register__(module_name)
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


class LimsGenerateResultsReportResultAutExcludedNotebookLine(ModelSQL,
        ModelView):
    'Excluded Notebook Line'
    __name__ = 'lims.generate_results_report.aut.excluded_notebook-line'
    _table = 'lims_generate_results_report_aut_excluded_nb-line'

    notebook = fields.Many2One(
        'lims.generate_results_report.aut.excluded_notebook',
        'Notebook', ondelete='CASCADE', select=True, required=True)
    line = fields.Many2One('lims.notebook.line', 'Notebook Line',
        ondelete='CASCADE', select=True, required=True)


class LimsGenerateResultsReportResultMan(ModelView):
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

    @fields.depends('report')
    def on_change_with_party(self, name=None):
        if self.report:
            return self.report.party.id
        return None

    @fields.depends('report')
    def on_change_with_notebook(self, name=None):
        if self.report and self.report.notebook:
            return self.report.notebook.id
        return None

    @fields.depends('report')
    def on_change_with_report_grouper(self, name=None):
        if self.report:
            return self.report.report_grouper
        return None

    @fields.depends('report', 'laboratory')
    def on_change_with_report_type(self, name=None):
        if self.report:
            LimsResultsReportVersion = Pool().get(
                'lims.results_report.version')
            version = LimsResultsReportVersion.search([
                ('results_report.id', '=', self.report.id),
                ('laboratory.id', '=', self.laboratory.id),
                ], limit=1)
            if version:
                return version[0].report_type
            version = LimsResultsReportVersion.search([
                ('results_report.id', '=', self.report.id),
                ], order=[('id', 'DESC')], limit=1)
            if version:
                return version[0].report_type
        return None

    @fields.depends('report')
    def on_change_with_cie_fraction_type(self, name=None):
        if self.report:
            with Transaction().set_context(_check_access=False):
                return self.report.cie_fraction_type
        return False


class LimsGenerateResultsReport(Wizard):
    'Generate Results Report'
    __name__ = 'lims.generate_results_report'

    start = StateView('lims.generate_results_report.start',
        'lims.lims_generate_results_report_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search', 'search', 'tryton-go-next', default=True),
            ])
    search = StateTransition()
    empty = StateView('lims.generate_results_report.empty',
        'lims.lims_generate_results_report_empty_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search again', 'start', 'tryton-go-next', default=True),
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
        LimsResultsReportVersionDetailLine = pool.get(
            'lims.results_report.version.detail.line')
        NotebookLine = pool.get('lims.notebook.line')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        clause = [
            ('notebook.fraction.type.report', '=', True),
            ('notebook.date2', '>=', self.start.date_from),
            ('notebook.date2', '<=', self.start.date_to),
            ('laboratory', '=', self.start.laboratory.id),
            ('report', '=', True),
            ('annulled', '=', False),
            ]
        if self.start.party:
            clause.append(('notebook.party', '=', self.start.party.id))

        draft_lines_ids = []
        draft_lines = LimsResultsReportVersionDetailLine.search([
            ('report_version_detail.state', '=', 'draft'),
            ])
        if draft_lines:
            draft_lines_ids = [dl.notebook_line.id for dl in draft_lines]

        clause.extend([
            ('accepted', '=', True),
            ('results_report', '=', None),
            ('id', 'not in', draft_lines_ids),
            ])
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

        cursor.execute('SELECT nl.notebook, nl.analysis, nl.accepted, '
                'd.report_grouper '
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
                'AND nl.annulled = FALSE '
                + party_clause,
            (self.start.date_from, self.start.date_to,
                self.start.laboratory.id,))
        notebook_lines = cursor.fetchall()

        # Check accepted repetitions
        to_check = []
        oks = []
        accepted_notebooks = []
        for line in notebook_lines:
            key = (line[0], line[1], line[3])
            if not line[2]:
                to_check.append(key)
            else:
                oks.append(key)
                accepted_notebooks.append(line[0])

        to_check = list(set(to_check) - set(oks))
        accepted_notebooks = list(set(accepted_notebooks))

        excluded_notebooks = {}
        for n_id, a_id, grouper in to_check:
            if n_id not in accepted_notebooks:
                continue
            key = (n_id, grouper)
            if key not in excluded_notebooks:
                excluded_notebooks[key] = []
            excluded_notebooks[key].append(a_id)
        return excluded_notebooks

    def _search_aut(self):
        pool = Pool()
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsGenerateResultsReportResultAutNotebook = pool.get(
            'lims.generate_results_report.aut.notebook')
        LimsGenerateResultsReportResultAutExcludedNotebook = pool.get(
            'lims.generate_results_report.aut.excluded_notebook')

        self.result_aut.excluded_notebooks = None
        self.result_aut.notebooks = None
        self.result_aut.notebook_lines = None

        excluded_notebooks = self._get_excluded_notebooks()
        if excluded_notebooks:
            notebooks = {}
            for (n_id, grouper), a_ids in excluded_notebooks.iteritems():
                clause = [
                    ('notebook.id', '=', n_id),
                    ('analysis_detail.report_grouper', '=', grouper),
                    ('analysis', 'in', a_ids),
                    ('laboratory', '=', self.start.laboratory.id),
                    ('report', '=', True),
                    ('annulled', '=', False),
                    ]
                excluded_lines = LimsNotebookLine.search(clause)
                if excluded_lines:
                    notebooks[n_id] = [line.id for line in excluded_lines]

            to_create = [{
                'session_id': self._session_id,
                'notebook': k,
                'lines': [('add', v)],
                } for k, v in notebooks.iteritems()]
            self.result_aut.excluded_notebooks = (
                LimsGenerateResultsReportResultAutExcludedNotebook.create(
                    to_create))

        notebook_lines = self._get_notebook_lines('aut',
            excluded_notebooks.keys())
        if notebook_lines:
            notebooks = {}
            for line in notebook_lines:
                if line.notebook.id not in notebooks:
                    notebooks[line.notebook.id] = []
                notebooks[line.notebook.id].append(line.id)

            to_create = []
            for k, v in notebooks.iteritems():
                to_create.append({
                    'session_id': self._session_id,
                    'notebook': k,
                    'lines': [('add', v)],
                    })
            self.result_aut.notebooks = (
                LimsGenerateResultsReportResultAutNotebook.create(to_create))
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
        LimsResultsReport = Pool().get('lims.results_report')

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
            reports = LimsResultsReport.search(clause)
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
        LimsNotebookLine = Pool().get('lims.notebook.line')

        notebooks = {}
        for line in self.result_aut.notebook_lines:
            if line.notebook.id not in notebooks:
                notebooks[line.notebook.id] = {
                    'party': line.notebook.party.id,
                    'notebook': line.notebook.id,
                    'divided_report': line.notebook.divided_report,
                    'english_report': (
                        line.notebook.fraction.entry.english_report),
                    'notebook_lines': [],
                    'cie_fraction_type': (
                        line.notebook.fraction.cie_fraction_type),
                    }
            notebooks[line.notebook.id]['notebook_lines'].append({
                'notebook_line': line.id,
                })

        reports_details = []
        for notebook in notebooks.itervalues():
            if not notebook['divided_report']:
                details = {
                    'notebook_lines': [('create', notebook['notebook_lines'])],
                    'signer': self.start.laboratory.default_signer.id,
                    }
                versions = {
                    'laboratory': self.start.laboratory.id,
                    'details': [('create', [details])],
                    }
                reports = {
                    'party': notebook['party'],
                    'notebook': notebook['notebook'],
                    'report_grouper': 0,
                    'generation_type': 'aut',
                    'cie_fraction_type': notebook['cie_fraction_type'],
                    'english_report': notebook['english_report'],
                    'versions': [('create', [versions])],
                    }
                report_detail = self._get_results_report(reports, versions,
                    details)
                reports_details.extend(report_detail)
            else:
                grouped_reports = {}
                for line in notebook['notebook_lines']:
                    nline = LimsNotebookLine(line['notebook_line'])
                    report_grouper = nline.analysis_detail.report_grouper
                    if report_grouper not in grouped_reports:
                        grouped_reports[report_grouper] = []
                    grouped_reports[report_grouper].append(line)

                for grouper, notebook_lines in grouped_reports.iteritems():
                    details = {
                        'notebook_lines': [('create', notebook_lines)],
                        'signer': self.start.laboratory.default_signer.id,
                        }
                    versions = {
                        'laboratory': self.start.laboratory.id,
                        'details': [('create', [details])],
                        }
                    reports = {
                        'party': notebook['party'],
                        'notebook': notebook['notebook'],
                        'report_grouper': grouper,
                        'generation_type': 'aut',
                        'cie_fraction_type': notebook['cie_fraction_type'],
                        'english_report': notebook['english_report'],
                        'versions': [('create', [versions])],
                        }
                    report_detail = self._get_results_report(reports, versions,
                        details)
                    reports_details.extend(report_detail)

        self.result_aut.reports_details = reports_details
        return 'open'

    def _generate_man(self):
        pool = Pool()
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsResultsReportVersion = pool.get('lims.results_report.version')
        LimsResultsReportVersionDetail = pool.get(
            'lims.results_report.version.detail')

        if self.result_man.report:  # Result report selected
            report_type_forced = self.result_man.report_type
            if report_type_forced == 'polisample':  # Polisample report
                notebook_lines = []
                for line in self.result_man.notebook_lines:
                    notebook_lines.append({
                        'notebook_line': line.id,
                        })

                details = {
                    'notebook_lines': [('create', notebook_lines)],
                    'report_type_forced': 'polisample',
                    'signer': self.start.laboratory.default_signer.id,
                    }
                actual_version = LimsResultsReportVersion.search([
                    ('results_report', '=', self.result_man.report.id),
                    ('laboratory', '=', self.start.laboratory.id),
                    ], limit=1)
                if not actual_version:
                    version, = LimsResultsReportVersion.create([{
                        'results_report': self.result_man.report.id,
                        'laboratory': self.start.laboratory.id,
                        'details': [('create', [details])],
                        }])
                    reports_details = [d.id for d in version.details]
                else:
                    draft_detail = LimsResultsReportVersionDetail.search([
                        ('report_version', '=', actual_version[0].id),
                        ('state', '=', 'draft'),
                        ], limit=1)
                    if not draft_detail:
                        details['report_version'] = actual_version[0].id
                        valid_detail = LimsResultsReportVersionDetail.search([
                            ('report_version', '=', actual_version[0].id),
                            ('valid', '=', True),
                            ], limit=1)
                        if valid_detail:
                            details['report_type_forced'] = (
                                valid_detail[0].report_type_forced)
                            details['report_result_type_forced'] = (
                                valid_detail[0].report_result_type_forced)
                            if valid_detail[0].signer:
                                details['signer'] = valid_detail[0].signer.id
                            details['comments'] = unicode(
                                valid_detail[0].comments or '')
                        detail, = LimsResultsReportVersionDetail.create([
                            details])
                        reports_details = [detail.id]
                    else:
                        del details['signer']
                        LimsResultsReportVersionDetail.write(draft_detail,
                            details)
                        reports_details = [draft_detail[0].id]
            else:  # Normal report
                notebook_lines = []
                for line in self.result_man.notebook_lines:
                    notebook_lines.append({
                        'notebook_line': line.id,
                        })
                details = {
                    'notebook_lines': [('create', notebook_lines)],
                    #'report_type_forced': 'normal',
                    'signer': self.start.laboratory.default_signer.id,
                    }

                actual_version = LimsResultsReportVersion.search([
                    ('results_report', '=', self.result_man.report.id),
                    ('laboratory', '=', self.start.laboratory.id),
                    ], limit=1)
                if not actual_version:
                    version, = LimsResultsReportVersion.create([{
                        'results_report': self.result_man.report.id,
                        'laboratory': self.start.laboratory.id,
                        'details': [('create', [details])],
                        }])
                    reports_details = [d.id for d in version.details]
                else:
                    draft_detail = LimsResultsReportVersionDetail.search([
                        ('report_version', '=', actual_version[0].id),
                        ('state', '=', 'draft'),
                        ], limit=1)
                    if not draft_detail:
                        details['report_version'] = actual_version[0].id
                        valid_detail = LimsResultsReportVersionDetail.search([
                            ('report_version', '=', actual_version[0].id),
                            ('valid', '=', True),
                            ], limit=1)
                        if valid_detail:
                            details['report_type_forced'] = (
                                valid_detail[0].report_type_forced)
                            details['report_result_type_forced'] = (
                                valid_detail[0].report_result_type_forced)
                            if valid_detail[0].signer:
                                details['signer'] = valid_detail[0].signer.id
                            details['comments'] = unicode(
                                valid_detail[0].comments or '')
                        detail, = LimsResultsReportVersionDetail.create([
                            details])
                        reports_details = [detail.id]
                    else:
                        del details['signer']
                        LimsResultsReportVersionDetail.write(draft_detail,
                            details)
                        reports_details = [draft_detail[0].id]
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
                            'english_report': (
                                line.notebook.fraction.entry.english_report),
                            'notebook_lines': [],
                            'cie_fraction_type': (
                                line.notebook.fraction.cie_fraction_type),
                            }
                    parties[key]['notebook_lines'].append({
                        'notebook_line': line.id,
                        })

                reports_details = []
                for party in parties.itervalues():
                    grouped_reports = {}
                    for line in party['notebook_lines']:
                        nline = LimsNotebookLine(line['notebook_line'])
                        report_grouper = nline.analysis_detail.report_grouper
                        if report_grouper not in grouped_reports:
                            grouped_reports[report_grouper] = []
                        grouped_reports[report_grouper].append(line)

                    for grouper, notebook_lines in grouped_reports.iteritems():
                        details = {
                            'notebook_lines': [('create', notebook_lines)],
                            'report_type_forced': report_type_forced,
                            'signer': self.start.laboratory.default_signer.id,
                            }
                        versions = {
                            'laboratory': self.start.laboratory.id,
                            'details': [('create', [details])],
                            }
                        reports = {
                            'party': party['party'],
                            'notebook': None,
                            'report_grouper': grouper,
                            'generation_type': 'man',
                            'cie_fraction_type': party['cie_fraction_type'],
                            'english_report': party['english_report'],
                            'versions': [('create', [versions])],
                            }
                        report_detail = self._get_results_report(reports,
                            versions, details, append=False)
                        reports_details.extend(report_detail)
            else:  # Normal report
                notebooks = {}
                for line in self.result_man.notebook_lines:
                    if line.notebook.id not in notebooks:
                        notebooks[line.notebook.id] = {
                            'party': line.notebook.party.id,
                            'notebook': line.notebook.id,
                            'divided_report': line.notebook.divided_report,
                            'english_report': (
                                line.notebook.fraction.entry.english_report),
                            'notebook_lines': [],
                            'cie_fraction_type': (
                                line.notebook.fraction.cie_fraction_type),
                            }
                    notebooks[line.notebook.id]['notebook_lines'].append({
                        'notebook_line': line.id,
                        })

                reports_details = []
                for notebook in notebooks.itervalues():
                    if not notebook['divided_report']:
                        details = {
                            'notebook_lines': [('create',
                                notebook['notebook_lines'])],
                            'report_type_forced': report_type_forced,
                            'signer': self.start.laboratory.default_signer.id,
                            }
                        versions = {
                            'laboratory': self.start.laboratory.id,
                            'details': [('create', [details])],
                            }
                        reports = {
                            'party': notebook['party'],
                            'notebook': notebook['notebook'],
                            'report_grouper': 0,
                            'generation_type': 'man',
                            'cie_fraction_type': notebook['cie_fraction_type'],
                            'english_report': notebook['english_report'],
                            'versions': [('create', [versions])],
                            }
                        report_detail = self._get_results_report(reports,
                            versions, details, append=False)
                        reports_details.extend(report_detail)
                    else:
                        grouped_reports = {}
                        for line in notebook['notebook_lines']:
                            nline = LimsNotebookLine(line['notebook_line'])
                            report_grouper = (
                                nline.analysis_detail.report_grouper)
                            if report_grouper not in grouped_reports:
                                grouped_reports[report_grouper] = []
                            grouped_reports[report_grouper].append(line)

                        for grouper, notebook_lines in \
                                grouped_reports.iteritems():
                            details = {
                                'notebook_lines': [('create', notebook_lines)],
                                'report_type_forced': report_type_forced,
                                'signer': (
                                    self.start.laboratory.default_signer.id),
                                }
                            versions = {
                                'laboratory': self.start.laboratory.id,
                                'details': [('create', [details])],
                                }
                            reports = {
                                'party': notebook['party'],
                                'notebook': notebook['notebook'],
                                'report_grouper': grouper,
                                'generation_type': 'man',
                                'cie_fraction_type': (
                                    notebook['cie_fraction_type']),
                                'english_report': notebook['english_report'],
                                'versions': [('create', [versions])],
                                }
                            report_detail = self._get_results_report(reports,
                                versions, details, append=False)
                            reports_details.extend(report_detail)
            self.result_man.reports_details = reports_details
        return 'open'

    def _get_results_report(self, reports, versions, details, append=True):
        pool = Pool()
        LimsResultsReport = pool.get('lims.results_report')
        LimsResultsReportVersion = pool.get('lims.results_report.version')
        LimsResultsReportVersionDetail = pool.get(
            'lims.results_report.version.detail')

        if not append:
            report, = LimsResultsReport.create([reports])
            reports_details = [d.id for d in report.versions[0].details]
            return reports_details

        actual_report = LimsResultsReport.search([
            ('party', '=', reports['party']),
            ('notebook', '=', reports['notebook']),
            ('report_grouper', '=', reports['report_grouper']),
            ('generation_type', '=', reports['generation_type']),
            ('cie_fraction_type', '=', reports['cie_fraction_type']),
            ], limit=1)
        if not actual_report:
            report, = LimsResultsReport.create([reports])
            reports_details = [d.id for d in report.versions[0].details]
            return reports_details

        actual_version = LimsResultsReportVersion.search([
            ('results_report', '=', actual_report[0].id),
            ('laboratory', '=', self.start.laboratory.id),
            ], limit=1)
        if not actual_version:
            version, = LimsResultsReportVersion.create([{
                'results_report': actual_report[0].id,
                'laboratory': self.start.laboratory.id,
                'details': [('create', [details])],
                }])
            reports_details = [d.id for d in version.details]
        else:
            draft_detail = LimsResultsReportVersionDetail.search([
                ('report_version', '=', actual_version[0].id),
                ('state', '=', 'draft'),
                ], limit=1)
            if not draft_detail:
                details['report_version'] = actual_version[0].id
                valid_detail = LimsResultsReportVersionDetail.search([
                    ('report_version', '=', actual_version[0].id),
                    ('valid', '=', True),
                    ], limit=1)
                if valid_detail:
                    if details.get('report_type_forced') != 'none':
                        details['report_type_forced'] = (
                            valid_detail[0].report_type_forced)
                    details['report_result_type_forced'] = (
                        valid_detail[0].report_result_type_forced)
                    if valid_detail[0].signer:
                        details['signer'] = valid_detail[0].signer.id
                    details['comments'] = unicode(
                        valid_detail[0].comments or '')
                detail, = LimsResultsReportVersionDetail.create([details])
                reports_details = [detail.id]
            else:
                if 'report_type_forced' in details:
                    del details['report_type_forced']
                del details['signer']
                LimsResultsReportVersionDetail.write(draft_detail, details)
                reports_details = [draft_detail[0].id]
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


class LimsDuplicateAnalysisFamilyStart(ModelView):
    'Duplicate Analysis Family'
    __name__ = 'lims.analysis.family.duplicate.start'

    family_origin = fields.Many2One('lims.analysis.family', 'Family Origin')
    code = fields.Char('Code', required=True)
    description = fields.Char('Description', required=True)
    party = fields.Many2One('party.party', 'Certificant party')


class LimsDuplicateAnalysisFamily(Wizard):
    'Duplicate Analysis Family'
    __name__ = 'lims.analysis.family.duplicate'

    start = StateView('lims.analysis.family.duplicate.start',
        'lims.lims_duplicate_analysis_family_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Duplicate', 'duplicate', 'tryton-ok', default=True),
            ])
    duplicate = StateTransition()

    def default_start(self, fields):
        LimsAnalysisFamily = Pool().get('lims.analysis.family')
        family_origin = LimsAnalysisFamily(Transaction().context['active_id'])
        return {
            'family_origin': family_origin.id,
            'code': family_origin.code,
            'description': family_origin.description,
            }

    def transition_duplicate(self):
        LimsAnalysisFamily = Pool().get('lims.analysis.family')
        LimsAnalysisFamily.copy([self.start.family_origin], default={
            'code': self.start.code,
            'description': self.start.description,
            'party': self.start.party.id if self.start.party else None,
            })
        return 'end'


class LimsServiceResultsReport(Wizard):
    'Service Results Report'
    __name__ = 'lims.service.results_report'

    start = StateAction('lims.act_lims_results_report')

    def do_start(self, action):
        pool = Pool()
        LimsService = pool.get('lims.service')
        LimsEntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        service = LimsService(Transaction().context['active_id'])

        results_report_ids = []
        details = LimsEntryDetailAnalysis.search([
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


class LimsPrintResultsReport(Wizard):
    'Print Results Report'
    __name__ = 'lims.print_results_report'

    start = StateTransition()
    print_ = StateAction('lims.report_global_results_report')

    def transition_start(self):
        pool = Pool()
        LimsResultsReport = pool.get(
            'lims.results_report')
        LimsResultsReportVersionDetail = pool.get(
            'lims.results_report.version.detail')

        if not HAS_PDFMERGER:
            LimsResultsReport.raise_user_error('missing_module')

        results_report = LimsResultsReport(Transaction().context['active_id'])
        format_field = 'report_format'
        if results_report.english_report:
            format_field = 'report_format_eng'
        with Transaction().set_user(0):
            details = LimsResultsReportVersionDetail.search([
                ('report_version.results_report.id', '=', results_report.id),
                ('valid', '=', True),
                (format_field, '=', 'pdf'),
                ])
        if not details:
            LimsResultsReport.raise_user_error('empty_report')

        if results_report.english_report:
            results_report.report_format_eng = 'pdf'
            results_report.report_cache_eng = self._get_global_report(details,
                True)
        else:
            results_report.report_format = 'pdf'
            results_report.report_cache = self._get_global_report(details,
                False)
        results_report.save()
        return 'print_'

    def _get_global_report(self, details, english_report=False):
        merger = PdfFileMerger()
        if english_report:
            for detail in details:
                filedata = StringIO.StringIO(detail.report_cache_eng)
                merger.append(filedata)
        else:
            for detail in details:
                filedata = StringIO.StringIO(detail.report_cache)
                merger.append(filedata)
        output = StringIO.StringIO()
        merger.write(output)
        return bytearray(output.getvalue())

    def do_print_(self, action):
        result_id = Transaction().context['active_id']
        data = {
            'id': result_id,
            'ids': [result_id],
            }
        return action, data

    def transition_print_(self):
        return 'end'


class LimsFractionResultsReport(Wizard):
    'Fraction Results Report'
    __name__ = 'lims.fraction.results_report'

    start = StateAction('lims.act_lims_results_report')

    def do_start(self, action):
        pool = Pool()
        LimsFraction = pool.get('lims.fraction')
        LimsEntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        fraction = LimsFraction(Transaction().context['active_id'])

        results_report_ids = []
        details = LimsEntryDetailAnalysis.search([
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


class LimsSampleResultsReport(Wizard):
    'Sample Results Report'
    __name__ = 'lims.sample.results_report'

    start = StateAction('lims.act_lims_results_report')

    def do_start(self, action):
        pool = Pool()
        LimsSample = pool.get('lims.sample')
        LimsEntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        sample = LimsSample(Transaction().context['active_id'])

        results_report_ids = []
        details = LimsEntryDetailAnalysis.search([
            ('sample', '=', sample.id),
            ])
        if details:
            results_report_ids = [d.results_report.id for d in details
                if d.results_report]

        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', 'in', results_report_ids),
            ])
        action['name'] += ' (%s)' % sample.rec_name
        return action, {}


class LimsResultsReportSample(Wizard):
    'Results Report Sample'
    __name__ = 'lims.results_report.sample'

    start = StateAction('lims.act_lims_sample_list')

    def do_start(self, action):
        pool = Pool()
        LimsResultsReport = pool.get('lims.results_report')
        LimsNotebookLine = pool.get('lims.notebook.line')

        results_report = LimsResultsReport(Transaction().context['active_id'])

        samples_ids = []
        lines = LimsNotebookLine.search([
            ('results_report', '=', results_report.id),
            ])
        if lines:
            samples_ids = [l.fraction.sample.id for l in lines]

        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', 'in', samples_ids),
            ])
        action['name'] += ' (%s)' % results_report.rec_name
        return action, {}


class LimsResultsReportAnnulationStart(ModelView):
    'Report Annulation'
    __name__ = 'lims.results_report_annulation.start'

    annulment_reason = fields.Text('Annulment reason', required=True)


class LimsResultsReportAnnulation(Wizard):
    'Report Annulation'
    __name__ = 'lims.results_report_annulation'

    start = StateView('lims.results_report_annulation.start',
        'lims.lims_results_report_annulation_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Annul', 'annul', 'tryton-ok', default=True),
            ])
    annul = StateTransition()

    def transition_annul(self):
        LimsResultsReportVersionDetail = Pool().get(
            'lims.results_report.version.detail')

        details = LimsResultsReportVersionDetail.search([
            ('id', 'in', Transaction().context['active_ids']),
            ])
        if details:
            LimsResultsReportVersionDetail.annul_notebook_lines(details)
            LimsResultsReportVersionDetail.write(details, {
                'state': 'annulled',
                'valid': False,
                'report_cache': None,
                'report_format': None,
                'report_cache_eng': None,
                'report_format_eng': None,
                'annulment_reason': self.start.annulment_reason,
                'annulment_date': datetime.now(),
                })
        return 'end'


class LimsCountersampleStorageStart(ModelView):
    'Countersamples Storage'
    __name__ = 'lims.countersample.storage.start'

    report_date_from = fields.Date('Report date from', required=True)
    report_date_to = fields.Date('to', required=True)
    date_from = fields.Date('Date from', required=True)
    date_to = fields.Date('to', required=True)
    location_origin = fields.Many2One('stock.location', 'Origin Location',
        required=True, domain=[('type', '=', 'storage')])
    storage_force = fields.Boolean('Storage force')


class LimsCountersampleStorageEmpty(ModelView):
    'Countersamples Storage'
    __name__ = 'lims.countersample.storage.empty'


class LimsCountersampleStorageResult(ModelView):
    'Countersamples Storage'
    __name__ = 'lims.countersample.storage.result'

    location_destination = fields.Many2One('stock.location',
        'Destination Location', required=True,
        domain=[('type', '=', 'storage')])
    countersample_date = fields.Date('Storage date', required=True)
    fractions = fields.Many2Many('lims.fraction', None, None,
        'Fractions', required=True,
        domain=[('id', 'in', Eval('fraction_domain'))],
        depends=['fraction_domain'])
    fraction_domain = fields.One2Many('lims.fraction', None,
        'Fractions domain')
    shipment = fields.Many2One('stock.shipment.internal', 'Internal Shipment')


class LimsCountersampleStorage(Wizard):
    'Countersamples Storage'
    __name__ = 'lims.countersample.storage'

    start = StateView('lims.countersample.storage.start',
        'lims.lims_countersample_storage_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search', 'search', 'tryton-go-next', default=True),
            ])
    search = StateTransition()
    empty = StateView('lims.countersample.storage.empty',
        'lims.lims_countersample_storage_empty_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search again', 'start', 'tryton-go-next', default=True),
            ])
    result = StateView('lims.countersample.storage.result',
        'lims.lims_countersample_storage_result_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Storage', 'storage', 'tryton-ok', default=True),
            ])
    storage = StateTransition()
    open = StateAction('stock.act_shipment_internal_form')

    @classmethod
    def __setup__(cls):
        super(LimsCountersampleStorage, cls).__setup__()
        cls._error_messages.update({
            'reference': 'Countersamples Storage',
            })

    def default_start(self, fields):
        res = {}
        for field in ('report_date_from', 'report_date_to',
                'date_from', 'date_to'):
            if (hasattr(self.start, field) and getattr(self.start, field)):
                res[field] = getattr(self.start, field)
        for field in ('location_origin',):
            if (hasattr(self.start, field) and getattr(self.start, field)):
                res[field] = getattr(self.start, field).id
        return res

    def transition_search(self):
        pool = Pool()
        LimsFraction = pool.get('lims.fraction')
        LimsNotebookLine = pool.get('lims.notebook.line')
        f_list = []
        if self.start.storage_force is True:
            fractions = LimsFraction.search([
                ('countersample_date', '=', None),
                ('sample.date2', '>=', self.start.date_from),
                ('sample.date2', '<=', self.start.date_to),
                ('current_location', '=', self.start.location_origin.id),
                ])
            if fractions:
                for f in fractions:
                    notebook_lines_ids = (
                        self._get_fraction_notebook_lines_storage_force(f.id))
                    if not notebook_lines_ids:
                        continue
                    notebook_lines = LimsNotebookLine.search([
                        ('id', 'in', notebook_lines_ids),
                        ])
                    if not notebook_lines:
                        continue
                    f_list.append(f)

        else:
            fractions = LimsFraction.search([
                ('countersample_date', '=', None),
                ('sample.date2', '>=', self.start.date_from),
                ('sample.date2', '<=', self.start.date_to),
                ('has_results_report', '=', True),
                ('current_location', '=', self.start.location_origin.id),
                ])
            if fractions:
                for f in fractions:
                    notebook_lines_ids = self._get_fraction_notebook_lines(
                        f.id)
                    if not notebook_lines_ids:
                        continue
                    notebook_lines = LimsNotebookLine.search([
                        ('id', 'in', notebook_lines_ids),
                        ])
                    if not notebook_lines:
                        continue

                    # Check not accepted (with repetitions)
                    to_check = []
                    oks = []
                    for line in notebook_lines:
                        key = line.analysis.id
                        if not line.accepted:
                            to_check.append(key)
                        else:
                            oks.append(key)
                    to_check = list(set(to_check))
                    oks = list(set(oks))
                    if to_check:
                        for key in oks:
                            if key in to_check:
                                to_check.remove(key)
                    if len(to_check) > 0:
                        continue

                    all_results_reported = True
                    for nl in notebook_lines:
                        if not nl.accepted:
                            continue
                        if not nl.results_report:
                            all_results_reported = False
                            break
                        if not self._get_line_reported(nl,
                                self.start.report_date_from,
                                self.start.report_date_to):
                            all_results_reported = False
                            break
                    if all_results_reported:
                        f_list.append(f)
        if f_list:
            self.result.fractions = f_list
            return 'result'
        return 'empty'

    def _get_fraction_notebook_lines(self, fraction_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        Service = pool.get('lims.service')

        cursor.execute('SELECT nl.id '
            'FROM "' + NotebookLine._table + '" nl '
                'INNER JOIN "' + EntryDetailAnalysis._table + '" ad '
                'ON ad.id = nl.analysis_detail '
                'INNER JOIN "' + Service._table + '" srv '
                'ON srv.id = nl.service '
            'WHERE srv.fraction = %s '
                'AND nl.report = TRUE '
                'AND nl.annulled = FALSE',
            (fraction_id,))
        return [x[0] for x in cursor.fetchall()]

    def _get_line_reported(self, nl, date_from, date_to):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        ReportVersionDetailLine = pool.get(
            'lims.results_report.version.detail.line')
        ReportVersionDetail = pool.get('lims.results_report.version.detail')
        ReportVersion = pool.get('lims.results_report.version')

        cursor.execute('SELECT rvdl.id '
            'FROM "' + ReportVersionDetailLine._table + '" rvdl '
                'INNER JOIN "' + ReportVersionDetail._table + '" rvd '
                'ON rvd.id = rvdl.report_version_detail '
                'INNER JOIN "' + ReportVersion._table + '" rv '
                'ON rv.id = rvd.report_version '
            'WHERE rvdl.notebook_line = %s '
                'AND rv.results_report = %s '
                'AND DATE(COALESCE(rvd.write_date, rvd.create_date)) '
                'BETWEEN %s::date AND %s::date',
            (nl.id, nl.results_report.id, date_from, date_to))
        return cursor.fetchone()

    def default_result(self, fields):
        fractions = [f.id for f in self.result.fractions]
        self.result.fractions = None
        return {
            'fractions': fractions,
            'fraction_domain': fractions,
            }

    def transition_storage(self):
        LimsFraction = Pool().get('lims.fraction')

        countersample_location = self.result.location_destination
        countersample_date = self.result.countersample_date
        fractions_to_save = []
        for fraction in self.result.fractions:
            fraction.countersample_location = countersample_location
            fraction.countersample_date = countersample_date
            fraction.expiry_date = countersample_date + relativedelta(
                months=fraction.storage_time)
            fractions_to_save.append(fraction)
        LimsFraction.save(fractions_to_save)

        moves = self._get_stock_moves(self.result.fractions)
        shipment = self.create_internal_shipment(moves)
        if shipment:
            self.result.shipment = shipment
            return 'open'
        return 'end'

    def create_internal_shipment(self, moves):
        ShipmentInternal = Pool().get('stock.shipment.internal')
        shipment = self._get_internal_shipment()
        if not shipment:
            return
        shipment.moves = moves
        with Transaction().set_context(check_current_location=False):
            shipment.save()
        ShipmentInternal.wait([shipment])
        ShipmentInternal.assign_force([shipment])
        ShipmentInternal.done([shipment])
        return shipment

    def _get_internal_shipment(self):
        pool = Pool()
        User = pool.get('res.user')
        ShipmentInternal = pool.get('stock.shipment.internal')

        company = User(Transaction().user).company
        from_location = self.start.location_origin
        to_location = self.result.location_destination
        planned_date = self.result.countersample_date

        with Transaction().set_user(0, set_context=True):
            shipment = ShipmentInternal()
        shipment.reference = LimsCountersampleStorage.raise_user_error(
            'reference', raise_exception=False)
        shipment.planned_date = planned_date
        shipment.company = company
        shipment.from_location = from_location
        shipment.to_location = to_location
        shipment.state = 'draft'
        return shipment

    def _get_stock_moves(self, fractions):
        pool = Pool()
        Config = pool.get('lims.configuration')
        LimsFraction = pool.get('lims.fraction')
        User = pool.get('res.user')
        Move = pool.get('stock.move')

        config_ = Config(1)
        if config_.fraction_product:
            product = config_.fraction_product
        else:
            LimsFraction.raise_user_error('missing_fraction_product')
        company = User(Transaction().user).company

        from_location = self.start.location_origin
        to_location = self.result.location_destination
        planned_date = self.result.countersample_date

        moves = []
        for fraction in fractions:
            with Transaction().set_user(0, set_context=True):
                move = Move()
            move.product = product.id
            move.fraction = fraction.id
            move.quantity = fraction.packages_quantity
            move.uom = product.default_uom
            move.from_location = from_location
            move.to_location = to_location
            move.company = company
            move.planned_date = planned_date
            move.origin = fraction
            move.state = 'draft'
            moves.append(move)
        return moves

    def do_open(self, action):
        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', '=', self.result.shipment.id),
            ])
        return action, {}

    def transition_open(self):
        return 'end'

    def _get_fraction_notebook_lines_storage_force(self, fraction_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        Service = pool.get('lims.service')

        cursor.execute('SELECT nl.id '
            'FROM "' + NotebookLine._table + '" nl '
                'INNER JOIN "' + EntryDetailAnalysis._table + '" ad '
                'ON ad.id = nl.analysis_detail '
                'INNER JOIN "' + Service._table + '" srv '
                'ON srv.id = nl.service '
            'WHERE srv.fraction = %s ',
            (fraction_id,))
        return [x[0] for x in cursor.fetchall()]


class LimsCountersampleStorageRevertStart(ModelView):
    'Revert Countersamples Storage'
    __name__ = 'lims.countersample.storage_revert.start'

    date_from = fields.Date('Date from', required=True)
    date_to = fields.Date('Date to', required=True)
    location_origin = fields.Many2One('stock.location', 'Origin Location',
        required=True, domain=[('type', '=', 'storage')])


class LimsCountersampleStorageRevertEmpty(ModelView):
    'Revert Countersamples Storage'
    __name__ = 'lims.countersample.storage_revert.empty'


class LimsCountersampleStorageRevertResult(ModelView):
    'Revert Countersamples Storage'
    __name__ = 'lims.countersample.storage_revert.result'

    location_destination = fields.Many2One('stock.location',
        'Destination Location', required=True,
        domain=[('type', '=', 'storage')])
    fractions = fields.Many2Many('lims.fraction', None, None,
        'Fractions', required=True,
        domain=[('id', 'in', Eval('fraction_domain'))],
        depends=['fraction_domain'])
    fraction_domain = fields.One2Many('lims.fraction', None,
        'Fractions domain')
    shipment = fields.Many2One('stock.shipment.internal', 'Internal Shipment')


class LimsCountersampleStorageRevert(Wizard):
    'Revert Countersamples Storage'
    __name__ = 'lims.countersample.storage_revert'

    start = StateView('lims.countersample.storage_revert.start',
        'lims.lims_countersample_storage_revert_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search', 'search', 'tryton-go-next', default=True),
            ])
    search = StateTransition()
    empty = StateView('lims.countersample.storage_revert.empty',
        'lims.lims_countersample_storage_revert_empty_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search again', 'start', 'tryton-go-next', default=True),
            ])
    result = StateView('lims.countersample.storage_revert.result',
        'lims.lims_countersample_storage_revert_result_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Revert', 'revert', 'tryton-ok', default=True),
            ])
    revert = StateTransition()
    open = StateAction('stock.act_shipment_internal_form')

    @classmethod
    def __setup__(cls):
        super(LimsCountersampleStorageRevert, cls).__setup__()
        cls._error_messages.update({
            'reference': 'Countersamples Storage Reversion',
            })

    def default_start(self, fields):
        res = {}
        for field in ('date_from', 'date_to'):
            if (hasattr(self.start, field) and getattr(self.start, field)):
                res[field] = getattr(self.start, field)
        for field in ('location_origin',):
            if (hasattr(self.start, field) and getattr(self.start, field)):
                res[field] = getattr(self.start, field).id
        return res

    def transition_search(self):
        LimsFraction = Pool().get('lims.fraction')

        fractions = LimsFraction.search([
            ('countersample_date', '>=', self.start.date_from),
            ('countersample_date', '<=', self.start.date_to),
            ('current_location', '=', self.start.location_origin.id),
            ])
        if fractions:
            self.result.fractions = fractions
            return 'result'
        return 'empty'

    def default_result(self, fields):
        fractions = [f.id for f in self.result.fractions]
        self.result.fractions = None
        return {
            'fractions': fractions,
            'fraction_domain': fractions,
            }

    def transition_revert(self):
        LimsFraction = Pool().get('lims.fraction')

        fractions_to_save = []
        for fraction in self.result.fractions:
            fraction.countersample_location = None
            fraction.countersample_date = None
            fraction.expiry_date = None
            fractions_to_save.append(fraction)
        LimsFraction.save(fractions_to_save)

        moves = self._get_stock_moves(self.result.fractions)
        shipment = self.create_internal_shipment(moves)
        if shipment:
            self.result.shipment = shipment
            return 'open'
        return 'end'

    def create_internal_shipment(self, moves):
        ShipmentInternal = Pool().get('stock.shipment.internal')
        shipment = self._get_internal_shipment()
        if not shipment:
            return
        shipment.moves = moves
        with Transaction().set_context(check_current_location=False):
            shipment.save()
        ShipmentInternal.wait([shipment])
        ShipmentInternal.assign_force([shipment])
        ShipmentInternal.done([shipment])
        return shipment

    def _get_internal_shipment(self):
        pool = Pool()
        User = pool.get('res.user')
        Date = pool.get('ir.date')
        ShipmentInternal = pool.get('stock.shipment.internal')

        company = User(Transaction().user).company
        from_location = self.start.location_origin
        to_location = self.result.location_destination
        today = Date.today()

        with Transaction().set_user(0, set_context=True):
            shipment = ShipmentInternal()
        shipment.reference = LimsCountersampleStorageRevert.raise_user_error(
            'reference', raise_exception=False)
        shipment.planned_date = today
        shipment.company = company
        shipment.from_location = from_location
        shipment.to_location = to_location
        shipment.state = 'draft'
        return shipment

    def _get_stock_moves(self, fractions):
        pool = Pool()
        Config = pool.get('lims.configuration')
        LimsFraction = pool.get('lims.fraction')
        User = pool.get('res.user')
        Date = pool.get('ir.date')
        Move = pool.get('stock.move')

        config_ = Config(1)
        if config_.fraction_product:
            product = config_.fraction_product
        else:
            LimsFraction.raise_user_error('missing_fraction_product')
        company = User(Transaction().user).company

        from_location = self.start.location_origin
        to_location = self.result.location_destination
        today = Date.today()

        moves = []
        for fraction in fractions:
            with Transaction().set_user(0, set_context=True):
                move = Move()
            move.product = product.id
            move.fraction = fraction.id
            move.quantity = fraction.packages_quantity
            move.uom = product.default_uom
            move.from_location = from_location
            move.to_location = to_location
            move.company = company
            move.planned_date = today
            move.origin = fraction
            move.state = 'draft'
            moves.append(move)
        return moves

    def do_open(self, action):
        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', '=', self.result.shipment.id),
            ])
        return action, {}

    def transition_open(self):
        return 'end'


class LimsCountersampleDischargeStart(ModelView):
    'Countersamples Discharge'
    __name__ = 'lims.countersample.discharge.start'

    expiry_date_from = fields.Date('Expiry date from', required=True)
    expiry_date_to = fields.Date('to', required=True)
    date_from = fields.Date('Date from', required=True)
    date_to = fields.Date('to', required=True)
    location_origin = fields.Many2One('stock.location', 'Origin Location',
        required=True, domain=[('type', '=', 'storage')])


class LimsCountersampleDischargeEmpty(ModelView):
    'Countersamples Discharge'
    __name__ = 'lims.countersample.discharge.empty'


class LimsCountersampleDischargeResult(ModelView):
    'Countersamples Discharge'
    __name__ = 'lims.countersample.discharge.result'

    location_destination = fields.Many2One('stock.location',
        'Destination Location', required=True,
        domain=[('type', '=', 'lost_found')])
    discharge_date = fields.Date('Discharge date', required=True)
    fractions = fields.Many2Many('lims.fraction', None, None,
        'Fractions', required=True,
        domain=[('id', 'in', Eval('fraction_domain'))],
        depends=['fraction_domain'])
    fraction_domain = fields.One2Many('lims.fraction', None,
        'Fractions domain')
    shipment = fields.Many2One('stock.shipment.internal', 'Internal Shipment')


class LimsCountersampleDischarge(Wizard):
    'Countersamples Discharge'
    __name__ = 'lims.countersample.discharge'

    start = StateView('lims.countersample.discharge.start',
        'lims.lims_countersample_discharge_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search', 'search', 'tryton-go-next', default=True),
            ])
    search = StateTransition()
    empty = StateView('lims.countersample.discharge.empty',
        'lims.lims_countersample_discharge_empty_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search again', 'start', 'tryton-go-next', default=True),
            ])
    result = StateView('lims.countersample.discharge.result',
        'lims.lims_countersample_discharge_result_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Discharge', 'discharge', 'tryton-ok', default=True),
            ])
    discharge = StateTransition()
    open = StateAction('stock.act_shipment_internal_form')

    @classmethod
    def __setup__(cls):
        super(LimsCountersampleDischarge, cls).__setup__()
        cls._error_messages.update({
            'reference': 'Countersamples Discharge',
            })

    def default_start(self, fields):
        res = {}
        for field in ('expiry_date_from', 'expiry_date_to',
                'date_from', 'date_to'):
            if (hasattr(self.start, field) and getattr(self.start, field)):
                res[field] = getattr(self.start, field)
        for field in ('location_origin',):
            if (hasattr(self.start, field) and getattr(self.start, field)):
                res[field] = getattr(self.start, field).id
        return res

    def transition_search(self):
        LimsFraction = Pool().get('lims.fraction')

        fractions = LimsFraction.search([
            ('discharge_date', '=', None),
            ('sample.date2', '>=', self.start.date_from),
            ('sample.date2', '<=', self.start.date_to),
            ('expiry_date', '>=', self.start.expiry_date_from),
            ('expiry_date', '<=', self.start.expiry_date_to),
            ('current_location', '=', self.start.location_origin.id),
            ])
        if fractions:
            self.result.fractions = fractions
            return 'result'
        return 'empty'

    def default_result(self, fields):
        fractions = [f.id for f in self.result.fractions]
        self.result.fractions = None
        return {
            'fractions': fractions,
            'fraction_domain': fractions,
            }

    def transition_discharge(self):
        LimsFraction = Pool().get('lims.fraction')

        discharge_date = self.result.discharge_date
        fractions_to_save = []
        for fraction in self.result.fractions:
            fraction.discharge_date = discharge_date
            fractions_to_save.append(fraction)
        LimsFraction.save(fractions_to_save)

        moves = self._get_stock_moves(self.result.fractions)
        shipment = self.create_internal_shipment(moves)
        if shipment:
            self.result.shipment = shipment
            return 'open'
        return 'end'

    def create_internal_shipment(self, moves):
        ShipmentInternal = Pool().get('stock.shipment.internal')
        shipment = self._get_internal_shipment()
        if not shipment:
            return
        shipment.moves = moves
        with Transaction().set_context(check_current_location=False):
            shipment.save()
        ShipmentInternal.wait([shipment])
        ShipmentInternal.assign_force([shipment])
        ShipmentInternal.done([shipment])
        return shipment

    def _get_internal_shipment(self):
        pool = Pool()
        User = pool.get('res.user')
        ShipmentInternal = pool.get('stock.shipment.internal')

        company = User(Transaction().user).company
        from_location = self.start.location_origin
        to_location = self.result.location_destination
        planned_date = self.result.discharge_date

        with Transaction().set_user(0, set_context=True):
            shipment = ShipmentInternal()
        shipment.reference = LimsCountersampleDischarge.raise_user_error(
            'reference', raise_exception=False)
        shipment.planned_date = planned_date
        shipment.company = company
        shipment.from_location = from_location
        shipment.to_location = to_location
        shipment.state = 'draft'
        return shipment

    def _get_stock_moves(self, fractions):
        pool = Pool()
        Config = pool.get('lims.configuration')
        LimsFraction = pool.get('lims.fraction')
        User = pool.get('res.user')
        Move = pool.get('stock.move')

        config_ = Config(1)
        if config_.fraction_product:
            product = config_.fraction_product
        else:
            LimsFraction.raise_user_error('missing_fraction_product')
        company = User(Transaction().user).company

        from_location = self.start.location_origin
        to_location = self.result.location_destination
        planned_date = self.result.discharge_date

        moves = []
        for fraction in fractions:
            with Transaction().set_user(0, set_context=True):
                move = Move()
            move.product = product.id
            move.fraction = fraction.id
            move.quantity = fraction.packages_quantity
            move.uom = product.default_uom
            move.from_location = from_location
            move.to_location = to_location
            move.company = company
            move.planned_date = planned_date
            move.origin = fraction
            move.state = 'draft'
            moves.append(move)
        return moves

    def do_open(self, action):
        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', '=', self.result.shipment.id),
            ])
        return action, {}

    def transition_open(self):
        return 'end'


class LimsFractionDischargeStart(ModelView):
    'Fractions Discharge'
    __name__ = 'lims.fraction.discharge.start'

    date_from = fields.Date('Date from', required=True)
    date_to = fields.Date('Date to', required=True)
    location_origin = fields.Many2One('stock.location', 'Origin Location',
        required=True, domain=[('type', '=', 'storage')])
    discharge_force = fields.Boolean('Discharge force')


class LimsFractionDischargeEmpty(ModelView):
    'Fractions Discharge'
    __name__ = 'lims.fraction.discharge.empty'


class LimsFractionDischargeResult(ModelView):
    'Fractions Discharge'
    __name__ = 'lims.fraction.discharge.result'

    location_destination = fields.Many2One('stock.location',
        'Destination Location', required=True,
        domain=[('type', '=', 'lost_found')])
    discharge_date = fields.Date('Discharge date', required=True)
    fractions = fields.Many2Many('lims.fraction', None, None,
        'Fractions', required=True,
        domain=[('id', 'in', Eval('fraction_domain'))],
        depends=['fraction_domain'])
    fraction_domain = fields.One2Many('lims.fraction', None,
        'Fractions domain')
    shipment = fields.Many2One('stock.shipment.internal', 'Internal Shipment')


class LimsFractionDischarge(Wizard):
    'Fractions Discharge'
    __name__ = 'lims.fraction.discharge'

    start = StateView('lims.fraction.discharge.start',
        'lims.lims_fraction_discharge_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search', 'search', 'tryton-go-next', default=True),
            ])
    search = StateTransition()
    empty = StateView('lims.fraction.discharge.empty',
        'lims.lims_fraction_discharge_empty_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search again', 'start', 'tryton-go-next', default=True),
            ])
    result = StateView('lims.fraction.discharge.result',
        'lims.lims_fraction_discharge_result_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Discharge', 'discharge', 'tryton-ok', default=True),
            ])
    discharge = StateTransition()
    open = StateAction('stock.act_shipment_internal_form')

    @classmethod
    def __setup__(cls):
        super(LimsFractionDischarge, cls).__setup__()
        cls._error_messages.update({
            'reference': 'Fractions Discharge',
            })

    def default_start(self, fields):
        res = {}
        for field in ('date_from', 'date_to'):
            if (hasattr(self.start, field) and getattr(self.start, field)):
                res[field] = getattr(self.start, field)
        for field in ('location_origin',):
            if (hasattr(self.start, field) and getattr(self.start, field)):
                res[field] = getattr(self.start, field).id
        return res

    def transition_search(self):
        LimsFraction = Pool().get('lims.fraction')
        if self.start.discharge_force is True:
            fractions = LimsFraction.search([
                ('discharge_date', '=', None),
                ('sample.date2', '>=', self.start.date_from),
                ('sample.date2', '<=', self.start.date_to),
                ('current_location', '=', self.start.location_origin.id),
                ])
        else:
            fractions = LimsFraction.search([
                ('discharge_date', '=', None),
                ('sample.date2', '>=', self.start.date_from),
                ('sample.date2', '<=', self.start.date_to),
                ('has_results_report', '=', False),
                ('current_location', '=', self.start.location_origin.id),
                ])

        if fractions:
            self.result.fractions = fractions
            return 'result'
        return 'empty'

    def default_result(self, fields):
        fractions = [f.id for f in self.result.fractions]
        self.result.fractions = None
        return {
            'fractions': fractions,
            'fraction_domain': fractions,
            }

    def transition_discharge(self):
        LimsFraction = Pool().get('lims.fraction')

        discharge_date = self.result.discharge_date
        fractions_to_save = []
        for fraction in self.result.fractions:
            fraction.discharge_date = discharge_date
            fractions_to_save.append(fraction)
        LimsFraction.save(fractions_to_save)

        moves = self._get_stock_moves(self.result.fractions)
        shipment = self.create_internal_shipment(moves)
        if shipment:
            self.result.shipment = shipment
            return 'open'
        return 'end'

    def create_internal_shipment(self, moves):
        ShipmentInternal = Pool().get('stock.shipment.internal')
        shipment = self._get_internal_shipment()
        if not shipment:
            return
        shipment.moves = moves
        with Transaction().set_context(check_current_location=False):
            shipment.save()
        ShipmentInternal.wait([shipment])
        ShipmentInternal.assign_force([shipment])
        ShipmentInternal.done([shipment])
        return shipment

    def _get_internal_shipment(self):
        pool = Pool()
        User = pool.get('res.user')
        ShipmentInternal = pool.get('stock.shipment.internal')

        company = User(Transaction().user).company
        from_location = self.start.location_origin
        to_location = self.result.location_destination
        planned_date = self.result.discharge_date

        with Transaction().set_user(0, set_context=True):
            shipment = ShipmentInternal()
        shipment.reference = LimsFractionDischarge.raise_user_error(
            'reference', raise_exception=False)
        shipment.planned_date = planned_date
        shipment.company = company
        shipment.from_location = from_location
        shipment.to_location = to_location
        shipment.state = 'draft'
        return shipment

    def _get_stock_moves(self, fractions):
        pool = Pool()
        Config = pool.get('lims.configuration')
        LimsFraction = pool.get('lims.fraction')
        User = pool.get('res.user')
        Move = pool.get('stock.move')

        config_ = Config(1)
        if config_.fraction_product:
            product = config_.fraction_product
        else:
            LimsFraction.raise_user_error('missing_fraction_product')
        company = User(Transaction().user).company

        from_location = self.start.location_origin
        to_location = self.result.location_destination
        planned_date = self.result.discharge_date

        moves = []
        for fraction in fractions:
            with Transaction().set_user(0, set_context=True):
                move = Move()
            move.product = product.id
            move.fraction = fraction.id
            move.quantity = fraction.packages_quantity
            move.uom = product.default_uom
            move.from_location = from_location
            move.to_location = to_location
            move.company = company
            move.planned_date = planned_date
            move.origin = fraction
            move.state = 'draft'
            moves.append(move)
        return moves

    def do_open(self, action):
        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', '=', self.result.shipment.id),
            ])
        return action, {}

    def transition_open(self):
        return 'end'


class LimsFractionDischargeRevertStart(ModelView):
    'Revert Fractions Discharge'
    __name__ = 'lims.fraction.discharge_revert.start'

    date_from = fields.Date('Date from', required=True)
    date_to = fields.Date('Date to', required=True)
    location_origin = fields.Many2One('stock.location', 'Origin Location',
        required=True, domain=[('type', '=', 'lost_found')])


class LimsFractionDischargeRevertEmpty(ModelView):
    'Revert Fractions Discharge'
    __name__ = 'lims.fraction.discharge_revert.empty'


class LimsFractionDischargeRevertResult(ModelView):
    'Revert Fractions Discharge'
    __name__ = 'lims.fraction.discharge_revert.result'

    location_destination = fields.Many2One('stock.location',
        'Destination Location', required=True,
        domain=[('type', '=', 'storage')])
    fractions = fields.Many2Many('lims.fraction', None, None,
        'Fractions', required=True,
        domain=[('id', 'in', Eval('fraction_domain'))],
        depends=['fraction_domain'])
    fraction_domain = fields.One2Many('lims.fraction', None,
        'Fractions domain')
    shipment = fields.Many2One('stock.shipment.internal', 'Internal Shipment')


class LimsFractionDischargeRevert(Wizard):
    'Revert Fractions Discharge'
    __name__ = 'lims.fraction.discharge_revert'

    start = StateView('lims.fraction.discharge_revert.start',
        'lims.lims_fraction_discharge_revert_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search', 'search', 'tryton-go-next', default=True),
            ])
    search = StateTransition()
    empty = StateView('lims.fraction.discharge_revert.empty',
        'lims.lims_fraction_discharge_revert_empty_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search again', 'start', 'tryton-go-next', default=True),
            ])
    result = StateView('lims.fraction.discharge_revert.result',
        'lims.lims_fraction_discharge_revert_result_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Revert', 'revert', 'tryton-ok', default=True),
            ])
    revert = StateTransition()
    open = StateAction('stock.act_shipment_internal_form')

    @classmethod
    def __setup__(cls):
        super(LimsFractionDischargeRevert, cls).__setup__()
        cls._error_messages.update({
            'reference': 'Fractions Discharge Reversion',
            })

    def default_start(self, fields):
        res = {}
        for field in ('date_from', 'date_to'):
            if (hasattr(self.start, field) and getattr(self.start, field)):
                res[field] = getattr(self.start, field)
        for field in ('location_origin',):
            if (hasattr(self.start, field) and getattr(self.start, field)):
                res[field] = getattr(self.start, field).id
        return res

    def transition_search(self):
        LimsFraction = Pool().get('lims.fraction')

        fractions = LimsFraction.search([
            ('discharge_date', '>=', self.start.date_from),
            ('discharge_date', '<=', self.start.date_to),
            ('current_location', '=', self.start.location_origin.id),
            ])
        if fractions:
            self.result.fractions = fractions
            return 'result'
        return 'empty'

    def default_result(self, fields):
        fractions = [f.id for f in self.result.fractions]
        self.result.fractions = None
        return {
            'fractions': fractions,
            'fraction_domain': fractions,
            }

    def transition_revert(self):
        LimsFraction = Pool().get('lims.fraction')

        fractions_to_save = []
        for fraction in self.result.fractions:
            fraction.discharge_date = None
            fractions_to_save.append(fraction)
        LimsFraction.save(fractions_to_save)

        moves = self._get_stock_moves(self.result.fractions)
        shipment = self.create_internal_shipment(moves)
        if shipment:
            self.result.shipment = shipment
            return 'open'
        return 'end'

    def create_internal_shipment(self, moves):
        ShipmentInternal = Pool().get('stock.shipment.internal')
        shipment = self._get_internal_shipment()
        if not shipment:
            return
        shipment.moves = moves
        with Transaction().set_context(check_current_location=False):
            shipment.save()
        ShipmentInternal.wait([shipment])
        ShipmentInternal.assign_force([shipment])
        ShipmentInternal.done([shipment])
        return shipment

    def _get_internal_shipment(self):
        pool = Pool()
        User = pool.get('res.user')
        Date = pool.get('ir.date')
        ShipmentInternal = pool.get('stock.shipment.internal')

        company = User(Transaction().user).company
        from_location = self.start.location_origin
        to_location = self.result.location_destination
        today = Date.today()

        with Transaction().set_user(0, set_context=True):
            shipment = ShipmentInternal()
        shipment.reference = LimsFractionDischargeRevert.raise_user_error(
            'reference', raise_exception=False)
        shipment.planned_date = today
        shipment.company = company
        shipment.from_location = from_location
        shipment.to_location = to_location
        shipment.state = 'draft'
        return shipment

    def _get_stock_moves(self, fractions):
        pool = Pool()
        Config = pool.get('lims.configuration')
        LimsFraction = pool.get('lims.fraction')
        User = pool.get('res.user')
        Date = pool.get('ir.date')
        Move = pool.get('stock.move')

        config_ = Config(1)
        if config_.fraction_product:
            product = config_.fraction_product
        else:
            LimsFraction.raise_user_error('missing_fraction_product')
        company = User(Transaction().user).company

        from_location = self.start.location_origin
        to_location = self.result.location_destination
        today = Date.today()

        moves = []
        for fraction in fractions:
            with Transaction().set_user(0, set_context=True):
                move = Move()
            move.product = product.id
            move.fraction = fraction.id
            move.quantity = fraction.packages_quantity
            move.uom = product.default_uom
            move.from_location = from_location
            move.to_location = to_location
            move.company = company
            move.planned_date = today
            move.origin = fraction
            move.state = 'draft'
            moves.append(move)
        return moves

    def do_open(self, action):
        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', '=', self.result.shipment.id),
            ])
        return action, {}

    def transition_open(self):
        return 'end'


class LimsCreateSampleStart(ModelView):
    'Create Sample'
    __name__ = 'lims.create_sample.start'

    party = fields.Many2One('party.party', 'Party')
    date = fields.DateTime('Date', required=True)
    producer = fields.Many2One('lims.sample.producer', 'Producer company',
        domain=[('party', '=', Eval('party'))], depends=['party'])
    sample_client_description = fields.Char(
        'Product described by the client', required=True)
    sample_client_description_eng = fields.Char(
        'Product described by the client (English)')
    product_type = fields.Many2One('lims.product.type', 'Product type',
        required=True, states={'readonly': Bool(Eval('services'))},
        domain=[('id', 'in', Eval('product_type_domain'))],
        depends=['product_type_domain', 'services'])
    product_type_domain = fields.Many2Many('lims.product.type', None, None,
        'Product type domain')
    matrix = fields.Many2One('lims.matrix', 'Matrix', required=True,
        states={'readonly': Bool(Eval('services'))},
        domain=[('id', 'in', Eval('matrix_domain'))],
        depends=['matrix_domain', 'services'])
    matrix_domain = fields.Many2Many('lims.matrix', None, None,
        'Matrix domain')
    fraction_state = fields.Many2One('lims.packaging.integrity',
        'Package state', required=True)
    package_type = fields.Many2One('lims.packaging.type', 'Package type',
        required=True)
    packages_quantity = fields.Integer('Packages quantity', required=True)
    size = fields.Float('Size')
    size_uom = fields.Many2One('product.uom', 'Size UoM',
        domain=[('category.lims_only_available', '=', True)])
    restricted_entry = fields.Boolean('Restricted entry',
        states={'readonly': True})
    zone = fields.Many2One('lims.zone', 'Zone', required=True)
    trace_report = fields.Boolean('Trace report')
    report_comments = fields.Text('Report comments', translate=True)
    comments = fields.Text('Comments')
    variety = fields.Many2One('lims.variety', 'Variety',
        domain=[('varieties.matrix', '=', Eval('matrix'))],
        depends=['matrix'])
    labels = fields.Text('Labels')
    fraction_type = fields.Many2One('lims.fraction.type', 'Fraction type',
        required=True)
    storage_location = fields.Many2One('stock.location', 'Storage location',
        required=True, domain=[('type', '=', 'storage')])
    storage_time = fields.Integer('Storage time (in months)', required=True)
    weight = fields.Float('Weight')
    weight_uom = fields.Many2One('product.uom', 'Weight UoM',
        domain=[('category.lims_only_available', '=', True)])
    shared = fields.Boolean('Shared')
    analysis_domain = fields.Function(fields.Many2Many('lims.analysis',
        None, None, 'Analysis domain'), 'on_change_with_analysis_domain')
    services = fields.One2Many('lims.create_sample.service', None, 'Services',
        required=True, depends=['analysis_domain', 'product_type', 'matrix'],
        context={
            'analysis_domain': Eval('analysis_domain'),
            'product_type': Eval('product_type'), 'matrix': Eval('matrix'),
            })

    @staticmethod
    def default_date():
        return datetime.now()

    @staticmethod
    def default_restricted_entry():
        return False

    @staticmethod
    def default_zone():
        Entry = Pool().get('lims.entry')
        entry_id = Transaction().context.get('active_id', None)
        if entry_id:
            entry = Entry(entry_id)
            if entry.party.entry_zone:
                return entry.party.entry_zone.id

    @staticmethod
    def default_trace_report():
        return False

    @staticmethod
    def default_storage_time():
        return 3

    @staticmethod
    def default_product_type_domain():
        cursor = Transaction().connection.cursor()
        LimsTypification = Pool().get('lims.typification')

        cursor.execute('SELECT DISTINCT(product_type) '
            'FROM "' + LimsTypification._table + '" '
            'WHERE valid')
        res = cursor.fetchall()
        if not res:
            return []
        return [x[0] for x in res]

    @fields.depends('product_type', 'matrix', 'matrix_domain')
    def on_change_product_type(self):
        matrix_domain = []
        matrix = None
        if self.product_type:
            matrix_domain = self.on_change_with_matrix_domain()
            if len(matrix_domain) == 1:
                matrix = matrix_domain[0]
        self.matrix_domain = matrix_domain
        self.matrix = matrix

    @fields.depends('product_type')
    def on_change_with_matrix_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        LimsTypification = Pool().get('lims.typification')

        if not self.product_type:
            return []

        cursor.execute('SELECT DISTINCT(matrix) '
            'FROM "' + LimsTypification._table + '" '
            'WHERE product_type = %s '
            'AND valid',
            (self.product_type.id,))
        res = cursor.fetchall()
        if not res:
            return []
        return [x[0] for x in res]

    @fields.depends('product_type', 'matrix')
    def on_change_with_analysis_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsTypification = pool.get('lims.typification')
        LimsCalculatedTypification = pool.get('lims.typification.calculated')
        LimsAnalysis = pool.get('lims.analysis')

        if not self.product_type or not self.matrix:
            return []

        cursor.execute('SELECT DISTINCT(analysis) '
            'FROM "' + LimsTypification._table + '" '
            'WHERE product_type = %s '
                'AND matrix = %s '
                'AND valid',
            (self.product_type.id, self.matrix.id))
        typified_analysis = [a[0] for a in cursor.fetchall()]
        if not typified_analysis:
            return []

        cursor.execute('SELECT id '
            'FROM "' + LimsAnalysis._table + '" '
            'WHERE type = \'analysis\' '
                'AND behavior IN (\'normal\', \'internal_relation\') '
                'AND disable_as_individual IS TRUE '
                'AND state = \'active\'')
        disabled_analysis = [a[0] for a in cursor.fetchall()]
        if disabled_analysis:
            typified_analysis = list(set(typified_analysis)
                - set(disabled_analysis))

        cursor.execute('SELECT DISTINCT(analysis) '
            'FROM "' + LimsCalculatedTypification._table + '" '
            'WHERE product_type = %s '
                'AND matrix = %s',
            (self.product_type.id, self.matrix.id))
        typified_sets_groups = [a[0] for a in cursor.fetchall()]

        cursor.execute('SELECT id '
            'FROM "' + LimsAnalysis._table + '" '
            'WHERE behavior = \'additional\' '
                'AND state = \'active\'')
        additional_analysis = [a[0] for a in cursor.fetchall()]

        return typified_analysis + typified_sets_groups + additional_analysis

    @fields.depends('product_type', 'matrix', 'zone')
    def on_change_with_restricted_entry(self, name=None):
        return (self.product_type and self.product_type.restricted_entry
                and self.matrix and self.matrix.restricted_entry
                and self.zone and self.zone.restricted_entry)

    @fields.depends('fraction_type', 'package_type', 'fraction_state')
    def on_change_fraction_type(self):
        if self.fraction_type:
            if (not self.package_type and
                    self.fraction_type.default_package_type):
                self.package_type = self.fraction_type.default_package_type
            if (not self.fraction_state and
                    self.fraction_type.default_fraction_state):
                self.fraction_state = self.fraction_type.default_fraction_state

    @fields.depends('fraction_type', 'storage_location')
    def on_change_with_storage_time(self, name=None):
        if self.fraction_type and self.fraction_type.max_storage_time:
            return self.fraction_type.max_storage_time
        if self.storage_location and self.storage_location.storage_time:
            return self.storage_location.storage_time
        return 3

    @fields.depends('shared', 'services')
    def on_change_with_shared(self, name=None):
        shared = self.shared
        if not self.services:
            return shared

        labs = []
        for s in self.services:
            if not s.analysis:
                continue
            if s.analysis.type == 'analysis':
                if s.analysis.behavior == 'additional':
                    continue
                labs.append(s.laboratory.id)
            else:
                labs.extend(self._get_included_labs(s.analysis))
        if len(set(labs)) > 1:
            return True
        return False

    def _get_included_labs(self, analysis):
        childs = []
        if analysis.included_analysis:
            for included in analysis.included_analysis:
                if included.included_analysis.type == 'analysis':
                    childs.append(included.laboratory.id)
                childs.extend(self._get_included_labs(
                    included.included_analysis))
        return childs


class LimsCreateSampleService(ModelView):
    'Service'
    __name__ = 'lims.create_sample.service'

    analysis = fields.Many2One('lims.analysis', 'Analysis/Set/Group',
        required=True, domain=[
            ('id', 'in', Eval('context', {}).get('analysis_domain', [])),
            ])
    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        domain=[('id', 'in', Eval('laboratory_domain'))],
        states={'required': Bool(Eval('laboratory_domain'))},
        depends=['laboratory_domain'])
    laboratory_domain = fields.Many2Many('lims.laboratory',
        None, None, 'Laboratory domain')
    method = fields.Many2One('lims.lab.method', 'Method',
        domain=[('id', 'in', Eval('method_domain'))],
        states={'required': Bool(Eval('method_domain'))},
        depends=['method_domain'])
    method_domain = fields.Many2Many('lims.lab.method',
        None, None, 'Method domain')
    device = fields.Many2One('lims.lab.device', 'Device',
        domain=[('id', 'in', Eval('device_domain'))],
        states={'required': Bool(Eval('device_domain'))},
        depends=['device_domain'])
    device_domain = fields.Many2Many('lims.lab.device',
        None, None, 'Device domain')
    urgent = fields.Boolean('Urgent')
    priority = fields.Integer('Priority')
    report_date = fields.Date('Date agreed for result')
    divide = fields.Boolean('Divide')

    @staticmethod
    def default_urgent():
        return False

    @staticmethod
    def default_priority():
        return 0

    @staticmethod
    def default_divide():
        return False

    @fields.depends('analysis')
    def on_change_analysis(self):
        analysis_id = self.analysis.id if self.analysis else None

        product_type_id = Transaction().context.get('product_type', None)
        matrix_id = Transaction().context.get('matrix', None)

        laboratory_id = None
        laboratory_domain = []
        method_id = None
        method_domain = []
        device_id = None
        device_domain = []
        if analysis_id:
            laboratory_domain = self._get_laboratory_domain(analysis_id)
            if len(laboratory_domain) == 1:
                laboratory_id = laboratory_domain[0]

            method_domain = self._get_method_domain(analysis_id,
                product_type_id, matrix_id)
            if len(method_domain) == 1:
                method_id = method_domain[0]

            if laboratory_id:
                device_domain = self._get_device_domain(analysis_id,
                    laboratory_id)
                if len(device_domain) == 1:
                    device_id = device_domain[0]

        self.laboratory_domain = laboratory_domain
        self.laboratory = laboratory_id
        self.method_domain = method_domain
        self.method = method_id
        self.device_domain = device_domain
        self.device = device_id

    @staticmethod
    def _get_laboratory_domain(analysis_id):
        cursor = Transaction().connection.cursor()
        LimsAnalysisLaboratory = Pool().get('lims.analysis-laboratory')

        cursor.execute('SELECT DISTINCT(laboratory) '
            'FROM "' + LimsAnalysisLaboratory._table + '" '
            'WHERE analysis = %s',
            (analysis_id,))
        res = cursor.fetchall()
        if not res:
            return []
        return [x[0] for x in res]

    @staticmethod
    def _get_method_domain(analysis_id, product_type_id, matrix_id):
        cursor = Transaction().connection.cursor()
        LimsTypification = Pool().get('lims.typification')

        cursor.execute('SELECT DISTINCT(method) '
            'FROM "' + LimsTypification._table + '" '
            'WHERE product_type = %s '
                'AND matrix = %s '
                'AND analysis = %s '
                'AND valid',
            (product_type_id, matrix_id, analysis_id))
        res = cursor.fetchall()
        if not res:
            return []
        return [x[0] for x in res]

    @staticmethod
    def _get_device_domain(analysis_id, laboratory_id):
        cursor = Transaction().connection.cursor()
        LimsAnalysisDevice = Pool().get('lims.analysis.device')

        cursor.execute('SELECT DISTINCT(device) '
            'FROM "' + LimsAnalysisDevice._table + '" '
            'WHERE analysis = %s  '
                'AND laboratory = %s '
                'AND by_default = TRUE',
            (analysis_id, laboratory_id))
        res = cursor.fetchall()
        if not res:
            return []
        return [x[0] for x in res]


class LimsCreateSample(Wizard):
    'Create Sample'
    __name__ = 'lims.create_sample'

    start = StateView('lims.create_sample.start',
        'lims.lims_create_sample_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Create', 'create_', 'tryton-ok', default=True),
            ])
    create_ = StateTransition()

    def default_start(self, fields):
        LimsEntry = Pool().get('lims.entry')
        entry = LimsEntry(Transaction().context['active_id'])
        return {
            'party': entry.party.id,
            }

    def transition_create_(self):
        # TODO: Remove logs
        logger = logging.getLogger(__name__)
        logger.info('-- LimsCreateSample().transition_create_():INIT --')
        LimsSample = Pool().get('lims.sample')

        entry_id = Transaction().context['active_id']
        samples_defaults = self._get_samples_defaults(entry_id)
        logger.info('.. LimsSample.create(..)')
        sample, = LimsSample.create(samples_defaults)

        if self.start.sample_client_description_eng:
            with Transaction().set_context(language='en'):
                sample_eng = LimsSample(sample.id)
                sample_eng.sample_client_description = (
                    self.start.sample_client_description_eng)
                sample_eng.save()

        labels_list = self._get_labels_list(self.start.labels)
        if len(labels_list) > 1:
            logger.info('.. LimsSample.copy(..): %s' % (len(labels_list) - 1))
            for label in labels_list[1:]:
                LimsSample.copy([sample], default={
                    'label': label,
                    })

        logger.info('-- LimsCreateSample().transition_create_():END --')
        return 'end'

    def _get_samples_defaults(self, entry_id):
        producer_id = self.start.producer.id if self.start.producer else None
        size_uom_id = self.start.size_uom.id if self.start.size_uom else None
        zone_id = self.start.zone.id if self.start.zone else None
        variety_id = self.start.variety.id if self.start.variety else None
        weight_uom_id = (self.start.weight_uom.id if self.start.weight_uom
            else None)

        # services data
        services_defaults = []
        for service in self.start.services:
            service_defaults = {
                'analysis': service.analysis.id,
                'laboratory': (service.laboratory.id if service.laboratory
                    else None),
                'method': service.method.id if service.method else None,
                'device': service.device.id if service.device else None,
                'urgent': service.urgent,
                'priority': service.priority,
                'report_date': service.report_date,
                'divide': service.divide,
                }
            services_defaults.append(service_defaults)

        # samples data
        samples_defaults = []
        labels_list = self._get_labels_list(self.start.labels)
        for label in labels_list[:1]:
            # fraction data
            fraction_defaults = {
                'type': self.start.fraction_type.id,
                'storage_location': self.start.storage_location.id,
                'storage_time': self.start.storage_time,
                'weight': self.start.weight,
                'weight_uom': weight_uom_id,
                'packages_quantity': self.start.packages_quantity,
                'size': self.start.size,
                'size_uom': size_uom_id,
                'shared': self.start.shared,
                'package_type': self.start.package_type.id,
                'fraction_state': self.start.fraction_state.id,
                'services': [('create', services_defaults)],
                }

            sample_defaults = {
                'entry': entry_id,
                'date': self.start.date,
                'producer': producer_id,
                'sample_client_description': (
                    self.start.sample_client_description),
                'product_type': self.start.product_type.id,
                'matrix': self.start.matrix.id,
                'package_state': self.start.fraction_state.id,
                'package_type': self.start.package_type.id,
                'packages_quantity': self.start.packages_quantity,
                'size': self.start.size,
                'size_uom': size_uom_id,
                'restricted_entry': self.start.restricted_entry,
                'zone': zone_id,
                'trace_report': self.start.trace_report,
                'report_comments': self.start.report_comments,
                'comments': self.start.comments,
                'variety': variety_id,
                'label': label,
                'fractions': [('create', [fraction_defaults])],
                }

            samples_defaults.append(sample_defaults)

        return samples_defaults

    def _get_labels_list(self, labels=None):
        if not labels:
            return [None]
        return labels.split('\n')


class OpenNotebookLines(Wizard):
    'Open Notebook Lines'
    __name__ = 'lims.open_notebook_lines'
    start_state = 'open_'
    open_ = StateAction('lims.act_lims_notebook_line_related1')

    def do_open_(self, action):
        Notebook = Pool().get('lims.notebook')

        notebook = Notebook.browse(Transaction().context['active_ids'])[0]
        action['pyson_domain'] = PYSONEncoder().encode(
            [('notebook', 'in', Transaction().context['active_ids'])])

        action['name'] = \
            '%s - %s - %s - %s - %s' % (notebook.fraction.number,
                notebook.party.name, notebook.product_type.description,
                notebook.matrix.description, notebook.label)
        return action, {}


class LimsCreateAnalysisProduct(Wizard):
    'Create Analysis Product'
    __name__ = 'lims.create_analysis_product'

    start = StateTransition()

    def transition_start(self):
        pool = Pool()
        Template = pool.get('product.template')
        Product = pool.get('product.product')
        Analysis = pool.get('lims.analysis')
        Template = pool.get('product.template')
        TemplateCategory = pool.get('product.template-product.category')
        Uom = pool.get('product.uom')
        Distribution = pool.get('analytic_account.distribution')
        Lang = pool.get('ir.lang')
        Config = pool.get('lims.configuration')

        config_ = Config(1)
        uom, = Uom.search([('symbol', '=', 'x 1 u')])

        analysis = Analysis(Transaction().context['active_id'])

        if (analysis.type == 'analysis' and
                analysis.behavior == 'internal_relation'):
            return 'end'

        if analysis.product:
            return 'end'

        template = Template()

        template.name = analysis.description
        template.type = 'service'
        template.list_price = Decimal('1.0')
        template.cost_price = Decimal('1.0')
        template.salable = True
        template.default_uom = uom
        template.sale_uom = uom
        template.account_category = config_.analysis_product_category.id
        template.accounts_category = True

        if analysis.behavior != 'additional':
            if analysis.type != 'group':
                laboratory = analysis.laboratories[0].laboratory
            else:
                laboratory = analysis.included_analysis[0].laboratory

            analytic_distribution, = Distribution.search([
                ('code', '=', laboratory.code)
                ])

            template.analytic_distribution = analytic_distribution

        template.save()

        template_category = TemplateCategory()
        template_category.template = template.id
        template_category.category = config_.analysis_product_category.id
        template_category.save()

        product = Product()
        product.template = template.id
        product.code = analysis.code
        product.save()

        analysis.product = product
        analysis.save()

        lang, = Lang.search([
                ('code', '=', 'en'),
                ], limit=1)
        with Transaction().set_context(language=lang.code):
            template = Template(template.id)
            template.name = Analysis(analysis.id).description
            template.save()

        return 'end'


class LimsChangeInvoicePartyStart(ModelView):
    'Change Invoice Party'
    __name__ = 'lims.entry.change_invoice_party.start'

    invoice_party_domain = fields.Many2Many('party.party', None, None,
        'Invoice party domain')
    invoice_party = fields.Many2One('party.party', 'Invoice party',
        domain=[('id', 'in', Eval('invoice_party_domain'))],
        depends=['invoice_party_domain'], required=True)


class LimsChangeInvoicePartyError(ModelView):
    'Change Invoice Party'
    __name__ = 'lims.entry.change_invoice_party.error'


class LimsChangeInvoiceParty(Wizard):
    'Change Invoice Party'
    __name__ = 'lims.entry.change_invoice_party'

    start_state = 'check'
    check = StateTransition()
    error = StateView('lims.entry.change_invoice_party.error',
        'lims.lims_change_invoice_party_error_view_form', [
            Button('Cancel', 'end', 'tryton-cancel', default=True),
            ])
    start = StateView('lims.entry.change_invoice_party.start',
        'lims.lims_change_invoice_party_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Change', 'change', 'tryton-ok', default=True),
            ])
    change = StateTransition()

    def transition_check(self):
        pool = Pool()
        Entry = pool.get('lims.entry')
        Service = pool.get('lims.service')
        InvoiceLine = pool.get('account.invoice.line')

        entry = Entry(Transaction().context['active_id'])

        if entry.state == 'draft':
            return 'end'

        services = Service.search([
            ('entry', '=', entry.id),
            ])
        if not services:
            return 'end'

        for s in services:
            invoiced_lines = InvoiceLine.search([
                ('origin', '=', 'lims.service,%s' % s.id),
                ('invoice', '!=', None),
                ])
            if invoiced_lines:
                return 'error'

        return 'start'

    def default_start(self, fields):
        Entry = Pool().get('lims.entry')

        entry = Entry(Transaction().context['active_id'])

        invoice_party_domain = entry.on_change_with_invoice_party_domain()
        invoice_party = None
        if len(invoice_party_domain) == 1:
            invoice_party = invoice_party_domain[0]
        return {
            'invoice_party_domain': invoice_party_domain,
            'invoice_party': invoice_party,
            }

    def transition_change(self):
        pool = Pool()
        Entry = pool.get('lims.entry')
        Service = pool.get('lims.service')
        InvoiceLine = pool.get('account.invoice.line')
        InvoiceContacts = pool.get('lims.entry.invoice_contacts')
        ReportContacts = pool.get('lims.entry.report_contacts')
        AcknowledgmentContacts = pool.get('lims.entry.acknowledgment_contacts')

        entry = Entry(Transaction().context['active_id'])

        lines_to_change = []
        services = Service.search([
            ('entry', '=', entry.id),
            ])
        for s in services:
            invoiced_lines = InvoiceLine.search([
                ('origin', '=', 'lims.service,%s' % s.id),
                ])
            for l in invoiced_lines:
                line = InvoiceLine(l.id)
                line.party = self.start.invoice_party.id
                lines_to_change.append(line)
        if lines_to_change:
            InvoiceLine.save(lines_to_change)

        if entry.invoice_party != entry.party:
            entry_contacts = InvoiceContacts.search([
                ('entry', '=', entry.id),
                ('contact.party', '=', entry.invoice_party.id),
                ])
            if entry_contacts:
                InvoiceContacts.delete(entry_contacts)
            entry_contacts = ReportContacts.search([
                ('entry', '=', entry.id),
                ('contact.party', '=', entry.invoice_party.id),
                ])
            if entry_contacts:
                ReportContacts.delete(entry_contacts)
            entry_contacts = AcknowledgmentContacts.search([
                ('entry', '=', entry.id),
                ('contact.party', '=', entry.invoice_party.id),
                ])
            if entry_contacts:
                AcknowledgmentContacts.delete(entry_contacts)
        entry.invoice_party = self.start.invoice_party.id
        entry.save()

        return 'end'


class OpenTypifications(Wizard):
    'Open Typifications'
    __name__ = 'lims.scope_version.open_typifications'

    start_state = 'open_'
    open_ = StateAction('lims.act_lims_typification_readonly_list')

    def do_open_(self, action):
        cursor = Transaction().connection.cursor()
        LimsTechnicalScopeVersionLine = Pool().get(
            'lims.technical.scope.version.line')

        cursor.execute('SELECT typification '
            'FROM "' + LimsTechnicalScopeVersionLine._table + '" '
            'WHERE version = %s', (Transaction().context['active_id'],))
        t_ids = [x[0] for x in cursor.fetchall()]

        action['pyson_domain'] = PYSONEncoder().encode([('id', 'in', t_ids)])
        return action, {}


class AddTypificationsStart(ModelView):
    'Add Typifications'
    __name__ = 'lims.scope_version.add_typifications.start'

    typifications = fields.Many2Many('lims.typification.readonly',
        None, None, 'Typifications', required=True)


class AddTypifications(Wizard):
    'Add Typifications'
    __name__ = 'lims.scope_version.add_typifications'

    start = StateView('lims.scope_version.add_typifications.start',
        'lims.scope_version_add_typifications_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Add', 'add', 'tryton-ok', default=True),
            ])
    add = StateTransition()

    def transition_add(self):
        LimsTechnicalScopeVersion = Pool().get('lims.technical.scope.version')

        scope_version = LimsTechnicalScopeVersion(
            Transaction().context['active_id'])
        LimsTechnicalScopeVersion.write([scope_version], {
            'version_lines': [('remove',
                [t.id for t in self.start.typifications])],
            })
        LimsTechnicalScopeVersion.write([scope_version], {
            'version_lines': [('add',
                [t.id for t in self.start.typifications])],
            })
        return 'end'


class RemoveTypificationsStart(ModelView):
    'Remove Typifications'
    __name__ = 'lims.scope_version.remove_typifications.start'

    typifications = fields.Many2Many('lims.typification.readonly',
        None, None, 'Typifications', required=True,
        domain=[('id', 'in', Eval('typifications_domain'))],
        depends=['typifications_domain'])
    typifications_domain = fields.One2Many('lims.typification.readonly',
        None, 'Typifications domain')


class RemoveTypifications(Wizard):
    'Remove Typifications'
    __name__ = 'lims.scope_version.remove_typifications'

    start = StateView('lims.scope_version.remove_typifications.start',
        'lims.scope_version_remove_typifications_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Remove', 'remove', 'tryton-ok', default=True),
            ])
    remove = StateTransition()

    def default_start(self, fields):
        cursor = Transaction().connection.cursor()
        LimsTechnicalScopeVersionLine = Pool().get(
            'lims.technical.scope.version.line')

        cursor.execute('SELECT typification '
            'FROM "' + LimsTechnicalScopeVersionLine._table + '" '
            'WHERE version = %s', (Transaction().context['active_id'],))
        t_ids = [x[0] for x in cursor.fetchall()]

        return {'typifications_domain': t_ids}

    def transition_remove(self):
        LimsTechnicalScopeVersion = Pool().get('lims.technical.scope.version')

        scope_version = LimsTechnicalScopeVersion(
            Transaction().context['active_id'])
        LimsTechnicalScopeVersion.write([scope_version], {
            'version_lines': [('remove',
                [t.id for t in self.start.typifications])],
            })
        return 'end'


class ChangeEstimatedDaysForResultsStart(ModelView):
    'Change Estimated Days For Results'
    __name__ = 'lims.change_results_estimated_waiting.start'

    date_from = fields.Date('Confirmation date From', required=True)
    date_to = fields.Date('Confirmation date To', required=True)
    methods = fields.Many2Many('lims.lab.method',
        None, None, 'Methods', required=True)
    results_estimated_waiting = fields.Integer('Days to add')


class ChangeEstimatedDaysForResults(Wizard):
    'Change Estimated Days For Results'
    __name__ = 'lims.change_results_estimated_waiting'

    start = StateView('lims.change_results_estimated_waiting.start',
        'lims.change_results_estimated_waiting_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Change', 'change', 'tryton-ok', default=True),
            ])
    change = StateTransition()

    def transition_change(self):
        LimsNotebookLine = Pool().get('lims.notebook.line')

        methods_ids = [m.id for m in self.start.methods]
        notebook_lines = LimsNotebookLine.search([
            ('method', 'in', methods_ids),
            ('analysis_detail.confirmation_date', '>=', self.start.date_from),
            ('analysis_detail.confirmation_date', '<=', self.start.date_to),
            ('accepted', '=', False),
            ])
        if notebook_lines:
            lines_to_save = []
            for line in notebook_lines:
                line.results_estimated_waiting = ((
                    line.results_estimated_waiting or 0)
                    + self.start.results_estimated_waiting)
                lines_to_save.append(line)
            LimsNotebookLine.save(lines_to_save)
        return 'end'
