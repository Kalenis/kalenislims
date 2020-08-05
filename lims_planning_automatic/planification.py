# This file is part of lims_planning_automatic module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction

__all__ = ['Planification']


class Planification(metaclass=PoolMeta):
    __name__ = 'lims.planification'

    automatic = fields.Boolean('Automatic')

    @classmethod
    def automatic_plan(cls, entries=None, tests=None):
        pool = Pool()
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        PlanificationTechnician = pool.get('lims.planification.technician')
        SearchFractions = pool.get(
            'lims.planification.search_fractions', type='wizard')
        SearchFractionsDetail = pool.get(
            'lims.planification.search_fractions.detail')
        TechniciansQualification = pool.get(
            'lims.planification.technicians_qualification', type='wizard')
        Laboratory = pool.get('lims.laboratory')
        Date = pool.get('ir.date')

        laboratories = Laboratory.search([('automatic_planning', '=', True)])
        for laboratory in laboratories:

            clause = [
                ('laboratory', '=', laboratory),
                ('plannable', '=', True),
                ]
            if entries:
                clause.append(('entry', 'in', [e.id for e in entries]),)

            if tests:
                clause.append(('sample', 'in', [t.sample.id for t in tests]),)

            detail_analyses = EntryDetailAnalysis.search(clause)
            if not detail_analyses:
                continue

            analyses_to_plan = []
            for detail_analysis in detail_analyses:
                analyses_to_plan.append(detail_analysis.analysis)

            planification = cls()
            planification.automatic = True
            planification.laboratory = laboratory
            planification.start_date = Date.today()
            planification.analysis = analyses_to_plan

            technician = PlanificationTechnician()
            technician.laboratory_professional = \
                laboratory.default_laboratory_professional
            planification.technicians = [technician]
            planification.save()
            session_id, _, _ = SearchFractions.create()
            search_fractions = SearchFractions(session_id)
            with Transaction().set_context(active_id=planification.id):
                search_fractions.transition_search()
                details = SearchFractionsDetail.search([])
                search_fractions.next.details = details
                search_fractions.transition_add()
            cls.preplan([planification])
            for f in planification.details:
                for s in f.details:
                    s.staff_responsible = [
                        laboratory.default_laboratory_professional.id]
                    s.save()
            planification.save()
            session_id, _, _ = TechniciansQualification.create()
            technicians_qualification = TechniciansQualification(session_id)
            with Transaction().set_context(active_id=planification.id):
                technicians_qualification.transition_start()
                technicians_qualification.transition_next_()
                technicians_qualification.transition_confirm()
