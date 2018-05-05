# -*- coding: utf-8 -*-
# This file is part of lims_project_study_plan module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateView, StateAction, Button
from trytond.report import Report
from trytond.pool import Pool
from trytond.transaction import Transaction

__all__ = ['LimsProjectGLPReport01', 'LimsProjectGLPReport02',
    'LimsProjectGLPReport03PrintStart', 'LimsProjectGLPReport03Print',
    'LimsProjectGLPReport03', 'LimsProjectGLPReport04',
    'LimsProjectGLPReport05PrintStart', 'LimsProjectGLPReport05Print',
    'LimsProjectGLPReport05', 'LimsProjectGLPReport06',
    'LimsProjectGLPReport07', 'LimsProjectGLPReport08',
    'LimsProjectGLPReport09', 'LimsProjectGLPReport10PrintStart',
    'LimsProjectGLPReport10Print', 'LimsProjectGLPReport10',
    'LimsProjectGLPReport11', 'LimsProjectGLPReport12PrintStart',
    'LimsProjectGLPReport12Print', 'LimsProjectGLPReport12',
    'LimsProjectGLPReportStudyPlan', 'LimsProjectGLPReportFinalRP',
    'LimsProjectGLPReportFinalFOR', 'LimsProjectGLPReportAnalyticalPhase',
    'LimsProjectGLPReport13']


class LimsProjectGLPReport01(Report):
    'GLP-005- Annex 3 Temporary input and output of samples to the file'
    __name__ = 'lims.project.glp_report.01'

    @classmethod
    def execute(cls, ids, data):
        LimsProject = Pool().get('lims.project')
        if len(ids) > 1:
            LimsProject.raise_user_error('not_glp')

        project = LimsProject(ids[0])
        if project.type != 'study_plan':
            LimsProject.raise_user_error('not_glp')

        return super(LimsProjectGLPReport01, cls).execute(ids, data)

    @classmethod
    def get_context(cls, records, data):
        LimsProjectSampleInCustody = Pool().get(
            'lims.project.sample_in_custody')

        report_context = super(LimsProjectGLPReport01, cls).get_context(
            records, data)

        report_context['company'] = report_context['user'].company
        report_context['stp_number'] = records[0].stp_number
        report_context['stp_sponsor'] = (records[0].stp_sponsor.code if
            records[0].stp_sponsor else '')
        report_context['stp_matrix'] = records[0].stp_matrix_client_description
        report_context['stp_product_brand'] = records[0].stp_product_brand
        report_context['code'] = records[0].code

        samples = LimsProjectSampleInCustody.search([
            ('project', '=', records[0].id),
            ('location', '!=', None),
            ])

        objects = {}
        for sample in samples:
            if sample.location.id not in objects:
                objects[sample.location.id] = {
                    'location': sample.location.rec_name,
                    'samples': [],
                    }
            objects[sample.location.id]['samples'].append({
                'entry_date': sample.entry_date,
                'processing_state': sample.processing_state_string,
                'temperature': sample.temperature_string,
                'packages': '%s %s' % (sample.packages_quantity or '',
                    sample.package_type.description if sample.package_type
                    else ''),
                'comments': unicode(sample.comments or ''),
                'entry_responsible': (sample.entry_responsible.rec_name
                    if sample.entry_responsible else ''),
                'file_operator_responsible': (
                    sample.file_operator_responsible.rec_name
                    if sample.file_operator_responsible else ''),
                })
        report_context['objects'] = objects

        return report_context


class LimsProjectGLPReport02(Report):
    'GLP-005- Annex 4 Definitive input and output of samples to analyze'
    __name__ = 'lims.project.glp_report.02'

    @classmethod
    def execute(cls, ids, data):
        LimsProject = Pool().get('lims.project')
        if len(ids) > 1:
            LimsProject.raise_user_error('not_glp')

        project = LimsProject(ids[0])
        if project.type != 'study_plan':
            LimsProject.raise_user_error('not_glp')

        return super(LimsProjectGLPReport02, cls).execute(ids, data)

    @classmethod
    def get_context(cls, records, data):
        LimsFraction = Pool().get('lims.fraction')

        report_context = super(LimsProjectGLPReport02, cls).get_context(
            records, data)

        report_context['company'] = report_context['user'].company
        report_context['stp_number'] = records[0].stp_number
        report_context['min_qty_sample_compliance'] = \
            records[0].min_qty_sample_compliance_string
        report_context['min_qty_sample'] = records[0].min_qty_sample
        report_context['stp_sponsor'] = (records[0].stp_sponsor.code if
            records[0].stp_sponsor else '')
        report_context['stp_matrix'] = records[0].stp_matrix_client_description
        report_context['stp_product_brand'] = records[0].stp_product_brand
        report_context['project_comments'] = records[0].comments
        report_context['code'] = records[0].code
        report_context['balance_name'] = ''

        fractions = LimsFraction.search([
            ('sample.entry.project', '=', records[0].id),
            ], order=[('number', 'ASC')])

        objects = {}
        for fraction in fractions:
            report_context['balance_name'] = (
                fractions[0].sample.balance.rec_name if
                fractions[0].sample.balance else '')
            if fraction.storage_location.id not in objects:
                objects[fraction.storage_location.id] = {
                    'location': fraction.storage_location.rec_name,
                    'samples': [],
                    }

            objects[fraction.storage_location.id]['samples'].append({
                'number': fraction.get_formated_number('pt-m-sy-sn-fn'),
                'packages': '%s %s' % (fraction.packages_quantity or '',
                    fraction.package_type.description if fraction.package_type
                    else ''),
                'entry_date': fraction.sample.date2,
                'label': fraction.sample.label,
                'sample_weight': fraction.sample.sample_weight,
                'comments': unicode(fraction.comments or '')
                })

        report_context['objects'] = objects
        return report_context


class LimsProjectGLPReport03PrintStart(ModelView):
    'GLP-005- Annex 5 Storage of samples'
    __name__ = 'lims.project.glp_report.03.print.start'

    project = fields.Many2One('lims.project', 'Project', readonly=True)
    report_date_from = fields.Date('Report date from', required=True)
    report_date_to = fields.Date('to', required=True)


class LimsProjectGLPReport03Print(Wizard):
    'GLP-005- Annex 5 Storage of samples'
    __name__ = 'lims.project.glp_report.03.print'

    start = StateView('lims.project.glp_report.03.print.start',
        'lims_project_study_plan.report_glp_03_print_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print', 'print_', 'tryton-print', default=True),
            ])
    print_ = StateAction('lims_project_study_plan.report_glp_03')

    def default_start(self, fields):
        return {
            'project': Transaction().context['active_id'],
            }

    def do_print_(self, action):
        data = {
            'id': self.start.project.id,
            'report_date_from': self.start.report_date_from,
            'report_date_to': self.start.report_date_to,
            }
        return action, data


class LimsProjectGLPReport03(Report):
    'GLP-005- Annex 5 Storage of samples'
    __name__ = 'lims.project.glp_report.03'

    @classmethod
    def execute(cls, ids, data):
        LimsProject = Pool().get('lims.project')

        project = LimsProject(data['id'])
        if project.type != 'study_plan':
            LimsProject.raise_user_error('not_glp')

        return super(LimsProjectGLPReport03, cls).execute(ids, data)

    @classmethod
    def get_context(cls, records, data):
        pool = Pool()
        LimsProject = pool.get('lims.project')
        LimsFraction = pool.get('lims.fraction')

        report_context = super(LimsProjectGLPReport03, cls).get_context(
            records, data)

        project = LimsProject(data['id'])

        report_context['company'] = report_context['user'].company
        report_context['stp_number'] = project.stp_number
        report_context['report_date_from'] = data['report_date_from']
        report_context['report_date_to'] = data['report_date_to']
        report_context['stp_code'] = project.code
        fractions = LimsFraction.search([
            ('sample.entry.project', '=', project.id),
            ('countersample_date', '>=',
                data['report_date_from']),
            ('countersample_date', '<=',
                data['report_date_to']),
            ], order=[('number', 'ASC')])

        objects = []
        for fraction in fractions:

            objects.append({
                'number': fraction.get_formated_number('pt-m-sy-sn-fn'),
                'type': fraction.type.code,
                'packages': '%s %s' % (fraction.packages_quantity or '',
                    fraction.package_type.description if fraction.package_type
                    else ''),
                'storage_location': fraction.storage_location.code,
                'entry_date': fraction.sample.date2,
                'countersample_location': (fraction.countersample_location.code
                    if fraction.countersample_location else ''),
                'countersample_date': fraction.countersample_date or '',
                'comments': unicode(fraction.comments or ''),
                })
        report_context['objects'] = objects

        return report_context


class LimsProjectGLPReport04(Report):
    'GLP-005- Annex 6 Movements of countersamples'
    __name__ = 'lims.project.glp_report.04'

    @classmethod
    def execute(cls, ids, data):
        LimsProject = Pool().get('lims.project')
        if len(ids) > 1:
            LimsProject.raise_user_error('not_glp')

        project = LimsProject(ids[0])
        if project.type != 'study_plan':
            LimsProject.raise_user_error('not_glp')

        return super(LimsProjectGLPReport04, cls).execute(ids, data)

    @classmethod
    def get_context(cls, records, data):
        pool = Pool()
        LimsFraction = pool.get('lims.fraction')
        Move = pool.get('stock.move')

        report_context = super(LimsProjectGLPReport04, cls).get_context(
            records, data)

        report_context['company'] = report_context['user'].company
        report_context['stp_number'] = records[0].stp_number
        report_context['stp_sponsor'] = (records[0].stp_sponsor.code if
            records[0].stp_sponsor else '')
        report_context['stp_matrix'] = records[0].stp_matrix_client_description
        report_context['stp_product_brand'] = records[0].stp_product_brand
        report_context['code'] = records[0].code
        fractions = LimsFraction.search([
            ('sample.entry.project', '=', records[0].id),
            ], order=[('number', 'ASC')])

        objects = {}
        for fraction in fractions:
            clause = [
                ('fraction', '=', fraction.id),
                ('effective_date', '>=', fraction.countersample_date),
                ('create_uid', '!=', 0),
                ]
            if fraction.discharge_date:
                clause.append(
                    ('effective_date', '<=', fraction.discharge_date))
            fraction_moves = Move.search(clause, order=[
                ('effective_date', 'ASC'), ('id', 'ASC')])
            if not fraction_moves:
                continue

            current_location = fraction.current_location
            if current_location.id not in objects:
                objects[current_location.id] = {
                    'location': current_location.rec_name,
                    'samples': [],
                    }
            for move in fraction_moves:
                objects[current_location.id]['samples'].append({
                    'number': fraction.get_formated_number('pt-m-sy-sn-fn'),
                    'from_location': move.from_location.rec_name,
                    'to_location': move.to_location.rec_name,
                    'date': move.effective_date,
                    'shipment': move.shipment.number,
                    'responsible': move.create_uid.name,
                    })
        report_context['objects'] = objects

        return report_context


class LimsProjectGLPReport05PrintStart(ModelView):
    'GLP-005- Annex 7 Discharge of samples'
    __name__ = 'lims.project.glp_report.05.print.start'

    project = fields.Many2One('lims.project', 'Project', readonly=True)
    expiry_date_from = fields.Date('Expiry date from', required=True)
    expiry_date_to = fields.Date('to', required=True)


class LimsProjectGLPReport05Print(Wizard):
    'GLP-005- Annex 7 Discharge of samples'
    __name__ = 'lims.project.glp_report.05.print'

    start = StateView('lims.project.glp_report.05.print.start',
        'lims_project_study_plan.report_glp_05_print_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print', 'print_', 'tryton-print', default=True),
            ])
    print_ = StateAction('lims_project_study_plan.report_glp_05')

    def default_start(self, fields):
        return {
            'project': Transaction().context['active_id'],
            }

    def do_print_(self, action):
        data = {
            'id': self.start.project.id,
            'expiry_date_from': self.start.expiry_date_from,
            'expiry_date_to': self.start.expiry_date_to,
            }
        return action, data


class LimsProjectGLPReport05(Report):
    'GLP-005- Annex 7 Discharge of samples'
    __name__ = 'lims.project.glp_report.05'

    @classmethod
    def execute(cls, ids, data):
        LimsProject = Pool().get('lims.project')

        project = LimsProject(data['id'])
        if project.type != 'study_plan':
            LimsProject.raise_user_error('not_glp')

        return super(LimsProjectGLPReport05, cls).execute(ids, data)

    @classmethod
    def get_context(cls, records, data):
        pool = Pool()
        LimsProject = pool.get('lims.project')
        LimsFraction = pool.get('lims.fraction')

        report_context = super(LimsProjectGLPReport05, cls).get_context(
            records, data)

        project = LimsProject(data['id'])

        report_context['company'] = report_context['user'].company
        report_context['stp_number'] = project.stp_number
        report_context['expiry_date_from'] = data['expiry_date_from']
        report_context['expiry_date_to'] = data['expiry_date_to']
        report_context['code'] = project.code
        fractions = LimsFraction.search([
            ('sample.entry.project', '=', project.id),
            ('expiry_date', '>=', data['expiry_date_from']),
            ('expiry_date', '<=', data['expiry_date_to']),
            ], order=[('number', 'ASC')])

        objects = []
        for fraction in fractions:
            objects.append({
                'number': fraction.get_formated_number('pt-m-sy-sn-fn'),
                'type': fraction.type.code,
                'packages': '%s %s' % (fraction.packages_quantity or '',
                    fraction.package_type.description if fraction.package_type
                    else ''),
                'storage_location': fraction.storage_location.code,
                'entry_date': fraction.sample.date2,
                'countersample_location': (fraction.countersample_location.code
                    if fraction.countersample_location else ''),
                'countersample_date': fraction.countersample_date or '',
                'discharge_date': fraction.discharge_date or '',
                'comments': unicode(fraction.comments or ''),
                })
        report_context['objects'] = objects

        return report_context


class LimsProjectGLPReport06(Report):
    'GLP-001- Annex 3 Deviations and amendments of Study plan'
    __name__ = 'lims.project.glp_report.06'

    @classmethod
    def execute(cls, ids, data):
        LimsProject = Pool().get('lims.project')
        if len(ids) > 1:
            LimsProject.raise_user_error('not_glp')

        project = LimsProject(ids[0])
        if project.type != 'study_plan':
            LimsProject.raise_user_error('not_glp')

        return super(LimsProjectGLPReport06, cls).execute(ids, data)

    @classmethod
    def get_context(cls, records, data):
        pool = Pool()
        ProjectDevAndAmndmnt = pool.get(
            'lims.project.deviation_amendment')
        ProjectDevAndAmndmntProfessional = pool.get(
            'lims.project.deviation_amendment.professional')

        report_context = super(LimsProjectGLPReport06, cls).get_context(
            records, data)

        report_context['company'] = report_context['user'].company
        report_context['stp_number'] = records[0].stp_number
        report_context['stp_title'] = records[0].stp_title
        report_context['code'] = records[0].code

        devs_amnds = ProjectDevAndAmndmnt.search([
            ('project', '=', records[0].id),
            ], order=[('date', 'ASC')])

        objects = []
        for dev_amnd in devs_amnds:
            professionals = ProjectDevAndAmndmntProfessional.search([
                ('deviation_amendment', '=', dev_amnd.id),
                ])
            objects.append({
                'type_number': '%s %s' % (dev_amnd.type_string,
                    dev_amnd.number),
                'document_type': dev_amnd.document_type_string,
                'reason': unicode(dev_amnd.reason or ''),
                'description': unicode(dev_amnd.description or ''),
                'professionals': [{
                    'name': p.professional.rec_name,
                    'date': p.date or '',
                    } for p in professionals],
                })
        report_context['objects'] = objects

        return report_context


class LimsProjectGLPReport07(Report):
    'Table 1- Study plan'
    __name__ = 'lims.project.glp_report.07'

    @classmethod
    def execute(cls, ids, data):
        LimsProject = Pool().get('lims.project')
        if len(ids) > 1:
            LimsProject.raise_user_error('not_glp')

        project = LimsProject(ids[0])
        if project.type != 'study_plan':
            LimsProject.raise_user_error('not_glp')

        return super(LimsProjectGLPReport07, cls).execute(ids, data)

    @classmethod
    def get_context(cls, records, data):
        pool = Pool()
        LimsEntry = pool.get('lims.entry')
        LimsFraction = pool.get('lims.fraction')

        report_context = super(LimsProjectGLPReport07, cls).get_context(
            records, data)

        report_context['company'] = report_context['user'].company
        report_context['stp_number'] = records[0].stp_number
        report_context['stp_matrix'] = records[0].stp_matrix_client_description
        report_context['code'] = records[0].code
        entries = LimsEntry.search([
            ('project', '=', records[0].id),
            ], order=[('number', 'ASC')])
        report_context['entries'] = ', '.join(e.number for e in entries)

        fractions = LimsFraction.search([
            ('sample.entry.project', '=', records[0].id),
            ], order=[('number', 'ASC')])

        objects = []
        for fraction in fractions:
            objects.append({
                'number': fraction.get_formated_number('sy-sn-fn'),
                'packages': '%s %s' % (fraction.packages_quantity or '',
                    fraction.package_type.description if fraction.package_type
                    else ''),
                'reception_date': fraction.sample.reception_date,
                'application_date': fraction.sample.application_date,
                'sampling_date': fraction.sample.sampling_date,
                'treatment': fraction.sample.treatment,
                'dosis': fraction.sample.dosis,
                'glp_repetitions': fraction.sample.glp_repetitions,
                'zone': (fraction.sample.cultivation_zone if
                    fraction.sample.cultivation_zone else ''),
                'after_application_days': (
                    fraction.sample.after_application_days),
                'variety': (fraction.sample.variety.description if
                    fraction.sample.variety else ''),
                'label': fraction.sample.label,
                'storage_location': fraction.storage_location.code,
                })
        report_context['objects'] = objects

        return report_context


class LimsProjectGLPReport08(Report):
    'Table 2- Test elements for Final report (RP)'
    __name__ = 'lims.project.glp_report.08'

    @classmethod
    def execute(cls, ids, data):
        LimsProject = Pool().get('lims.project')
        if len(ids) > 1:
            LimsProject.raise_user_error('not_glp')

        project = LimsProject(ids[0])
        if project.type != 'study_plan':
            LimsProject.raise_user_error('not_glp')

        return super(LimsProjectGLPReport08, cls).execute(ids, data)

    @classmethod
    def get_context(cls, records, data):
        pool = Pool()
        LimsEntry = pool.get('lims.entry')
        LimsFraction = pool.get('lims.fraction')

        report_context = super(LimsProjectGLPReport08, cls).get_context(
            records, data)

        report_context['company'] = report_context['user'].company
        report_context['stp_number'] = records[0].stp_number
        report_context['code'] = records[0].code

        entries = LimsEntry.search([
            ('project', '=', records[0].id),
            ], order=[('number', 'ASC')])
        report_context['entries'] = ', '.join(e.number for e in entries)

        fractions = LimsFraction.search([
            ('sample.entry.project', '=', records[0].id),
            ], order=[('number', 'ASC')])

        objects = []
        for fraction in fractions:
            objects.append({
                'number': fraction.get_formated_number('sy-sn-fn'),
                'reception_date': fraction.sample.reception_date,
                'application_date': fraction.sample.application_date,
                'sampling_date': fraction.sample.sampling_date,
                'treatment': fraction.sample.treatment,
                'dosis': fraction.sample.dosis,
                'glp_repetitions': fraction.sample.glp_repetitions,
                'zone': (fraction.sample.cultivation_zone if
                    fraction.sample.cultivation_zone else ''),
                'after_application_days': (
                    fraction.sample.after_application_days),
                'variety': (fraction.sample.variety.description if
                    fraction.sample.variety else ''),
                'label': fraction.sample.label,
                'sample_weight': fraction.sample.sample_weight,
                })
        report_context['objects'] = objects

        return report_context


class LimsProjectGLPReport09(Report):
    'Table 3- Result of Final report'
    __name__ = 'lims.project.glp_report.09'

    @classmethod
    def execute(cls, ids, data):
        LimsProject = Pool().get('lims.project')
        if len(ids) > 1:
            LimsProject.raise_user_error('not_glp')

        project = LimsProject(ids[0])
        if project.type != 'study_plan':
            LimsProject.raise_user_error('not_glp')

        return super(LimsProjectGLPReport09, cls).execute(ids, data)

    @classmethod
    def get_context(cls, records, data):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsFraction = pool.get('lims.fraction')
        LimsService = pool.get('lims.service')
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsResultsReport = pool.get('lims.results_report')
        LimsAnalysis = pool.get('lims.analysis')

        report_context = super(LimsProjectGLPReport09, cls).get_context(
            records, data)

        report_context['company'] = report_context['user'].company
        report_context['stp_number'] = records[0].stp_number
        report_context['code'] = records[0].code

        fractions = LimsFraction.search([
            ('sample.entry.project', '=', records[0].id),
            ], order=[('number', 'ASC')])

        objects = {}
        for fraction in fractions:

            cursor.execute('SELECT DISTINCT(nl.results_report) , '
                'nl.result_modifier, nl.result, a.description '
                'FROM "' + LimsNotebookLine._table + '" nl '
                    'INNER JOIN "' + LimsService._table + '" s '
                    'ON nl.service = s.id '
                'INNER JOIN "' + LimsAnalysis._table + '" a '
                'ON a.id = nl.analysis '
                'WHERE s.fraction = %s '
                    'AND nl.results_report IS NOT NULL '
                'ORDER BY nl.results_report ASC ',
                (fraction.id,))
            res = cursor.fetchall()
            if not res:
                continue

            key = (fraction.sample.variety.id if fraction.sample.variety
                else None)
            if key not in objects:
                objects[key] = {
                    'matrix': records[0].stp_matrix_client_description,
                    'variety': (fraction.sample.variety.description if
                        fraction.sample.variety else ''),
                    'reports': {},
                    }
            for report_id in res:
                if report_id[0] not in objects[key]['reports']:
                    report = LimsResultsReport(report_id[0])
                    objects[key]['reports'][report_id[0]] = {
                        'report_id': report.id,
                        'number': report.number,
                        'zone': (fraction.sample.cultivation_zone if
                        fraction.sample.cultivation_zone else ''),
                        'fractions': [],
                        }

                re = None
                analysis = None
                if report_id[1] == 'eq':
                        re = report_id[2]
                else:
                    if report_id[1] == 'low':
                        re = '< ' + report_id[2]
                    else:
                        if report_id[1] == 'nd':
                            re = report_id[1]
                analysis = report_id[3]

                objects[key]['reports'][report_id[0]]['fractions'].append({
                    'number': fraction.get_formated_number('sy-sn-fn'),
                    'treatment': fraction.sample.treatment,
                    'dosis': fraction.sample.dosis,
                    'glp_repetitions': fraction.sample.glp_repetitions,
                    'after_application_days': (
                        fraction.sample.after_application_days),
                    'sample_weight': fraction.sample.sample_weight,
                    'label': fraction.sample.label,
                    'analysis': analysis if analysis else '',
                    'result': re if re else '',
                    })

        report_context['objects'] = objects

        return report_context


class LimsProjectGLPReport10PrintStart(ModelView):
    'Rector scheme'
    __name__ = 'lims.project.glp_report.10.print.start'

    date_from = fields.Date('Ingress date from', required=True)
    date_to = fields.Date('to', required=True)
    stp_state = fields.Selection([
        ('canceled', 'Canceled'),
        ('finalized', 'Finalized'),
        ('initiated', 'Initiated'),
        ('unfinished', 'Unfinished'),
        ('pending', 'Pending'),
        ('no_status', 'No status'),
        ('requested', 'Requested'),
        ('all', 'All'),
        ], 'State', sort=False, required=True)

    @staticmethod
    def default_stp_state():
        return 'all'


class LimsProjectGLPReport10Print(Wizard):
    'Rector scheme'
    __name__ = 'lims.project.glp_report.10.print'

    start = StateView('lims.project.glp_report.10.print.start',
        'lims_project_study_plan.report_glp_10_print_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print', 'print_', 'tryton-print', default=True),
            ])
    print_ = StateAction('lims_project_study_plan.report_glp_10')

    def do_print_(self, action):
        data = {
            'date_from': self.start.date_from,
            'date_to': self.start.date_to,
            'stp_state': self.start.stp_state,
            }
        return action, data


class LimsProjectGLPReport10(Report):
    'Rector scheme'
    __name__ = 'lims.project.glp_report.10'

    @classmethod
    def get_context(cls, records, data):
        pool = Pool()
        LimsProject = pool.get('lims.project')

        report_context = super(LimsProjectGLPReport10, cls).get_context(
            records, data)

        report_context['company'] = report_context['user'].company
        report_context['date_from'] = data['date_from']
        report_context['date_to'] = data['date_to']
        clause = [
            ('type', '=', 'study_plan'),
            ('stp_date', '>=', data['date_from']),
            ('stp_date', '<=', data['date_to']),
            ]

        if data['stp_state'] in ('canceled', 'finalized', 'initiated',
                'pending', 'requested'):
            clause.append(('stp_state', '=', data['stp_state']))
        elif data['stp_state'] == 'unfinished':
            clause.append([
                ('stp_state', '!=', 'finalized'),
                ('stp_state', '!=', None),
                ('stp_state', '!=', 'canceled')])
        elif data['stp_state'] == 'no_status':
            clause.append(('stp_state', '=', None))

        projects = LimsProject.search(clause)

        objects = []
        for project in projects:
            objects.append({
                'stp_number': project.stp_number,
                'stp_code': project.code,
                'stp_glp': project.stp_glp,
                'stp_sponsor': (project.stp_sponsor.code
                    if project.stp_sponsor else ''),
                'stp_study_director': (project.stp_study_director.rec_name
                    if project.stp_study_director else ''),
                'stp_start_date': project.stp_start_date,
                'stp_end_date': project.stp_end_date,
                'stp_state': project.stp_state_string,
                'stp_proposal_start_date': project.stp_proposal_start_date,
                'stp_proposal_end_date': project.stp_proposal_end_date,
                'stp_product_brand': project.stp_product_brand,
                'stp_implementation_validation': (True if
                    project.stp_implementation_validation ==
                    'implementation_validation' else False),
                'stp_pattern_availability': project.stp_pattern_availability,
                'stp_matrix': project.stp_matrix_client_description,
                'stp_description': project.stp_description,
                'samples': [{
                    'entry_date': s.entry_date,
                    'packages': '%s %s' % (s.packages_quantity or '',
                        s.package_type.description if s.package_type
                        else ''),
                    'comments': unicode(s.comments or ''),
                    } for s in project.stp_samples_in_custody],
                })
        report_context['objects'] = objects

        return report_context


class LimsProjectGLPReport11(Report):
    'Reference/Test elements (FOR)'
    __name__ = 'lims.project.glp_report.11'

    @classmethod
    def execute(cls, ids, data):
        LimsProject = Pool().get('lims.project')
        if len(ids) > 1:
            LimsProject.raise_user_error('not_glp')

        project = LimsProject(ids[0])
        if project.type != 'study_plan':
            LimsProject.raise_user_error('not_glp')

        return super(LimsProjectGLPReport11, cls).execute(ids, data)

    @classmethod
    def get_context(cls, records, data):
        LimsProjectReferenceElement = Pool().get(
            'lims.project.reference_element')

        report_context = super(LimsProjectGLPReport11, cls).get_context(
            records, data)

        report_context['company'] = report_context['user'].company
        report_context['stp_number'] = records[0].stp_number
        report_context['code'] = records[0].code
        report_context['test_objects'] = []
        report_context['reference_objects'] = []

        elements = LimsProjectReferenceElement.search([
            ('project', '=', records[0].id),
            ])

        for element in elements:
            record = {
                'chemical_name': element.chemical_name or '',
                'common_name': element.common_name or '',
                'cas_number': element.cas_number or '',
                'catalog': element.input_product.catalog or '',
                'lot': element.lot.rec_name if element.lot else '',
                'purity_degree': (element.purity_degree.rec_name
                    if element.purity_degree else ''),
                'stability': element.stability or '',
                'homogeneity': element.homogeneity or '',
                'expiration_date': element.expiration_date,
                'reception_date': element.reception_date,
                'formula': element.formula or '',
                'molecular_weight': element.molecular_weight or '',
                'location': (element.location.rec_name if element.location
                    else ''),
                }
            if element.type == 'test':
                report_context['test_objects'].append(record)
            elif element.type == 'reference':
                report_context['reference_objects'].append(record)

        return report_context


class LimsProjectGLPReport12PrintStart(ModelView):
    'Changelog'
    __name__ = 'lims.project.glp_report.12.print.start'

    date_from = fields.Date('Date from', required=True)
    date_to = fields.Date('to', required=True)


class LimsProjectGLPReport12Print(Wizard):
    'Changelog'
    __name__ = 'lims.project.glp_report.12.print'

    start = StateView('lims.project.glp_report.12.print.start',
        'lims_project_study_plan.report_glp_12_print_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print', 'print_', 'tryton-print', default=True),
            ])
    print_ = StateAction('lims_project_study_plan.report_glp_12')

    def do_print_(self, action):
        data = {
            'date_from': self.start.date_from,
            'date_to': self.start.date_to,
            }
        return action, data


class LimsProjectGLPReport12(Report):
    'Changelog'
    __name__ = 'lims.project.glp_report.12'

    @classmethod
    def get_context(cls, records, data):
        pool = Pool()
        LimsProjectChangeLog = pool.get('lims.project.stp_changelog')

        report_context = super(LimsProjectGLPReport12, cls).get_context(
            records, data)

        report_context['company'] = report_context['user'].company
        report_context['date_from'] = data['date_from']
        report_context['date_to'] = data['date_to']

        changelogs = LimsProjectChangeLog.search([
            ('date2', '>=', data['date_from']),
            ('date2', '<=', data['date_to']),
            ], order=[
            ('project', 'ASC'), ('date', 'ASC'),
            ])

        objects = []
        for change in changelogs:
            project = change.project
            objects.append({
                'change_reason': change.reason,
                'change_date': change.date,
                'change_user': change.user.rec_name,
                'stp_number': project.stp_number,
                'stp_code': project.code,
                'stp_title': project.stp_title,
                'stp_sponsor': (project.stp_sponsor.code
                    if project.stp_sponsor else ''),
                'stp_glp': project.stp_glp,
                'stp_matrix': project.stp_matrix_client_description,
                'stp_product_brand': project.stp_product_brand,
                'stp_start_date': project.stp_start_date,
                'stp_end_date': project.stp_end_date,
                'stp_state': project.stp_state_string,
                'stp_proposal_start_date': project.stp_proposal_start_date,
                'stp_proposal_end_date': project.stp_proposal_end_date,
                'stp_rector_scheme_comments': unicode(
                    project.stp_rector_scheme_comments or ''),
                'stp_implementation_validation': (True if
                    project.stp_implementation_validation ==
                    'implementation_validation' else False),
                'stp_pattern_availability': (
                    project.stp_pattern_availability),
                'stp_target': unicode(project.stp_target or ''),
                'stp_description': project.stp_description,
                'stp_test_method': unicode(project.stp_test_method or ''),
                'stp_study_director': (project.stp_study_director.rec_name
                    if project.stp_study_director else ''),
                'stp_facility_director': (
                    project.stp_facility_director.rec_name
                    if project.stp_facility_director else ''),
                'stp_quality_unit': (project.stp_quality_unit.rec_name
                    if project.stp_quality_unit else ''),
                'stp_records': project.stp_records,
                'stp_laboratory_professionals': [{
                    'professional': p.professional.rec_name,
                    'position': p.position.description if p.position else '',
                    } for p in project.stp_laboratory_professionals],
                })

        report_context['objects'] = objects

        return report_context


class LimsProjectGLPReportStudyPlan(Report):
    'BPL Study plan'
    __name__ = 'lims.project.glp_report.study_plan'

    @classmethod
    def execute(cls, ids, data):
        LimsProject = Pool().get('lims.project')
        if len(ids) > 1:
            LimsProject.raise_user_error('not_glp')

        project = LimsProject(ids[0])
        if project.type != 'study_plan':
            LimsProject.raise_user_error('not_glp')

        return super(LimsProjectGLPReportStudyPlan, cls).execute(ids, data)

    @classmethod
    def get_context(cls, records, data):
        report_context = super(LimsProjectGLPReportStudyPlan, cls).get_context(
            records, data)

        project = records[0]

        report_context['company'] = report_context['user'].company
        c = report_context['user'].company.rec_name.split('-')
        company = c[0]
        report_context['company_name'] = company
        report_context['stp_number'] = project.stp_number
        report_context['code'] = project.code
        report_context['stp_title'] = project.stp_title
        report_context['stp_target'] = unicode(project.stp_target or '')
        report_context['stp_description'] = project.stp_description
        report_context['stp_sponsor'] = project.stp_sponsor
        report_context['stp_date'] = project.stp_date
        report_context['stp_reception_date_list'] = ', '.join(
            cls.get_reception_date(project.id))
        report_context['stp_start_date'] = project.stp_start_date
        report_context['stp_proposal_start_date'] = (
            project.stp_proposal_start_date)
        report_context['stp_proposal_end_date'] = project.stp_proposal_end_date
        report_context['stp_test_method'] = unicode(project.stp_test_method
            or '')
        report_context['stp_test_system'] = unicode(project.stp_test_system
            or '')
        report_context['stp_study_director'] = None
        report_context['stp_study_director_date'] = None
        report_context['stp_quality_unit'] = None
        report_context['stp_quality_unit_date'] = None
        report_context['stp_facility_director'] = None
        report_context['stp_facility_director_date'] = None
        report_context['stp_professionals'] = []
        report_context['stp_entry_list'] = ', '.join([
            e.number for e in cls.get_entry_list(project.id)])
        for pp in project.stp_laboratory_professionals:
            report_context['stp_professionals'].append(pp.professional.party)
            if pp.role_study_director:
                report_context['stp_study_director'] = pp.professional.party
                report_context['stp_study_director_date'] = pp.approval_date
            elif pp.role_quality_unit:
                report_context['stp_quality_unit'] = pp.professional.party
                report_context['stp_quality_unit_date'] = pp.approval_date
            elif pp.role_facility_director:
                report_context['stp_facility_director'] = pp.professional.party
                report_context['stp_facility_director_date'] = pp.approval_date

        return report_context

    @staticmethod
    def get_reception_date(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsProjectSampleInCustody = pool.get('lims.project.sample_in_custody')

        cursor.execute('SELECT DISTINCT(psc.entry_date ) '
            'FROM "' + LimsProjectSampleInCustody._table + '" psc '
            'WHERE psc.project = %s ',
            (project_id,))
        return [x[0].strftime("%d/%m/%Y") for x in cursor.fetchall()]

    @staticmethod
    def get_entry_list(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsEntry = pool.get('lims.entry')

        cursor.execute('SELECT DISTINCT(e.id) '
            'FROM "' + LimsEntry._table + '" e '
            'WHERE e.project = %s ',
            (project_id,))
        return LimsEntry.search([
            ('id', 'in', cursor.fetchall()),
            ])


class LimsProjectGLPReportFinalRP(Report):
    'BPL Final Report (RP)'
    __name__ = 'lims.project.glp_report.final_rp'

    @classmethod
    def execute(cls, ids, data):
        LimsProject = Pool().get('lims.project')
        if len(ids) > 1:
            LimsProject.raise_user_error('not_glp')

        project = LimsProject(ids[0])
        if project.type != 'study_plan':
            LimsProject.raise_user_error('not_glp')
        else:
            if project.stp_phase != 'study_plan':
                LimsProject.raise_user_error('not_study_plan')
        return super(LimsProjectGLPReportFinalRP, cls).execute(ids, data)

    @classmethod
    def get_context(cls, records, data):
        report_context = super(LimsProjectGLPReportFinalRP, cls).get_context(
            records, data)

        project = records[0]

        report_context['company'] = report_context['user'].company
        c = report_context['user'].company.rec_name.split('-')
        company = c[0]
        report_context['company_name'] = company
        report_context['stp_title'] = project.stp_title
        report_context['stp_end_date'] = project.stp_end_date
        report_context['stp_number'] = project.stp_number
        report_context['code'] = project.code
        report_context['stp_sponsor'] = project.stp_sponsor
        report_context['stp_samples'] = ', '.join(
            cls.get_fraction(project.id))
        report_context['stp_reference_elements'] = [e for e in
            project.stp_reference_elements if e.type == 'reference']
        report_context['stp_reference_elements_list'] = ', '.join([
            e.common_name or ''
            for e in report_context['stp_reference_elements']])
        report_context['stp_matrix'] = project.stp_matrix_client_description
        report_context['stp_study_director'] = (
            project.stp_study_director.party if project.stp_study_director
            else None)
        report_context['stp_target'] = unicode(project.stp_target or '')
        report_context['stp_description'] = project.stp_description
        report_context['stp_test_elements'] = [e for e in
            project.stp_reference_elements if e.type == 'test']
        report_context['stp_professionals'] = [pp.professional.party
            for pp in project.stp_laboratory_professionals]
        report_context['stp_all_professionals'] = (
            cls.get_laboratory_professionals(project.id))
        report_context['stp_start_date'] = project.stp_start_date
        report_context['stp_experimental_start_date'] = (
            cls.get_experimental_start_date(project.id))
        report_context['stp_experimental_end_date'] = (
            cls.get_experimental_end_date(project.id))
        report_context['stp_lims_sample_input'] = (
            cls.get_lims_sample_input(project.id))
        report_context['stp_test_method'] = unicode(project.stp_test_method
            or '')
        report_context['stp_solvents_and_reagents'] = (
            project.stp_solvents_and_reagents)
        report_context['stp_results_reports_list'] = ', '.join([
            r.number for r in cls.get_results_reports(project.id)])
        report_context['stp_deviation_and_amendment'] = (
            project.stp_deviation_and_amendment)
        report_context['stp_reception_date_list'] = ', '.join(
            cls.get_reception_date(project.id))

        return report_context

    @staticmethod
    def get_experimental_start_date(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsPlanification = pool.get('lims.planification')
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsService = pool.get('lims.service')
        LimsFraction = pool.get('lims.fraction')
        LimsSample = pool.get('lims.sample')
        LimsEntry = pool.get('lims.entry')

        cursor.execute('SELECT MIN(p.start_date) '
            'FROM "' + LimsPlanification._table + '" p '
                'INNER JOIN "' + LimsNotebookLine._table + '" nl '
                'ON nl.planification = p.id '
                'INNER JOIN "' + LimsService._table + '" srv '
                'ON nl.service = srv.id '
                'INNER JOIN "' + LimsFraction._table + '" f '
                'ON srv.fraction = f.id '
                'INNER JOIN "' + LimsSample._table + '" s '
                'ON f.sample = s.id '
                'INNER JOIN "' + LimsEntry._table + '" e '
                'ON s.entry = e.id '
            'WHERE e.project = %s '
                'AND nl.results_report IS NOT NULL',
            (project_id,))
        return cursor.fetchone()[0]

    @staticmethod
    def get_experimental_end_date(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsService = pool.get('lims.service')
        LimsFraction = pool.get('lims.fraction')
        LimsSample = pool.get('lims.sample')
        LimsEntry = pool.get('lims.entry')

        cursor.execute('SELECT MAX(nl.end_date) '
            'FROM "' + LimsNotebookLine._table + '" nl '
                'INNER JOIN "' + LimsService._table + '" srv '
                'ON nl.service = srv.id '
                'INNER JOIN "' + LimsFraction._table + '" f '
                'ON srv.fraction = f.id '
                'INNER JOIN "' + LimsSample._table + '" s '
                'ON f.sample = s.id '
                'INNER JOIN "' + LimsEntry._table + '" e '
                'ON s.entry = e.id '
            'WHERE e.project = %s '
                'AND nl.results_report IS NOT NULL',
            (project_id,))
        return cursor.fetchone()[0]

    @staticmethod
    def get_results_reports(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsService = pool.get('lims.service')
        LimsFraction = pool.get('lims.fraction')
        LimsSample = pool.get('lims.sample')
        LimsEntry = pool.get('lims.entry')
        LimsResultsReport = pool.get('lims.results_report')

        cursor.execute('SELECT DISTINCT(nl.results_report) '
            'FROM "' + LimsNotebookLine._table + '" nl '
                'INNER JOIN "' + LimsService._table + '" srv '
                'ON nl.service = srv.id '
                'INNER JOIN "' + LimsFraction._table + '" f '
                'ON srv.fraction = f.id '
                'INNER JOIN "' + LimsSample._table + '" s '
                'ON f.sample = s.id '
                'INNER JOIN "' + LimsEntry._table + '" e '
                'ON s.entry = e.id '
            'WHERE e.project = %s '
                'AND nl.results_report IS NOT NULL',
            (project_id,))
        return LimsResultsReport.search([
            ('id', 'in', cursor.fetchall()),
            ])

    @staticmethod
    def get_reception_date(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsProjectSampleInCustody = pool.get('lims.project.sample_in_custody')

        cursor.execute('SELECT DISTINCT(psc.entry_date ) '
            'FROM "' + LimsProjectSampleInCustody._table + '" psc '
            'WHERE psc.project = %s ',
            (project_id,))
        return [x[0].strftime("%d/%m/%Y") for x in cursor.fetchall()]

    @staticmethod
    def get_lims_sample_input(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsPlanification = pool.get('lims.planification')
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsService = pool.get('lims.service')
        LimsFraction = pool.get('lims.fraction')
        LimsSample = pool.get('lims.sample')
        LimsEntry = pool.get('lims.entry')

        cursor.execute('SELECT MIN(srv.confirmation_date) '
            'FROM "' + LimsPlanification._table + '" p '
                'INNER JOIN "' + LimsNotebookLine._table + '" nl '
                'ON nl.planification = p.id '
                'INNER JOIN "' + LimsService._table + '" srv '
                'ON nl.service = srv.id '
                'INNER JOIN "' + LimsFraction._table + '" f '
                'ON srv.fraction = f.id '
                'INNER JOIN "' + LimsSample._table + '" s '
                'ON f.sample = s.id '
                'INNER JOIN "' + LimsEntry._table + '" e '
                'ON s.entry = e.id '
            'WHERE e.project = %s '
                'AND nl.end_date IS NOT NULL',
            (project_id,))
        return cursor.fetchone()[0]

    @classmethod
    def get_laboratory_professionals(cls, project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsLaboratoryProfessionals = pool.get('lims.project.stp_professional')
        LimsPosition = pool.get('lims.project.stp_professional.position')
        LaboratoryProfessional = pool.get('lims.laboratory.professional')
        Party = pool.get('party.party')

        cursor.execute('SELECT  p.description, pa.name '
            'FROM "' + LimsLaboratoryProfessionals._table + '" lp '
                'INNER JOIN "' + LimsPosition._table + '" p '
                'ON lp.position = p.id '
                'INNER JOIN "' + LaboratoryProfessional._table + '" pr '
                'ON lp.professional = pr.id '
                'INNER JOIN "' + Party._table + '" pa '
                'ON pr.party = pa.id '
            'WHERE lp.project = %s ',
            (project_id,))
        professional_lines = {}
        professional_lines = cursor.fetchall()
        res = []
        if professional_lines:
            for line in professional_lines:
                line_p = ['%s: %s' % (line[0], line[1])]
                res.extend(line_p)
        return res

    @staticmethod
    def get_fraction(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsFraction = pool.get('lims.fraction')
        LimsSample = pool.get('lims.sample')
        LimsEntry = pool.get('lims.entry')

        cursor.execute('SELECT f.number '
            'FROM "' + LimsEntry._table + '" e '
                'INNER JOIN "' + LimsSample._table + '" s '
                'ON e.id = s.entry '
                'INNER JOIN "' + LimsFraction._table + '" f '
                'ON s.id = f.sample '
            'WHERE e.project = %s ',
            (project_id,))
        return [x[0] for x in cursor.fetchall()]


class LimsProjectGLPReportFinalFOR(Report):
    'BPL Final Report (FOR)'
    __name__ = 'lims.project.glp_report.final_for'

    @classmethod
    def execute(cls, ids, data):
        LimsProject = Pool().get('lims.project')
        if len(ids) > 1:
            LimsProject.raise_user_error('not_glp')

        project = LimsProject(ids[0])
        if project.type != 'study_plan':
            LimsProject.raise_user_error('not_glp')
        else:
            if project.stp_phase != 'study_plan':
                LimsProject.raise_user_error('not_study_plan')
        return super(LimsProjectGLPReportFinalFOR, cls).execute(ids, data)

    @classmethod
    def get_context(cls, records, data):
        report_context = super(LimsProjectGLPReportFinalFOR, cls).get_context(
            records, data)

        project = records[0]

        report_context['company'] = report_context['user'].company
        c = report_context['user'].company.rec_name.split('-')
        company = c[0]
        report_context['company_name'] = company
        report_context['stp_title'] = project.stp_title
        report_context['stp_end_date'] = project.stp_end_date
        report_context['stp_number'] = project.stp_number
        report_context['stp_sponsor'] = project.stp_sponsor
        report_context['stp_samples'] = ''
        report_context['code'] = project.code
        product_type_matrix = {}
        for s in project.stp_samples:
            if report_context['stp_samples']:
                report_context['stp_samples'] += ', '
            report_context['stp_samples'] += s.number
            key = (s.product_type.id, s.matrix.id)
            if key not in product_type_matrix:
                product_type_matrix[key] = '%s-%s' % (
                    s.product_type.code, s.matrix.code)
        report_context['product_type_matrix_list'] = ', '.join(
            product_type_matrix.values())
        report_context['stp_test_elements'] = [e for e in
            project.stp_reference_elements if e.type == 'test']
        report_context['stp_test_elements_list'] = ', '.join([
            e.common_name or ''
            for e in report_context['stp_test_elements']])
        report_context['stp_analysis_list'] = cls.get_analysis_list(project.id)
        report_context['stp_study_director'] = (
            project.stp_study_director.party if project.stp_study_director
            else None)
        report_context['stp_target'] = unicode(project.stp_target or '')
        report_context['stp_description'] = project.stp_description
        report_context['stp_professionals'] = [pp.professional.party
            for pp in project.stp_laboratory_professionals]
        report_context['stp_start_date'] = project.stp_start_date
        report_context['stp_experimental_start_date'] = (
            cls.get_experimental_start_date(project.id))
        report_context['stp_experimental_end_date'] = (
            cls.get_experimental_end_date(project.id))
        report_context['stp_lims_sample_input'] = (
            cls.get_lims_sample_input(project.id))
        report_context['stp_all_professionals'] = (
            cls.get_laboratory_professionals(project.id))
        report_context['stp_test_method'] = unicode(project.stp_test_method
            or '')
        report_context['stp_reference_elements'] = [e for e in
            project.stp_reference_elements if e.type == 'reference']
        report_context['stp_solvents_and_reagents'] = (
            project.stp_solvents_and_reagents)
        report_context['stp_results_reports_list'] = ', '.join([
            r.number for r in cls.get_results_reports(project.id)])
        report_context['stp_deviation_and_amendment'] = (
            project.stp_deviation_and_amendment)
        report_context['stp_reception_date_list'] = ', '.join(
            cls.get_reception_date(project.id))

        return report_context

    @staticmethod
    def get_analysis_list(project_id):
        LimsEntryDetailAnalysis = Pool().get('lims.entry.detail.analysis')

        analysis = {}
        details = LimsEntryDetailAnalysis.search([
            ('entry.project', '=', project_id),
            ])
        for detail in details:
            if detail.analysis.id not in analysis:
                analysis[detail.analysis.id] = detail.analysis.description
        return ', '.join(analysis.values())

    @staticmethod
    def get_experimental_start_date(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsPlanification = pool.get('lims.planification')
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsService = pool.get('lims.service')
        LimsFraction = pool.get('lims.fraction')
        LimsSample = pool.get('lims.sample')
        LimsEntry = pool.get('lims.entry')

        cursor.execute('SELECT MIN(p.start_date) '
            'FROM "' + LimsPlanification._table + '" p '
                'INNER JOIN "' + LimsNotebookLine._table + '" nl '
                'ON nl.planification = p.id '
                'INNER JOIN "' + LimsService._table + '" srv '
                'ON nl.service = srv.id '
                'INNER JOIN "' + LimsFraction._table + '" f '
                'ON srv.fraction = f.id '
                'INNER JOIN "' + LimsSample._table + '" s '
                'ON f.sample = s.id '
                'INNER JOIN "' + LimsEntry._table + '" e '
                'ON s.entry = e.id '
            'WHERE e.project = %s '
                'AND nl.results_report IS NOT NULL',
            (project_id,))
        return cursor.fetchone()[0]

    @staticmethod
    def get_experimental_end_date(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsService = pool.get('lims.service')
        LimsFraction = pool.get('lims.fraction')
        LimsSample = pool.get('lims.sample')
        LimsEntry = pool.get('lims.entry')

        cursor.execute('SELECT MAX(nl.end_date) '
            'FROM "' + LimsNotebookLine._table + '" nl '
                'INNER JOIN "' + LimsService._table + '" srv '
                'ON nl.service = srv.id '
                'INNER JOIN "' + LimsFraction._table + '" f '
                'ON srv.fraction = f.id '
                'INNER JOIN "' + LimsSample._table + '" s '
                'ON f.sample = s.id '
                'INNER JOIN "' + LimsEntry._table + '" e '
                'ON s.entry = e.id '
            'WHERE e.project = %s '
                'AND nl.results_report IS NOT NULL',
            (project_id,))
        return cursor.fetchone()[0]

    @staticmethod
    def get_results_reports(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsService = pool.get('lims.service')
        LimsFraction = pool.get('lims.fraction')
        LimsSample = pool.get('lims.sample')
        LimsEntry = pool.get('lims.entry')
        LimsResultsReport = pool.get('lims.results_report')

        cursor.execute('SELECT DISTINCT(nl.results_report) '
            'FROM "' + LimsNotebookLine._table + '" nl '
                'INNER JOIN "' + LimsService._table + '" srv '
                'ON nl.service = srv.id '
                'INNER JOIN "' + LimsFraction._table + '" f '
                'ON srv.fraction = f.id '
                'INNER JOIN "' + LimsSample._table + '" s '
                'ON f.sample = s.id '
                'INNER JOIN "' + LimsEntry._table + '" e '
                'ON s.entry = e.id '
            'WHERE e.project = %s '
                'AND nl.results_report IS NOT NULL',
            (project_id,))
        return LimsResultsReport.search([
            ('id', 'in', cursor.fetchall()),
            ])

    @staticmethod
    def get_lims_sample_input(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsPlanification = pool.get('lims.planification')
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsService = pool.get('lims.service')
        LimsFraction = pool.get('lims.fraction')
        LimsSample = pool.get('lims.sample')
        LimsEntry = pool.get('lims.entry')

        cursor.execute('SELECT MIN(srv.confirmation_date) '
            'FROM "' + LimsPlanification._table + '" p '
                'INNER JOIN "' + LimsNotebookLine._table + '" nl '
                'ON nl.planification = p.id '
                'INNER JOIN "' + LimsService._table + '" srv '
                'ON nl.service = srv.id '
                'INNER JOIN "' + LimsFraction._table + '" f '
                'ON srv.fraction = f.id '
                'INNER JOIN "' + LimsSample._table + '" s '
                'ON f.sample = s.id '
                'INNER JOIN "' + LimsEntry._table + '" e '
                'ON s.entry = e.id '
            'WHERE e.project = %s '
                'AND nl.end_date IS NOT NULL',
            (project_id,))
        return cursor.fetchone()[0]

    @staticmethod
    def get_reception_date(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsProjectSampleInCustody = pool.get('lims.project.sample_in_custody')

        cursor.execute('SELECT DISTINCT(psc.entry_date ) '
            'FROM "' + LimsProjectSampleInCustody._table + '" psc '
            'WHERE psc.project = %s ',
            (project_id,))
        return [x[0].strftime("%d/%m/%Y") for x in cursor.fetchall()]

    @classmethod
    def get_laboratory_professionals(cls, project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsLaboratoryProfessionals = pool.get('lims.project.stp_professional')
        LimsPosition = pool.get('lims.project.stp_professional.position')
        LaboratoryProfessional = pool.get('lims.laboratory.professional')
        Party = pool.get('party.party')

        cursor.execute('SELECT  p.description, pa.name '
            'FROM "' + LimsLaboratoryProfessionals._table + '" lp '
                'INNER JOIN "' + LimsPosition._table + '" p '
                'ON lp.position = p.id '
                'INNER JOIN "' + LaboratoryProfessional._table + '" pr '
                'ON lp.professional = pr.id '
                'INNER JOIN "' + Party._table + '" pa '
                'ON pr.party = pa.id '
            'WHERE lp.project = %s ',
            (project_id,))
        professional_lines = {}
        professional_lines = cursor.fetchall()
        res = []
        if professional_lines:
            for line in professional_lines:
                line_p = ['%s: %s' % (line[0], line[1])]
                res.extend(line_p)
        return res


class LimsProjectGLPReportAnalyticalPhase(Report):
    'BPL Analytical Phase Report '
    __name__ = 'lims.project.glp_report.analytical_phase'

    @classmethod
    def execute(cls, ids, data):
        LimsProject = Pool().get('lims.project')
        if len(ids) > 1:
            LimsProject.raise_user_error('not_glp')

        project = LimsProject(ids[0])
        if project.type != 'study_plan':
            LimsProject.raise_user_error('not_glp')
        else:
            if project.stp_phase != 'analytical_phase':
                LimsProject.raise_user_error('not_analytical_phase')
        return super(LimsProjectGLPReportAnalyticalPhase,
            cls).execute(ids, data)

    @classmethod
    def get_context(cls, records, data):
        report_context = super(LimsProjectGLPReportAnalyticalPhase,
            cls).get_context(records, data)

        project = records[0]

        report_context['company'] = report_context['user'].company
        c = report_context['user'].company.rec_name.split('-')
        company = c[0]
        report_context['company_name'] = company
        report_context['stp_title'] = project.stp_title
        report_context['stp_end_date'] = project.stp_end_date
        report_context['stp_number'] = project.stp_number
        report_context['code'] = project.code
        report_context['stp_sponsor'] = project.stp_sponsor
        report_context['stp_samples'] = ', '.join(
            cls.get_fraction(project.id))
        report_context['stp_reference_elements'] = [e for e in
            project.stp_reference_elements if e.type == 'reference']
        report_context['stp_reference_elements_list'] = ', '.join([
            e.common_name or ''
            for e in report_context['stp_reference_elements']])
        report_context['stp_matrix'] = project.stp_matrix_client_description
        report_context['stp_study_director'] = (
            project.stp_study_director.party if project.stp_study_director
            else None)
        report_context['stp_target'] = unicode(project.stp_target or '')
        report_context['stp_description'] = project.stp_description
        report_context['stp_test_elements'] = [e for e in
            project.stp_reference_elements if e.type == 'test']
        report_context['stp_professionals'] = [pp.professional.party
            for pp in project.stp_laboratory_professionals]
        report_context['stp_start_date'] = project.stp_start_date
        report_context['stp_experimental_start_date'] = (
            cls.get_experimental_start_date(project.id))
        report_context['stp_experimental_end_date'] = (
            cls.get_experimental_end_date(project.id))
        report_context['stp_lims_sample_input'] = (
            cls.get_lims_sample_input(project.id))
        report_context['stp_all_professionals'] = (
            cls.get_laboratory_professionals(project.id))
        report_context['stp_test_method'] = unicode(project.stp_test_method
            or '')
        report_context['stp_solvents_and_reagents'] = (
            project.stp_solvents_and_reagents)
        report_context['stp_results_reports_list'] = ', '.join([
            r.number for r in cls.get_results_reports(project.id)])
        report_context['stp_deviation_and_amendment'] = (
            project.stp_deviation_and_amendment)
        report_context['stp_reception_date_list'] = ', '.join(
            cls.get_reception_date(project.id))

        return report_context

    @staticmethod
    def get_experimental_start_date(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsPlanification = pool.get('lims.planification')
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsService = pool.get('lims.service')
        LimsFraction = pool.get('lims.fraction')
        LimsSample = pool.get('lims.sample')
        LimsEntry = pool.get('lims.entry')

        cursor.execute('SELECT MIN(p.start_date) '
            'FROM "' + LimsPlanification._table + '" p '
                'INNER JOIN "' + LimsNotebookLine._table + '" nl '
                'ON nl.planification = p.id '
                'INNER JOIN "' + LimsService._table + '" srv '
                'ON nl.service = srv.id '
                'INNER JOIN "' + LimsFraction._table + '" f '
                'ON srv.fraction = f.id '
                'INNER JOIN "' + LimsSample._table + '" s '
                'ON f.sample = s.id '
                'INNER JOIN "' + LimsEntry._table + '" e '
                'ON s.entry = e.id '
            'WHERE e.project = %s '
                'AND nl.results_report IS NOT NULL',
            (project_id,))
        return cursor.fetchone()[0]

    @staticmethod
    def get_experimental_end_date(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsService = pool.get('lims.service')
        LimsFraction = pool.get('lims.fraction')
        LimsSample = pool.get('lims.sample')
        LimsEntry = pool.get('lims.entry')

        cursor.execute('SELECT MAX(nl.end_date) '
            'FROM "' + LimsNotebookLine._table + '" nl '
                'INNER JOIN "' + LimsService._table + '" srv '
                'ON nl.service = srv.id '
                'INNER JOIN "' + LimsFraction._table + '" f '
                'ON srv.fraction = f.id '
                'INNER JOIN "' + LimsSample._table + '" s '
                'ON f.sample = s.id '
                'INNER JOIN "' + LimsEntry._table + '" e '
                'ON s.entry = e.id '
            'WHERE e.project = %s '
                'AND nl.results_report IS NOT NULL',
            (project_id,))
        return cursor.fetchone()[0]

    @staticmethod
    def get_results_reports(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsService = pool.get('lims.service')
        LimsFraction = pool.get('lims.fraction')
        LimsSample = pool.get('lims.sample')
        LimsEntry = pool.get('lims.entry')
        LimsResultsReport = pool.get('lims.results_report')

        cursor.execute('SELECT DISTINCT(nl.results_report) '
            'FROM "' + LimsNotebookLine._table + '" nl '
                'INNER JOIN "' + LimsService._table + '" srv '
                'ON nl.service = srv.id '
                'INNER JOIN "' + LimsFraction._table + '" f '
                'ON srv.fraction = f.id '
                'INNER JOIN "' + LimsSample._table + '" s '
                'ON f.sample = s.id '
                'INNER JOIN "' + LimsEntry._table + '" e '
                'ON s.entry = e.id '
            'WHERE e.project = %s '
                'AND nl.results_report IS NOT NULL',
            (project_id,))
        return LimsResultsReport.search([
            ('id', 'in', cursor.fetchall()),
            ])

    @staticmethod
    def get_lims_sample_input(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsPlanification = pool.get('lims.planification')
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsService = pool.get('lims.service')
        LimsFraction = pool.get('lims.fraction')
        LimsSample = pool.get('lims.sample')
        LimsEntry = pool.get('lims.entry')

        cursor.execute('SELECT MIN(srv.confirmation_date) '
            'FROM "' + LimsPlanification._table + '" p '
                'INNER JOIN "' + LimsNotebookLine._table + '" nl '
                'ON nl.planification = p.id '
                'INNER JOIN "' + LimsService._table + '" srv '
                'ON nl.service = srv.id '
                'INNER JOIN "' + LimsFraction._table + '" f '
                'ON srv.fraction = f.id '
                'INNER JOIN "' + LimsSample._table + '" s '
                'ON f.sample = s.id '
                'INNER JOIN "' + LimsEntry._table + '" e '
                'ON s.entry = e.id '
            'WHERE e.project = %s '
                'AND nl.end_date IS NOT NULL',
            (project_id,))
        return cursor.fetchone()[0]

    @staticmethod
    def get_reception_date(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsProjectSampleInCustody = pool.get('lims.project.sample_in_custody')

        cursor.execute('SELECT DISTINCT(psc.entry_date ) '
            'FROM "' + LimsProjectSampleInCustody._table + '" psc '
            'WHERE psc.project = %s ',
            (project_id,))
        return [x[0].strftime("%d/%m/%Y") for x in cursor.fetchall()]

    @classmethod
    def get_laboratory_professionals(cls, project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsLaboratoryProfessionals = pool.get('lims.project.stp_professional')
        LimsPosition = pool.get('lims.project.stp_professional.position')
        LaboratoryProfessional = pool.get('lims.laboratory.professional')
        Party = pool.get('party.party')

        cursor.execute('SELECT  p.description, pa.name '
            'FROM "' + LimsLaboratoryProfessionals._table + '" lp '
                'INNER JOIN "' + LimsPosition._table + '" p '
                'ON lp.position = p.id '
                'INNER JOIN "' + LaboratoryProfessional._table + '" pr '
                'ON lp.professional = pr.id '
                'INNER JOIN "' + Party._table + '" pa '
                'ON pr.party = pa.id '
            'WHERE lp.project = %s ',
            (project_id,))
        professional_lines = {}
        professional_lines = cursor.fetchall()
        res = []
        if professional_lines:
            for line in professional_lines:
                line_p = ['%s: %s' % (line[0], line[1])]
                res.extend(line_p)
        return res

    @staticmethod
    def get_fraction(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsFraction = pool.get('lims.fraction')
        LimsSample = pool.get('lims.sample')
        LimsEntry = pool.get('lims.entry')

        cursor.execute('SELECT f.number '
            'FROM "' + LimsEntry._table + '" e '
                'INNER JOIN "' + LimsSample._table + '" s '
                'ON e.id = s.entry '
                'INNER JOIN "' + LimsFraction._table + '" f '
                'ON s.id = f.sample '
            'WHERE e.project = %s ',
            (project_id,))
        return [x[0] for x in cursor.fetchall()]


class LimsProjectGLPReport13(Report):
    'GLP 13. GLP-007- Annex 3 Sample preparation registration GLP'
    __name__ = 'lims.project.glp_report.13'

    @classmethod
    def execute(cls, ids, data):
        LimsProject = Pool().get('lims.project')
        if len(ids) > 1:
            LimsProject.raise_user_error('not_glp')

        project = LimsProject(ids[0])
        if project.type != 'study_plan':
            LimsProject.raise_user_error('not_glp')

        return super(LimsProjectGLPReport13, cls).execute(ids, data)

    @classmethod
    def get_context(cls, records, data):
        pool = Pool()
        LimsFraction = pool.get('lims.fraction')

        report_context = super(LimsProjectGLPReport13, cls).get_context(
            records, data)

        report_context['company'] = report_context['user'].company
        report_context['stp_matrix'] = records[0].stp_matrix_client_description
        report_context['code'] = records[0].code
        report_context['stp_reference_objects_list'] = ', '.join([
            r.common_name for r in
            cls.get_reference_objects_list(records[0].id)])
        report_context['stp_test_method'] = records[0].stp_test_method

        fractions = LimsFraction.search([
            ('sample.entry.project', '=', records[0].id),
            ], order=[('number', 'ASC')])

        objects = []
        for fraction in fractions:
            objects.append({
                'number': fraction.get_formated_number('sy-sn-fn'),
                'label': fraction.sample.label,
                'fraction_type': fraction.type.code,
                })
        report_context['objects'] = objects
        return report_context

    @staticmethod
    def get_reference_objects_list(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsReferenceElement = pool.get('lims.project.reference_element')
        LimsEntry = pool.get('lims.entry')

        cursor.execute('SELECT DISTINCT(el.id) '
            'FROM "' + LimsReferenceElement._table + '" el '
                'INNER JOIN "' + LimsEntry._table + '" e '
                'ON el.project = e.project '
            'WHERE e.project = %s ',
            (project_id,))
        return LimsReferenceElement.search([
            ('id', 'in', cursor.fetchall()),
            ])
