# -*- coding: utf-8 -*-
# This file is part of lims_planification module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from datetime import datetime
import operator
import logging

from trytond.model import Workflow, ModelView, ModelSQL, fields, Unique
from trytond.pool import PoolMeta, Pool
from trytond.transaction import Transaction
from trytond.pyson import Eval, Equal, Bool, Not, Or, If, Len

__all__ = ['LimsPlanification', 'LimsPlanificationTechnician',
    'LimsPlanificationTechnicianDetail', 'LimsPlanificationDetail',
    'LimsPlanificationServiceDetail', 'LimsNotebookLine',
    'LimsNotebookLineFraction', 'LimsEntryDetailAnalysis', 'LimsFraction',
    'LimsPlanificationServiceDetailLaboratoryProfessional',
    'LimsPlanificationAnalysis', 'LimsPlanificationFraction',
    'LimsFractionReagent', 'LimsFractionType', 'LimsLaboratoryProfessional',
    'LimsLabProfessionalMethod', 'LimsLabProfessionalMethodRequalification',
    'LimsLabProfessionalMethodRequalificationSupervisor',
    'LimsLabProfessionalMethodRequalificationControl', 'LimsAnalysis',
    'LimsService', 'LimsBlindSample']


class LimsPlanification(Workflow, ModelSQL, ModelView):
    'Planification'
    __name__ = 'lims.planification'
    __metaclass__ = PoolMeta
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
        super(LimsPlanification, cls).__setup__()
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
        LimsAnalysisLaboratory = pool.get('lims.analysis-laboratory')
        LimsAnalysis = pool.get('lims.analysis')

        if not laboratory:
            return []

        cursor.execute('SELECT al.analysis '
            'FROM "' + LimsAnalysisLaboratory._table + '" al '
                'INNER JOIN "' + LimsAnalysis._table + '" a '
                'ON a.id = al.analysis '
            'WHERE al.laboratory = %s '
                'AND a.behavior != \'internal_relation\'',
            (laboratory.id,))
        analysis_sets_list = [a[0] for a in cursor.fetchall()]

        groups_list = []
        cursor.execute('SELECT id '
            'FROM "' + LimsAnalysis._table + '" '
            'WHERE type = \'group\'')
        groups_list_ids = [g[0] for g in cursor.fetchall()]
        for group_id in groups_list_ids:
            if LimsPlanification._get_group_available(group_id,
                    analysis_sets_list):
                groups_list.append(group_id)

        return analysis_sets_list + groups_list

    @staticmethod
    def _get_group_available(group_id, analysis_sets_list):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsAnalysisIncluded = pool.get('lims.analysis.included')
        LimsAnalysis = pool.get('lims.analysis')

        cursor.execute('SELECT ia.included_analysis, a.type '
            'FROM "' + LimsAnalysisIncluded._table + '" ia '
                'INNER JOIN "' + LimsAnalysis._table + '" a '
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
                    LimsPlanification._get_group_available(analysis[0],
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
        return super(LimsPlanification, cls).create(vlist)

    @classmethod
    def check_delete(cls, planifications):
        for planification in planifications:
            if planification.state not in ['draft', 'preplanned']:
                cls.raise_user_error('delete_planification',
                    (planification.rec_name,))

    @classmethod
    def delete(cls, planifications):
        cls.check_delete(planifications)
        super(LimsPlanification, cls).delete(planifications)

    @classmethod
    def copy(cls, planifications, default=None):
        cls.raise_user_error('copy_planification')

    @classmethod
    @ModelView.button_action('lims_planification.wiz_lims_add_analysis')
    def add_analysis(cls, planifications):
        pass

    @classmethod
    @ModelView.button_action('lims_planification.wiz_lims_search_fractions')
    def search_fractions(cls, planifications):
        pass

    @classmethod
    @ModelView.button_action(
        'lims_planification.wiz_lims_search_planned_fractions')
    def search_planned_fractions(cls, planifications):
        pass

    @classmethod
    @ModelView.button
    @Workflow.transition('preplanned')
    def preplan(cls, planifications):
        for planification in planifications:
            planification.check_start_date()

    @classmethod
    @ModelView.button_action(
        'lims_planification.wiz_lims_technicians_qualification')
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
            sorted_fractions = sorted(fractions.values(), key=lambda x: x)
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
        LimsPlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')
        LimsNotebookLine = pool.get('lims.notebook.line')

        notebook_lines = []
        service_details = LimsPlanificationServiceDetail.search([
            ('detail.planification', '=', self.id),
            ('notebook_line', '!=', None),
            ])
        for service_detail in service_details:
            notebook_line = LimsNotebookLine(
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
            LimsNotebookLine.save(notebook_lines)

    def update_analysis_detail(self):
        pool = Pool()
        LimsPlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')
        LimsEntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        analysis_detail_ids = []
        service_details = LimsPlanificationServiceDetail.search([
            ('detail.planification', '=', self.id),
            ('notebook_line.analysis_detail', '!=', None),
            ])
        for service_detail in service_details:
            analysis_detail_ids.append(
                service_detail.notebook_line.analysis_detail.id)

        analysis_details = LimsEntryDetailAnalysis.search([
            ('id', 'in', analysis_detail_ids),
            ])
        if analysis_details:
            LimsEntryDetailAnalysis.write(analysis_details, {
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
        LimsNotebookLine = Pool().get('lims.notebook.line')
        for detail in self.details:
            for service_detail in detail.details:
                if service_detail.is_control and service_detail.notebook_line:
                    notebook_line = LimsNotebookLine(
                        service_detail.notebook_line.id)
                    notebook_line.start_date = None
                    notebook_line.laboratory_professionals = []
                    notebook_line.planification = None
                    notebook_line.controls = []
                    notebook_line.save()

    def re_update_analysis_detail(self):
        LimsEntryDetailAnalysis = Pool().get('lims.entry.detail.analysis')
        analysis_detail_ids = []
        for detail in self.details:
            for service_detail in detail.details:
                if (service_detail.is_control and service_detail.notebook_line
                        and service_detail.notebook_line.analysis_detail):
                    analysis_detail_ids.append(
                        service_detail.notebook_line.analysis_detail.id)
        analysis_details = LimsEntryDetailAnalysis.search([
            ('id', 'in', analysis_detail_ids),
            ])
        if analysis_details:
            LimsEntryDetailAnalysis.write(analysis_details, {
                'state': 'unplanned',
                })

    def unlink_controls(self):
        pool = Pool()
        LimsPlanificationFraction = pool.get('lims.planification-fraction')
        LimsPlanificationDetail = pool.get('lims.planification.detail')

        controls = LimsPlanificationFraction.search([
            ('planification', '=', self.id),
            ])
        if controls:
            LimsPlanificationFraction.delete(controls)

        controls_details = LimsPlanificationDetail.search([
            ('planification', '=', self.id),
            ('details.is_control', '=', True),
            ])
        if controls_details:
            LimsPlanificationDetail.delete(controls_details)

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
        LimsUserLaboratory = pool.get('lims.user-laboratory')
        LimsLaboratoryProfessional = pool.get('lims.laboratory.professional')

        if not self.laboratory:
            return []
        users = LimsUserLaboratory.search([
            ('laboratory', '=', self.laboratory.id),
            ])
        if not users:
            return []
        professionals = LimsLaboratoryProfessional.search([
            ('party.lims_user', 'in', [u.user.id for u in users]),
            ])
        if not professionals:
            return []
        return [p.id for p in professionals]

    @classmethod
    @ModelView.button_action('lims_planification.wiz_lims_relate_technicians')
    def relate_technicians(cls, planifications):
        pass

    @classmethod
    @ModelView.button_action('lims_planification.wiz_lims_unlink_technicians')
    def unlink_technicians(cls, planifications):
        pass

    @classmethod
    @ModelView.button_action('lims_planification.wiz_lims_replace_technician')
    def replace_technician(cls, planifications):
        pass

    @classmethod
    @ModelView.button_action('lims_planification.wiz_lims_add_fraction_con')
    def add_fraction_con(cls, planifications):
        pass

    @classmethod
    @ModelView.button_action('lims_planification.wiz_lims_add_fraction_rm_bmz')
    def add_fraction_rm_bmz(cls, planifications):
        pass

    @classmethod
    @ModelView.button_action('lims_planification.wiz_lims_add_fraction_bre')
    def add_fraction_bre(cls, planifications):
        pass

    @classmethod
    @ModelView.button_action('lims_planification.wiz_lims_add_fraction_mrt')
    def add_fraction_mrt(cls, planifications):
        pass

    @classmethod
    @ModelView.button_action('lims_planification.wiz_lims_remove_control')
    def remove_control(cls, planifications):
        pass


class LimsPlanificationTechnician(ModelSQL, ModelView):
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
        super(LimsPlanificationTechnician, cls).__setup__()
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
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsFraction = pool.get('lims.fraction')
        LimsLabMethod = pool.get('lims.lab.method')

        cursor.execute('SELECT DISTINCT(f.number, nl.analysis_origin, '
                'm.code||\' - \'||m.name) '
            'FROM "' + PlanificationDetailProfessional._table + '" sdp '
                'INNER JOIN "' + PlanificationServiceDetail._table + '" sd '
                'ON sd.id = sdp.detail '
                'INNER JOIN "' + PlanificationDetail._table + '" d '
                'ON d.id = sd.detail '
                'INNER JOIN "' + LimsNotebookLine._table + '" nl '
                'ON nl.id = sd.notebook_line '
                'INNER JOIN "' + LimsLabMethod._table + '" m '
                'ON m.id = nl.method '
                'INNER JOIN "' + LimsFraction._table + '" f '
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


class LimsPlanificationTechnicianDetail(ModelView):
    'Technician Detail'
    __name__ = 'lims.planification.technician.detail'

    fraction = fields.Char('Fraction')
    analysis_origin = fields.Char('Analysis origin')
    method = fields.Char('Method')


class LimsPlanificationDetail(ModelSQL, ModelView):
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

    @classmethod
    def __setup__(cls):
        super(LimsPlanificationDetail, cls).__setup__()
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

    @classmethod
    def view_attributes(cls):
        return [
            ('/tree', 'colors',
                If(Len(Eval('comments')) > 0, 'blue', 'black')),
            ]


class LimsPlanificationServiceDetail(ModelSQL, ModelView):
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


class LimsPlanificationServiceDetailLaboratoryProfessional(ModelSQL):
    'Planification Detail - Laboratory Professional'
    __name__ = 'lims.planification.service_detail-laboratory.professional'
    _table = 'lims_plan_service_d-laboratory_professional'

    detail = fields.Many2One('lims.planification.service_detail',
        'Planification detail', ondelete='CASCADE', select=True,
        required=True)
    professional = fields.Many2One('lims.laboratory.professional',
        'Laboratory professional', ondelete='CASCADE', select=True,
        required=True)


class LimsPlanificationAnalysis(ModelSQL):
    'Planification - Analysis'
    __name__ = 'lims.planification-analysis'

    planification = fields.Many2One('lims.planification', 'Planification',
        ondelete='CASCADE', select=True, required=True)
    analysis = fields.Many2One('lims.analysis', 'Analysis',
        ondelete='CASCADE', select=True, required=True)


class LimsPlanificationFraction(ModelSQL):
    'Planification - Fraction'
    __name__ = 'lims.planification-fraction'

    planification = fields.Many2One('lims.planification', 'Planification',
        ondelete='CASCADE', select=True, required=True)
    fraction = fields.Many2One('lims.fraction', 'Fraction',
        ondelete='CASCADE', select=True, required=True)


class LimsNotebookLine:
    __name__ = 'lims.notebook.line'
    __metaclass__ = PoolMeta

    planning_comments = fields.Function(fields.Text('Planification comments'),
        'get_planning_comments')
    controls = fields.Many2Many('lims.notebook.line-fraction',
        'notebook_line', 'fraction', 'Controls')

    def get_planning_comments(self, name=None):
        if self.planification:
            return self.planification.comments
        return ''


class LimsNotebookLineFraction(ModelSQL):
    'Laboratory Notebook Line - Fraction'
    __name__ = 'lims.notebook.line-fraction'

    notebook_line = fields.Many2One('lims.notebook.line', 'Notebook Line',
        ondelete='CASCADE', select=True, required=True)
    fraction = fields.Many2One('lims.fraction', 'Fraction',
        ondelete='CASCADE', select=True, required=True)


class LimsEntryDetailAnalysis:
    __name__ = 'lims.entry.detail.analysis'
    __metaclass__ = PoolMeta

    state = fields.Selection([
        ('draft', 'Draft'),
        ('unplanned', 'Unplanned'),
        ('planned', 'Planned'),
        ('done', 'Done'),
        ('reported', 'Reported'),
        ], 'State', readonly=True)
    cie_min_value = fields.Char('Minimum value')
    cie_max_value = fields.Char('Maximum value')
    cie_fraction_type = fields.Function(fields.Boolean('Blind Sample'),
        'get_cie_fraction_type')

    @staticmethod
    def default_state():
        return 'draft'

    def get_cie_fraction_type(self, name=None):
        if (self.service and self.service.fraction and
                self.service.fraction.cie_fraction_type and
                not self.service.fraction.cie_original_fraction):
            return True
        return False

    @classmethod
    def view_attributes(cls):
        return super(LimsEntryDetailAnalysis, cls).view_attributes() + [
            ('//group[@id="cie"]', 'states', {
                    'invisible': ~Eval('cie_fraction_type'),
                    })]

    @classmethod
    def write(cls, *args):
        super(LimsEntryDetailAnalysis, cls).write(*args)
        actions = iter(args)
        for details, vals in zip(actions, actions):
            change_cie_data = False
            for field in ('cie_min_value', 'cie_max_value'):
                if vals.get(field):
                    change_cie_data = True
                    break
            if change_cie_data:
                for detail in details:
                    if (detail.service and detail.service.fraction
                            and detail.service.fraction.confirmed):
                        detail.update_cie_data()

    def update_cie_data(self):
        pool = Pool()
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsBlindSample = pool.get('lims.blind_sample')

        nlines = LimsNotebookLine.search([
            ('analysis_detail', '=', self.id),
            ])
        if nlines:
            blind_samples = LimsBlindSample.search([
                ('line', 'in', [nl.id for nl in nlines]),
                ])
            if blind_samples:
                LimsBlindSample.write(blind_samples, {
                    'min_value': self.cie_min_value,
                    'max_value': self.cie_max_value,
                    })


class LimsFraction:
    __name__ = 'lims.fraction'
    __metaclass__ = PoolMeta

    special_type = fields.Function(fields.Char('Fraction type'),
        'on_change_with_special_type',
        searcher='search_special_type')
    con_type = fields.Selection([
        ('', ''),
        ('con', 'CON'),
        ('coi', 'COI'),
        ('mrc', 'MRC'),
        ('sla', 'SLA'),
        ('itc', 'ITC'),
        ('itl', 'ITL'),
        ], 'Type', sort=False)
    con_original_fraction = fields.Many2One('lims.fraction',
        'Original fraction')
    bmz_type = fields.Selection([
        ('', ''),
        ('sla', 'SLA'),
        ('noinitialbmz', 'No initial BMZ'),
        ], 'Type', sort=False)
    bmz_product_type = fields.Many2One('lims.product.type', 'Product type')
    bmz_matrix = fields.Many2One('lims.matrix', 'Matrix')
    bmz_original_fraction = fields.Many2One('lims.fraction',
        'Original fraction')
    rm_type = fields.Selection([
        ('', ''),
        ('sla', 'SLA'),
        ('noinitialrm', 'No initial RM'),
        ], 'Type', sort=False)
    rm_product_type = fields.Many2One('lims.product.type', 'Product type')
    rm_matrix = fields.Many2One('lims.matrix', 'Matrix')
    rm_original_fraction = fields.Many2One('lims.fraction',
        'Original fraction')
    bre_product_type = fields.Many2One('lims.product.type', 'Product type')
    bre_matrix = fields.Many2One('lims.matrix', 'Matrix')
    bre_reagents = fields.One2Many('lims.fraction.reagent', 'fraction',
        'Reagents')
    mrt_product_type = fields.Many2One('lims.product.type', 'Product type')
    mrt_matrix = fields.Many2One('lims.matrix', 'Matrix')
    cie_fraction_type_available = fields.Function(fields.Boolean(
        'Available for Blind Sample'),
        'on_change_with_cie_fraction_type_available')
    cie_fraction_type = fields.Boolean('Blind Sample',
        states={'readonly': Not(Bool(Eval('cie_fraction_type_available')))},
        depends=['cie_fraction_type_available'])
    cie_original_fraction = fields.Many2One('lims.fraction',
        'Original fraction', states={'readonly': Bool(Eval('confirmed'))},
        depends=['confirmed'])

    @classmethod
    def __setup__(cls):
        super(LimsFraction, cls).__setup__()
        cls._buttons.update({
            'load_services': {
                'invisible': Or(Bool(Eval('button_manage_services_available')),
                    Bool(Eval('services'))),
                },
            })
        for field in ('special_type', 'con_original_fraction', 'services',
                'create_date'):
            if field not in cls.label.on_change_with:
                cls.label.on_change_with.add(field)

    @staticmethod
    def default_cie_fraction_type():
        return False

    @fields.depends('type')
    def on_change_with_special_type(self, name=None):
        Config = Pool().get('lims.configuration')
        if self.type:
            config = Config(1)
            if self.type == config.mcl_fraction_type:
                return 'mcl'
            elif self.type == config.con_fraction_type:
                return 'con'
            elif self.type == config.bmz_fraction_type:
                return 'bmz'
            elif self.type == config.rm_fraction_type:
                return 'rm'
            elif self.type == config.bre_fraction_type:
                return 'bre'
            elif self.type == config.mrt_fraction_type:
                return 'mrt'
            elif self.type == config.coi_fraction_type:
                return 'coi'
            elif self.type == config.mrc_fraction_type:
                return 'mrc'
            elif self.type == config.sla_fraction_type:
                return 'sla'
            elif self.type == config.itc_fraction_type:
                return 'itc'
            elif self.type == config.itl_fraction_type:
                return 'itl'
        return ''

    @classmethod
    def search_special_type(cls, name, clause):
        Config = Pool().get('lims.configuration')
        if clause[1] in ('=', '!='):
            types = [clause[2]]
        elif clause[1] in ('in', 'not in'):
            types = clause[2]
        else:
            return []
        if types:
            config = Config(1)
            res_type = []
            for type_ in types:
                if type_ == 'mcl':
                    res_type.append(config.mcl_fraction_type)
                if type_ == 'con':
                    res_type.append(config.con_fraction_type)
                if type_ == 'bmz':
                    res_type.append(config.bmz_fraction_type)
                if type_ == 'rm':
                    res_type.append(config.rm_fraction_type)
                if type_ == 'bre':
                    res_type.append(config.bre_fraction_type)
                if type_ == 'mrt':
                    res_type.append(config.mrt_fraction_type)
                if type_ == 'coi':
                    res_type.append(config.coi_fraction_type)
                if type_ == 'mrc':
                    res_type.append(config.mrc_fraction_type)
                if type_ == 'sla':
                    res_type.append(config.sla_fraction_type)
                if type_ == 'itc':
                    res_type.append(config.itc_fraction_type)
                if type_ == 'itl':
                    res_type.append(config.itl_fraction_type)
            if clause[1] in ('=', '!='):
                return [('type', clause[1], res_type[0])]
            elif clause[1] in ('in', 'not in'):
                return [('type', clause[1], res_type)]
        return []

    @fields.depends('special_type', 'con_original_fraction', 'services',
        'create_date')
    def on_change_with_label(self, name=None):
        type = self.special_type
        if type == 'con':
            label = ''
            if self.con_original_fraction:
                label += self.con_original_fraction.label
            if self.services:
                if self.services[0].analysis:
                    label += ' ' + self.services[0].analysis.code
            if self.create_date:
                label += ' ' + str(datetime.date(self.create_date))
            return label
        elif type == 'bmz':
            label = 'BMZ'
            if self.services:
                if self.services[0].analysis:
                    label += ' ' + self.services[0].analysis.code
            if self.create_date:
                label += ' ' + str(datetime.date(self.create_date))
            return label
        elif type == 'rm':
            label = 'RM'
            if self.services:
                if self.services[0].analysis:
                    label += ' ' + self.services[0].analysis.code
            if self.create_date:
                label += ' ' + str(datetime.date(self.create_date))
            return label
        elif type == 'bre':
            label = 'BRE'
            if self.services:
                if self.services[0].analysis:
                    label += ' ' + self.services[0].analysis.code
            if self.create_date:
                label += ' ' + str(datetime.date(self.create_date))
            return label
        elif type == 'mrt':
            label = 'MRT'
            if self.services:
                if self.services[0].analysis:
                    label += ' ' + self.services[0].analysis.code
            if self.create_date:
                label += ' ' + str(datetime.date(self.create_date))
            return label
        else:
            return super(LimsFraction, self).on_change_with_label(name)

    @fields.depends('confirmed', 'type')
    def on_change_with_cie_fraction_type_available(self, name=None):
        if not self.confirmed and self.type and self.type.cie_fraction_type:
            return True
        return False

    @classmethod
    def copy(cls, fractions, default=None):
        if default is None:
            default = {}
        with Transaction().set_context(_check_access=False):
            new_fractions = super(LimsFraction, cls).copy(fractions,
                default=default)
        return new_fractions

    @classmethod
    @ModelView.button_action('lims_planification.wiz_lims_load_services')
    def load_services(cls, fractions):
        pass

    @classmethod
    def confirm(cls, fractions):
        super(LimsFraction, cls).confirm(fractions)
        with Transaction().set_context(_check_access=False):
            fracts = cls.search([
                ('id', 'in', [f.id for f in fractions]),
                ])
        for fraction in fracts:
            fraction.update_detail_analysis()
            if fraction.cie_fraction_type:
                fraction.create_blind_samples()

    def update_detail_analysis(self):
        LimsEntryDetailAnalysis = Pool().get('lims.entry.detail.analysis')

        analysis_details = LimsEntryDetailAnalysis.search([
            ('fraction', '=', self.id),
            ])
        if analysis_details:
            LimsEntryDetailAnalysis.write(analysis_details, {
                'state': 'unplanned',
                })

    def create_blind_samples(self):
        pool = Pool()
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsBlindSample = pool.get('lims.blind_sample')
        Date = pool.get('ir.date')

        confirmation_date = Date.today()

        to_create = []
        nlines = LimsNotebookLine.search([
            ('notebook.fraction', '=', self.id),
            ])
        for nline in nlines:
            detail = nline.analysis_detail
            record = {
                'line': nline.id,
                'entry': nline.fraction.entry.id,
                'sample': nline.fraction.sample.id,
                'fraction': nline.fraction.id,
                'service': nline.service.id,
                'analysis': nline.analysis.id,
                'repetition': nline.repetition,
                'date': confirmation_date,
                'min_value': detail.cie_min_value,
                'max_value': detail.cie_max_value,
                }
            original_fraction = self.cie_original_fraction
            if original_fraction:
                record['original_sample'] = original_fraction.sample.id
                record['original_fraction'] = original_fraction.id
                original_line = LimsNotebookLine.search([
                    ('notebook.fraction', '=', original_fraction.id),
                    ('analysis', '=', nline.analysis.id),
                    ('repetition', '=', nline.repetition),
                    ])
                if original_line:
                    record['original_line'] = original_line[0].id
                    record['original_repetition'] = original_line[0].repetition
            to_create.append(record)
        if to_create:
            LimsBlindSample.create(to_create)

    @classmethod
    def view_attributes(cls):
        return super(LimsFraction, cls).view_attributes() + [
            ('//page[@id="cie"]', 'states', {
                    'invisible': Not(Bool(Eval('cie_fraction_type'))),
                    }),
            ('//page[@id="mrt"]', 'states', {
                    'invisible': Not(Bool(Equal(Eval('special_type'), 'mrt'))),
                    }),
            ('//page[@id="bre"]', 'states', {
                    'invisible': Not(Bool(Equal(Eval('special_type'), 'bre'))),
                    }),
            ('//page[@id="rm"]', 'states', {
                    'invisible': Not(Bool(Equal(Eval('special_type'), 'rm'))),
                    }),
            ('//page[@id="bmz"]', 'states', {
                    'invisible': Not(Bool(Equal(Eval('special_type'), 'bmz'))),
                    }),
            ('//page[@id="con"]', 'states', {
                    'invisible': Not(Bool(Equal(Eval('special_type'), 'con'))),
                    })]

    @staticmethod
    def get_stored_fractions():
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Move = pool.get('stock.move')
        Location = pool.get('stock.location')

        cursor.execute('SELECT DISTINCT ON (m.fraction) m.fraction, l.type '
            'FROM "' + Move._table + '" m '
                'INNER JOIN "' + Location._table + '" l '
                'ON m.to_location = l.id '
            'WHERE m.fraction IS NOT NULL '
                'AND m.state IN (\'assigned\', \'done\') '
            'ORDER BY m.fraction ASC, m.effective_date DESC, m.id DESC')
        return [x[0] for x in cursor.fetchall() if x[1] == 'storage']


class LimsFractionReagent(ModelSQL, ModelView):
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


class LimsFractionType:
    __name__ = 'lims.fraction.type'
    __metaclass__ = PoolMeta

    plannable = fields.Boolean('Plannable')
    default_package_type = fields.Many2One('lims.packaging.type',
        'Default Package type')
    default_fraction_state = fields.Many2One('lims.packaging.integrity',
        'Default Fraction state')
    cie_fraction_type = fields.Boolean('Available for Blind Samples')

    @staticmethod
    def default_plannable():
        return True


class LimsLaboratoryProfessional:
    __name__ = 'lims.laboratory.professional'
    __metaclass__ = PoolMeta

    methods = fields.One2Many('lims.lab.professional.method', 'professional',
        'Methods')


class LimsLabProfessionalMethod(ModelSQL, ModelView):
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

    @classmethod
    def __setup__(cls):
        super(LimsLabProfessionalMethod, cls).__setup__()
        cls._order.insert(0, ('professional', 'ASC'))
        cls._order.insert(1, ('method', 'ASC'))
        t = cls.__table__()
        cls._sql_constraints += [
            ('professional_method_type_uniq',
                Unique(t, t.professional, t.method, t.type),
                'The method already exists for this professional'),
            ]


class LimsLabProfessionalMethodRequalification(ModelSQL, ModelView):
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


class LimsLabProfessionalMethodRequalificationSupervisor(ModelSQL, ModelView):
    'Laboratory Professional Method Requalification Supervisor'
    __name__ = 'lims.lab.professional.method.requalification.supervisor'
    _table = 'lims_lab_pro_method_req_supervisor'

    method_requalification = fields.Many2One(
        'lims.lab.professional.method.requalification',
        'Professional method requalification', ondelete='CASCADE',
        select=True, required=True)
    supervisor = fields.Many2One('lims.laboratory.professional', 'Supervisor',
        required=True)


class LimsLabProfessionalMethodRequalificationControl(ModelSQL, ModelView):
    'Laboratory Professional Method Requalification Control'
    __name__ = 'lims.lab.professional.method.requalification.control'
    _table = 'lims_lab_pro_method_req_control'

    method_requalification = fields.Many2One(
        'lims.lab.professional.method.requalification',
        'Professional method requalification', ondelete='CASCADE',
        select=True, required=True)
    control = fields.Many2One('lims.fraction', 'Control',
        required=True)


class LimsAnalysis:
    __name__ = 'lims.analysis'
    __metaclass__ = PoolMeta

    pending_fractions = fields.Function(fields.Integer('Pending fractions'),
        'get_pending_fractions', searcher='search_pending_fractions')

    @classmethod
    def get_pending_fractions(cls, records, name):
        context = Transaction().context

        date_from = context.get('date_from') or None
        date_to = context.get('date_to') or None
        calculate = context.get('calculate', True)
        if not (date_from and date_to) or not calculate:
            return dict((r.id, None) for r in records)

        new_context = {}
        new_context['date_from'] = date_from
        new_context['date_to'] = date_to
        with Transaction().set_context(new_context):
            return cls.analysis_pending_fractions([r.id for r in records])

    @classmethod
    def search_pending_fractions(cls, name, domain=None):
        context = Transaction().context

        date_from = context.get('date_from') or None
        date_to = context.get('date_to') or None
        calculate = context.get('calculate', True)
        if not (date_from and date_to) or not calculate:
            return []

        new_context = {}
        new_context['date_from'] = date_from
        new_context['date_to'] = date_to
        with Transaction().set_context(new_context):
            pending_fractions = cls.analysis_pending_fractions().iteritems()

        processed_lines = []
        for analysis, pending in pending_fractions:
            processed_lines.append({
                'analysis': analysis,
                'pending_fractions': pending,
                })

        record_ids = [line['analysis'] for line in processed_lines
            if cls._search_pending_fractions_eval_domain(line, domain)]
        return [('id', 'in', record_ids)]

    @classmethod
    def analysis_pending_fractions(cls, analysis_ids=None):
        cursor = Transaction().connection.cursor()
        context = Transaction().context
        pool = Pool()
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsPlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')
        LimsPlanificationDetail = pool.get('lims.planification.detail')
        LimsPlanification = pool.get('lims.planification')
        LimsEntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        LimsAnalysis = pool.get('lims.analysis')
        LimsService = pool.get('lims.service')
        LimsFraction = pool.get('lims.fraction')
        LimsFractionType = pool.get('lims.fraction.type')

        date_from = context.get('date_from')
        date_to = context.get('date_to')

        preplanned_clause = ''
        cursor.execute('SELECT DISTINCT(nl.service) '
            'FROM "' + LimsNotebookLine._table + '" nl '
                'INNER JOIN "' + LimsPlanificationServiceDetail._table +
                '" psd ON psd.notebook_line = nl.id '
                'INNER JOIN "' + LimsPlanificationDetail._table + '" pd '
                'ON psd.detail = pd.id '
                'INNER JOIN "' + LimsPlanification._table + '" p '
                'ON pd.planification = p.id '
            'WHERE p.state = \'preplanned\'')
        preplanned_services = [s[0] for s in cursor.fetchall()]
        if preplanned_services:
            preplanned_services_ids = ', '.join(str(s) for s in
                    preplanned_services)
            preplanned_clause = ('AND service.id NOT IN (' +
                preplanned_services_ids + ')')

        not_planned_services_clause = ''
        cursor.execute('SELECT DISTINCT(d.service) '
            'FROM "' + LimsEntryDetailAnalysis._table + '" d '
                'INNER JOIN "' + LimsAnalysis._table + '" a '
                'ON a.id = d.analysis '
            'WHERE d.state IN (\'draft\', \'unplanned\') '
                'AND a.behavior != \'internal_relation\'')
        not_planned_services = [s[0] for s in cursor.fetchall()]
        if not_planned_services:
            not_planned_services_ids = ', '.join(str(s) for s in
                not_planned_services)
            not_planned_services_clause = ('AND id  IN (' +
                not_planned_services_ids + ')')

        if analysis_ids:
            all_analysis_ids = analysis_ids
        else:
            cursor.execute('SELECT id FROM "' + cls._table + '"')
            all_analysis_ids = [a[0] for a in cursor.fetchall()]

        res = {}
        for analysis_id in all_analysis_ids:
            count = 0
            cursor.execute('SELECT service.id '
                'FROM "' + LimsService._table + '" service '
                    'INNER JOIN "' + LimsFraction._table + '" fraction '
                    'ON fraction.id = service.fraction '
                    'INNER JOIN "' + LimsFractionType._table + '" f_type '
                    'ON f_type.id = fraction.type '
                'WHERE service.analysis = %s '
                    'AND confirmation_date::date >= %s::date '
                    'AND confirmation_date::date <= %s::date '
                    'AND fraction.confirmed = TRUE '
                    'AND f_type.plannable = TRUE '
                    + preplanned_clause,
                (analysis_id, date_from, date_to))
            pending_services = [s[0] for s in cursor.fetchall()]
            if pending_services:
                pending_services_ids = ', '.join(str(s) for s in
                    pending_services)
                cursor.execute('SELECT COUNT(*) '
                    'FROM "' + LimsService._table + '" '
                    'WHERE id IN (' + pending_services_ids + ') '
                        + not_planned_services_clause)
                count = cursor.fetchone()[0]

            res[analysis_id] = count
        return res

    @staticmethod
    def _search_pending_fractions_eval_domain(line, domain):
        operator_funcs = {
            '=': operator.eq,
            '>=': operator.ge,
            '>': operator.gt,
            '<=': operator.le,
            '<': operator.lt,
            '!=': operator.ne,
            'in': lambda v, l: v in l,
            'not in': lambda v, l: v not in l,
            }
        field, op, operand = domain
        value = line.get(field)
        return operator_funcs[op](value, operand)


class LimsService:
    __name__ = 'lims.service'
    __metaclass__ = PoolMeta

    @classmethod
    def __setup__(cls):
        super(LimsService, cls).__setup__()
        cls.planned.getter = 'get_planned'
        cls.planned.searcher = 'search_planned'

    planned = fields.Function(fields.Boolean('Planned'), 'get_planned',
        searcher='search_planned')

    def get_planned(self, name):
        if not self.analysis_detail:
            return False
        for ad in self.analysis_detail:
            if (ad.state in ('draft', 'unplanned') and
                    ad.analysis.behavior != 'internal_relation'):
                return False
        return True

    @classmethod
    def search_planned(cls, name, clause):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsEntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        LimsAnalysis = pool.get('lims.analysis')

        cursor.execute('SELECT DISTINCT(d.service) '
            'FROM "' + LimsEntryDetailAnalysis._table + '" d '
                'INNER JOIN "' + LimsAnalysis._table + '" a '
                'ON a.id = d.analysis '
            'WHERE d.state IN (\'draft\', \'unplanned\') '
                'AND a.behavior != \'internal_relation\'')
        not_planned_ids = [s[0] for s in cursor.fetchall()]

        field, op, operand = clause
        if (op, operand) in (('=', True), ('!=', False)):
            return [('id', 'not in', not_planned_ids)]
        elif (op, operand) in (('=', False), ('!=', True)):
            return [('id', 'in', not_planned_ids)]
        else:
            return []


class LimsBlindSample(ModelSQL, ModelView):
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
