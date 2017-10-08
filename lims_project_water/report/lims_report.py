# -*- coding: utf-8 -*-
# This file is part of lims_project_water module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import sys

from trytond.report import Report
from trytond.pool import Pool
from trytond.transaction import Transaction

reload(sys)
sys.setdefaultencoding('utf8')


__all__ = ['LimsProjectWaterSampling']


class LimsProjectWaterSampling(Report):
    'Project Water Sampling report'
    __name__ = 'lims.project.water_sampling_report'

    @classmethod
    def execute(cls, ids, data):
        LimsProject = Pool().get('lims.project')

        project = LimsProject(data['id'])
        if project.type != 'water':
            LimsProject.raise_user_error('not_water')

        return super(LimsProjectWaterSampling, cls).execute(ids, data)

    @classmethod
    def get_context(cls, records, data):
        pool = Pool()
        LimsProject = pool.get('lims.project')
        LimsFraction = pool.get('lims.fraction')
        LimsEntry = pool.get('lims.entry')
        report_context = super(LimsProjectWaterSampling, cls).get_context(
            records, data)

        project = LimsProject(data['id'])
        entry = LimsEntry.search([
            ('project', '=', project.id),
            ], order=[('number', 'ASC')])

        report_context['company'] = report_context['user'].company
        report_context['date'] = project.end_date
        report_context['description'] = project.description
        report_context['client'] = project.client
        report_context['project_comments'] = project.comments
        report_context['wtr_comments'] = project.wtr_comments
        report_context['code'] = project.code
        report_context['invoice_party'] = ''
        report_context['technical_team'] = ''
        report_context['contact_results'] = ''
        report_context['contact_invoice'] = ''

        if entry:
            report_context['invoice_party'] = entry[0].invoice_party
            report_context['technical_team'] = entry[0].comments
            report_context['contact_results'] = ', '.join([
                r.name for r in cls.get_contact_results(project.id)])
            report_context['contact_invoice'] = ', '.join([
                r.name for r in cls.get_contact_invoice(project.id)])

        fractions = LimsFraction.search([
            ('sample.entry.project', '=', project.id),
            ('confirmed', '=', True),
            ], order=[('number', 'ASC')])

        objects = []
        for fraction in fractions:
            objects.append({
                'number': fraction.get_formated_number('pt-m-sy-sn-fn'),
                'type': fraction.type.code,
                'packages': '%s %s' % (fraction.packages_quantity or '',
                    fraction.package_type.description if fraction.package_type
                    else ''),
                'sampling_point': (fraction.sample.sampling_point
                    if fraction.sample.sampling_point else ''),
                'gps_coordinates': (fraction.sample.gps_coordinates
                    if fraction.sample.gps_coordinates else ''),
                'sampling_responsible': (fraction.sample.sampling_responsible
                    if fraction.sample.sampling_responsible else ''),
                'entry_date': fraction.sample.date2,
                'countersample_location': (fraction.countersample_location.code
                    if fraction.countersample_location else ''),
                'countersample_date': fraction.countersample_date or '',
                'discharge_date': fraction.discharge_date or '',
                'sample_comments': unicode(fraction.sample.comments or ''),
                'label': fraction.sample.label,
                'results': (cls.get_results_insitu(fraction.id)),
                })

        report_context['objects'] = objects
        return report_context

    @classmethod
    def get_results_insitu(cls, fraction_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsService = pool.get('lims.service')
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsAnalysis = pool.get('lims.analysis')
        ProductUom = pool.get('product.uom')

        slike = '%in situ%'
        cursor.execute('SELECT DISTINCT(a.description) , '
                ' nl.result, p.symbol AS initial_unit '
            'FROM "' + LimsNotebookLine._table + '" nl '
                'INNER JOIN "' + LimsService._table + '" s '
                'ON nl.service = s.id '
                'INNER JOIN "' + LimsAnalysis._table + '" a '
                'ON a.id = nl.analysis '
                'INNER JOIN "' + ProductUom._table + '" p '
                'ON nl.initial_unit = p.id '
            'WHERE s.fraction = %s '
            'AND a.description LIKE %s '
            'ORDER BY a.description ASC ',
            (fraction_id, slike,))

        res = {}
        res = cursor.fetchall()

        line_result = []
        if res:
            for line in res:
                r0 = line[0].encode('utf-8')
                r2 = line[2].encode('utf-8')
                if line[1] is None:
                    r1 = ' '
                else:
                    r1 = line[1].encode('utf-8')
                line_p = ['%s: %s %s \n' % (r0, r1, r2)]
                line_result.extend(line_p)
        return line_result

    @staticmethod
    def get_contact_results(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsEntry = pool.get('lims.entry')
        Party = pool.get('party.party')
        PartyAddress = pool.get('party.address')
        LimsEntryReportContact = pool.get('lims.entry.report_contacts')

        cursor.execute('SELECT  rc.contact '
            'FROM "' + LimsEntry._table + '" e '
                'INNER JOIN "' + Party._table + '" p '
                'ON e.party = p.id '
                'INNER JOIN "' + LimsEntryReportContact._table + '" rc '
                'ON e.id = rc.entry '
            'WHERE e.project = %s ',
            (project_id,))

        return PartyAddress.search([
            ('id', 'in', cursor.fetchall()),
            ])

    @staticmethod
    def get_contact_invoice(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsEntry = pool.get('lims.entry')
        Party = pool.get('party.party')
        PartyAddress = pool.get('party.address')
        LimsEntryInvoiceContact = pool.get('lims.entry.invoice_contacts')

        cursor.execute('SELECT  ic.contact '
            'FROM "' + LimsEntry._table + '" e '
                'INNER JOIN "' + Party._table + '" p '
                'ON e.party = p.id '
                'INNER JOIN "' + LimsEntryInvoiceContact._table + '" ic '
                'ON e.id = ic.entry '
            'WHERE e.project = %s ',
            (project_id,))

        return PartyAddress.search([
            ('id', 'in', cursor.fetchall()),
            ])
