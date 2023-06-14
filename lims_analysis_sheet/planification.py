# This file is part of lims_analysis_sheet module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import operator
from datetime import datetime, time
from collections import defaultdict
from sql import Column, Literal, Cast

from trytond.model import ModelView, ModelSQL, fields
from trytond.wizard import Wizard, StateTransition, StateView, StateAction, \
    Button
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, Equal, Bool, If, PYSONEncoder
from trytond.transaction import Transaction


class Planification(metaclass=PoolMeta):
    __name__ = 'lims.planification'

    planification_update_draft_sheet = fields.Boolean(
        'Update draft sheets')
    analysis_sheets = fields.One2Many('lims.planification.analysis_sheet',
        'planification', 'Analysis sheets to update',
        states={'readonly': Eval('state') != 'preplanned'})

    @staticmethod
    def default_planification_update_draft_sheet():
        Config = Pool().get('lims.configuration')
        return Config(1).planification_update_draft_sheet

    @classmethod
    def __setup__(cls):
        super().__setup__()
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
    @ModelView.button_action('lims.wiz_lims_technicians_qualification')
    def confirm(cls, planifications):
        super().confirm(planifications)
        for planification in planifications:
            planification.load_analysis_sheets()

    def load_analysis_sheets(self):
        pool = Pool()
        PlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')
        AnalysisSheet = pool.get('lims.analysis_sheet')
        PlanificationAnalysisSheet = pool.get(
            'lims.planification.analysis_sheet')

        if not self.planification_update_draft_sheet:
            return

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

        for key, values in analysis_sheets.items():
            if PlanificationAnalysisSheet.search([
                    ('planification', '=', self.id),
                    ('professional', '=', key[1]),
                    ('analysis_sheet.template', '=', key[0]),
                    ('analysis_sheet.date2', '=', self.start_date),
                    ]):
                continue
            draft_sheet = AnalysisSheet.search([
                ('template', '=', key[0]),
                ('professional', '=', key[1]),
                ('date2', '=', self.start_date),
                ('state', '=', 'draft'),
                ])
            if not draft_sheet:
                continue
            PlanificationAnalysisSheet.create([{
                'planification': self.id,
                'professional': key[1],
                'analysis_sheet': draft_sheet[0].id,
                }])

    @classmethod
    def do_confirm(cls, planifications):
        super().do_confirm(planifications)
        for planification in planifications:
            planification.create_analysis_sheets()

    def create_analysis_sheets(self):
        pool = Pool()
        PlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')
        AnalysisSheet = pool.get('lims.analysis_sheet')
        PlanificationAnalysisSheet = pool.get(
            'lims.planification.analysis_sheet')
        analysis_sheets = {}
        sheets = []
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
            planification_sheet = PlanificationAnalysisSheet.search([
                ('planification', '=', self.id),
                ('professional', '=', key[1]),
                ('analysis_sheet.template', '=', key[0]),
                ('analysis_sheet.state', 'in', ['draft', 'active']),
                ('analysis_sheet.date2', '=', self.start_date),
                ])
            if planification_sheet:
                sheet = AnalysisSheet(planification_sheet[0].analysis_sheet.id)
            else:
                sheet = AnalysisSheet()
                sheet.template = key[0]
                sheet.compilation = sheet.get_new_compilation(
                    {'date_time': date_time})
                sheet.professional = key[1]
                sheet.laboratory = self.laboratory.id
                sheet.planification = self.id
                sheet.save()
            sheets.append(sheet)
            sheet.create_lines(values)
        return sheets


class PlanificationAnalysisSheet(ModelSQL, ModelView):
    'Planification - Analysis Sheet'
    __name__ = 'lims.planification.analysis_sheet'

    planification = fields.Many2One('lims.planification', 'Planification',
        ondelete='CASCADE', required=True)
    professional = fields.Many2One('lims.laboratory.professional',
        'Laboratory professional', required=True)
    analysis_sheet = fields.Many2One('lims.analysis_sheet',
        'Analysis Sheet', required=True,
        domain=['OR', ('id', '=', Eval('analysis_sheet', -1)),
            [('state', 'in', ['draft', 'active']),
                ('professional', '=', Eval('professional'))]])
    template = fields.Function(fields.Many2One('lims.template.analysis_sheet',
        'Template'), 'on_change_with_template')

    @fields.depends('analysis_sheet')
    def on_change_with_template(self, name=None):
        if self.analysis_sheet:
            return self.analysis_sheet.template.id
        return None


class SearchAnalysisSheetStart(ModelView):
    'Search Analysis Sheets'
    __name__ = 'lims.planification.search_analysis_sheet.start'

    date_from = fields.Date('Date from', readonly=True)
    date_to = fields.Date('Date to', readonly=True)
    templates = fields.Many2Many('lims.template.analysis_sheet',
        None, None, 'Templates', required=True,
        domain=[('id', 'in', Eval('templates_domain'))],
        context={'date_from': Eval('date_from'), 'date_to': Eval('date_to')},
        depends={'date_from', 'date_to'})
    templates_domain = fields.One2Many('lims.template.analysis_sheet',
        None, 'Templates domain')


class SearchAnalysisSheetNext(ModelView):
    'Search Analysis Sheets'
    __name__ = 'lims.planification.search_analysis_sheet.next'

    details = fields.Many2Many(
        'lims.planification.search_fractions.detail',
        None, None, 'Fractions to plan',
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
        templates_domain = self._get_templates(planification)
        return {
            'templates': [],
            'templates_domain': templates_domain,
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
        Sample = pool.get('lims.sample')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        Analysis = pool.get('lims.analysis')
        Template = pool.get('lims.template.analysis_sheet')
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
        planned_lines = [x[0] for x in cursor.fetchall()]
        planned_lines_ids = ', '.join(str(x) for x in [0] + planned_lines)
        preplanned_where = 'AND nl.id NOT IN (%s) ' % planned_lines_ids

        dates_where = ''
        if planification.date_from:
            dates_where += ('AND ad.confirmation_date::date >= \'%s\'::date ' %
                planification.date_from)
        if planification.date_to:
            dates_where += ('AND ad.confirmation_date::date <= \'%s\'::date ' %
                planification.date_to)

        sql_select = 'SELECT nl.analysis, nl.method, s.product_type, s.matrix '
        sql_from = (
            'FROM "' + NotebookLine._table + '" nl '
            'INNER JOIN "' + Analysis._table + '" nla '
            'ON nla.id = nl.analysis '
            'INNER JOIN "' + Notebook._table + '" n '
            'ON n.id = nl.notebook '
            'INNER JOIN "' + Fraction._table + '" f '
            'ON f.id = n.fraction '
            'INNER JOIN "' + Sample._table + '" s '
            'ON s.id = f.sample '
            'INNER JOIN "' + EntryDetailAnalysis._table + '" ad '
            'ON ad.id = nl.analysis_detail ')
        sql_where = (
            'WHERE ad.plannable = TRUE '
            'AND nl.start_date IS NULL '
            'AND nl.annulled = FALSE '
            'AND nl.laboratory = %s '
            'AND nla.behavior != \'internal_relation\' ' +
            preplanned_where + dates_where)

        with Transaction().set_user(0):
            cursor.execute(sql_select + sql_from + sql_where,
                (planification.laboratory.id,))
        notebook_lines = cursor.fetchall()
        if not notebook_lines:
            return []

        result = []
        for nl in notebook_lines:
            cursor.execute('SELECT t.id '
                'FROM "' + Template._table + '" t '
                    'INNER JOIN "' + TemplateAnalysis._table + '" ta '
                    'ON t.id = ta.template '
                'WHERE t.active IS TRUE '
                    'AND ta.analysis = %s '
                    'AND (ta.method = %s OR ta.method IS NULL) '
                    'AND (ta.product_type = %s OR ta.product_type IS NULL) '
                    'AND (ta.matrix = %s OR ta.matrix IS NULL)',
                (nl[0], nl[1], nl[2], nl[3]))
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

        template_analysis = {}
        for template in self.start.templates:
            cursor.execute('SELECT analysis, method '
                'FROM "' + TemplateAnalysis._table + '" '
                'WHERE template = %s',
                (template.id,))
            for res in cursor.fetchall():
                if res[0] not in template_analysis:
                    template_analysis[res[0]] = []
                if res[1]:
                    template_analysis[res[0]].append(res[1])
        if not template_analysis:
            return {}
        all_included_analysis_ids = ', '.join(str(x)
            for x in list(template_analysis.keys()))
        service_where = 'AND ad.analysis IN (%s) ' % all_included_analysis_ids

        planification_details = PlanificationServiceDetail.search([['OR',
            ('planification.state', '=', 'preplanned'),
            ('planification', '=', planification.id)],
            ('notebook_line', '!=', None),
            ])
        planned_lines = [pd.notebook_line.id for pd in planification_details]
        planned_lines_ids = ', '.join(str(x) for x in [0] + planned_lines)
        preplanned_where = 'AND nl.id NOT IN (%s) ' % planned_lines_ids

        dates_where = ''
        if planification.date_from:
            dates_where += ('AND ad.confirmation_date::date >= \'%s\'::date ' %
                planification.date_from)
        if planification.date_to:
            dates_where += ('AND ad.confirmation_date::date <= \'%s\'::date ' %
                planification.date_to)

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
            'AND nla.behavior != \'internal_relation\' ' +
            preplanned_where + dates_where + service_where + extra_where)

        sql_order = (
            'ORDER BY nb.fraction ASC, srv.analysis ASC')

        with Transaction().set_user(0):
            cursor.execute(sql_select + sql_from + sql_where + sql_order,
                (planification.laboratory.id,))
        notebook_lines = cursor.fetchall()
        if not notebook_lines:
            return {}

        result = {}
        nlines_added = []
        if extra_where:
            for nl in notebook_lines:
                if (template_analysis[nl[3]] and
                        nl[4] not in template_analysis[nl[3]]):
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
                        nl[4] not in template_analysis[nl[3]]):
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
        super().__setup__()
        grouping = ('analysis_sheet', 'Analysis sheet')
        if grouping not in cls.grouping.selection:
            cls.grouping.selection.append(grouping)


class RelateTechniciansResult(metaclass=PoolMeta):
    __name__ = 'lims.planification.relate_technicians.result'

    details4 = fields.Many2Many(
        'lims.planification.relate_technicians.detail4', None, None,
        'Fractions to plan', domain=[('id', 'in', Eval('details4_domain'))],
        states={'invisible': ~Bool(Equal(Eval('grouping'), 'analysis_sheet'))})
    details4_domain = fields.One2Many(
        'lims.planification.relate_technicians.detail4', None,
        'Fractions domain')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        grouping = ('analysis_sheet', 'Analysis sheet')
        if grouping not in cls.grouping.selection:
            cls.grouping.selection.append(grouping)

    @fields.depends('grouping')
    def on_change_grouping(self):
        super().on_change_grouping()
        self.details4 = []


class RelateTechniciansDetail4(ModelSQL, ModelView):
    'Fraction Detail'
    __name__ = 'lims.planification.relate_technicians.detail4'
    _table = 'lims_planification_relate_technicians_d4'

    fraction = fields.Many2One('lims.fraction', 'Fraction')
    template = fields.Many2One('lims.template.analysis_sheet',
        'Analysis sheet')
    services_list = fields.Char('Services')
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
        cls._order.insert(1, ('template', 'ASC'))


class RelateTechnicians(metaclass=PoolMeta):
    __name__ = 'lims.planification.relate_technicians'

    def transition_search(self):
        planification_id = Transaction().context['active_id']

        self.result.details4_domain = []

        if self.start.grouping == 'analysis_sheet':
            self.result.details4_domain = self._view_details4(planification_id,
                self.start.exclude_relateds)
        return super().transition_search()

    def default_result(self, fields):
        res = super().default_result(fields)
        details4_domain = []
        if self.result.details4_domain:
            details4_domain = [d.id for d in self.result.details4_domain]
        res['details4_domain'] = details4_domain
        return res

    def _view_details4(self, planification_id, exclude_relateds):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        PlanificationDetail = pool.get('lims.planification.detail')
        PlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')
        ServiceDetailProfessional = pool.get(
            'lims.planification.service_detail-laboratory.professional')
        NotebookLine = pool.get('lims.notebook.line')
        RelateTechniciansDetail4 = pool.get(
            'lims.planification.relate_technicians.detail4')
        Template = pool.get('lims.template.analysis_sheet')
        TemplateAnalysis = pool.get('lims.template.analysis_sheet.analysis')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        Service = pool.get('lims.service')

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
        cursor.execute('SELECT d.fraction, nl.analysis, nl.method, '
                'ad.service '
            'FROM "' + PlanificationDetail._table + '" d '
                'INNER JOIN "' + PlanificationServiceDetail._table + '" sd '
                    'ON sd.detail = d.id '
                'INNER JOIN "' + NotebookLine._table + '" nl '
                    'ON sd.notebook_line = nl.id '
                'INNER JOIN "' + EntryDetailAnalysis._table + '" ad '
                    'ON nl.analysis_detail = ad.id '
            'WHERE d.planification = %s' +
            exclude_relateds_clause,
            (planification_id,))
        for x in cursor.fetchall():
            cursor.execute('SELECT t.id '
                'FROM "' + Template._table + '" t '
                    'INNER JOIN "' + TemplateAnalysis._table + '" ta '
                    'ON t.id = ta.template '
                'WHERE t.active IS TRUE '
                    'AND ta.analysis = %s '
                    'AND (ta.method = %s OR ta.method IS NULL)',
                (x[1], x[2]))
            template = cursor.fetchone()
            t = template and template[0] or None
            f = x[0]
            if (f, t) not in details4:
                details4[(f, t)] = {
                    'fraction': f,
                    'template': t,
                    'service_ids': [],
                    }
            details4[(f, t)]['service_ids'].append(x[3])

        to_create = []
        for d in details4.values():
            services = Service.browse(list(set(d['service_ids'])))
            to_create.append({
                'session_id': self._session_id,
                'fraction': d['fraction'],
                'template': d['template'],
                'services_list': ' // '.join(
                    s.analysis.rec_name for s in services),
                })
        return RelateTechniciansDetail4.create(to_create)

    def _get_details(self, planification_id):
        details = super()._get_details(planification_id)
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
                if res[0] not in template_analysis:
                    template_analysis[res[0]] = []
                if res[1]:
                    template_analysis[res[0]].append(res[1])
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
                        x[2] not in template_analysis[x[1]]):
                    continue
                details.append(x[0])

        return PlanificationServiceDetail.browse(details)


class LaboratoryProfessional(metaclass=PoolMeta):
    __name__ = 'lims.laboratory.professional'

    sheets_queue = fields.Function(fields.Integer('# Sheets in queue'),
        'get_professional')
    sheets_process = fields.Function(fields.Integer('# Sheets in process'),
        'get_professional')
    samples_qty = fields.Function(fields.Integer('# Samples'),
        'get_professional')

    @classmethod
    def get_professional(cls, records, name):
        pool = Pool()
        Sheet = pool.get('lims.analysis_sheet')

        res = defaultdict(int)
        clause = [('state', 'in', ['draft', 'active'])]

        context = Transaction().context
        if context.get('laboratory'):
            clause.append(('laboratory', '=', context.get('laboratory')))
        if context.get('from_date'):
            clause.append(('date', '>=', datetime.combine(
                context.get('from_date'), time(0, 0))))
        if context.get('to_date'):
            clause.append(('date', '<=', datetime.combine(
                context.get('to_date'), time(23, 59))))

        sheets = Sheet.search(clause)
        for sheet in sheets:
            if name == 'sheets_queue' and sheet.state == 'draft':
                res[sheet.professional.id] += 1
            if name == 'sheets_process' and sheet.state == 'active':
                res[sheet.professional.id] += 1
            if name == 'samples_qty':
                res[sheet.professional.id] += sheet.samples_qty
        return res


class PlanificationProfessional(ModelSQL, ModelView):
    'Planification Professional'
    __name__ = 'lims.planification.professional'

    name = fields.Char('Name')
    sheets_queue = fields.Function(fields.Integer('# Sheets in queue'),
        'get_professional', searcher='search_professional')
    sheets_process = fields.Function(fields.Integer('# Sheets in process'),
        'get_professional', searcher='search_professional')
    samples_qty = fields.Function(fields.Integer('# Samples'),
        'get_professional', searcher='search_professional')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order.insert(0, ('name', 'ASC'))

    @classmethod
    def table_query(cls):
        pool = Pool()
        Professional = pool.get('lims.laboratory.professional')
        Party = pool.get('party.party')
        professional = Professional.__table__()
        party = Party.__table__()
        columns = []
        for fname, field in cls._fields.items():
            if hasattr(field, 'set'):
                continue
            if fname == 'name':
                column = Column(party, 'name').as_(fname)
            else:
                column = Column(professional, fname).as_(fname)
            columns.append(column)
        return professional.join(
            party, condition=professional.party == party.id).select(*columns)

    @classmethod
    def get_professional(cls, records, name):
        pool = Pool()
        Professional = pool.get('lims.laboratory.professional')

        professionals = Professional.browse(records)
        return {p.id: getattr(p, name) for p in professionals}

    @classmethod
    def search_professional(cls, name, domain):
        pool = Pool()
        Professional = pool.get('lims.laboratory.professional')

        professionals = Professional.search([], order=[])

        _, operator_, operand = domain
        operator_ = {
            '=': operator.eq,
            '>=': operator.ge,
            '>': operator.gt,
            '<=': operator.le,
            '<': operator.lt,
            '!=': operator.ne,
            'in': lambda v, l: v in l,
            'not in': lambda v, l: v not in l,
            }.get(operator_, lambda v, l: False)

        ids = [p.id for p in professionals
            if operator_(getattr(p, name), operand)]
        return [('id', 'in', ids)]

    def get_rec_name(self, name):
        return self.name


class PlanificationProfessionalContext(ModelView):
    'Planification Professional Context'
    __name__ = 'lims.planification.professional.context'
    laboratory = fields.Many2One('lims.laboratory', 'Laboratory')
    from_date = fields.Date("From Date",
        domain=[
            If(Eval('to_date') & Eval('from_date'),
                ('from_date', '<=', Eval('to_date')),
                ()),
            ])
    to_date = fields.Date("To Date",
        domain=[
            If(Eval('from_date') & Eval('to_date'),
                ('to_date', '>=', Eval('from_date')),
                ()),
            ])

    @classmethod
    def default_laboratory(cls):
        return Transaction().context.get('laboratory')

    @classmethod
    def default_from_date(cls):
        return Transaction().context.get('from_date')

    @classmethod
    def default_to_date(cls):
        return Transaction().context.get('to_date')


class PlanificationProfessionalLine(ModelSQL, ModelView):
    'Planification Professional Line'
    __name__ = 'lims.planification.professional.line'

    template = fields.Many2One('lims.template.analysis_sheet', 'Template')
    laboratory = fields.Many2One('lims.laboratory', 'Laboratory')
    professional = fields.Many2One('lims.laboratory.professional',
        'Professional')
    date = fields.Date('Date')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('validated', 'Validated'),
        ('done', 'Done'),
        ], 'State')
    samples_qty = fields.Function(fields.Integer('# Samples'),
        'get_fields')
    completion_percentage = fields.Function(fields.Numeric('Complete',
        digits=(1, 4), domain=[
            ('completion_percentage', '>=', 0),
            ('completion_percentage', '<=', 1),
            ]),
        'get_fields')
    color = fields.Function(fields.Char('Color'), 'get_color')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order.insert(0, ('date', 'ASC'))

    @classmethod
    def table_query(cls):
        pool = Pool()
        Sheet = pool.get('lims.analysis_sheet')
        Compilation = pool.get('lims.interface.compilation')
        sheet = Sheet.__table__()
        compilation = Compilation.__table__()

        context = Transaction().context
        where = Literal(True)
        if context.get('laboratory'):
            where &= sheet.laboratory == context.get('laboratory')
        if context.get('from_date'):
            where &= compilation.date_time >= datetime.combine(
                context.get('from_date'), time(0, 0))
        if context.get('to_date'):
            where &= compilation.date_time <= datetime.combine(
                context.get('to_date'), time(23, 59))

        columns = []
        for fname, field in cls._fields.items():
            if hasattr(field, 'set'):
                continue
            if fname == 'date':
                column = Cast(compilation.date_time, 'date').as_(fname)
            else:
                column = Column(sheet, fname).as_(fname)
            columns.append(column)
        return sheet.join(compilation,
            condition=sheet.compilation == compilation.id).select(*columns,
            where=where)

    @classmethod
    def get_fields(cls, records, name):
        pool = Pool()
        Sheet = pool.get('lims.analysis_sheet')

        sheets = Sheet.browse(records)
        return {s.id: getattr(s, name) for s in sheets}

    def get_color(self, name):
        return 'lightblue'


class OpenSheetSample(Wizard):
    'Open Sheet Sample'
    __name__ = 'lims.planification.professional.open_sheet_sample'
    start_state = 'open_'
    open_ = StateAction('lims.act_lims_sample_list')

    def do_open_(self, action):
        pool = Pool()
        Sheet = pool.get('lims.analysis_sheet')
        Data = pool.get('lims.interface.data')

        sheet = Sheet(Transaction().context['active_id'])

        with Transaction().set_context(
                lims_interface_table=sheet.compilation.table.id):
            lines = Data.search([('compilation', '=', sheet.compilation.id)])
            samples = []
            for line in lines:
                nl = line.notebook_line
                if not nl:
                    continue
                if nl.sample.id not in samples:
                    samples.append(nl.sample.id)

        action['pyson_domain'] = [
            ('id', 'in', samples),
            ]
        action['pyson_domain'] = PYSONEncoder().encode(action['pyson_domain'])
        return action, {}


class SamplesPendingPlanning(ModelSQL, ModelView):
    'Samples Pending Planning'
    __name__ = 'lims.sample_pending_planning'

    name = fields.Char('Name')
    samples_qty = fields.Function(fields.Integer('# Samples'),
        'get_samples_qty')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order.insert(0, ('name', 'ASC'))

    @classmethod
    def table_query(cls):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        PlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')
        PlanificationDetail = pool.get('lims.planification.detail')
        Planification = pool.get('lims.planification')
        NotebookLine = pool.get('lims.notebook.line')
        Notebook = pool.get('lims.notebook')
        Fraction = pool.get('lims.fraction')
        Sample = pool.get('lims.sample')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        Analysis = pool.get('lims.analysis')
        TemplateAnalysis = pool.get('lims.template.analysis_sheet.analysis')
        Template = pool.get('lims.template.analysis_sheet')
        template = Template.__table__()

        context = Transaction().context

        cursor.execute('SELECT nl.id '
            'FROM "' + NotebookLine._table + '" nl '
                'INNER JOIN "' + PlanificationServiceDetail._table +
                '" psd ON psd.notebook_line = nl.id '
                'INNER JOIN "' + PlanificationDetail._table + '" pd '
                'ON psd.detail = pd.id '
                'INNER JOIN "' + Planification._table + '" p '
                'ON pd.planification = p.id '
            'WHERE p.state = \'preplanned\' ')
        planned_lines = [x[0] for x in cursor.fetchall()]
        planned_lines_ids = ', '.join(str(x)
            for x in [0] + planned_lines)
        preplanned_where = 'AND nl.id NOT IN (%s) ' % planned_lines_ids

        sql_select = 'SELECT nl.analysis, nl.method, s.product_type, s.matrix '
        sql_from = (
            'FROM "' + NotebookLine._table + '" nl '
            'INNER JOIN "' + Analysis._table + '" nla '
            'ON nla.id = nl.analysis '
            'INNER JOIN "' + Notebook._table + '" n '
            'ON n.id = nl.notebook '
            'INNER JOIN "' + Fraction._table + '" f '
            'ON f.id = n.fraction '
            'INNER JOIN "' + Sample._table + '" s '
            'ON s.id = f.sample '
            'INNER JOIN "' + EntryDetailAnalysis._table + '" ad '
            'ON ad.id = nl.analysis_detail ')
        sql_where = (
            'WHERE ad.plannable = TRUE '
            'AND nl.start_date IS NULL '
            'AND nl.annulled = FALSE '
            'AND nla.behavior != \'internal_relation\' ' +
            preplanned_where)
        params = []

        if context.get('laboratory'):
            sql_where += 'AND nl.laboratory = %s '
            params.append(context.get('laboratory'))
        if context.get('department'):
            sql_where += 'AND nl.department = %s '
            params.append(context.get('department'))
        if context.get('date_from'):
            sql_where += 'AND ad.confirmation_date::date >= %s::date '
            params.append(context.get('date_from'))
        if context.get('date_to'):
            sql_where += 'AND ad.confirmation_date::date <= %s::date '
            params.append(context.get('date_to'))

        with Transaction().set_user(0):
            cursor.execute(sql_select + sql_from + sql_where, tuple(params))
        notebook_lines = cursor.fetchall()

        result = []
        for nl in notebook_lines:
            cursor.execute('SELECT t.id '
                'FROM "' + Template._table + '" t '
                    'INNER JOIN "' + TemplateAnalysis._table + '" ta '
                    'ON t.id = ta.template '
                'WHERE t.active IS TRUE '
                    'AND ta.analysis = %s '
                    'AND (ta.method = %s OR ta.method IS NULL) '
                    'AND (ta.product_type = %s OR ta.product_type IS NULL) '
                    'AND (ta.matrix = %s OR ta.matrix IS NULL)',
                (nl[0], nl[1], nl[2], nl[3]))
            template_id = cursor.fetchone()
            if template_id:
                result.append(template_id[0])
        template_ids = list(set(result))

        where = (template.id.in_(template_ids))
        if not template_ids:
            where = (template.id == -1)
        columns = []
        for fname, field in cls._fields.items():
            if hasattr(field, 'set'):
                continue
            columns.append(Column(template, fname).as_(fname))
        return template.select(*columns, where=where)

    @classmethod
    def get_samples_qty(cls, records, name):
        pool = Pool()
        Template = pool.get('lims.template.analysis_sheet')

        context = Transaction().context
        with Transaction().set_context(
                date_from=context.get('date_from') or datetime.min,
                date_to=context.get('date_to') or datetime.max,
                laboratory=context.get('laboratory'),
                department=context.get('department')):
            templates = Template.browse(records)
        return {t.id: getattr(t, 'pending_fractions') for t in templates}

    def get_rec_name(self, name):
        return self.name


class SamplesPendingPlanningContext(ModelView):
    'Samples Pending Planning Context'
    __name__ = 'lims.sample_pending_planning.context'

    laboratory = fields.Many2One('lims.laboratory', 'Laboratory')
    department = fields.Many2One('company.department', 'Department')
    date_from = fields.Date("From Date",
        domain=[
            If(Eval('date_to') & Eval('date_from'),
                ('date_from', '<=', Eval('date_to')),
                ()),
            ])
    date_to = fields.Date("To Date",
        domain=[
            If(Eval('date_from') & Eval('date_to'),
                ('date_to', '>=', Eval('date_from')),
                ()),
            ])

    @classmethod
    def default_laboratory(cls):
        return Transaction().context.get('laboratory')

    @classmethod
    def default_date_from(cls):
        return Transaction().context.get('date_from')

    @classmethod
    def default_date_to(cls):
        return Transaction().context.get('date_to')


class OpenPendingPlanningSample(Wizard):
    'Open Pending Planning Sample'
    __name__ = 'lims.sample_pending_planning.open_sample'

    start_state = 'open_'
    open_ = StateAction('lims.act_lims_sample_list')

    def do_open_(self, action):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Template = pool.get('lims.template.analysis_sheet')
        PlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')
        PlanificationDetail = pool.get('lims.planification.detail')
        Planification = pool.get('lims.planification')
        NotebookLine = pool.get('lims.notebook.line')
        Notebook = pool.get('lims.notebook')
        Fraction = pool.get('lims.fraction')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        Analysis = pool.get('lims.analysis')

        context = Transaction().context
        template = Template(context['active_id'])
        template_analysis = {}
        for analysis in template.analysis:
            if analysis.analysis.id not in template_analysis:
                template_analysis[analysis.analysis.id] = []
            if analysis.method:
                template_analysis[analysis.analysis.id].append(
                    analysis.method.id)

        cursor.execute('SELECT nl.id '
            'FROM "' + NotebookLine._table + '" nl '
                'INNER JOIN "' + PlanificationServiceDetail._table +
                '" psd ON psd.notebook_line = nl.id '
                'INNER JOIN "' + PlanificationDetail._table + '" pd '
                'ON psd.detail = pd.id '
                'INNER JOIN "' + Planification._table + '" p '
                'ON pd.planification = p.id '
            'WHERE p.state = \'preplanned\' ')
        planned_lines = [x[0] for x in cursor.fetchall()]
        planned_lines_ids = ', '.join(str(x)
            for x in [0] + planned_lines)
        preplanned_where = 'AND nl.id NOT IN (%s) ' % planned_lines_ids

        analysis_ids = ', '.join(str(x) for x in template_analysis.keys())
        sql_select = 'SELECT nl.analysis, nl.method, frc.sample '
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
            'AND nl.analysis IN (' + analysis_ids + ') '
            'AND nl.annulled = FALSE '
            'AND nla.behavior != \'internal_relation\' ' +
            preplanned_where)
        params = []

        if context.get('laboratory'):
            sql_where += 'AND nl.laboratory = %s '
            params.append(context.get('laboratory'))
        if context.get('department'):
            sql_where += 'AND nl.department = %s '
            params.append(context.get('department'))
        if context.get('date_from'):
            sql_where += 'AND ad.confirmation_date::date >= %s::date '
            params.append(context.get('date_from'))
        if context.get('date_to'):
            sql_where += 'AND ad.confirmation_date::date <= %s::date '
            params.append(context.get('date_to'))

        with Transaction().set_user(0):
            cursor.execute(sql_select + sql_from + sql_where, tuple(params))
        notebook_lines = cursor.fetchall()

        result = []
        for nl in notebook_lines:
            if (template_analysis[nl[0]] and
                    nl[1] not in template_analysis[nl[0]]):
                continue
            result.append(nl[2])
        samples = list(set(result))

        action['pyson_domain'] = [
            ('id', 'in', samples),
            ]
        action['pyson_domain'] = PYSONEncoder().encode(action['pyson_domain'])
        action['name'] += ' (%s)' % template.rec_name
        return action, {}
