# -*- coding: utf-8 -*-
# This file is part of lims_project_water module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, Equal, Bool, Not
from trytond.transaction import Transaction
from trytond.report import Report

__all__ = ['Project', 'Entry', 'Sample', 'CreateSampleStart', 'CreateSample']

STATES = {
    'required': Bool(Equal(Eval('type'), 'water')),
}
DEPENDS = ['type']
PROJECT_TYPE = ('water', 'Water sampling')


class Project(metaclass=PoolMeta):
    __name__ = 'lims.project'

    wtr_comments = fields.Text('Climatic conditions of the sampling')

    @classmethod
    def __setup__(cls):
        super(Project, cls).__setup__()
        project_type = PROJECT_TYPE
        if project_type not in cls.type.selection:
            cls.type.selection.append(project_type)
        cls._error_messages.update({
            'not_water': ('Please, select a "Water sampling" Project to print '
                'this report'),
            })

    @classmethod
    def view_attributes(cls):
        return super(Project, cls).view_attributes() + [
            ('//group[@id="water"]', 'states', {
                    'invisible': Not(Bool(Equal(Eval('type'), 'water'))),
                    })]


class Entry(metaclass=PoolMeta):
    __name__ = 'lims.entry'

    @classmethod
    def __setup__(cls):
        super(Entry, cls).__setup__()
        project_type = PROJECT_TYPE
        if project_type not in cls.project_type.selection:
            cls.project_type.selection.append(project_type)


class Sample(metaclass=PoolMeta):
    __name__ = 'lims.sample'

    sampling_point = fields.Char('Sampling point', states={
            'invisible': Not(Bool(Equal(Eval('project_type'), 'water'))),
            }, depends=['project_type'])
    gps_coordinates = fields.Char('GPS coordinates', states={
            'invisible': Not(Bool(Equal(Eval('project_type'), 'water'))),
            }, depends=['project_type'])
    sampling_datetime = fields.DateTime('Sampling date and time', states={
            'invisible': Not(Bool(Equal(Eval('project_type'), 'water'))),
            }, depends=['project_type'])
    sampling_responsible = fields.Many2One('party.party',
        'Sampling responsible', states={
            'invisible': Not(Bool(Equal(Eval('project_type'), 'water'))),
            }, depends=['project_type'])

    @classmethod
    def view_attributes(cls):
        return super(Sample, cls).view_attributes() + [
            ('//page[@id="water_sampling"]', 'states', {
                    'invisible': Not(Bool(
                        Equal(Eval('project_type'), 'water'))),
                    })]


class CreateSampleStart(metaclass=PoolMeta):
    __name__ = 'lims.create_sample.start'

    sampling_point = fields.Char('Sampling point', states={
            'invisible': Not(Bool(Equal(Eval('project_type'), 'water'))),
            }, depends=['project_type'])
    gps_coordinates = fields.Char('GPS coordinates', states={
            'invisible': Not(Bool(Equal(Eval('project_type'), 'water'))),
            }, depends=['project_type'])
    sampling_datetime = fields.DateTime('Sampling date and time', states={
            'invisible': Not(Bool(Equal(Eval('project_type'), 'water'))),
            }, depends=['project_type'])
    sampling_responsible = fields.Many2One('party.party',
        'Sampling responsible', states={
            'invisible': Not(Bool(Equal(Eval('project_type'), 'water'))),
            }, depends=['project_type'])

    @classmethod
    def view_attributes(cls):
        return super(CreateSampleStart, cls).view_attributes() + [
            ('//page[@id="water_sampling"]', 'states', {
                    'invisible': Not(Bool(
                        Equal(Eval('project_type'), 'water'))),
                    })]


class CreateSample(metaclass=PoolMeta):
    __name__ = 'lims.create_sample'

    def _get_samples_defaults(self, entry_id):
        samples_defaults = super(CreateSample,
            self)._get_samples_defaults(entry_id)

        sampling_point = (hasattr(self.start, 'sampling_point') and
            getattr(self.start, 'sampling_point') or None)
        gps_coordinates = (hasattr(self.start, 'gps_coordinates') and
            getattr(self.start, 'gps_coordinates') or None)
        sampling_responsible_id = None
        if (hasattr(self.start, 'sampling_responsible') and
                getattr(self.start, 'sampling_responsible')):
            sampling_responsible_id = getattr(self.start,
                'sampling_responsible').id

        for sample_defaults in samples_defaults:
            sample_defaults['sampling_point'] = sampling_point
            sample_defaults['gps_coordinates'] = gps_coordinates
            sample_defaults['sampling_responsible'] = sampling_responsible_id

        return samples_defaults


class ProjectWaterSampling(Report):
    'Project Water Sampling report'
    __name__ = 'lims.project.water_sampling_report'

    @classmethod
    def execute(cls, ids, data):
        Project = Pool().get('lims.project')

        project = Project(data['id'])
        if project.type != 'water':
            Project.raise_user_error('not_water')

        return super(ProjectWaterSampling, cls).execute(ids, data)

    @classmethod
    def get_context(cls, records, data):
        pool = Pool()
        Project = pool.get('lims.project')
        Fraction = pool.get('lims.fraction')
        Entry = pool.get('lims.entry')
        report_context = super(ProjectWaterSampling, cls).get_context(
            records, data)

        project = Project(data['id'])
        entry = Entry.search([
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

        fractions = Fraction.search([
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
                'sample_comments': str(fraction.sample.comments or ''),
                'label': fraction.sample.label,
                'results': (cls.get_results_insitu(fraction.id)),
                })

        report_context['objects'] = objects
        return report_context

    @classmethod
    def get_results_insitu(cls, fraction_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Service = pool.get('lims.service')
        NotebookLine = pool.get('lims.notebook.line')
        Analysis = pool.get('lims.analysis')
        ProductUom = pool.get('product.uom')

        slike = '%in situ%'
        cursor.execute('SELECT DISTINCT(a.description) , '
                ' nl.result, p.symbol AS initial_unit '
            'FROM "' + NotebookLine._table + '" nl '
                'INNER JOIN "' + Service._table + '" s '
                'ON nl.service = s.id '
                'INNER JOIN "' + Analysis._table + '" a '
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
        Entry = pool.get('lims.entry')
        Party = pool.get('party.party')
        PartyAddress = pool.get('party.address')
        EntryReportContact = pool.get('lims.entry.report_contacts')

        cursor.execute('SELECT  rc.contact '
            'FROM "' + Entry._table + '" e '
                'INNER JOIN "' + Party._table + '" p '
                'ON e.party = p.id '
                'INNER JOIN "' + EntryReportContact._table + '" rc '
                'ON e.id = rc.entry '
            'WHERE e.project = %s ',
            (project_id,))

        return PartyAddress.search([
            ('id', 'in', [x[0] for x in cursor.fetchall()]),
            ])

    @staticmethod
    def get_contact_invoice(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Entry = pool.get('lims.entry')
        Party = pool.get('party.party')
        PartyAddress = pool.get('party.address')
        EntryInvoiceContact = pool.get('lims.entry.invoice_contacts')

        cursor.execute('SELECT  ic.contact '
            'FROM "' + Entry._table + '" e '
                'INNER JOIN "' + Party._table + '" p '
                'ON e.party = p.id '
                'INNER JOIN "' + EntryInvoiceContact._table + '" ic '
                'ON e.id = ic.entry '
            'WHERE e.project = %s ',
            (project_id,))

        return PartyAddress.search([
            ('id', 'in', [x[0] for x in cursor.fetchall()]),
            ])
