# -*- coding: utf-8 -*-
# This file is part of lims_planification module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from datetime import datetime, date

from dateutil.relativedelta import relativedelta
from trytond.model import ModelSQL, ModelView, fields
from trytond.wizard import Wizard, StateTransition, StateView, StateAction, \
    Button
from trytond.pyson import PYSONEncoder, Eval, Equal, Bool, Not, Or
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction


__all__ = ['LimsRelateTechniciansStart', 'LimsRelateTechniciansResult',
    'LimsRelateTechniciansDetail1', 'LimsRelateTechniciansDetail2',
    'LimsRelateTechniciansDetail3', 'LimsRelateTechnicians',
    'LimsUnlinkTechniciansStart', 'LimsUnlinkTechniciansDetail1',
    'LimsUnlinkTechnicians', 'LimsAddFractionControlStart',
    'LimsAddFractionControl', 'LimsAddFractionRMBMZStart',
    'LimsAddFractionRMBMZ', 'LimsAddFractionBREStart', 'LimsAddFractionBRE',
    'LimsAddFractionMRTStart', 'LimsAddFractionMRT', 'LimsRemoveControlStart',
    'LimsRemoveControl', 'LimsAddAnalysisStart', 'LimsAddAnalysis',
    'LimsSearchFractionsNext', 'LimsSearchFractionsDetail',
    'LimsSearchFractions', 'LimsSearchPlannedFractionsStart',
    'LimsSearchPlannedFractionsNext', 'LimsSearchPlannedFractionsDetail',
    'LimsSearchPlannedFractions', 'LimsCreateFractionControlStart',
    'LimsCreateFractionControl', 'LimsReleaseFractionStart',
    'LimsReleaseFractionEmpty', 'LimsReleaseFractionResult',
    'LimsReleaseFraction', 'LimsQualificationSituations',
    'LimsQualificationSituation', 'LimsQualificationAction',
    'LimsQualificationSituation2', 'LimsQualificationSituation3',
    'LimsQualificationSituation4', 'LimsTechniciansQualification',
    'LimsReplaceTechnicianStart', 'LimsReplaceTechnician',
    'LimsManageServices', 'LimsLoadServices']


class LimsRelateTechniciansStart(ModelView):
    'Relate Technicians'
    __name__ = 'lims.planification.relate_technicians.start'

    exclude_relateds = fields.Boolean('Exclude fractions already related')
    grouping = fields.Selection([
        ('none', 'None'),
        ('origin_method', 'Analysis origin and Method'),
        ('origin', 'Analysis origin'),
        ], 'Grouping', sort=False, required=True)


class LimsRelateTechniciansResult(ModelView):
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


class LimsRelateTechniciansDetail1(ModelSQL, ModelView):
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
        super(LimsRelateTechniciansDetail1,
            cls).__register__(module_name)
        cursor = Transaction().connection.cursor()
        cursor.execute('DELETE FROM "' + cls._table + '"')

    @classmethod
    def __setup__(cls):
        super(LimsRelateTechniciansDetail1, cls).__setup__()
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


class LimsRelateTechniciansDetail2(ModelSQL, ModelView):
    'Fraction Detail'
    __name__ = 'lims.planification.relate_technicians.detail2'
    _table = 'lims_planification_relate_technicians_d2'

    fraction = fields.Many2One('lims.fraction', 'Fraction')
    analysis_origin = fields.Char('Analysis origin')
    method = fields.Many2One('lims.lab.method', 'Method')
    session_id = fields.Integer('Session ID')

    @classmethod
    def __register__(cls, module_name):
        super(LimsRelateTechniciansDetail2,
            cls).__register__(module_name)
        cursor = Transaction().connection.cursor()
        cursor.execute('DELETE FROM "' + cls._table + '"')

    @classmethod
    def __setup__(cls):
        super(LimsRelateTechniciansDetail2, cls).__setup__()
        cls._order.insert(0, ('fraction', 'ASC'))
        cls._order.insert(1, ('analysis_origin', 'ASC'))
        cls._order.insert(2, ('method', 'ASC'))


class LimsRelateTechniciansDetail3(ModelSQL, ModelView):
    'Fraction Detail'
    __name__ = 'lims.planification.relate_technicians.detail3'
    _table = 'lims_planification_relate_technicians_d3'

    fraction = fields.Many2One('lims.fraction', 'Fraction')
    analysis_origin = fields.Char('Analysis origin')
    session_id = fields.Integer('Session ID')

    @classmethod
    def __register__(cls, module_name):
        super(LimsRelateTechniciansDetail3,
            cls).__register__(module_name)
        cursor = Transaction().connection.cursor()
        cursor.execute('DELETE FROM "' + cls._table + '"')

    @classmethod
    def __setup__(cls):
        super(LimsRelateTechniciansDetail3, cls).__setup__()
        cls._order.insert(0, ('fraction', 'ASC'))
        cls._order.insert(1, ('analysis_origin', 'ASC'))


class LimsRelateTechnicians(Wizard):
    'Relate Technicians'
    __name__ = 'lims.planification.relate_technicians'

    start = StateView('lims.planification.relate_technicians.start',
        'lims_planification.lims_relate_technicians_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search', 'search', 'tryton-ok', default=True),
            ])
    search = StateTransition()
    result = StateView('lims.planification.relate_technicians.result',
        'lims_planification.lims_relate_technicians_result_view_form', [
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
        LimsPlanification = Pool().get('lims.planification')

        planification = LimsPlanification(Transaction().context['active_id'])

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
        LimsRelateTechniciansDetail1 = pool.get(
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
            'WHERE d.planification = %s'
            + exclude_relateds_clause,
            (planification_id,))
        for x in cursor.fetchall():
            f, s = x[0], x[1]
            if (f, s) not in details1:
                details1[(f, s)] = {
                    'fraction': f,
                    'service_analysis': s,
                    }

        to_create = []
        for d in details1.itervalues():
            to_create.append({
                'session_id': self._session_id,
                'fraction': d['fraction'],
                'service_analysis': d['service_analysis'],
                })
        return LimsRelateTechniciansDetail1.create(to_create)

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
        LimsRelateTechniciansDetail2 = pool.get(
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
            'WHERE d.planification = %s'
            + exclude_relateds_clause,
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
        for d in details2.itervalues():
            to_create.append({
                'session_id': self._session_id,
                'fraction': d['fraction'],
                'analysis_origin': d['analysis_origin'],
                'method': d['method'],
                })
        return LimsRelateTechniciansDetail2.create(to_create)

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
        LimsRelateTechniciansDetail3 = pool.get(
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
            'WHERE d.planification = %s'
            + exclude_relateds_clause,
            (planification_id,))
        for x in cursor.fetchall():
            f, a = x[0], x[1]
            if (f, a) not in details3:
                details3[(f, a)] = {
                    'fraction': f,
                    'analysis_origin': a,
                    }

        to_create = []
        for d in details3.itervalues():
            to_create.append({
                'session_id': self._session_id,
                'fraction': d['fraction'],
                'analysis_origin': d['analysis_origin'],
                })
        return LimsRelateTechniciansDetail3.create(to_create)

    def transition_relate(self):
        pool = Pool()
        LimsPlanification = pool.get('lims.planification')
        LimsPlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')

        planification = LimsPlanification(Transaction().context['active_id'])

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

        LimsPlanificationServiceDetail.write(details, {
            'staff_responsible': [('remove',
                [t.id for t in self.result.technicians])],
            })
        LimsPlanificationServiceDetail.write(details, {
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
                    'AND d.service_analysis = %s'
                    + exclude_relateds_clause,
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
                    'AND nl.method = %s'
                    + exclude_relateds_clause,
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
                    'AND nl.analysis_origin = %s'
                    + exclude_relateds_clause,
                (planification_id, detail.fraction.id,
                    detail.analysis_origin))
            for x in cursor.fetchall():
                details.append(x[0])

        return PlanificationServiceDetail.browse(details)


class LimsUnlinkTechniciansStart(ModelView):
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


class LimsUnlinkTechniciansDetail1(ModelSQL, ModelView):
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
        super(LimsUnlinkTechniciansDetail1,
            cls).__register__(module_name)
        cursor = Transaction().connection.cursor()
        cursor.execute('DELETE FROM "' + cls._table + '"')

    @classmethod
    def __setup__(cls):
        super(LimsUnlinkTechniciansDetail1, cls).__setup__()
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


class LimsUnlinkTechnicians(Wizard):
    'Unlink Technicians'
    __name__ = 'lims.planification.unlink_technicians'

    start = StateView('lims.planification.unlink_technicians.start',
        'lims_planification.lims_unlink_technicians_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Unlink', 'unlink', 'tryton-ok', default=True),
            ])
    unlink = StateTransition()

    def default_start(self, fields):
        LimsPlanification = Pool().get('lims.planification')

        planification = LimsPlanification(Transaction().context['active_id'])

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
        LimsUnlinkTechniciansDetail1 = pool.get(
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
        for d in details1.itervalues():
            to_create.append({
                'session_id': self._session_id,
                'fraction': d['fraction'],
                'service_analysis': d['service_analysis'],
                })
        return LimsUnlinkTechniciansDetail1.create(to_create)

    def transition_unlink(self):
        pool = Pool()
        LimsPlanification = pool.get('lims.planification')
        LimsPlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')

        planification = LimsPlanification(Transaction().context['active_id'])

        details = self._get_details(planification.id)

        LimsPlanificationServiceDetail.write(details, {
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


class LimsAddFractionControlStart(ModelView):
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
        LimsAnalysis = pool.get('lims.analysis')
        LimsFraction = pool.get('lims.fraction')
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsNotebook = pool.get('lims.notebook')

        if not self.type:
            return []

        p_analysis_ids = []
        for p_analysis in self.planification.analysis:
            if p_analysis.type == 'analysis':
                p_analysis_ids.append(p_analysis.id)
            else:
                p_analysis_ids.extend(
                    LimsAnalysis.get_included_analysis_analysis(p_analysis.id))

        stored_fractions_ids = LimsFraction.get_stored_fractions()

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
        notebook_lines = LimsNotebookLine.search(clause)
        if not notebook_lines:
            return []

        notebook_lines_ids = ', '.join(str(nl.id) for nl in notebook_lines)
        cursor.execute('SELECT DISTINCT(n.fraction) '
            'FROM "' + LimsNotebook._table + '" n '
                'INNER JOIN "' + LimsNotebookLine._table + '" nl '
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
            #if self.original_fraction.services:
            #    if self.original_fraction.services[0].analysis:
            #        label += (' ' +
            #            self.original_fraction.services[0].analysis.code)
        if self.concentration_level:
                label += (' (' +
                        self.concentration_level.description + ')')
        label += ' ' + str(Date.today())
        return label


class LimsAddFractionControl(Wizard):
    'Add Fraction Control'
    __name__ = 'lims.planification.add_fraction_con'

    start = StateView('lims.planification.add_fraction_con.start',
        'lims_planification.lims_add_fraction_con_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Add', 'add', 'tryton-ok', default=True),
            ])
    add = StateTransition()

    @classmethod
    def __setup__(cls):
        super(LimsAddFractionControl, cls).__setup__()
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
        LimsLabWorkYear = pool.get('lims.lab.workyear')
        LimsEntry = pool.get('lims.entry')
        LimsSample = pool.get('lims.sample')
        LimsFraction = pool.get('lims.fraction')
        LimsService = pool.get('lims.service')
        LimsAnalysis = pool.get('lims.analysis')
        LimsNotebookLine = pool.get('lims.notebook.line')

        config = Config(1)
        fraction_type = config.con_fraction_type
        if not fraction_type:
            self.raise_user_error('no_con_fraction_type')

        if (fraction_type.control_charts
                and not self.start.concentration_level):
            self.raise_user_error('no_concentration_level')

        workyear_id = LimsLabWorkYear.find()
        workyear = LimsLabWorkYear(workyear_id)
        if not workyear.default_entry_control:
            self.raise_user_error('no_entry_control')

        entry = LimsEntry(workyear.default_entry_control.id)
        original_fraction = self.start.original_fraction
        original_sample = LimsSample(original_fraction.sample.id)

        # new sample
        new_sample, = LimsSample.copy([original_sample], default={
            'entry': entry.id,
            'date': datetime.now(),
            'label': self.start.label,
            'fractions': [],
            })

        # new fraction
        new_fraction, = LimsFraction.copy([original_fraction], default={
            'sample': new_sample.id,
            'type': fraction_type.id,
            'services': [],
            'con_type': self.start.type,
            'con_original_fraction': original_fraction.id,
            })

        # new services
        services = LimsService.search([
            ('fraction', '=', original_fraction),
            ])
        for service in services:
            if not LimsAnalysis.is_typified(service.analysis,
                    new_sample.product_type, new_sample.matrix):
                continue

            method_id = service.method and service.method.id or None
            device_id = service.device and service.device.id or None
            if service.analysis.type == 'analysis':
                original_lines = LimsNotebookLine.search([
                    ('notebook.fraction', '=', original_fraction.id),
                    ('analysis', '=', service.analysis.id),
                    ('repetition', '=', 0),
                    ], limit=1)
                original_line = original_lines[0] if original_lines else None
                if original_line:
                    method_id = original_line.method.id
                    if original_line.device:
                        device_id = original_line.device.id

            new_service, = LimsService.copy([service], default={
                'fraction': new_fraction.id,
                'method': method_id,
                'device': device_id,
                })

        # confirm fraction: new notebook and stock move
        LimsFraction.confirm([new_fraction])

        # Edit notebook lines
        if fraction_type.control_charts:
            notebook_lines = LimsNotebookLine.search([
                ('notebook.fraction', '=', new_fraction.id),
                ])
            if notebook_lines:
                defaults = {
                    'concentration_level': self.start.concentration_level.id,
                    }
                LimsNotebookLine.write(notebook_lines, defaults)

        # Generate repetition
        if self.start.generate_repetition:
            notebook_lines = LimsNotebookLine.search([
                ('notebook.fraction', '=', new_fraction.id),
                ])
            if notebook_lines:
                self.generate_repetition(notebook_lines)

        return new_fraction

    def generate_repetition(self, notebook_lines):
        pool = Pool()
        LimsAnalysis = pool.get('lims.analysis')
        LimsNotebook = pool.get('lims.notebook')

        p_analysis_ids = []
        for p_analysis in self.start.planification.analysis:
            if p_analysis.type == 'analysis':
                p_analysis_ids.append(p_analysis.id)
            else:
                p_analysis_ids.extend(
                    LimsAnalysis.get_included_analysis_analysis(p_analysis.id))

        analysis_to_repeat = {}
        for notebook_line in notebook_lines:
            if notebook_line.analysis.id not in p_analysis_ids:
                continue
            if notebook_line.analysis.id not in analysis_to_repeat:
                analysis_to_repeat[notebook_line.analysis.id] = notebook_line
            elif (notebook_line.repetition >
                    analysis_to_repeat[notebook_line.analysis.id].repetition):
                analysis_to_repeat[notebook_line.analysis.id] = notebook_line

        notebook = LimsNotebook(notebook_lines[0].notebook.id)

        to_create = []
        for analysis_id, nline in analysis_to_repeat.iteritems():
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
                })
        LimsNotebook.write([notebook], {
            'lines': [('create', to_create)],
            })

    def add_control(self, fraction):
        LimsPlanification = Pool().get('lims.planification')
        LimsPlanification.write([self.start.planification], {
            'controls': [('add', [fraction.id])],
            })

    def add_planification_detail(self, fraction):
        pool = Pool()
        LimsAnalysis = pool.get('lims.analysis')
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsPlanificationDetail = pool.get('lims.planification.detail')

        p_analysis_ids = []
        for p_analysis in self.start.planification.analysis:
            if p_analysis.type == 'analysis':
                p_analysis_ids.append(p_analysis.id)
            else:
                p_analysis_ids.extend(
                    LimsAnalysis.get_included_analysis_analysis(p_analysis.id))
        clause = [
            ('notebook.fraction', '=', fraction.id),
            ('analysis', 'in', p_analysis_ids),
            ('analysis.behavior', '!=', 'internal_relation'),
            ]
        if self.start.type == 'exist':
 #          clause.append(('result', '=', None))
            clause.extend([
                ('result', 'in', (None, '')),
                ('end_date', '=', None),
                ('annulment_date', '=', None),
                ])
        else:
            clause.append(('planification', '=', None))
        notebook_lines = LimsNotebookLine.search(clause)
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
                for k, v in details_to_create.iteritems():
                    details = LimsPlanificationDetail.search([
                        ('planification', '=', self.start.planification.id),
                        ('fraction', '=', k[0]),
                        ('service_analysis', '=', k[1]),
                        ])
                    if details:
                        LimsPlanificationDetail.write([details[0]], {
                            'details': [('create', v)],
                            })
                    else:
                        LimsPlanificationDetail.create([{
                            'planification': self.start.planification.id,
                            'fraction': k[0],
                            'service_analysis': k[1],
                            'details': [('create', v)],
                            }])


class LimsAddFractionRMBMZStart(ModelView):
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
    label = fields.Char('Label', depends=['rm_bmz_type'], states={
        'readonly': Eval('rm_bmz_type') == 'exist'})
    concentration_level = fields.Many2One('lims.concentration.level',
        'Concentration level', states={
            'invisible': Bool(Eval('concentration_level_invisible')),
            }, depends=['concentration_level_invisible'])
    concentration_level_invisible = fields.Boolean(
        'Concentration level invisible')
    generate_repetition = fields.Boolean('Generate repetition',
        states={'readonly': Or(Eval('type') == 'bmz',
            Eval('rm_bmz_type') == 'exist')},
        depends=['type', 'rm_bmz_type'])

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
        LimsAnalysis = pool.get('lims.analysis')
        LimsFraction = pool.get('lims.fraction')
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsNotebook = pool.get('lims.notebook')

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
                    LimsAnalysis.get_included_analysis_analysis(p_analysis.id))

        stored_fractions_ids = LimsFraction.get_stored_fractions()

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
        notebook_lines = LimsNotebookLine.search(clause)
        if not notebook_lines:
            return []

        notebook_lines_ids = ', '.join(str(nl.id) for nl in notebook_lines)
        cursor.execute('SELECT DISTINCT(n.fraction) '
            'FROM "' + LimsNotebook._table + '" n '
                'INNER JOIN "' + LimsNotebookLine._table + '" nl '
                'ON nl.notebook = n.id '
            'WHERE nl.id IN (' + notebook_lines_ids + ')')
        return [x[0] for x in cursor.fetchall()]

    @staticmethod
    def default_product_type_domain():
        cursor = Transaction().connection.cursor()
        LimsTypification = Pool().get('lims.typification')

        cursor.execute('SELECT DISTINCT(product_type) '
                'FROM "' + LimsTypification._table + '" '
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
        LimsTypification = Pool().get('lims.typification')

        if not self.product_type:
            return []

        cursor.execute('SELECT DISTINCT(matrix) '
                'FROM "' + LimsTypification._table + '" '
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


class LimsAddFractionRMBMZ(Wizard):
    'Add Fraction RM/BMZ'
    __name__ = 'lims.planification.add_fraction_rm_bmz'

    start = StateView('lims.planification.add_fraction_rm_bmz.start',
        'lims_planification.lims_add_fraction_rm_bmz_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Add', 'add', 'tryton-ok', default=True),
            ])
    add = StateTransition()

    @classmethod
    def __setup__(cls):
        super(LimsAddFractionRMBMZ, cls).__setup__()
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
        LimsLabWorkYear = pool.get('lims.lab.workyear')
        LimsEntry = pool.get('lims.entry')
        LimsSample = pool.get('lims.sample')
        LimsFraction = pool.get('lims.fraction')
        LimsService = pool.get('lims.service')
        LimsAnalysis = pool.get('lims.analysis')
        LimsNotebookLine = pool.get('lims.notebook.line')

        config = Config(1)
        if self.start.type == 'rm':
            if not config.rm_fraction_type:
                self.raise_user_error('no_rm_fraction_type')
            fraction_type = config.rm_fraction_type
        elif self.start.type == 'bmz':
            if not config.bmz_fraction_type:
                self.raise_user_error('no_bmz_fraction_type')
            fraction_type = config.bmz_fraction_type

        if (fraction_type.control_charts
                and not self.start.concentration_level):
            self.raise_user_error('no_concentration_level')

        workyear_id = LimsLabWorkYear.find()
        workyear = LimsLabWorkYear(workyear_id)
        if not workyear.default_entry_control:
            self.raise_user_error('no_entry_control')

        entry = LimsEntry(workyear.default_entry_control.id)
        original_fraction = self.start.reference_fraction
        original_sample = LimsSample(original_fraction.sample.id)

        # new sample
        new_sample, = LimsSample.copy([original_sample], default={
            'entry': entry.id,
            'date': datetime.now(),
            'label': self.start.label,
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
        new_fraction, = LimsFraction.copy([original_fraction],
            default=fraction_default)

        # new services
        services = LimsService.search([
            ('fraction', '=', original_fraction),
            ])
        for service in services:
            if not LimsAnalysis.is_typified(service.analysis,
                    new_sample.product_type, new_sample.matrix):
                continue

            method_id = service.method and service.method.id or None
            device_id = service.device and service.device.id or None
            if service.analysis.type == 'analysis':
                original_lines = LimsNotebookLine.search([
                    ('notebook.fraction', '=', original_fraction.id),
                    ('analysis', '=', service.analysis.id),
                    ('repetition', '=', 0),
                    ], limit=1)
                original_line = original_lines[0] if original_lines else None
                if original_line:
                    method_id = original_line.method.id
                    if original_line.device:
                        device_id = original_line.device.id

            new_service, = LimsService.copy([service], default={
                'fraction': new_fraction.id,
                'method': method_id,
                'device': device_id,
                })

        # confirm fraction: new notebook and stock move
        LimsFraction.confirm([new_fraction])

        # Edit notebook lines
        if fraction_type.control_charts:
            notebook_lines = LimsNotebookLine.search([
                ('notebook.fraction', '=', new_fraction.id),
                ])
            if notebook_lines:
                defaults = {
                    'concentration_level': self.start.concentration_level.id,
                    }
                LimsNotebookLine.write(notebook_lines, defaults)
        if self.start.type == 'rm':
            notebook_lines = LimsNotebookLine.search([
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
                LimsNotebookLine.write(notebook_lines, defaults)

        # Generate repetition
        if self.start.generate_repetition:
            notebook_lines = LimsNotebookLine.search([
                ('notebook.fraction', '=', new_fraction.id),
                ])
            if notebook_lines:
                self.generate_repetition(notebook_lines)

        return new_fraction

    def _create_control_noref(self):
        pool = Pool()
        Config = pool.get('lims.configuration')
        LimsLabWorkYear = pool.get('lims.lab.workyear')
        LimsEntry = pool.get('lims.entry')
        LimsSample = pool.get('lims.sample')
        LimsFraction = pool.get('lims.fraction')
        LimsService = pool.get('lims.service')
        LimsAnalysis = pool.get('lims.analysis')
        LimsNotebookLine = pool.get('lims.notebook.line')

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

        if (fraction_type.control_charts
                and not self.start.concentration_level):
            self.raise_user_error('no_concentration_level')

        workyear_id = LimsLabWorkYear.find()
        workyear = LimsLabWorkYear(workyear_id)
        if not workyear.default_entry_control:
            self.raise_user_error('no_entry_control')

        laboratory = self.start.planification.laboratory
        entry = LimsEntry(workyear.default_entry_control.id)

        # new sample
        new_sample, = LimsSample.create([{
            'entry': entry.id,
            'date': datetime.now(),
            'product_type': self.start.product_type.id,
            'matrix': self.start.matrix.id,
            'zone': entry.party.entry_zone.id,
            'label': self.start.label,
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
        new_fraction, = LimsFraction.create([fraction_default])

        # new services
        services_default = []
        for p_analysis in self.start.planification.analysis:
            if not LimsAnalysis.is_typified(p_analysis,
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
                    if (t.analysis.id == p_analysis.id
                            and t.by_default is True):
                        method_id = t.method.id
            device_id = None
            if p_analysis.devices:
                for d in p_analysis.devices:
                    if (d.laboratory.id == laboratory.id
                            and d.by_default is True):
                        device_id = d.device.id
            services_default.append({
                'fraction': new_fraction.id,
                'analysis': p_analysis.id,
                'laboratory': laboratory_id,
                'method': method_id,
                'device': device_id,
                })
        for service in services_default:
            new_service, = LimsService.create([service])

            # new analysis details (on service create)

        # confirm fraction: new notebook and stock move
        LimsFraction.confirm([new_fraction])

        # Edit notebook lines
        if fraction_type.control_charts:
            notebook_lines = LimsNotebookLine.search([
                ('notebook.fraction', '=', new_fraction.id),
                ])
            if notebook_lines:
                defaults = {
                    'concentration_level': self.start.concentration_level.id,
                    }
                LimsNotebookLine.write(notebook_lines, defaults)
        if self.start.type == 'rm':
            notebook_lines = LimsNotebookLine.search([
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
                LimsNotebookLine.write(notebook_lines, defaults)

        # Generate repetition
        if self.start.generate_repetition:
            notebook_lines = LimsNotebookLine.search([
                ('notebook.fraction', '=', new_fraction.id),
                ])
            if notebook_lines:
                self.generate_repetition(notebook_lines)

        return new_fraction

    def generate_repetition(self, notebook_lines):
        pool = Pool()
        LimsAnalysis = pool.get('lims.analysis')
        LimsNotebook = pool.get('lims.notebook')

        p_analysis_ids = []
        for p_analysis in self.start.planification.analysis:
            if p_analysis.type == 'analysis':
                p_analysis_ids.append(p_analysis.id)
            else:
                p_analysis_ids.extend(
                    LimsAnalysis.get_included_analysis_analysis(p_analysis.id))

        analysis_to_repeat = {}
        for notebook_line in notebook_lines:
            if notebook_line.analysis.id not in p_analysis_ids:
                continue
            if notebook_line.analysis.id not in analysis_to_repeat:
                analysis_to_repeat[notebook_line.analysis.id] = notebook_line
            elif (notebook_line.repetition >
                    analysis_to_repeat[notebook_line.analysis.id].repetition):
                analysis_to_repeat[notebook_line.analysis.id] = notebook_line

        notebook = LimsNotebook(notebook_lines[0].notebook.id)

        to_create = []
        for analysis_id, nline in analysis_to_repeat.iteritems():
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
                })
        LimsNotebook.write([notebook], {
            'lines': [('create', to_create)],
            })

    def add_control(self, fraction):
        LimsPlanification = Pool().get('lims.planification')
        LimsPlanification.write([self.start.planification], {
            'controls': [('add', [fraction.id])],
            })

    def add_planification_detail(self, fraction):
        pool = Pool()
        LimsAnalysis = pool.get('lims.analysis')
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsPlanificationDetail = pool.get('lims.planification.detail')

        p_analysis_ids = []
        for p_analysis in self.start.planification.analysis:
            if p_analysis.type == 'analysis':
                p_analysis_ids.append(p_analysis.id)
            else:
                p_analysis_ids.extend(
                    LimsAnalysis.get_included_analysis_analysis(p_analysis.id))
        clause = [
            ('notebook.fraction', '=', fraction.id),
            ('analysis', 'in', p_analysis_ids),
            ('analysis.behavior', '!=', 'internal_relation'),
            ]
        if self.start.rm_bmz_type == 'exist':
 #          clause.append(('result', '=', None))
            clause.extend([
                ('result', 'in', (None, '')),
                ('end_date', '=', None),
                ('annulment_date', '=', None),
                ])
        else:
            clause.append(('planification', '=', None))
        notebook_lines = LimsNotebookLine.search(clause)
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
                for k, v in details_to_create.iteritems():
                    details = LimsPlanificationDetail.search([
                        ('planification', '=', self.start.planification.id),
                        ('fraction', '=', k[0]),
                        ('service_analysis', '=', k[1]),
                        ])
                    if details:
                        LimsPlanificationDetail.write([details[0]], {
                            'details': [('create', v)],
                            })
                    else:
                        LimsPlanificationDetail.create([{
                            'planification': self.start.planification.id,
                            'fraction': k[0],
                            'service_analysis': k[1],
                            'details': [('create', v)],
                            }])


class LimsAddFractionBREStart(ModelView):
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
        LimsAnalysis = pool.get('lims.analysis')
        LimsFraction = pool.get('lims.fraction')
        LimsNotebookLine = pool.get('lims.notebook.line')

        if self.type != 'exist':
            return []

        p_analysis_ids = []
        for p_analysis in self.planification.analysis:
            if p_analysis.type == 'analysis':
                p_analysis_ids.append(p_analysis.id)
            else:
                p_analysis_ids.extend(
                    LimsAnalysis.get_included_analysis_analysis(p_analysis.id))

        stored_fractions_ids = LimsFraction.get_stored_fractions()

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
        notebook_lines = LimsNotebookLine.search(clause)

        fractions = [nl.notebook.fraction.id for nl in notebook_lines]
        return list(set(fractions))

    @staticmethod
    def default_product_type_domain():
        cursor = Transaction().connection.cursor()
        LimsTypification = Pool().get('lims.typification')

        cursor.execute('SELECT DISTINCT(product_type) '
                'FROM "' + LimsTypification._table + '" '
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
        LimsTypification = Pool().get('lims.typification')

        if not self.product_type:
            return []

        cursor.execute('SELECT DISTINCT(matrix) '
                'FROM "' + LimsTypification._table + '" '
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


class LimsAddFractionBRE(Wizard):
    'Add Fraction BRE'
    __name__ = 'lims.planification.add_fraction_bre'

    start = StateView('lims.planification.add_fraction_bre.start',
        'lims_planification.lims_add_fraction_bre_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Add', 'add', 'tryton-ok', default=True),
            ])
    add = StateTransition()

    @classmethod
    def __setup__(cls):
        super(LimsAddFractionBRE, cls).__setup__()
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
        LimsLabWorkYear = pool.get('lims.lab.workyear')
        LimsEntry = pool.get('lims.entry')
        LimsSample = pool.get('lims.sample')
        LimsFraction = pool.get('lims.fraction')
        LimsService = pool.get('lims.service')
        LimsAnalysis = pool.get('lims.analysis')
        LimsNotebookLine = pool.get('lims.notebook.line')

        config = Config(1)
        if not config.bre_fraction_type:
            self.raise_user_error('no_bre_fraction_type')
        fraction_type = config.bre_fraction_type
        if (not fraction_type.default_package_type or
                not fraction_type.default_fraction_state):
            self.raise_user_error('no_bre_default_configuration')

        if (fraction_type.control_charts
                and not self.start.concentration_level):
            self.raise_user_error('no_concentration_level')

        workyear_id = LimsLabWorkYear.find()
        workyear = LimsLabWorkYear(workyear_id)
        if not workyear.default_entry_control:
            self.raise_user_error('no_entry_control')

        laboratory = self.start.planification.laboratory
        entry = LimsEntry(workyear.default_entry_control.id)

        # new sample
        new_sample, = LimsSample.create([{
            'entry': entry.id,
            'date': datetime.now(),
            'product_type': self.start.product_type.id,
            'matrix': self.start.matrix.id,
            'zone': entry.party.entry_zone.id,
            'label': self.start.label,
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
        new_fraction, = LimsFraction.create([fraction_default])

        # new services
        services_default = []
        for p_analysis in self.start.planification.analysis:
            if not LimsAnalysis.is_typified(p_analysis,
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
                    if (t.analysis.id == p_analysis.id
                            and t.by_default is True):
                        method_id = t.method.id
            device_id = None
            if p_analysis.devices:
                for d in p_analysis.devices:
                    if (d.laboratory.id == laboratory.id
                            and d.by_default is True):
                        device_id = d.device.id
            services_default.append({
                'fraction': new_fraction.id,
                'analysis': p_analysis.id,
                'laboratory': laboratory_id,
                'method': method_id,
                'device': device_id,
                })
        for service in services_default:
            new_service, = LimsService.create([service])

            # new analysis details (on service create)

        # confirm fraction: new notebook and stock move
        LimsFraction.confirm([new_fraction])

        # Edit notebook lines
        if fraction_type.control_charts:
            notebook_lines = LimsNotebookLine.search([
                ('notebook.fraction', '=', new_fraction.id),
                ])
            if notebook_lines:
                defaults = {
                    'concentration_level': self.start.concentration_level.id,
                    }
                LimsNotebookLine.write(notebook_lines, defaults)

        return new_fraction

    def add_control(self, fraction):
        LimsPlanification = Pool().get('lims.planification')
        LimsPlanification.write([self.start.planification], {
            'controls': [('add', [fraction.id])],
            })

    def add_planification_detail(self, fraction):
        pool = Pool()
        LimsAnalysis = pool.get('lims.analysis')
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsPlanificationDetail = pool.get('lims.planification.detail')

        p_analysis_ids = []
        for p_analysis in self.start.planification.analysis:
            if p_analysis.type == 'analysis':
                p_analysis_ids.append(p_analysis.id)
            else:
                p_analysis_ids.extend(
                    LimsAnalysis.get_included_analysis_analysis(p_analysis.id))
        clause = [
            ('notebook.fraction', '=', fraction.id),
            ('analysis', 'in', p_analysis_ids),
            ('analysis.behavior', '!=', 'internal_relation'),
            ]
        if self.start.type == 'exist':
#           clause.append(('result', '=', None))
            clause.extend([
                ('result', 'in', (None, '')),
                ('end_date', '=', None),
                ('annulment_date', '=', None),
                ])
        else:
            clause.append(('planification', '=', None))
        notebook_lines = LimsNotebookLine.search(clause)
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
                for k, v in details_to_create.iteritems():
                    details = LimsPlanificationDetail.search([
                        ('planification', '=', self.start.planification.id),
                        ('fraction', '=', k[0]),
                        ('service_analysis', '=', k[1]),
                        ])
                    if details:
                        LimsPlanificationDetail.write([details[0]], {
                            'details': [('create', v)],
                            })
                    else:
                        LimsPlanificationDetail.create([{
                            'planification': self.start.planification.id,
                            'fraction': k[0],
                            'service_analysis': k[1],
                            'details': [('create', v)],
                            }])


class LimsAddFractionMRTStart(ModelView):
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
        LimsAnalysis = pool.get('lims.analysis')
        LimsFraction = pool.get('lims.fraction')
        LimsNotebookLine = pool.get('lims.notebook.line')

        if self.type != 'exist':
            return []

        p_analysis_ids = []
        for p_analysis in self.planification.analysis:
            if p_analysis.type == 'analysis':
                p_analysis_ids.append(p_analysis.id)
            else:
                p_analysis_ids.extend(
                    LimsAnalysis.get_included_analysis_analysis(p_analysis.id))

        stored_fractions_ids = LimsFraction.get_stored_fractions()

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
        notebook_lines = LimsNotebookLine.search(clause)

        fractions = [nl.notebook.fraction.id for nl in notebook_lines]
        return list(set(fractions))

    @staticmethod
    def default_product_type_domain():
        cursor = Transaction().connection.cursor()
        LimsTypification = Pool().get('lims.typification')

        cursor.execute('SELECT DISTINCT(product_type) '
                'FROM "' + LimsTypification._table + '" '
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
        LimsTypification = Pool().get('lims.typification')

        if not self.product_type:
            return []

        cursor.execute('SELECT DISTINCT(matrix) '
                'FROM "' + LimsTypification._table + '" '
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


class LimsAddFractionMRT(Wizard):
    'Add Fraction MRT'
    __name__ = 'lims.planification.add_fraction_mrt'

    start = StateView('lims.planification.add_fraction_mrt.start',
        'lims_planification.lims_add_fraction_mrt_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Add', 'add', 'tryton-ok', default=True),
            ])
    add = StateTransition()

    @classmethod
    def __setup__(cls):
        super(LimsAddFractionMRT, cls).__setup__()
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
        LimsLabWorkYear = pool.get('lims.lab.workyear')
        LimsEntry = pool.get('lims.entry')
        LimsSample = pool.get('lims.sample')
        LimsFraction = pool.get('lims.fraction')
        LimsService = pool.get('lims.service')
        LimsAnalysis = pool.get('lims.analysis')
        LimsNotebookLine = pool.get('lims.notebook.line')

        config = Config(1)
        if not config.mrt_fraction_type:
            self.raise_user_error('no_mrt_fraction_type')
        fraction_type = config.mrt_fraction_type
        if (not fraction_type.default_package_type or
                not fraction_type.default_fraction_state):
            self.raise_user_error('no_mrt_default_configuration')

        if (fraction_type.control_charts
                and not self.start.concentration_level):
            self.raise_user_error('no_concentration_level')

        workyear_id = LimsLabWorkYear.find()
        workyear = LimsLabWorkYear(workyear_id)
        if not workyear.default_entry_control:
            self.raise_user_error('no_entry_control')

        laboratory = self.start.planification.laboratory
        entry = LimsEntry(workyear.default_entry_control.id)

        # new sample
        new_sample, = LimsSample.create([{
            'entry': entry.id,
            'date': datetime.now(),
            'product_type': self.start.product_type.id,
            'matrix': self.start.matrix.id,
            'zone': entry.party.entry_zone.id,
            'label': self.start.label,
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
        new_fraction, = LimsFraction.create([fraction_default])

        # new services
        services_default = []
        for p_analysis in self.start.planification.analysis:
            if not LimsAnalysis.is_typified(p_analysis,
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
                    if (t.analysis.id == p_analysis.id
                            and t.by_default is True):
                        method_id = t.method.id
            device_id = None
            if p_analysis.devices:
                for d in p_analysis.devices:
                    if (d.laboratory.id == laboratory.id
                            and d.by_default is True):
                        device_id = d.device.id
            services_default.append({
                'fraction': new_fraction.id,
                'analysis': p_analysis.id,
                'laboratory': laboratory_id,
                'method': method_id,
                'device': device_id,
                })
        for service in services_default:
            new_service, = LimsService.create([service])

            # new analysis details (on service create)

        # confirm fraction: new notebook and stock move
        LimsFraction.confirm([new_fraction])

        # Edit notebook lines
        if fraction_type.control_charts:
            notebook_lines = LimsNotebookLine.search([
                ('notebook.fraction', '=', new_fraction.id),
                ])
            if notebook_lines:
                defaults = {
                    'concentration_level': self.start.concentration_level.id,
                    }
                LimsNotebookLine.write(notebook_lines, defaults)

        # Generate repetition
        if self.start.repetitions and self.start.repetitions > 0:
            notebook_lines = LimsNotebookLine.search([
                ('notebook.fraction', '=', new_fraction.id),
                ])
            if notebook_lines:
                self.generate_repetition(notebook_lines,
                    self.start.repetitions)

        return new_fraction

    def generate_repetition(self, notebook_lines, repetitions):
        pool = Pool()
        LimsAnalysis = pool.get('lims.analysis')
        LimsNotebook = pool.get('lims.notebook')

        p_analysis_ids = []
        for p_analysis in self.start.planification.analysis:
            if p_analysis.type == 'analysis':
                p_analysis_ids.append(p_analysis.id)
            else:
                p_analysis_ids.extend(
                    LimsAnalysis.get_included_analysis_analysis(p_analysis.id))

        analysis_to_repeat = {}
        for notebook_line in notebook_lines:
            if notebook_line.analysis.id not in p_analysis_ids:
                continue
            if notebook_line.analysis.id not in analysis_to_repeat:
                analysis_to_repeat[notebook_line.analysis.id] = notebook_line
            elif (notebook_line.repetition >
                    analysis_to_repeat[notebook_line.analysis.id].repetition):
                analysis_to_repeat[notebook_line.analysis.id] = notebook_line

        notebook = LimsNotebook(notebook_lines[0].notebook.id)

        to_create = []
        for nline in analysis_to_repeat.itervalues():
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
                    })
        LimsNotebook.write([notebook], {
            'lines': [('create', to_create)],
            })

    def add_control(self, fraction):
        LimsPlanification = Pool().get('lims.planification')
        LimsPlanification.write([self.start.planification], {
            'controls': [('add', [fraction.id])],
            })

    def add_planification_detail(self, fraction):
        pool = Pool()
        LimsAnalysis = pool.get('lims.analysis')
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsPlanificationDetail = pool.get('lims.planification.detail')

        p_analysis_ids = []
        for p_analysis in self.start.planification.analysis:
            if p_analysis.type == 'analysis':
                p_analysis_ids.append(p_analysis.id)
            else:
                p_analysis_ids.extend(
                    LimsAnalysis.get_included_analysis_analysis(p_analysis.id))
        clause = [
            ('notebook.fraction', '=', fraction.id),
            ('analysis', 'in', p_analysis_ids),
            ('analysis.behavior', '!=', 'internal_relation'),
            ]
        if self.start.type == 'exist':
 #          clause.append(('result', '=', None))
            clause.extend([
                ('result', 'in', (None, '')),
                ('end_date', '=', None),
                ('annulment_date', '=', None),
                ])
        else:
            clause.append(('planification', '=', None))
        notebook_lines = LimsNotebookLine.search(clause)
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
                for k, v in details_to_create.iteritems():
                    details = LimsPlanificationDetail.search([
                        ('planification', '=', self.start.planification.id),
                        ('fraction', '=', k[0]),
                        ('service_analysis', '=', k[1]),
                        ])
                    if details:
                        LimsPlanificationDetail.write([details[0]], {
                            'details': [('create', v)],
                            })
                    else:
                        LimsPlanificationDetail.create([{
                            'planification': self.start.planification.id,
                            'fraction': k[0],
                            'service_analysis': k[1],
                            'details': [('create', v)],
                            }])


class LimsRemoveControlStart(ModelView):
    'Remove Control'
    __name__ = 'lims.planification.remove_control.start'

    controls = fields.Many2Many('lims.fraction', None, None, 'Controls',
        required=True, domain=[('id', 'in', Eval('controls_domain'))],
        depends=['controls_domain'])
    controls_domain = fields.Many2Many('lims.fraction', None, None,
        'Controls domain')


class LimsRemoveControl(Wizard):
    'Remove Control'
    __name__ = 'lims.planification.remove_control'

    start = StateView('lims.planification.remove_control.start',
        'lims_planification.lims_remove_control_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Remove', 'remove', 'tryton-ok', default=True),
            ])
    remove = StateTransition()

    def default_start(self, fields):
        LimsPlanification = Pool().get('lims.planification')
        planification = LimsPlanification(Transaction().context['active_id'])
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
        LimsPlanificationFraction = pool.get('lims.planification-fraction')
        LimsPlanificationDetail = pool.get('lims.planification.detail')

        controls = LimsPlanificationFraction.search([
            ('planification', '=', planification_id),
            ('fraction', 'in', control_ids),
            ])
        if controls:
            LimsPlanificationFraction.delete(controls)

        controls_details = LimsPlanificationDetail.search([
            ('planification', '=', planification_id),
            ('fraction', 'in', control_ids),
            ])
        if controls_details:
            LimsPlanificationDetail.delete(controls_details)


class LimsAddAnalysisStart(ModelView):
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


class LimsAddAnalysis(Wizard):
    'Add Analysis'
    __name__ = 'lims.planification.add_analysis'

    start = StateView('lims.planification.add_analysis.start',
        'lims_planification.lims_add_analysis_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Add', 'add', 'tryton-ok', default=True),
            ])
    add = StateTransition()

    def default_start(self, fields):
        LimsPlanification = Pool().get('lims.planification')
        planification = LimsPlanification(Transaction().context['active_id'])
        analysis_domain = LimsAddAnalysis._get_analysis_domain(
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
        LimsPlanification = pool.get('lims.planification')
        LimsAnalysis = pool.get('lims.analysis')

        if not laboratory:
            return []

        asg_list = LimsPlanification._get_analysis_domain(laboratory)

        new_context = {}
        new_context['date_from'] = date_from
        new_context['date_to'] = date_to
        with Transaction().set_context(new_context):
            analysis_domain = LimsAnalysis.search([
                ('id', 'in', asg_list),
                ('pending_fractions', '>', 0),
                ])
            if analysis_domain:
                return [a.id for a in analysis_domain]
            return []

    def transition_add(self):
        LimsPlanification = Pool().get('lims.planification')

        planification = LimsPlanification(Transaction().context['active_id'])

        LimsPlanification.write([planification], {
            'analysis': [('remove', self.start.analysis)],
            })
        LimsPlanification.write([planification], {
            'analysis': [('add', self.start.analysis)],
            })
        return 'end'


class LimsSearchFractionsNext(ModelView):
    'Search Fractions'
    __name__ = 'lims.planification.search_fractions.next'

    details = fields.Many2Many(
        'lims.planification.search_fractions.detail',
        None, None, 'Fractions to plan', depends=['details_domain'],
        domain=[('id', 'in', Eval('details_domain'))], required=True)
    details_domain = fields.One2Many(
        'lims.planification.search_fractions.detail',
        None, 'Fractions domain')


class LimsSearchFractionsDetail(ModelSQL, ModelView):
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
        super(LimsSearchFractionsDetail,
            cls).__register__(module_name)
        cursor = Transaction().connection.cursor()
        cursor.execute('DELETE FROM "' + cls._table + '"')

    @classmethod
    def __setup__(cls):
        super(LimsSearchFractionsDetail, cls).__setup__()
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


class LimsSearchFractions(Wizard):
    'Search Fractions'
    __name__ = 'lims.planification.search_fractions'

    start_state = 'search'
    search = StateTransition()
    next = StateView('lims.planification.search_fractions.next',
        'lims_planification.lims_search_fractions_next_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Add', 'add', 'tryton-ok', default=True),
            ])
    add = StateTransition()

    def transition_search(self):
        pool = Pool()
        LimsPlanification = pool.get('lims.planification')
        LimsPlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')
        LimsPlanificationDetail = pool.get('lims.planification.detail')
        LimsSearchFractionsDetail = pool.get(
            'lims.planification.search_fractions.detail')

        planification = LimsPlanification(Transaction().context['active_id'])

        service_detail = LimsPlanificationServiceDetail.search([
            ('planification', '=', planification.id),
            ('is_control', '=', False),
            ('is_replanned', '=', False),
            ])
        if service_detail:
            LimsPlanificationServiceDetail.delete(service_detail)

        details = LimsPlanificationDetail.search([
            ('planification', '=', planification.id),
            ('details', '=', None),
            ])
        if details:
            LimsPlanificationDetail.delete(details)

        fractions_added = []
        if not planification.analysis:
            self.next.details = fractions_added
            return 'next'

        data = self._get_service_details(planification)

        to_create = []
        for k, v in data.iteritems():
            to_create.append({
                'session_id': self._session_id,
                'fraction': k[0],
                'service_analysis': k[1],
                'product_type': v['product_type'],
                'matrix': v['matrix'],
                })
        fractions_added = LimsSearchFractionsDetail.create(to_create)

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
        LimsPlanification = pool.get('lims.planification')
        LimsPlanificationDetail = pool.get('lims.planification.detail')

        planification = LimsPlanification(Transaction().context['active_id'])

        records_added = ['(%s,%s)' % (d.fraction.id, d.service_analysis.id)
            for d in self.next.details]
        records_ids_added = ', '.join(str(x)
            for x in ['(0,0)'] + records_added)
        extra_where = (
            'AND (nb.fraction, srv.analysis) IN (' + records_ids_added + ') ')

        data = self._get_service_details(planification, extra_where)

        to_create = []
        for k, v in data.iteritems():
            details = LimsPlanificationDetail.search([
                ('planification', '=', planification.id),
                ('fraction', '=', k[0]),
                ('service_analysis', '=', k[1]),
                ])
            if details:
                LimsPlanificationDetail.write([details[0]], {
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
            LimsPlanificationDetail.create(to_create)

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
            service_where = ('AND ad.analysis IN ('
                + all_included_analysis_ids + ') ')

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
                    'ON srv.id = nl.service '
                    + sample_from)

            sql_where = (
                'WHERE nl.planification IS NULL '
                    'AND ft.plannable = TRUE '
                    'AND nl.id NOT IN (' + planned_lines_ids + ') '
                    'AND nl.laboratory = %s '
                    'AND nla.behavior != \'internal_relation\' '
                    'AND ad.confirmation_date::date >= %s::date '
                    'AND ad.confirmation_date::date <= %s::date '
                    + service_where + extra_where)

            sql_order = (
                'ORDER BY nb.fraction ASC, srv.analysis ASC')

            with Transaction().set_user(0):
                cursor.execute(sql_select + sql_from + sql_where + sql_order,
                    (planification.laboratory.id, planification.date_from,
                    planification.date_to,))
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
                                })
                else:
                    for nl in notebook_lines:
                        f_ = nl[1]
                        s_ = nl[2]
                        if (f_, s_) not in result:
                            result[(f_, s_)] = {
                                'product_type': nl[3],
                                'matrix': nl[4],
                                }

        return result


class LimsSearchPlannedFractionsStart(ModelView):
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


class LimsSearchPlannedFractionsNext(ModelView):
    'Search Planned Fractions'
    __name__ = 'lims.planification.search_planned_fractions.next'

    details = fields.Many2Many(
        'lims.planification.search_planned_fractions.detail',
        None, None, 'Fractions to replan', depends=['details_domain'],
        domain=[('id', 'in', Eval('details_domain'))], required=True)
    details_domain = fields.One2Many(
        'lims.planification.search_planned_fractions.detail',
        None, 'Fractions domain')


class LimsSearchPlannedFractionsDetail(ModelSQL, ModelView):
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
        super(LimsSearchPlannedFractionsDetail,
            cls).__register__(module_name)
        cursor = Transaction().connection.cursor()
        cursor.execute('DELETE FROM "' + cls._table + '"')

    @classmethod
    def __setup__(cls):
        super(LimsSearchPlannedFractionsDetail, cls).__setup__()
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


class LimsSearchPlannedFractions(Wizard):
    'Search Planned Fractions'
    __name__ = 'lims.planification.search_planned_fractions'

    start = StateView('lims.planification.search_planned_fractions.start',
        'lims_planification.lims_search_planned_fractions_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search', 'search', 'tryton-go-next', default=True),
            ])
    search = StateTransition()
    next = StateView('lims.planification.search_planned_fractions.next',
        'lims_planification.lims_search_planned_fractions_next_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Add', 'add', 'tryton-ok', default=True),
            ])
    add = StateTransition()

    def default_start(self, fields):
        LimsPlanification = Pool().get('lims.planification')
        planification = LimsPlanification(Transaction().context['active_id'])
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
        LimsSearchPlannedFractionsDetail = pool.get(
            'lims.planification.search_planned_fractions.detail')

        data = self._get_service_details()

        to_create = []
        for k, v in data.iteritems():
            to_create.append({
                'session_id': self._session_id,
                'fraction': k[0],
                'service_analysis': k[1],
                'product_type': v['product_type'],
                'matrix': v['matrix'],
                })
        fractions_added = LimsSearchPlannedFractionsDetail.create(to_create)

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
        LimsPlanification = pool.get('lims.planification')
        LimsPlanificationDetail = pool.get('lims.planification.detail')

        planification = LimsPlanification(Transaction().context['active_id'])

        records_added = ['(%s,%s)' % (d.fraction.id, d.service_analysis.id)
            for d in self.next.details]
        records_ids_added = ', '.join(str(x)
            for x in ['(0,0)'] + records_added)
        extra_where = (
            'AND (nb.fraction, srv.analysis) IN (' + records_ids_added + ') ')

        data = self._get_service_details(extra_where)

        to_create = []
        for k, v in data.iteritems():
            details = LimsPlanificationDetail.search([
                ('planification', '=', planification.id),
                ('fraction', '=', k[0]),
                ('service_analysis', '=', k[1]),
                ])
            if details:
                LimsPlanificationDetail.write([details[0]], {
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
            LimsPlanificationDetail.create(to_create)

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
            service_where = ('AND ad.analysis IN ('
                + all_included_analysis_ids + ') ')
            service_clause = [
                ('analysis_detail.analysis', 'in', all_included_analysis),
                ]

            excluded_fractions = self.get_control_fractions_excluded(
                self.start.laboratory.id, service_clause)
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
                    'ON srv.id = nl.service '
                    + sample_from)

            sql_where = (
                'WHERE nl.planification IS NOT NULL '
                    'AND ft.plannable = TRUE '
                    'AND nl.end_date IS NULL '
                    'AND nl.laboratory = %s '
                    'AND nla.behavior != \'internal_relation\' '
                    'AND nb.fraction NOT IN (' + excluded_fractions_ids + ') '
                    'AND ad.confirmation_date::date >= %s::date '
                    'AND ad.confirmation_date::date <= %s::date '
                    + service_where + extra_where)

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
                        if (f_, s_) not in result:
                            result[(f_, s_)] = {
                                'product_type': nl[3],
                                'matrix': nl[4],
                                }

        return result

    def get_control_fractions_excluded(self, laboratory, search_clause):
        pool = Pool()
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsNotebook = pool.get('lims.notebook')

        excluded_fractions = []

        notebook_lines = LimsNotebookLine.search([
            ('planification', '!=', None),
            ('end_date', '=', None),
            ('laboratory', '=', laboratory),
            ('notebook.fraction.special_type', 'in',
                ('rm', 'bmz', 'bre', 'mrt')),
            search_clause])
        if notebook_lines:
            analysis = []
            notebooks_id = []
            for nbl in notebook_lines:
                analysis.append(nbl.analysis.id)
                if nbl.notebook.id not in notebooks_id:
                    notebooks_id.append(nbl.notebook.id)
            analysis = list(set(analysis))
            notebooks = LimsNotebook.search([
                ('id', 'in', notebooks_id),
                ])
            if notebooks:
                for nb in notebooks:
                    nbl_analysis_ids = [l.analysis.id for l in nb.lines or []]
                    for p_analysis_id in analysis:
                        if p_analysis_id not in nbl_analysis_ids:
                            excluded_fractions.append(nb.fraction.id)
                            break
        return list(set(excluded_fractions))


class LimsCreateFractionControlStart(ModelView):
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
        LimsAnalysisLaboratory = pool.get('lims.analysis-laboratory')
        LimsAnalysis = pool.get('lims.analysis')
        LimsTypification = pool.get('lims.typification')
        LimsCalculatedTypification = pool.get('lims.typification.calculated')

        if not self.laboratory or not self.product_type or not self.matrix:
            return []

        cursor.execute('SELECT DISTINCT(analysis) '
            'FROM "' + LimsAnalysisLaboratory._table + '" '
            'WHERE laboratory = %s', (self.laboratory.id,))
        analysis_sets_list = [a[0] for a in cursor.fetchall()]
        if not analysis_sets_list:
            return []
        lab_analysis_ids = ', '.join(str(a) for a in
                analysis_sets_list)

        groups_list = []
        groups = LimsAnalysis.search([
            ('type', '=', 'group'),
            ])
        if groups:
            for group in groups:
                available = True

                ia = LimsAnalysis.get_included_analysis_analysis(
                    group.id)
                if not ia:
                    continue
                included_ids = ', '.join(str(a) for a in ia)

                cursor.execute('SELECT id '
                    'FROM "' + LimsAnalysis._table + '" '
                    'WHERE id IN (' + included_ids + ') '
                        'AND id NOT IN (' + lab_analysis_ids
                        + ')')
                if cursor.fetchone():
                    available = False

                if available:
                    groups_list.append(group.id)

        analysis_domain = analysis_sets_list + groups_list
        analysis_domain_ids = ', '.join(str(a) for a in analysis_domain)

        cursor.execute('SELECT DISTINCT(typ.analysis) '
            'FROM ('
                'SELECT t.analysis FROM "' + LimsTypification._table + '" t '
                'WHERE t.product_type = %s AND t.matrix = %s AND t.valid '
            'UNION '
                'SELECT ct.analysis FROM "' + LimsCalculatedTypification._table
                + '" ct '
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
        LimsTypification = Pool().get('lims.typification')

        cursor.execute('SELECT DISTINCT(product_type) '
                'FROM "' + LimsTypification._table + '" '
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
        LimsTypification = Pool().get('lims.typification')

        if not self.product_type:
            return []

        cursor.execute('SELECT DISTINCT(matrix) '
                'FROM "' + LimsTypification._table + '" '
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


class LimsCreateFractionControl(Wizard):
    'Create Fraction Control'
    __name__ = 'lims.planification.create_fraction_con'

    start = StateView('lims.planification.create_fraction_con.start',
        'lims_planification.lims_create_fraction_con_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Create', 'create_', 'tryton-ok', default=True),
            ])
    create_ = StateTransition()
    open_ = StateAction('lims.act_lims_sample_list')

    @classmethod
    def __setup__(cls):
        super(LimsCreateFractionControl, cls).__setup__()
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
        LimsLabWorkYear = pool.get('lims.lab.workyear')
        LimsEntry = pool.get('lims.entry')
        LimsSample = pool.get('lims.sample')
        LimsFraction = pool.get('lims.fraction')
        LimsService = pool.get('lims.service')
        LimsNotebookLine = pool.get('lims.notebook.line')

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

        if (fraction_type.control_charts
                and not self.start.concentration_level):
            self.raise_user_error('no_concentration_level')

        workyear_id = LimsLabWorkYear.find()
        workyear = LimsLabWorkYear(workyear_id)
        if not workyear.default_entry_control:
            self.raise_user_error('no_entry_control')

        laboratory = self.start.laboratory
        entry = LimsEntry(workyear.default_entry_control.id)

        # new sample
        new_sample, = LimsSample.create([{
            'entry': entry.id,
            'date': datetime.now(),
            'product_type': self.start.product_type.id,
            'matrix': self.start.matrix.id,
            'zone': entry.party.entry_zone.id,
            'label': self.start.label,
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
        new_fraction, = LimsFraction.create([fraction_default])

        # new services
        services_default = []
        for p_analysis in self.start.analysis:
            laboratory_id = (laboratory.id if p_analysis.type != 'group'
                else None)
            method_id = None
            if new_sample.typification_domain:
                for t in new_sample.typification_domain:
                    if (t.analysis.id == p_analysis.id
                            and t.by_default is True):
                        method_id = t.method.id
            device_id = None
            if p_analysis.devices:
                for d in p_analysis.devices:
                    if (d.laboratory.id == laboratory.id
                            and d.by_default is True):
                        device_id = d.device.id
            services_default.append({
                'fraction': new_fraction.id,
                'analysis': p_analysis.id,
                'laboratory': laboratory_id,
                'method': method_id,
                'device': device_id,
                })
        for service in services_default:
            new_service, = LimsService.create([service])

            # new analysis details (on service create)

        # confirm fraction: new notebook and stock move
        LimsFraction.confirm([new_fraction])

        # Edit notebook lines
        if fraction_type.control_charts:
            notebook_lines = LimsNotebookLine.search([
                ('notebook.fraction', '=', new_fraction.id),
                ])
            if notebook_lines:
                defaults = {
                    'concentration_level': self.start.concentration_level.id,
                    }
                LimsNotebookLine.write(notebook_lines, defaults)

        return new_fraction

    def do_open_(self, action):
        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', '=', self.start.sample_created.id),
            ])
        return action, {}


class LimsReleaseFractionStart(ModelView):
    'Release Fraction'
    __name__ = 'lims.planification.release_fraction.start'

    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        required=True)
    date_from = fields.Date('Date from', required=True)
    date_to = fields.Date('Date to', required=True)


class LimsReleaseFractionEmpty(ModelView):
    'Release Fraction'
    __name__ = 'lims.planification.release_fraction.empty'


class LimsReleaseFractionResult(ModelView):
    'Release Fraction'
    __name__ = 'lims.planification.release_fraction.result'

    fractions = fields.Many2Many('lims.planification.detail', None, None,
        'Fractions', required=True,
        domain=[('id', 'in', Eval('fractions_domain'))],
        depends=['fractions_domain'])
    fractions_domain = fields.One2Many('lims.planification.detail', None,
        'Fractions domain')


class LimsReleaseFraction(Wizard):
    'Release Fraction'
    __name__ = 'lims.planification.release_fraction'

    start = StateView('lims.planification.release_fraction.start',
        'lims_planification.lims_planification_release_fraction_start'
        '_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search', 'search', 'tryton-go-next', default=True),
            ])
    search = StateTransition()
    empty = StateView('lims.planification.release_fraction.empty',
        'lims_planification.lims_planification_release_fraction_empty'
        '_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search again', 'start', 'tryton-go-next', default=True),
            ])
    result = StateView('lims.planification.release_fraction.result',
        'lims_planification.lims_planification_release_fraction_result'
        '_view_form', [
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
        LimsPlanificationDetail = Pool().get('lims.planification.detail')

        details = LimsPlanificationDetail.search([
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
        LimsNotebookLine = Pool().get('lims.notebook.line')
        for detail in self.result.fractions:
            for service_detail in detail.details:
                if (not service_detail.is_control
                        and service_detail.notebook_line):
                    notebook_line = LimsNotebookLine(
                        service_detail.notebook_line.id)
                    notebook_line.start_date = None
                    notebook_line.laboratory_professionals = []
                    notebook_line.planification = None
                    notebook_line.controls = []
                    notebook_line.save()

    def _re_update_analysis_detail(self):
        LimsEntryDetailAnalysis = Pool().get('lims.entry.detail.analysis')
        analysis_detail_ids = []
        for detail in self.result.fractions:
            for service_detail in detail.details:
                if (not service_detail.is_control
                        and service_detail.notebook_line
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

    def _unlink_fractions(self):
        pool = Pool()
        LimsPlanificationServiceDetail = Pool().get(
            'lims.planification.service_detail')
        LimsPlanificationDetail = pool.get('lims.planification.detail')

        details_ids = []
        service_details_ids = []
        for detail in self.result.fractions:
            for service_detail in detail.details:
                if not service_detail.is_control:
                    service_details_ids.append(service_detail.id)
                    details_ids.append(service_detail.detail.id)

        service_detail = LimsPlanificationServiceDetail.search([
            ('id', 'in', service_details_ids),
            ])
        if service_detail:
            LimsPlanificationServiceDetail.delete(service_detail)

        details = LimsPlanificationDetail.search([
            ('id', 'in', details_ids),
            ('details', '=', None),
            ])
        if details:
            LimsPlanificationDetail.delete(details)


class LimsQualificationSituations(ModelView):
    'Technicians Qualification'
    __name__ = 'lims.planification.qualification.situations'

    situations = fields.Many2Many('lims.planification.qualification.situation',
        None, None, 'Situations')
    total = fields.Integer('Total')
    index = fields.Integer('Index')


class LimsQualificationSituation(ModelSQL, ModelView):
    'Qualification Situation'
    __name__ = 'lims.planification.qualification.situation'

    method = fields.Many2One('lims.lab.method', 'Method', readonly=True)
    professional = fields.Many2One('lims.laboratory.professional',
        'Professional', readonly=True)
    situation = fields.Integer('Situation', readonly=True)
    session_id = fields.Integer('Session ID')

    @classmethod
    def __register__(cls, module_name):
        super(LimsQualificationSituation,
            cls).__register__(module_name)
        cursor = Transaction().connection.cursor()
        cursor.execute('DELETE FROM "' + cls._table + '"')


class LimsQualificationAction(ModelSQL):
    'Qualification Action'
    __name__ = 'lims.planification.qualification.action'

    method = fields.Many2One('lims.lab.method', 'Method')
    professional = fields.Many2One('lims.laboratory.professional',
        'Professional')
    action = fields.Integer('Action')
    session_id = fields.Integer('Session ID')

    @classmethod
    def __register__(cls, module_name):
        super(LimsQualificationAction,
            cls).__register__(module_name)
        cursor = Transaction().connection.cursor()
        cursor.execute('DELETE FROM "' + cls._table + '"')


class LimsQualificationSituation2(ModelView):
    'Technicians Qualification'
    __name__ = 'lims.planification.qualification.situation.2'

    method = fields.Many2One('lims.lab.method', 'Method', readonly=True)
    professional = fields.Many2One('lims.laboratory.professional',
        'Professional', readonly=True)


class LimsQualificationSituation3(ModelView):
    'Technicians Qualification'
    __name__ = 'lims.planification.qualification.situation.3'

    method = fields.Many2One('lims.lab.method', 'Method', readonly=True)
    professional = fields.Many2One('lims.laboratory.professional',
        'Professional', readonly=True)


class LimsQualificationSituation4(ModelView):
    'Technicians Qualification'
    __name__ = 'lims.planification.qualification.situation.4'

    methods = fields.Text('Methods', readonly=True)


class LimsTechniciansQualification(Wizard):
    'Technicians Qualification'
    __name__ = 'lims.planification.technicians_qualification'

    situations = StateView('lims.planification.qualification.situations',
        'lims_planification.lims_qualification_situations_view_form', [])
    start = StateTransition()
    next_ = StateTransition()
    confirm = StateTransition()

    sit2 = StateView('lims.planification.qualification.situation.2',
        'lims_planification.lims_qualification_situation_2_view_form', [
            Button('Qualify', 'sit2_op1', 'tryton-ok', default=True),
            Button('New Training', 'sit2_op2', 'tryton-ok'),
            Button('Cancel', 'end', 'tryton-cancel'),
            ])
    sit2_op1 = StateTransition()
    sit2_op2 = StateTransition()

    sit3 = StateView('lims.planification.qualification.situation.3',
        'lims_planification.lims_qualification_situation_3_view_form', [
            Button('Requalify', 'sit3_op1', 'tryton-ok', default=True),
            Button('Cancel', 'end', 'tryton-cancel'),
            ])
    sit3_op1 = StateTransition()

    sit4 = StateView('lims.planification.qualification.situation.4',
        'lims_planification.lims_qualification_situation_4_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            ])

    def transition_start(self):
        pool = Pool()
        LimsPlanification = pool.get('lims.planification')
        LimsPlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')
        LimsLabProfessionalMethod = pool.get('lims.lab.professional.method')
        LimsQualificationSituation = pool.get(
            'lims.planification.qualification.situation')

        planification = LimsPlanification(Transaction().context['active_id'])

        planification_details = LimsPlanificationServiceDetail.search([
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
                    qualifications = LimsLabProfessionalMethod.search([
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
            self.situations.situations = LimsQualificationSituation.create([{
                'session_id': self._session_id,
                'professional': k[0],
                'method': k[1],
                'situation': v,
                } for k, v in situations.iteritems()])
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
        LimsQualificationAction = Pool().get(
            'lims.planification.qualification.action')

        LimsQualificationAction.create([{
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
        LimsQualificationAction = Pool().get(
            'lims.planification.qualification.action')

        LimsQualificationAction.create([{
            'session_id': self._session_id,
            'professional': self.sit2.professional.id,
            'method': self.sit2.method.id,
            'action': 2,
            }])
        return self._continue()

    def transition_sit2_op2(self):
        # Write a new training.
        LimsQualificationAction = Pool().get(
            'lims.planification.qualification.action')

        LimsQualificationAction.create([{
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
        LimsLabProfessionalMethod = pool.get('lims.lab.professional.method')
        Date = pool.get('ir.date')
        LimsQualificationAction = pool.get(
            'lims.planification.qualification.action')

        deadline = Date.today() - relativedelta(
            months=data.method.requalification_months)
        professional_method, = LimsLabProfessionalMethod.search([
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
            LimsQualificationAction.create([{
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
        LimsQualificationAction = Pool().get(
            'lims.planification.qualification.action')

        LimsQualificationAction.create([{
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
        LimsPlanification = pool.get('lims.planification')
        LimsPlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')
        LimsLabProfessionalMethod = pool.get('lims.lab.professional.method')
        LimsQualificationAction = pool.get(
            'lims.planification.qualification.action')

        planification = LimsPlanification(Transaction().context['active_id'])

        planification_details = LimsPlanificationServiceDetail.search([
            ('planification', '=', planification.id),
            ])
        methods = []
        for detail in planification_details:
            method = (detail.notebook_line.method if detail.notebook_line
                else None)
            if method:
                qualified = False
                for technician in detail.staff_responsible:
                    qualifications = LimsLabProfessionalMethod.search([
                        ('professional', '=', technician.id),
                        ('method', '=', method.id),
                        ('type', '=', 'preparation'),
                        ])
                    if (qualifications and qualifications[0].state in
                            ('qualified', 'requalified')):
                        if not method.supervised_requalification:
                            qualified = True
                            break
                        actions = LimsQualificationAction.search([
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

        actions = LimsQualificationAction.search([
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
        LimsLabProfessionalMethod = pool.get('lims.lab.professional.method')
        Date = pool.get('ir.date')

        supervisors = self._get_supervisors(data)
        requalification_history = [{
            'type': 'training',
            'date': Date.today(),
            'last_execution_date': start_date,
            'supervisors': [('create', supervisors)],
            'controls': [('create', controls)],
            }]
        professional_method, = LimsLabProfessionalMethod.create([{
            'professional': data.professional.id,
            'method': data.method.id,
            'state': 'training',
            'type': 'preparation',
            'requalification_history': [('create', requalification_history)],
            }])

    def action_2(self, data, controls, start_date):
        # Qualify the technician
        pool = Pool()
        LimsLabProfessionalMethod = pool.get('lims.lab.professional.method')
        Date = pool.get('ir.date')

        professional_method, = LimsLabProfessionalMethod.search([
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
        LimsLabProfessionalMethod.write([professional_method], {
            'state': 'qualified',
            'requalification_history': [('create', requalification_history)],
            })

    def action_3(self, data, controls, start_date):
        # Write a new training
        pool = Pool()
        LimsLabProfessionalMethod = pool.get('lims.lab.professional.method')
        Date = pool.get('ir.date')

        professional_method, = LimsLabProfessionalMethod.search([
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
        LimsLabProfessionalMethod.write([professional_method], {
            'requalification_history': [('create', requalification_history)],
            })

    def action_4(self, data, controls, start_date):
        # Requalify the technician
        pool = Pool()
        LimsLabProfessionalMethod = pool.get('lims.lab.professional.method')
        Date = pool.get('ir.date')

        professional_method, = LimsLabProfessionalMethod.search([
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
        LimsLabProfessionalMethod.write([professional_method], {
            'state': 'requalified',
            'requalification_history': [('create', requalification_history)],
            })

    def action_5(self, data, controls, start_date):
        # Write a new execution
        pool = Pool()
        LimsLabProfessionalMethod = pool.get('lims.lab.professional.method')
        Date = pool.get('ir.date')

        professional_method, = LimsLabProfessionalMethod.search([
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
        LimsLabProfessionalMethod.write([professional_method], {
            'requalification_history': [('create', requalification_history)],
            })

    def transition_confirm(self):
        pool = Pool()
        LimsPlanification = pool.get('lims.planification')
        Config = pool.get('lims.configuration')
        process_background = Config(1).planification_process_background

        planification = LimsPlanification(Transaction().context['active_id'])
        planification.state = 'confirmed'
        if process_background:
            planification.waiting_process = True
        planification.save()

        if not process_background:
            LimsPlanification.do_confirm([planification])
        return 'end'

    def _get_supervisors(self, data):
        pool = Pool()
        LimsPlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')
        LimsLabProfessionalMethod = pool.get('lims.lab.professional.method')
        LimsQualificationAction = pool.get(
            'lims.planification.qualification.action')

        planification_id = Transaction().context['active_id']
        supervisors = []

        planification_details = LimsPlanificationServiceDetail.search([
            ('planification', '=', planification_id),
            ('notebook_line.method', '=', data.method.id),
            ])
        for detail in planification_details:
            for technician in detail.staff_responsible:
                if technician.id == data.professional.id:
                    continue
                qualifications = LimsLabProfessionalMethod.search([
                    ('professional', '=', technician.id),
                    ('method', '=', data.method.id),
                    ('type', '=', 'preparation'),
                    ])
                if (qualifications and qualifications[0].state in
                        ('qualified', 'requalified')):
                    if not data.method.supervised_requalification:
                        supervisors.append(technician.id)
                    else:
                        actions = LimsQualificationAction.search([
                            ('session_id', '=', self._session_id),
                            ('professional', '=', technician.id),
                            ('method', '=', data.method.id),
                            ('action', '=', 4),
                            ])
                        if not actions:
                            supervisors.append(technician.id)

        return [{'supervisor': t_id} for t_id in list(set(supervisors))]

    def _get_controls(self):
        LimsPlanificationFraction = Pool().get('lims.planification-fraction')

        planification_id = Transaction().context['active_id']
        controls = []

        planification_controls = LimsPlanificationFraction.search([
            ('planification', '=', planification_id),
            ('fraction.type.requalify', '=', True),
            ])
        for p_control in planification_controls:
            controls.append(p_control.fraction.id)

        return [{'control': f_id} for f_id in list(set(controls))]


class LimsReplaceTechnicianStart(ModelView):
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
        LimsUserLaboratory = pool.get('lims.user-laboratory')
        LimsLaboratoryProfessional = pool.get('lims.laboratory.professional')
        LimsPlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')
        LimsLabProfessionalMethod = pool.get('lims.lab.professional.method')

        if not self.technician_replaced:
            return []

        substitute_domain = []
        users = LimsUserLaboratory.search([
            ('laboratory', '=', self.planification.laboratory.id),
            ])
        if users:
            professionals = LimsLaboratoryProfessional.search([
                ('party.lims_user', 'in', [u.user.id for u in users]),
                ])
            if professionals:
                substitute_domain = [p.id for p in professionals]

        service_details = LimsPlanificationServiceDetail.search([
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
                qualifications = LimsLabProfessionalMethod.search([
                    ('professional', '=', technician_id),
                    ('method', '=', method_id),
                    ('type', '=', 'preparation'),
                    ])
                if not (qualifications and qualifications[0].state in
                        ('qualified', 'requalified')):
                    substitute_domain.remove(technician_id)
                    break
        return substitute_domain


class LimsReplaceTechnician(Wizard):
    'Replace Technician'
    __name__ = 'lims.planification.replace_technician'

    start_state = 'check'
    check = StateTransition()
    start = StateView('lims.planification.replace_technician.start',
        'lims_planification.lims_replace_technician_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Replace', 'replace', 'tryton-ok', default=True),
            ])
    replace = StateTransition()

    def transition_check(self):
        pool = Pool()
        LimsPlanification = pool.get('lims.planification')
        NotebookLine = pool.get('lims.notebook.line')

        planification = LimsPlanification(Transaction().context['active_id'])
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
        LimsPlanification = Pool().get('lims.planification')

        planification = LimsPlanification(Transaction().context['active_id'])

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


class LimsManageServices:
    __name__ = 'lims.manage_services'
    __metaclass__ = PoolMeta

    def transition_ok(self):
        res = super(LimsManageServices, self).transition_ok()

        LimsFraction = Pool().get('lims.fraction')
        fraction = LimsFraction(Transaction().context['active_id'])

        original_services = [s for s in fraction.services if not s.planned]
        actual_services = self.start.services

        for original_service in original_services:
            for actual_service in actual_services:
                if original_service == actual_service:
                    update_cie_data = True
                    for field in ('analysis', 'laboratory', 'method',
                            'device'):
                        if (getattr(original_service, field) !=
                                getattr(actual_service, field)):
                            update_cie_data = False
                            break
                    if update_cie_data:
                        for detail in actual_service.analysis_detail:
                            detail.save()
        return res

    def create_service(self, service, fraction):
        pool = Pool()
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        new_service = super(LimsManageServices, self).create_service(service,
            fraction)

        analysis_detail = EntryDetailAnalysis.search([
            ('service', '=', new_service.id)])
        EntryDetailAnalysis.write(analysis_detail, {
            'state': 'unplanned',
            })
        if fraction.cie_fraction_type:
            self._create_blind_samples(analysis_detail, fraction)

        return new_service

    def update_service(self, original_service, actual_service, fraction,
            field_changed):
        pool = Pool()
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        super(LimsManageServices, self).update_service(original_service,
            actual_service, fraction, field_changed)

        update_details = True if field_changed in ('analysis', 'laboratory',
            'method', 'device') else False

        if update_details:
            analysis_detail = EntryDetailAnalysis.search([
                ('service', '=', original_service.id)])
            EntryDetailAnalysis.write(analysis_detail, {
                'state': 'unplanned',
                })
            if fraction.cie_fraction_type:
                self._create_blind_samples(analysis_detail, fraction)

    def _create_blind_samples(self, analysis_detail, fraction):
        pool = Pool()
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsBlindSample = pool.get('lims.blind_sample')
        Date = pool.get('ir.date')

        confirmation_date = Date.today()

        to_create = []
        for detail in analysis_detail:
            nlines = LimsNotebookLine.search([
                ('analysis_detail', '=', detail.id),
                ])
            for nline in nlines:
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
                original_fraction = fraction.cie_original_fraction
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
                        record['original_repetition'] = (
                            original_line[0].repetition)
                to_create.append(record)
        if to_create:
            LimsBlindSample.create(to_create)


class LimsLoadServices(Wizard):
    'Load Services'
    __name__ = 'lims.load_services'

    start_state = 'check'
    check = StateTransition()
    load = StateTransition()

    def transition_check(self):
        LimsFraction = Pool().get('lims.fraction')

        fraction = LimsFraction(Transaction().context['active_id'])
        if (not fraction or not fraction.cie_fraction_type or
                not fraction.cie_original_fraction):
            return 'end'
        return 'load'

    def transition_load(self):
        pool = Pool()
        LimsFraction = pool.get('lims.fraction')
        LimsService = pool.get('lims.service')
        LimsAnalysis = pool.get('lims.analysis')

        new_fraction = LimsFraction(Transaction().context['active_id'])
        original_fraction = new_fraction.cie_original_fraction

        # new services
        services = LimsService.search([
            ('fraction', '=', original_fraction),
            ])
        for service in services:
            if not LimsAnalysis.is_typified(service.analysis,
                    new_fraction.product_type, new_fraction.matrix):
                continue
            new_service, = LimsService.copy([service], default={
                'fraction': new_fraction.id,
                })
        return 'end'
