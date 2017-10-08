# -*- coding: utf-8 -*-
# This file is part of lims_planification module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateView, StateAction, Button
from trytond.report import Report
from trytond.pool import Pool
from trytond.transaction import Transaction
from datetime import datetime
from dateutil.relativedelta import relativedelta

__all__ = ['LimsPlanificationSequenceReport',
    'LimsPlanificationWorksheetAnalysisReport',
    'LimsPlanificationWorksheetMethodReport',
    'LimsPlanificationWorksheetReport', 'LimsPendingServicesUnplannedReport',
    'LimsPendingServicesUnplannedSpreadsheet', 'PrintBlindSampleReportStart',
    'PrintBlindSampleReport', 'LimsBlindSampleReport',
    'PrintPendingServicesUnplannedReportStart',
    'PrintPendingServicesUnplannedReport',
    'LimsPlanificationSequenceAnalysisReport']


class LimsPlanificationSequenceReport(Report):
    'Sequence'
    __name__ = 'lims.planification.sequence.report'

    @classmethod
    def get_context(cls, records, data):
        report_context = super(LimsPlanificationSequenceReport,
                cls).get_context(records, data)

        report_context['company'] = report_context['user'].company

        objects = {}
        for planification in records:
            if planification.state != 'confirmed':
                continue
            date = str(planification.start_date)
            if date not in objects:
                objects[date] = {
                    'date': planification.start_date,
                    'methods': {},
                    }
            for detail in planification.details:
                fraction = detail.fraction
                for service_detail in detail.details:
                    if (service_detail.notebook_line.analysis.behavior ==
                            'internal_relation'):
                        continue
                    notebook_line = service_detail.notebook_line
                    method_id = notebook_line.method.id
                    if method_id not in objects[date]['methods']:
                        objects[date]['methods'][method_id] = {
                            'method': notebook_line.method.code,
                            'lines': {},
                            }

                    number = fraction.get_formated_number('sn-sy-fn')
                    number = (number + '-' + str(notebook_line.repetition))
                    number_parts = number.split('-')
                    order = (number_parts[1] + '-' + number_parts[0] + '-' +
                        number_parts[2] + '-' + number_parts[3])

                    product_type = fraction.product_type.code
                    matrix = fraction.matrix.code
                    fraction_type = fraction.type.code
                    comments = fraction.comments
                    analysis_origin = notebook_line.analysis_origin
                    priority = notebook_line.priority
                    urgent = notebook_line.urgent
                    trace_report = fraction.sample.trace_report
                    sample_client_description = (
                        fraction.sample.sample_client_description)
                    key = (number, product_type, matrix, fraction_type,
                        analysis_origin, priority, trace_report)
                    if key not in objects[date]['methods'][method_id]['lines']:
                        objects[date]['methods'][method_id]['lines'][key] = {
                            'order': order,
                            'number': number,
                            'product_type': product_type,
                            'matrix': matrix,
                            'fraction_type': fraction_type,
                            'analysis_origin': analysis_origin,
                            'priority': priority,
                            'trace_report': trace_report,
                            'urgent': urgent,
                            'comments': comments,
                            'sample_client_description': (
                                sample_client_description),
                            }

        for k1 in objects.iterkeys():
            for k2, lines in objects[k1]['methods'].iteritems():
                sorted_lines = sorted(lines['lines'].values(),
                    key=lambda x: x['order'])
                objects[k1]['methods'][k2]['lines'] = sorted_lines

        report_context['objects'] = objects

        return report_context


class LimsPlanificationWorksheetAnalysisReport(Report):
    'Worksheet by Analysis'
    __name__ = 'lims.planification.worksheet_analysis.report'

    @classmethod
    def get_context(cls, records, data):
        report_context = super(LimsPlanificationWorksheetAnalysisReport,
                cls).get_context(records, data)

        report_context['company'] = report_context['user'].company

        objects = {}
        for planification in records:
            if planification.state != 'confirmed':
                continue
            date = str(planification.start_date)
            if date not in objects:
                objects[date] = {
                    'date': planification.start_date,
                    'professionals': {},
                    }
            for detail in planification.details:
                fraction = detail.fraction
                for service_detail in detail.details:
                    if not service_detail.notebook_line:
                        continue
                    if (service_detail.notebook_line.analysis.behavior ==
                            'internal_relation'):
                        continue
                    p_key = ()
                    p_names = ''
                    for professional in service_detail.staff_responsible:
                        p_key += (professional.id,)
                        if p_names:
                            p_names += ', '
                        p_names += professional.rec_name
                    if not p_key:
                        continue
                    p_key = tuple(sorted(p_key))
                    if (p_key not in objects[date]['professionals']):
                        objects[date]['professionals'][p_key] = {
                            'professional': p_names,
                            'analysis': {},
                            'total': 0,
                            }
                    notebook_line = service_detail.notebook_line
                    key = (notebook_line.analysis.id, notebook_line.method.id)
                    if (key not in
                            objects[date]['professionals'][p_key]['analysis']):
                        objects[date]['professionals'][p_key]['analysis'][
                            key] = {
                                'order': notebook_line.analysis.order or 9999,
                                'analysis': notebook_line.analysis.rec_name,
                                'method': notebook_line.method.rec_name,
                                'lines': {},
                                }

                    number = fraction.get_formated_number('pt-m-sy-sn-fn')
                    number = (number + '-' + str(notebook_line.repetition))
                    concentration_level = (
                        notebook_line.concentration_level.description if
                        notebook_line.concentration_level else '')
                    if (number in objects[date]['professionals'][p_key][
                            'analysis'][key]['lines']):
                        continue

                    number_parts = number.split('-')
                    order = (number_parts[3] + '-' + number_parts[2] + '-' +
                        number_parts[4] + '-' + number_parts[5])
                    comments = '%s - %s - %s' % (planification.comments or '',
                        notebook_line.service.comments or '',
                        notebook_line.service.fraction.comments or '')
                    record = {
                        'order': order,
                        'number': number,
                        'label': fraction.label,
                        'sample_client_description': (
                            fraction.sample.sample_client_description),
                        'party': fraction.party.code,
                        'storage_location': fraction.storage_location.code,
                        'fraction_type': fraction.type.code,
                        'concentration_level': concentration_level,
                        'device': (notebook_line.device.code if
                            notebook_line.device else None),
                        'urgent': 'SI' if notebook_line.urgent else '',
                        'comments': comments,
                        'planification_code': planification.code,
                        }
                    objects[date]['professionals'][p_key]['analysis'][
                        key]['lines'][number] = record
                    objects[date]['professionals'][p_key]['total'] += 1

        for k1 in objects.iterkeys():
            for k2 in objects[k1]['professionals'].iterkeys():
                sorted_analysis = sorted(objects[k1]['professionals'][k2][
                    'analysis'].items(), key=lambda x: x[1]['order'])
                objects[k1]['professionals'][k2]['analysis'] = []
                for item in sorted_analysis:
                    sorted_lines = sorted(item[1]['lines'].items(),
                            key=lambda x: x[1]['order'])
                    item[1]['lines'] = [l[1] for l in sorted_lines]
                    objects[k1]['professionals'][k2]['analysis'].append(
                        item[1])

        report_context['records'] = objects

        return report_context


class LimsPlanificationWorksheetMethodReport(Report):
    'Worksheet by Method'
    __name__ = 'lims.planification.worksheet_method.report'

    @classmethod
    def get_context(cls, records, data):
        report_context = super(LimsPlanificationWorksheetMethodReport,
                cls).get_context(records, data)

        report_context['company'] = report_context['user'].company

        objects = {}
        for planification in records:
            if planification.state != 'confirmed':
                continue
            date = str(planification.start_date)
            if date not in objects:
                objects[date] = {
                    'date': planification.start_date,
                    'professionals': {},
                    }
            for detail in planification.details:
                fraction = detail.fraction
                for service_detail in detail.details:
                    if not service_detail.notebook_line:
                        continue
                    if (service_detail.notebook_line.analysis.behavior ==
                            'internal_relation'):
                        continue
                    p_key = ()
                    p_names = ''
                    for professional in service_detail.staff_responsible:
                        p_key += (professional.id,)
                        if p_names:
                            p_names += ', '
                        p_names += professional.rec_name
                    if not p_key:
                        continue
                    p_key = tuple(sorted(p_key))
                    if (p_key not in objects[date]['professionals']):
                        objects[date]['professionals'][p_key] = {
                            'professional': p_names,
                            'total': 0,
                            'lines': {},
                            }
                    notebook_line = service_detail.notebook_line

                    number = fraction.get_formated_number('pt-m-sy-sn-fn')
                    number = (number + '-' + str(notebook_line.repetition))
                    concentration_level = (
                        notebook_line.concentration_level.description if
                        notebook_line.concentration_level else '')
                    if (number not in objects[date]['professionals'][p_key][
                            'lines']):
                        number_parts = number.split('-')
                        order = (number_parts[3] + '-' + number_parts[2] +
                            '-' + number_parts[4] + '-' + number_parts[5])

                        comments_planif = '. '.join(cls.get_planning_legend(
                            fraction, planification))
                        if comments_planif:
                            comments = '%s - %s - %s - %s' % (
                                planification.comments or '',
                                notebook_line.service.comments or '',
                                notebook_line.service.fraction.comments or '',
                                comments_planif or '')
                        else:
                            comments = '%s - %s - %s' % (planification.comments
                                or '', notebook_line.service.comments or '',
                                notebook_line.service.fraction.comments or '')

                        record = {
                            'order': order,
                            'number': number,
                            'label': fraction.label,
                            'sample_client_description': (
                                fraction.sample.sample_client_description),
                            'party': fraction.party.code,
                            'storage_location': fraction.storage_location.code,
                            'fraction_type': fraction.type.code,
                            'concentration_level': concentration_level,
                            'device': (notebook_line.device.code if
                                notebook_line.device else None),
                            'urgent': 'SI' if notebook_line.urgent else '',
                            'comments': comments,
                            'planification_code': planification.code,
                            'package_type': fraction.package_type.description,
                            'methods': {},
                            }
                        objects[date]['professionals'][p_key]['lines'][
                            number] = record
                        objects[date]['professionals'][p_key]['total'] += 1
                    if (notebook_line.method.id not in
                            objects[date]['professionals'][p_key]['lines'][
                            number]['methods']):
                        objects[date]['professionals'][p_key]['lines'][
                            number]['methods'][notebook_line.method.id] = (
                                notebook_line.method.rec_name)

        for k1 in objects.iterkeys():
            for k2 in objects[k1]['professionals'].iterkeys():
                objects[k1]['professionals'][k2]['methods'] = {}
                fractions = objects[k1]['professionals'][k2]['lines'].values()
                for fraction in fractions:
                    m_key = ()
                    m_names = []
                    for m_id, m_name in fraction['methods'].iteritems():
                        m_key += (m_id,)
                        m_names.append(m_name)
                    m_key = tuple(sorted(m_key))
                    if (m_key not in objects[k1]['professionals'][k2][
                            'methods']):
                        objects[k1]['professionals'][k2]['methods'][m_key] = {
                            'methods': m_names,
                            'lines': [],
                            }
                    objects[k1]['professionals'][k2]['methods'][m_key][
                        'lines'].append(fraction)

                del objects[k1]['professionals'][k2]['lines']
                for m_key in objects[k1]['professionals'][k2][
                        'methods'].iterkeys():
                    sorted_lines = sorted(objects[k1]['professionals'][k2][
                        'methods'][m_key]['lines'], key=lambda x: x['order'])
                    objects[k1]['professionals'][k2]['methods'][m_key][
                        'lines'] = sorted_lines

        report_context['records'] = objects

        return report_context

    @classmethod
    def get_planning_legend(cls, fraction, planification):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsAnalysis = pool.get('lims.analysis')
        LimsPlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')
        LimsPlanificationDetail = pool.get('lims.planification.detail')
        LimsNotebookLine = pool.get('lims.notebook.line')

        cursor.execute('SELECT DISTINCT(a.planning_legend) '
            'FROM "' + LimsPlanificationDetail._table + '" pd '
                'INNER JOIN "' + LimsPlanificationServiceDetail._table +
                    '" psd '
                'ON pd.id = psd.detail '
                'INNER JOIN "' + LimsNotebookLine._table + '" nl '
                'ON nl.id = psd.notebook_line '
                'INNER JOIN "' + LimsAnalysis._table + '" a '
                'ON a.id = nl.analysis '
            'WHERE pd.planification = %s '
                'AND pd.fraction = %s '
                'AND a.planning_legend IS NOT NULL ',
                (planification.id, fraction.id))

        planned_ids = [s[0] for s in cursor.fetchall()]
        return planned_ids


class LimsPlanificationWorksheetReport(Report):
    'Worksheet'
    __name__ = 'lims.planification.worksheet.report'

    @classmethod
    def get_context(cls, records, data):
        report_context = super(LimsPlanificationWorksheetReport,
                cls).get_context(records, data)

        report_context['company'] = report_context['user'].company

        objects = {}
        for planification in records:
            if planification.state != 'confirmed':
                continue
            date = str(planification.start_date)
            if date not in objects:
                objects[date] = {
                    'date': planification.start_date,
                    'professionals': {},
                    }
            for detail in planification.details:
                fraction = detail.fraction
                for service_detail in detail.details:
                    if not service_detail.notebook_line:
                        continue
                    if (service_detail.notebook_line.analysis.behavior ==
                            'internal_relation'):
                        continue
                    p_key = ()
                    p_names = ''
                    for professional in service_detail.staff_responsible:
                        p_key += (professional.id,)
                        if p_names:
                            p_names += ', '
                        p_names += professional.rec_name
                    if not p_key:
                        continue
                    p_key = tuple(sorted(p_key))
                    if (p_key not in objects[date]['professionals']):
                        objects[date]['professionals'][p_key] = {
                            'professional': p_names,
                            'analysis': {},
                            'total': 0,
                            }
                    notebook_line = service_detail.notebook_line
                    key = service_detail.planned_service.id
                    if (key not in
                            objects[date]['professionals'][p_key]['analysis']):
                        objects[date]['professionals'][p_key]['analysis'][
                            key] = {
                                'analysis': (
                                    service_detail.planned_service.rec_name),
                                'lines': {},
                                }

                    number = fraction.get_formated_number('pt-m-sy-sn-fn')
                    number = (number + '-' + str(notebook_line.repetition))
                    concentration_level = (
                        notebook_line.concentration_level.description if
                        notebook_line.concentration_level else '')
                    if (number not in objects[date]['professionals'][p_key][
                            'analysis'][key]['lines']):
                        number_parts = number.split('-')
                        order = (number_parts[3] + '-' + number_parts[2] +
                            '-' + number_parts[4] + '-' + number_parts[5])

                        comments_planif = '. '.join(cls.get_planning_legend(
                            fraction, planification))
                        if comments_planif:
                            comments = '%s - %s - %s - %s' % (
                                planification.comments or '',
                                notebook_line.service.comments or '',
                                notebook_line.service.fraction.comments or '',
                                comments_planif or '')
                        else:
                            comments = '%s - %s - %s' % (planification.comments
                                or '', notebook_line.service.comments or '',
                                notebook_line.service.fraction.comments or '')

                        record = {
                            'order': order,
                            'number': number,
                            'label': fraction.label,
                            'sample_client_description': (
                                fraction.sample.sample_client_description if
                                fraction.sample.sample_client_description else
                                ''),
                            'party': fraction.party.code,
                            'storage_location': fraction.storage_location.code,
                            'fraction_type': fraction.type.code,
                            'concentration_level': concentration_level,
                            'device': (notebook_line.device.code if
                                notebook_line.device else None),
                            'urgent': 'SI' if notebook_line.urgent else '',
                            'comments': comments,
                            'planification_code': planification.code,
                            'package_type': fraction.package_type.description,
                            'methods': {},
                            }
                        objects[date]['professionals'][p_key]['analysis'][key][
                            'lines'][number] = record
                        objects[date]['professionals'][p_key]['total'] += 1
                    if (notebook_line.method.id not in
                            objects[date]['professionals'][p_key]['analysis'][
                            key]['lines'][number]['methods']):
                        objects[date]['professionals'][p_key]['analysis'][
                            key]['lines'][number]['methods'][
                            notebook_line.method.id] = (
                                notebook_line.method.rec_name)

        for k1 in objects.iterkeys():
            for k2 in objects[k1]['professionals'].iterkeys():
                for k3 in objects[k1]['professionals'][k2][
                        'analysis'].iterkeys():
                    objects[k1]['professionals'][k2]['analysis'][k3][
                        'methods'] = {}
                    fractions = objects[k1]['professionals'][k2]['analysis'][
                        k3]['lines'].values()
                    for fraction in fractions:
                        m_key = ()
                        m_names = []
                        for m_id, m_name in fraction['methods'].iteritems():
                            m_key += (m_id,)
                            m_names.append(m_name)
                        m_key = tuple(sorted(m_key))
                        if (m_key not in objects[k1]['professionals'][k2][
                                'analysis'][k3]['methods']):
                            objects[k1]['professionals'][k2]['analysis'][k3][
                                'methods'][m_key] = {
                                    'methods': m_names,
                                    'lines': [],
                                    }
                        objects[k1]['professionals'][k2]['analysis'][k3][
                            'methods'][m_key]['lines'].append(fraction)

                    del objects[k1]['professionals'][k2]['analysis'][k3][
                        'lines']
                    for m_key in objects[k1]['professionals'][k2][
                            'analysis'][k3]['methods'].iterkeys():
                        sorted_lines = sorted(objects[k1]['professionals'][k2][
                            'analysis'][k3]['methods'][m_key]['lines'],
                            key=lambda x: x['order'])
                        objects[k1]['professionals'][k2]['analysis'][k3][
                            'methods'][m_key]['lines'] = sorted_lines

        report_context['records'] = objects
        return report_context

    @classmethod
    def get_planning_legend(cls, fraction, planification):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsAnalysis = pool.get('lims.analysis')
        LimsPlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')
        LimsPlanificationDetail = pool.get('lims.planification.detail')
        LimsNotebookLine = pool.get('lims.notebook.line')

        cursor.execute('SELECT DISTINCT(a.planning_legend) '
            'FROM "' + LimsPlanificationDetail._table + '" pd '
                'INNER JOIN "' + LimsPlanificationServiceDetail._table +
                    '" psd '
                'ON pd.id = psd.detail '
                'INNER JOIN "' + LimsNotebookLine._table + '" nl '
                'ON nl.id = psd.notebook_line '
                'INNER JOIN "' + LimsAnalysis._table + '" a '
                'ON a.id = nl.analysis '
            'WHERE pd.planification = %s '
                'AND pd.fraction = %s '
                'AND a.planning_legend IS NOT NULL ',
                (planification.id, fraction.id))

        planned_ids = [s[0] for s in cursor.fetchall()]
        return planned_ids


class PrintPendingServicesUnplannedReportStart(ModelView):
    'Print Pending Services Unplanned Report Start'
    __name__ = 'lims.pending_services_unplanned.start'

    start_date = fields.Date('Start Date', required=True)
    end_date = fields.Date('End Date', required=True)
    party = fields.Many2One('party.party', 'Party')


class PrintPendingServicesUnplannedReport(Wizard):
    'Print Pending Services Unplanned Report'
    __name__ = 'lims.pending_services_unplanned'

    start = StateView('lims.pending_services_unplanned.start',
        'lims_planification.print_pending_services_unplanned_report_start'
        '_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print', 'print_', 'tryton-print', default=True),
            Button('Save', 'save', 'tryton-save'),
        ])
    print_ = StateAction(
        'lims_planification.report_pending_services_unplanned')
    save = StateAction(
        'lims_planification.report_pending_services_unplanned_spreadsheet')

    def do_print_(self, action):
        data = {
            'start_date': self.start.start_date,
            'end_date': self.start.end_date or None,
            'party': self.start.party and self.start.party.id or None,
            }
        return action, data

    def do_save(self, action):
        data = {
            'start_date': self.start.start_date,
            'end_date': self.start.end_date or None,
            'party': self.start.party and self.start.party.id or None,
            }
        return action, data


class LimsPendingServicesUnplannedReport(Report):
    'Pending Services Unplanned'
    __name__ = 'lims.pending_services_unplanned.report'

    @classmethod
    def get_context(cls, records, data):
        report_context = super(LimsPendingServicesUnplannedReport,
                cls).get_context(records, data)

        pool = Pool()
        LimsService = pool.get('lims.service')
        LimsLaboratory = pool.get('lims.laboratory')

        if report_context['user'].laboratory:
            labs = [report_context['user'].laboratory.id]
        else:
            labs = [l.id for l in LimsLaboratory.search([])]

        report_context['company'] = report_context['user'].company

        clause = []
        if data['start_date']:
            clause.append(('confirmation_date', '>=', data['start_date']))
        if data['end_date']:
            clause.append(('confirmation_date', '<=', data['end_date']))
        if data['party']:
            clause.append(('party', '=', data['party']))
        clause.extend([
            ('fraction.type.plannable', '=', True),
            ('fraction.confirmed', '=', True),
            ('analysis.behavior', '!=', 'internal_relation'),
            ])
        unplanned_services = cls.get_unplanned_services()
        clause.append(('id', 'in', unplanned_services))

        report_context['start_date'] = (data['start_date']
            if data['start_date'] else '')
        report_context['end_date'] = (data['end_date']
            if data['end_date'] else '')
        objects = {}
        with Transaction().set_user(0):
            pending_services = LimsService.search(clause)
        for service in pending_services:
            # Laboratory
            laboratory = cls.get_service_laboratory(service.id)
            if laboratory.id not in labs:
                continue

            if laboratory.id not in objects:
                objects[laboratory.id] = {
                    'laboratory': laboratory.rec_name,
                    'services': {},
                    'total': 0,
                    }

            # Service
            analysis = service.analysis
            if analysis.id not in objects[laboratory.id]['services']:
                objects[laboratory.id]['services'][analysis.id] = {
                    'service': analysis.rec_name,
                    'parties': {},
                    'total': 0,
                    }

            # Party
            party = service.party
            if (party.id not in objects[laboratory.id]['services'][
                    analysis.id]['parties']):
                objects[laboratory.id]['services'][analysis.id]['parties'][
                    party.id] = {
                        'party': party.code,
                        'lines': [],
                        'total': 0,
                        }

            number = service.fraction.get_formated_number('pt-m-sn-sy-fn')
            number = (number + '-' + unicode(service.sample.label))
            number_parts = number.split('-')
            order = (number_parts[3] + '-' + number_parts[2] + '-' +
                number_parts[4])

            result_estimated = []
            result_estimated = cls.get_results_estimated(service.id)
            result_estimated_date = None
            result_estimated_waiting = None

            if result_estimated:
                result_estimated_waiting = result_estimated[0][1]
                confirmation_date = result_estimated[0][0]
                number_d = 0
                days = result_estimated_waiting
                date_from = confirmation_date
                while number_d < days:
                    date_from = date_from + relativedelta(days=1)
                    if (datetime.weekday(date_from) != 5
                            and datetime.weekday(date_from) != 6):
                        number_d += 1
                result_estimated_date = date_from

            record = {
                'order': order,
                'number': number,
                'date': service.sample.date2,
                'sample_client_description': (
                    service.sample.sample_client_description),
                'current_location': (service.fraction.current_location.code
                    if service.fraction.current_location else ''),
                'fraction_type': service.fraction.type.code,
                'priority': service.priority,
                'urgent': 'Yes' if service.urgent else 'No',
                'comments': ('%s - %s' % (service.fraction.comments or '',
                    service.sample.comments or '')),
                'report_date': service.report_date,
                'confirmation_date': (service.confirmation_date
                    if service.confirmation_date else ''),
                'results_estimated_date': (result_estimated_date
                    if result_estimated_date else ''),
                }
            objects[laboratory.id]['services'][analysis.id]['parties'][
                party.id]['lines'].append(record)
            objects[laboratory.id]['total'] += 1
            objects[laboratory.id]['services'][analysis.id]['total'] += 1
            objects[laboratory.id]['services'][analysis.id]['parties'][
                party.id]['total'] += 1
        for k1 in objects.iterkeys():
            for k2 in objects[k1]['services'].iterkeys():
                for k3, lines in objects[k1]['services'][k2][
                        'parties'].iteritems():
                    sorted_lines = sorted(lines['lines'],
                        key=lambda x: x['order'])
                    objects[k1]['services'][k2]['parties'][k3]['lines'] = (
                        sorted_lines)

        report_context['objects'] = objects

        return report_context

    @classmethod
    def get_unplanned_services(cls):
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
        return not_planned_ids

    @classmethod
    def get_service_laboratory(cls, service_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsEntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        LimsService = pool.get('lims.service')
        LimsLaboratory = pool.get('lims.laboratory')

        cursor.execute('SELECT d.laboratory '
            'FROM "' + LimsEntryDetailAnalysis._table + '" d '
                'INNER JOIN "' + LimsService._table + '" s '
                'ON s.id = d.service '
            'WHERE s.id = %s '
            'ORDER BY d.id ASC LIMIT 1',
            (service_id,))
        return LimsLaboratory(cursor.fetchone()[0])

    @classmethod
    def get_results_estimated(cls, service_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsEntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsAnalysis = pool.get('lims.analysis')

        cursor.execute('SELECT  d.confirmation_date, '
                'n.results_estimated_waiting '
            'FROM "' + LimsNotebookLine._table + '" n '
                'INNER JOIN "' + LimsEntryDetailAnalysis._table + '" d '
                'ON (d.service = n.service  AND d.analysis = n.analysis) '
                'INNER JOIN "' + LimsAnalysis._table + '" a '
                'ON a.id = d.analysis '
            'WHERE d.state IN (\'draft\', \'unplanned\') '
                'AND d.service = %s '
                'AND n.results_estimated_waiting IS NOT Null '
                'AND a.behavior != \'internal_relation\''
                'ORDER BY n.results_estimated_waiting ASC LIMIT 1',
                (service_id,))

        return list(cursor.fetchall())


class LimsPendingServicesUnplannedSpreadsheet(Report):
    'Pending Services Unplanned'
    __name__ = 'lims.pending_services_unplanned.spreadsheet'

    @classmethod
    def get_context(cls, records, data):
        report_context = super(LimsPendingServicesUnplannedSpreadsheet,
                cls).get_context(records, data)

        pool = Pool()
        LimsService = pool.get('lims.service')
        LimsLaboratory = pool.get('lims.laboratory')

        if report_context['user'].laboratory:
            labs = [report_context['user'].laboratory.id]
        else:
            labs = [l.id for l in LimsLaboratory.search([])]

        report_context['company'] = report_context['user'].company

        clause = []
        if data['start_date']:
            clause.append(('confirmation_date', '>=', data['start_date']))
        if data['end_date']:
            clause.append(('confirmation_date', '<=', data['end_date']))
        if data['party']:
            clause.append(('party', '=', data['party']))
        clause.extend([
            ('fraction.type.plannable', '=', True),
            ('fraction.confirmed', '=', True),
            ('analysis.behavior', '!=', 'internal_relation'),
            ])
        unplanned_services = cls.get_unplanned_services()
        clause.append(('id', 'in', unplanned_services))

        report_context['start_date'] = (data['start_date']
            if data['start_date'] else '')
        report_context['end_date'] = (data['end_date']
            if data['end_date'] else '')
        objects = []
        with Transaction().set_user(0):
            pending_services = LimsService.search(clause)

        for service in pending_services:
            laboratory = cls.get_service_laboratory(service.id)
            if laboratory.id not in labs:
                continue

            number = service.fraction.get_formated_number('pt-m-sn-sy-fn')
            number = (number + '-' + unicode(service.sample.label))
            number_parts = number.split('-')
            order = (number_parts[3] + '-' + number_parts[2] + '-' +
                number_parts[4])

            result_estimated = []
            result_estimated = cls.get_results_estimated(service.id)
            result_estimated_date = None
            result_estimated_waiting = None

            if result_estimated:
                result_estimated_waiting = result_estimated[0][1]
                confirmation_date = result_estimated[0][0]
                number_d = 0
                days = result_estimated_waiting
                date_from = confirmation_date
                while number_d < days:
                    date_from = date_from + relativedelta(days=1)
                    if (datetime.weekday(date_from) != 5
                            and datetime.weekday(date_from) != 6):
                        number_d += 1
                result_estimated_date = date_from
            notice = None
            report_date = service.report_date
            today = datetime.today().date()

            if report_date:
                if report_date < today:
                    notice = 'Timed out'
            else:
                if result_estimated_date:
                    if result_estimated_date < today:
                        notice = 'Timed out'

            if report_date:
                d = (report_date - today).days
                if d >= 0 and d < 3:
                    notice = 'To expire'
            else:
                if result_estimated_date:
                    d = (result_estimated_date - today).days
                    if d >= 0 and d < 3:
                        notice = 'To expire'

            record = {
                'laboratory': laboratory.rec_name,
                'service': service.analysis.rec_name,
                'party': service.party.code,
                'order': order,
                'number': number,
                'date': service.sample.date2,
                'sample_client_description': (
                    service.sample.sample_client_description),
                'current_location': (service.fraction.current_location.code
                    if service.fraction.current_location else ''),
                'fraction_type': service.fraction.type.code,
                'priority': service.priority,
                'urgent': 'Yes' if service.urgent else 'No',
                'comments': ('%s - %s' % (service.fraction.comments or '',
                    service.sample.comments or '')),
                'report_date': service.report_date,
                'confirmation_date': (service.confirmation_date
                    if service.confirmation_date else ''),
                'results_estimated_date': (result_estimated_date
                    if result_estimated_date else ''),
                'results_estimated_waiting': (result_estimated_waiting
                    if result_estimated_waiting else ''),
                'notice': (notice
                    if notice else ''),
                }
            objects.append(record)
        objects = sorted(objects, key=lambda x: (
                x['laboratory'], x['service'], x['party'], x['order']))

        report_context['objects'] = objects

        return report_context

    @classmethod
    def get_unplanned_services(cls):
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
        return not_planned_ids

    @classmethod
    def get_service_laboratory(cls, service_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsEntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        LimsService = pool.get('lims.service')
        LimsLaboratory = pool.get('lims.laboratory')

        cursor.execute('SELECT d.laboratory '
            'FROM "' + LimsEntryDetailAnalysis._table + '" d '
                'INNER JOIN "' + LimsService._table + '" s '
                'ON s.id = d.service '
            'WHERE s.id = %s '
            'ORDER BY d.id ASC LIMIT 1',
            (service_id,))
        return LimsLaboratory(cursor.fetchone()[0])

    @classmethod
    def get_results_estimated(cls, service_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsEntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsAnalysis = pool.get('lims.analysis')

        cursor.execute('SELECT  d.confirmation_date, '
                'n.results_estimated_waiting '
            'FROM "' + LimsNotebookLine._table + '" n '
                'INNER JOIN "' + LimsEntryDetailAnalysis._table + '" d '
                'ON (d.service = n.service  AND d.analysis = n.analysis) '
                'INNER JOIN "' + LimsAnalysis._table + '" a '
                'ON a.id = d.analysis '
            'WHERE d.state IN (\'draft\', \'unplanned\') '
                'AND d.service = %s '
                'AND n.results_estimated_waiting IS NOT Null '
                'AND a.behavior != \'internal_relation\''
                'ORDER BY n.results_estimated_waiting ASC LIMIT 1',
                (service_id,))

        return list(cursor.fetchall())


class PrintBlindSampleReportStart(ModelView):
    'Blind Samples Report'
    __name__ = 'lims.print_blind_sample_report.start'

    date_from = fields.Date('Date from', required=True)
    date_to = fields.Date('Date to', required=True)


class PrintBlindSampleReport(Wizard):
    'Blind Samples Report'
    __name__ = 'lims.print_blind_sample_report'

    start = StateView('lims.print_blind_sample_report.start',
        'lims_planification.lims_print_blind_sample_report_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print', 'print_', 'tryton-print', default=True),
            ])
    print_ = StateAction('lims_planification.report_blind_sample')

    def do_print_(self, action):
        LimsBlindSample = Pool().get('lims.blind_sample')

        blind_samples = LimsBlindSample.search_count([
            ('date', '>=', self.start.date_from),
            ('date', '<=', self.start.date_to),
            ('line.result', '!=', None),
            ])
        if blind_samples > 0:
            data = {
                'date_from': self.start.date_from,
                'date_to': self.start.date_to,
                }
            return action, data

    def transition_print_(self):
        return 'end'


class LimsBlindSampleReport(Report):
    'Blind Samples Report'
    __name__ = 'lims.blind_sample_report'

    @classmethod
    def get_context(cls, records, data):
        report_context = super(LimsBlindSampleReport, cls).get_context(records,
                data)
        LimsBlindSample = Pool().get('lims.blind_sample')

        report_context['company'] = report_context['user'].company

        objects = []
        blind_samples = LimsBlindSample.search([
            ('date', '>=', data['date_from']),
            ('date', '<=', data['date_to']),
            ('line.result', '!=', None),
            ], order=[('date', 'ASC')])
        for bs in blind_samples:

            if bs.line.converted_result:
                result = float(bs.line.converted_result)
                unit = bs.line.final_unit
                concentration = bs.line.final_concentration
                result = round(result, bs.line.decimals)
            elif bs.line.result:
                result = float(bs.line.result)
                unit = bs.line.initial_unit
                concentration = bs.line.initial_concentration
                result = round(result, bs.line.decimals)
            else:
                result = None
                unit = None
                concentration = ''

            record = {
                'date': bs.date,
                'fraction': bs.fraction.rec_name,
                'report': (bs.line.results_report.number if
                    bs.line.results_report else ''),
                'repetition': bs.line.repetition,
                'analysis_origin': bs.line.analysis_origin,
                'analysis': bs.analysis.rec_name,
                'result': result,
                'unit': unit.symbol if unit else '',
                'concentration': concentration,
                'original_fraction': '',
                'original_report': '',
                'original_result': '',
                'original_unit': '',
                'original_concentration': '',
                'error': '',
                'max_sd': '',
                'two_max_sd': '',
                'accepted': '',
                }
            if bs.original_fraction:
                record['original_fraction'] = bs.original_fraction.rec_name
                if bs.original_line:
                    if bs.original_line.results_report:
                        record['original_report'] = (
                            bs.original_line.results_report.number)
                    if bs.original_line.converted_result:
                        original_result = float(
                            bs.original_line.converted_result)
                        original_unit = bs.original_line.final_unit
                        original_concentration = (
                            bs.original_line.final_concentration)
                    elif bs.original_line.result:
                        original_result = float(bs.original_line.result)
                        original_unit = bs.original_line.initial_unit
                        original_concentration = (
                            bs.original_line.initial_concentration)
                    else:
                        original_result = None
                    if original_result:
                        original_result = round(original_result,
                            bs.original_line.decimals)
                        record['original_result'] = original_result
                        record['original_unit'] = (original_unit.symbol
                            if original_unit else '')
                        record['original_concentration'] = (
                            original_concentration)
                        if unit == original_unit:
                            average = (result + original_result) / 2
                            difference = result - original_result
                            record['error'] = round(difference * 100 / average,
                                2)
                            try:
                                maximum_concentration = float(
                                    unit.maximum_concentration)
                                rsd_horwitz = float(unit.rsd_horwitz)
                            except (TypeError, ValueError):
                                maximum_concentration = 0
                                rsd_horwitz = 0

                            if result <= maximum_concentration:
                                record['max_sd'] = round(average * rsd_horwitz,
                                    2)
                                record['two_max_sd'] = round(record['max_sd']
                                    * 2, 2)
                                if abs(difference) <= record['two_max_sd']:
                                    record['accepted'] = 'a'
                                else:
                                    record['accepted'] = 'r'
            else:
                if bs.min_value and bs.max_value:
                    min_value = float(bs.min_value)
                    max_value = float(bs.max_value)
                    if min_value <= result and result <= max_value:
                        record['error'] = 'OK'
                    elif result < min_value:
                        record['error'] = round(result - min_value, 2)
                    elif result > max_value:
                        record['error'] = round(result - max_value, 2)
            objects.append(record)

        report_context['objects'] = objects

        report_context['date_from'] = data['date_from']
        report_context['date_to'] = data['date_to']

        return report_context

    def _get_variables(self, formula, notebook_line):
        LimsVolumeConversion = Pool().get('lims.volume.conversion')

        variables = {}
        for var in ('DI',):
            while True:
                idx = formula.find(var)
                if idx >= 0:
                    variables[var] = 0
                    formula = formula.replace(var, '_')
                else:
                    break
        for var in variables.iterkeys():
            if var == 'DI':
                ic = float(notebook_line.final_concentration)
                result = LimsVolumeConversion.brixToDensity(ic)
                if result:
                    variables[var] = result
        return variables


class LimsPlanificationSequenceAnalysisReport(Report):
    'Sequence Analysis'
    __name__ = 'lims.planification.sequence.analysis.report'

    @classmethod
    def get_context(cls, records, data):
        report_context = super(LimsPlanificationSequenceAnalysisReport,
                cls).get_context(records, data)

        report_context['company'] = report_context['user'].company

        objects = {}
        for planification in records:
            if planification.state != 'confirmed':
                continue
            date = str(planification.start_date)
            if date not in objects:
                objects[date] = {
                    'date': planification.start_date,
                    'methods': {},
                    }
            for detail in planification.details:
                fraction = detail.fraction
                for service_detail in detail.details:
                    if (service_detail.notebook_line.analysis.behavior ==
                            'internal_relation'):
                        continue
                    notebook_line = service_detail.notebook_line
                    method_id = notebook_line.method.id
                    if method_id not in objects[date]['methods']:
                        objects[date]['methods'][method_id] = {
                            'method': notebook_line.method.code,
                            'lines': {},
                            }

                    number = fraction.get_formated_number('sn-sy-fn')
                    number = (number + '-' + str(notebook_line.repetition))
                    number_parts = number.split('-')
                    order = (number_parts[1] + '-' + number_parts[0] + '-' +
                        number_parts[2] + '-' + number_parts[3])

                    product_type = fraction.product_type.code
                    matrix = fraction.matrix.code
                    fraction_type = fraction.type.code
                    analysis = notebook_line.analysis.rec_name
                    priority = notebook_line.priority
                    urgent = notebook_line.urgent
                    trace_report = fraction.sample.trace_report
                    sample_client_description = (
                        fraction.sample.sample_client_description)
                    key = (number, product_type, matrix, fraction_type,
                        analysis, priority, trace_report)
                    if key not in objects[date]['methods'][method_id]['lines']:
                        objects[date]['methods'][method_id]['lines'][key] = {
                            'order': order,
                            'number': number,
                            'product_type': product_type,
                            'matrix': matrix,
                            'fraction_type': fraction_type,
                            'analysis': analysis,
                            'priority': priority,
                            'trace_report': trace_report,
                            'urgent': urgent,
                            'sample_client_description': (
                                sample_client_description),
                            }

        for k1 in objects.iterkeys():
            for k2, lines in objects[k1]['methods'].iteritems():
                sorted_lines = sorted(lines['lines'].values(),
                    key=lambda x: x['order'])
                objects[k1]['methods'][k2]['lines'] = sorted_lines

        report_context['objects'] = objects

        return report_context
