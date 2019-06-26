# -*- coding: utf-8 -*-
# This file is part of lims module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import logging
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from trytond.model import Workflow, ModelView, ModelSQL, fields, Unique
from trytond.wizard import Wizard, StateTransition, StateView, StateAction, \
    Button
from trytond.report import Report
from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.pyson import PYSONEncoder, Eval, Equal, Bool, Not, Or
from .results_report import get_print_date

__all__ = ['Planification', 'PlanificationTechnician',
    'PlanificationTechnicianDetail', 'PlanificationDetail',
    'PlanificationServiceDetail', 'NotebookLineFraction',
    'PlanificationServiceDetailLaboratoryProfessional',
    'PlanificationAnalysis', 'PlanificationFraction', 'FractionReagent',
    'LabProfessionalMethod', 'LabProfessionalMethodRequalification',
    'LabProfessionalMethodRequalificationSupervisor',
    'LabProfessionalMethodRequalificationControl', 'BlindSample',
    'RelateTechniciansStart', 'RelateTechniciansResult',
    'RelateTechniciansDetail1', 'RelateTechniciansDetail2',
    'RelateTechniciansDetail3', 'RelateTechnicians', 'UnlinkTechniciansStart',
    'UnlinkTechniciansDetail1', 'UnlinkTechnicians', 'AddFractionControlStart',
    'AddFractionControl', 'AddFractionRMBMZStart', 'AddFractionRMBMZ',
    'AddFractionBREStart', 'AddFractionBRE', 'AddFractionMRTStart',
    'AddFractionMRT', 'RemoveControlStart', 'RemoveControl',
    'AddAnalysisStart', 'AddAnalysis', 'SearchFractionsNext',
    'SearchFractionsDetail', 'SearchFractions', 'SearchPlannedFractionsStart',
    'SearchPlannedFractionsNext', 'SearchPlannedFractionsDetail',
    'SearchPlannedFractions', 'CreateFractionControlStart',
    'CreateFractionControl', 'ReleaseFractionStart', 'ReleaseFractionEmpty',
    'ReleaseFractionResult', 'ReleaseFraction', 'QualificationSituations',
    'QualificationSituation', 'QualificationAction', 'QualificationSituation2',
    'QualificationSituation3', 'QualificationSituation4',
    'TechniciansQualification', 'ReplaceTechnicianStart', 'ReplaceTechnician',
    'LoadServices', 'PlanificationSequenceReport',
    'PlanificationWorksheetAnalysisReport',
    'PlanificationWorksheetMethodReport', 'PlanificationWorksheetReport',
    'PendingServicesUnplannedReport', 'PendingServicesUnplannedSpreadsheet',
    'PrintBlindSampleReportStart', 'PrintBlindSampleReport',
    'BlindSampleReport', 'PrintPendingServicesUnplannedReportStart',
    'PrintPendingServicesUnplannedReport',
    'PlanificationSequenceAnalysisReport']


class Planification(Workflow, ModelSQL, ModelView):
    'Planification'
    __name__ = 'lims.planification'
    _rec_name = 'code'

    code = fields.Char('Code', select=True, readonly=True)
    date = fields.Date('Date', readonly=True)
    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        required=True)
    analysis = fields.Many2Many('lims.planification-analysis',
        'planification', 'analysis', 'Analysis/Sets/Groups',
        states={'readonly': Not(Bool(Equal(Eval('state'), 'draft')))},
        context={'date_from': Eval('date_from'), 'date_to': Eval('date_to'),
            'calculate': Bool(Equal(Eval('state'), 'draft'))},
        domain=['OR', ('id', 'in', Eval('analysis')), [
            ('id', 'in', Eval('analysis_domain'))]],
        depends=['state', 'date_from', 'date_to', 'analysis_domain'])
    analysis_domain = fields.Function(fields.Many2Many('lims.analysis',
        None, None, 'Analysis domain'),
        'on_change_with_analysis_domain')
    technicians = fields.One2Many('lims.planification.technician',
        'planification', 'Technicians', depends=['method_domain',
        'technicians_domain'])
    date_from = fields.Date('Date from', depends=['state'], required=True,
        states={'readonly': Not(Bool(Equal(Eval('state'), 'draft')))})
    date_to = fields.Date('Date to', depends=['state'], required=True,
        states={'readonly': Not(Bool(Equal(Eval('state'), 'draft')))})
    start_date = fields.Date('Start date', depends=['state'],
        states={'readonly': Bool(Equal(Eval('state'), 'confirmed'))})
    details = fields.One2Many('lims.planification.detail',
        'planification', 'Fractions to plan',
        states={'readonly': Not(Bool(Equal(Eval('state'), 'draft')))},
        depends=['state'])
    controls = fields.Many2Many('lims.planification-fraction',
        'planification', 'fraction', 'Controls', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('preplanned', 'Pre-Planned'),
        ('confirmed', 'Confirmed'),
        ('not_executed', 'Not executed'),
        ], 'State', required=True, readonly=True)
    waiting_process = fields.Boolean('Waiting process')
    method_domain = fields.Function(fields.One2Many('lims.lab.method',
        None, 'Method domain'),
        'on_change_with_method_domain')
    technicians_domain = fields.Function(fields.One2Many(
        'lims.laboratory.professional', None, 'Technicians domain'),
        'on_change_with_technicians_domain')
    comments = fields.Text('Comments')

    @classmethod
    def __setup__(cls):
        super(Planification, cls).__setup__()
        cls._order.insert(0, ('code', 'DESC'))
        cls._transitions |= set((
            ('draft', 'preplanned'),
            ('preplanned', 'confirmed'),
            ('confirmed', 'not_executed'),
            ))
        cls._buttons.update({
            'add_analysis': {
                'readonly': (Eval('state') != 'draft'),
                },
            'search_fractions': {
                'readonly': (Eval('state') != 'draft'),
                },
            'search_planned_fractions': {
                'readonly': (Eval('state') != 'draft'),
                },
            'preplan': {
                'invisible': (Eval('state') != 'draft'),
                },
            'confirm': {
                'invisible': (Eval('state') != 'preplanned'),
                },
            'release_controls': {
                'invisible': (Eval('state') != 'confirmed'),
                },
            'relate_technicians': {
                'readonly': (Eval('state') != 'preplanned'),
                },
            'unlink_technicians': {
                'readonly': (Eval('state') != 'preplanned'),
                },
            'replace_technician': {
                'readonly': (Eval('state') != 'confirmed'),
                },
            'add_fraction_con': {
                'readonly': (Eval('state') != 'preplanned'),
                },
            'add_fraction_rm_bmz': {
                'readonly': (Eval('state') != 'preplanned'),
                },
            'add_fraction_bre': {
                'readonly': (Eval('state') != 'preplanned'),
                },
            'add_fraction_mrt': {
                'readonly': (Eval('state') != 'preplanned'),
                },
            'remove_control': {
                'readonly': (Eval('state') != 'preplanned'),
                },
            })
        cls._error_messages.update({
            'not_start_date': 'The planification must have a start date',
            'invalid_start_date': 'The start date must be after "%s"',
            'no_technician': ('The following fractions have not a responsible '
                'technician:%s'),
            'waiting_process': ('Planification "%s" is still waiting for '
                'processing'),
            'delete_planification': ('You can not delete planification "%s" '
                'because it is not in draft or pre-planned state'),
            'copy_planification': ('You can not copy planifications'),
            })

    @staticmethod
    def default_state():
        return 'draft'

    @staticmethod
    def default_waiting_process():
        return False

    @staticmethod
    def default_date():
        Date = Pool().get('ir.date')
        return Date.today()

    @staticmethod
    def default_laboratory():
        return Transaction().context.get('laboratory', None)

    @fields.depends('laboratory', 'state')
    def on_change_with_analysis_domain(self, name=None):
        if not self.laboratory or self.state != 'draft':
            return []
        return self._get_analysis_domain(self.laboratory)

    @staticmethod
    def _get_analysis_domain(laboratory):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        AnalysisLaboratory = pool.get('lims.analysis-laboratory')
        Analysis = pool.get('lims.analysis')

        if not laboratory:
            return []

        cursor.execute('SELECT al.analysis '
            'FROM "' + AnalysisLaboratory._table + '" al '
                'INNER JOIN "' + Analysis._table + '" a '
                'ON a.id = al.analysis '
            'WHERE al.laboratory = %s '
                'AND a.behavior != \'internal_relation\'',
            (laboratory.id,))
        analysis_sets_list = [a[0] for a in cursor.fetchall()]

        groups_list = []
        cursor.execute('SELECT id '
            'FROM "' + Analysis._table + '" '
            'WHERE type = \'group\'')
        groups_list_ids = [g[0] for g in cursor.fetchall()]
        for group_id in groups_list_ids:
            if Planification._get_group_available(group_id,
                    analysis_sets_list):
                groups_list.append(group_id)

        return analysis_sets_list + groups_list

    @staticmethod
    def _get_group_available(group_id, analysis_sets_list):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        AnalysisIncluded = pool.get('lims.analysis.included')
        Analysis = pool.get('lims.analysis')

        cursor.execute('SELECT ia.included_analysis, a.type '
            'FROM "' + AnalysisIncluded._table + '" ia '
                'INNER JOIN "' + Analysis._table + '" a '
                'ON a.id = ia.included_analysis '
            'WHERE ia.analysis = %s '
                'AND a.behavior != \'internal_relation\'',
            (group_id,))
        included_analysis = cursor.fetchall()
        if not included_analysis:
            return False
        for analysis in included_analysis:
            if (analysis[1] != 'group' and analysis[0] not in
                    analysis_sets_list):
                return False
            if (analysis[1] == 'group' and not
                    Planification._get_group_available(analysis[0],
                    analysis_sets_list)):
                return False
        return True

    @classmethod
    def create(cls, vlist):
        pool = Pool()
        Config = pool.get('lims.configuration')
        Sequence = pool.get('ir.sequence')

        vlist = [x.copy() for x in vlist]
        config = Config(1)
        for values in vlist:
            values['code'] = Sequence.get_id(
                config.planification_sequence.id)
        return super(Planification, cls).create(vlist)

    @classmethod
    def check_delete(cls, planifications):
        for planification in planifications:
            if planification.state not in ['draft', 'preplanned']:
                cls.raise_user_error('delete_planification',
                    (planification.rec_name,))

    @classmethod
    def delete(cls, planifications):
        cls.check_delete(planifications)
        super(Planification, cls).delete(planifications)

    @classmethod
    def copy(cls, planifications, default=None):
        cls.raise_user_error('copy_planification')

    @classmethod
    @ModelView.button_action('lims.wiz_lims_add_analysis')
    def add_analysis(cls, planifications):
        pass

    @classmethod
    @ModelView.button_action('lims.wiz_lims_search_fractions')
    def search_fractions(cls, planifications):
        pass

    @classmethod
    @ModelView.button_action('lims.wiz_lims_search_planned_fractions')
    def search_planned_fractions(cls, planifications):
        pass

    @classmethod
    @ModelView.button
    @Workflow.transition('preplanned')
    def preplan(cls, planifications):
        for planification in planifications:
            planification.check_start_date()

    @classmethod
    @ModelView.button_action('lims.wiz_lims_technicians_qualification')
    def confirm(cls, planifications):
        for planification in planifications:
            planification.check_start_date()
            planification.check_technicians()

    def check_start_date(self):
        if not self.start_date:
            self.raise_user_error('not_start_date')
        for detail in self.details:
            if detail.fraction.sample.date2 > self.start_date:
                self.raise_user_error('invalid_start_date',
                        (detail.fraction.sample.date2,))

    def check_technicians(self):
        fractions = {}
        for detail in self.details:
            for service_detail in detail.details:
                if not service_detail.staff_responsible:
                    key = (detail.fraction.id,
                        service_detail.notebook_line.method.id)
                    if key not in fractions:
                        fractions[key] = '%s (%s)' % (detail.fraction.rec_name,
                            service_detail.notebook_line.method.code)
        if fractions:
            sorted_fractions = sorted(list(fractions.values()), key=lambda x: x)
            self.raise_user_error('no_technician',
                ('\n' + '\n'.join(sorted_fractions) + '\n',))

    @classmethod
    def process_waiting_planifications(cls):
        '''
        Cron - Process Waiting Planifications
        '''
        logger = logging.getLogger('lims_planification')

        planifications = cls.search([
            ('waiting_process', '=', True),
            ], order=[('id', 'ASC')])
        if planifications:
            logger.info('Cron - Processing planifications:INIT')
            for planification in planifications:
                if planification.state == 'confirmed':
                    cls.do_confirm([planification])
                elif planification.state == 'not_executed':
                    cls.do_release_controls([planification])
            logger.info('Cron - Processing planifications:END')

    @classmethod
    def do_confirm(cls, planifications):
        for planification in planifications:
            planification.update_laboratory_notebook()
            planification.update_analysis_detail()
            if planification.waiting_process:
                planification.waiting_process = False
                planification.save()

    def update_laboratory_notebook(self):
        pool = Pool()
        PlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')
        NotebookLine = pool.get('lims.notebook.line')

        notebook_lines = []
        service_details = PlanificationServiceDetail.search([
            ('detail.planification', '=', self.id),
            ('notebook_line', '!=', None),
            ])
        for service_detail in service_details:
            notebook_line = NotebookLine(
                service_detail.notebook_line.id)
            notebook_line.start_date = self.start_date
            notebook_line.laboratory_professionals = [p.id
                for p in service_detail.staff_responsible]
            notebook_line.planification = self.id
            if not service_detail.is_control:
                notebook_line.controls = [f.id
                    for f in self.controls]
            notebook_lines.append(notebook_line)
        if notebook_lines:
            NotebookLine.save(notebook_lines)

    def update_analysis_detail(self):
        pool = Pool()
        PlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        analysis_detail_ids = []
        service_details = PlanificationServiceDetail.search([
            ('detail.planification', '=', self.id),
            ('notebook_line.analysis_detail', '!=', None),
            ])
        for service_detail in service_details:
            analysis_detail_ids.append(
                service_detail.notebook_line.analysis_detail.id)

        analysis_details = EntryDetailAnalysis.search([
            ('id', 'in', analysis_detail_ids),
            ])
        if analysis_details:
            EntryDetailAnalysis.write(analysis_details, {
                'state': 'planned',
                })

    @classmethod
    @ModelView.button
    @Workflow.transition('not_executed')
    def release_controls(cls, planifications):
        Config = Pool().get('lims.configuration')
        process_background = Config(1).planification_process_background

        for planification in planifications:
            # Check if is still waiting for confirmation
            if planification.waiting_process:
                cls.raise_user_error('waiting_process',
                    (planification.code,))
            if process_background:
                planification.waiting_process = True
                planification.save()
        if not process_background:
            cls.do_release_controls(planifications)

    @classmethod
    def do_release_controls(cls, planifications):
        for planification in planifications:
            planification.re_update_laboratory_notebook()
            planification.re_update_analysis_detail()
            planification.unlink_controls()
            if planification.waiting_process:
                planification.waiting_process = False
                planification.save()

    def re_update_laboratory_notebook(self):
        NotebookLine = Pool().get('lims.notebook.line')
        for detail in self.details:
            for service_detail in detail.details:
                if service_detail.is_control and service_detail.notebook_line:
                    notebook_line = NotebookLine(
                        service_detail.notebook_line.id)
                    notebook_line.start_date = None
                    notebook_line.laboratory_professionals = []
                    notebook_line.planification = None
                    notebook_line.controls = []
                    notebook_line.save()

    def re_update_analysis_detail(self):
        EntryDetailAnalysis = Pool().get('lims.entry.detail.analysis')
        analysis_detail_ids = []
        for detail in self.details:
            for service_detail in detail.details:
                if (service_detail.is_control and
                        service_detail.notebook_line and
                        service_detail.notebook_line.analysis_detail):
                    analysis_detail_ids.append(
                        service_detail.notebook_line.analysis_detail.id)
        analysis_details = EntryDetailAnalysis.search([
            ('id', 'in', analysis_detail_ids),
            ])
        if analysis_details:
            EntryDetailAnalysis.write(analysis_details, {
                'state': 'unplanned',
                })

    def unlink_controls(self):
        pool = Pool()
        PlanificationFraction = pool.get('lims.planification-fraction')
        PlanificationDetail = pool.get('lims.planification.detail')

        controls = PlanificationFraction.search([
            ('planification', '=', self.id),
            ])
        if controls:
            PlanificationFraction.delete(controls)

        controls_details = PlanificationDetail.search([
            ('planification', '=', self.id),
            ('details.is_control', '=', True),
            ])
        if controls_details:
            PlanificationDetail.delete(controls_details)

    @fields.depends('analysis')
    def on_change_with_method_domain(self, name=None):
        methods = []
        if self.analysis:
            for a in self.analysis:
                if a.methods:
                    methods.extend([m.id for m in a.methods])
        return methods

    @fields.depends('laboratory')
    def on_change_with_technicians_domain(self, name=None):
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
            ])
        if not professionals:
            return []
        return [p.id for p in professionals]

    @classmethod
    @ModelView.button_action('lims.wiz_lims_relate_technicians')
    def relate_technicians(cls, planifications):
        pass

    @classmethod
    @ModelView.button_action('lims.wiz_lims_unlink_technicians')
    def unlink_technicians(cls, planifications):
        pass

    @classmethod
    @ModelView.button_action('lims.wiz_lims_replace_technician')
    def replace_technician(cls, planifications):
        pass

    @classmethod
    @ModelView.button_action('lims.wiz_lims_add_fraction_con')
    def add_fraction_con(cls, planifications):
        pass

    @classmethod
    @ModelView.button_action('lims.wiz_lims_add_fraction_rm_bmz')
    def add_fraction_rm_bmz(cls, planifications):
        pass

    @classmethod
    @ModelView.button_action('lims.wiz_lims_add_fraction_bre')
    def add_fraction_bre(cls, planifications):
        pass

    @classmethod
    @ModelView.button_action('lims.wiz_lims_add_fraction_mrt')
    def add_fraction_mrt(cls, planifications):
        pass

    @classmethod
    @ModelView.button_action('lims.wiz_lims_remove_control')
    def remove_control(cls, planifications):
        pass


class PlanificationTechnician(ModelSQL, ModelView):
    'Technician'
    __name__ = 'lims.planification.technician'

    planification = fields.Many2One('lims.planification', 'Planification',
        ondelete='CASCADE', select=True, required=True)
    laboratory_professional = fields.Many2One('lims.laboratory.professional',
        'Laboratory professional', required=True, domain=[
            ('id', 'in', Eval('_parent_planification',
                {}).get('technicians_domain')),
            ])
    details = fields.Function(fields.One2Many(
        'lims.planification.technician.detail', 'technician',
        'Fractions to plan'), 'get_details')

    @classmethod
    def __setup__(cls):
        super(PlanificationTechnician, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('planification_professional_uniq',
                Unique(t, t.planification, t.laboratory_professional),
                'Professionals cannot be repeated'),
            ]

    def get_details(self, name=None):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        PlanificationDetailProfessional = pool.get(
            'lims.planification.service_detail-laboratory.professional')
        PlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')
        PlanificationDetail = pool.get('lims.planification.detail')
        NotebookLine = pool.get('lims.notebook.line')
        Fraction = pool.get('lims.fraction')
        LabMethod = pool.get('lims.lab.method')

        cursor.execute('SELECT DISTINCT(f.number, nl.analysis_origin, '
                'm.code||\' - \'||m.name) '
            'FROM "' + PlanificationDetailProfessional._table + '" sdp '
                'INNER JOIN "' + PlanificationServiceDetail._table + '" sd '
                'ON sd.id = sdp.detail '
                'INNER JOIN "' + PlanificationDetail._table + '" d '
                'ON d.id = sd.detail '
                'INNER JOIN "' + NotebookLine._table + '" nl '
                'ON nl.id = sd.notebook_line '
                'INNER JOIN "' + LabMethod._table + '" m '
                'ON m.id = nl.method '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON f.id = d.fraction '
            'WHERE sdp.professional = %s '
                'AND d.planification = %s',
            (self.laboratory_professional.id, self.planification.id))

        fractions = []
        for d in cursor.fetchall():
            r = d[0].split(',')
            fractions.append({
                'fraction': str(r[0][1:]),
                'analysis_origin': str(r[1]).replace('"', ''),
                'method': str(','.join(r[2:])[:-1].replace('"', '')),
                })
        return fractions


class PlanificationTechnicianDetail(ModelView):
    'Technician Detail'
    __name__ = 'lims.planification.technician.detail'

    fraction = fields.Char('Fraction')
    analysis_origin = fields.Char('Analysis origin')
    method = fields.Char('Method')


class PlanificationDetail(ModelSQL, ModelView):
    'Fraction to Plan'
    __name__ = 'lims.planification.detail'

    planification = fields.Many2One('lims.planification', 'Planification',
        ondelete='CASCADE', select=True, required=True)
    fraction = fields.Many2One('lims.fraction', 'Fraction', required=True)
    service_analysis = fields.Many2One('lims.analysis', 'Service',
        required=True)
    fraction_type = fields.Function(fields.Many2One('lims.fraction.type',
        'Fraction type'), 'get_fraction_field',
        searcher='search_fraction_field')
    label = fields.Function(fields.Char('Label'), 'get_fraction_field',
        searcher='search_fraction_field')
    product_type = fields.Function(fields.Many2One('lims.product.type',
        'Product type'), 'get_fraction_field')
    matrix = fields.Function(fields.Many2One('lims.matrix', 'Matrix'),
        'get_fraction_field')
    details = fields.One2Many('lims.planification.service_detail',
        'detail', 'Planification detail', states={'readonly': True})
    urgent = fields.Function(fields.Boolean('Urgent'), 'get_service_field')
    priority = fields.Function(fields.Integer('Priority'), 'get_service_field')
    report_date = fields.Function(fields.Date('Date agreed for result'),
        'get_service_field')
    comments = fields.Function(fields.Text('Comments'), 'get_fraction_field')
    icon = fields.Function(fields.Char("Icon"), 'get_icon')

    @classmethod
    def __setup__(cls):
        super(PlanificationDetail, cls).__setup__()
        cls._order.insert(0, ('fraction', 'ASC'))
        cls._order.insert(1, ('service_analysis', 'ASC'))

    @classmethod
    def get_fraction_field(cls, details, names):
        result = {}
        for name in names:
            result[name] = {}
            if (name == 'label' or name == 'comments'):
                for d in details:
                    result[name][d.id] = getattr(d.fraction, name, None)
            elif name == 'fraction_type':
                for d in details:
                    field = getattr(d.fraction, 'type', None)
                    result[name][d.id] = field.id if field else None
            else:
                for d in details:
                    field = getattr(d.fraction, name, None)
                    result[name][d.id] = field.id if field else None
        return result

    @classmethod
    def search_fraction_field(cls, name, clause):
        if name == 'fraction_type':
            name = 'type'
        return [('fraction.' + name,) + tuple(clause[1:])]

    @classmethod
    def get_service_field(cls, details, names):
        result = {}
        for name in names:
            result[name] = {}
            if name == 'urgent':
                for d in details:
                    result[name][d.id] = False
            elif name == 'priority':
                for d in details:
                    result[name][d.id] = 0
            else:
                for d in details:
                    result[name][d.id] = None
        for d in details:
            if d.fraction and d.service_analysis:
                for service in d.fraction.services:
                    if service.analysis == d.service_analysis:
                        for name in names:
                            result[name][d.id] = getattr(service, name)
        return result

    def get_icon(self, name):
        if self.comments:
            return 'lims-blue'
        return 'lims-white'


class PlanificationServiceDetail(ModelSQL, ModelView):
    'Planification Detail'
    __name__ = 'lims.planification.service_detail'

    detail = fields.Many2One('lims.planification.detail', 'Planification',
        ondelete='CASCADE', select=True, required=True)
    planification = fields.Function(fields.Many2One('lims.planification',
        'Planification'), 'get_planification', searcher='search_planification')
    notebook_line = fields.Many2One('lims.notebook.line', 'Notebook line',
        required=True)
    staff_responsible = fields.Many2Many(
        'lims.planification.service_detail-laboratory.professional', 'detail',
        'professional', 'Laboratory professionals')
    is_control = fields.Boolean('Is Control')
    is_replanned = fields.Boolean('Is Replanned')
    planned_service = fields.Many2One('lims.analysis', 'Planned service')
    repetition = fields.Function(fields.Integer('Repetition'),
        'get_repetition')

    @staticmethod
    def default_is_control():
        return False

    @staticmethod
    def default_is_replanned():
        return False

    def get_planification(self, name=None):
        if self.detail:
            if self.detail.planification:
                return self.detail.planification.id
        return None

    @classmethod
    def search_planification(cls, name, clause):
        return [('detail.' + name,) + tuple(clause[1:])]

    def get_repetition(self, name=None):
        if self.notebook_line:
            return self.notebook_line.repetition
        return None


class PlanificationServiceDetailLaboratoryProfessional(ModelSQL):
    'Planification Detail - Laboratory Professional'
    __name__ = 'lims.planification.service_detail-laboratory.professional'
    _table = 'lims_plan_service_d-laboratory_professional'

    detail = fields.Many2One('lims.planification.service_detail',
        'Planification detail', ondelete='CASCADE', select=True,
        required=True)
    professional = fields.Many2One('lims.laboratory.professional',
        'Laboratory professional', ondelete='CASCADE', select=True,
        required=True)


class PlanificationAnalysis(ModelSQL):
    'Planification - Analysis'
    __name__ = 'lims.planification-analysis'

    planification = fields.Many2One('lims.planification', 'Planification',
        ondelete='CASCADE', select=True, required=True)
    analysis = fields.Many2One('lims.analysis', 'Analysis',
        ondelete='CASCADE', select=True, required=True)


class PlanificationFraction(ModelSQL):
    'Planification - Fraction'
    __name__ = 'lims.planification-fraction'

    planification = fields.Many2One('lims.planification', 'Planification',
        ondelete='CASCADE', select=True, required=True)
    fraction = fields.Many2One('lims.fraction', 'Fraction',
        ondelete='CASCADE', select=True, required=True)


class NotebookLineFraction(ModelSQL):
    'Laboratory Notebook Line - Fraction'
    __name__ = 'lims.notebook.line-fraction'

    notebook_line = fields.Many2One('lims.notebook.line', 'Notebook Line',
        ondelete='CASCADE', select=True, required=True)
    fraction = fields.Many2One('lims.fraction', 'Fraction',
        ondelete='CASCADE', select=True, required=True)


class FractionReagent(ModelSQL, ModelView):
    'Fraction Reagent'
    __name__ = 'lims.fraction.reagent'

    fraction = fields.Many2One('lims.fraction', 'Fraction', required=True,
        ondelete='CASCADE', select=True)
    product = fields.Many2One('product.product', 'Reagent', required=True,
        domain=[('account_category', 'in', Eval('reagent_domain'))],
        depends=['reagent_domain'])
    reagent_domain = fields.Function(fields.Many2Many('product.category',
        None, None, 'Reagent domain'), 'get_reagent_domain')
    lot = fields.Many2One('stock.lot', 'Lot',
        domain=[('product', '=', Eval('product'))],
        depends=['product'])
    quantity = fields.Function(fields.Float('Current quantity'),
        'on_change_with_quantity')
    default_uom = fields.Function(fields.Many2One('product.uom',
        'Default UOM'),
        'on_change_with_default_uom')

    @staticmethod
    def default_reagent_domain():
        Config = Pool().get('lims.configuration')
        config = Config(1)
        return config.get_reagents()

    def get_reagent_domain(self, name=None):
        return self.default_reagent_domain()

    @fields.depends('product')
    def on_change_with_quantity(self, name=None):
        pool = Pool()
        Location = pool.get('stock.location')
        Product = pool.get('product.product')
        Date = pool.get('ir.date')

        if not self.product:
            return 0
        locations = Location.search([('type', '=', 'storage')])
        with Transaction().set_context(locations=[l.id for l in locations],
                stock_date_end=Date.today()):
            product = Product(self.product.id)
        return product.quantity or 0

    @fields.depends('product')
    def on_change_with_default_uom(self, name=None):
        if self.product:
            return self.product.default_uom.id


class LabProfessionalMethod(ModelSQL, ModelView):
    'Laboratory Professional Method'
    __name__ = 'lims.lab.professional.method'

    professional = fields.Many2One('lims.laboratory.professional',
        'Professional', required=True)
    method = fields.Many2One('lims.lab.method', 'Method', required=True)
    state = fields.Selection([
        ('training', 'Training'),
        ('qualified', 'Qualified'),
        ('requalified', 'Requalified'),
        ], 'State', sort=False)
    type = fields.Selection([
        ('preparation', 'Preparation'),
        ('analytical', 'Analytical'),
        ], 'Type', sort=False)
    requalification_history = fields.One2Many(
        'lims.lab.professional.method.requalification', 'professional_method',
        'Trainings/Qualifications/Requalifications')
    determination = fields.Function(fields.Char('Determination'),
        'get_determination', searcher='search_determination')

    @classmethod
    def __setup__(cls):
        super(LabProfessionalMethod, cls).__setup__()
        cls._order.insert(0, ('professional', 'ASC'))
        cls._order.insert(1, ('method', 'ASC'))
        t = cls.__table__()
        cls._sql_constraints += [
            ('professional_method_type_uniq',
                Unique(t, t.professional, t.method, t.type),
                'The method already exists for this professional'),
            ]

    def get_determination(self, name=None):
        if self.method:
            return self.method.determination
        return None

    @classmethod
    def search_determination(cls, name, clause):
        return [('method.' + name,) + tuple(clause[1:])]


class LabProfessionalMethodRequalification(ModelSQL, ModelView):
    'Laboratory Professional Method Requalification'
    __name__ = 'lims.lab.professional.method.requalification'
    _table = 'lims_lab_pro_method_req'

    professional_method = fields.Many2One('lims.lab.professional.method',
        'Professional Method', ondelete='CASCADE', select=True, required=True)
    type = fields.Selection([
        ('training', 'Training'),
        ('qualification', 'Qualification'),
        ('requalification', 'Requalification'),
        ], 'Type', sort=False)
    date = fields.Date('Date', required=True)
    last_execution_date = fields.Date('Last execution Date')
    supervisors = fields.One2Many(
        'lims.lab.professional.method.requalification.supervisor',
        'method_requalification', 'Supervisors')
    controls = fields.One2Many(
        'lims.lab.professional.method.requalification.control',
        'method_requalification', 'Controls')


class LabProfessionalMethodRequalificationSupervisor(ModelSQL, ModelView):
    'Laboratory Professional Method Requalification Supervisor'
    __name__ = 'lims.lab.professional.method.requalification.supervisor'
    _table = 'lims_lab_pro_method_req_supervisor'

    method_requalification = fields.Many2One(
        'lims.lab.professional.method.requalification',
        'Professional method requalification', ondelete='CASCADE',
        select=True, required=True)
    supervisor = fields.Many2One('lims.laboratory.professional', 'Supervisor',
        required=True)


class LabProfessionalMethodRequalificationControl(ModelSQL, ModelView):
    'Laboratory Professional Method Requalification Control'
    __name__ = 'lims.lab.professional.method.requalification.control'
    _table = 'lims_lab_pro_method_req_control'

    method_requalification = fields.Many2One(
        'lims.lab.professional.method.requalification',
        'Professional method requalification', ondelete='CASCADE',
        select=True, required=True)
    control = fields.Many2One('lims.fraction', 'Control',
        required=True)


class BlindSample(ModelSQL, ModelView):
    'Blind Sample'
    __name__ = 'lims.blind_sample'

    line = fields.Many2One('lims.notebook.line', 'Line', required=True,
        readonly=True, ondelete='CASCADE', select=True)
    entry = fields.Many2One('lims.entry', 'Entry', readonly=True)
    sample = fields.Many2One('lims.sample', 'Sample', readonly=True)
    fraction = fields.Many2One('lims.fraction', 'Fraction', readonly=True)
    service = fields.Many2One('lims.service', 'Service', readonly=True)
    analysis = fields.Many2One('lims.analysis', 'Analysis', readonly=True)
    repetition = fields.Integer('Repetition', readonly=True)
    date = fields.Date('Date', readonly=True)
    original_line = fields.Many2One('lims.notebook.line', 'Original line')
    original_sample = fields.Many2One('lims.sample', 'Original sample',
        readonly=True)
    original_fraction = fields.Many2One('lims.fraction', 'Original fraction',
        readonly=True)
    original_repetition = fields.Integer('Repetition', readonly=True)
    min_value = fields.Char('Minimum value', readonly=True)
    max_value = fields.Char('Maximum value', readonly=True)


class RelateTechniciansStart(ModelView):
    'Relate Technicians'
    __name__ = 'lims.planification.relate_technicians.start'

    exclude_relateds = fields.Boolean('Exclude fractions already related')
    grouping = fields.Selection([
        ('none', 'None'),
        ('origin_method', 'Analysis origin and Method'),
        ('origin', 'Analysis origin'),
        ], 'Grouping', sort=False, required=True)


class RelateTechniciansResult(ModelView):
    'Relate Technicians'
    __name__ = 'lims.planification.relate_technicians.result'

    technicians = fields.Many2Many('lims.laboratory.professional',
        None, None, 'Technicians', required=True,
        domain=[('id', 'in', Eval('technicians_domain'))],
        depends=['technicians_domain'])
    technicians_domain = fields.One2Many('lims.laboratory.professional',
        None, 'Technicians domain')
    grouping = fields.Selection([
        ('none', 'None'),
        ('origin_method', 'Analysis origin and Method'),
        ('origin', 'Analysis origin'),
        ], 'Grouping', sort=False, readonly=True)
    details1 = fields.Many2Many(
        'lims.planification.relate_technicians.detail1', None, None,
        'Fractions to plan', domain=[('id', 'in', Eval('details1_domain'))],
        states={'invisible': Not(Bool(Equal(Eval('grouping'), 'none')))},
        depends=['details1_domain', 'grouping'])
    details1_domain = fields.One2Many(
        'lims.planification.relate_technicians.detail1', None,
        'Fractions domain')
    details2 = fields.Many2Many(
        'lims.planification.relate_technicians.detail2', None, None,
        'Fractions to plan', domain=[('id', 'in', Eval('details2_domain'))],
        states={
            'invisible': Not(Bool(Equal(Eval('grouping'), 'origin_method'))),
        }, depends=['details2_domain', 'grouping'])
    details2_domain = fields.One2Many(
        'lims.planification.relate_technicians.detail2', None,
        'Fractions domain')
    details3 = fields.Many2Many(
        'lims.planification.relate_technicians.detail3', None, None,
        'Fractions to plan', domain=[('id', 'in', Eval('details3_domain'))],
        states={'invisible': Not(Bool(Equal(Eval('grouping'), 'origin')))},
        depends=['details3_domain', 'grouping'])
    details3_domain = fields.One2Many(
        'lims.planification.relate_technicians.detail3', None,
        'Fractions domain')

    @fields.depends('grouping')
    def on_change_grouping(self):
        self.details1 = []
        self.details2 = []
        self.details3 = []


class RelateTechniciansDetail1(ModelSQL, ModelView):
    'Fraction Detail'
    __name__ = 'lims.planification.relate_technicians.detail1'
    _table = 'lims_planification_relate_technicians_d1'

    fraction = fields.Many2One('lims.fraction', 'Fraction')
    service_analysis = fields.Many2One('lims.analysis', 'Service')
    fraction_type = fields.Function(fields.Many2One('lims.fraction.type',
        'Fraction type'), 'get_fraction_field')
    label = fields.Function(fields.Char('Label'), 'get_fraction_field')
    session_id = fields.Integer('Session ID')

    @classmethod
    def __register__(cls, module_name):
        super(RelateTechniciansDetail1,
            cls).__register__(module_name)
        cursor = Transaction().connection.cursor()
        cursor.execute('DELETE FROM "' + cls._table + '"')

    @classmethod
    def __setup__(cls):
        super(RelateTechniciansDetail1, cls).__setup__()
        cls._order.insert(0, ('fraction', 'ASC'))
        cls._order.insert(1, ('service_analysis', 'ASC'))

    @classmethod
    def get_fraction_field(cls, details, names):
        result = {}
        for name in names:
            result[name] = {}
            if name == 'label':
                for d in details:
                    result[name][d.id] = getattr(d.fraction, name, None)
            elif name == 'fraction_type':
                for d in details:
                    field = getattr(d.fraction, 'type', None)
                    result[name][d.id] = field.id if field else None
            else:
                for d in details:
                    field = getattr(d.fraction, name, None)
                    result[name][d.id] = field.id if field else None
        return result


class RelateTechniciansDetail2(ModelSQL, ModelView):
    'Fraction Detail'
    __name__ = 'lims.planification.relate_technicians.detail2'
    _table = 'lims_planification_relate_technicians_d2'

    fraction = fields.Many2One('lims.fraction', 'Fraction')
    analysis_origin = fields.Char('Analysis origin')
    method = fields.Many2One('lims.lab.method', 'Method')
    session_id = fields.Integer('Session ID')

    @classmethod
    def __register__(cls, module_name):
        super(RelateTechniciansDetail2,
            cls).__register__(module_name)
        cursor = Transaction().connection.cursor()
        cursor.execute('DELETE FROM "' + cls._table + '"')

    @classmethod
    def __setup__(cls):
        super(RelateTechniciansDetail2, cls).__setup__()
        cls._order.insert(0, ('fraction', 'ASC'))
        cls._order.insert(1, ('analysis_origin', 'ASC'))
        cls._order.insert(2, ('method', 'ASC'))


class RelateTechniciansDetail3(ModelSQL, ModelView):
    'Fraction Detail'
    __name__ = 'lims.planification.relate_technicians.detail3'
    _table = 'lims_planification_relate_technicians_d3'

    fraction = fields.Many2One('lims.fraction', 'Fraction')
    analysis_origin = fields.Char('Analysis origin')
    session_id = fields.Integer('Session ID')

    @classmethod
    def __register__(cls, module_name):
        super(RelateTechniciansDetail3,
            cls).__register__(module_name)
        cursor = Transaction().connection.cursor()
        cursor.execute('DELETE FROM "' + cls._table + '"')

    @classmethod
    def __setup__(cls):
        super(RelateTechniciansDetail3, cls).__setup__()
        cls._order.insert(0, ('fraction', 'ASC'))
        cls._order.insert(1, ('analysis_origin', 'ASC'))


class RelateTechnicians(Wizard):
    'Relate Technicians'
    __name__ = 'lims.planification.relate_technicians'

    start = StateView('lims.planification.relate_technicians.start',
        'lims.lims_relate_technicians_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search', 'search', 'tryton-ok', default=True),
            ])
    search = StateTransition()
    result = StateView('lims.planification.relate_technicians.result',
        'lims.lims_relate_technicians_result_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Relate', 'relate', 'tryton-ok', default=True),
            ])
    relate = StateTransition()

    def default_start(self, fields):
        return {
            'exclude_relateds': True,
            'grouping': 'none',
            }

    def transition_search(self):
        planification_id = Transaction().context['active_id']

        self.result.grouping = self.start.grouping
        self.result.details1_domain = []
        self.result.details2_domain = []
        self.result.details3_domain = []

        if self.start.grouping == 'none':
            self.result.details1_domain = self._view_details1(planification_id,
                self.start.exclude_relateds)
        elif self.start.grouping == 'origin_method':
            self.result.details2_domain = self._view_details2(planification_id,
                self.start.exclude_relateds)
        elif self.start.grouping == 'origin':
            self.result.details3_domain = self._view_details3(planification_id,
                self.start.exclude_relateds)
        return 'result'

    def default_result(self, fields):
        Planification = Pool().get('lims.planification')

        planification = Planification(Transaction().context['active_id'])

        details1_domain = []
        if self.result.details1_domain:
            details1_domain = [d.id for d in self.result.details1_domain]
        details2_domain = []
        if self.result.details2_domain:
            details2_domain = [d.id for d in self.result.details2_domain]
        details3_domain = []
        if self.result.details3_domain:
            details3_domain = [d.id for d in self.result.details3_domain]

        return {
            'technicians_domain': [t.laboratory_professional.id
                for t in planification.technicians],
            'details1_domain': details1_domain,
            'details2_domain': details2_domain,
            'details3_domain': details3_domain,
            'grouping': self.start.grouping,
            }

    def _view_details1(self, planification_id, exclude_relateds):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        PlanificationDetail = pool.get(
            'lims.planification.detail')
        PlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')
        ServiceDetailProfessional = pool.get(
            'lims.planification.service_detail-laboratory.professional')
        RelateTechniciansDetail1 = pool.get(
            'lims.planification.relate_technicians.detail1')

        exclude_relateds_clause = ''
        if exclude_relateds:
            exclude_relateds_clause = (' AND sd.id NOT IN ('
                'SELECT sdp.detail '
                'FROM "' + ServiceDetailProfessional._table + '" sdp '
                    'INNER JOIN "' + PlanificationServiceDetail._table + '" sd'
                    ' ON sdp.detail = sd.id '
                    'INNER JOIN "' + PlanificationDetail._table + '" d'
                    ' ON sd.detail = d.id '
                 'WHERE d.planification = %s'
                ')' % planification_id)

        details1 = {}
        cursor.execute('SELECT d.fraction, d.service_analysis, sd.id '
            'FROM "' + PlanificationDetail._table + '" d '
                'INNER JOIN "' + PlanificationServiceDetail._table + '" sd '
                    'ON sd.detail = d.id '
            'WHERE d.planification = %s' +
            exclude_relateds_clause,
            (planification_id,))
        for x in cursor.fetchall():
            f, s = x[0], x[1]
            if (f, s) not in details1:
                details1[(f, s)] = {
                    'fraction': f,
                    'service_analysis': s,
                    }

        to_create = []
        for d in details1.values():
            to_create.append({
                'session_id': self._session_id,
                'fraction': d['fraction'],
                'service_analysis': d['service_analysis'],
                })
        return RelateTechniciansDetail1.create(to_create)

    def _view_details2(self, planification_id, exclude_relateds):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        PlanificationDetail = pool.get(
            'lims.planification.detail')
        PlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')
        ServiceDetailProfessional = pool.get(
            'lims.planification.service_detail-laboratory.professional')
        NotebookLine = pool.get(
            'lims.notebook.line')
        RelateTechniciansDetail2 = pool.get(
            'lims.planification.relate_technicians.detail2')

        exclude_relateds_clause = ''
        if exclude_relateds:
            exclude_relateds_clause = (' AND sd.id NOT IN ('
                'SELECT sdp.detail '
                'FROM "' + ServiceDetailProfessional._table + '" sdp '
                    'INNER JOIN "' + PlanificationServiceDetail._table + '" sd'
                    ' ON sdp.detail = sd.id '
                    'INNER JOIN "' + PlanificationDetail._table + '" d'
                    ' ON sd.detail = d.id '
                 'WHERE d.planification = %s'
                ')' % planification_id)

        details2 = {}
        cursor.execute('SELECT d.fraction, nl.analysis_origin, nl.method, '
                'sd.id '
            'FROM "' + PlanificationDetail._table + '" d '
                'INNER JOIN "' + PlanificationServiceDetail._table + '" sd '
                    'ON sd.detail = d.id '
                'INNER JOIN "' + NotebookLine._table + '" nl '
                    'ON sd.notebook_line = nl.id '
            'WHERE d.planification = %s' +
            exclude_relateds_clause,
            (planification_id,))
        for x in cursor.fetchall():
            f, a, m = x[0], x[1], x[2]
            if (f, a, m) not in details2:
                details2[(f, a, m)] = {
                    'fraction': f,
                    'analysis_origin': a,
                    'method': m,
                    }

        to_create = []
        for d in details2.values():
            to_create.append({
                'session_id': self._session_id,
                'fraction': d['fraction'],
                'analysis_origin': d['analysis_origin'],
                'method': d['method'],
                })
        return RelateTechniciansDetail2.create(to_create)

    def _view_details3(self, planification_id, exclude_relateds):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        PlanificationDetail = pool.get(
            'lims.planification.detail')
        PlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')
        ServiceDetailProfessional = pool.get(
            'lims.planification.service_detail-laboratory.professional')
        NotebookLine = pool.get(
            'lims.notebook.line')
        RelateTechniciansDetail3 = pool.get(
            'lims.planification.relate_technicians.detail3')

        exclude_relateds_clause = ''
        if exclude_relateds:
            exclude_relateds_clause = (' AND sd.id NOT IN ('
                'SELECT sdp.detail '
                'FROM "' + ServiceDetailProfessional._table + '" sdp '
                    'INNER JOIN "' + PlanificationServiceDetail._table + '" sd'
                    ' ON sdp.detail = sd.id '
                    'INNER JOIN "' + PlanificationDetail._table + '" d'
                    ' ON sd.detail = d.id '
                 'WHERE d.planification = %s'
                ')' % planification_id)

        details3 = {}
        cursor.execute('SELECT d.fraction, nl.analysis_origin, sd.id '
            'FROM "' + PlanificationDetail._table + '" d '
                'INNER JOIN "' + PlanificationServiceDetail._table + '" sd '
                    'ON sd.detail = d.id '
                'INNER JOIN "' + NotebookLine._table + '" nl '
                    'ON sd.notebook_line = nl.id '
            'WHERE d.planification = %s' +
            exclude_relateds_clause,
            (planification_id,))
        for x in cursor.fetchall():
            f, a = x[0], x[1]
            if (f, a) not in details3:
                details3[(f, a)] = {
                    'fraction': f,
                    'analysis_origin': a,
                    }

        to_create = []
        for d in details3.values():
            to_create.append({
                'session_id': self._session_id,
                'fraction': d['fraction'],
                'analysis_origin': d['analysis_origin'],
                })
        return RelateTechniciansDetail3.create(to_create)

    def transition_relate(self):
        pool = Pool()
        Planification = pool.get('lims.planification')
        PlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')

        planification = Planification(Transaction().context['active_id'])

        if self.start.grouping == 'none':
            details = self._get_details1(planification.id,
                self.start.exclude_relateds)
        elif self.start.grouping == 'origin_method':
            details = self._get_details2(planification.id,
                self.start.exclude_relateds)
        elif self.start.grouping == 'origin':
            details = self._get_details3(planification.id,
                self.start.exclude_relateds)
        else:
            return 'end'

        PlanificationServiceDetail.write(details, {
            'staff_responsible': [('remove',
                [t.id for t in self.result.technicians])],
            })
        PlanificationServiceDetail.write(details, {
            'staff_responsible': [('add',
                [t.id for t in self.result.technicians])],
            })
        return 'end'

    def _get_details1(self, planification_id, exclude_relateds):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        PlanificationDetail = pool.get(
            'lims.planification.detail')
        PlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')
        ServiceDetailProfessional = pool.get(
            'lims.planification.service_detail-laboratory.professional')

        exclude_relateds_clause = ''
        if exclude_relateds:
            exclude_relateds_clause = (' AND sd.id NOT IN ('
                'SELECT sdp.detail '
                'FROM "' + ServiceDetailProfessional._table + '" sdp '
                    'INNER JOIN "' + PlanificationServiceDetail._table + '" sd'
                    ' ON sdp.detail = sd.id '
                    'INNER JOIN "' + PlanificationDetail._table + '" d'
                    ' ON sd.detail = d.id '
                 'WHERE d.planification = %s'
                ')' % planification_id)

        details = []
        for detail in self.result.details1:
            cursor.execute('SELECT sd.id '
                'FROM "' + PlanificationDetail._table + '" d '
                    'INNER JOIN "' + PlanificationServiceDetail._table + '" sd'
                        ' ON sd.detail = d.id '
                'WHERE d.planification = %s '
                    'AND d.fraction = %s '
                    'AND d.service_analysis = %s' +
                    exclude_relateds_clause,
                (planification_id, detail.fraction.id,
                    detail.service_analysis.id))
            for x in cursor.fetchall():
                details.append(x[0])

        return PlanificationServiceDetail.browse(details)

    def _get_details2(self, planification_id, exclude_relateds):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        PlanificationDetail = pool.get(
            'lims.planification.detail')
        PlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')
        ServiceDetailProfessional = pool.get(
            'lims.planification.service_detail-laboratory.professional')
        NotebookLine = pool.get(
            'lims.notebook.line')

        exclude_relateds_clause = ''
        if exclude_relateds:
            exclude_relateds_clause = (' AND sd.id NOT IN ('
                'SELECT sdp.detail '
                'FROM "' + ServiceDetailProfessional._table + '" sdp '
                    'INNER JOIN "' + PlanificationServiceDetail._table + '" sd'
                    ' ON sdp.detail = sd.id '
                    'INNER JOIN "' + PlanificationDetail._table + '" d'
                    ' ON sd.detail = d.id '
                 'WHERE d.planification = %s'
                ')' % planification_id)

        details = []
        for detail in self.result.details2:
            cursor.execute('SELECT sd.id '
                'FROM "' + PlanificationDetail._table + '" d '
                    'INNER JOIN "' + PlanificationServiceDetail._table + '" sd'
                        ' ON sd.detail = d.id '
                    'INNER JOIN "' + NotebookLine._table + '" nl '
                        'ON sd.notebook_line = nl.id '
                'WHERE d.planification = %s '
                    'AND d.fraction = %s '
                    'AND nl.analysis_origin = %s '
                    'AND nl.method = %s' +
                    exclude_relateds_clause,
                (planification_id, detail.fraction.id,
                    detail.analysis_origin, detail.method.id))
            for x in cursor.fetchall():
                details.append(x[0])

        return PlanificationServiceDetail.browse(details)

    def _get_details3(self, planification_id, exclude_relateds):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        PlanificationDetail = pool.get(
            'lims.planification.detail')
        PlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')
        ServiceDetailProfessional = pool.get(
            'lims.planification.service_detail-laboratory.professional')
        NotebookLine = pool.get(
            'lims.notebook.line')

        exclude_relateds_clause = ''
        if exclude_relateds:
            exclude_relateds_clause = (' AND sd.id NOT IN ('
                'SELECT sdp.detail '
                'FROM "' + ServiceDetailProfessional._table + '" sdp '
                    'INNER JOIN "' + PlanificationServiceDetail._table + '" sd'
                    ' ON sdp.detail = sd.id '
                    'INNER JOIN "' + PlanificationDetail._table + '" d'
                    ' ON sd.detail = d.id '
                 'WHERE d.planification = %s'
                ')' % planification_id)

        details = []
        for detail in self.result.details3:
            cursor.execute('SELECT sd.id '
                'FROM "' + PlanificationDetail._table + '" d '
                    'INNER JOIN "' + PlanificationServiceDetail._table + '" sd'
                        ' ON sd.detail = d.id '
                    'INNER JOIN "' + NotebookLine._table + '" nl '
                        'ON sd.notebook_line = nl.id '
                'WHERE d.planification = %s '
                    'AND d.fraction = %s '
                    'AND nl.analysis_origin = %s' +
                    exclude_relateds_clause,
                (planification_id, detail.fraction.id,
                    detail.analysis_origin))
            for x in cursor.fetchall():
                details.append(x[0])

        return PlanificationServiceDetail.browse(details)


class UnlinkTechniciansStart(ModelView):
    'Unlink Technicians Start'
    __name__ = 'lims.planification.unlink_technicians.start'

    technicians = fields.Many2Many('lims.laboratory.professional',
        None, None, 'Technicians', required=True,
        domain=[('id', 'in', Eval('technicians_domain'))],
        depends=['technicians_domain'])
    technicians_domain = fields.One2Many('lims.laboratory.professional',
        None, 'Technicians domain')
    details1 = fields.Many2Many(
        'lims.planification.unlink_technicians.detail1', None, None,
        'Assigned fractions', domain=[('id', 'in', Eval('details1_domain'))],
        depends=['details1_domain'])
    details1_domain = fields.Many2Many(
        'lims.planification.unlink_technicians.detail1', None, None,
        'Fractions domain')


class UnlinkTechniciansDetail1(ModelSQL, ModelView):
    'Fraction Detail Unlink'
    __name__ = 'lims.planification.unlink_technicians.detail1'
    _table = 'lims_planification_unlink_technicians_d1'

    fraction = fields.Many2One('lims.fraction', 'Fraction')
    service_analysis = fields.Many2One('lims.analysis', 'Service')
    fraction_type = fields.Function(fields.Many2One('lims.fraction.type',
        'Fraction type'), 'get_fraction_field')
    label = fields.Function(fields.Char('Label'), 'get_fraction_field')
    session_id = fields.Integer('Session ID')

    @classmethod
    def __register__(cls, module_name):
        super(UnlinkTechniciansDetail1,
            cls).__register__(module_name)
        cursor = Transaction().connection.cursor()
        cursor.execute('DELETE FROM "' + cls._table + '"')

    @classmethod
    def __setup__(cls):
        super(UnlinkTechniciansDetail1, cls).__setup__()
        cls._order.insert(0, ('fraction', 'ASC'))
        cls._order.insert(1, ('service_analysis', 'ASC'))

    @classmethod
    def get_fraction_field(cls, details, names):
        result = {}
        for name in names:
            result[name] = {}
            if name == 'label':
                for d in details:
                    result[name][d.id] = getattr(d.fraction, name, None)
            elif name == 'fraction_type':
                for d in details:
                    field = getattr(d.fraction, 'type', None)
                    result[name][d.id] = field.id if field else None
            else:
                for d in details:
                    field = getattr(d.fraction, name, None)
                    result[name][d.id] = field.id if field else None
        return result


class UnlinkTechnicians(Wizard):
    'Unlink Technicians'
    __name__ = 'lims.planification.unlink_technicians'

    start = StateView('lims.planification.unlink_technicians.start',
        'lims.lims_unlink_technicians_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Unlink', 'unlink', 'tryton-ok', default=True),
            ])
    unlink = StateTransition()

    def default_start(self, fields):
        Planification = Pool().get('lims.planification')

        planification = Planification(Transaction().context['active_id'])

        details_domain = self._view_details(planification.id)

        return {
            'technicians_domain': [t.laboratory_professional.id
                for t in planification.technicians],
            'details1_domain': [d.id for d in details_domain],
            }

    def _view_details(self, planification_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        PlanificationDetail = pool.get(
            'lims.planification.detail')
        PlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')
        UnlinkTechniciansDetail1 = pool.get(
            'lims.planification.unlink_technicians.detail1')

        details1 = {}
        cursor.execute('SELECT d.fraction, d.service_analysis, sd.id '
            'FROM "' + PlanificationDetail._table + '" d '
                'INNER JOIN "' + PlanificationServiceDetail._table + '" sd '
                    'ON sd.detail = d.id '
            'WHERE d.planification = %s',
            (planification_id,))
        for x in cursor.fetchall():
            f, s = x[0], x[1]
            if (f, s) not in details1:
                details1[(f, s)] = {
                    'fraction': f,
                    'service_analysis': s,
                    }

        to_create = []
        for d in details1.values():
            to_create.append({
                'session_id': self._session_id,
                'fraction': d['fraction'],
                'service_analysis': d['service_analysis'],
                })
        return UnlinkTechniciansDetail1.create(to_create)

    def transition_unlink(self):
        pool = Pool()
        Planification = pool.get('lims.planification')
        PlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')

        planification = Planification(Transaction().context['active_id'])

        details = self._get_details(planification.id)

        PlanificationServiceDetail.write(details, {
            'staff_responsible': [('remove',
                [t.id for t in self.start.technicians])],
            })
        return 'end'

    def _get_details(self, planification_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        PlanificationDetail = pool.get(
            'lims.planification.detail')
        PlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')

        details = []
        for detail in self.start.details1:
            cursor.execute('SELECT sd.id '
                'FROM "' + PlanificationDetail._table + '" d '
                    'INNER JOIN "' + PlanificationServiceDetail._table + '" sd'
                        ' ON sd.detail = d.id '
                'WHERE d.planification = %s '
                    'AND d.fraction = %s '
                    'AND d.service_analysis = %s',
                (planification_id, detail.fraction.id,
                    detail.service_analysis.id))
            for x in cursor.fetchall():
                details.append(x[0])

        return PlanificationServiceDetail.browse(details)


class AddFractionControlStart(ModelView):
    'Add Fraction Control'
    __name__ = 'lims.planification.add_fraction_con.start'

    planification = fields.Many2One('lims.planification', 'Planification')
    type = fields.Selection([
        ('exist', 'Existing CON'),
        ('coi', 'COI'),
        ('mrc', 'MRC'),
        ('sla', 'SLA'),
        ('itc', 'ITC'),
        ('itl', 'ITL'),
        ], 'Control type', sort=False, required=True)
    original_fraction = fields.Many2One('lims.fraction', 'Original fraction',
        required=True, domain=[('id', 'in', Eval('fraction_domain'))],
        depends=['fraction_domain'])
    fraction_domain = fields.Function(fields.One2Many('lims.fraction',
        None, 'Fraction domain'), 'on_change_with_fraction_domain')
    label = fields.Char('Label', depends=['type'],
        states={'readonly': Eval('type') == 'exist'})
    concentration_level = fields.Many2One('lims.concentration.level',
        'Concentration level', states={
            'invisible': Bool(Eval('concentration_level_invisible')),
            }, depends=['concentration_level_invisible'])
    concentration_level_invisible = fields.Boolean(
        'Concentration level invisible')
    generate_repetition = fields.Boolean('Generate repetition',
        states={'readonly': Eval('type') == 'exist'}, depends=['type'])

    @fields.depends('planification', 'type')
    def on_change_with_fraction_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Analysis = pool.get('lims.analysis')
        Fraction = pool.get('lims.fraction')
        NotebookLine = pool.get('lims.notebook.line')
        Notebook = pool.get('lims.notebook')

        if not self.type:
            return []

        p_analysis_ids = []
        for p_analysis in self.planification.analysis:
            if p_analysis.type == 'analysis':
                p_analysis_ids.append(p_analysis.id)
            else:
                p_analysis_ids.extend(
                    Analysis.get_included_analysis_analysis(p_analysis.id))

        stored_fractions_ids = Fraction.get_stored_fractions()

        special_type = 'con' if self.type == 'exist' else self.type
        clause = [
            ('notebook.fraction.special_type', '=', special_type),
            ('notebook.fraction.id', 'in', stored_fractions_ids),
            ('analysis', 'in', p_analysis_ids),
            ]
        if self.type == 'exist':
            deadline = datetime.now() - relativedelta(days=5)
            clause.extend([
                ('result', 'in', (None, '')),
                ('end_date', '=', None),
                ('annulment_date', '=', None),
                ('notebook.fraction.sample.date2', '>=', deadline),
                ])
        notebook_lines = NotebookLine.search(clause)
        if not notebook_lines:
            return []

        notebook_lines_ids = ', '.join(str(nl.id) for nl in notebook_lines)
        cursor.execute('SELECT DISTINCT(n.fraction) '
            'FROM "' + Notebook._table + '" n '
                'INNER JOIN "' + NotebookLine._table + '" nl '
                'ON nl.notebook = n.id '
            'WHERE nl.id IN (' + notebook_lines_ids + ')')
        return [x[0] for x in cursor.fetchall()]

    @fields.depends('type', 'original_fraction', 'concentration_level')
    def on_change_with_label(self, name=None):
        Date = Pool().get('ir.date')
        if self.type == 'exist':
            return ''
        label = ''
        if self.original_fraction:
            label += self.original_fraction.label
        if self.concentration_level:
                label += (' (' +
                        self.concentration_level.description + ')')
        label += ' ' + str(Date.today())
        return label


class AddFractionControl(Wizard):
    'Add Fraction Control'
    __name__ = 'lims.planification.add_fraction_con'

    start = StateView('lims.planification.add_fraction_con.start',
        'lims.lims_add_fraction_con_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Add', 'add', 'tryton-ok', default=True),
            ])
    add = StateTransition()

    @classmethod
    def __setup__(cls):
        super(AddFractionControl, cls).__setup__()
        cls._error_messages.update({
            'no_entry_control': ('There is no default entry control for this '
                'work year'),
            'no_con_fraction_type': ('There is no Control fraction type '
                'configured'),
            'no_concentration_level': ('Missing concentration level '
                'for this control type'),
            })

    def default_start(self, fields):
        Config = Pool().get('lims.configuration')
        config = Config(1)
        defaults = {
            'planification': Transaction().context['active_id'],
            'concentration_level_invisible': True,
            }
        if (config.con_fraction_type and
                config.con_fraction_type.control_charts):
            defaults['concentration_level_invisible'] = False
        return defaults

    def transition_add(self):
        fraction = self.start.original_fraction
        if self.start.type != 'exist':
            fraction = self.create_control()
        self.add_control(fraction)
        self.add_planification_detail(fraction)
        return 'end'

    def create_control(self):
        pool = Pool()
        Config = pool.get('lims.configuration')
        LabWorkYear = pool.get('lims.lab.workyear')
        Entry = pool.get('lims.entry')
        Sample = pool.get('lims.sample')
        Fraction = pool.get('lims.fraction')
        Service = pool.get('lims.service')
        Analysis = pool.get('lims.analysis')
        NotebookLine = pool.get('lims.notebook.line')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        config = Config(1)
        fraction_type = config.con_fraction_type
        if not fraction_type:
            self.raise_user_error('no_con_fraction_type')

        if (fraction_type.control_charts and not
                self.start.concentration_level):
            self.raise_user_error('no_concentration_level')

        workyear_id = LabWorkYear.find()
        workyear = LabWorkYear(workyear_id)
        if not workyear.default_entry_control:
            self.raise_user_error('no_entry_control')

        entry = Entry(workyear.default_entry_control.id)
        original_fraction = self.start.original_fraction
        original_sample = Sample(original_fraction.sample.id)
        obj_description = self._get_obj_description(original_sample)

        # new sample
        new_sample, = Sample.copy([original_sample], default={
            'entry': entry.id,
            'date': datetime.now(),
            'label': self.start.label,
            'obj_description': obj_description,
            'fractions': [],
            })

        # new fraction
        new_fraction, = Fraction.copy([original_fraction], default={
            'sample': new_sample.id,
            'type': fraction_type.id,
            'services': [],
            'con_type': self.start.type,
            'con_original_fraction': original_fraction.id,
            })

        # new services
        p_analysis_ids = []
        for p_analysis in self.start.planification.analysis:
            if p_analysis.type == 'analysis':
                p_analysis_ids.append(p_analysis.id)
            else:
                p_analysis_ids.extend(
                    Analysis.get_included_analysis_analysis(p_analysis.id))

        services = Service.search([
            ('fraction', '=', original_fraction),
            ])
        for service in services:
            if not Analysis.is_typified(service.analysis,
                    new_sample.product_type, new_sample.matrix):
                continue

            method_id = service.method and service.method.id or None
            device_id = service.device and service.device.id or None
            if service.analysis.type == 'analysis':
                original_lines = NotebookLine.search([
                    ('notebook.fraction', '=', original_fraction.id),
                    ('analysis', '=', service.analysis.id),
                    ('repetition', '=', 0),
                    ], limit=1)
                original_line = original_lines[0] if original_lines else None
                if original_line:
                    method_id = original_line.method.id
                    if original_line.device:
                        device_id = original_line.device.id

            new_service, = Service.copy([service], default={
                'fraction': new_fraction.id,
                'method': method_id,
                'device': device_id,
                })

            # delete services/details not related to planification
            to_delete = EntryDetailAnalysis.search([
                ('service', '=', new_service.id),
                ('analysis', 'not in', p_analysis_ids),
                ])
            if to_delete:
                with Transaction().set_user(0, set_context=True):
                    EntryDetailAnalysis.delete(to_delete)
            if EntryDetailAnalysis.search_count([
                    ('service', '=', new_service.id),
                    ]) == 0:
                with Transaction().set_user(0, set_context=True):
                    Service.delete([new_service])

        # confirm fraction: new notebook and stock move
        Fraction.confirm([new_fraction])

        # Edit notebook lines
        if fraction_type.control_charts:
            notebook_lines = NotebookLine.search([
                ('notebook.fraction', '=', new_fraction.id),
                ])
            if notebook_lines:
                defaults = {
                    'concentration_level': self.start.concentration_level.id,
                    }
                NotebookLine.write(notebook_lines, defaults)

        # Generate repetition
        if self.start.generate_repetition:
            notebook_lines = NotebookLine.search([
                ('notebook.fraction', '=', new_fraction.id),
                ])
            if notebook_lines:
                self.generate_repetition(notebook_lines)

        return new_fraction

    def _get_obj_description(self, sample):
        cursor = Transaction().connection.cursor()
        ObjectiveDescription = Pool().get('lims.objective_description')

        if not sample.product_type or not sample.matrix:
            return None

        cursor.execute('SELECT id '
            'FROM "' + ObjectiveDescription._table + '" '
            'WHERE product_type = %s '
                'AND matrix = %s',
            (sample.product_type.id, sample.matrix.id))
        res = cursor.fetchone()
        return res and res[0] or None

    def generate_repetition(self, notebook_lines):
        pool = Pool()
        Analysis = pool.get('lims.analysis')
        Notebook = pool.get('lims.notebook')

        p_analysis_ids = []
        for p_analysis in self.start.planification.analysis:
            if p_analysis.type == 'analysis':
                p_analysis_ids.append(p_analysis.id)
            else:
                p_analysis_ids.extend(
                    Analysis.get_included_analysis_analysis(p_analysis.id))

        analysis_to_repeat = {}
        for notebook_line in notebook_lines:
            if notebook_line.analysis.id not in p_analysis_ids:
                continue
            if notebook_line.analysis.id not in analysis_to_repeat:
                analysis_to_repeat[notebook_line.analysis.id] = notebook_line
            elif (notebook_line.repetition >
                    analysis_to_repeat[notebook_line.analysis.id].repetition):
                analysis_to_repeat[notebook_line.analysis.id] = notebook_line

        notebook = Notebook(notebook_lines[0].notebook.id)

        to_create = []
        for analysis_id, nline in analysis_to_repeat.items():
            to_create.append({
                'analysis_detail': nline.analysis_detail.id,
                'service': nline.service.id,
                'analysis': analysis_id,
                'analysis_origin': nline.analysis_origin,
                'repetition': nline.repetition + 1,
                'laboratory': nline.laboratory.id,
                'method': nline.method.id,
                'device': nline.device.id if nline.device else None,
                'initial_concentration': nline.initial_concentration,
                'final_concentration': nline.final_concentration,
                'initial_unit': (nline.initial_unit.id if
                    nline.initial_unit else None),
                'final_unit': (nline.final_unit.id if
                    nline.final_unit else None),
                'detection_limit': nline.detection_limit,
                'quantification_limit': nline.quantification_limit,
                'decimals': nline.decimals,
                'report': nline.report,
                'concentration_level': (nline.concentration_level.id if
                    nline.concentration_level else None),
                'results_estimated_waiting': nline.results_estimated_waiting,
                'department': (nline.department.id if
                    nline.department else None),
                })
        Notebook.write([notebook], {
            'lines': [('create', to_create)],
            })

    def add_control(self, fraction):
        Planification = Pool().get('lims.planification')
        Planification.write([self.start.planification], {
            'controls': [('add', [fraction.id])],
            })

    def add_planification_detail(self, fraction):
        pool = Pool()
        Analysis = pool.get('lims.analysis')
        NotebookLine = pool.get('lims.notebook.line')
        PlanificationDetail = pool.get('lims.planification.detail')

        p_analysis_ids = []
        for p_analysis in self.start.planification.analysis:
            if p_analysis.type == 'analysis':
                p_analysis_ids.append(p_analysis.id)
            else:
                p_analysis_ids.extend(
                    Analysis.get_included_analysis_analysis(p_analysis.id))
        clause = [
            ('notebook.fraction', '=', fraction.id),
            ('analysis', 'in', p_analysis_ids),
            ('analysis.behavior', '!=', 'internal_relation'),
            ]
        if self.start.type == 'exist':
            clause.extend([
                ('result', 'in', (None, '')),
                ('end_date', '=', None),
                ('annulment_date', '=', None),
                ])
        else:
            clause.append(('planification', '=', None))
        notebook_lines = NotebookLine.search(clause)
        if notebook_lines:
            details_to_create = {}
            for nl in notebook_lines:
                f = nl.notebook.fraction.id
                s = nl.service.analysis.id
                if (f, s) not in details_to_create:
                    details_to_create[(f, s)] = []
                details_to_create[(f, s)].append({
                    'notebook_line': nl.id,
                    'planned_service': s,
                    'is_control': True,
                    })
            if details_to_create:
                for k, v in details_to_create.items():
                    details = PlanificationDetail.search([
                        ('planification', '=', self.start.planification.id),
                        ('fraction', '=', k[0]),
                        ('service_analysis', '=', k[1]),
                        ])
                    if details:
                        PlanificationDetail.write([details[0]], {
                            'details': [('create', v)],
                            })
                    else:
                        PlanificationDetail.create([{
                            'planification': self.start.planification.id,
                            'fraction': k[0],
                            'service_analysis': k[1],
                            'details': [('create', v)],
                            }])


class AddFractionRMBMZStart(ModelView):
    'Add Fraction RM/BMZ'
    __name__ = 'lims.planification.add_fraction_rm_bmz.start'

    planification = fields.Many2One('lims.planification', 'Planification')
    type = fields.Selection([
        ('rm', 'RM'),
        ('bmz', 'BMZ'),
        ], 'Control type', sort=False, required=True)
    rm_bmz_type = fields.Selection([
        ('sla', 'SLA'),
        ('noref', 'No Reference'),
        ('exist', 'Existing RM/BMZ'),
        ], 'RM/BMZ type', sort=False, required=True)
    reference_fraction = fields.Many2One('lims.fraction',
        'Reference fraction', depends=['fraction_domain', 'rm_bmz_type'],
        states={
            'readonly': Bool(Equal(Eval('rm_bmz_type'), 'noref')),
            'required': Not(Bool(Equal(Eval('rm_bmz_type'), 'noref'))),
        }, domain=[('id', 'in', Eval('fraction_domain'))])
    fraction_domain = fields.Function(fields.One2Many('lims.fraction',
        None, 'Fraction domain'), 'on_change_with_fraction_domain')
    product_type = fields.Many2One('lims.product.type', 'Product type',
        states={
            'readonly': Not(Bool(Equal(Eval('rm_bmz_type'), 'noref'))),
            'required': Bool(Equal(Eval('rm_bmz_type'), 'noref'))},
        domain=[('id', 'in', Eval('product_type_domain'))],
        depends=['rm_bmz_type', 'product_type_domain'])
    product_type_domain = fields.Function(fields.Many2Many(
        'lims.product.type', None, None, 'Product type domain'),
        'on_change_with_product_type_domain')
    matrix = fields.Many2One('lims.matrix', 'Matrix', required=True,
        states={
            'readonly': Not(Bool(Equal(Eval('rm_bmz_type'), 'noref'))),
            'required': Bool(Equal(Eval('rm_bmz_type'), 'noref'))},
        domain=[('id', 'in', Eval('matrix_domain'))],
        depends=['rm_bmz_type', 'matrix_domain'])
    matrix_domain = fields.Function(fields.Many2Many('lims.matrix',
        None, None, 'Matrix domain'),
        'on_change_with_matrix_domain')
    repetitions = fields.Integer('Repetitions',
        states={'readonly': Or(Eval('type') == 'bmz',
            Eval('rm_bmz_type') == 'exist')},
        depends=['type', 'rm_bmz_type'])
    label = fields.Char('Label', depends=['rm_bmz_type'], states={
        'readonly': Eval('rm_bmz_type') == 'exist'})
    concentration_level = fields.Many2One('lims.concentration.level',
        'Concentration level', states={
            'invisible': Bool(Eval('concentration_level_invisible')),
            }, depends=['concentration_level_invisible'])
    concentration_level_invisible = fields.Boolean(
        'Concentration level invisible')

    @fields.depends('type')
    def on_change_with_concentration_level_invisible(self, name=None):
        Config = Pool().get('lims.configuration')
        config = Config(1)
        if self.type == 'rm':
            if (config.rm_fraction_type and
                    config.rm_fraction_type.control_charts):
                return False
        elif self.type == 'bmz':
            if (config.bmz_fraction_type and
                    config.bmz_fraction_type.control_charts):
                return False
        return True

    @fields.depends('planification', 'type', 'rm_bmz_type')
    def on_change_with_fraction_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Analysis = pool.get('lims.analysis')
        Fraction = pool.get('lims.fraction')
        NotebookLine = pool.get('lims.notebook.line')
        Notebook = pool.get('lims.notebook')

        if not self.type or not self.rm_bmz_type:
            return []
        if self.rm_bmz_type == 'noref':
            return []

        p_analysis_ids = []
        for p_analysis in self.planification.analysis:
            if p_analysis.type == 'analysis':
                p_analysis_ids.append(p_analysis.id)
            else:
                p_analysis_ids.extend(
                    Analysis.get_included_analysis_analysis(p_analysis.id))

        stored_fractions_ids = Fraction.get_stored_fractions()

        special_type = 'sla' if self.rm_bmz_type == 'sla' else self.type
        clause = [
            ('notebook.fraction.special_type', '=', special_type),
            ('notebook.fraction.id', 'in', stored_fractions_ids),
            ('analysis', 'in', p_analysis_ids),
            ]
        if self.rm_bmz_type == 'exist':
            deadline = datetime.now() - relativedelta(days=5)
            clause.extend([
                ('result', 'in', (None, '')),
                ('end_date', '=', None),
                ('annulment_date', '=', None),
                ('notebook.fraction.sample.date2', '>=', deadline),
                ])
        notebook_lines = NotebookLine.search(clause)
        if not notebook_lines:
            return []

        notebook_lines_ids = ', '.join(str(nl.id) for nl in notebook_lines)
        cursor.execute('SELECT DISTINCT(n.fraction) '
            'FROM "' + Notebook._table + '" n '
                'INNER JOIN "' + NotebookLine._table + '" nl '
                'ON nl.notebook = n.id '
            'WHERE nl.id IN (' + notebook_lines_ids + ')')
        return [x[0] for x in cursor.fetchall()]

    @staticmethod
    def default_product_type_domain():
        cursor = Transaction().connection.cursor()
        Typification = Pool().get('lims.typification')

        cursor.execute('SELECT DISTINCT(product_type) '
                'FROM "' + Typification._table + '" '
                'WHERE valid')
        return [x[0] for x in cursor.fetchall()]

    def on_change_with_product_type_domain(self, name=None):
        return self.default_product_type_domain()

    @fields.depends('product_type')
    def on_change_product_type(self):
        matrix = None
        if self.product_type:
            matrixs = self.on_change_with_matrix_domain()
            if len(matrixs) == 1:
                matrix = matrixs[0]
        self.matrix = matrix

    @fields.depends('product_type')
    def on_change_with_matrix_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        Typification = Pool().get('lims.typification')

        if not self.product_type:
            return []

        cursor.execute('SELECT DISTINCT(matrix) '
                'FROM "' + Typification._table + '" '
                'WHERE product_type = %s '
                'AND valid',
                (self.product_type.id,))
        return [x[0] for x in cursor.fetchall()]

    @fields.depends('type', 'rm_bmz_type', 'reference_fraction',
        'product_type', 'matrix', 'concentration_level')
    def on_change_with_label(self, name=None):
        Date = Pool().get('ir.date')
        if self.rm_bmz_type == 'exist':
            return ''
        label = ''
        if self.type == 'rm':
            label = 'RM'
            if self.concentration_level:
                label += (' (' +
                        self.concentration_level.description + ')')
        elif self.type == 'bmz':
            label = 'BMZ'
        if self.rm_bmz_type == 'sla':
            if self.reference_fraction:
                label += (' ' +
                       self.reference_fraction.label)
            label += ' ' + str(Date.today())
        elif self.rm_bmz_type == 'noref':
            label += ' ' + str(Date.today())
        return label


class AddFractionRMBMZ(Wizard):
    'Add Fraction RM/BMZ'
    __name__ = 'lims.planification.add_fraction_rm_bmz'

    start = StateView('lims.planification.add_fraction_rm_bmz.start',
        'lims.lims_add_fraction_rm_bmz_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Add', 'add', 'tryton-ok', default=True),
            ])
    add = StateTransition()

    @classmethod
    def __setup__(cls):
        super(AddFractionRMBMZ, cls).__setup__()
        cls._error_messages.update({
            'no_entry_control': ('There is no default entry control for this '
                'work year'),
            'no_rm_fraction_type': ('There is no RM fraction type '
                'configured'),
            'no_bmz_fraction_type': ('There is no BMZ fraction type '
                'configured'),
            'no_rm_default_configuration': ('Missing default configuration '
                'for RM fraction type'),
            'no_bmz_default_configuration': ('Missing default configuration '
                'for BMZ fraction type'),
            'no_concentration_level': ('Missing concentration level '
                'for this control type'),
            'not_typified': ('The analysis "%(analysis)s" is not typified '
                'for product type "%(product_type)s" and matrix "%(matrix)s"'),
            })

    def default_start(self, fields):
        defaults = {
            'planification': Transaction().context['active_id'],
            'concentration_level_invisible': True,
            }
        return defaults

    def transition_add(self):
        fraction = self.start.reference_fraction
        if self.start.rm_bmz_type != 'exist':
            fraction = self.create_control()
        self.add_control(fraction)
        self.add_planification_detail(fraction)
        return 'end'

    def create_control(self):
        if self.start.rm_bmz_type == 'sla':
            return self._create_control_sla()
        if self.start.rm_bmz_type == 'noref':
            return self._create_control_noref()

    def _create_control_sla(self):
        pool = Pool()
        Config = pool.get('lims.configuration')
        LabWorkYear = pool.get('lims.lab.workyear')
        Entry = pool.get('lims.entry')
        Sample = pool.get('lims.sample')
        Fraction = pool.get('lims.fraction')
        Service = pool.get('lims.service')
        Analysis = pool.get('lims.analysis')
        NotebookLine = pool.get('lims.notebook.line')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        config = Config(1)
        if self.start.type == 'rm':
            if not config.rm_fraction_type:
                self.raise_user_error('no_rm_fraction_type')
            fraction_type = config.rm_fraction_type
        elif self.start.type == 'bmz':
            if not config.bmz_fraction_type:
                self.raise_user_error('no_bmz_fraction_type')
            fraction_type = config.bmz_fraction_type

        if (fraction_type.control_charts and not
                self.start.concentration_level):
            self.raise_user_error('no_concentration_level')

        workyear_id = LabWorkYear.find()
        workyear = LabWorkYear(workyear_id)
        if not workyear.default_entry_control:
            self.raise_user_error('no_entry_control')

        entry = Entry(workyear.default_entry_control.id)
        original_fraction = self.start.reference_fraction
        original_sample = Sample(original_fraction.sample.id)
        obj_description = self._get_obj_description(original_sample)

        # new sample
        new_sample, = Sample.copy([original_sample], default={
            'entry': entry.id,
            'date': datetime.now(),
            'label': self.start.label,
            'obj_description': obj_description,
            'fractions': [],
            })

        # new fraction
        fraction_default = {
            'sample': new_sample.id,
            'type': fraction_type.id,
            'con_type': '',
            'services': [],
            }
        if self.start.type == 'rm':
            fraction_default['rm_type'] = 'sla'
            fraction_default['rm_product_type'] = new_sample.product_type.id
            fraction_default['rm_matrix'] = new_sample.matrix.id
            fraction_default['rm_original_fraction'] = original_fraction.id
        if self.start.type == 'bmz':
            fraction_default['bmz_type'] = 'sla'
            fraction_default['bmz_product_type'] = new_sample.product_type.id
            fraction_default['bmz_matrix'] = new_sample.matrix.id
            fraction_default['bmz_original_fraction'] = original_fraction.id
        new_fraction, = Fraction.copy([original_fraction],
            default=fraction_default)

        # new services
        p_analysis_ids = []
        for p_analysis in self.start.planification.analysis:
            if p_analysis.type == 'analysis':
                p_analysis_ids.append(p_analysis.id)
            else:
                p_analysis_ids.extend(
                    Analysis.get_included_analysis_analysis(p_analysis.id))

        services = Service.search([
            ('fraction', '=', original_fraction),
            ])
        for service in services:
            if not Analysis.is_typified(service.analysis,
                    new_sample.product_type, new_sample.matrix):
                continue

            method_id = service.method and service.method.id or None
            device_id = service.device and service.device.id or None
            if service.analysis.type == 'analysis':
                original_lines = NotebookLine.search([
                    ('notebook.fraction', '=', original_fraction.id),
                    ('analysis', '=', service.analysis.id),
                    ('repetition', '=', 0),
                    ], limit=1)
                original_line = original_lines[0] if original_lines else None
                if original_line:
                    method_id = original_line.method.id
                    if original_line.device:
                        device_id = original_line.device.id

            new_service, = Service.copy([service], default={
                'fraction': new_fraction.id,
                'method': method_id,
                'device': device_id,
                })

            # delete services/details not related to planification
            to_delete = EntryDetailAnalysis.search([
                ('service', '=', new_service.id),
                ('analysis', 'not in', p_analysis_ids),
                ])
            if to_delete:
                with Transaction().set_user(0, set_context=True):
                    EntryDetailAnalysis.delete(to_delete)
            if EntryDetailAnalysis.search_count([
                    ('service', '=', new_service.id),
                    ]) == 0:
                with Transaction().set_user(0, set_context=True):
                    Service.delete([new_service])

        # confirm fraction: new notebook and stock move
        Fraction.confirm([new_fraction])

        # Edit notebook lines
        if fraction_type.control_charts:
            notebook_lines = NotebookLine.search([
                ('notebook.fraction', '=', new_fraction.id),
                ])
            if notebook_lines:
                defaults = {
                    'concentration_level': self.start.concentration_level.id,
                    }
                NotebookLine.write(notebook_lines, defaults)
        if self.start.type == 'rm':
            notebook_lines = NotebookLine.search([
                ('notebook.fraction', '=', new_fraction.id),
                ])
            if notebook_lines:
                defaults = {
                    'final_concentration': None,
                    'final_unit': None,
                    'detection_limit': None,
                    'quantification_limit': None,
                    }
                if config.rm_start_uom:
                    defaults['initial_unit'] = config.rm_start_uom.id
                NotebookLine.write(notebook_lines, defaults)

        # Generate repetition
        if self.start.repetitions and self.start.repetitions > 0:
            notebook_lines = NotebookLine.search([
                ('notebook.fraction', '=', new_fraction.id),
                ])
            if notebook_lines:
                self.generate_repetition(notebook_lines,
                    self.start.repetitions)

        return new_fraction

    def _get_obj_description(self, sample):
        cursor = Transaction().connection.cursor()
        ObjectiveDescription = Pool().get('lims.objective_description')

        if not sample.product_type or not sample.matrix:
            return None

        cursor.execute('SELECT id '
            'FROM "' + ObjectiveDescription._table + '" '
            'WHERE product_type = %s '
                'AND matrix = %s',
            (sample.product_type.id, sample.matrix.id))
        res = cursor.fetchone()
        return res and res[0] or None

    def _create_control_noref(self):
        pool = Pool()
        Config = pool.get('lims.configuration')
        LabWorkYear = pool.get('lims.lab.workyear')
        Entry = pool.get('lims.entry')
        Sample = pool.get('lims.sample')
        Fraction = pool.get('lims.fraction')
        Service = pool.get('lims.service')
        Analysis = pool.get('lims.analysis')
        NotebookLine = pool.get('lims.notebook.line')

        config = Config(1)
        if self.start.type == 'rm':
            if not config.rm_fraction_type:
                self.raise_user_error('no_rm_fraction_type')
            fraction_type = config.rm_fraction_type
            if (not fraction_type.default_package_type or
                    not fraction_type.default_fraction_state):
                self.raise_user_error('no_rm_default_configuration')
        elif self.start.type == 'bmz':
            if not config.bmz_fraction_type:
                self.raise_user_error('no_bmz_fraction_type')
            fraction_type = config.bmz_fraction_type
            if (not fraction_type.default_package_type or
                    not fraction_type.default_fraction_state):
                self.raise_user_error('no_bmz_default_configuration')

        if (fraction_type.control_charts and not
                self.start.concentration_level):
            self.raise_user_error('no_concentration_level')

        workyear_id = LabWorkYear.find()
        workyear = LabWorkYear(workyear_id)
        if not workyear.default_entry_control:
            self.raise_user_error('no_entry_control')

        laboratory = self.start.planification.laboratory
        entry = Entry(workyear.default_entry_control.id)
        obj_description = self._get_obj_description(self.start)

        # new sample
        new_sample, = Sample.create([{
            'entry': entry.id,
            'date': datetime.now(),
            'product_type': self.start.product_type.id,
            'matrix': self.start.matrix.id,
            'zone': entry.party.entry_zone.id,
            'label': self.start.label,
            'obj_description': obj_description,
            'packages_quantity': 1,
            'fractions': [],
            }])

        # new fraction
        fraction_default = {
            'sample': new_sample.id,
            'type': fraction_type.id,
            'storage_location': laboratory.related_location.id,
            'packages_quantity': 1,
            'package_type': fraction_type.default_package_type.id,
            'fraction_state': fraction_type.default_fraction_state.id,
            'services': [],
            }
        if fraction_type.max_storage_time:
            fraction_default['storage_time'] = fraction_type.max_storage_time
        elif laboratory.related_location.storage_time:
            fraction_default['storage_time'] = (
                laboratory.related_location.storage_time)
        else:
            fraction_default['storage_time'] = 3
        if self.start.type == 'rm':
            fraction_default['rm_type'] = 'noinitialrm'
            fraction_default['rm_product_type'] = new_sample.product_type.id
            fraction_default['rm_matrix'] = new_sample.matrix.id
        if self.start.type == 'bmz':
            fraction_default['bmz_type'] = 'noinitialbmz'
            fraction_default['bmz_product_type'] = new_sample.product_type.id
            fraction_default['bmz_matrix'] = new_sample.matrix.id
        new_fraction, = Fraction.create([fraction_default])

        # new services
        services_default = []
        for p_analysis in self.start.planification.analysis:
            if not Analysis.is_typified(p_analysis,
                    new_sample.product_type, new_sample.matrix):
                self.raise_user_error('not_typified', {
                    'analysis': p_analysis.rec_name,
                    'product_type': new_sample.product_type.rec_name,
                    'matrix': new_sample.matrix.rec_name,
                    })
            laboratory_id = (laboratory.id if p_analysis.type != 'group'
                else None)
            method_id = None
            if new_sample.typification_domain:
                for t in new_sample.typification_domain:
                    if (t.analysis.id == p_analysis.id and
                            t.by_default is True):
                        method_id = t.method.id
            device_id = None
            if p_analysis.devices:
                for d in p_analysis.devices:
                    if (d.laboratory.id == laboratory.id and
                            d.by_default is True):
                        device_id = d.device.id
            services_default.append({
                'fraction': new_fraction.id,
                'analysis': p_analysis.id,
                'laboratory': laboratory_id,
                'method': method_id,
                'device': device_id,
                })
        for service in services_default:
            new_service, = Service.create([service])

            # new analysis details (on service create)

        # confirm fraction: new notebook and stock move
        Fraction.confirm([new_fraction])

        # Edit notebook lines
        if fraction_type.control_charts:
            notebook_lines = NotebookLine.search([
                ('notebook.fraction', '=', new_fraction.id),
                ])
            if notebook_lines:
                defaults = {
                    'concentration_level': self.start.concentration_level.id,
                    }
                NotebookLine.write(notebook_lines, defaults)
        if self.start.type == 'rm':
            notebook_lines = NotebookLine.search([
                ('notebook.fraction', '=', new_fraction.id),
                ])
            if notebook_lines:
                defaults = {
                    'final_concentration': None,
                    'final_unit': None,
                    'detection_limit': None,
                    'quantification_limit': None,
                    }
                if config.rm_start_uom:
                    defaults['initial_unit'] = config.rm_start_uom.id
                NotebookLine.write(notebook_lines, defaults)

        # Generate repetition
        if self.start.repetitions and self.start.repetitions > 0:
            notebook_lines = NotebookLine.search([
                ('notebook.fraction', '=', new_fraction.id),
                ])
            if notebook_lines:
                self.generate_repetition(notebook_lines,
                    self.start.repetitions)

        return new_fraction

    def _get_obj_description(self, sample):
        cursor = Transaction().connection.cursor()
        ObjectiveDescription = Pool().get('lims.objective_description')

        if not sample.product_type or not sample.matrix:
            return None

        cursor.execute('SELECT id '
            'FROM "' + ObjectiveDescription._table + '" '
            'WHERE product_type = %s '
                'AND matrix = %s',
            (sample.product_type.id, sample.matrix.id))
        res = cursor.fetchone()
        return res and res[0] or None

    def generate_repetition(self, notebook_lines, repetitions):
        pool = Pool()
        Analysis = pool.get('lims.analysis')
        Notebook = pool.get('lims.notebook')

        p_analysis_ids = []
        for p_analysis in self.start.planification.analysis:
            if p_analysis.type == 'analysis':
                p_analysis_ids.append(p_analysis.id)
            else:
                p_analysis_ids.extend(
                    Analysis.get_included_analysis_analysis(p_analysis.id))

        analysis_to_repeat = {}
        for notebook_line in notebook_lines:
            if notebook_line.analysis.id not in p_analysis_ids:
                continue
            if notebook_line.analysis.id not in analysis_to_repeat:
                analysis_to_repeat[notebook_line.analysis.id] = notebook_line
            elif (notebook_line.repetition >
                    analysis_to_repeat[notebook_line.analysis.id].repetition):
                analysis_to_repeat[notebook_line.analysis.id] = notebook_line

        notebook = Notebook(notebook_lines[0].notebook.id)

        to_create = []
        for nline in analysis_to_repeat.values():
            for i in range(1, repetitions + 1):
                to_create.append({
                    'analysis_detail': nline.analysis_detail.id,
                    'service': nline.service.id,
                    'analysis': nline.analysis.id,
                    'analysis_origin': nline.analysis_origin,
                    'repetition': nline.repetition + i,
                    'laboratory': nline.laboratory.id,
                    'method': nline.method.id,
                    'device': nline.device.id if nline.device else None,
                    'initial_concentration': nline.initial_concentration,
                    'final_concentration': nline.final_concentration,
                    'initial_unit': (nline.initial_unit.id if
                        nline.initial_unit else None),
                    'final_unit': (nline.final_unit.id if
                        nline.final_unit else None),
                    'detection_limit': nline.detection_limit,
                    'quantification_limit': nline.quantification_limit,
                    'decimals': nline.decimals,
                    'report': nline.report,
                    'concentration_level': (nline.concentration_level.id if
                        nline.concentration_level else None),
                    'results_estimated_waiting': (
                        nline.results_estimated_waiting),
                    'department': (nline.department.id if
                        nline.department else None),
                    })
        Notebook.write([notebook], {
            'lines': [('create', to_create)],
            })

    def add_control(self, fraction):
        Planification = Pool().get('lims.planification')
        Planification.write([self.start.planification], {
            'controls': [('add', [fraction.id])],
            })

    def add_planification_detail(self, fraction):
        pool = Pool()
        Analysis = pool.get('lims.analysis')
        NotebookLine = pool.get('lims.notebook.line')
        PlanificationDetail = pool.get('lims.planification.detail')

        p_analysis_ids = []
        for p_analysis in self.start.planification.analysis:
            if p_analysis.type == 'analysis':
                p_analysis_ids.append(p_analysis.id)
            else:
                p_analysis_ids.extend(
                    Analysis.get_included_analysis_analysis(p_analysis.id))
        clause = [
            ('notebook.fraction', '=', fraction.id),
            ('analysis', 'in', p_analysis_ids),
            ('analysis.behavior', '!=', 'internal_relation'),
            ]
        if self.start.rm_bmz_type == 'exist':
            clause.extend([
                ('result', 'in', (None, '')),
                ('end_date', '=', None),
                ('annulment_date', '=', None),
                ])
        else:
            clause.append(('planification', '=', None))
        notebook_lines = NotebookLine.search(clause)
        if notebook_lines:
            details_to_create = {}
            for nl in notebook_lines:
                f = nl.notebook.fraction.id
                s = nl.service.analysis.id
                if (f, s) not in details_to_create:
                    details_to_create[(f, s)] = []
                details_to_create[(f, s)].append({
                    'notebook_line': nl.id,
                    'planned_service': s,
                    'is_control': True,
                    })
            if details_to_create:
                for k, v in details_to_create.items():
                    details = PlanificationDetail.search([
                        ('planification', '=', self.start.planification.id),
                        ('fraction', '=', k[0]),
                        ('service_analysis', '=', k[1]),
                        ])
                    if details:
                        PlanificationDetail.write([details[0]], {
                            'details': [('create', v)],
                            })
                    else:
                        PlanificationDetail.create([{
                            'planification': self.start.planification.id,
                            'fraction': k[0],
                            'service_analysis': k[1],
                            'details': [('create', v)],
                            }])


class AddFractionBREStart(ModelView):
    'Add Fraction BRE'
    __name__ = 'lims.planification.add_fraction_bre.start'

    planification = fields.Many2One('lims.planification', 'Planification')
    type = fields.Selection([
        ('new', 'New BRE'),
        ('exist', 'Existing BRE'),
        ], 'BRE Type', sort=False, required=True)
    bre_fraction = fields.Many2One('lims.fraction',
        'BRE fraction', depends=['fraction_domain', 'type'],
        states={
            'readonly': Bool(Equal(Eval('type'), 'new')),
            'required': Bool(Equal(Eval('type'), 'exist')),
        }, domain=[('id', 'in', Eval('fraction_domain'))])
    fraction_domain = fields.Function(fields.One2Many('lims.fraction',
        None, 'Fraction domain'), 'on_change_with_fraction_domain')
    product_type = fields.Many2One('lims.product.type', 'Product type',
        states={'required': Bool(Equal(Eval('type'), 'new'))},
        domain=[('id', 'in', Eval('product_type_domain'))],
        depends=['type', 'product_type_domain'])
    product_type_domain = fields.Function(fields.Many2Many(
        'lims.product.type', None, None, 'Product type domain'),
        'on_change_with_product_type_domain')
    matrix = fields.Many2One('lims.matrix', 'Matrix', required=True,
        states={'required': Bool(Equal(Eval('type'), 'new'))},
        domain=[('id', 'in', Eval('matrix_domain'))],
        depends=['type', 'matrix_domain'])
    matrix_domain = fields.Function(fields.Many2Many('lims.matrix',
        None, None, 'Matrix domain'),
        'on_change_with_matrix_domain')
    reagents = fields.One2Many('lims.fraction.reagent', None,
        'Reagents', states={
            'readonly': Bool(Equal(Eval('type'), 'exist')),
        }, depends=['type'], required=True)
    label = fields.Char('Label', depends=['type'], states={
        'readonly': Eval('type') == 'exist'})
    concentration_level = fields.Many2One('lims.concentration.level',
        'Concentration level', states={
            'invisible': Bool(Eval('concentration_level_invisible')),
            }, depends=['concentration_level_invisible'])
    concentration_level_invisible = fields.Boolean(
        'Concentration level invisible')

    @fields.depends('planification', 'type')
    def on_change_with_fraction_domain(self, name=None):
        pool = Pool()
        Analysis = pool.get('lims.analysis')
        Fraction = pool.get('lims.fraction')
        NotebookLine = pool.get('lims.notebook.line')

        if self.type != 'exist':
            return []

        p_analysis_ids = []
        for p_analysis in self.planification.analysis:
            if p_analysis.type == 'analysis':
                p_analysis_ids.append(p_analysis.id)
            else:
                p_analysis_ids.extend(
                    Analysis.get_included_analysis_analysis(p_analysis.id))

        stored_fractions_ids = Fraction.get_stored_fractions()

        deadline = datetime.now() - relativedelta(days=5)
        clause = [
            ('notebook.fraction.special_type', '=', 'bre'),
            ('notebook.fraction.id', 'in', stored_fractions_ids),
            ('analysis', 'in', p_analysis_ids),
            ('result', 'in', (None, '')),
            ('end_date', '=', None),
            ('annulment_date', '=', None),
            ('notebook.fraction.sample.date2', '>=', deadline),
            ]
        notebook_lines = NotebookLine.search(clause)

        fractions = [nl.notebook.fraction.id for nl in notebook_lines]
        return list(set(fractions))

    @staticmethod
    def default_product_type_domain():
        cursor = Transaction().connection.cursor()
        Typification = Pool().get('lims.typification')

        cursor.execute('SELECT DISTINCT(product_type) '
                'FROM "' + Typification._table + '" '
                'WHERE valid')
        return [x[0] for x in cursor.fetchall()]

    def on_change_with_product_type_domain(self, name=None):
        return self.default_product_type_domain()

    @fields.depends('product_type')
    def on_change_product_type(self):
        matrix = None
        if self.product_type:
            matrixs = self.on_change_with_matrix_domain()
            if len(matrixs) == 1:
                matrix = matrixs[0]
        self.matrix = matrix

    @fields.depends('product_type')
    def on_change_with_matrix_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        Typification = Pool().get('lims.typification')

        if not self.product_type:
            return []

        cursor.execute('SELECT DISTINCT(matrix) '
                'FROM "' + Typification._table + '" '
                'WHERE product_type = %s '
                'AND valid',
                (self.product_type.id,))
        return [x[0] for x in cursor.fetchall()]

    @fields.depends('type', 'product_type', 'matrix')
    def on_change_with_label(self, name=None):
        Date = Pool().get('ir.date')
        if self.type == 'exist':
            return ''
        label = 'BRE'
        label += ' ' + str(Date.today())
        return label


class AddFractionBRE(Wizard):
    'Add Fraction BRE'
    __name__ = 'lims.planification.add_fraction_bre'

    start = StateView('lims.planification.add_fraction_bre.start',
        'lims.lims_add_fraction_bre_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Add', 'add', 'tryton-ok', default=True),
            ])
    add = StateTransition()

    @classmethod
    def __setup__(cls):
        super(AddFractionBRE, cls).__setup__()
        cls._error_messages.update({
            'no_entry_control': ('There is no default entry control for this '
                'work year'),
            'no_bre_fraction_type': ('There is no BRE fraction type '
                'configured'),
            'no_bre_default_configuration': ('Missing default configuration '
                'for BRE fraction type'),
            'no_concentration_level': ('Missing concentration level '
                'for this control type'),
            'not_typified': ('The analysis "%(analysis)s" is not typified '
                'for product type "%(product_type)s" and matrix "%(matrix)s"'),
            })

    def default_start(self, fields):
        Config = Pool().get('lims.configuration')
        config = Config(1)
        defaults = {
            'planification': Transaction().context['active_id'],
            'concentration_level_invisible': True,
            }
        if (config.bre_fraction_type and
                config.bre_fraction_type.control_charts):
            defaults['concentration_level_invisible'] = False
        return defaults

    def transition_add(self):
        fraction = self.start.bre_fraction
        if self.start.type == 'new':
            fraction = self.create_control()
        self.add_control(fraction)
        self.add_planification_detail(fraction)
        return 'end'

    def create_control(self):
        pool = Pool()
        Config = pool.get('lims.configuration')
        LabWorkYear = pool.get('lims.lab.workyear')
        Entry = pool.get('lims.entry')
        Sample = pool.get('lims.sample')
        Fraction = pool.get('lims.fraction')
        Service = pool.get('lims.service')
        Analysis = pool.get('lims.analysis')
        NotebookLine = pool.get('lims.notebook.line')

        config = Config(1)
        if not config.bre_fraction_type:
            self.raise_user_error('no_bre_fraction_type')
        fraction_type = config.bre_fraction_type
        if (not fraction_type.default_package_type or
                not fraction_type.default_fraction_state):
            self.raise_user_error('no_bre_default_configuration')

        if (fraction_type.control_charts and not
                self.start.concentration_level):
            self.raise_user_error('no_concentration_level')

        workyear_id = LabWorkYear.find()
        workyear = LabWorkYear(workyear_id)
        if not workyear.default_entry_control:
            self.raise_user_error('no_entry_control')

        laboratory = self.start.planification.laboratory
        entry = Entry(workyear.default_entry_control.id)
        obj_description = self._get_obj_description(self.start)

        # new sample
        new_sample, = Sample.create([{
            'entry': entry.id,
            'date': datetime.now(),
            'product_type': self.start.product_type.id,
            'matrix': self.start.matrix.id,
            'zone': entry.party.entry_zone.id,
            'label': self.start.label,
            'obj_description': obj_description,
            'packages_quantity': 1,
            'fractions': [],
            }])

        # new fraction
        bre_reagents = [{
            'product': r.product.id,
            'lot': r.lot.id if r.lot else None,
            } for r in self.start.reagents]
        fraction_default = {
            'sample': new_sample.id,
            'type': fraction_type.id,
            'storage_location': laboratory.related_location.id,
            'packages_quantity': 1,
            'package_type': fraction_type.default_package_type.id,
            'fraction_state': fraction_type.default_fraction_state.id,
            'services': [],
            'bre_product_type': new_sample.product_type.id,
            'bre_matrix': new_sample.matrix.id,
            'bre_reagents': [('create', bre_reagents)],
            }
        if fraction_type.max_storage_time:
            fraction_default['storage_time'] = fraction_type.max_storage_time
        elif laboratory.related_location.storage_time:
            fraction_default['storage_time'] = (
                laboratory.related_location.storage_time)
        else:
            fraction_default['storage_time'] = 3
        new_fraction, = Fraction.create([fraction_default])

        # new services
        services_default = []
        for p_analysis in self.start.planification.analysis:
            if not Analysis.is_typified(p_analysis,
                    new_sample.product_type, new_sample.matrix):
                self.raise_user_error('not_typified', {
                    'analysis': p_analysis.rec_name,
                    'product_type': new_sample.product_type.rec_name,
                    'matrix': new_sample.matrix.rec_name,
                    })
            laboratory_id = (laboratory.id if p_analysis.type != 'group'
                else None)
            method_id = None
            if new_sample.typification_domain:
                for t in new_sample.typification_domain:
                    if (t.analysis.id == p_analysis.id and
                            t.by_default is True):
                        method_id = t.method.id
            device_id = None
            if p_analysis.devices:
                for d in p_analysis.devices:
                    if (d.laboratory.id == laboratory.id and
                            d.by_default is True):
                        device_id = d.device.id
            services_default.append({
                'fraction': new_fraction.id,
                'analysis': p_analysis.id,
                'laboratory': laboratory_id,
                'method': method_id,
                'device': device_id,
                })
        for service in services_default:
            new_service, = Service.create([service])

            # new analysis details (on service create)

        # confirm fraction: new notebook and stock move
        Fraction.confirm([new_fraction])

        # Edit notebook lines
        if fraction_type.control_charts:
            notebook_lines = NotebookLine.search([
                ('notebook.fraction', '=', new_fraction.id),
                ])
            if notebook_lines:
                defaults = {
                    'concentration_level': self.start.concentration_level.id,
                    }
                NotebookLine.write(notebook_lines, defaults)

        return new_fraction

    def _get_obj_description(self, sample):
        cursor = Transaction().connection.cursor()
        ObjectiveDescription = Pool().get('lims.objective_description')

        if not sample.product_type or not sample.matrix:
            return None

        cursor.execute('SELECT id '
            'FROM "' + ObjectiveDescription._table + '" '
            'WHERE product_type = %s '
                'AND matrix = %s',
            (sample.product_type.id, sample.matrix.id))
        res = cursor.fetchone()
        return res and res[0] or None

    def add_control(self, fraction):
        Planification = Pool().get('lims.planification')
        Planification.write([self.start.planification], {
            'controls': [('add', [fraction.id])],
            })

    def add_planification_detail(self, fraction):
        pool = Pool()
        Analysis = pool.get('lims.analysis')
        NotebookLine = pool.get('lims.notebook.line')
        PlanificationDetail = pool.get('lims.planification.detail')

        p_analysis_ids = []
        for p_analysis in self.start.planification.analysis:
            if p_analysis.type == 'analysis':
                p_analysis_ids.append(p_analysis.id)
            else:
                p_analysis_ids.extend(
                    Analysis.get_included_analysis_analysis(p_analysis.id))
        clause = [
            ('notebook.fraction', '=', fraction.id),
            ('analysis', 'in', p_analysis_ids),
            ('analysis.behavior', '!=', 'internal_relation'),
            ]
        if self.start.type == 'exist':
            clause.extend([
                ('result', 'in', (None, '')),
                ('end_date', '=', None),
                ('annulment_date', '=', None),
                ])
        else:
            clause.append(('planification', '=', None))
        notebook_lines = NotebookLine.search(clause)
        if notebook_lines:
            details_to_create = {}
            for nl in notebook_lines:
                f = nl.notebook.fraction.id
                s = nl.service.analysis.id
                if (f, s) not in details_to_create:
                    details_to_create[(f, s)] = []
                details_to_create[(f, s)].append({
                    'notebook_line': nl.id,
                    'planned_service': s,
                    'is_control': True,
                    })
            if details_to_create:
                for k, v in details_to_create.items():
                    details = PlanificationDetail.search([
                        ('planification', '=', self.start.planification.id),
                        ('fraction', '=', k[0]),
                        ('service_analysis', '=', k[1]),
                        ])
                    if details:
                        PlanificationDetail.write([details[0]], {
                            'details': [('create', v)],
                            })
                    else:
                        PlanificationDetail.create([{
                            'planification': self.start.planification.id,
                            'fraction': k[0],
                            'service_analysis': k[1],
                            'details': [('create', v)],
                            }])


class AddFractionMRTStart(ModelView):
    'Add Fraction MRT'
    __name__ = 'lims.planification.add_fraction_mrt.start'

    planification = fields.Many2One('lims.planification', 'Planification')
    type = fields.Selection([
        ('new', 'New MRT'),
        ('exist', 'Existing MRT'),
        ], 'MRT Type', sort=False, required=True)
    mrt_fraction = fields.Many2One('lims.fraction',
        'MRT fraction', depends=['fraction_domain', 'type'],
        states={
            'readonly': Bool(Equal(Eval('type'), 'new')),
            'required': Bool(Equal(Eval('type'), 'exist')),
        }, domain=[('id', 'in', Eval('fraction_domain'))])
    fraction_domain = fields.Function(fields.One2Many('lims.fraction',
        None, 'Fraction domain'), 'on_change_with_fraction_domain')
    product_type = fields.Many2One('lims.product.type', 'Product type',
        states={'required': Bool(Equal(Eval('type'), 'new'))},
        domain=[('id', 'in', Eval('product_type_domain'))],
        depends=['type', 'product_type_domain'])
    product_type_domain = fields.Function(fields.Many2Many(
        'lims.product.type', None, None, 'Product type domain'),
        'on_change_with_product_type_domain')
    matrix = fields.Many2One('lims.matrix', 'Matrix', required=True,
        states={'required': Bool(Equal(Eval('type'), 'new'))},
        domain=[('id', 'in', Eval('matrix_domain'))],
        depends=['type', 'matrix_domain'])
    matrix_domain = fields.Function(fields.Many2Many('lims.matrix',
        None, None, 'Matrix domain'),
        'on_change_with_matrix_domain')
    repetitions = fields.Integer('Repetitions')
    label = fields.Char('Label', depends=['type'], states={
        'readonly': Eval('type') == 'exist'})
    concentration_level = fields.Many2One('lims.concentration.level',
        'Concentration level', states={
            'invisible': Bool(Eval('concentration_level_invisible')),
            }, depends=['concentration_level_invisible'])
    concentration_level_invisible = fields.Boolean(
        'Concentration level invisible')

    @fields.depends('planification', 'type')
    def on_change_with_fraction_domain(self, name=None):
        pool = Pool()
        Analysis = pool.get('lims.analysis')
        Fraction = pool.get('lims.fraction')
        NotebookLine = pool.get('lims.notebook.line')

        if self.type != 'exist':
            return []

        p_analysis_ids = []
        for p_analysis in self.planification.analysis:
            if p_analysis.type == 'analysis':
                p_analysis_ids.append(p_analysis.id)
            else:
                p_analysis_ids.extend(
                    Analysis.get_included_analysis_analysis(p_analysis.id))

        stored_fractions_ids = Fraction.get_stored_fractions()

        deadline = datetime.now() - relativedelta(days=5)
        clause = [
            ('notebook.fraction.special_type', '=', 'mrt'),
            ('notebook.fraction.id', 'in', stored_fractions_ids),
            ('analysis', 'in', p_analysis_ids),
            ('result', 'in', (None, '')),
            ('end_date', '=', None),
            ('annulment_date', '=', None),
            ('notebook.fraction.sample.date2', '>=', deadline),
            ]
        notebook_lines = NotebookLine.search(clause)

        fractions = [nl.notebook.fraction.id for nl in notebook_lines]
        return list(set(fractions))

    @staticmethod
    def default_product_type_domain():
        cursor = Transaction().connection.cursor()
        Typification = Pool().get('lims.typification')

        cursor.execute('SELECT DISTINCT(product_type) '
                'FROM "' + Typification._table + '" '
                'WHERE valid')
        return [x[0] for x in cursor.fetchall()]

    def on_change_with_product_type_domain(self, name=None):
        return self.default_product_type_domain()

    @fields.depends('product_type')
    def on_change_product_type(self):
        matrix = None
        if self.product_type:
            matrixs = self.on_change_with_matrix_domain()
            if len(matrixs) == 1:
                matrix = matrixs[0]
        self.matrix = matrix

    @fields.depends('product_type')
    def on_change_with_matrix_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        Typification = Pool().get('lims.typification')

        if not self.product_type:
            return []

        cursor.execute('SELECT DISTINCT(matrix) '
                'FROM "' + Typification._table + '" '
                'WHERE product_type = %s '
                'AND valid',
                (self.product_type.id,))
        return [x[0] for x in cursor.fetchall()]

    @fields.depends('type', 'product_type', 'matrix')
    def on_change_with_label(self, name=None):
        Date = Pool().get('ir.date')
        if self.type == 'exist':
            return ''
        label = 'MRT'
        label += ' ' + str(Date.today())
        return label


class AddFractionMRT(Wizard):
    'Add Fraction MRT'
    __name__ = 'lims.planification.add_fraction_mrt'

    start = StateView('lims.planification.add_fraction_mrt.start',
        'lims.lims_add_fraction_mrt_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Add', 'add', 'tryton-ok', default=True),
            ])
    add = StateTransition()

    @classmethod
    def __setup__(cls):
        super(AddFractionMRT, cls).__setup__()
        cls._error_messages.update({
            'no_entry_control': ('There is no default entry control for this '
                'work year'),
            'no_mrt_fraction_type': ('There is no MRT fraction type '
                'configured'),
            'no_mrt_default_configuration': ('Missing default configuration '
                'for MRT fraction type'),
            'no_concentration_level': ('Missing concentration level '
                'for this control type'),
            'not_typified': ('The analysis "%(analysis)s" is not typified '
                'for product type "%(product_type)s" and matrix "%(matrix)s"'),
            })

    def default_start(self, fields):
        Config = Pool().get('lims.configuration')
        config = Config(1)
        defaults = {
            'planification': Transaction().context['active_id'],
            'concentration_level_invisible': True,
            }
        if (config.mrt_fraction_type and
                config.mrt_fraction_type.control_charts):
            defaults['concentration_level_invisible'] = False
        return defaults

    def transition_add(self):
        fraction = self.start.mrt_fraction
        if self.start.type == 'new':
            fraction = self.create_control()
        self.add_control(fraction)
        self.add_planification_detail(fraction)
        return 'end'

    def create_control(self):
        pool = Pool()
        Config = pool.get('lims.configuration')
        LabWorkYear = pool.get('lims.lab.workyear')
        Entry = pool.get('lims.entry')
        Sample = pool.get('lims.sample')
        Fraction = pool.get('lims.fraction')
        Service = pool.get('lims.service')
        Analysis = pool.get('lims.analysis')
        NotebookLine = pool.get('lims.notebook.line')

        config = Config(1)
        if not config.mrt_fraction_type:
            self.raise_user_error('no_mrt_fraction_type')
        fraction_type = config.mrt_fraction_type
        if (not fraction_type.default_package_type or
                not fraction_type.default_fraction_state):
            self.raise_user_error('no_mrt_default_configuration')

        if (fraction_type.control_charts and not
                self.start.concentration_level):
            self.raise_user_error('no_concentration_level')

        workyear_id = LabWorkYear.find()
        workyear = LabWorkYear(workyear_id)
        if not workyear.default_entry_control:
            self.raise_user_error('no_entry_control')

        laboratory = self.start.planification.laboratory
        entry = Entry(workyear.default_entry_control.id)
        obj_description = self._get_obj_description(self.start)

        # new sample
        new_sample, = Sample.create([{
            'entry': entry.id,
            'date': datetime.now(),
            'product_type': self.start.product_type.id,
            'matrix': self.start.matrix.id,
            'zone': entry.party.entry_zone.id,
            'label': self.start.label,
            'obj_description': obj_description,
            'packages_quantity': 1,
            'fractions': [],
            }])

        # new fraction
        fraction_default = {
            'sample': new_sample.id,
            'type': fraction_type.id,
            'storage_location': laboratory.related_location.id,
            'packages_quantity': 1,
            'package_type': fraction_type.default_package_type.id,
            'fraction_state': fraction_type.default_fraction_state.id,
            'services': [],
            'mrt_product_type': new_sample.product_type.id,
            'mrt_matrix': new_sample.matrix.id,
            }
        if fraction_type.max_storage_time:
            fraction_default['storage_time'] = fraction_type.max_storage_time
        elif laboratory.related_location.storage_time:
            fraction_default['storage_time'] = (
                laboratory.related_location.storage_time)
        else:
            fraction_default['storage_time'] = 3
        new_fraction, = Fraction.create([fraction_default])

        # new services
        services_default = []
        for p_analysis in self.start.planification.analysis:
            if not Analysis.is_typified(p_analysis,
                    new_sample.product_type, new_sample.matrix):
                self.raise_user_error('not_typified', {
                    'analysis': p_analysis.rec_name,
                    'product_type': new_sample.product_type.rec_name,
                    'matrix': new_sample.matrix.rec_name,
                    })
            laboratory_id = (laboratory.id if p_analysis.type != 'group'
                else None)
            method_id = None
            if new_sample.typification_domain:
                for t in new_sample.typification_domain:
                    if (t.analysis.id == p_analysis.id and
                            t.by_default is True):
                        method_id = t.method.id
            device_id = None
            if p_analysis.devices:
                for d in p_analysis.devices:
                    if (d.laboratory.id == laboratory.id and
                            d.by_default is True):
                        device_id = d.device.id
            services_default.append({
                'fraction': new_fraction.id,
                'analysis': p_analysis.id,
                'laboratory': laboratory_id,
                'method': method_id,
                'device': device_id,
                })
        for service in services_default:
            new_service, = Service.create([service])

            # new analysis details (on service create)

        # confirm fraction: new notebook and stock move
        Fraction.confirm([new_fraction])

        # Edit notebook lines
        if fraction_type.control_charts:
            notebook_lines = NotebookLine.search([
                ('notebook.fraction', '=', new_fraction.id),
                ])
            if notebook_lines:
                defaults = {
                    'concentration_level': self.start.concentration_level.id,
                    }
                NotebookLine.write(notebook_lines, defaults)

        # Generate repetition
        if self.start.repetitions and self.start.repetitions > 0:
            notebook_lines = NotebookLine.search([
                ('notebook.fraction', '=', new_fraction.id),
                ])
            if notebook_lines:
                self.generate_repetition(notebook_lines,
                    self.start.repetitions)

        return new_fraction

    def _get_obj_description(self, sample):
        cursor = Transaction().connection.cursor()
        ObjectiveDescription = Pool().get('lims.objective_description')

        if not sample.product_type or not sample.matrix:
            return None

        cursor.execute('SELECT id '
            'FROM "' + ObjectiveDescription._table + '" '
            'WHERE product_type = %s '
                'AND matrix = %s',
            (sample.product_type.id, sample.matrix.id))
        res = cursor.fetchone()
        return res and res[0] or None

    def generate_repetition(self, notebook_lines, repetitions):
        pool = Pool()
        Analysis = pool.get('lims.analysis')
        Notebook = pool.get('lims.notebook')

        p_analysis_ids = []
        for p_analysis in self.start.planification.analysis:
            if p_analysis.type == 'analysis':
                p_analysis_ids.append(p_analysis.id)
            else:
                p_analysis_ids.extend(
                    Analysis.get_included_analysis_analysis(p_analysis.id))

        analysis_to_repeat = {}
        for notebook_line in notebook_lines:
            if notebook_line.analysis.id not in p_analysis_ids:
                continue
            if notebook_line.analysis.id not in analysis_to_repeat:
                analysis_to_repeat[notebook_line.analysis.id] = notebook_line
            elif (notebook_line.repetition >
                    analysis_to_repeat[notebook_line.analysis.id].repetition):
                analysis_to_repeat[notebook_line.analysis.id] = notebook_line

        notebook = Notebook(notebook_lines[0].notebook.id)

        to_create = []
        for nline in analysis_to_repeat.values():
            for i in range(1, repetitions + 1):
                to_create.append({
                    'analysis_detail': nline.analysis_detail.id,
                    'service': nline.service.id,
                    'analysis': nline.analysis.id,
                    'analysis_origin': nline.analysis_origin,
                    'repetition': nline.repetition + i,
                    'laboratory': nline.laboratory.id,
                    'method': nline.method.id,
                    'device': nline.device.id if nline.device else None,
                    'initial_concentration': nline.initial_concentration,
                    'final_concentration': nline.final_concentration,
                    'initial_unit': (nline.initial_unit.id if
                        nline.initial_unit else None),
                    'final_unit': (nline.final_unit.id if
                        nline.final_unit else None),
                    'detection_limit': nline.detection_limit,
                    'quantification_limit': nline.quantification_limit,
                    'decimals': nline.decimals,
                    'report': nline.report,
                    'concentration_level': (nline.concentration_level.id if
                        nline.concentration_level else None),
                    'results_estimated_waiting': (
                        nline.results_estimated_waiting),
                    'department': (nline.department.id if
                        nline.department else None),
                    })
        Notebook.write([notebook], {
            'lines': [('create', to_create)],
            })

    def add_control(self, fraction):
        Planification = Pool().get('lims.planification')
        Planification.write([self.start.planification], {
            'controls': [('add', [fraction.id])],
            })

    def add_planification_detail(self, fraction):
        pool = Pool()
        Analysis = pool.get('lims.analysis')
        NotebookLine = pool.get('lims.notebook.line')
        PlanificationDetail = pool.get('lims.planification.detail')

        p_analysis_ids = []
        for p_analysis in self.start.planification.analysis:
            if p_analysis.type == 'analysis':
                p_analysis_ids.append(p_analysis.id)
            else:
                p_analysis_ids.extend(
                    Analysis.get_included_analysis_analysis(p_analysis.id))
        clause = [
            ('notebook.fraction', '=', fraction.id),
            ('analysis', 'in', p_analysis_ids),
            ('analysis.behavior', '!=', 'internal_relation'),
            ]
        if self.start.type == 'exist':
            clause.extend([
                ('result', 'in', (None, '')),
                ('end_date', '=', None),
                ('annulment_date', '=', None),
                ])
        else:
            clause.append(('planification', '=', None))
        notebook_lines = NotebookLine.search(clause)
        if notebook_lines:
            details_to_create = {}
            for nl in notebook_lines:
                f = nl.notebook.fraction.id
                s = nl.service.analysis.id
                if (f, s) not in details_to_create:
                    details_to_create[(f, s)] = []
                details_to_create[(f, s)].append({
                    'notebook_line': nl.id,
                    'planned_service': s,
                    'is_control': True,
                    })
            if details_to_create:
                for k, v in details_to_create.items():
                    details = PlanificationDetail.search([
                        ('planification', '=', self.start.planification.id),
                        ('fraction', '=', k[0]),
                        ('service_analysis', '=', k[1]),
                        ])
                    if details:
                        PlanificationDetail.write([details[0]], {
                            'details': [('create', v)],
                            })
                    else:
                        PlanificationDetail.create([{
                            'planification': self.start.planification.id,
                            'fraction': k[0],
                            'service_analysis': k[1],
                            'details': [('create', v)],
                            }])


class RemoveControlStart(ModelView):
    'Remove Control'
    __name__ = 'lims.planification.remove_control.start'

    controls = fields.Many2Many('lims.fraction', None, None, 'Controls',
        required=True, domain=[('id', 'in', Eval('controls_domain'))],
        depends=['controls_domain'])
    controls_domain = fields.Many2Many('lims.fraction', None, None,
        'Controls domain')


class RemoveControl(Wizard):
    'Remove Control'
    __name__ = 'lims.planification.remove_control'

    start = StateView('lims.planification.remove_control.start',
        'lims.lims_remove_control_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Remove', 'remove', 'tryton-ok', default=True),
            ])
    remove = StateTransition()

    def default_start(self, fields):
        Planification = Pool().get('lims.planification')
        planification = Planification(Transaction().context['active_id'])
        controls_domain = []
        for c in planification.controls:
            controls_domain.append(c.id)
        return {
            'controls_domain': controls_domain,
            }

    def transition_remove(self):
        planification_id = Transaction().context['active_id']
        control_ids = [c.id for c in self.start.controls]
        self._unlink_controls(planification_id, control_ids)
        return 'end'

    def _unlink_controls(self, planification_id, control_ids):
        pool = Pool()
        PlanificationFraction = pool.get('lims.planification-fraction')
        PlanificationDetail = pool.get('lims.planification.detail')

        controls = PlanificationFraction.search([
            ('planification', '=', planification_id),
            ('fraction', 'in', control_ids),
            ])
        if controls:
            PlanificationFraction.delete(controls)

        controls_details = PlanificationDetail.search([
            ('planification', '=', planification_id),
            ('fraction', 'in', control_ids),
            ])
        if controls_details:
            PlanificationDetail.delete(controls_details)


class AddAnalysisStart(ModelView):
    'Add Analysis'
    __name__ = 'lims.planification.add_analysis.start'

    laboratory = fields.Many2One('lims.laboratory', 'Laboratory')
    date_from = fields.Date('Date from', required=True, readonly=True)
    date_to = fields.Date('Date to', required=True, readonly=True)
    analysis = fields.Many2Many('lims.analysis', None, None,
        'Analysis/Sets/Groups', required=True,
        domain=[('id', 'in', Eval('analysis_domain'))],
        context={'date_from': Eval('date_from'), 'date_to': Eval('date_to')},
        depends=['analysis_domain', 'date_from', 'date_to'])
    analysis_domain = fields.Many2Many('lims.analysis', None, None,
        'Analysis domain')


class AddAnalysis(Wizard):
    'Add Analysis'
    __name__ = 'lims.planification.add_analysis'

    start = StateView('lims.planification.add_analysis.start',
        'lims.lims_add_analysis_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Add', 'add', 'tryton-ok', default=True),
            ])
    add = StateTransition()

    def default_start(self, fields):
        Planification = Pool().get('lims.planification')
        planification = Planification(Transaction().context['active_id'])
        analysis_domain = AddAnalysis._get_analysis_domain(
            planification.laboratory, planification.date_from,
            planification.date_to)

        return {
            'laboratory': planification.laboratory.id,
            'analysis_domain': analysis_domain,
            'date_from': planification.date_from,
            'date_to': planification.date_to,
            }

    @staticmethod
    def _get_analysis_domain(laboratory, date_from, date_to):
        pool = Pool()
        Planification = pool.get('lims.planification')
        Analysis = pool.get('lims.analysis')

        if not laboratory:
            return []

        asg_list = Planification._get_analysis_domain(laboratory)

        new_context = {}
        new_context['date_from'] = date_from
        new_context['date_to'] = date_to
        with Transaction().set_context(new_context):
            pending_fractions = Analysis.analysis_pending_fractions(asg_list)
        res = []
        for analysis, pending in iter(pending_fractions.items()):
            if pending > 0:
                res.append(analysis)
        return res

    def transition_add(self):
        Planification = Pool().get('lims.planification')

        planification = Planification(Transaction().context['active_id'])

        Planification.write([planification], {
            'analysis': [('remove', self.start.analysis)],
            })
        Planification.write([planification], {
            'analysis': [('add', self.start.analysis)],
            })
        return 'end'


class SearchFractionsNext(ModelView):
    'Search Fractions'
    __name__ = 'lims.planification.search_fractions.next'

    details = fields.Many2Many(
        'lims.planification.search_fractions.detail',
        None, None, 'Fractions to plan', depends=['details_domain'],
        domain=[('id', 'in', Eval('details_domain'))], required=True)
    details_domain = fields.One2Many(
        'lims.planification.search_fractions.detail',
        None, 'Fractions domain')


class SearchFractionsDetail(ModelSQL, ModelView):
    'Fraction to Plan'
    __name__ = 'lims.planification.search_fractions.detail'
    _table = 'lims_plan_search_fractions_detail'

    fraction = fields.Many2One('lims.fraction', 'Fraction', readonly=True)
    service_analysis = fields.Many2One('lims.analysis', 'Service',
        readonly=True)
    fraction_type = fields.Function(fields.Many2One('lims.fraction.type',
        'Fraction type'), 'get_fraction_field')
    label = fields.Function(fields.Char('Label'), 'get_fraction_field')
    product_type = fields.Many2One('lims.product.type', 'Product type')
    matrix = fields.Many2One('lims.matrix', 'Matrix')
    urgent = fields.Function(fields.Boolean('Urgent'), 'get_service_field')
    priority = fields.Function(fields.Integer('Priority'), 'get_service_field')
    report_date = fields.Function(fields.Date('Date agreed for result'),
        'get_service_field')
    session_id = fields.Integer('Session ID')

    @classmethod
    def __register__(cls, module_name):
        super(SearchFractionsDetail,
            cls).__register__(module_name)
        cursor = Transaction().connection.cursor()
        cursor.execute('DELETE FROM "' + cls._table + '"')

    @classmethod
    def __setup__(cls):
        super(SearchFractionsDetail, cls).__setup__()
        cls._order.insert(0, ('fraction', 'ASC'))
        cls._order.insert(1, ('service_analysis', 'ASC'))

    @classmethod
    def get_fraction_field(cls, details, names):
        result = {}
        for name in names:
            result[name] = {}
            if name == 'label':
                for d in details:
                    result[name][d.id] = getattr(d.fraction, name, None)
            elif name == 'fraction_type':
                for d in details:
                    field = getattr(d.fraction, 'type', None)
                    result[name][d.id] = field.id if field else None
            else:
                for d in details:
                    field = getattr(d.fraction, name, None)
                    result[name][d.id] = field.id if field else None
        return result

    @classmethod
    def search_fraction_field(cls, name, clause):
        return [('fraction.' + name,) + tuple(clause[1:])]

    @classmethod
    def get_service_field(cls, details, names):
        result = {}
        for name in names:
            result[name] = {}
            if name == 'urgent':
                for d in details:
                    result[name][d.id] = False
            elif name == 'priority':
                for d in details:
                    result[name][d.id] = 0
            else:
                for d in details:
                    result[name][d.id] = None
        for d in details:
            if d.fraction and d.service_analysis:
                for service in d.fraction.services:
                    if service.analysis == d.service_analysis:
                        for name in names:
                            result[name][d.id] = getattr(service, name)
        return result


class SearchFractions(Wizard):
    'Search Fractions'
    __name__ = 'lims.planification.search_fractions'

    start_state = 'search'
    search = StateTransition()
    next = StateView('lims.planification.search_fractions.next',
        'lims.lims_search_fractions_next_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Add', 'add', 'tryton-ok', default=True),
            ])
    add = StateTransition()

    def transition_search(self):
        pool = Pool()
        Planification = pool.get('lims.planification')
        PlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')
        PlanificationDetail = pool.get('lims.planification.detail')
        SearchFractionsDetail = pool.get(
            'lims.planification.search_fractions.detail')

        planification = Planification(Transaction().context['active_id'])

        service_detail = PlanificationServiceDetail.search([
            ('planification', '=', planification.id),
            ('is_control', '=', False),
            ('is_replanned', '=', False),
            ])
        if service_detail:
            PlanificationServiceDetail.delete(service_detail)

        details = PlanificationDetail.search([
            ('planification', '=', planification.id),
            ('details', '=', None),
            ])
        if details:
            PlanificationDetail.delete(details)

        fractions_added = []
        if not planification.analysis:
            self.next.details = fractions_added
            return 'next'

        data = self._get_service_details(planification)

        to_create = []
        for k, v in data.items():
            to_create.append({
                'session_id': self._session_id,
                'fraction': k[0],
                'service_analysis': k[1],
                'product_type': v['product_type'],
                'matrix': v['matrix'],
                })
        fractions_added = SearchFractionsDetail.create(to_create)

        self.next.details = fractions_added
        return 'next'

    def default_next(self, fields):
        details = [d.id for d in self.next.details]
        self.next.details = None
        return {
            'details': [],
            'details_domain': details,
            }

    def transition_add(self):
        pool = Pool()
        Planification = pool.get('lims.planification')
        PlanificationDetail = pool.get('lims.planification.detail')

        planification = Planification(Transaction().context['active_id'])

        records_added = ['(%s,%s)' % (d.fraction.id, d.service_analysis.id)
            for d in self.next.details]
        records_ids_added = ', '.join(str(x)
            for x in ['(0,0)'] + records_added)
        extra_where = (
            'AND (nb.fraction, srv.analysis) IN (' + records_ids_added + ') ')

        data = self._get_service_details(planification, extra_where)

        to_create = []
        for k, v in data.items():
            details = PlanificationDetail.search([
                ('planification', '=', planification.id),
                ('fraction', '=', k[0]),
                ('service_analysis', '=', k[1]),
                ])
            if details:
                PlanificationDetail.write([details[0]], {
                    'details': [('create', v)],
                    })
            else:
                to_create.append({
                    'planification': planification.id,
                    'fraction': k[0],
                    'service_analysis': k[1],
                    'details': [('create', v)],
                    })
        if to_create:
            PlanificationDetail.create(to_create)

        return 'end'

    def _get_service_details(self, planification, extra_where=''):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        PlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')
        NotebookLine = pool.get('lims.notebook.line')
        Notebook = pool.get('lims.notebook')
        Fraction = pool.get('lims.fraction')
        FractionType = pool.get('lims.fraction.type')
        Sample = pool.get('lims.sample')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        Service = pool.get('lims.service')
        Analysis = pool.get('lims.analysis')

        planification_details = PlanificationServiceDetail.search([
            ('planification.state', '=', 'preplanned'),
            ])
        planned_lines = [pd.notebook_line.id for pd in planification_details
            if pd.notebook_line]
        planned_lines_ids = ', '.join(str(x) for x in [0] + planned_lines)

        result = {}
        nlines_added = []
        for a in planification.analysis:
            analysis_id = a.id

            all_included_analysis = [analysis_id]
            all_included_analysis.extend(
                Analysis.get_included_analysis_analysis(analysis_id))
            all_included_analysis_ids = ', '.join(str(x)
                for x in all_included_analysis)
            service_where = ('AND ad.analysis IN (' +
                all_included_analysis_ids + ') ')

            if extra_where:
                sample_select = ' '
                sample_from = ''
            else:
                sample_select = ', smp.product_type, smp.matrix '
                sample_from = (
                    'INNER JOIN "' + Sample._table + '" smp '
                    'ON smp.id = frc.sample ')

            sql_select = (
                'SELECT nl.id, nb.fraction, srv.analysis' + sample_select)

            sql_from = (
                'FROM "' + NotebookLine._table + '" nl '
                'INNER JOIN "' + Analysis._table + '" nla '
                'ON nla.id = nl.analysis '
                'INNER JOIN "' + Notebook._table + '" nb '
                'ON nb.id = nl.notebook '
                'INNER JOIN "' + Fraction._table + '" frc '
                'ON frc.id = nb.fraction '
                'INNER JOIN "' + FractionType._table + '" ft '
                'ON ft.id = frc.type '
                'INNER JOIN "' + EntryDetailAnalysis._table + '" ad '
                'ON ad.id = nl.analysis_detail '
                'INNER JOIN "' + Service._table + '" srv '
                'ON srv.id = nl.service ' +
                sample_from)

            sql_where = (
                'WHERE nl.planification IS NULL '
                'AND nl.annulled = FALSE '
                'AND ft.plannable = TRUE '
                'AND nl.id NOT IN (' + planned_lines_ids + ') '
                'AND nl.laboratory = %s '
                'AND nla.behavior != \'internal_relation\' '
                'AND ad.confirmation_date::date >= %s::date '
                'AND ad.confirmation_date::date <= %s::date ' +
                service_where + extra_where)

            sql_order = (
                'ORDER BY nb.fraction ASC, srv.analysis ASC')

            with Transaction().set_user(0):
                cursor.execute(sql_select + sql_from + sql_where + sql_order,
                    (planification.laboratory.id, planification.date_from,
                    planification.date_to,))
            notebook_lines = cursor.fetchall()
            if not notebook_lines:
                continue
            if extra_where:
                for nl in notebook_lines:
                    f_ = nl[1]
                    s_ = nl[2]
                    if (f_, s_) not in result:
                        result[(f_, s_)] = []
                    if nl[0] not in nlines_added:
                        nlines_added.append(nl[0])
                        result[(f_, s_)].append({
                            'notebook_line': nl[0],
                            'planned_service': a.id,
                            })
            else:
                for nl in notebook_lines:
                    f_ = nl[1]
                    s_ = nl[2]
                    result[(f_, s_)] = {
                        'product_type': nl[3],
                        'matrix': nl[4],
                        }

        return result


class SearchPlannedFractionsStart(ModelView):
    'Search Planned Fractions'
    __name__ = 'lims.planification.search_planned_fractions.start'

    laboratory = fields.Many2One('lims.laboratory', 'Laboratory')
    date_from = fields.Date('Date from', required=True)
    date_to = fields.Date('Date to', required=True)
    analysis = fields.Many2Many('lims.planification-analysis',
        'planification', 'analysis', 'Analysis/Sets/Groups',
        domain=[('id', 'in', Eval('analysis_domain'))],
        depends=['analysis_domain'], required=True)
    analysis_domain = fields.One2Many('lims.analysis', None,
        'Analysis domain')


class SearchPlannedFractionsNext(ModelView):
    'Search Planned Fractions'
    __name__ = 'lims.planification.search_planned_fractions.next'

    details = fields.Many2Many(
        'lims.planification.search_planned_fractions.detail',
        None, None, 'Fractions to replan', depends=['details_domain'],
        domain=[('id', 'in', Eval('details_domain'))], required=True)
    details_domain = fields.One2Many(
        'lims.planification.search_planned_fractions.detail',
        None, 'Fractions domain')


class SearchPlannedFractionsDetail(ModelSQL, ModelView):
    'Fraction to Replan'
    __name__ = 'lims.planification.search_planned_fractions.detail'
    _table = 'lims_plan_search_planned_fractions_detail'

    fraction = fields.Many2One('lims.fraction', 'Fraction', readonly=True)
    service_analysis = fields.Many2One('lims.analysis', 'Service',
        readonly=True)
    fraction_type = fields.Function(fields.Many2One('lims.fraction.type',
        'Fraction type'), 'get_fraction_field')
    label = fields.Function(fields.Char('Label'), 'get_fraction_field')
    product_type = fields.Many2One('lims.product.type', 'Product type')
    matrix = fields.Many2One('lims.matrix', 'Matrix')
    urgent = fields.Function(fields.Boolean('Urgent'), 'get_service_field')
    priority = fields.Function(fields.Integer('Priority'), 'get_service_field')
    report_date = fields.Function(fields.Date('Date agreed for result'),
        'get_service_field')
    session_id = fields.Integer('Session ID')

    @classmethod
    def __register__(cls, module_name):
        super(SearchPlannedFractionsDetail,
            cls).__register__(module_name)
        cursor = Transaction().connection.cursor()
        cursor.execute('DELETE FROM "' + cls._table + '"')

    @classmethod
    def __setup__(cls):
        super(SearchPlannedFractionsDetail, cls).__setup__()
        cls._order.insert(0, ('fraction', 'ASC'))
        cls._order.insert(1, ('service_analysis', 'ASC'))

    @classmethod
    def get_fraction_field(cls, details, names):
        result = {}
        for name in names:
            result[name] = {}
            if name == 'label':
                for d in details:
                    result[name][d.id] = getattr(d.fraction, name, None)
            elif name == 'fraction_type':
                for d in details:
                    field = getattr(d.fraction, 'type', None)
                    result[name][d.id] = field.id if field else None
            else:
                for d in details:
                    field = getattr(d.fraction, name, None)
                    result[name][d.id] = field.id if field else None
        return result

    @classmethod
    def search_fraction_field(cls, name, clause):
        return [('fraction.' + name,) + tuple(clause[1:])]

    @classmethod
    def get_service_field(cls, details, names):
        result = {}
        for name in names:
            result[name] = {}
            if name == 'urgent':
                for d in details:
                    result[name][d.id] = False
            elif name == 'priority':
                for d in details:
                    result[name][d.id] = 0
            else:
                for d in details:
                    result[name][d.id] = None
        for d in details:
            if d.fraction and d.service_analysis:
                for service in d.fraction.services:
                    if service.analysis == d.service_analysis:
                        for name in names:
                            result[name][d.id] = getattr(service, name)
        return result


class SearchPlannedFractions(Wizard):
    'Search Planned Fractions'
    __name__ = 'lims.planification.search_planned_fractions'

    start = StateView('lims.planification.search_planned_fractions.start',
        'lims.lims_search_planned_fractions_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search', 'search', 'tryton-forward', default=True),
            ])
    search = StateTransition()
    next = StateView('lims.planification.search_planned_fractions.next',
        'lims.lims_search_planned_fractions_next_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Add', 'add', 'tryton-ok', default=True),
            ])
    add = StateTransition()

    def default_start(self, fields):
        Planification = Pool().get('lims.planification')
        planification = Planification(Transaction().context['active_id'])
        analysis = [a.id for a in planification.analysis]
        return {
            'laboratory': planification.laboratory.id,
            'analysis': analysis,
            'analysis_domain': analysis,
            'date_from': planification.date_from,
            'date_to': planification.date_to,
            }

    def transition_search(self):
        pool = Pool()
        SearchPlannedFractionsDetail = pool.get(
            'lims.planification.search_planned_fractions.detail')

        data = self._get_service_details()

        to_create = []
        for k, v in data.items():
            to_create.append({
                'session_id': self._session_id,
                'fraction': k[0],
                'service_analysis': k[1],
                'product_type': v['product_type'],
                'matrix': v['matrix'],
                })
        fractions_added = SearchPlannedFractionsDetail.create(to_create)

        self.next.details = fractions_added
        return 'next'

    def default_next(self, fields):
        details = [d.id for d in self.next.details]
        self.next.details = None
        return {
            'details': [],
            'details_domain': details,
            }

    def transition_add(self):
        pool = Pool()
        Planification = pool.get('lims.planification')
        PlanificationDetail = pool.get('lims.planification.detail')

        planification = Planification(Transaction().context['active_id'])

        records_added = ['(%s,%s)' % (d.fraction.id, d.service_analysis.id)
            for d in self.next.details]
        records_ids_added = ', '.join(str(x)
            for x in ['(0,0)'] + records_added)
        extra_where = (
            'AND (nb.fraction, srv.analysis) IN (' + records_ids_added + ') ')

        data = self._get_service_details(extra_where)

        to_create = []
        for k, v in data.items():
            details = PlanificationDetail.search([
                ('planification', '=', planification.id),
                ('fraction', '=', k[0]),
                ('service_analysis', '=', k[1]),
                ])
            if details:
                PlanificationDetail.write([details[0]], {
                    'details': [('create', v)],
                    })
            else:
                to_create.append({
                    'planification': planification.id,
                    'fraction': k[0],
                    'service_analysis': k[1],
                    'details': [('create', v)],
                    })
        if to_create:
            PlanificationDetail.create(to_create)

        return 'end'

    def _get_service_details(self, extra_where=''):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        Notebook = pool.get('lims.notebook')
        Fraction = pool.get('lims.fraction')
        FractionType = pool.get('lims.fraction.type')
        Sample = pool.get('lims.sample')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        Service = pool.get('lims.service')
        Analysis = pool.get('lims.analysis')

        result = {}
        nlines_added = []
        for a in self.start.analysis:
            analysis_id = a.id

            all_included_analysis = [analysis_id]
            all_included_analysis.extend(
                Analysis.get_included_analysis_analysis(analysis_id))
            all_included_analysis_ids = ', '.join(str(x)
                for x in all_included_analysis)
            service_where = ('AND ad.analysis IN (' +
                all_included_analysis_ids + ') ')

            excluded_fractions = self.get_control_fractions_excluded(
                self.start.laboratory.id, service_where)
            excluded_fractions_ids = ', '.join(str(x)
                for x in [0] + excluded_fractions)

            if extra_where:
                sample_select = ' '
                sample_from = ''
            else:
                sample_select = ', smp.product_type, smp.matrix '
                sample_from = (
                    'INNER JOIN "' + Sample._table + '" smp '
                    'ON smp.id = frc.sample ')

            sql_select = (
                'SELECT nl.id, nb.fraction, srv.analysis' + sample_select)

            sql_from = (
                'FROM "' + NotebookLine._table + '" nl '
                'INNER JOIN "' + Analysis._table + '" nla '
                'ON nla.id = nl.analysis '
                'INNER JOIN "' + Notebook._table + '" nb '
                'ON nb.id = nl.notebook '
                'INNER JOIN "' + Fraction._table + '" frc '
                'ON frc.id = nb.fraction '
                'INNER JOIN "' + FractionType._table + '" ft '
                'ON ft.id = frc.type '
                'INNER JOIN "' + EntryDetailAnalysis._table + '" ad '
                'ON ad.id = nl.analysis_detail '
                'INNER JOIN "' + Service._table + '" srv '
                'ON srv.id = nl.service ' +
                sample_from)

            sql_where = (
                'WHERE nl.planification IS NOT NULL '
                'AND ft.plannable = TRUE '
                'AND nl.end_date IS NULL '
                'AND nl.laboratory = %s '
                'AND nla.behavior != \'internal_relation\' '
                'AND nb.fraction NOT IN (' + excluded_fractions_ids + ') '
                'AND ad.confirmation_date::date >= %s::date '
                'AND ad.confirmation_date::date <= %s::date ' +
                service_where + extra_where)

            sql_order = (
                'ORDER BY nb.fraction ASC, srv.analysis ASC')

            with Transaction().set_user(0):
                cursor.execute(sql_select + sql_from + sql_where + sql_order,
                    (self.start.laboratory.id, self.start.date_from,
                    self.start.date_to,))
            notebook_lines = cursor.fetchall()
            if notebook_lines:
                if extra_where:
                    for nl in notebook_lines:
                        f_ = nl[1]
                        s_ = nl[2]
                        if (f_, s_) not in result:
                            result[(f_, s_)] = []
                        if nl[0] not in nlines_added:
                            nlines_added.append(nl[0])
                            result[(f_, s_)].append({
                                'notebook_line': nl[0],
                                'planned_service': a.id,
                                'is_replanned': True,
                                })
                else:
                    for nl in notebook_lines:
                        f_ = nl[1]
                        s_ = nl[2]
                        result[(f_, s_)] = {
                            'product_type': nl[3],
                            'matrix': nl[4],
                            }

        return result

    def get_control_fractions_excluded(self, laboratory, search_clause):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        Notebook = pool.get('lims.notebook')
        Fraction = pool.get('lims.fraction')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        Config = pool.get('lims.configuration')

        config = Config(1)
        special_types = []
        if config.rm_fraction_type:
            special_types.append(config.rm_fraction_type.id)
        if config.bmz_fraction_type:
            special_types.append(config.bmz_fraction_type.id)
        if config.bre_fraction_type:
            special_types.append(config.bre_fraction_type.id)
        if config.mrt_fraction_type:
            special_types.append(config.mrt_fraction_type.id)
        special_types_ids = ', '.join(str(x) for x in special_types)

        cursor.execute('SELECT nl.analysis, nl.notebook '
            'FROM "' + NotebookLine._table + '" nl '
                'INNER JOIN "' + Notebook._table + '" nb '
                'ON nb.id = nl.notebook '
                'INNER JOIN "' + Fraction._table + '" frc '
                'ON frc.id = nb.fraction '
                'INNER JOIN "' + EntryDetailAnalysis._table + '" ad '
                'ON ad.id = nl.analysis_detail '
            'WHERE nl.planification IS NOT NULL '
                'AND nl.end_date IS NULL '
                'AND nl.laboratory = %s '
                'AND frc.type IN (' + special_types_ids + ') ' +
                search_clause,
                (laboratory,))
        notebook_lines = cursor.fetchall()
        if not notebook_lines:
            return []

        excluded_fractions = []
        analysis = []
        notebooks_id = []
        for nbl in notebook_lines:
            analysis.append(nbl[0])
            notebooks_id.append(nbl[1])
        analysis = set(analysis)

        notebooks = Notebook.search([
            ('id', 'in', list(set(notebooks_id))),
            ])
        for nb in notebooks:
            cursor.execute('SELECT analysis '
                'FROM "' + NotebookLine._table + '" '
                'WHERE notebook = %s', (nb.id,))
            nbl_analysis_ids = set(cursor.fetchall())
            if not analysis.issubset(nbl_analysis_ids):
                excluded_fractions.append(nb.fraction.id)
        return list(set(excluded_fractions))


class CreateFractionControlStart(ModelView):
    'Create Fraction Control'
    __name__ = 'lims.planification.create_fraction_con.start'

    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        required=True)
    type = fields.Selection([
        ('coi', 'COI'),
        ('mrc', 'MRC'),
        ('sla', 'SLA'),
        ], 'Control type', sort=False, required=True)
    product_type = fields.Many2One('lims.product.type', 'Product type',
        required=True,
        domain=[('id', 'in', Eval('product_type_domain'))],
        depends=['product_type_domain'])
    product_type_domain = fields.Function(fields.Many2Many(
        'lims.product.type', None, None, 'Product type domain'),
        'on_change_with_product_type_domain')
    matrix = fields.Many2One('lims.matrix', 'Matrix', required=True,
        domain=[('id', 'in', Eval('matrix_domain'))],
        depends=['matrix_domain'])
    matrix_domain = fields.Function(fields.Many2Many('lims.matrix',
        None, None, 'Matrix domain'),
        'on_change_with_matrix_domain')
    analysis = fields.Many2Many('lims.planification-analysis',
        'planification', 'analysis', 'Analysis/Sets/Groups',
        domain=[('id', 'in', Eval('analysis_domain'))],
        depends=['analysis_domain'])
    analysis_domain = fields.Function(fields.One2Many('lims.analysis',
        None, 'Analysis domain'), 'on_change_with_analysis_domain')
    label = fields.Char('Label')
    concentration_level = fields.Many2One('lims.concentration.level',
        'Concentration level', states={
            'invisible': Bool(Eval('concentration_level_invisible')),
            }, depends=['concentration_level_invisible'])
    concentration_level_invisible = fields.Boolean(
        'Concentration level invisible')
    sample_created = fields.Many2One('lims.sample', 'Sample created')

    @fields.depends('type')
    def on_change_with_concentration_level_invisible(self, name=None):
        Config = Pool().get('lims.configuration')
        config = Config(1)
        if self.type == 'coi':
            if (config.coi_fraction_type and
                    config.coi_fraction_type.control_charts):
                return False
        elif self.type == 'mrc':
            if (config.mrc_fraction_type and
                    config.mrc_fraction_type.control_charts):
                return False
        elif self.type == 'sla':
            if (config.sla_fraction_type and
                    config.sla_fraction_type.control_charts):
                return False
        return True

    @fields.depends('laboratory', 'product_type', 'matrix')
    def on_change_with_analysis_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        AnalysisLaboratory = pool.get('lims.analysis-laboratory')
        Analysis = pool.get('lims.analysis')
        Typification = pool.get('lims.typification')
        CalculatedTypification = pool.get('lims.typification.calculated')

        if not self.laboratory or not self.product_type or not self.matrix:
            return []

        cursor.execute('SELECT DISTINCT(analysis) '
            'FROM "' + AnalysisLaboratory._table + '" '
            'WHERE laboratory = %s', (self.laboratory.id,))
        analysis_sets_list = [a[0] for a in cursor.fetchall()]
        if not analysis_sets_list:
            return []
        lab_analysis_ids = ', '.join(str(a) for a in
                analysis_sets_list)

        groups_list = []
        groups = Analysis.search([
            ('type', '=', 'group'),
            ])
        if groups:
            for group in groups:
                available = True

                ia = Analysis.get_included_analysis_analysis(
                    group.id)
                if not ia:
                    continue
                included_ids = ', '.join(str(a) for a in ia)

                cursor.execute('SELECT id '
                    'FROM "' + Analysis._table + '" '
                    'WHERE id IN (' + included_ids + ') '
                        'AND id NOT IN (' + lab_analysis_ids +
                        ')')
                if cursor.fetchone():
                    available = False

                if available:
                    groups_list.append(group.id)

        analysis_domain = analysis_sets_list + groups_list
        analysis_domain_ids = ', '.join(str(a) for a in analysis_domain)

        cursor.execute('SELECT DISTINCT(typ.analysis) '
            'FROM ('
                'SELECT t.analysis FROM "' + Typification._table + '" t '
                'WHERE t.product_type = %s AND t.matrix = %s AND t.valid '
            'UNION '
                'SELECT ct.analysis FROM "' + CalculatedTypification._table +
                '" ct '
                'WHERE ct.product_type = %s AND ct.matrix = %s'
            ') AS typ '
            'WHERE typ.analysis IN (' + analysis_domain_ids + ')',
            (self.product_type.id, self.matrix.id,
            self.product_type.id, self.matrix.id))
        typified_analysis = [a[0] for a in cursor.fetchall()]
        return typified_analysis

    @staticmethod
    def default_product_type_domain():
        cursor = Transaction().connection.cursor()
        Typification = Pool().get('lims.typification')

        cursor.execute('SELECT DISTINCT(product_type) '
                'FROM "' + Typification._table + '" '
                'WHERE valid')
        return [x[0] for x in cursor.fetchall()]

    def on_change_with_product_type_domain(self, name=None):
        return self.default_product_type_domain()

    @fields.depends('product_type')
    def on_change_product_type(self):
        matrix = None
        if self.product_type:
            matrixs = self.on_change_with_matrix_domain()
            if len(matrixs) == 1:
                matrix = matrixs[0]
        self.matrix = matrix

    @fields.depends('product_type')
    def on_change_with_matrix_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        Typification = Pool().get('lims.typification')

        if not self.product_type:
            return []

        cursor.execute('SELECT DISTINCT(matrix) '
                'FROM "' + Typification._table + '" '
                'WHERE product_type = %s '
                'AND valid',
                (self.product_type.id,))
        return [x[0] for x in cursor.fetchall()]

    @fields.depends('type', 'product_type', 'matrix')
    def on_change_with_label(self, name=None):
        label = ''
        if self.type == 'coi':
            label += 'COI'
        elif self.type == 'mrc':
            label += 'MRC'
        elif self.type == 'sla':
            label += 'SLA'
        if self.product_type:
            label += ' ' + self.product_type.code
        if self.matrix:
            label += ' ' + self.matrix.code
        return label


class CreateFractionControl(Wizard):
    'Create Fraction Control'
    __name__ = 'lims.planification.create_fraction_con'

    start = StateView('lims.planification.create_fraction_con.start',
        'lims.lims_create_fraction_con_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Create', 'create_', 'tryton-ok', default=True),
            ])
    create_ = StateTransition()
    open_ = StateAction('lims.act_lims_sample_list')

    @classmethod
    def __setup__(cls):
        super(CreateFractionControl, cls).__setup__()
        cls._error_messages.update({
            'no_entry_control': ('There is no default entry control for this '
                'work year'),
            'no_coi_fraction_type': ('There is no COI fraction type '
                'configured'),
            'no_mrc_fraction_type': ('There is no MRC fraction type '
                'configured'),
            'no_sla_fraction_type': ('There is no SLA fraction type '
                'configured'),
            'no_coi_default_configuration': ('Missing default configuration '
                'for COI fraction type'),
            'no_mrc_default_configuration': ('Missing default configuration '
                'for MRC fraction type'),
            'no_sla_default_configuration': ('Missing default configuration '
                'for SLA fraction type'),
            'no_concentration_level': ('Missing concentration level '
                'for this control type'),
            })

    def default_start(self, fields):
        defaults = {
            'laboratory': Transaction().context.get('laboratory', None),
            'concentration_level_invisible': True,
            }
        return defaults

    def transition_create_(self):
        control = self.create_control()
        self.start.sample_created = control.sample.id
        return 'open_'

    def create_control(self):
        pool = Pool()
        Config = pool.get('lims.configuration')
        LabWorkYear = pool.get('lims.lab.workyear')
        Entry = pool.get('lims.entry')
        Sample = pool.get('lims.sample')
        Fraction = pool.get('lims.fraction')
        Service = pool.get('lims.service')
        NotebookLine = pool.get('lims.notebook.line')

        config = Config(1)
        if self.start.type == 'coi':
            if not config.coi_fraction_type:
                self.raise_user_error('no_coi_fraction_type')
            fraction_type = config.coi_fraction_type
            if (not fraction_type.default_package_type or
                    not fraction_type.default_fraction_state):
                self.raise_user_error('no_coi_default_configuration')
        elif self.start.type == 'mrc':
            if not config.mrc_fraction_type:
                self.raise_user_error('no_mrc_fraction_type')
            fraction_type = config.mrc_fraction_type
            if (not fraction_type.default_package_type or
                    not fraction_type.default_fraction_state):
                self.raise_user_error('no_mrc_default_configuration')
        elif self.start.type == 'sla':
            if not config.sla_fraction_type:
                self.raise_user_error('no_sla_fraction_type')
            fraction_type = config.sla_fraction_type
            if (not fraction_type.default_package_type or
                    not fraction_type.default_fraction_state):
                self.raise_user_error('no_sla_default_configuration')

        if (fraction_type.control_charts and not
                self.start.concentration_level):
            self.raise_user_error('no_concentration_level')

        workyear_id = LabWorkYear.find()
        workyear = LabWorkYear(workyear_id)
        if not workyear.default_entry_control:
            self.raise_user_error('no_entry_control')

        laboratory = self.start.laboratory
        entry = Entry(workyear.default_entry_control.id)
        obj_description = self._get_obj_description(self.start)

        # new sample
        new_sample, = Sample.create([{
            'entry': entry.id,
            'date': datetime.now(),
            'product_type': self.start.product_type.id,
            'matrix': self.start.matrix.id,
            'zone': entry.party.entry_zone.id,
            'label': self.start.label,
            'obj_description': obj_description,
            'packages_quantity': 1,
            'fractions': [],
            }])

        # new fraction
        fraction_default = {
            'sample': new_sample.id,
            'type': fraction_type.id,
            'storage_location': laboratory.related_location.id,
            'packages_quantity': 1,
            'package_type': fraction_type.default_package_type.id,
            'fraction_state': fraction_type.default_fraction_state.id,
            'services': [],
            'con_type': self.start.type,
            }
        if fraction_type.max_storage_time:
            fraction_default['storage_time'] = fraction_type.max_storage_time
        elif laboratory.related_location.storage_time:
            fraction_default['storage_time'] = (
                laboratory.related_location.storage_time)
        else:
            fraction_default['storage_time'] = 3
        new_fraction, = Fraction.create([fraction_default])

        # new services
        services_default = []
        for p_analysis in self.start.analysis:
            laboratory_id = (laboratory.id if p_analysis.type != 'group'
                else None)
            method_id = None
            if new_sample.typification_domain:
                for t in new_sample.typification_domain:
                    if (t.analysis.id == p_analysis.id and
                            t.by_default is True):
                        method_id = t.method.id
            device_id = None
            if p_analysis.devices:
                for d in p_analysis.devices:
                    if (d.laboratory.id == laboratory.id and
                            d.by_default is True):
                        device_id = d.device.id
            services_default.append({
                'fraction': new_fraction.id,
                'analysis': p_analysis.id,
                'laboratory': laboratory_id,
                'method': method_id,
                'device': device_id,
                })
        for service in services_default:
            new_service, = Service.create([service])

            # new analysis details (on service create)

        # confirm fraction: new notebook and stock move
        Fraction.confirm([new_fraction])

        # Edit notebook lines
        if fraction_type.control_charts:
            notebook_lines = NotebookLine.search([
                ('notebook.fraction', '=', new_fraction.id),
                ])
            if notebook_lines:
                defaults = {
                    'concentration_level': self.start.concentration_level.id,
                    }
                NotebookLine.write(notebook_lines, defaults)

        return new_fraction

    def _get_obj_description(self, sample):
        cursor = Transaction().connection.cursor()
        ObjectiveDescription = Pool().get('lims.objective_description')

        if not sample.product_type or not sample.matrix:
            return None

        cursor.execute('SELECT id '
            'FROM "' + ObjectiveDescription._table + '" '
            'WHERE product_type = %s '
                'AND matrix = %s',
            (sample.product_type.id, sample.matrix.id))
        res = cursor.fetchone()
        return res and res[0] or None

    def do_open_(self, action):
        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', '=', self.start.sample_created.id),
            ])
        return action, {}


class ReleaseFractionStart(ModelView):
    'Release Fraction'
    __name__ = 'lims.planification.release_fraction.start'

    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        required=True)
    date_from = fields.Date('Date from', required=True)
    date_to = fields.Date('Date to', required=True)


class ReleaseFractionEmpty(ModelView):
    'Release Fraction'
    __name__ = 'lims.planification.release_fraction.empty'


class ReleaseFractionResult(ModelView):
    'Release Fraction'
    __name__ = 'lims.planification.release_fraction.result'

    fractions = fields.Many2Many('lims.planification.detail', None, None,
        'Fractions', required=True,
        domain=[('id', 'in', Eval('fractions_domain'))],
        depends=['fractions_domain'])
    fractions_domain = fields.One2Many('lims.planification.detail', None,
        'Fractions domain')


class ReleaseFraction(Wizard):
    'Release Fraction'
    __name__ = 'lims.planification.release_fraction'

    start = StateView('lims.planification.release_fraction.start',
        'lims.lims_planification_release_fraction_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search', 'search', 'tryton-forward', default=True),
            ])
    search = StateTransition()
    empty = StateView('lims.planification.release_fraction.empty',
        'lims.lims_planification_release_fraction_empty_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search again', 'start', 'tryton-forward', default=True),
            ])
    result = StateView('lims.planification.release_fraction.result',
        'lims.lims_planification_release_fraction_result_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Release', 'release', 'tryton-ok', default=True),
            ])
    release = StateTransition()

    def default_start(self, fields):
        res = {}
        for field in ('date_from', 'date_to'):
            if (hasattr(self.start, field) and getattr(self.start, field)):
                res[field] = getattr(self.start, field)
        if (hasattr(self.start, 'laboratory') and
                getattr(self.start, 'laboratory')):
            res['laboratory'] = getattr(self.start, 'laboratory').id
        else:
            res['laboratory'] = Transaction().context.get('laboratory', None)
        return res

    def transition_search(self):
        PlanificationDetail = Pool().get('lims.planification.detail')

        details = PlanificationDetail.search([
            ('planification.laboratory', '=', self.start.laboratory.id),
            ('planification.start_date', '>=', self.start.date_from),
            ('planification.start_date', '<=', self.start.date_to),
            ('planification.state', '!=', 'draft'),
            ])
        if details:
            fractions = []
            for detail in details:
                available = True
                for service_detail in detail.details:
                    if service_detail.is_control:
                        available = False
                        break
                    nline = service_detail.notebook_line
                    if not nline:
                        available = False
                        break
                    if (nline.result or nline.converted_result or
                            nline.literal_result or nline.end_date or
                            nline.annulment_date):
                        available = False
                        break
                if available:
                    fractions.append(detail)

            if fractions:
                self.result.fractions = fractions
                return 'result'
        return 'empty'

    def default_result(self, fields):
        fractions = [f.id for f in self.result.fractions]
        self.result.fractions = None
        return {
            'fractions_domain': fractions,
            }

    def transition_release(self):
        self._re_update_laboratory_notebook()
        self._re_update_analysis_detail()
        self._unlink_fractions()
        return 'end'

    def _re_update_laboratory_notebook(self):
        NotebookLine = Pool().get('lims.notebook.line')
        for detail in self.result.fractions:
            for service_detail in detail.details:
                if (not service_detail.is_control and
                        service_detail.notebook_line):
                    notebook_line = NotebookLine(
                        service_detail.notebook_line.id)
                    notebook_line.start_date = None
                    notebook_line.laboratory_professionals = []
                    notebook_line.planification = None
                    notebook_line.controls = []
                    notebook_line.save()

    def _re_update_analysis_detail(self):
        EntryDetailAnalysis = Pool().get('lims.entry.detail.analysis')
        analysis_detail_ids = []
        for detail in self.result.fractions:
            for service_detail in detail.details:
                if (not service_detail.is_control and
                        service_detail.notebook_line and
                        service_detail.notebook_line.analysis_detail):
                    analysis_detail_ids.append(
                        service_detail.notebook_line.analysis_detail.id)
        analysis_details = EntryDetailAnalysis.search([
            ('id', 'in', analysis_detail_ids),
            ])
        if analysis_details:
            EntryDetailAnalysis.write(analysis_details, {
                'state': 'unplanned',
                })

    def _unlink_fractions(self):
        pool = Pool()
        PlanificationServiceDetail = Pool().get(
            'lims.planification.service_detail')
        PlanificationDetail = pool.get('lims.planification.detail')

        details_ids = []
        service_details_ids = []
        for detail in self.result.fractions:
            for service_detail in detail.details:
                if not service_detail.is_control:
                    service_details_ids.append(service_detail.id)
                    details_ids.append(service_detail.detail.id)

        service_detail = PlanificationServiceDetail.search([
            ('id', 'in', service_details_ids),
            ])
        if service_detail:
            PlanificationServiceDetail.delete(service_detail)

        details = PlanificationDetail.search([
            ('id', 'in', details_ids),
            ('details', '=', None),
            ])
        if details:
            PlanificationDetail.delete(details)


class QualificationSituations(ModelView):
    'Technicians Qualification'
    __name__ = 'lims.planification.qualification.situations'

    situations = fields.Many2Many('lims.planification.qualification.situation',
        None, None, 'Situations')
    total = fields.Integer('Total')
    index = fields.Integer('Index')


class QualificationSituation(ModelSQL, ModelView):
    'Qualification Situation'
    __name__ = 'lims.planification.qualification.situation'

    method = fields.Many2One('lims.lab.method', 'Method', readonly=True)
    professional = fields.Many2One('lims.laboratory.professional',
        'Professional', readonly=True)
    situation = fields.Integer('Situation', readonly=True)
    session_id = fields.Integer('Session ID')

    @classmethod
    def __register__(cls, module_name):
        super(QualificationSituation,
            cls).__register__(module_name)
        cursor = Transaction().connection.cursor()
        cursor.execute('DELETE FROM "' + cls._table + '"')


class QualificationAction(ModelSQL):
    'Qualification Action'
    __name__ = 'lims.planification.qualification.action'

    method = fields.Many2One('lims.lab.method', 'Method')
    professional = fields.Many2One('lims.laboratory.professional',
        'Professional')
    action = fields.Integer('Action')
    session_id = fields.Integer('Session ID')

    @classmethod
    def __register__(cls, module_name):
        super(QualificationAction,
            cls).__register__(module_name)
        cursor = Transaction().connection.cursor()
        cursor.execute('DELETE FROM "' + cls._table + '"')


class QualificationSituation2(ModelView):
    'Technicians Qualification'
    __name__ = 'lims.planification.qualification.situation.2'

    method = fields.Many2One('lims.lab.method', 'Method', readonly=True)
    professional = fields.Many2One('lims.laboratory.professional',
        'Professional', readonly=True)


class QualificationSituation3(ModelView):
    'Technicians Qualification'
    __name__ = 'lims.planification.qualification.situation.3'

    method = fields.Many2One('lims.lab.method', 'Method', readonly=True)
    professional = fields.Many2One('lims.laboratory.professional',
        'Professional', readonly=True)


class QualificationSituation4(ModelView):
    'Technicians Qualification'
    __name__ = 'lims.planification.qualification.situation.4'

    methods = fields.Text('Methods', readonly=True)


class TechniciansQualification(Wizard):
    'Technicians Qualification'
    __name__ = 'lims.planification.technicians_qualification'

    situations = StateView('lims.planification.qualification.situations',
        'lims.lims_qualification_situations_view_form', [])
    start = StateTransition()
    next_ = StateTransition()
    confirm = StateTransition()

    sit2 = StateView('lims.planification.qualification.situation.2',
        'lims.lims_qualification_situation_2_view_form', [
            Button('Qualify', 'sit2_op1', 'tryton-ok', default=True),
            Button('New Training', 'sit2_op2', 'tryton-ok'),
            Button('Cancel', 'end', 'tryton-cancel'),
            ])
    sit2_op1 = StateTransition()
    sit2_op2 = StateTransition()

    sit3 = StateView('lims.planification.qualification.situation.3',
        'lims.lims_qualification_situation_3_view_form', [
            Button('Requalify', 'sit3_op1', 'tryton-ok', default=True),
            Button('Cancel', 'end', 'tryton-cancel'),
            ])
    sit3_op1 = StateTransition()

    sit4 = StateView('lims.planification.qualification.situation.4',
        'lims.lims_qualification_situation_4_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            ])

    def transition_start(self):
        pool = Pool()
        Planification = pool.get('lims.planification')
        PlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')
        LabProfessionalMethod = pool.get('lims.lab.professional.method')
        QualificationSituation = pool.get(
            'lims.planification.qualification.situation')

        planification = Planification(Transaction().context['active_id'])

        planification_details = PlanificationServiceDetail.search([
            ('planification', '=', planification.id),
            ])

        situations = {}
        for detail in planification_details:
            method = (detail.notebook_line.method if detail.notebook_line
                else None)
            if method:
                for technician in detail.staff_responsible:
                    key = (technician.id, method.id)
                    if key in situations:
                        continue
                    situations[key] = 0
                    qualifications = LabProfessionalMethod.search([
                        ('professional', '=', technician.id),
                        ('method', '=', method.id),
                        ('type', '=', 'preparation'),
                        ])
                    if not qualifications:
                        situations[key] = 1
                    else:
                        if qualifications[0].state == 'training':
                            situations[key] = 2
                        elif (qualifications[0].state in
                                ('qualified', 'requalified')):
                            situations[key] = 3

        if situations:
            self.situations.situations = QualificationSituation.create([{
                'session_id': self._session_id,
                'professional': k[0],
                'method': k[1],
                'situation': v,
                } for k, v in situations.items()])
            self.situations.total = len(self.situations.situations)
            self.situations.index = 0
            return 'next_'
        return self._confirm()

    def transition_next_(self):

        data = self.situations.situations[self.situations.index]
        if data.situation == 1:
            return self.situation_1(data)
        elif data.situation == 2:
            return self.situation_2(data)
        elif data.situation == 3:
            return self.situation_3(data)
        return self._continue()

    def situation_1(self, data):
        # The technician has not the method. Write a new training directly.
        QualificationAction = Pool().get(
            'lims.planification.qualification.action')

        QualificationAction.create([{
            'session_id': self._session_id,
            'professional': data.professional.id,
            'method': data.method.id,
            'action': 1,
            }])
        return self._continue()

    def situation_2(self, data):
        # The technician has received at least one training. Ask if qualify
        # or write a new training.
        self.sit2.professional = data.professional.id
        self.sit2.method = data.method.id
        return 'sit2'

    def default_sit2(self, fields):
        professional = self.sit2.professional.id
        method = self.sit2.method.id
        self.sit2.professional = None
        self.sit2.method = None
        return {
            'professional': professional,
            'method': method,
            }

    def transition_sit2_op1(self):
        # Qualify the technician
        QualificationAction = Pool().get(
            'lims.planification.qualification.action')

        QualificationAction.create([{
            'session_id': self._session_id,
            'professional': self.sit2.professional.id,
            'method': self.sit2.method.id,
            'action': 2,
            }])
        return self._continue()

    def transition_sit2_op2(self):
        # Write a new training.
        QualificationAction = Pool().get(
            'lims.planification.qualification.action')

        QualificationAction.create([{
            'session_id': self._session_id,
            'professional': self.sit2.professional.id,
            'method': self.sit2.method.id,
            'action': 3,
            }])
        return self._continue()

    def situation_3(self, data):
        # The technician is qualified. Check the last execution date of the
        # method; if it's expired, ask if requalify or cancel the process.
        # If it is valid, write a new execution
        pool = Pool()
        LabProfessionalMethod = pool.get('lims.lab.professional.method')
        Date = pool.get('ir.date')
        QualificationAction = pool.get(
            'lims.planification.qualification.action')

        deadline = Date.today() - relativedelta(
            months=data.method.requalification_months)
        professional_method, = LabProfessionalMethod.search([
            ('professional', '=', data.professional),
            ('method', '=', data.method),
            ('type', '=', 'preparation'),
            ])
        last_execution = date.min
        for requalification in professional_method.requalification_history:
            if (requalification.last_execution_date and
                    last_execution < requalification.last_execution_date):
                last_execution = requalification.last_execution_date

        if last_execution < deadline:
            self.sit3.professional = data.professional.id
            self.sit3.method = data.method.id
            return 'sit3'
        else:
            QualificationAction.create([{
                'session_id': self._session_id,
                'professional': data.professional.id,
                'method': data.method.id,
                'action': 5,
                }])
        return self._continue()

    def default_sit3(self, fields):
        professional = self.sit3.professional.id
        method = self.sit3.method.id
        self.sit3.professional = None
        self.sit3.method = None
        return {
            'professional': professional,
            'method': method,
            }

    def transition_sit3_op1(self):
        # Requalify the technician
        QualificationAction = Pool().get(
            'lims.planification.qualification.action')

        QualificationAction.create([{
            'session_id': self._session_id,
            'professional': self.sit3.professional.id,
            'method': self.sit3.method.id,
            'action': 4,
            }])
        return self._continue()

    def situation_4(self, data):
        # The method has no qualified technician
        self.sit4.methods = data['methods']
        return 'sit4'

    def default_sit4(self, fields):
        methods = self.sit4.methods
        self.sit4.methods = None
        return {
            'methods': methods,
            }

    def _continue(self):
        self.situations.index += 1
        if self.situations.index < self.situations.total:
            return 'next_'
        return self._confirm()

    def _confirm(self):
        pool = Pool()
        Planification = pool.get('lims.planification')
        PlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')
        LabProfessionalMethod = pool.get('lims.lab.professional.method')
        QualificationAction = pool.get(
            'lims.planification.qualification.action')

        planification = Planification(Transaction().context['active_id'])

        planification_details = PlanificationServiceDetail.search([
            ('planification', '=', planification.id),
            ])
        methods = []
        for detail in planification_details:
            method = (detail.notebook_line.method if detail.notebook_line
                else None)
            if method:
                qualified = False
                for technician in detail.staff_responsible:
                    qualifications = LabProfessionalMethod.search([
                        ('professional', '=', technician.id),
                        ('method', '=', method.id),
                        ('type', '=', 'preparation'),
                        ])
                    if (qualifications and qualifications[0].state in
                            ('qualified', 'requalified')):
                        if not method.supervised_requalification:
                            qualified = True
                            break
                        actions = QualificationAction.search([
                            ('session_id', '=', self._session_id),
                            ('professional', '=', technician.id),
                            ('method', '=', method.id),
                            ('action', '=', 4),
                            ])
                        if not actions:
                            qualified = True
                            break
                if not qualified:
                    methods.append('[%s] %s' % (method.code, method.name))

        if methods:
            return self.situation_4({'methods': '\n'.join(list(set(methods)))})

        actions = QualificationAction.search([
            ('session_id', '=', self._session_id),
            ])
        if actions:
            controls = self._get_controls()
            start_date = planification.start_date
            for data in actions:
                if data.action == 1:
                    self.action_1(data, controls, start_date)
                elif data.action == 2:
                    self.action_2(data, controls, start_date)
                elif data.action == 3:
                    self.action_3(data, controls, start_date)
                elif data.action == 4:
                    self.action_4(data, controls, start_date)
                elif data.action == 5:
                    self.action_5(data, controls, start_date)
        return 'confirm'

    def action_1(self, data, controls, start_date):
        # The technician has not the method. Write a new training directly.
        pool = Pool()
        LabProfessionalMethod = pool.get('lims.lab.professional.method')
        Date = pool.get('ir.date')

        supervisors = self._get_supervisors(data)
        requalification_history = [{
            'type': 'training',
            'date': Date.today(),
            'last_execution_date': start_date,
            'supervisors': [('create', supervisors)],
            'controls': [('create', controls)],
            }]
        professional_method, = LabProfessionalMethod.create([{
            'professional': data.professional.id,
            'method': data.method.id,
            'state': 'training',
            'type': 'preparation',
            'requalification_history': [('create', requalification_history)],
            }])

    def action_2(self, data, controls, start_date):
        # Qualify the technician
        pool = Pool()
        LabProfessionalMethod = pool.get('lims.lab.professional.method')
        Date = pool.get('ir.date')

        professional_method, = LabProfessionalMethod.search([
            ('professional', '=', data.professional),
            ('method', '=', data.method),
            ('type', '=', 'preparation'),
            ])
        supervisors = self._get_supervisors(data)
        requalification_history = [{
            'type': 'qualification',
            'date': Date.today(),
            'last_execution_date': start_date,
            'supervisors': [('create', supervisors)],
            'controls': [('create', controls)],
            }]
        LabProfessionalMethod.write([professional_method], {
            'state': 'qualified',
            'requalification_history': [('create', requalification_history)],
            })

    def action_3(self, data, controls, start_date):
        # Write a new training
        pool = Pool()
        LabProfessionalMethod = pool.get('lims.lab.professional.method')
        Date = pool.get('ir.date')

        professional_method, = LabProfessionalMethod.search([
            ('professional', '=', data.professional),
            ('method', '=', data.method),
            ('type', '=', 'preparation'),
            ])
        supervisors = self._get_supervisors(data)
        requalification_history = [{
            'type': 'training',
            'date': Date.today(),
            'last_execution_date': start_date,
            'supervisors': [('create', supervisors)],
            'controls': [('create', controls)],
            }]
        LabProfessionalMethod.write([professional_method], {
            'requalification_history': [('create', requalification_history)],
            })

    def action_4(self, data, controls, start_date):
        # Requalify the technician
        pool = Pool()
        LabProfessionalMethod = pool.get('lims.lab.professional.method')
        Date = pool.get('ir.date')

        professional_method, = LabProfessionalMethod.search([
            ('professional', '=', data.professional),
            ('method', '=', data.method),
            ('type', '=', 'preparation'),
            ])
        supervisors = self._get_supervisors(data)
        requalification_history = [{
            'type': 'requalification',
            'date': Date.today(),
            'last_execution_date': start_date,
            'supervisors': [('create', supervisors)],
            'controls': [('create', controls)],
            }]
        LabProfessionalMethod.write([professional_method], {
            'state': 'requalified',
            'requalification_history': [('create', requalification_history)],
            })

    def action_5(self, data, controls, start_date):
        # Write a new execution
        pool = Pool()
        LabProfessionalMethod = pool.get('lims.lab.professional.method')
        Date = pool.get('ir.date')

        professional_method, = LabProfessionalMethod.search([
            ('professional', '=', data.professional),
            ('method', '=', data.method),
            ('type', '=', 'preparation'),
            ])
        supervisors = self._get_supervisors(data)
        requalification_history = [{
            'type': ('qualification'
                if professional_method.state == 'qualified'
                else 'requalification'),
            'date': Date.today(),
            'last_execution_date': start_date,
            'supervisors': [('create', supervisors)],
            'controls': [('create', controls)],
            }]
        LabProfessionalMethod.write([professional_method], {
            'requalification_history': [('create', requalification_history)],
            })

    def transition_confirm(self):
        pool = Pool()
        Planification = pool.get('lims.planification')
        Config = pool.get('lims.configuration')
        process_background = Config(1).planification_process_background

        planification = Planification(Transaction().context['active_id'])
        planification.state = 'confirmed'
        if process_background:
            planification.waiting_process = True
        planification.save()

        if not process_background:
            Planification.do_confirm([planification])
        return 'end'

    def _get_supervisors(self, data):
        pool = Pool()
        PlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')
        LabProfessionalMethod = pool.get('lims.lab.professional.method')
        QualificationAction = pool.get(
            'lims.planification.qualification.action')

        planification_id = Transaction().context['active_id']
        supervisors = []

        planification_details = PlanificationServiceDetail.search([
            ('planification', '=', planification_id),
            ('notebook_line.method', '=', data.method.id),
            ])
        for detail in planification_details:
            for technician in detail.staff_responsible:
                if technician.id == data.professional.id:
                    continue
                qualifications = LabProfessionalMethod.search([
                    ('professional', '=', technician.id),
                    ('method', '=', data.method.id),
                    ('type', '=', 'preparation'),
                    ])
                if (qualifications and qualifications[0].state in
                        ('qualified', 'requalified')):
                    if not data.method.supervised_requalification:
                        supervisors.append(technician.id)
                    else:
                        actions = QualificationAction.search([
                            ('session_id', '=', self._session_id),
                            ('professional', '=', technician.id),
                            ('method', '=', data.method.id),
                            ('action', '=', 4),
                            ])
                        if not actions:
                            supervisors.append(technician.id)

        return [{'supervisor': t_id} for t_id in list(set(supervisors))]

    def _get_controls(self):
        PlanificationFraction = Pool().get('lims.planification-fraction')

        planification_id = Transaction().context['active_id']
        controls = []

        planification_controls = PlanificationFraction.search([
            ('planification', '=', planification_id),
            ('fraction.type.requalify', '=', True),
            ])
        for p_control in planification_controls:
            controls.append(p_control.fraction.id)

        return [{'control': f_id} for f_id in list(set(controls))]


class ReplaceTechnicianStart(ModelView):
    'Replace Technician'
    __name__ = 'lims.planification.replace_technician.start'

    planification = fields.Many2One('lims.planification', 'Planification')
    technician_replaced = fields.Many2One('lims.laboratory.professional',
        'Technician replaced', required=True,
        domain=[('id', 'in', Eval('replaced_domain'))],
        depends=['replaced_domain'])
    replaced_domain = fields.One2Many('lims.laboratory.professional',
        None, 'Replaced domain')
    technician_substitute = fields.Many2One('lims.laboratory.professional',
        'Technician substitute', required=True,
        domain=[('id', 'in', Eval('substitute_domain'))],
        depends=['substitute_domain'])
    substitute_domain = fields.Function(fields.One2Many(
        'lims.laboratory.professional', None, 'Substitute domain'),
        'on_change_with_substitute_domain')

    @fields.depends('technician_replaced', 'planification')
    def on_change_with_substitute_domain(self, name=None):
        pool = Pool()
        UserLaboratory = pool.get('lims.user-laboratory')
        LaboratoryProfessional = pool.get('lims.laboratory.professional')
        PlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')
        LabProfessionalMethod = pool.get('lims.lab.professional.method')

        if not self.technician_replaced:
            return []

        substitute_domain = []
        users = UserLaboratory.search([
            ('laboratory', '=', self.planification.laboratory.id),
            ])
        if users:
            professionals = LaboratoryProfessional.search([
                ('party.lims_user', 'in', [u.user.id for u in users]),
                ])
            if professionals:
                substitute_domain = [p.id for p in professionals]

        service_details = PlanificationServiceDetail.search([
            ('planification', '=', self.planification.id),
            ('notebook_line', '!=', None),
            ('staff_responsible', '=', self.technician_replaced.id),
            ])
        methods_ids = []
        for service_detail in service_details:
            method = service_detail.notebook_line.method
            if method:
                methods_ids.append(method.id)

        methods_ids = list(set(methods_ids))
        for technician_id in substitute_domain:
            for method_id in methods_ids:
                qualifications = LabProfessionalMethod.search([
                    ('professional', '=', technician_id),
                    ('method', '=', method_id),
                    ('type', '=', 'preparation'),
                    ])
                if not (qualifications and qualifications[0].state in
                        ('qualified', 'requalified')):
                    substitute_domain.remove(technician_id)
                    break
        return substitute_domain


class ReplaceTechnician(Wizard):
    'Replace Technician'
    __name__ = 'lims.planification.replace_technician'

    start_state = 'check'
    check = StateTransition()
    start = StateView('lims.planification.replace_technician.start',
        'lims.lims_replace_technician_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Replace', 'replace', 'tryton-ok', default=True),
            ])
    replace = StateTransition()

    def transition_check(self):
        pool = Pool()
        Planification = pool.get('lims.planification')
        NotebookLine = pool.get('lims.notebook.line')

        planification = Planification(Transaction().context['active_id'])
        if planification.state != 'confirmed':
            return 'end'

        notebook_lines = NotebookLine.search([
            ('planification', '=', planification.id),
            ('end_date', '!=', None),
            ])
        if notebook_lines:
            return 'end'

        return 'start'

    def default_start(self, fields):
        Planification = Pool().get('lims.planification')

        planification = Planification(Transaction().context['active_id'])

        return {
            'planification': planification.id,
            'replaced_domain': [t.laboratory_professional.id
                for t in planification.technicians],
            'substitute_domain': [],
            }

    def transition_replace(self):
        planification_id = Transaction().context['active_id']
        technician_replaced_id = self.start.technician_replaced.id
        technician_substitute_id = self.start.technician_substitute.id

        self.update_planification_detail(planification_id,
            technician_replaced_id, technician_substitute_id)
        self.update_planification_technician(planification_id,
            technician_replaced_id, technician_substitute_id)
        self.update_laboratory_notebook(planification_id,
            technician_replaced_id, technician_substitute_id)
        return 'end'

    def update_planification_detail(self, planification_id,
            technician_replaced_id, technician_substitute_id):
        PlanificationServiceDetailProfessional = Pool().get(
            'lims.planification.service_detail-laboratory.professional')

        details_professional = PlanificationServiceDetailProfessional.search([
            ('detail.detail.planification', '=', planification_id),
            ('professional', '=', technician_replaced_id),
            ])
        PlanificationServiceDetailProfessional.write(details_professional, {
            'professional': technician_substitute_id,
            })

    def update_planification_technician(self, planification_id,
            technician_replaced_id, technician_substitute_id):
        PlanificationTechnician = Pool().get('lims.planification.technician')

        planification_professional = PlanificationTechnician.search([
            ('planification', '=', planification_id),
            ('laboratory_professional', '=', technician_replaced_id),
            ])
        PlanificationTechnician.delete(planification_professional)

        planification_professional = PlanificationTechnician.search([
            ('planification', '=', planification_id),
            ('laboratory_professional', '=', technician_substitute_id),
            ])
        if not planification_professional:
            PlanificationTechnician.create([{
                'planification': planification_id,
                'laboratory_professional': technician_substitute_id,
                }])

    def update_laboratory_notebook(self, planification_id,
            technician_replaced_id, technician_substitute_id):
        NotebookLineProfessional = Pool().get(
            'lims.notebook.line-laboratory.professional')

        notebook_line_professional = NotebookLineProfessional.search([
            ('notebook_line.planification', '=', planification_id),
            ('professional', '=', technician_replaced_id),
            ])
        NotebookLineProfessional.write(notebook_line_professional, {
            'professional': technician_substitute_id,
            })


class LoadServices(Wizard):
    'Load Services'
    __name__ = 'lims.load_services'

    start_state = 'check'
    check = StateTransition()
    load = StateTransition()

    def transition_check(self):
        Fraction = Pool().get('lims.fraction')

        fraction = Fraction(Transaction().context['active_id'])
        if (not fraction or not fraction.cie_fraction_type or
                not fraction.cie_original_fraction):
            return 'end'
        return 'load'

    def transition_load(self):
        pool = Pool()
        Fraction = pool.get('lims.fraction')
        Service = pool.get('lims.service')
        Analysis = pool.get('lims.analysis')

        new_fraction = Fraction(Transaction().context['active_id'])
        original_fraction = new_fraction.cie_original_fraction

        # new services
        services = Service.search([
            ('fraction', '=', original_fraction),
            ])
        for service in services:
            if not Analysis.is_typified(service.analysis,
                    new_fraction.product_type, new_fraction.matrix):
                continue
            new_service, = Service.copy([service], default={
                'fraction': new_fraction.id,
                })
        return 'end'


class PlanificationSequenceReport(Report):
    'Sequence'
    __name__ = 'lims.planification.sequence.report'

    @classmethod
    def get_context(cls, records, data):
        report_context = super(PlanificationSequenceReport,
                cls).get_context(records, data)

        report_context['company'] = report_context['user'].company

        objects = {}
        for planification in records:
            if planification.state != 'confirmed':
                continue
            date = str(planification.start_date)
            if date not in objects:
                objects[date] = {
                    'date': planification.start_date,
                    'methods': {},
                    }
            for detail in planification.details:
                fraction = detail.fraction
                for service_detail in detail.details:
                    if (service_detail.notebook_line.analysis.behavior ==
                            'internal_relation'):
                        continue
                    notebook_line = service_detail.notebook_line
                    method_id = notebook_line.method.id
                    if method_id not in objects[date]['methods']:
                        objects[date]['methods'][method_id] = {
                            'method': notebook_line.method.code,
                            'lines': {},
                            }

                    number = fraction.get_formated_number('sn-sy-fn')
                    number = (number + '-' + str(notebook_line.repetition))
                    number_parts = number.split('-')
                    order = (number_parts[1] + '-' + number_parts[0] + '-' +
                        number_parts[2] + '-' + number_parts[3])

                    product_type = fraction.product_type.code
                    matrix = fraction.matrix.code
                    fraction_type = fraction.type.code
                    comments = fraction.comments
                    analysis_origin = notebook_line.analysis_origin
                    priority = notebook_line.priority
                    urgent = notebook_line.urgent
                    report_date = (notebook_line.report_date or
                        notebook_line.results_estimated_date)
                    trace_report = fraction.sample.trace_report
                    sample_client_description = (
                        fraction.sample.sample_client_description)
                    key = (number, product_type, matrix, fraction_type,
                        analysis_origin, priority, trace_report)
                    if key not in objects[date]['methods'][method_id]['lines']:
                        objects[date]['methods'][method_id]['lines'][key] = {
                            'order': order,
                            'number': number,
                            'product_type': product_type,
                            'matrix': matrix,
                            'fraction_type': fraction_type,
                            'analysis_origin': analysis_origin,
                            'priority': priority,
                            'urgent': urgent,
                            'report_date': report_date,
                            'trace_report': trace_report,
                            'comments': comments,
                            'sample_client_description': (
                                sample_client_description),
                            }

        for k1 in objects.keys():
            for k2, lines in objects[k1]['methods'].items():
                sorted_lines = sorted(list(lines['lines'].values()),
                    key=lambda x: x['order'])
                objects[k1]['methods'][k2]['lines'] = sorted_lines

        report_context['objects'] = objects

        return report_context


class PlanificationWorksheetAnalysisReport(Report):
    'Worksheet by Analysis'
    __name__ = 'lims.planification.worksheet_analysis.report'

    @classmethod
    def get_context(cls, records, data):
        report_context = super(PlanificationWorksheetAnalysisReport,
                cls).get_context(records, data)

        report_context['company'] = report_context['user'].company

        objects = {}
        for planification in records:
            if planification.state != 'confirmed':
                continue
            date = str(planification.start_date)
            if date not in objects:
                objects[date] = {
                    'date': planification.start_date,
                    'professionals': {},
                    }
            for detail in planification.details:
                fraction = detail.fraction
                for service_detail in detail.details:
                    if not service_detail.notebook_line:
                        continue
                    if (service_detail.notebook_line.analysis.behavior ==
                            'internal_relation'):
                        continue
                    p_key = ()
                    p_names = ''
                    for professional in service_detail.staff_responsible:
                        p_key += (professional.id,)
                        if p_names:
                            p_names += ', '
                        p_names += professional.rec_name
                    if not p_key:
                        continue
                    p_key = tuple(sorted(p_key))
                    if (p_key not in objects[date]['professionals']):
                        objects[date]['professionals'][p_key] = {
                            'professional': p_names,
                            'analysis': {},
                            'total': 0,
                            }
                    notebook_line = service_detail.notebook_line
                    key = (notebook_line.analysis.id, notebook_line.method.id)
                    if (key not in
                            objects[date]['professionals'][p_key]['analysis']):
                        objects[date]['professionals'][p_key]['analysis'][
                            key] = {
                                'order': notebook_line.analysis.order or 9999,
                                'analysis': notebook_line.analysis.rec_name,
                                'method': notebook_line.method.rec_name,
                                'lines': {},
                                }

                    number = fraction.get_formated_number('pt-m-sy-sn-fn')
                    number = (number + '-' + str(notebook_line.repetition))
                    concentration_level = (
                        notebook_line.concentration_level.description if
                        notebook_line.concentration_level else '')
                    if (number in objects[date]['professionals'][p_key][
                            'analysis'][key]['lines']):
                        continue

                    number_parts = number.split('-')
                    order = (number_parts[3] + '-' + number_parts[2] + '-' +
                        number_parts[4] + '-' + number_parts[5])
                    comments = '%s - %s - %s' % (planification.comments or '',
                        notebook_line.service.comments or '',
                        notebook_line.service.fraction.comments or '')
                    record = {
                        'order': order,
                        'number': number,
                        'label': fraction.label,
                        'sample_client_description': (
                            fraction.sample.sample_client_description),
                        'party': fraction.party.code,
                        'storage_location': fraction.storage_location.code,
                        'fraction_type': fraction.type.code,
                        'concentration_level': concentration_level,
                        'device': (notebook_line.device.code if
                            notebook_line.device else None),
                        'urgent': 'SI' if notebook_line.urgent else '',
                        'comments': comments,
                        'planification_code': planification.code,
                        }
                    objects[date]['professionals'][p_key]['analysis'][
                        key]['lines'][number] = record
                    objects[date]['professionals'][p_key]['total'] += 1

        for k1 in objects.keys():
            for k2 in objects[k1]['professionals'].keys():
                sorted_analysis = sorted(list(objects[k1]['professionals'][k2][
                    'analysis'].items()), key=lambda x: x[1]['order'])
                objects[k1]['professionals'][k2]['analysis'] = []
                for item in sorted_analysis:
                    sorted_lines = sorted(list(item[1]['lines'].items()),
                            key=lambda x: x[1]['order'])
                    item[1]['lines'] = [l[1] for l in sorted_lines]
                    objects[k1]['professionals'][k2]['analysis'].append(
                        item[1])

        report_context['records'] = objects

        return report_context


class PlanificationWorksheetMethodReport(Report):
    'Worksheet by Method'
    __name__ = 'lims.planification.worksheet_method.report'

    @classmethod
    def get_context(cls, records, data):
        report_context = super(PlanificationWorksheetMethodReport,
                cls).get_context(records, data)

        report_context['company'] = report_context['user'].company

        objects = {}
        for planification in records:
            if planification.state != 'confirmed':
                continue
            date = str(planification.start_date)
            if date not in objects:
                objects[date] = {
                    'date': planification.start_date,
                    'professionals': {},
                    }
            for detail in planification.details:
                fraction = detail.fraction
                for service_detail in detail.details:
                    if not service_detail.notebook_line:
                        continue
                    if (service_detail.notebook_line.analysis.behavior ==
                            'internal_relation'):
                        continue
                    p_key = ()
                    p_names = ''
                    for professional in service_detail.staff_responsible:
                        p_key += (professional.id,)
                        if p_names:
                            p_names += ', '
                        p_names += professional.rec_name
                    if not p_key:
                        continue
                    p_key = tuple(sorted(p_key))
                    if (p_key not in objects[date]['professionals']):
                        objects[date]['professionals'][p_key] = {
                            'professional': p_names,
                            'total': 0,
                            'lines': {},
                            }
                    notebook_line = service_detail.notebook_line

                    number = fraction.get_formated_number('pt-m-sy-sn-fn')
                    number = (number + '-' + str(notebook_line.repetition))
                    concentration_level = (
                        notebook_line.concentration_level.description if
                        notebook_line.concentration_level else '')
                    if (number not in objects[date]['professionals'][p_key][
                            'lines']):
                        number_parts = number.split('-')
                        order = (number_parts[3] + '-' + number_parts[2] +
                            '-' + number_parts[4] + '-' + number_parts[5])

                        comments_planif = '. '.join(cls.get_planning_legend(
                            fraction, planification))
                        if comments_planif:
                            comments = '%s - %s - %s - %s' % (
                                planification.comments or '',
                                notebook_line.service.comments or '',
                                notebook_line.service.fraction.comments or '',
                                comments_planif or '')
                        else:
                            comments = '%s - %s - %s' % (
                                planification.comments or
                                '', notebook_line.service.comments or '',
                                notebook_line.service.fraction.comments or '')

                        if fraction.packages_quantity != 0.0:
                            pack_quant = str(fraction.packages_quantity)
                        else:
                            pack_quant = ''
                        record = {
                            'order': order,
                            'number': number,
                            'label': fraction.label,
                            'sample_client_description': (
                                fraction.sample.sample_client_description),
                            'party': fraction.party.code,
                            'storage_location': fraction.storage_location.code,
                            'fraction_type': fraction.type.code,
                            'concentration_level': concentration_level,
                            'device': (notebook_line.device.code if
                                notebook_line.device else None),
                            'urgent': 'SI' if notebook_line.urgent else '',
                            'comments': comments,
                            'planification_code': planification.code,
                            'package_type':
                                pack_quant + ' ' +
                                fraction.package_type.description,
                            'methods': {},
                            }
                        objects[date]['professionals'][p_key]['lines'][
                            number] = record
                        objects[date]['professionals'][p_key]['total'] += 1
                    if (notebook_line.method.id not in
                            objects[date]['professionals'][p_key]['lines'][
                            number]['methods']):
                        objects[date]['professionals'][p_key]['lines'][
                            number]['methods'][notebook_line.method.id] = (
                                notebook_line.method.rec_name)

        for k1 in objects.keys():
            for k2 in objects[k1]['professionals'].keys():
                objects[k1]['professionals'][k2]['methods'] = {}
                fractions = list(objects[k1]['professionals'][k2]['lines'].values())
                for fraction in fractions:
                    m_key = ()
                    m_names = []
                    for m_id, m_name in fraction['methods'].items():
                        m_key += (m_id,)
                        m_names.append(m_name)
                    m_key = tuple(sorted(m_key))
                    if (m_key not in objects[k1]['professionals'][k2][
                            'methods']):
                        objects[k1]['professionals'][k2]['methods'][m_key] = {
                            'methods': m_names,
                            'lines': [],
                            }
                    objects[k1]['professionals'][k2]['methods'][m_key][
                        'lines'].append(fraction)

                del objects[k1]['professionals'][k2]['lines']
                for m_key in objects[k1]['professionals'][k2][
                        'methods'].keys():
                    sorted_lines = sorted(objects[k1]['professionals'][k2][
                        'methods'][m_key]['lines'], key=lambda x: x['order'])
                    objects[k1]['professionals'][k2]['methods'][m_key][
                        'lines'] = sorted_lines

        report_context['records'] = objects

        return report_context

    @classmethod
    def get_planning_legend(cls, fraction, planification):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Analysis = pool.get('lims.analysis')
        PlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')
        PlanificationDetail = pool.get('lims.planification.detail')
        NotebookLine = pool.get('lims.notebook.line')

        cursor.execute('SELECT DISTINCT(a.planning_legend) '
            'FROM "' + PlanificationDetail._table + '" pd '
                'INNER JOIN "' + PlanificationServiceDetail._table +
                    '" psd '
                'ON pd.id = psd.detail '
                'INNER JOIN "' + NotebookLine._table + '" nl '
                'ON nl.id = psd.notebook_line '
                'INNER JOIN "' + Analysis._table + '" a '
                'ON a.id = nl.analysis '
            'WHERE pd.planification = %s '
                'AND pd.fraction = %s '
                'AND a.planning_legend IS NOT NULL ',
                (planification.id, fraction.id))

        planned_ids = [s[0] for s in cursor.fetchall()]
        return planned_ids


class PlanificationWorksheetReport(Report):
    'Worksheet'
    __name__ = 'lims.planification.worksheet.report'

    @classmethod
    def get_context(cls, records, data):
        report_context = super(PlanificationWorksheetReport,
                cls).get_context(records, data)

        report_context['company'] = report_context['user'].company

        objects = {}
        for planification in records:
            if planification.state != 'confirmed':
                continue
            date = str(planification.start_date)
            if date not in objects:
                objects[date] = {
                    'date': planification.start_date,
                    'professionals': {},
                    }
            for detail in planification.details:
                fraction = detail.fraction
                for service_detail in detail.details:
                    if not service_detail.notebook_line:
                        continue
                    if (service_detail.notebook_line.analysis.behavior ==
                            'internal_relation'):
                        continue
                    p_key = ()
                    p_names = ''
                    for professional in service_detail.staff_responsible:
                        p_key += (professional.id,)
                        if p_names:
                            p_names += ', '
                        p_names += professional.rec_name
                    if not p_key:
                        continue
                    p_key = tuple(sorted(p_key))
                    if (p_key not in objects[date]['professionals']):
                        objects[date]['professionals'][p_key] = {
                            'professional': p_names,
                            'analysis': {},
                            'total': 0,
                            }
                    notebook_line = service_detail.notebook_line
                    key = service_detail.planned_service.id
                    if (key not in
                            objects[date]['professionals'][p_key]['analysis']):
                        objects[date]['professionals'][p_key]['analysis'][
                            key] = {
                                'analysis': (
                                    service_detail.planned_service.rec_name),
                                'lines': {},
                                }

                    number = fraction.get_formated_number('pt-m-sy-sn-fn')
                    number = (number + '-' + str(notebook_line.repetition))
                    concentration_level = (
                        notebook_line.concentration_level.description if
                        notebook_line.concentration_level else '')
                    if (number not in objects[date]['professionals'][p_key][
                            'analysis'][key]['lines']):
                        number_parts = number.split('-')
                        order = (number_parts[3] + '-' + number_parts[2] +
                            '-' + number_parts[4] + '-' + number_parts[5])

                        comments_planif = '. '.join(cls.get_planning_legend(
                            fraction, planification))
                        if comments_planif:
                            comments = '%s - %s - %s - %s' % (
                                planification.comments or '',
                                notebook_line.service.comments or '',
                                notebook_line.service.fraction.comments or '',
                                comments_planif or '')
                        else:
                            comments = '%s - %s - %s' % (
                                planification.comments or
                                '', notebook_line.service.comments or '',
                                notebook_line.service.fraction.comments or '')

                        if fraction.packages_quantity != 0.0:
                            pack_quant = str(fraction.packages_quantity)
                        else:
                            pack_quant = ''
                        record = {
                            'order': order,
                            'number': number,
                            'label': fraction.label,
                            'sample_client_description': (
                                fraction.sample.sample_client_description if
                                fraction.sample.sample_client_description else
                                ''),
                            'party': fraction.party.code,
                            'storage_location': fraction.storage_location.code,
                            'fraction_type': fraction.type.code,
                            'concentration_level': concentration_level,
                            'device': (notebook_line.device.code if
                                notebook_line.device else None),
                            'urgent': 'SI' if notebook_line.urgent else '',
                            'comments': comments,
                            'planification_code': planification.code,
                            'package_type':
                                pack_quant + ' ' +
                                fraction.package_type.description,
                            'methods': {},
                            }
                        objects[date]['professionals'][p_key]['analysis'][key][
                            'lines'][number] = record
                        objects[date]['professionals'][p_key]['total'] += 1
                    if (notebook_line.method.id not in
                            objects[date]['professionals'][p_key]['analysis'][
                            key]['lines'][number]['methods']):
                        objects[date]['professionals'][p_key]['analysis'][
                            key]['lines'][number]['methods'][
                            notebook_line.method.id] = (
                                notebook_line.method.rec_name)

        for k1 in objects.keys():
            for k2 in objects[k1]['professionals'].keys():
                for k3 in objects[k1]['professionals'][k2][
                        'analysis'].keys():
                    objects[k1]['professionals'][k2]['analysis'][k3][
                        'methods'] = {}
                    fractions = list(objects[k1]['professionals'][k2]['analysis'][
                        k3]['lines'].values())
                    for fraction in fractions:
                        m_key = ()
                        m_names = []
                        for m_id, m_name in fraction['methods'].items():
                            m_key += (m_id,)
                            m_names.append(m_name)
                        m_key = tuple(sorted(m_key))
                        if (m_key not in objects[k1]['professionals'][k2][
                                'analysis'][k3]['methods']):
                            objects[k1]['professionals'][k2]['analysis'][k3][
                                'methods'][m_key] = {
                                    'methods': m_names,
                                    'lines': [],
                                    }
                        objects[k1]['professionals'][k2]['analysis'][k3][
                            'methods'][m_key]['lines'].append(fraction)

                    del objects[k1]['professionals'][k2]['analysis'][k3][
                        'lines']
                    for m_key in objects[k1]['professionals'][k2][
                            'analysis'][k3]['methods'].keys():
                        sorted_lines = sorted(objects[k1]['professionals'][k2][
                            'analysis'][k3]['methods'][m_key]['lines'],
                            key=lambda x: x['order'])
                        objects[k1]['professionals'][k2]['analysis'][k3][
                            'methods'][m_key]['lines'] = sorted_lines

        report_context['records'] = objects
        return report_context

    @classmethod
    def get_planning_legend(cls, fraction, planification):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Analysis = pool.get('lims.analysis')
        PlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')
        PlanificationDetail = pool.get('lims.planification.detail')
        NotebookLine = pool.get('lims.notebook.line')

        cursor.execute('SELECT DISTINCT(a.planning_legend) '
            'FROM "' + PlanificationDetail._table + '" pd '
                'INNER JOIN "' + PlanificationServiceDetail._table +
                    '" psd '
                'ON pd.id = psd.detail '
                'INNER JOIN "' + NotebookLine._table + '" nl '
                'ON nl.id = psd.notebook_line '
                'INNER JOIN "' + Analysis._table + '" a '
                'ON a.id = nl.analysis '
            'WHERE pd.planification = %s '
                'AND pd.fraction = %s '
                'AND a.planning_legend IS NOT NULL ',
                (planification.id, fraction.id))

        planned_ids = [s[0] for s in cursor.fetchall()]
        return planned_ids


class PrintPendingServicesUnplannedReportStart(ModelView):
    'Print Pending Services Unplanned Report Start'
    __name__ = 'lims.pending_services_unplanned.start'

    start_date = fields.Date('Start Date', required=True)
    end_date = fields.Date('End Date', required=True)
    party = fields.Many2One('party.party', 'Party')
    include_method = fields.Boolean('Include method')


class PrintPendingServicesUnplannedReport(Wizard):
    'Print Pending Services Unplanned Report'
    __name__ = 'lims.pending_services_unplanned'

    start = StateView('lims.pending_services_unplanned.start',
        'lims.print_pending_services_unplanned_report_start'
        '_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print', 'print_', 'tryton-print', default=True),
            Button('Save', 'save', 'tryton-save'),
        ])
    print_ = StateAction(
        'lims.report_pending_services_unplanned')
    save = StateAction(
        'lims.report_pending_services_unplanned_spreadsheet')

    def do_print_(self, action):
        data = {
            'start_date': self.start.start_date,
            'end_date': self.start.end_date or None,
            'party': self.start.party and self.start.party.id or None,
            'include_method': self.start.include_method or None,
            }
        return action, data

    def do_save(self, action):
        data = {
            'start_date': self.start.start_date,
            'end_date': self.start.end_date or None,
            'party': self.start.party and self.start.party.id or None,
            'include_method': self.start.include_method or None,
            }
        return action, data


class PendingServicesUnplannedReport(Report):
    'Pending Services Unplanned'
    __name__ = 'lims.pending_services_unplanned.report'

    @classmethod
    def get_context(cls, records, data):
        report_context = super(PendingServicesUnplannedReport,
                cls).get_context(records, data)

        pool = Pool()
        Service = pool.get('lims.service')
        Laboratory = pool.get('lims.laboratory')

        if report_context['user'].laboratory:
            labs = [report_context['user'].laboratory.id]
        else:
            labs = [l.id for l in Laboratory.search([])]

        report_context['company'] = report_context['user'].company

        clause = []
        if data['start_date']:
            clause.append(('confirmation_date', '>=', data['start_date']))
        if data['end_date']:
            clause.append(('confirmation_date', '<=', data['end_date']))
        if data['party']:
            clause.append(('party', '=', data['party']))
        clause.extend([
            ('fraction.type.plannable', '=', True),
            ('fraction.confirmed', '=', True),
            ('analysis.behavior', '!=', 'internal_relation'),
            ])
        unplanned_services = cls.get_unplanned_services()
        clause.append(('id', 'in', unplanned_services))

        report_context['start_date'] = (data['start_date']
            if data['start_date'] else '')
        report_context['end_date'] = (data['end_date']
            if data['end_date'] else '')
        report_context['include_method'] = data['include_method']
        objects = {}
        with Transaction().set_user(0):
            pending_services = Service.search(clause)
        for service in pending_services:
            # Laboratory
            laboratory = cls.get_service_laboratory(service.id)
            if laboratory.id not in labs:
                continue

            if laboratory.id not in objects:
                objects[laboratory.id] = {
                    'laboratory': laboratory.rec_name,
                    'services': {},
                    'total': 0,
                    }

            # Service
            analysis = service.analysis
            if analysis.id not in objects[laboratory.id]['services']:
                objects[laboratory.id]['services'][analysis.id] = {
                    'service': analysis.rec_name,
                    'parties': {},
                    'total': 0,
                    }

            # Party
            party = service.party
            if (party.id not in objects[laboratory.id]['services'][
                    analysis.id]['parties']):
                objects[laboratory.id]['services'][analysis.id]['parties'][
                    party.id] = {
                        'party': party.code,
                        'lines': [],
                        'total': 0,
                        }

            number = service.fraction.get_formated_number('pt-m-sn-sy-fn')
            number = (number + '-' + str(service.sample.label))
            number_parts = number.split('-')
            order = (number_parts[3] + '-' + number_parts[2] + '-' +
                number_parts[4])

            result_estimated = []
            result_estimated = cls.get_results_estimated(service.id)
            result_estimated_date = None
            result_estimated_waiting = None

            if result_estimated:
                result_estimated_waiting = result_estimated[0][1]
                confirmation_date = result_estimated[0][0]
                c_days = result_estimated_waiting
                result_estimated_date = (confirmation_date +
                    relativedelta(days=c_days))

            if data['include_method']:
                method_pending = cls.get_unplanned_method(service.id)
                for method in method_pending:
                    record = {
                        'order': order,
                        'number': number,
                        'date': service.sample.date2,
                        'sample_client_description': (
                            service.sample.sample_client_description),
                        'current_location': (
                            service.fraction.current_location.code
                            if service.fraction.current_location else ''),
                        'fraction_type': service.fraction.type.code,
                        'priority': service.priority,
                        'urgent': 'Yes' if service.urgent else 'No',
                        'method': method[0],
                        'comments': (
                            '%s - %s' % (service.fraction.comments or '',
                            service.sample.comments or '')),
                        'report_date': service.report_date,
                        'confirmation_date': (service.confirmation_date
                            if service.confirmation_date else ''),
                        'results_estimated_date': (result_estimated_date
                            if result_estimated_date else ''),
                        }
                    objects[laboratory.id]['services'][analysis.id]['parties'][
                        party.id]['lines'].append(record)
                    objects[laboratory.id]['total'] += 1
                    objects[laboratory.id]['services'][analysis.id][
                        'total'] += 1
                    objects[laboratory.id]['services'][analysis.id]['parties'][
                        party.id]['total'] += 1
            else:
                record = {
                    'order': order,
                    'number': number,
                    'date': service.sample.date2,
                    'sample_client_description': (
                        service.sample.sample_client_description),
                    'current_location': (service.fraction.current_location.code
                        if service.fraction.current_location else ''),
                    'fraction_type': service.fraction.type.code,
                    'priority': service.priority,
                    'urgent': 'Yes' if service.urgent else 'No',
                    'method': '',
                    'comments': ('%s - %s' % (service.fraction.comments or '',
                        service.sample.comments or '')),
                    'report_date': service.report_date,
                    'confirmation_date': (service.confirmation_date
                        if service.confirmation_date else ''),
                    'results_estimated_date': (result_estimated_date
                        if result_estimated_date else ''),
                    }
                objects[laboratory.id]['services'][analysis.id]['parties'][
                    party.id]['lines'].append(record)
                objects[laboratory.id]['total'] += 1
                objects[laboratory.id]['services'][analysis.id]['total'] += 1
                objects[laboratory.id]['services'][analysis.id]['parties'][
                    party.id]['total'] += 1
        for k1 in objects.keys():
            for k2 in objects[k1]['services'].keys():
                for k3, lines in objects[k1]['services'][k2][
                        'parties'].items():
                    sorted_lines = sorted(lines['lines'],
                        key=lambda x: x['order'])
                    objects[k1]['services'][k2]['parties'][k3]['lines'] = (
                        sorted_lines)

        report_context['objects'] = objects

        return report_context

    @classmethod
    def get_unplanned_services(cls):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        Analysis = pool.get('lims.analysis')

        cursor.execute('SELECT DISTINCT(d.service) '
            'FROM "' + EntryDetailAnalysis._table + '" d '
                'INNER JOIN "' + Analysis._table + '" a '
                'ON a.id = d.analysis '
            'WHERE d.state = \'unplanned\' '
                'AND a.behavior != \'internal_relation\'')
        not_planned_ids = [s[0] for s in cursor.fetchall()]
        return not_planned_ids

    @classmethod
    def get_unplanned_method(cls, service_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        Analysis = pool.get('lims.analysis')
        LabMethod = pool.get('lims.lab.method')

        cursor.execute('SELECT DISTINCT(m.code) '
            'FROM "' + EntryDetailAnalysis._table + '" d '
                'INNER JOIN "' + Analysis._table + '" a '
                'ON a.id = d.analysis '
                'INNER JOIN"' + LabMethod._table + '" m '
                'ON d.method = m.id '
            'WHERE d.service = %s '
                'AND d.state = \'unplanned\' '
                'AND a.behavior != \'internal_relation\'',
                (service_id,))
        not_planned_ids = list(cursor.fetchall())
        return not_planned_ids

    @classmethod
    def get_service_laboratory(cls, service_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        Service = pool.get('lims.service')
        Laboratory = pool.get('lims.laboratory')

        cursor.execute('SELECT d.laboratory '
            'FROM "' + EntryDetailAnalysis._table + '" d '
                'INNER JOIN "' + Service._table + '" s '
                'ON s.id = d.service '
            'WHERE s.id = %s '
            'ORDER BY d.id ASC LIMIT 1',
            (service_id,))
        return Laboratory(cursor.fetchone()[0])

    @classmethod
    def get_results_estimated(cls, service_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        NotebookLine = pool.get('lims.notebook.line')
        Analysis = pool.get('lims.analysis')

        cursor.execute('SELECT  d.confirmation_date, '
                'n.results_estimated_waiting '
            'FROM "' + NotebookLine._table + '" n '
                'INNER JOIN "' + EntryDetailAnalysis._table + '" d '
                'ON (d.service = n.service  AND d.analysis = n.analysis) '
                'INNER JOIN "' + Analysis._table + '" a '
                'ON a.id = d.analysis '
            'WHERE d.state = \'unplanned\' '
                'AND d.service = %s '
                'AND n.results_estimated_waiting IS NOT Null '
                'AND a.behavior != \'internal_relation\''
                'ORDER BY n.results_estimated_waiting ASC LIMIT 1',
                (service_id,))

        return list(cursor.fetchall())


class PendingServicesUnplannedSpreadsheet(Report):
    'Pending Services Unplanned'
    __name__ = 'lims.pending_services_unplanned.spreadsheet'

    @classmethod
    def get_context(cls, records, data):
        report_context = super(PendingServicesUnplannedSpreadsheet,
                cls).get_context(records, data)

        pool = Pool()
        Service = pool.get('lims.service')
        Laboratory = pool.get('lims.laboratory')

        if report_context['user'].laboratory:
            labs = [report_context['user'].laboratory.id]
        else:
            labs = [l.id for l in Laboratory.search([])]

        report_context['company'] = report_context['user'].company

        clause = []
        if data['start_date']:
            clause.append(('confirmation_date', '>=', data['start_date']))
        if data['end_date']:
            clause.append(('confirmation_date', '<=', data['end_date']))
        if data['party']:
            clause.append(('party', '=', data['party']))
        clause.extend([
            ('fraction.type.plannable', '=', True),
            ('fraction.confirmed', '=', True),
            ('analysis.behavior', '!=', 'internal_relation'),
            ])
        unplanned_services = cls.get_unplanned_services()
        clause.append(('id', 'in', unplanned_services))

        report_context['start_date'] = (data['start_date']
            if data['start_date'] else '')
        report_context['end_date'] = (data['end_date']
            if data['end_date'] else '')
        report_context['include_method'] = data['include_method']
        objects = []
        with Transaction().set_user(0):
            pending_services = Service.search(clause)

        for service in pending_services:
            laboratory = cls.get_service_laboratory(service.id)
            if laboratory.id not in labs:
                continue

            number = service.fraction.get_formated_number('pt-m-sn-sy-fn')
            number = (number + '-' + str(service.sample.label))
            number_parts = number.split('-')
            order = (number_parts[3] + '-' + number_parts[2] + '-' +
                number_parts[4])

            result_estimated = []
            result_estimated = cls.get_results_estimated(service.id)
            result_estimated_date = None
            result_estimated_waiting = None

            if result_estimated:
                result_estimated_waiting = result_estimated[0][1]
                confirmation_date = result_estimated[0][0]
                c_days = result_estimated_waiting
                result_estimated_date = (confirmation_date +
                    relativedelta(days=c_days))
            notice = None
            report_date = service.report_date
            today_datetime = get_print_date()
            today = today_datetime.date()

            if report_date:
                if report_date < today:
                    notice = 'Timed out'
            else:
                if result_estimated_date:
                    if result_estimated_date < today:
                        notice = 'Timed out'

            if report_date:
                d = (report_date - today).days
                if d >= 0 and d < 3:
                    notice = 'To expire'
            else:
                if result_estimated_date:
                    d = (result_estimated_date - today).days
                    if d >= 0 and d < 3:
                        notice = 'To expire'

            if data['include_method']:
                method_pending = cls.get_unplanned_method(service.id)
                for method in method_pending:
                    record = {
                        'laboratory': laboratory.rec_name,
                        'service': service.analysis.rec_name,
                        'method': method[0],
                        'party': service.party.code,
                        'order': order,
                        'number': number,
                        'date': service.sample.date2,
                        'sample_client_description': (
                            service.sample.sample_client_description),
                        'current_location': (
                            service.fraction.current_location.code
                            if service.fraction.current_location else ''),
                        'fraction_type': service.fraction.type.code,
                        'priority': service.priority,
                        'urgent': 'Yes' if service.urgent else 'No',
                        'comments': (
                            '%s - %s' % (service.fraction.comments or '',
                            service.sample.comments or '')),
                        'report_date': service.report_date,
                        'confirmation_date': (service.confirmation_date
                           if service.confirmation_date else ''),
                        'results_estimated_date': (result_estimated_date
                            if result_estimated_date else ''),
                        'results_estimated_waiting': (
                            result_estimated_waiting
                            if result_estimated_waiting else ''),
                        'notice': (notice
                            if notice else ''),
                        }
                    objects.append(record)
            else:
                record = {
                    'laboratory': laboratory.rec_name,
                    'service': service.analysis.rec_name,
                    'party': service.party.code,
                    'order': order,
                    'number': number,
                    'date': service.sample.date2,
                    'sample_client_description': (
                        service.sample.sample_client_description),
                    'current_location': (
                        service.fraction.current_location.code
                        if service.fraction.current_location else ''),
                    'fraction_type': service.fraction.type.code,
                    'priority': service.priority,
                    'urgent': 'Yes' if service.urgent else 'No',
                    'comments': ('%s - %s' % (service.fraction.comments or '',
                       service.sample.comments or '')),
                    'report_date': service.report_date,
                    'confirmation_date': (service.confirmation_date
                        if service.confirmation_date else ''),
                    'results_estimated_date': (result_estimated_date
                        if result_estimated_date else ''),
                    'results_estimated_waiting': (
                        result_estimated_waiting
                        if result_estimated_waiting else ''),
                    'notice': (notice
                        if notice else ''),
                    }
                objects.append(record)

        objects = sorted(objects, key=lambda x: (
                x['laboratory'], x['service'], x['party'], x['order']))

        report_context['objects'] = objects

        return report_context

    @classmethod
    def get_unplanned_services(cls):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        Analysis = pool.get('lims.analysis')

        cursor.execute('SELECT DISTINCT(d.service) '
            'FROM "' + EntryDetailAnalysis._table + '" d '
                'INNER JOIN "' + Analysis._table + '" a '
                'ON a.id = d.analysis '
            'WHERE d.state = \'unplanned\' '
                'AND a.behavior != \'internal_relation\'')
        not_planned_ids = [s[0] for s in cursor.fetchall()]
        return not_planned_ids

    @classmethod
    def get_unplanned_method(cls, service_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        Analysis = pool.get('lims.analysis')
        LabMethod = pool.get('lims.lab.method')

        cursor.execute('SELECT DISTINCT(m.code) '
            'FROM "' + EntryDetailAnalysis._table + '" d '
                'INNER JOIN "' + Analysis._table + '" a '
                'ON a.id = d.analysis '
                'INNER JOIN"' + LabMethod._table + '" m '
                'ON d.method = m.id '
            'WHERE d.service = %s '
                'AND d.state = \'unplanned\' '
                'AND a.behavior != \'internal_relation\'',
                (service_id,))
        not_planned_ids = list(cursor.fetchall())
        return not_planned_ids

    @classmethod
    def get_service_laboratory(cls, service_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        Service = pool.get('lims.service')
        Laboratory = pool.get('lims.laboratory')

        cursor.execute('SELECT d.laboratory '
            'FROM "' + EntryDetailAnalysis._table + '" d '
                'INNER JOIN "' + Service._table + '" s '
                'ON s.id = d.service '
            'WHERE s.id = %s '
            'ORDER BY d.id ASC LIMIT 1',
            (service_id,))
        return Laboratory(cursor.fetchone()[0])

    @classmethod
    def get_results_estimated(cls, service_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        NotebookLine = pool.get('lims.notebook.line')
        Analysis = pool.get('lims.analysis')

        cursor.execute('SELECT  d.confirmation_date, '
                'n.results_estimated_waiting '
            'FROM "' + NotebookLine._table + '" n '
                'INNER JOIN "' + EntryDetailAnalysis._table + '" d '
                'ON (d.service = n.service  AND d.analysis = n.analysis) '
                'INNER JOIN "' + Analysis._table + '" a '
                'ON a.id = d.analysis '
            'WHERE d.state = \'unplanned\' '
                'AND d.service = %s '
                'AND n.results_estimated_waiting IS NOT Null '
                'AND a.behavior != \'internal_relation\''
                'ORDER BY n.results_estimated_waiting ASC LIMIT 1',
                (service_id,))

        return list(cursor.fetchall())


class PrintBlindSampleReportStart(ModelView):
    'Blind Samples Report'
    __name__ = 'lims.print_blind_sample_report.start'

    date_from = fields.Date('Date from', required=True)
    date_to = fields.Date('Date to', required=True)


class PrintBlindSampleReport(Wizard):
    'Blind Samples Report'
    __name__ = 'lims.print_blind_sample_report'

    start = StateView('lims.print_blind_sample_report.start',
        'lims.lims_print_blind_sample_report_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print', 'print_', 'tryton-print', default=True),
            ])
    print_ = StateAction('lims.report_blind_sample')

    def do_print_(self, action):
        BlindSample = Pool().get('lims.blind_sample')

        blind_samples = BlindSample.search_count([
            ('date', '>=', self.start.date_from),
            ('date', '<=', self.start.date_to),
            ('line.result', '!=', None),
            ])
        if blind_samples > 0:
            data = {
                'date_from': self.start.date_from,
                'date_to': self.start.date_to,
                }
            return action, data

    def transition_print_(self):
        return 'end'


class BlindSampleReport(Report):
    'Blind Samples Report'
    __name__ = 'lims.blind_sample_report'

    @classmethod
    def get_context(cls, records, data):
        report_context = super(BlindSampleReport, cls).get_context(records,
                data)
        BlindSample = Pool().get('lims.blind_sample')

        report_context['company'] = report_context['user'].company

        objects = []
        blind_samples = BlindSample.search([
            ('date', '>=', data['date_from']),
            ('date', '<=', data['date_to']),
            ('line.result', '!=', None),
            ], order=[('date', 'ASC')])
        for bs in blind_samples:

            if bs.line.converted_result:
                result = float(bs.line.converted_result)
                unit = bs.line.final_unit
                concentration = bs.line.final_concentration
                result = round(result, bs.line.decimals)
            elif bs.line.result:
                result = float(bs.line.result)
                unit = bs.line.initial_unit
                concentration = bs.line.initial_concentration
                result = round(result, bs.line.decimals)
            else:
                result = None
                unit = None
                concentration = ''

            record = {
                'date': bs.date,
                'fraction': bs.fraction.rec_name,
                'report': (bs.line.results_report.number if
                    bs.line.results_report else ''),
                'repetition': bs.line.repetition,
                'analysis_origin': bs.line.analysis_origin,
                'analysis': bs.analysis.rec_name,
                'result': result,
                'unit': unit.symbol if unit else '',
                'concentration': concentration,
                'original_fraction': '',
                'original_report': '',
                'original_result': '',
                'original_unit': '',
                'original_concentration': '',
                'error': '',
                'max_sd': '',
                'two_max_sd': '',
                'accepted': '',
                }
            if bs.original_fraction:
                record['original_fraction'] = bs.original_fraction.rec_name
                if bs.original_line:
                    if bs.original_line.results_report:
                        record['original_report'] = (
                            bs.original_line.results_report.number)
                    if bs.original_line.converted_result:
                        original_result = float(
                            bs.original_line.converted_result)
                        original_unit = bs.original_line.final_unit
                        original_concentration = (
                            bs.original_line.final_concentration)
                    elif bs.original_line.result:
                        original_result = float(bs.original_line.result)
                        original_unit = bs.original_line.initial_unit
                        original_concentration = (
                            bs.original_line.initial_concentration)
                    else:
                        original_result = None
                    if original_result:
                        original_result = round(original_result,
                            bs.original_line.decimals)
                        record['original_result'] = original_result
                        record['original_unit'] = (original_unit.symbol
                            if original_unit else '')
                        record['original_concentration'] = (
                            original_concentration)
                        if unit == original_unit:
                            average = (result + original_result) / 2
                            difference = result - original_result
                            record['error'] = round(difference * 100 / average,
                                2)
                            try:
                                maximum_concentration = float(
                                    unit.maximum_concentration)
                                rsd_horwitz = float(unit.rsd_horwitz)
                            except (TypeError, ValueError):
                                maximum_concentration = 0
                                rsd_horwitz = 0

                            if result <= maximum_concentration:
                                record['max_sd'] = round(average * rsd_horwitz,
                                    2)
                                record['two_max_sd'] = round(record['max_sd'] *
                                    2, 2)
                                if abs(difference) <= record['two_max_sd']:
                                    record['accepted'] = 'a'
                                else:
                                    record['accepted'] = 'r'
            else:
                if bs.min_value and bs.max_value:
                    min_value = float(bs.min_value)
                    max_value = float(bs.max_value)
                    if min_value <= result and result <= max_value:
                        record['error'] = 'OK'
                    elif result < min_value:
                        record['error'] = round(result - min_value, 2)
                    elif result > max_value:
                        record['error'] = round(result - max_value, 2)
            objects.append(record)

        report_context['objects'] = objects

        report_context['date_from'] = data['date_from']
        report_context['date_to'] = data['date_to']

        return report_context

    def _get_variables(self, formula, notebook_line):
        VolumeConversion = Pool().get('lims.volume.conversion')

        variables = {}
        for var in ('DI',):
            while True:
                idx = formula.find(var)
                if idx >= 0:
                    variables[var] = 0
                    formula = formula.replace(var, '_')
                else:
                    break
        for var in variables.keys():
            if var == 'DI':
                ic = float(notebook_line.final_concentration)
                result = VolumeConversion.brixToDensity(ic)
                if result:
                    variables[var] = result
        return variables


class PlanificationSequenceAnalysisReport(Report):
    'Sequence Analysis'
    __name__ = 'lims.planification.sequence.analysis.report'

    @classmethod
    def get_context(cls, records, data):
        report_context = super(PlanificationSequenceAnalysisReport,
                cls).get_context(records, data)

        report_context['company'] = report_context['user'].company

        objects = {}
        for planification in records:
            if planification.state != 'confirmed':
                continue
            date = str(planification.start_date)
            if date not in objects:
                objects[date] = {
                    'date': planification.start_date,
                    'methods': {},
                    }
            for detail in planification.details:
                fraction = detail.fraction
                for service_detail in detail.details:
                    if (service_detail.notebook_line.analysis.behavior ==
                            'internal_relation'):
                        continue
                    notebook_line = service_detail.notebook_line
                    method_id = notebook_line.method.id
                    if method_id not in objects[date]['methods']:
                        objects[date]['methods'][method_id] = {
                            'method': notebook_line.method.code,
                            'lines': {},
                            }

                    number = fraction.get_formated_number('sn-sy-fn')
                    number = (number + '-' + str(notebook_line.repetition))
                    number_parts = number.split('-')
                    order = (number_parts[1] + '-' + number_parts[0] + '-' +
                        number_parts[2] + '-' + number_parts[3])

                    product_type = fraction.product_type.code
                    matrix = fraction.matrix.code
                    fraction_type = fraction.type.code
                    analysis = notebook_line.analysis.rec_name
                    priority = notebook_line.priority
                    urgent = notebook_line.urgent
                    report_date = (notebook_line.report_date or
                        notebook_line.results_estimated_date)
                    trace_report = fraction.sample.trace_report
                    sample_client_description = (
                        fraction.sample.sample_client_description)
                    key = (number, product_type, matrix, fraction_type,
                        analysis, priority, trace_report)
                    if key not in objects[date]['methods'][method_id]['lines']:
                        objects[date]['methods'][method_id]['lines'][key] = {
                            'order': order,
                            'number': number,
                            'product_type': product_type,
                            'matrix': matrix,
                            'fraction_type': fraction_type,
                            'analysis': analysis,
                            'priority': priority,
                            'urgent': urgent,
                            'report_date': report_date,
                            'trace_report': trace_report,
                            'sample_client_description': (
                                sample_client_description),
                            }

        for k1 in objects.keys():
            for k2, lines in objects[k1]['methods'].items():
                sorted_lines = sorted(list(lines['lines'].values()),
                    key=lambda x: x['order'])
                objects[k1]['methods'][k2]['lines'] = sorted_lines

        report_context['objects'] = objects

        return report_context
