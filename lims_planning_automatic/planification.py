# This file is part of lims_planning_automatic module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from datetime import datetime

from trytond.model import ModelSQL, ModelView, fields
from trytond.wizard import Wizard, StateTransition, StateView, Button
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
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
        Company = pool.get('company.company')

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

            company = Company(Transaction().context.get('company'))
            company_timezone = company.get_timezone()
            date_time = company_timezone.localize(datetime.combine(
                start_date, datetime.min.time()))

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


class ReleaseFractionAutomaticStart(ModelView):
    'Release Fraction'
    __name__ = 'lims.planification.release_fraction_automatic.start'

    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        required=True)
    date_from = fields.Date('Date from', required=True)
    date_to = fields.Date('Date to', required=True)


class ReleaseFractionAutomaticEmpty(ModelView):
    'Release Fraction'
    __name__ = 'lims.planification.release_fraction_automatic.empty'


class ReleaseFractionAutomaticResult(ModelView):
    'Release Fraction'
    __name__ = 'lims.planification.release_fraction_automatic.result'

    fractions = fields.Many2Many(
        'lims.planification.release_fraction_automatic.detail', None, None,
        'Fractions', required=True,
        domain=[('id', 'in', Eval('fractions_domain'))],
        depends=['fractions_domain'])
    fractions_domain = fields.One2Many(
        'lims.planification.release_fraction_automatic.detail', None,
        'Fractions domain')


class ReleaseFractionDetail(ModelSQL, ModelView):
    'Fraction to Release'
    __name__ = 'lims.planification.release_fraction_automatic.detail'
    _table = 'lims_planification_release_fraction_detail'

    fraction = fields.Many2One('lims.fraction', 'Fraction', readonly=True)
    service_analysis = fields.Many2One('lims.analysis', 'Service',
        readonly=True)
    fraction_type = fields.Function(fields.Many2One('lims.fraction.type',
        'Fraction type'), 'get_fraction_field',
        searcher='search_fraction_field')
    label = fields.Function(fields.Char('Label'), 'get_fraction_field',
        searcher='search_fraction_field')
    product_type = fields.Function(fields.Many2One('lims.product.type',
        'Product type'), 'get_fraction_field',
        searcher='search_fraction_field')
    matrix = fields.Function(fields.Many2One('lims.matrix', 'Matrix'),
        'get_fraction_field', searcher='search_fraction_field')
    notebook_lines = fields.Many2Many(
        'lims.planification.release_fraction_automatic.detail.line',
        'detail', 'notebook_line', 'Notebook Lines', readonly=True)
    session_id = fields.Integer('Session ID')

    @classmethod
    def __register__(cls, module_name):
        super().__register__(module_name)
        cursor = Transaction().connection.cursor()
        cursor.execute('DELETE FROM "' + cls._table + '"')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order.insert(0, ('fraction', 'ASC'))
        cls._order.insert(1, ('service_analysis', 'ASC'))

    @classmethod
    def get_fraction_field(cls, details, names):
        result = {}
        for name in names:
            result[name] = {}
            if name == 'fraction_type':
                for d in details:
                    field = getattr(d.fraction, 'type', None)
                    result[name][d.id] = field.id if field else None
            elif cls._fields[name]._type == 'many2one':
                for d in details:
                    field = getattr(d.fraction, name, None)
                    result[name][d.id] = field.id if field else None
            else:
                for d in details:
                    result[name][d.id] = getattr(d.fraction, name, None)
        return result

    @classmethod
    def search_fraction_field(cls, name, clause):
        if name == 'fraction_type':
            name = 'type'
        return [('fraction.' + name,) + tuple(clause[1:])]

    def _order_sample_field(name):
        def order_field(tables):
            pool = Pool()
            Sample = pool.get('lims.sample')
            Fraction = pool.get('lims.fraction')
            field = Sample._fields[name]
            table, _ = tables[None]
            fraction_tables = tables.get('fraction')
            if fraction_tables is None:
                fraction = Fraction.__table__()
                fraction_tables = {
                    None: (fraction, fraction.id == table.fraction),
                    }
                tables['fraction'] = fraction_tables
            return field.convert_order(name, fraction_tables, Fraction)
        return staticmethod(order_field)
    order_product_type = _order_sample_field('product_type')
    order_matrix = _order_sample_field('matrix')


class ReleaseFractionDetailLine(ModelSQL):
    'Line of Fraction to Release'
    __name__ = 'lims.planification.release_fraction_automatic.detail.line'
    _table = 'lims_planification_release_fraction_detail_line'

    detail = fields.Many2One(
        'lims.planification.release_fraction_automatic.detail', 'Detail',
        ondelete='CASCADE', select=True, required=True)
    notebook_line = fields.Many2One('lims.notebook.line', 'Notebook Line',
        ondelete='CASCADE', select=True, required=True)


class ReleaseFractionAutomatic(Wizard):
    'Release Fraction'
    __name__ = 'lims.planification.release_fraction_automatic'

    start = StateView('lims.planification.release_fraction_automatic.start',
        'lims_planning_automatic.lims_planification_release_fraction_automatic'
        '_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search', 'search', 'tryton-forward', default=True),
            ])
    search = StateTransition()
    empty = StateView('lims.planification.release_fraction_automatic.empty',
        'lims_planning_automatic.lims_planification_release_fraction_automatic'
        '_empty_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search again', 'start', 'tryton-forward', default=True),
            ])
    result = StateView('lims.planification.release_fraction_automatic.result',
        'lims_planning_automatic.lims_planification_release_fraction_automatic'
        '_result_view_form', [
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
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        ReleaseFractionDetail = pool.get(
            'lims.planification.release_fraction_automatic.detail')

        lines = NotebookLine.search([
            ('laboratory', '=', self.start.laboratory.id),
            ('start_date', '>=', self.start.date_from),
            ('start_date', '<=', self.start.date_to),
            ('end_date', '=', None),
            ('annulment_date', '=', None),
            ('result', 'in', [None, '']),
            ('converted_result', 'in', [None, '']),
            ('literal_result', 'in', [None, '']),
            ])

        records = {}
        for line in lines:
            key = (line.fraction.id, line.service.id)
            if key not in records:
                records[key] = {
                    'session_id': self._session_id,
                    'fraction': line.fraction.id,
                    'service_analysis': line.service.analysis.id,
                    'notebook_lines': [('add', [])],
                    }
            records[key]['notebook_lines'][0][1].append(line.id)

        if records:
            self.result.fractions = ReleaseFractionDetail.create(
                records.values())
            return 'result'
        return 'empty'

    def default_result(self, fields):
        fractions = [f.id for f in self.result.fractions]
        self.result.fractions = None
        return {
            'fractions_domain': fractions,
            }

    def transition_release(self):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        NotebookLineProfessional = pool.get(
            'lims.notebook.line-laboratory.professional')
        NotebookLineControl = pool.get('lims.notebook.line-fraction')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        notebook_lines_ids = []
        analysis_detail_ids = []

        for detail in self.result.fractions:
            for notebook_line in detail.notebook_lines:
                notebook_lines_ids.append(notebook_line.id)
                if notebook_line.analysis_detail:
                    analysis_detail_ids.append(
                        notebook_line.analysis_detail.id)

        if notebook_lines_ids:
            notebook_lines_ids = ', '.join(str(nl)
                for nl in notebook_lines_ids)
            cursor.execute('UPDATE "' + NotebookLine._table + '" '
                'SET start_date = NULL, planification = NULL '
                'WHERE id IN (' + notebook_lines_ids + ')')
            cursor.execute('DELETE FROM "' +
                NotebookLineProfessional._table + '" '
                'WHERE notebook_line IN (' + notebook_lines_ids + ')')
            cursor.execute('DELETE FROM "' +
                NotebookLineControl._table + '" '
                'WHERE notebook_line IN (' + notebook_lines_ids + ')')

        if analysis_detail_ids:
            analysis_detail_ids = ', '.join(str(ad)
                for ad in analysis_detail_ids)
            cursor.execute('UPDATE "' + EntryDetailAnalysis._table + '" '
                'SET state = \'unplanned\' '
                'WHERE id IN (' + analysis_detail_ids + ')')

        return 'end'
