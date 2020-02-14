# This file is part of lims_analysis_sheet module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateTransition, StateView, Button
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction

__all__ = ['Planification', 'SearchAnalysisSheetStart',
    'SearchAnalysisSheetNext', 'SearchAnalysisSheet']


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


class SearchAnalysisSheetStart(ModelView):
    'Search Analysis Sheets'
    __name__ = 'lims.planification.search_analysis_sheet.start'

    templates = fields.Many2Many('lims.template.analysis_sheet',
        None, None, 'Templates', depends=['templates_domain'],
        domain=[('id', 'in', Eval('templates_domain'))], required=True)
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
            }

    def _get_templates(self, planification):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        PlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')
        NotebookLine = pool.get('lims.notebook.line')
        Notebook = pool.get('lims.notebook')
        Fraction = pool.get('lims.fraction')
        FractionType = pool.get('lims.fraction.type')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        Analysis = pool.get('lims.analysis')
        TemplateAnalysis = pool.get('lims.template.analysis_sheet.analysis')

        planification_details = PlanificationServiceDetail.search(['OR',
            ('planification.state', '=', 'preplanned'),
            ('planification', '=', planification.id),
            ])
        planned_lines = [pd.notebook_line.id for pd in planification_details
            if pd.notebook_line]
        planned_lines_ids = ', '.join(str(x) for x in [0] + planned_lines)

        sql_select = 'SELECT nl.analysis, nl.method '

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
            'ON ad.id = nl.analysis_detail ')

        sql_where = (
            'WHERE nl.planification IS NULL '
            'AND nl.annulled = FALSE '
            'AND ft.plannable = TRUE '
            'AND nl.id NOT IN (' + planned_lines_ids + ') '
            'AND nl.laboratory = %s '
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
                'product_type': v['product_type'],
                'matrix': v['matrix'],
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
            'AND (nb.fraction, nl.analysis) IN (' + records_ids_added + ') ')

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
        FractionType = pool.get('lims.fraction.type')
        Sample = pool.get('lims.sample')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
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

        if extra_where:
            sample_select = ''
            sample_from = ''
            repetition_select = ''
        else:
            sample_select = ', smp.product_type, smp.matrix'
            sample_from = (
                'INNER JOIN "' + Sample._table + '" smp '
                'ON smp.id = frc.sample ')
            repetition_select = ', nl.repetition != 0'

        sql_select = ('SELECT nl.id, nb.fraction, nl.analysis, nl.method' +
            sample_select + repetition_select + ' ')

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
            'ON ad.id = nl.analysis_detail ' +
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
            'ORDER BY nb.fraction ASC, nl.analysis ASC')

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
                if (template_analysis[nl[2]] and
                        template_analysis[nl[2]] != nl[3]):
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
                if (template_analysis[nl[2]] and
                        template_analysis[nl[2]] != nl[3]):
                    continue
                f_ = nl[1]
                s_ = nl[2]
                result[(f_, s_)] = {
                    'product_type': nl[4],
                    'matrix': nl[5],
                    'repetition': nl[6],
                    }

        return result
