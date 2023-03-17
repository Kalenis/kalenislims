# This file is part of lims_planning_automatic module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from datetime import datetime

from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction


class Planification(metaclass=PoolMeta):
    __name__ = 'lims.planification'

    automatic = fields.Boolean('Automatic')

    @classmethod
    def automatic_plan(cls, entries=None, tests=None):
        pool = Pool()
        SearchFractions = pool.get(
            'lims.planification.search_fractions', type='wizard')
        SearchFractionsDetail = pool.get(
            'lims.planification.search_fractions.detail')
        TechniciansQualification = pool.get(
            'lims.planification.technicians_qualification', type='wizard')

        for planification in cls._get_automatic_planifications():

            session_id, _, _ = SearchFractions.create()
            search_fractions = SearchFractions(session_id)
            with Transaction().set_context(active_id=planification.id):
                search_fractions.transition_search()
                details = SearchFractionsDetail.search([])
                search_fractions.next.details = details
                search_fractions.transition_add()

            cls.preplan([planification])

            staff = [t.laboratory_professional.id
                for t in planification.technicians]
            for f in planification.details:
                for s in f.details:
                    s.staff_responsible = staff
                    s.save()
            planification.save()

            session_id, _, _ = TechniciansQualification.create()
            technicians_qualification = TechniciansQualification(session_id)
            with Transaction().set_context(active_id=planification.id):
                res = technicians_qualification.transition_start()
                while res == 'next_':
                    res = technicians_qualification.transition_next_()
                technicians_qualification.transition_confirm()

    @classmethod
    def _get_automatic_planifications(cls, entries=None, tests=None):
        pool = Pool()
        Laboratory = pool.get('lims.laboratory')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        Planification = pool.get('lims.planification')
        PlanificationTechnician = pool.get('lims.planification.technician')

        res = []

        laboratories = Laboratory.search([('automatic_planning', '=', True)])
        for laboratory in laboratories:

            clause = [
                ('laboratory', '=', laboratory),
                ('plannable', '=', True),
                ('state', '=', 'unplanned'),
                ]
            if entries:
                clause.append(
                    ('entry', 'in', [e.id for e in entries]))
            if tests:
                clause.append(
                    ('sample', 'in', [t.sample.id for t in tests]))

            analysis_details = EntryDetailAnalysis.search(clause)
            if not analysis_details:
                continue

            analysis = list(set(d.analysis for d in analysis_details))
            professional = laboratory.default_laboratory_professional

            planification = Planification()
            planification.automatic = True
            planification.laboratory = laboratory
            planification.start_date = datetime.now().date()
            planification.analysis = analysis

            technician = PlanificationTechnician()
            technician.laboratory_professional = professional
            planification.technicians = [technician]
            planification.save()

            res.append(planification)

        return res
