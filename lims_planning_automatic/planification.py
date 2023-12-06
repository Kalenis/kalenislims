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

        for planification in cls._get_automatic_planifications(
                entries=entries, tests=tests):

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

            planification.load_analysis_sheets()

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

            if laboratory.automatic_planning_simplified:
                cls.automatic_plan_simplified(laboratory, entries, tests)
                continue

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

    @classmethod
    def automatic_plan_simplified(cls, laboratory, entries=None, tests=None):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        Notebook = pool.get('lims.notebook')
        Fraction = pool.get('lims.fraction')
        Sample = pool.get('lims.sample')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        Analysis = pool.get('lims.analysis')
        Date = pool.get('ir.date')
        NotebookLineProfessional = pool.get(
            'lims.notebook.line-laboratory.professional')
        try:
            AnalysisSheet = pool.get('lims.analysis_sheet')
        except KeyError:
            analysis_sheet_activated = False
        else:
            analysis_sheet_activated = True

        sql_select = 'SELECT nl.id, ad.id '
        sql_from = (
            'FROM "' + NotebookLine._table + '" nl '
            'INNER JOIN "' + Analysis._table + '" an '
            'ON an.id = nl.analysis '
            'INNER JOIN "' + EntryDetailAnalysis._table + '" ad '
            'ON ad.id = nl.analysis_detail '
            'INNER JOIN "' + Notebook._table + '" nb '
            'ON nb.id = nl.notebook '
            'INNER JOIN "' + Fraction._table + '" fr '
            'ON fr.id = nb.fraction '
            'INNER JOIN "' + Sample._table + '" sa '
            'ON sa.id = fr.sample ')
        sql_where = (
            'WHERE ad.plannable = TRUE '
            'AND nl.start_date IS NULL '
            'AND nl.annulled = FALSE '
            'AND nl.laboratory = %s '
            'AND an.behavior != \'internal_relation\' ')

        if entries:
            sql_where += 'AND sa.entry IN (%s) ' % ', '.join(
                str(e.id) for e in entries)
        if tests:
            sql_where += 'AND fr.sample IN (%s) ' % ', '.join(
                str(t.sample.id) for t in tests)

        sql_order = 'ORDER BY nb.fraction ASC'

        with Transaction().set_user(0):
            cursor.execute(sql_select + sql_from + sql_where + sql_order,
                (laboratory.id,))
        res = cursor.fetchall()
        if not res:
            return

        notebook_lines, detail_analyses = set(), set()
        for x in res:
            notebook_lines.add(x[0])
            detail_analyses.add(x[1])

        lines = NotebookLine.browse(list(notebook_lines))
        details = EntryDetailAnalysis.browse(list(detail_analyses))

        start_date = Date.today()
        professional_id = laboratory.default_laboratory_professional.id

        NotebookLine.write(lines, {'start_date': start_date})

        EntryDetailAnalysis.write(details, {'state': 'planned'})

        notebook_lines_ids = ', '.join(str(nl_id) for nl_id in notebook_lines)
        cursor.execute('DELETE FROM "' +
            NotebookLineProfessional._table + '" '
            'WHERE notebook_line IN (' + notebook_lines_ids + ')')
        NotebookLineProfessional.create([{
            'notebook_line': nl_id,
            'professional': professional_id,
            } for nl_id in notebook_lines])

        if analysis_sheet_activated:

            date_time = datetime.combine(start_date, datetime.now().time())

            analysis_sheets = {}
            for nl in lines:
                template_id = nl.get_analysis_sheet_template()
                if not template_id:
                    continue
                key = (template_id, professional_id)
                if key not in analysis_sheets:
                    analysis_sheets[key] = []
                analysis_sheets[key].append(nl)

            for key, values in analysis_sheets.items():
                sheet = AnalysisSheet()
                sheet.template = key[0]
                sheet.compilation = sheet.get_new_compilation(
                    {'date_time': date_time})
                sheet.professional = key[1]
                sheet.laboratory = laboratory.id
                sheet.save()
                sheet.create_lines(values)

        return res
