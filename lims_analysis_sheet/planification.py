# This file is part of lims_analysis_sheet module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from datetime import datetime

from trytond.model import ModelView, ModelSQL, fields
from trytond.wizard import Wizard, StateTransition, StateView, Button
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, Equal, Bool
from trytond.transaction import Transaction

__all__ = ['Planification', 'SearchAnalysisSheetStart',
    'SearchAnalysisSheetNext', 'SearchAnalysisSheet', 'RelateTechniciansStart',
    'RelateTechniciansResult', 'RelateTechniciansDetail4', 'RelateTechnicians']


class Planification(metaclass=PoolMeta):
    __name__ = 'lims.planification'

    @classmethod
    def __setup__(cls):
        super(Planification, cls).__setup__()
        cls._buttons.update({
            'search_analysis_sheet': {
                'readonly': (Eval('state') != 'draft'),
                },
            })

    @classmethod
    @ModelView.button_action('lims_analysis_sheet.wiz_search_analysis_sheet')
    def search_analysis_sheet(cls, planifications):
        pass

    @classmethod
    def do_confirm(cls, planifications):
        super(Planification, cls).do_confirm(planifications)
        for planification in planifications:
            planification.create_analysis_sheets()

    def create_analysis_sheets(self):
        pool = Pool()
        PlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')
        AnalysisSheet = pool.get('lims.analysis_sheet')

        analysis_sheets = {}
        service_details = PlanificationServiceDetail.search([
            ('detail.planification', '=', self.id),
            ('notebook_line', '!=', None),
            ])
        for service_detail in service_details:
            nl = service_detail.notebook_line
            template_id = nl.get_analysis_sheet_template()
            if not template_id:
                continue
            key = (template_id, service_detail.staff_responsible[0])
            if key not in analysis_sheets:
                analysis_sheets[key] = []
            analysis_sheets[key].append(nl)

        date_time = datetime.combine(self.start_date, self.create_date.time())

        for key, values in analysis_sheets.items():
            sheet = AnalysisSheet()
            sheet.template = key[0]
            sheet.compilation = sheet.get_new_compilation(
                {'date_time': date_time})
            sheet.professional = key[1]
            sheet.laboratory = self.laboratory.id
            sheet.planification = self.id
            sheet.save()
            sheet.create_lines(values)
            #sheet.activate([sheet])


class SearchAnalysisSheetStart(ModelView):
    'Search Analysis Sheets'
    __name__ = 'lims.planification.search_analysis_sheet.start'

    date_from = fields.Date('Date from', required=True, readonly=True)
    date_to = fields.Date('Date to', required=True, readonly=True)
    templates = fields.Many2Many('lims.template.analysis_sheet',
        None, None, 'Templates', required=True,
        domain=[('id', 'in', Eval('templates_domain'))],
        context={'date_from': Eval('date_from'), 'date_to': Eval('date_to')},
        depends=['templates_domain', 'date_from', 'date_to'])
    templates_domain = fields.One2Many('lims.template.analysis_sheet',
        None, 'Templates domain')


class SearchAnalysisSheetNext(ModelView):
    'Search Analysis Sheets'
    __name__ = 'lims.planification.search_analysis_sheet.next'

    details = fields.Many2Many(
        'lims.planification.search_fractions.detail',
        None, None, 'Fractions to plan', depends=['details_domain'],
        domain=[('id', 'in', Eval('details_domain'))], required=True)
    details_domain = fields.One2Many(
        'lims.planification.search_fractions.detail',
        None, 'Fractions domain')


class SearchAnalysisSheet(Wizard):
    'Search Analysis Sheets'
    __name__ = 'lims.planification.search_analysis_sheet'

    start = StateView('lims.planification.search_analysis_sheet.start',
        'lims_analysis_sheet.planification_search_analysis_sheet_start'
        '_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search', 'search', 'tryton-forward', default=True),
            ])
    search = StateTransition()
    next = StateView('lims.planification.search_analysis_sheet.next',
        'lims_analysis_sheet.planification_search_analysis_sheet_next'
        '_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Add', 'add', 'tryton-ok', default=True),
            ])
    add = StateTransition()

    def default_start(self, fields):
        Planification = Pool().get('lims.planification')

        planification = Planification(Transaction().context['active_id'])
        templates = self._get_templates(planification)
        return {
            'templates': [],
            'templates_domain': templates,
            'date_from': planification.date_from,
            'date_to': planification.date_to,
            }

    def _get_templates(self, planification):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        PlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')
        PlanificationDetail = pool.get('lims.planification.detail')
        Planification = pool.get('lims.planification')
        NotebookLine = pool.get('lims.notebook.line')
        Notebook = pool.get('lims.notebook')
        Fraction = pool.get('lims.fraction')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        Analysis = pool.get('lims.analysis')
        TemplateAnalysis = pool.get('lims.template.analysis_sheet.analysis')

        cursor.execute('SELECT nl.id '
            'FROM "' + NotebookLine._table + '" nl '
                'INNER JOIN "' + PlanificationServiceDetail._table +
                '" psd ON psd.notebook_line = nl.id '
                'INNER JOIN "' + PlanificationDetail._table + '" pd '
                'ON psd.detail = pd.id '
                'INNER JOIN "' + Planification._table + '" p '
                'ON pd.planification = p.id '
            'WHERE p.state = \'preplanned\' '
                'OR p.id = %s',
            (str(planification.id),))
        preplanned_lines = [x[0] for x in cursor.fetchall()]
        preplanned_lines_ids = ', '.join(str(x)
            for x in [0] + preplanned_lines)

        sql_select = 'SELECT nl.analysis, nl.method '
        sql_from = (
            'FROM "' + NotebookLine._table + '" nl '
            'INNER JOIN "' + Analysis._table + '" nla '
            'ON nla.id = nl.analysis '
            'INNER JOIN "' + Notebook._table + '" nb '
            'ON nb.id = nl.notebook '
            'INNER JOIN "' + Fraction._table + '" frc '
            'ON frc.id = nb.fraction '
            'INNER JOIN "' + EntryDetailAnalysis._table + '" ad '
            'ON ad.id = nl.analysis_detail ')
        sql_where = (
            'WHERE ad.plannable = TRUE '
            'AND nl.start_date IS NULL '
            'AND nl.annulled = FALSE '
            'AND nl.laboratory = %s '
            'AND nl.id NOT IN (' + preplanned_lines_ids + ') '
            'AND nla.behavior != \'internal_relation\' '
            'AND ad.confirmation_date::date >= %s::date '
            'AND ad.confirmation_date::date <= %s::date')

        with Transaction().set_user(0):
            cursor.execute(sql_select + sql_from + sql_where,
                (planification.laboratory.id, planification.date_from,
                planification.date_to,))
        notebook_lines = cursor.fetchall()
        if not notebook_lines:
            return []

        result = []
        for nl in notebook_lines:
            cursor.execute('SELECT template '
                'FROM "' + TemplateAnalysis._table + '" '
                'WHERE analysis = %s '
                'AND (method = %s OR method IS NULL)',
                (nl[0], nl[1]))
            template = cursor.fetchone()
            if template:
                result.append(template[0])
        return list(set(result))

    def transition_search(self):
        pool = Pool()
        Planification = pool.get('lims.planification')
        SearchFractionsDetail = pool.get(
            'lims.planification.search_fractions.detail')

        planification = Planification(Transaction().context['active_id'])
        data = self._get_service_details(planification)

        to_create = []
        for k, v in data.items():
            to_create.append({
                'session_id': self._session_id,
                'fraction': k[0],
                'service_analysis': k[1],
                'repetition': v['repetition'],
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
        PlanificationAnalysis = pool.get('lims.planification-analysis')

        planification = Planification(Transaction().context['active_id'])

        records_added = ['(%s,%s)' % (d.fraction.id, d.service_analysis.id)
            for d in self.next.details]
        records_ids_added = ', '.join(str(x)
            for x in ['(0,0)'] + records_added)
        extra_where = (
            'AND (nb.fraction, srv.analysis) IN (' + records_ids_added + ') ')

        data = self._get_service_details(planification, extra_where)

        details_to_create = []
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
                details_to_create.append({
                    'planification': planification.id,
                    'fraction': k[0],
                    'service_analysis': k[1],
                    'details': [('create', v)],
                    })
        if details_to_create:
            PlanificationDetail.create(details_to_create)

        analysis_to_create = []
        for a_id in list(set(k[1] for k in list(data.keys()))):
            if not PlanificationAnalysis.search([
                    ('planification', '=', planification.id),
                    ('analysis', '=', a_id),
                    ]):
                analysis_to_create.append({
                    'planification': planification.id,
                    'analysis': a_id,
                    })
        if analysis_to_create:
            PlanificationAnalysis.create(analysis_to_create)

        return 'end'

    def _get_service_details(self, planification, extra_where=''):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        PlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')
        NotebookLine = pool.get('lims.notebook.line')
        Notebook = pool.get('lims.notebook')
        Fraction = pool.get('lims.fraction')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        Service = pool.get('lims.service')
        Analysis = pool.get('lims.analysis')
        TemplateAnalysis = pool.get('lims.template.analysis_sheet.analysis')

        planification_details = PlanificationServiceDetail.search(['OR',
            ('planification.state', '=', 'preplanned'),
            ('planification', '=', planification.id),
            ])
        planned_lines = [pd.notebook_line.id for pd in planification_details
            if pd.notebook_line]
        planned_lines_ids = ', '.join(str(x) for x in [0] + planned_lines)

        template_analysis = {}
        for template in self.start.templates:
            cursor.execute('SELECT analysis, method '
                'FROM "' + TemplateAnalysis._table + '" '
                'WHERE template = %s',
                (template.id,))
            for res in cursor.fetchall():
                template_analysis[res[0]] = res[1]
        if not template_analysis:
            return {}

        all_included_analysis_ids = ', '.join(str(x)
            for x in list(template_analysis.keys()))
        service_where = ('AND ad.analysis IN (' +
            all_included_analysis_ids + ') ')

        sql_select = ('SELECT nl.id, nb.fraction, srv.analysis' +
            ', nl.analysis, nl.method, nl.repetition != 0 ')

        sql_from = (
            'FROM "' + NotebookLine._table + '" nl '
            'INNER JOIN "' + Analysis._table + '" nla '
            'ON nla.id = nl.analysis '
            'INNER JOIN "' + Notebook._table + '" nb '
            'ON nb.id = nl.notebook '
            'INNER JOIN "' + Fraction._table + '" frc '
            'ON frc.id = nb.fraction '
            'INNER JOIN "' + EntryDetailAnalysis._table + '" ad '
            'ON ad.id = nl.analysis_detail '
            'INNER JOIN "' + Service._table + '" srv '
            'ON srv.id = nl.service ')

        sql_where = (
            'WHERE ad.plannable = TRUE '
            'AND nl.start_date IS NULL '
            'AND nl.annulled = FALSE '
            'AND nl.laboratory = %s '
            'AND nl.id NOT IN (' + planned_lines_ids + ') '
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
            return {}

        result = {}
        nlines_added = []
        if extra_where:
            for nl in notebook_lines:
                if (template_analysis[nl[3]] and
                        template_analysis[nl[3]] != nl[4]):
                    continue
                f_ = nl[1]
                s_ = nl[2]
                if (f_, s_) not in result:
                    result[(f_, s_)] = []
                if nl[0] not in nlines_added:
                    nlines_added.append(nl[0])
                    result[(f_, s_)].append({
                        'notebook_line': nl[0],
                        'planned_service': nl[2],
                        })
        else:
            for nl in notebook_lines:
                if (template_analysis[nl[3]] and
                        template_analysis[nl[3]] != nl[4]):
                    continue
                f_ = nl[1]
                s_ = nl[2]
                result[(f_, s_)] = {
                    'repetition': nl[5],
                    }

        return result


class RelateTechniciansStart(metaclass=PoolMeta):
    __name__ = 'lims.planification.relate_technicians.start'

    @classmethod
    def __setup__(cls):
        super(RelateTechniciansStart, cls).__setup__()
        grouping = ('analysis_sheet', 'Analysis sheet')
        if grouping not in cls.grouping.selection:
            cls.grouping.selection.append(grouping)


class RelateTechniciansResult(metaclass=PoolMeta):
    __name__ = 'lims.planification.relate_technicians.result'

    details4 = fields.Many2Many(
        'lims.planification.relate_technicians.detail4', None, None,
        'Fractions to plan', domain=[('id', 'in', Eval('details4_domain'))],
        states={'invisible': ~Bool(Equal(Eval('grouping'), 'analysis_sheet'))},
        depends=['details4_domain', 'grouping'])
    details4_domain = fields.One2Many(
        'lims.planification.relate_technicians.detail4', None,
        'Fractions domain')

    @classmethod
    def __setup__(cls):
        super(RelateTechniciansResult, cls).__setup__()
        grouping = ('analysis_sheet', 'Analysis sheet')
        if grouping not in cls.grouping.selection:
            cls.grouping.selection.append(grouping)

    @fields.depends('grouping')
    def on_change_grouping(self):
        super(RelateTechniciansResult, self).on_change_grouping()
        self.details4 = []


class RelateTechniciansDetail4(ModelSQL, ModelView):
    'Fraction Detail'
    __name__ = 'lims.planification.relate_technicians.detail4'
    _table = 'lims_planification_relate_technicians_d4'

    fraction = fields.Many2One('lims.fraction', 'Fraction')
    template = fields.Many2One('lims.template.analysis_sheet',
        'Analysis sheet')
    session_id = fields.Integer('Session ID')

    @classmethod
    def __register__(cls, module_name):
        super(RelateTechniciansDetail4,
            cls).__register__(module_name)
        cursor = Transaction().connection.cursor()
        cursor.execute('DELETE FROM "' + cls._table + '"')

    @classmethod
    def __setup__(cls):
        super(RelateTechniciansDetail4, cls).__setup__()
        cls._order.insert(0, ('fraction', 'ASC'))
        cls._order.insert(1, ('template', 'ASC'))


class RelateTechnicians(metaclass=PoolMeta):
    __name__ = 'lims.planification.relate_technicians'

    def transition_search(self):
        planification_id = Transaction().context['active_id']

        self.result.details4_domain = []

        if self.start.grouping == 'analysis_sheet':
            self.result.details4_domain = self._view_details4(planification_id,
                self.start.exclude_relateds)
        return super(RelateTechnicians, self).transition_search()

    def default_result(self, fields):
        res = super(RelateTechnicians, self).default_result(fields)
        details4_domain = []
        if self.result.details4_domain:
            details4_domain = [d.id for d in self.result.details4_domain]
        res['details4_domain'] = details4_domain
        return res

    def _view_details4(self, planification_id, exclude_relateds):
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
        RelateTechniciansDetail4 = pool.get(
            'lims.planification.relate_technicians.detail4')
        TemplateAnalysis = pool.get('lims.template.analysis_sheet.analysis')

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

        details4 = {}
        cursor.execute('SELECT d.fraction, nl.analysis, nl.method '
            'FROM "' + PlanificationDetail._table + '" d '
                'INNER JOIN "' + PlanificationServiceDetail._table + '" sd '
                    'ON sd.detail = d.id '
                'INNER JOIN "' + NotebookLine._table + '" nl '
                    'ON sd.notebook_line = nl.id '
            'WHERE d.planification = %s' +
            exclude_relateds_clause,
            (planification_id,))
        for x in cursor.fetchall():
            cursor.execute('SELECT template '
                'FROM "' + TemplateAnalysis._table + '" '
                'WHERE analysis = %s '
                'AND (method = %s OR method IS NULL)',
                (x[1], x[2]))
            template = cursor.fetchone()
            t = template and template[0] or None
            f = x[0]
            if (f, t) not in details4:
                details4[(f, t)] = {
                    'fraction': f,
                    'template': t,
                    }

        to_create = []
        for d in details4.values():
            to_create.append({
                'session_id': self._session_id,
                'fraction': d['fraction'],
                'template': d['template'],
                })
        return RelateTechniciansDetail4.create(to_create)

    def _get_details(self, planification_id):
        details = super(RelateTechnicians, self)._get_details(planification_id)
        if self.start.grouping == 'analysis_sheet':
            details = self._get_details4(planification_id,
                self.start.exclude_relateds)
        return details

    def _get_details4(self, planification_id, exclude_relateds):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        PlanificationDetail = pool.get(
            'lims.planification.detail')
        PlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')
        ServiceDetailProfessional = pool.get(
            'lims.planification.service_detail-laboratory.professional')
        NotebookLine = pool.get('lims.notebook.line')
        TemplateAnalysis = pool.get('lims.template.analysis_sheet.analysis')

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
        for detail in self.result.details4:

            template_analysis = {}
            cursor.execute('SELECT analysis, method '
                'FROM "' + TemplateAnalysis._table + '" '
                'WHERE template = %s',
                (detail.template and detail.template.id or None,))
            for res in cursor.fetchall():
                template_analysis[res[0]] = res[1]
            if not template_analysis:
                continue
            all_included_analysis_ids = ', '.join(str(x)
                for x in list(template_analysis.keys()))
            analysis_where = ('AND nl.analysis IN (' +
                all_included_analysis_ids + ') ')

            cursor.execute('SELECT sd.id, nl.analysis, nl.method '
                'FROM "' + PlanificationDetail._table + '" d '
                    'INNER JOIN "' + PlanificationServiceDetail._table + '" sd'
                        ' ON sd.detail = d.id '
                    'INNER JOIN "' + NotebookLine._table + '" nl '
                        'ON sd.notebook_line = nl.id '
                'WHERE d.planification = %s '
                    'AND d.fraction = %s ' +
                    analysis_where + exclude_relateds_clause,
                (planification_id, detail.fraction.id))
            for x in cursor.fetchall():
                if (template_analysis[x[1]] and
                        template_analysis[x[1]] != x[2]):
                    continue
                details.append(x[0])

        return PlanificationServiceDetail.browse(details)
