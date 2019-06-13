# -*- coding: utf-8 -*-
# This file is part of lims module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import sys
import logging
import operator
from datetime import datetime
from dateutil.relativedelta import relativedelta
from trytond.model import ModelView, ModelSQL, fields, Unique
from trytond.wizard import Wizard, StateTransition, StateView, StateAction, \
    Button
from trytond.pool import Pool
from trytond.pyson import PYSONEncoder, Eval, Equal, Bool, Not, Or
from trytond.transaction import Transaction
from trytond.report import Report

__all__ = ['Zone', 'Variety', 'MatrixVariety', 'PackagingIntegrity',
    'PackagingType', 'FractionType', 'SampleProducer', 'Service',
    'Fraction', 'Sample', 'DuplicateSampleStart', 'DuplicateSample',
    'DuplicateSampleFromEntryStart', 'DuplicateSampleFromEntry',
    'ManageServices', 'CompleteServices', 'FractionsByLocationsStart',
    'FractionsByLocations', 'CountersampleStorageStart',
    'CountersampleStorageEmpty', 'CountersampleStorageResult',
    'CountersampleStorage', 'CountersampleStorageRevertStart',
    'CountersampleStorageRevertEmpty', 'CountersampleStorageRevertResult',
    'CountersampleStorageRevert', 'CountersampleDischargeStart',
    'CountersampleDischargeEmpty', 'CountersampleDischargeResult',
    'CountersampleDischarge', 'FractionDischargeStart',
    'FractionDischargeEmpty', 'FractionDischargeResult', 'FractionDischarge',
    'FractionDischargeRevertStart', 'FractionDischargeRevertEmpty',
    'FractionDischargeRevertResult', 'FractionDischargeRevert',
    'CreateSampleStart', 'CreateSampleService', 'CreateSample',
    'CountersampleStoragePrintStart', 'CountersampleStoragePrint',
    'CountersampleStorageReport', 'CountersampleDischargePrintStart',
    'CountersampleDischargePrint', 'CountersampleDischargeReport']


class Zone(ModelSQL, ModelView):
    'Zone/Region'
    __name__ = 'lims.zone'
    _rec_name = 'description'

    code = fields.Char('Code', required=True)
    description = fields.Char('Description', required=True)
    restricted_entry = fields.Boolean('Restricted entry')

    @classmethod
    def __setup__(cls):
        super(Zone, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code),
                'Zone code must be unique'),
            ]

    def get_rec_name(self, name):
        if self.code:
            return self.code + ' - ' + self.description
        else:
            return self.description

    @classmethod
    def search_rec_name(cls, name, clause):
        field = None
        for field in ('code', 'description'):
            records = cls.search([(field,) + tuple(clause[1:])], limit=1)
            if records:
                break
        if records:
            return [(field,) + tuple(clause[1:])]
        return [(cls._rec_name,) + tuple(clause[1:])]


class Variety(ModelSQL, ModelView):
    'Variety'
    __name__ = 'lims.variety'
    _rec_name = 'description'

    code = fields.Char('Code', required=True)
    description = fields.Char('Description', required=True)
    varieties = fields.One2Many('lims.matrix.variety', 'variety',
        'Product Type - Matrix')

    @classmethod
    def __setup__(cls):
        super(Variety, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code),
                'Variety code must be unique'),
            ]

    def get_rec_name(self, name):
        if self.code:
            return self.code + ' - ' + self.description
        else:
            return self.description

    @classmethod
    def search_rec_name(cls, name, clause):
        field = None
        for field in ('code', 'description'):
            records = cls.search([(field,) + tuple(clause[1:])], limit=1)
            if records:
                break
        if records:
            return [(field,) + tuple(clause[1:])]
        return [(cls._rec_name,) + tuple(clause[1:])]


class MatrixVariety(ModelSQL, ModelView):
    'Product Type - Matrix - Variety'
    __name__ = 'lims.matrix.variety'

    product_type = fields.Many2One('lims.product.type', 'Product type',
        required=True)
    matrix = fields.Many2One('lims.matrix', 'Matrix', required=True)
    variety = fields.Many2One('lims.variety', 'Variety', required=True)


class PackagingIntegrity(ModelSQL, ModelView):
    'Packaging Integrity'
    __name__ = 'lims.packaging.integrity'
    _rec_name = 'description'

    code = fields.Char('Code', required=True)
    description = fields.Char('Description', required=True, translate=True)

    @classmethod
    def __setup__(cls):
        super(PackagingIntegrity, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code),
                'Packaging integrity code must be unique'),
            ]

    def get_rec_name(self, name):
        if self.code:
            return self.code + ' - ' + self.description
        else:
            return self.description

    @classmethod
    def search_rec_name(cls, name, clause):
        field = None
        for field in ('code', 'description'):
            records = cls.search([(field,) + tuple(clause[1:])], limit=1)
            if records:
                break
        if records:
            return [(field,) + tuple(clause[1:])]
        return [(cls._rec_name,) + tuple(clause[1:])]


class PackagingType(ModelSQL, ModelView):
    'Packaging Type'
    __name__ = 'lims.packaging.type'
    _rec_name = 'description'

    code = fields.Char('Code', required=True)
    description = fields.Char('Description', required=True, translate=True)

    @classmethod
    def __setup__(cls):
        super(PackagingType, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code),
                'Packaging type code must be unique'),
            ]

    def get_rec_name(self, name):
        if self.code:
            return self.code + ' - ' + self.description
        else:
            return self.description

    @classmethod
    def search_rec_name(cls, name, clause):
        field = None
        for field in ('code', 'description'):
            records = cls.search([(field,) + tuple(clause[1:])], limit=1)
            if records:
                break
        if records:
            return [(field,) + tuple(clause[1:])]
        return [(cls._rec_name,) + tuple(clause[1:])]


class FractionType(ModelSQL, ModelView):
    'Fraction Type'
    __name__ = 'lims.fraction.type'
    _rec_name = 'description'

    code = fields.Char('Code', required=True, translate=True)
    description = fields.Char('Description', required=True, translate=True)
    max_storage_time = fields.Integer('Maximum storage time (in months)')
    requalify = fields.Boolean('Requalify')
    control_charts = fields.Boolean('Available for Control Charts')
    report = fields.Boolean('Available for Results Report')
    plannable = fields.Boolean('Plannable')
    default_package_type = fields.Many2One('lims.packaging.type',
        'Default Package type')
    default_fraction_state = fields.Many2One('lims.packaging.integrity',
        'Default Fraction state')
    cie_fraction_type = fields.Boolean('Available for Blind Samples')

    @classmethod
    def __setup__(cls):
        super(FractionType, cls).__setup__()
        t = cls.__table__()
        cls._order.insert(0, ('code', 'ASC'))
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code),
                'Fraction type code must be unique'),
            ]

    @staticmethod
    def default_requalify():
        return False

    @staticmethod
    def default_control_charts():
        return False

    @staticmethod
    def default_report():
        return True

    @staticmethod
    def default_plannable():
        return True

    def get_rec_name(self, name):
        if self.code:
            return self.code + ' - ' + self.description
        else:
            return self.description

    @classmethod
    def search_rec_name(cls, name, clause):
        field = None
        for field in ('code', 'description'):
            records = cls.search([(field,) + tuple(clause[1:])], limit=1)
            if records:
                break
        if records:
            return [(field,) + tuple(clause[1:])]
        return [(cls._rec_name,) + tuple(clause[1:])]


class SampleProducer(ModelSQL, ModelView):
    'Sample Producer'
    __name__ = 'lims.sample.producer'

    party = fields.Many2One('party.party', 'Party', required=True)
    name = fields.Char('Name', required=True)


class Service(ModelSQL, ModelView):
    'Service'
    __name__ = 'lims.service'
    _rec_name = 'number'

    number = fields.Char('Number', select=True, readonly=True)
    create_date2 = fields.Function(fields.DateTime('Create Date'),
       'get_create_date2', searcher='search_create_date2')
    fraction = fields.Many2One('lims.fraction', 'Fraction', required=True,
        ondelete='CASCADE', select=True, depends=['number'],
        states={'readonly': Or(Bool(Eval('number')),
            Bool(Eval('context', {}).get('readonly', True))),
            })
    fraction_view = fields.Function(fields.Many2One('lims.fraction',
        'Fraction', states={'invisible': Not(Bool(Eval('_parent_fraction')))}),
        'on_change_with_fraction_view')
    sample = fields.Function(fields.Many2One('lims.sample', 'Sample'),
        'get_fraction_field',
        searcher='search_fraction_field')
    entry = fields.Function(fields.Many2One('lims.entry', 'Entry'),
        'get_fraction_field',
        searcher='search_fraction_field')
    party = fields.Function(fields.Many2One('party.party', 'Party'),
        'get_fraction_field',
        searcher='search_fraction_field')
    analysis = fields.Many2One('lims.analysis', 'Analysis/Set/Group',
        required=True, depends=['analysis_domain'],
        domain=['OR', ('id', '=', Eval('analysis')),
            ('id', 'in', Eval('analysis_domain'))],
        states={'readonly': Bool(Eval('context', {}).get('readonly', True))})
    analysis_view = fields.Function(fields.Many2One('lims.analysis',
        'Analysis/Set/Group'), 'get_views_field',
        searcher='search_views_field')
    analysis_domain = fields.Function(fields.Many2Many('lims.analysis',
        None, None, 'Analysis domain'),
        'on_change_with_analysis_domain')
    typification_domain = fields.Function(fields.Many2Many(
        'lims.typification', None, None, 'Typification domain'),
        'on_change_with_typification_domain')
    analysis_type = fields.Function(fields.Selection([
        ('analysis', 'Analysis'),
        ('set', 'Set'),
        ('group', 'Group'),
        ], 'Type', sort=False),
        'on_change_with_analysis_type', searcher='search_analysis_field')
    urgent = fields.Boolean('Urgent')
    priority = fields.Integer('Priority')
    report_date = fields.Date('Date agreed for result')
    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        domain=[('id', 'in', Eval('laboratory_domain'))],
        states={
            'required': Bool(Eval('laboratory_domain')),
            'readonly': Bool(Eval('context', {}).get('readonly', True)),
            },
        depends=['laboratory_domain'])
    laboratory_view = fields.Function(fields.Many2One('lims.laboratory',
        'Laboratory'), 'get_views_field')
    laboratory_domain = fields.Function(fields.Many2Many('lims.laboratory',
        None, None, 'Laboratory domain'),
        'on_change_with_laboratory_domain')
    method = fields.Many2One('lims.lab.method', 'Method',
        domain=['OR', ('id', '=', Eval('method')),
            ('id', 'in', Eval('method_domain'))],
        states={
            'required': Bool(Eval('method_domain')),
            'readonly': Bool(Eval('context', {}).get('readonly', True)),
            },
        depends=['method_domain'])
    method_view = fields.Function(fields.Many2One('lims.lab.method',
        'Method'), 'get_views_field')
    method_domain = fields.Function(fields.Many2Many('lims.lab.method',
        None, None, 'Method domain'), 'on_change_with_method_domain')
    device = fields.Many2One('lims.lab.device', 'Device',
        domain=[('id', 'in', Eval('device_domain'))],
        states={
            'required': Bool(Eval('device_domain')),
            'readonly': Bool(Eval('context', {}).get('readonly', True)),
            },
        depends=['device_domain'])
    device_view = fields.Function(fields.Many2One('lims.lab.device',
        'Device'), 'get_views_field')
    device_domain = fields.Function(fields.Many2Many('lims.lab.device',
        None, None, 'Device domain'), 'on_change_with_device_domain')
    comments = fields.Text('Comments',
        states={'readonly': Bool(Eval('context', {}).get('readonly', True))})
    analysis_detail = fields.One2Many('lims.entry.detail.analysis',
        'service', 'Analysis detail')
    confirmed = fields.Function(fields.Boolean('Confirmed'), 'get_confirmed',
        searcher='search_confirmed')
    confirmation_date = fields.Date('Confirmation date', readonly=True)
    divide = fields.Boolean('Divide')
    has_results_report = fields.Function(fields.Boolean('Results Report'),
        'get_has_results_report')
    manage_service_available = fields.Function(fields.Boolean(
        'Available for Manage services'), 'get_manage_service_available')
    icon = fields.Function(fields.Char("Icon"), 'get_icon')
    planned = fields.Function(fields.Boolean('Planned'), 'get_planned',
        searcher='search_planned')

    @classmethod
    def __setup__(cls):
        super(Service, cls).__setup__()
        cls._order.insert(0, ('number', 'DESC'))
        cls._error_messages.update({
            'no_service_sequence': ('There is no service sequence for '
                'the work year "%s".'),
            'delete_service': ('You can not delete service "%s" because '
                'its fraction is confirmed'),
            'duplicated_analysis': ('The analysis "%(analysis)s" is assigned '
                'more than once to the fraction "%(fraction)s"'),
            })

    @staticmethod
    def default_urgent():
        return False

    @staticmethod
    def default_priority():
        return 0

    @staticmethod
    def default_divide():
        return False

    @classmethod
    def validate(cls, services):
        super(Service, cls).validate(services)
        for service in services:
            service.check_duplicated_analysis()

    def check_duplicated_analysis(self):
        Analysis = Pool().get('lims.analysis')

        fraction_id = self.fraction.id
        services = self.search([
            ('fraction', '=', fraction_id),
            ('id', '!=', self.id)
            ])
        if services:
            analysis_ids = []
            for service in services:
                if service.analysis:
                    analysis_ids.append(service.analysis.id)
                    analysis_ids.extend(Analysis.get_included_analysis(
                        service.analysis.id))

            new_analysis_ids = [self.analysis.id]
            new_analysis_ids.extend(Analysis.get_included_analysis(
                self.analysis.id))
            for a_id in new_analysis_ids:
                if a_id in analysis_ids:
                    analysis = Analysis(a_id)
                    self.raise_user_error('duplicated_analysis', {
                        'analysis': analysis.rec_name,
                        'fraction': self.fraction.rec_name,
                        })

    @classmethod
    def create(cls, vlist):
        pool = Pool()
        LabWorkYear = pool.get('lims.lab.workyear')
        Sequence = pool.get('ir.sequence')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        workyear_id = LabWorkYear.find()
        workyear = LabWorkYear(workyear_id)
        sequence = workyear.get_sequence('service')
        if not sequence:
            cls.raise_user_error('no_service_sequence',
                (workyear.rec_name,))

        vlist = [x.copy() for x in vlist]
        for values in vlist:
            values['number'] = Sequence.get_id(sequence.id)
        services = super(Service, cls).create(vlist)

        if not Transaction().context.get('copying', False):
            cls.update_analysis_detail(services)
            aditional_services = cls.create_aditional_services(services)

            # Aditional processing for Manage Services
            if aditional_services and Transaction().context.get(
                    'manage_service', False):
                cls.copy_analysis_comments(aditional_services)
                cls.set_confirmation_date(aditional_services)
                analysis_detail = EntryDetailAnalysis.search([
                    ('service', 'in', [s.id for s in aditional_services])])
                if analysis_detail:
                    fraction = analysis_detail[0].fraction
                    EntryDetailAnalysis.create_notebook_lines(analysis_detail,
                        fraction)
                    EntryDetailAnalysis.write(analysis_detail, {
                        'state': 'unplanned',
                        })
                # from lims_account_invoice
                if 'trytond.modules.lims_account_invoice' in sys.modules:
                    for aditional_service in aditional_services:
                        aditional_service.create_invoice_line('out')

        fractions_ids = list(set(s.fraction.id for s in services))
        cls.set_shared_fraction(fractions_ids)
        return services

    @classmethod
    def write(cls, *args):
        super(Service, cls).write(*args)
        actions = iter(args)
        for services, vals in zip(actions, actions):
            change_detail = False
            for field in ('analysis', 'laboratory', 'method', 'device'):
                if vals.get(field):
                    change_detail = True
                    break
            if change_detail:
                cls.update_analysis_detail(services)
                fractions_ids = list(set(s.fraction.id for s in services))
                cls.set_shared_fraction(fractions_ids)

    @classmethod
    def delete(cls, services):
        if Transaction().user != 0:
            cls.check_delete(services)
        fractions_ids = list(set(s.fraction.id for s in services))
        super(Service, cls).delete(services)
        cls.set_shared_fraction(fractions_ids)

    @classmethod
    def check_delete(cls, services):
        for service in services:
            if service.fraction and service.fraction.confirmed:
                cls.raise_user_error('delete_service', (service.rec_name,))

    @staticmethod
    def update_analysis_detail(services):
        pool = Pool()
        Service = pool.get('lims.service')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        for service in services:
            to_delete = EntryDetailAnalysis.search([
                ('service', '=', service.id),
                ])
            if to_delete:
                with Transaction().set_user(0, set_context=True):
                    EntryDetailAnalysis.delete(to_delete)

            if service.analysis.behavior == 'additional':
                continue

            to_create = []
            service_context = {
                'product_type': service.fraction.product_type.id,
                'matrix': service.fraction.matrix.id,
                }
            analysis_data = []
            if service.analysis.type == 'analysis':
                laboratory_id = service.laboratory.id
                method_id = service.method.id if service.method else None
                device_id = service.device.id if service.device else None

                analysis_data.append({
                    'id': service.analysis.id,
                    'origin': service.analysis.code,
                    'laboratory': laboratory_id,
                    'method': method_id,
                    'device': device_id,
                    })
            else:
                analysis_data.extend(Service._get_included_analysis(
                    service.analysis, service.analysis.code,
                    service_context))

            if analysis_data:
                for analysis in analysis_data:
                    values = {}
                    values['service'] = service.id
                    values['analysis'] = analysis['id']
                    values['analysis_origin'] = analysis['origin']
                    values['laboratory'] = analysis['laboratory']
                    values['method'] = analysis['method']
                    values['device'] = analysis['device']
                    to_create.append(values)

            if to_create:
                with Transaction().set_user(0, set_context=True):
                    EntryDetailAnalysis.create(to_create)

    @staticmethod
    def _get_included_analysis(analysis, analysis_origin='',
            service_context=None):
        Typification = Pool().get('lims.typification')

        childs = []
        if analysis.included_analysis:
            for included in analysis.included_analysis:
                if (analysis.type == 'set' and
                        included.included_analysis.type == 'analysis'):
                    origin = analysis_origin
                else:
                    origin = (analysis_origin + ' > ' +
                        included.included_analysis.code)
                if included.included_analysis.type == 'analysis':

                    laboratory_id = included.laboratory.id

                    typifications = Typification.search([
                        ('product_type', '=', service_context['product_type']),
                        ('matrix', '=', service_context['matrix']),
                        ('analysis', '=', included.included_analysis),
                        ('by_default', '=', True),
                        ('valid', '=', True),
                        ])
                    method_id = (typifications[0].method.id if typifications
                        else None)

                    device_id = None
                    if included.included_analysis.devices:
                        for d in included.included_analysis.devices:
                            if (d.laboratory.id == laboratory_id and
                                    d.by_default is True):
                                device_id = d.device.id

                    childs.append({
                        'id': included.included_analysis.id,
                        'origin': origin,
                        'laboratory': laboratory_id,
                        'method': method_id,
                        'device': device_id,
                        })
                childs.extend(Service._get_included_analysis(
                    included.included_analysis, origin, service_context))
        return childs

    @staticmethod
    def create_aditional_services(services):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        Typification = pool.get('lims.typification')
        AnalysisLaboratory = pool.get('lims.analysis-laboratory')
        AnalysisDevice = pool.get('lims.analysis.device')
        Service = pool.get('lims.service')

        aditional_services = {}
        for service in services:
            entry_details = EntryDetailAnalysis.search([
                ('service', '=', service.id),
                ])
            for detail in entry_details:
                typifications = Typification.search([
                    ('product_type', '=', service.fraction.product_type.id),
                    ('matrix', '=', service.fraction.matrix.id),
                    ('analysis', '=', detail.analysis.id),
                    ('method', '=', detail.method),
                    ('valid', '=', True),
                    ])
                if not typifications:
                    continue
                typification = typifications[0]

                if typification.additional:
                    if service.fraction.id not in aditional_services:
                        aditional_services[service.fraction.id] = {}
                    if (typification.additional.id not in
                            aditional_services[service.fraction.id]):

                        aditional_services[service.fraction.id][
                                typification.additional.id] = {
                            'laboratory': None,
                            'method': None,
                            'device': None,
                            }

                if typification.additionals:
                    if service.fraction.id not in aditional_services:
                        aditional_services[service.fraction.id] = {}
                    for additional in typification.additionals:
                        if (additional.id not in
                                aditional_services[service.fraction.id]):

                            cursor.execute('SELECT laboratory '
                                'FROM "' + AnalysisLaboratory._table + '" '
                                'WHERE analysis = %s', (additional.id,))
                            res = cursor.fetchone()
                            laboratory_id = res and res[0] or None

                            cursor.execute('SELECT method '
                                'FROM "' + Typification._table + '" '
                                'WHERE product_type = %s '
                                    'AND matrix = %s '
                                    'AND analysis = %s '
                                    'AND valid IS TRUE '
                                    'AND by_default IS TRUE',
                                (service.fraction.product_type.id,
                                    service.fraction.matrix.id, additional.id))
                            res = cursor.fetchone()
                            method_id = res and res[0] or None

                            cursor.execute('SELECT device '
                                'FROM "' + AnalysisDevice._table + '" '
                                'WHERE analysis = %s '
                                    'AND laboratory = %s '
                                    'AND by_default IS TRUE',
                                (additional.id, laboratory_id))
                            res = cursor.fetchone()
                            device_id = res and res[0] or None

                            aditional_services[service.fraction.id][
                                    additional.id] = {
                                'laboratory': laboratory_id,
                                'method': method_id,
                                'device': device_id,
                                }

        if aditional_services:
            services_default = []
            for fraction_id, analysis in aditional_services.items():
                for analysis_id, service_data in analysis.items():
                    if not Service.search([
                            ('fraction', '=', fraction_id),
                            ('analysis', '=', analysis_id),
                            ]):
                        services_default.append({
                            'fraction': fraction_id,
                            'analysis': analysis_id,
                            'laboratory': service_data['laboratory'],
                            'method': service_data['method'],
                            'device': service_data['device'],
                            })
            return Service.create(services_default)

    @classmethod
    def set_shared_fraction(cls, fractions_ids):
        pool = Pool()
        Fraction = pool.get('lims.fraction')

        fractions = Fraction.search([
            ('id', 'in', fractions_ids),
            ])
        for fraction in fractions:
            shared = False
            labs = []
            for s in fraction.services:
                if not s.analysis:
                    continue
                if s.analysis.type == 'analysis':
                    if s.analysis.behavior == 'additional':
                        continue
                    labs.append(s.laboratory.id)
                else:
                    labs.extend(cls._get_analysis_included_labs(s.analysis))
            if len(set(labs)) > 1:
                shared = True
            if fraction.shared != shared:
                Fraction.write([fraction], {'shared': shared})

    @classmethod
    def _get_analysis_included_labs(cls, analysis):
        childs = []
        if analysis.included_analysis:
            for included in analysis.included_analysis:
                if included.included_analysis.type == 'analysis':
                    childs.append(included.laboratory.id)
                childs.extend(cls._get_analysis_included_labs(
                    included.included_analysis))
        return childs

    @classmethod
    def view_attributes(cls):
        return [
            ('//group[@id="invisible_fields"]', 'states', {
                    'invisible': True,
                    }),
            ]

    @classmethod
    def copy(cls, services, default=None):
        EntryDetailAnalysis = Pool().get('lims.entry.detail.analysis')

        if default is None:
            default = {}
        current_default = default.copy()
        current_default['confirmation_date'] = None
        current_default['analysis_detail'] = None

        detail_default = {}
        if current_default.get('method', None):
            detail_default['method'] = current_default['method']
        if current_default.get('device', None):
            detail_default['device'] = current_default['device']

        new_services = []
        for service in sorted(services, key=lambda x: x.number):
            with Transaction().set_context(copying=True):
                new_service, = super(Service, cls).copy([service],
                    default=current_default)
            detail_default['service'] = new_service.id
            EntryDetailAnalysis.copy(service.analysis_detail,
                default=detail_default)
            new_services.append(new_service)
        return new_services

    @staticmethod
    def copy_analysis_comments(services):
        pool = Pool()
        Fraction = pool.get('lims.fraction')

        comments = {}
        for service in services:
            if service.analysis.comments:
                fraction_id = service.fraction.id
                if fraction_id not in comments:
                    comments[fraction_id] = ''
                if comments[fraction_id]:
                    comments[fraction_id] += '\n'
                comments[fraction_id] += service.analysis.comments
        if comments:
            fractions_to_save = []
            for fraction_id, comment in comments.items():
                fraction = Fraction(fraction_id)
                if fraction.comments:
                    fraction.comments += '\n' + comment
                else:
                    fraction.comments = comment
                fractions_to_save.append(fraction)
            if fractions_to_save:
                Fraction.save(fractions_to_save)

    @staticmethod
    def set_confirmation_date(services, confirmation_date=None):
        pool = Pool()
        Date = pool.get('ir.date')
        Service = pool.get('lims.service')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        if not confirmation_date:
            confirmation_date = Date.today()
        Service.write(services, {
            'confirmation_date': confirmation_date,
            })
        analysis_details = EntryDetailAnalysis.search([
            ('service', 'in', [s.id for s in services]),
            ])
        if analysis_details:
            EntryDetailAnalysis.write(analysis_details, {
                'confirmation_date': confirmation_date,
                })

    @fields.depends('analysis', 'fraction', 'typification_domain',
        'laboratory')
    def on_change_analysis(self):
        Laboratory = Pool().get('lims.laboratory')
        laboratory = None
        method = None
        device = None
        if self.analysis:
            laboratories = self.on_change_with_laboratory_domain()
            if len(laboratories) == 1:
                laboratory = laboratories[0]
            methods = self.on_change_with_method_domain()
            if len(methods) == 1:
                method = methods[0]
            devices = self._on_change_with_device_domain(self.analysis,
                Laboratory(laboratory), True)
            if len(devices) == 1:
                device = devices[0]
        self.laboratory = laboratory
        self.method = method
        self.device = device

    @staticmethod
    def default_analysis_domain():
        return Transaction().context.get('analysis_domain', [])

    @fields.depends('fraction')
    def on_change_with_analysis_domain(self, name=None):
        if Transaction().context.get('analysis_domain'):
            return Transaction().context.get('analysis_domain')
        return []

    @staticmethod
    def default_typification_domain():
        return Transaction().context.get('typification_domain', [])

    @fields.depends('fraction')
    def on_change_with_typification_domain(self, name=None):
        if Transaction().context.get('typification_domain'):
            return Transaction().context.get('typification_domain')
        return []

    @fields.depends('analysis')
    def on_change_with_analysis_type(self, name=None):
        if self.analysis:
            return self.analysis.type
        return ''

    @staticmethod
    def default_fraction_view():
        if (Transaction().context.get('fraction', 0) > 0):
            return Transaction().context.get('fraction')
        return None

    @fields.depends('fraction')
    def on_change_with_fraction_view(self, name=None):
        if self.fraction:
            return self.fraction.id
        return None

    @staticmethod
    def default_sample():
        if (Transaction().context.get('sample', 0) > 0):
            return Transaction().context.get('sample')
        return None

    @fields.depends('fraction')
    def on_change_with_sample(self, name=None):
        if self.fraction:
            result = self.get_fraction_field((self,), ('sample',))
            return result['sample'][self.id]
        return None

    @staticmethod
    def default_entry():
        if (Transaction().context.get('entry', 0) > 0):
            return Transaction().context.get('entry')
        return None

    @fields.depends('fraction')
    def on_change_with_entry(self, name=None):
        if self.fraction:
            result = self.get_fraction_field((self,), ('entry',))
            return result['entry'][self.id]
        return None

    @staticmethod
    def default_party():
        if (Transaction().context.get('party', 0) > 0):
            return Transaction().context.get('party')
        return None

    @fields.depends('fraction')
    def on_change_with_party(self, name=None):
        if self.fraction:
            result = self.get_fraction_field((self,), ('party',))
            return result['party'][self.id]
        return None

    @fields.depends('analysis', 'laboratory')
    def on_change_laboratory(self):
        device = None
        if self.analysis and self.laboratory:
            devices = self._on_change_with_device_domain(self.analysis,
                self.laboratory, True)
            if len(devices) == 1:
                device = devices[0]
        self.device = device

    @fields.depends('analysis')
    def on_change_with_laboratory_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        AnalysisLaboratory = Pool().get('lims.analysis-laboratory')

        if not self.analysis:
            return []

        cursor.execute('SELECT DISTINCT(laboratory) '
            'FROM "' + AnalysisLaboratory._table + '" '
            'WHERE analysis = %s',
            (self.analysis.id,))
        res = cursor.fetchall()
        if not res:
            return []
        return [x[0] for x in res]

    @fields.depends('analysis', 'typification_domain')
    def on_change_with_method_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        Typification = Pool().get('lims.typification')

        if not self.analysis:
            return []

        typification_ids = ', '.join(str(t) for t in
            self.on_change_with_typification_domain())
        if not typification_ids:
            return []
        cursor.execute('SELECT DISTINCT(method) '
            'FROM "' + Typification._table + '" '
            'WHERE id IN (' + typification_ids + ') '
                'AND analysis = %s',
            (self.analysis.id,))
        res = cursor.fetchall()
        if not res:
            return []
        return [x[0] for x in res]

    @fields.depends('analysis', 'laboratory')
    def on_change_with_device_domain(self, name=None):
        return self._on_change_with_device_domain(self.analysis,
            self.laboratory)

    @staticmethod
    def _on_change_with_device_domain(analysis=None, laboratory=None,
            by_default=False):
        cursor = Transaction().connection.cursor()
        AnalysisDevice = Pool().get('lims.analysis.device')

        if not analysis or not laboratory:
            return []

        if by_default:
            by_default_clause = 'AND by_default = TRUE'
        else:
            by_default_clause = ''
        cursor.execute('SELECT DISTINCT(device) '
            'FROM "' + AnalysisDevice._table + '" '
            'WHERE analysis = %s  '
                'AND laboratory = %s ' +
                by_default_clause,
            (analysis.id, laboratory.id))
        res = cursor.fetchall()
        if not res:
            return []
        return [x[0] for x in res]

    @classmethod
    def get_views_field(cls, services, names):
        result = {}
        for name in names:
            field_name = name[:-5]
            result[name] = {}
            for s in services:
                field = getattr(s, field_name, None)
                result[name][s.id] = field.id if field else None
        return result

    @classmethod
    def search_views_field(cls, name, clause):
        return [(name[:-5],) + tuple(clause[1:])]

    @classmethod
    def search_analysis_field(cls, name, clause):
        if name == 'analysis_type':
            name = 'type'
        return [('analysis.' + name,) + tuple(clause[1:])]

    @classmethod
    def search_create_date2(cls, name, clause):
        cursor = Transaction().connection.cursor()
        operator_ = clause[1:2][0]
        cursor.execute('SELECT id '
                'FROM "' + cls._table + '" '
                'WHERE create_date' + operator_ + ' %s',
                clause[2:3])
        return [('id', 'in', [x[0] for x in cursor.fetchall()])]

    @classmethod
    def get_fraction_field(cls, services, names):
        result = {}
        for name in names:
            result[name] = {}
            if name == 'label':
                for s in services:
                    result[name][s.id] = getattr(s.fraction, name, None)
            else:
                for s in services:
                    field = getattr(s.fraction, name, None)
                    result[name][s.id] = field.id if field else None
        return result

    def get_create_date2(self, name):
        return self.create_date.replace(microsecond=0)

    @classmethod
    def search_fraction_field(cls, name, clause):
        return [('fraction.' + name,) + tuple(clause[1:])]

    @classmethod
    def order_create_date2(cls, tables):
        return cls.create_date.convert_order('create_date', tables, cls)

    def _order_analysis_field(name):
        def order_field(tables):
            Analysis = Pool().get('lims.analysis')
            field = Analysis._fields[name]
            table, _ = tables[None]
            analysis_tables = tables.get('analysis')
            if analysis_tables is None:
                analysis = Analysis.__table__()
                analysis_tables = {
                    None: (analysis, analysis.id == table.analysis),
                    }
                tables['analysis'] = analysis_tables
            return field.convert_order(name, analysis_tables, Analysis)
        return staticmethod(order_field)
    # Redefine convert_order function with 'order_%s' % field
    order_analysis_view = _order_analysis_field('id')
    order_analysis_type = _order_analysis_field('type')

    def _order_fraction_field(name):
        def order_field(tables):
            Fraction = Pool().get('lims.fraction')
            field = Fraction._fields[name]
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
    # Redefine convert_order function with 'order_%s' % field
    order_sample = _order_fraction_field('sample')
    order_entry = _order_fraction_field('entry')
    order_party = _order_fraction_field('party')

    def get_confirmed(self, name=None):
        if self.fraction:
            return self.fraction.confirmed
        return False

    @classmethod
    def search_confirmed(cls, name, clause):
        return [('fraction.confirmed',) + tuple(clause[1:])]

    @classmethod
    def get_has_results_report(cls, services, names):
        cursor = Transaction().connection.cursor()
        NotebookLine = Pool().get('lims.notebook.line')

        result = {}
        for name in names:
            result[name] = {}
            for s in services:
                cursor.execute('SELECT service '
                    'FROM "' + NotebookLine._table + '" '
                    'WHERE service = %s '
                        'AND results_report IS NOT NULL',
                    (s.id,))
                value = False
                if cursor.fetchone():
                    value = True
                result[name][s.id] = value
        return result

    def get_manage_service_available(self, name=None):
        NotebookLine = Pool().get('lims.notebook.line')

        planned_notebook_lines = NotebookLine.search([
            ('service', '=', self.id),
            ('planification', '!=', None),
            ])
        if planned_notebook_lines:
            return False
        return True

    def get_icon(self, name):
        if self.has_results_report:
            return 'lims-green'
        if not self.confirmed:
            return 'lims-red'
        return 'lims-white'

    def get_planned(self, name):
        if not self.analysis_detail:
            return False
        for ad in self.analysis_detail:
            if (ad.state in ('draft', 'unplanned') and
                    ad.analysis.behavior != 'internal_relation'):
                return False
        return True

    @classmethod
    def search_planned(cls, name, clause):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        Analysis = pool.get('lims.analysis')

        cursor.execute('SELECT DISTINCT(d.service) '
            'FROM "' + EntryDetailAnalysis._table + '" d '
                'INNER JOIN "' + Analysis._table + '" a '
                'ON a.id = d.analysis '
            'WHERE d.state IN (\'draft\', \'unplanned\') '
                'AND a.behavior != \'internal_relation\'')
        not_planned_ids = [s[0] for s in cursor.fetchall()]

        field, op, operand = clause
        if (op, operand) in (('=', True), ('!=', False)):
            return [('id', 'not in', not_planned_ids)]
        elif (op, operand) in (('=', False), ('!=', True)):
            return [('id', 'in', not_planned_ids)]
        else:
            return []


class Fraction(ModelSQL, ModelView):
    'Fraction'
    __name__ = 'lims.fraction'
    _rec_name = 'number'

    number = fields.Char('Number', select=True, readonly=True)
    create_date2 = fields.Function(fields.DateTime('Create Date'),
       'get_create_date2', searcher='search_create_date2')
    sample = fields.Many2One('lims.sample', 'Sample', required=True,
        ondelete='CASCADE', select=True, depends=['number'],
        states={'readonly': Bool(Eval('number'))})
    sample_view = fields.Function(fields.Many2One('lims.sample', 'Sample',
        states={'invisible': Not(Bool(Eval('_parent_sample')))}),
        'on_change_with_sample_view')
    entry = fields.Function(fields.Many2One('lims.entry', 'Entry'),
        'get_sample_field',
        searcher='search_sample_field')
    party = fields.Function(fields.Many2One('party.party', 'Party'),
        'get_sample_field',
        searcher='search_sample_field')
    label = fields.Function(fields.Char('Label'), 'get_sample_field',
        searcher='search_sample_field')
    type = fields.Many2One('lims.fraction.type', 'Fraction type',
        required=True)
    storage_location = fields.Many2One('stock.location', 'Storage location',
        required=True, domain=[('type', '=', 'storage')])
    storage_time = fields.Integer('Storage time (in months)', required=True)
    weight = fields.Float('Weight')
    weight_uom = fields.Many2One('product.uom', 'Weight UoM',
        domain=[('category.lims_only_available', '=', True)])
    packages_quantity = fields.Integer('Packages quantity', required=True)
    package_type = fields.Many2One('lims.packaging.type', 'Package type',
        required=True)
    size = fields.Float('Size')
    size_uom = fields.Many2One('product.uom', 'Size UoM',
        domain=[('category.lims_only_available', '=', True)])
    expiry_date = fields.Date('Expiry date', states={'readonly': True})
    discharge_date = fields.Date('Discharge date')
    countersample_location = fields.Many2One('stock.location',
        'Countersample location', readonly=True)
    countersample_date = fields.Date('Countersample date', readonly=True)
    fraction_state = fields.Many2One('lims.packaging.integrity',
        'Fraction state', required=True)
    services = fields.One2Many('lims.service', 'fraction', 'Services',
        states={'readonly': Bool(Eval('button_manage_services_available'))},
        context={
            'analysis_domain': Eval('analysis_domain'),
            'typification_domain': Eval('typification_domain'),
            'product_type': Eval('product_type'), 'matrix': Eval('matrix'),
            'fraction': Eval('id'), 'sample': Eval('sample'),
            'entry': Eval('entry'), 'party': Eval('party'),
            'readonly': False,
            },
        depends=['button_manage_services_available', 'analysis_domain',
            'typification_domain', 'product_type', 'matrix', 'sample',
            'entry', 'party',
            ])
    shared = fields.Boolean('Shared')
    comments = fields.Text('Comments')
    analysis_domain = fields.Function(fields.Many2Many('lims.analysis',
        None, None, 'Analysis domain'),
        'on_change_with_analysis_domain')
    typification_domain = fields.Function(fields.Many2Many(
        'lims.typification', None, None, 'Typification domain'),
        'on_change_with_typification_domain')
    product_type = fields.Function(fields.Many2One('lims.product.type',
        'Product type'),
        'on_change_with_product_type')
    matrix = fields.Function(fields.Many2One('lims.matrix', 'Matrix'),
        'on_change_with_matrix')
    button_manage_services_available = fields.Function(fields.Boolean(
        'Button manage services available'),
        'on_change_with_button_manage_services_available')
    confirmed = fields.Boolean('Confirmed')
    button_confirm_available = fields.Function(fields.Boolean(
        'Button confirm available'),
        'on_change_with_button_confirm_available')
    current_location = fields.Function(fields.Many2One('stock.location',
        'Current Location'), 'get_current_location',
        searcher='search_current_location')
    duplicated_analysis_message = fields.Text('Message', readonly=True,
        states={'invisible': Not(Bool(Eval('duplicated_analysis_message')))})
    has_results_report = fields.Function(fields.Boolean('Results Report'),
        'get_has_results_report', searcher='search_has_results_report')
    has_all_results_reported = fields.Function(fields.Boolean(
        'All results reported'), 'get_has_all_results_reported')
    waiting_confirmation = fields.Boolean('Waiting confirmation')
    entry_state = fields.Function(fields.Selection([
        ('draft', 'Draft'),
        ('ongoing', 'Ongoing'),
        ('pending', 'Administration pending'),
        ('closed', 'Closed'),
        ], 'Entry State'), 'get_entry_state', searcher='search_entry_state')
    icon = fields.Function(fields.Char("Icon"), 'get_icon')
    special_type = fields.Function(fields.Char('Fraction type'),
        'on_change_with_special_type',
        searcher='search_special_type')
    con_type = fields.Selection([
        ('', ''),
        ('con', 'CON'),
        ('coi', 'COI'),
        ('mrc', 'MRC'),
        ('sla', 'SLA'),
        ('itc', 'ITC'),
        ('itl', 'ITL'),
        ], 'Type', sort=False)
    con_original_fraction = fields.Many2One('lims.fraction',
        'Original fraction')
    bmz_type = fields.Selection([
        ('', ''),
        ('sla', 'SLA'),
        ('noinitialbmz', 'No initial BMZ'),
        ], 'Type', sort=False)
    bmz_product_type = fields.Many2One('lims.product.type', 'Product type')
    bmz_matrix = fields.Many2One('lims.matrix', 'Matrix')
    bmz_original_fraction = fields.Many2One('lims.fraction',
        'Original fraction')
    rm_type = fields.Selection([
        ('', ''),
        ('sla', 'SLA'),
        ('noinitialrm', 'No initial RM'),
        ], 'Type', sort=False)
    rm_product_type = fields.Many2One('lims.product.type', 'Product type')
    rm_matrix = fields.Many2One('lims.matrix', 'Matrix')
    rm_original_fraction = fields.Many2One('lims.fraction',
        'Original fraction')
    bre_product_type = fields.Many2One('lims.product.type', 'Product type')
    bre_matrix = fields.Many2One('lims.matrix', 'Matrix')
    bre_reagents = fields.One2Many('lims.fraction.reagent', 'fraction',
        'Reagents')
    mrt_product_type = fields.Many2One('lims.product.type', 'Product type')
    mrt_matrix = fields.Many2One('lims.matrix', 'Matrix')
    cie_fraction_type_available = fields.Function(fields.Boolean(
        'Available for Blind Sample'),
        'on_change_with_cie_fraction_type_available')
    cie_fraction_type = fields.Boolean('Blind Sample',
        states={'readonly': Not(Bool(Eval('cie_fraction_type_available')))},
        depends=['cie_fraction_type_available'])
    cie_original_fraction = fields.Many2One('lims.fraction',
        'Original fraction', states={'readonly': Bool(Eval('confirmed'))},
        depends=['confirmed'])

    @classmethod
    def __setup__(cls):
        super(Fraction, cls).__setup__()
        cls._order.insert(0, ('number', 'DESC'))
        cls._buttons.update({
            'manage_services': {
                'invisible': ~Eval('button_manage_services_available'),
                },
            'complete_services': {
                'invisible': ~Eval('button_manage_services_available'),
                },
            'confirm': {
                'invisible': ~Eval('button_confirm_available'),
                },
            'load_services': {
                'invisible': Or(Bool(Eval('button_manage_services_available')),
                    Bool(Eval('services'))),
                },
            })
        cls._error_messages.update({
            'missing_fraction_product': ('Missing "Fraction product" '
                'on Lims configuration'),
            'delete_fraction': ('You can not delete fraction "%s" because '
                'it is confirmed'),
            'duplicated_analysis': ('The analysis "%s" is assigned more'
                ' than once'),
            'not_services': ('You can not confirm fraction "%s" because '
                'has not services'),
            'not_divided': ('You can not confirm fraction because '
                'is not yet divided'),
            })

    @staticmethod
    def default_packages_quantity():
        return 1

    @staticmethod
    def default_storage_time():
        return 3

    @staticmethod
    def default_confirmed():
        return False

    @staticmethod
    def default_waiting_confirmation():
        return False

    @classmethod
    def get_next_number(cls, sample_id, f_count):
        Sample = Pool().get('lims.sample')

        samples = Sample.search([('id', '=', sample_id)])
        sample_number = samples[0].number
        fraction_number = cls.search_count([('sample', '=', sample_id)])
        fraction_number += f_count
        return '%s-%s' % (sample_number, fraction_number)

    @classmethod
    def create(cls, vlist):
        vlist = [x.copy() for x in vlist]
        f_count = {}
        for values in vlist:
            if not values['sample'] in f_count:
                f_count[values['sample']] = 0
            f_count[values['sample']] += 1
            values['number'] = cls.get_next_number(values['sample'],
                f_count[values['sample']])
        return super(Fraction, cls).create(vlist)

    @classmethod
    def view_attributes(cls):
        return [
            ('//group[@id="button_confirm"]', 'states', {
                    'invisible': ~Eval('button_confirm_available'),
                    }),
            ('//page[@id="cie"]', 'states', {
                    'invisible': Not(Bool(Eval('cie_fraction_type'))),
                    }),
            ('//page[@id="mrt"]', 'states', {
                    'invisible': Not(Bool(Equal(Eval('special_type'), 'mrt'))),
                    }),
            ('//page[@id="bre"]', 'states', {
                    'invisible': Not(Bool(Equal(Eval('special_type'), 'bre'))),
                    }),
            ('//page[@id="rm"]', 'states', {
                    'invisible': Not(Bool(Equal(Eval('special_type'), 'rm'))),
                    }),
            ('//page[@id="bmz"]', 'states', {
                    'invisible': Not(Bool(Equal(Eval('special_type'), 'bmz'))),
                    }),
            ('//page[@id="con"]', 'states', {
                    'invisible': Not(Bool(Equal(Eval('special_type'), 'con'))),
                    })]

    @classmethod
    def copy(cls, fractions, default=None):
        if default is None:
            default = {}

        with Transaction().set_context(_check_access=False):
            new_fractions = []
            for fraction in sorted(fractions, key=lambda x: x.number):
                current_default = default.copy()
                current_default['confirmed'] = False
                current_default['waiting_confirmation'] = False
                current_default['discharge_date'] = None
                current_default['expiry_date'] = None
                current_default['countersample_date'] = None
                current_default['countersample_location'] = None

                new_fraction, = super(Fraction, cls).copy([fraction],
                    default=current_default)
                new_fractions.append(new_fraction)
        return new_fractions

    @classmethod
    def check_delete(cls, fractions):
        for fraction in fractions:
            if fraction.confirmed:
                cls.raise_user_error('delete_fraction', (fraction.rec_name,))

    @classmethod
    def delete(cls, fractions):
        cls.check_delete(fractions)
        super(Fraction, cls).delete(fractions)

    @fields.depends('type', 'storage_location')
    def on_change_with_storage_time(self, name=None):
        if (self.type and self.type.max_storage_time):
            return self.type.max_storage_time
        if (self.storage_location and self.storage_location.storage_time):
            return self.storage_location.storage_time
        return 3

    @staticmethod
    def default_analysis_domain():
        return Transaction().context.get('analysis_domain', [])

    @fields.depends('sample')
    def on_change_with_analysis_domain(self, name=None):
        if Transaction().context.get('analysis_domain'):
            return Transaction().context.get('analysis_domain')
        if self.sample:
            return self.sample.on_change_with_analysis_domain()
        return []

    @staticmethod
    def default_typification_domain():
        return Transaction().context.get('typification_domain', [])

    @fields.depends('sample')
    def on_change_with_typification_domain(self, name=None):
        if Transaction().context.get('typification_domain'):
            return Transaction().context.get('typification_domain')
        if self.sample:
            return self.sample.on_change_with_typification_domain()
        return []

    @staticmethod
    def default_product_type():
        return Transaction().context.get('product_type', None)

    @fields.depends('sample')
    def on_change_with_product_type(self, name=None):
        if Transaction().context.get('product_type'):
            return Transaction().context.get('product_type')
        if self.sample and self.sample.product_type:
            return self.sample.product_type.id
        return None

    @staticmethod
    def default_matrix():
        return Transaction().context.get('matrix', None)

    @fields.depends('sample')
    def on_change_with_matrix(self, name=None):
        if Transaction().context.get('matrix'):
            return Transaction().context.get('matrix')
        if self.sample and self.sample.matrix:
            return self.sample.matrix.id
        return None

    @staticmethod
    def default_sample_view():
        if (Transaction().context.get('sample', 0) > 0):
            return Transaction().context.get('sample')
        return None

    @staticmethod
    def default_cie_fraction_type():
        return False

    @fields.depends('type')
    def on_change_with_special_type(self, name=None):
        Config = Pool().get('lims.configuration')
        if self.type:
            config = Config(1)
            if self.type == config.mcl_fraction_type:
                return 'mcl'
            elif self.type == config.con_fraction_type:
                return 'con'
            elif self.type == config.bmz_fraction_type:
                return 'bmz'
            elif self.type == config.rm_fraction_type:
                return 'rm'
            elif self.type == config.bre_fraction_type:
                return 'bre'
            elif self.type == config.mrt_fraction_type:
                return 'mrt'
            elif self.type == config.coi_fraction_type:
                return 'coi'
            elif self.type == config.mrc_fraction_type:
                return 'mrc'
            elif self.type == config.sla_fraction_type:
                return 'sla'
            elif self.type == config.itc_fraction_type:
                return 'itc'
            elif self.type == config.itl_fraction_type:
                return 'itl'
        return ''

    @classmethod
    def search_special_type(cls, name, clause):
        Config = Pool().get('lims.configuration')
        if clause[1] in ('=', '!='):
            types = [clause[2]]
        elif clause[1] in ('in', 'not in'):
            types = clause[2]
        else:
            return []
        if types:
            config = Config(1)
            res_type = []
            for type_ in types:
                if type_ == 'mcl':
                    res_type.append(config.mcl_fraction_type)
                if type_ == 'con':
                    res_type.append(config.con_fraction_type)
                if type_ == 'bmz':
                    res_type.append(config.bmz_fraction_type)
                if type_ == 'rm':
                    res_type.append(config.rm_fraction_type)
                if type_ == 'bre':
                    res_type.append(config.bre_fraction_type)
                if type_ == 'mrt':
                    res_type.append(config.mrt_fraction_type)
                if type_ == 'coi':
                    res_type.append(config.coi_fraction_type)
                if type_ == 'mrc':
                    res_type.append(config.mrc_fraction_type)
                if type_ == 'sla':
                    res_type.append(config.sla_fraction_type)
                if type_ == 'itc':
                    res_type.append(config.itc_fraction_type)
                if type_ == 'itl':
                    res_type.append(config.itl_fraction_type)
            if clause[1] in ('=', '!='):
                return [('type', clause[1], res_type[0])]
            elif clause[1] in ('in', 'not in'):
                return [('type', clause[1], res_type)]
        return []

    @fields.depends('sample')
    def on_change_with_sample_view(self, name=None):
        if self.sample:
            return self.sample.id
        return None

    @staticmethod
    def default_entry():
        if (Transaction().context.get('entry', 0) > 0):
            return Transaction().context.get('entry')
        return None

    @fields.depends('sample')
    def on_change_with_entry(self, name=None):
        if self.sample:
            result = self.get_sample_field((self,), ('entry',))
            return result['entry'][self.id]
        return None

    @staticmethod
    def default_party():
        if (Transaction().context.get('party', 0) > 0):
            return Transaction().context.get('party')
        return None

    @fields.depends('sample')
    def on_change_with_party(self, name=None):
        if self.sample:
            result = self.get_sample_field((self,), ('party',))
            return result['party'][self.id]
        return None

    @staticmethod
    def default_label():
        return Transaction().context.get('label', '')

    @fields.depends('sample', 'special_type', 'con_original_fraction',
        'services', 'create_date')
    def on_change_with_label(self, name=None):
        type = self.special_type
        if type == 'con':
            label = ''
            if self.con_original_fraction:
                label += self.con_original_fraction.label
            if self.services:
                if self.services[0].analysis:
                    label += ' ' + self.services[0].analysis.code
            if self.create_date:
                label += ' ' + str(datetime.date(self.create_date))
            return label
        elif type == 'bmz':
            label = 'BMZ'
            if self.services:
                if self.services[0].analysis:
                    label += ' ' + self.services[0].analysis.code
            if self.create_date:
                label += ' ' + str(datetime.date(self.create_date))
            return label
        elif type == 'rm':
            label = 'RM'
            if self.services:
                if self.services[0].analysis:
                    label += ' ' + self.services[0].analysis.code
            if self.create_date:
                label += ' ' + str(datetime.date(self.create_date))
            return label
        elif type == 'bre':
            label = 'BRE'
            if self.services:
                if self.services[0].analysis:
                    label += ' ' + self.services[0].analysis.code
            if self.create_date:
                label += ' ' + str(datetime.date(self.create_date))
            return label
        elif type == 'mrt':
            label = 'MRT'
            if self.services:
                if self.services[0].analysis:
                    label += ' ' + self.services[0].analysis.code
            if self.create_date:
                label += ' ' + str(datetime.date(self.create_date))
            return label
        else:
            if self.sample:
                result = self.get_sample_field((self,), ('label',))
                return result['label'][self.id]
            return ''

    @staticmethod
    def default_package_type():
        if Transaction().context.get('package_type'):
            return Transaction().context.get('package_type')
        return None

    @fields.depends('sample')
    def on_change_with_package_type(self, name=None):
        if self.sample:
            result = self.get_sample_field((self,), ('package_type',))
            return result['package_type'][self.id]
        return None

    @staticmethod
    def default_size():
        return Transaction().context.get('size', None)

    @fields.depends('sample')
    def on_change_with_size(self, name=None):
        if self.sample:
            result = self.get_sample_field((self,), ('size',))
            return result['size'][self.id]
        return None

    @staticmethod
    def default_size_uom():
        if Transaction().context.get('size_uom'):
            return Transaction().context.get('size_uom')
        return None

    @fields.depends('sample')
    def on_change_with_size_uom(self, name=None):
        if self.sample:
            result = self.get_sample_field((self,), ('size_uom',))
            return result['size_uom'][self.id]
        return None

    @staticmethod
    def default_fraction_state():
        if Transaction().context.get('fraction_state'):
            return Transaction().context.get('fraction_state')
        return None

    @fields.depends('sample')
    def on_change_with_fraction_state(self, name=None):
        if self.sample:
            result = self.get_sample_field((self,), ('fraction_state',))
            return result['fraction_state'][self.id]
        return None

    @classmethod
    def get_sample_field(cls, fractions, names):
        result = {}
        for name in names:
            result[name] = {}
            if name in ('label', 'size'):
                for f in fractions:
                    result[name][f.id] = getattr(f.sample, name, None)
            elif name == 'fraction_state':
                for f in fractions:
                    field = getattr(f.sample, 'package_state', None)
                    result[name][f.id] = field.id if field else None
            else:
                for f in fractions:
                    field = getattr(f.sample, name, None)
                    result[name][f.id] = field.id if field else None
        return result

    @classmethod
    def search_sample_field(cls, name, clause):
        return [('sample.' + name,) + tuple(clause[1:])]

    @classmethod
    def get_entry_state(cls, fractions, name):
        result = {}
        for f in fractions:
            result[f.id] = getattr(f.entry, 'state', None)
        return result

    @classmethod
    def search_entry_state(cls, name, clause):
        return [('sample.entry.state',) + tuple(clause[1:])]

    @fields.depends('confirmed')
    def on_change_with_button_manage_services_available(self, name=None):
        if self.confirmed:
            return True
        return False

    @fields.depends('confirmed', 'type')
    def on_change_with_cie_fraction_type_available(self, name=None):
        if not self.confirmed and self.type and self.type.cie_fraction_type:
            return True
        return False

    @classmethod
    @ModelView.button_action('lims.wiz_lims_manage_services')
    def manage_services(cls, fractions):
        pass

    @classmethod
    @ModelView.button_action('lims.wiz_lims_complete_services')
    def complete_services(cls, fractions):
        pass

    @classmethod
    @ModelView.button_action('lims.wiz_lims_load_services')
    def load_services(cls, fractions):
        pass

    @fields.depends('confirmed', 'sample')
    def on_change_with_button_confirm_available(self, name=None):
        if (not self.confirmed and self.sample and self.sample.entry and
                (self.sample.entry.state == 'ongoing')):
            return True
        return False

    @classmethod
    def check_divided_report(cls, fractions):
        pool = Pool()
        Service = pool.get('lims.service')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        services = Service.search([
            ('fraction', 'in', [f.id for f in fractions]),
            ('divide', '=', True),
            ])
        for service in services:
            if (EntryDetailAnalysis.search_count([
                    ('service', '=', service.id),
                    ('report_grouper', '!=', 0),
                    ]) == 0):
                cls.raise_user_error('not_divided')

    @classmethod
    @ModelView.button
    def confirm(cls, fractions):
        pool = Pool()
        Config = pool.get('lims.configuration')
        Service = pool.get('lims.service')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        Move = pool.get('stock.move')

        confirm_background = Config(1).entry_confirm_background

        cls.check_divided_report(fractions)
        fractions_to_save = []
        stock_moves_to_create = []
        for fraction in fractions:
            services = Service.search([('fraction', '=', fraction.id)])
            Service.copy_analysis_comments(services)
            Service.set_confirmation_date(services)
            fraction.create_laboratory_notebook()
            analysis_detail = EntryDetailAnalysis.search([
                ('fraction', '=', fraction.id)])
            if analysis_detail:
                EntryDetailAnalysis.create_notebook_lines(analysis_detail,
                    fraction)

            fraction.confirmed = True
            if confirm_background:
                fraction.waiting_confirmation = True
            else:
                stock_moves_to_create.append(fraction.create_stock_move())
            fractions_to_save.append(fraction)
        if stock_moves_to_create:
            with Transaction().set_context(check_current_location=False):
                Move.save(stock_moves_to_create)
                Move.assign(stock_moves_to_create)
                Move.do(stock_moves_to_create)
        cls.save(fractions_to_save)

        with Transaction().set_context(_check_access=False):
            fracts = cls.search([
                ('id', 'in', [f.id for f in fractions]),
                ])
        for fraction in fracts:
            fraction.update_detail_analysis()
            if fraction.cie_fraction_type:
                fraction.create_blind_samples()

    def create_laboratory_notebook(self):
        pool = Pool()
        Notebook = pool.get('lims.notebook')
        with Transaction().set_user(0):
            notebook = Notebook(
                fraction=self.id,
                )
            notebook.save()

    def create_stock_move(self):
        return self._get_stock_move()

    def _get_stock_move(self):
        pool = Pool()
        Config = pool.get('lims.configuration')
        Date = pool.get('ir.date')
        User = pool.get('res.user')
        Location = pool.get('stock.location')
        Move = pool.get('stock.move')

        config_ = Config(1)
        if config_.fraction_product:
            product = config_.fraction_product
        else:
            self.raise_user_error('missing_fraction_product')
        today = Date.today()
        company = User(Transaction().user).company
        if self.sample.entry.party.customer_location:
            from_location = self.sample.entry.party.customer_location
        else:
            locations = Location.search([('type', '=', 'customer')])
            from_location = locations[0] if len(locations) == 1 else None

        with Transaction().set_user(0, set_context=True):
            move = Move()
        move.product = product.id
        move.fraction = self.id
        move.quantity = self.packages_quantity
        move.uom = product.default_uom
        move.from_location = from_location
        move.to_location = self.storage_location
        move.company = company
        move.planned_date = today
        move.origin = self
        move.state = 'draft'
        return move

    @classmethod
    def confirm_waiting_fractions(cls):
        '''
        Cron - Confirm Waiting Fractions
        '''
        Move = Pool().get('stock.move')
        logger = logging.getLogger('lims')

        fractions = cls.search([
            ('waiting_confirmation', '=', True),
            ], order=[('id', 'ASC')])
        if fractions:
            logger.info('Cron - Confirming fractions:INIT')
            fractions_to_save = []
            stock_moves_to_create = []
            for fraction in fractions:
                fraction.waiting_confirmation = False
                stock_moves_to_create.append(fraction.create_stock_move())
                fractions_to_save.append(fraction)
            if stock_moves_to_create:
                with Transaction().set_context(check_current_location=False):
                    Move.save(stock_moves_to_create)
                    Move.assign(stock_moves_to_create)
                    Move.do(stock_moves_to_create)
            cls.save(fractions_to_save)
            logger.info('Cron - Confirming fractions:END')

    @fields.depends('services')
    def on_change_services(self, name=None):
        Analysis = Pool().get('lims.analysis')
        self.duplicated_analysis_message = ''
        if self.services:
            analysis_ids = []
            for service in self.services:
                if service.analysis:
                    new_analysis_ids = [service.analysis.id]
                    new_analysis_ids.extend(Analysis.get_included_analysis(
                        service.analysis.id))

                    for a_id in new_analysis_ids:
                        if a_id in analysis_ids:
                            analysis = Analysis(a_id)
                            self.duplicated_analysis_message = (
                                self.raise_user_error('duplicated_analysis',
                                    (analysis.rec_name,),
                                    raise_exception=False))
                            return
                    analysis_ids.extend(new_analysis_ids)

    def get_create_date2(self, name):
        return self.create_date.replace(microsecond=0)

    @classmethod
    def search_create_date2(cls, name, clause):
        cursor = Transaction().connection.cursor()
        operator_ = clause[1:2][0]
        cursor.execute('SELECT id '
                'FROM "' + cls._table + '" '
                'WHERE create_date' + operator_ + ' %s',
                clause[2:3])
        return [('id', 'in', [x[0] for x in cursor.fetchall()])]

    @fields.depends('countersample_date', 'storage_time')
    def on_change_with_expiry_date(self, name=None):
        if self.countersample_date:
            return self.countersample_date + relativedelta(
                months=self.storage_time)
        return None

    @classmethod
    def get_current_location(cls, fractions, name=None):
        cursor = Transaction().connection.cursor()
        Move = Pool().get('stock.move')

        result = {}
        for f in fractions:
            cursor.execute('SELECT to_location '
                'FROM "' + Move._table + '" '
                'WHERE fraction = %s '
                    'AND state IN (\'assigned\', \'done\') '
                'ORDER BY effective_date DESC, id DESC '
                'LIMIT 1', (f.id,))
            location = cursor.fetchone()
            result[f.id] = location[0] if location else None
        return result

    @classmethod
    def search_current_location(cls, name, domain=None):
        if not Transaction().context.get('check_current_location', True):
            return []

        cursor = Transaction().connection.cursor()
        pool = Pool()
        Fraction = pool.get('lims.fraction')
        Move = pool.get('stock.move')
        Location = pool.get('stock.location')

        def _search_current_location_eval_domain(line, domain):
            operator_funcs = {
                '=': operator.eq,
                '>=': operator.ge,
                '>': operator.gt,
                '<=': operator.le,
                '<': operator.lt,
                '!=': operator.ne,
                'in': lambda v, l: v in l,
                'not in': lambda v, l: v not in l,
                'ilike': lambda v, l: False,
                }
            field, op, operand = domain
            value = line.get(field)
            return operator_funcs[op](value, operand)

        if domain and domain[1] == 'ilike':
            locations = Location.search([
                ('code', '=', domain[2]),
                ], order=[])
            if not locations:
                locations = Location.search([
                    ('name',) + tuple(domain[1:]),
                    ], order=[])
                if not locations:
                    return []
            domain = ('current_location', 'in', [l.id for l in locations])

        cursor.execute('SELECT f.id, last_move.to_location '
            'FROM "' + Fraction._table + '" f '
                'INNER JOIN ( '
                    'SELECT DISTINCT ON (fraction) fraction, to_location '
                    'FROM "' + Move._table + '" '
                    'WHERE state IN (\'assigned\', \'done\') '
                    'ORDER BY fraction, effective_date DESC, id DESC '
                ') last_move '
                'ON f.id = last_move.fraction')

        processed_lines = [{
            'fraction': x[0],
            'current_location': x[1],
            } for x in cursor.fetchall()]

        record_ids = [line['fraction'] for line in processed_lines
            if _search_current_location_eval_domain(line, domain)]
        return [('id', 'in', record_ids)]

    @classmethod
    def order_create_date2(cls, tables):
        return cls.create_date.convert_order('create_date', tables, cls)

    def _order_sample_field(name):
        def order_field(tables):
            Sample = Pool().get('lims.sample')
            field = Sample._fields[name]
            table, _ = tables[None]
            sample_tables = tables.get('sample')
            if sample_tables is None:
                sample = Sample.__table__()
                sample_tables = {
                    None: (sample, sample.id == table.sample),
                    }
                tables['sample'] = sample_tables
            return field.convert_order(name, sample_tables, Sample)
        return staticmethod(order_field)
    # Redefine convert_order function with 'order_%s' % field
    order_entry = _order_sample_field('entry')
    order_party = _order_sample_field('party')
    order_label = _order_sample_field('label')
    order_product_type = _order_sample_field('product_type')
    order_matrix = _order_sample_field('matrix')

    @classmethod
    def get_has_results_report(cls, fractions, names):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Service = pool.get('lims.service')
        NotebookLine = pool.get('lims.notebook.line')

        result = {}
        for name in names:
            result[name] = {}
            for f in fractions:
                cursor.execute('SELECT s.fraction '
                    'FROM "' + Service._table + '" s '
                        'INNER JOIN "' + NotebookLine._table + '" nl '
                        'ON s.id = nl.service '
                    'WHERE s.fraction = %s '
                        'AND nl.results_report IS NOT NULL',
                    (f.id,))
                value = False
                if cursor.fetchone():
                    value = True
                result[name][f.id] = value
        return result

    @classmethod
    def search_has_results_report(cls, name, clause):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Service = pool.get('lims.service')
        NotebookLine = pool.get('lims.notebook.line')

        cursor.execute('SELECT DISTINCT(s.fraction) '
            'FROM "' + Service._table + '" s '
                'INNER JOIN "' + NotebookLine._table + '" nl '
                'ON s.id = nl.service '
            'WHERE nl.results_report IS NOT NULL')
        has_results_report = [x[0] for x in cursor.fetchall()]

        field, op, operand = clause
        if (op, operand) in (('=', True), ('!=', False)):
            return [('id', 'in', has_results_report)]
        elif (op, operand) in (('=', False), ('!=', True)):
            return [('id', 'not in', has_results_report)]
        else:
            return []

    def get_has_all_results_reported(self, name=None):
        NotebookLine = Pool().get('lims.notebook.line')
        notebook_lines = NotebookLine.search([
            ('analysis_detail.service.fraction', '=', self.id),
            ('report', '=', True),
            ('annulled', '=', False),
            ])
        if not notebook_lines:
            return False
        for nl in notebook_lines:
            if not nl.accepted:
                return False
            if not nl.results_report:
                return False
        return True

    def get_formated_number(self, format):
        formated_number = self.number

        number_parts = self.number.split('/')
        number_parts2 = number_parts[1].split('-')
        if len(number_parts2) < 2:         # 2014: "0000097-1/2014"
            number_parts2 = number_parts[0].split('-')
            sample_number = number_parts2[0]
            sample_year = number_parts[1]
            fraction_number = number_parts2[1]
        else:                              # 2015: "2015/0000017-1"
            sample_number = number_parts2[0]
            sample_year = number_parts[0]
            fraction_number = number_parts2[1]

        if format == 'sn-sy-fn':
            formated_number = (sample_number + '-' + sample_year + '-' +
                fraction_number)

        elif format == 'sy-sn-fn':
            formated_number = (sample_year + '-' + sample_number + '-' +
                fraction_number)

        elif format == 'pt-m-sn-sy-fn':
            formated_number = (self.product_type.code + '-' +
                self.matrix.code + '-' + sample_number + '-' +
                sample_year + '-' + fraction_number)

        elif format == 'pt-m-sy-sn-fn':
            formated_number = (self.product_type.code + '-' +
                self.matrix.code + '-' + sample_year + '-' +
                sample_number + '-' + fraction_number)

        return formated_number

    def get_icon(self, name):
        if self.has_results_report:
            return 'lims-green'
        if not self.confirmed:
            return 'lims-red'
        return 'lims-white'

    def update_detail_analysis(self):
        EntryDetailAnalysis = Pool().get('lims.entry.detail.analysis')

        analysis_details = EntryDetailAnalysis.search([
            ('fraction', '=', self.id),
            ])
        if analysis_details:
            EntryDetailAnalysis.write(analysis_details, {
                'state': 'unplanned',
                })

    def create_blind_samples(self):
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        BlindSample = pool.get('lims.blind_sample')
        Date = pool.get('ir.date')

        confirmation_date = Date.today()

        to_create = []
        nlines = NotebookLine.search([
            ('notebook.fraction', '=', self.id),
            ])
        for nline in nlines:
            detail = nline.analysis_detail
            record = {
                'line': nline.id,
                'entry': nline.fraction.entry.id,
                'sample': nline.fraction.sample.id,
                'fraction': nline.fraction.id,
                'service': nline.service.id,
                'analysis': nline.analysis.id,
                'repetition': nline.repetition,
                'date': confirmation_date,
                'min_value': detail.cie_min_value,
                'max_value': detail.cie_max_value,
                }
            original_fraction = self.cie_original_fraction
            if original_fraction:
                record['original_sample'] = original_fraction.sample.id
                record['original_fraction'] = original_fraction.id
                original_line = NotebookLine.search([
                    ('notebook.fraction', '=', original_fraction.id),
                    ('analysis', '=', nline.analysis.id),
                    ('repetition', '=', nline.repetition),
                    ])
                if original_line:
                    record['original_line'] = original_line[0].id
                    record['original_repetition'] = original_line[0].repetition
            to_create.append(record)
        if to_create:
            BlindSample.create(to_create)

    @staticmethod
    def get_stored_fractions():
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Move = pool.get('stock.move')
        Location = pool.get('stock.location')

        cursor.execute('SELECT DISTINCT ON (m.fraction) m.fraction, l.type '
            'FROM "' + Move._table + '" m '
                'INNER JOIN "' + Location._table + '" l '
                'ON m.to_location = l.id '
            'WHERE m.fraction IS NOT NULL '
                'AND m.state IN (\'assigned\', \'done\') '
            'ORDER BY m.fraction ASC, m.effective_date DESC, m.id DESC')
        return [x[0] for x in cursor.fetchall() if x[1] == 'storage']


class Sample(ModelSQL, ModelView):
    'Sample'
    __name__ = 'lims.sample'
    _rec_name = 'number'

    number = fields.Char('Number', select=True, readonly=True)
    create_date2 = fields.Function(fields.DateTime('Create Date'),
       'get_create_date2', searcher='search_create_date2')
    date = fields.DateTime('Date', required=True)
    date2 = fields.Function(fields.Date('Date'), 'get_date',
        searcher='search_date')
    entry = fields.Many2One('lims.entry', 'Entry', required=True,
        ondelete='CASCADE', select=True, depends=['number'],
        states={'readonly': Bool(Eval('number'))})
    entry_view = fields.Function(fields.Many2One('lims.entry', 'Entry',
        states={'invisible': Not(Bool(Eval('_parent_entry')))}),
        'on_change_with_entry_view')
    party = fields.Function(fields.Many2One('party.party', 'Party'),
        'get_entry_field',
        searcher='search_entry_field')
    producer = fields.Many2One('lims.sample.producer', 'Producer company',
        domain=[('party', '=', Eval('party'))], depends=['party'])
    label = fields.Char('Label', translate=True)
    sample_client_description = fields.Char('Product described by the client',
        translate=True)
    product_type = fields.Many2One('lims.product.type', 'Product type',
        states={'readonly': Bool(Eval('product_type_matrix_readonly'))},
        required=True, domain=[
            ('id', 'in', Eval('product_type_domain')),
            ], depends=['product_type_domain', 'product_type_matrix_readonly'])
    product_type_view = fields.Function(fields.Many2One('lims.product.type',
        'Product type'), 'get_views_field', searcher='search_views_field')
    product_type_domain = fields.Function(fields.Many2Many(
        'lims.product.type', None, None, 'Product type domain'),
        'on_change_with_product_type_domain')
    matrix = fields.Many2One('lims.matrix', 'Matrix', required=True,
        states={'readonly': Bool(Eval('product_type_matrix_readonly'))},
        domain=[
            ('id', 'in', Eval('matrix_domain')),
            ], depends=['matrix_domain', 'product_type_matrix_readonly'])
    matrix_view = fields.Function(fields.Many2One('lims.matrix',
        'Matrix'), 'get_views_field', searcher='search_views_field')
    matrix_domain = fields.Function(fields.Many2Many('lims.matrix',
        None, None, 'Matrix domain'),
        'on_change_with_matrix_domain')
    product_type_matrix_readonly = fields.Function(fields.Boolean(
        'Product type and Matrix readonly'),
        'get_product_type_matrix_readonly')
    obj_description = fields.Many2One('lims.objective_description',
        'Objective description', depends=['product_type', 'matrix'],
        domain=[
            ('product_type', '=', Eval('product_type')),
            ('matrix', '=', Eval('matrix')),
            ])
    obj_description_manual = fields.Char('Manual Objective description',
        translate=True, states={'readonly': Bool(Eval('obj_description'))},
        depends=['obj_description'])
    package_state = fields.Many2One('lims.packaging.integrity',
        'Package state')
    package_type = fields.Many2One('lims.packaging.type', 'Package type')
    packages_quantity = fields.Integer('Packages quantity', required=True)
    size = fields.Float('Size')
    size_uom = fields.Many2One('product.uom', 'Size UoM',
        domain=[('category.lims_only_available', '=', True)])
    restricted_entry = fields.Boolean('Restricted entry',
        states={'readonly': True})
    zone = fields.Many2One('lims.zone', 'Zone', required=True)
    trace_report = fields.Boolean('Trace report')
    fractions = fields.One2Many('lims.fraction', 'sample', 'Fractions',
        context={
            'analysis_domain': Eval('analysis_domain'),
            'typification_domain': Eval('typification_domain'),
            'product_type': Eval('product_type'), 'matrix': Eval('matrix'),
            'sample': Eval('id'), 'entry': Eval('entry'),
            'party': Eval('party'), 'label': Eval('label'),
            'package_type': Eval('package_type'), 'size': Eval('size'),
            'size_uom': Eval('size_uom'),
            'fraction_state': Eval('package_state'),
            },
        depends=['analysis_domain', 'typification_domain', 'entry',
            'party', 'label'])
    report_comments = fields.Text('Report comments', translate=True)
    comments = fields.Text('Comments')
    variety = fields.Many2One('lims.variety', 'Variety',
        domain=[('varieties.matrix', '=', Eval('matrix'))],
        depends=['matrix'])
    analysis_domain = fields.Function(fields.Many2Many('lims.analysis',
        None, None, 'Analysis domain'), 'on_change_with_analysis_domain')
    typification_domain = fields.Function(fields.Many2Many(
        'lims.typification', None, None, 'Typification domain'),
        'on_change_with_typification_domain')
    confirmed = fields.Function(fields.Boolean('Confirmed'), 'get_confirmed')
    has_results_report = fields.Function(fields.Boolean('Results Report'),
        'get_has_results_report')
    icon = fields.Function(fields.Char("Icon"), 'get_icon')

    @classmethod
    def __setup__(cls):
        super(Sample, cls).__setup__()
        cls._order.insert(0, ('number', 'DESC'))
        cls._error_messages.update({
            'no_sample_sequence': ('There is no sample sequence for '
                'the work year "%s".'),
            'duplicated_label': ('The label "%s" is already present in '
                'another sample'),
            'delete_sample': ('You can not delete sample "%s" because '
                'its entry is not in draft state'),
            })

    @staticmethod
    def default_date():
        return datetime.now()

    @staticmethod
    def default_restricted_entry():
        return False

    @staticmethod
    def default_trace_report():
        return False

    @classmethod
    def copy(cls, samples, default=None):
        if default is None:
            default = {}

        new_samples = []
        for sample in sorted(samples, key=lambda x: x.number):
            new_sample, = super(Sample, cls).copy([sample],
                default=default)
            new_samples.append(new_sample)
        return new_samples

    def get_date(self, name):
        pool = Pool()
        Company = pool.get('company.company')

        date = self.date
        if not date:
            return None
        company_id = Transaction().context.get('company')
        if company_id:
            date = Company(company_id).convert_timezone_datetime(date)
        return date.date()

    def get_create_date2(self, name):
        return self.create_date.replace(microsecond=0)

    @classmethod
    def search_date(cls, name, clause):
        pool = Pool()
        Company = pool.get('company.company')
        cursor = Transaction().connection.cursor()

        timezone = None
        company_id = Transaction().context.get('company')
        if company_id:
            timezone = Company(company_id).timezone
        timezone_datetime = 'date::timestamp AT TIME ZONE \'UTC\''
        if timezone:
            timezone_datetime += ' AT TIME ZONE \'' + timezone + '\''

        operator_ = clause[1:2][0]
        cursor.execute('SELECT id '
                'FROM "' + cls._table + '" '
                'WHERE (' + timezone_datetime + ')::date ' +
                operator_ + ' %s::date', clause[2:3])
        return [('id', 'in', [x[0] for x in cursor.fetchall()])]

    @classmethod
    def search_create_date2(cls, name, clause):
        cursor = Transaction().connection.cursor()
        operator_ = clause[1:2][0]
        cursor.execute('SELECT id '
                'FROM "' + cls._table + '" '
                'WHERE create_date' + operator_ + ' %s',
                clause[2:3])
        return [('id', 'in', [x[0] for x in cursor.fetchall()])]

    @classmethod
    def create(cls, vlist):
        pool = Pool()
        LabWorkYear = pool.get('lims.lab.workyear')
        Sequence = pool.get('ir.sequence')

        workyear_id = LabWorkYear.find()
        workyear = LabWorkYear(workyear_id)
        sequence = workyear.get_sequence('sample')
        if not sequence:
            cls.raise_user_error('no_sample_sequence',
                (workyear.rec_name,))

        vlist = [x.copy() for x in vlist]
        for values in vlist:
            values['number'] = Sequence.get_id(sequence.id)
        samples = super(Sample, cls).create(vlist)
        for sample in samples:
            sample.warn_duplicated_label()
        return samples

    def warn_duplicated_label(self):
        return  # deactivated
        if self.label:
            duplicated = self.search([
                ('entry', '=', self.entry.id),
                ('label', '=', self.label),
                ('id', '!=', self.id),
                ])
            if duplicated:
                self.raise_user_warning('lims_sample_label@%s' %
                    self.number, 'duplicated_label', self.label)

    @classmethod
    def write(cls, *args):
        super(Sample, cls).write(*args)
        actions = iter(args)
        for samples, vals in zip(actions, actions):
            if vals.get('label'):
                for sample in samples:
                    sample.warn_duplicated_label()

    @fields.depends('product_type', 'matrix', 'zone')
    def on_change_with_restricted_entry(self, name=None):
        return (self.product_type and self.product_type.restricted_entry and
            self.matrix and self.matrix.restricted_entry and
            self.zone and self.zone.restricted_entry)

    @fields.depends('product_type', 'matrix')
    def on_change_with_analysis_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Typification = pool.get('lims.typification')
        CalculatedTypification = pool.get('lims.typification.calculated')
        Analysis = pool.get('lims.analysis')

        if not self.product_type or not self.matrix:
            return []

        cursor.execute('SELECT DISTINCT(analysis) '
            'FROM "' + Typification._table + '" '
            'WHERE product_type = %s '
                'AND matrix = %s '
                'AND valid',
            (self.product_type.id, self.matrix.id))
        typified_analysis = [a[0] for a in cursor.fetchall()]
        if not typified_analysis:
            return []

        cursor.execute('SELECT id '
            'FROM "' + Analysis._table + '" '
            'WHERE type = \'analysis\' '
                'AND behavior IN (\'normal\', \'internal_relation\') '
                'AND disable_as_individual IS TRUE '
                'AND state = \'active\'')
        disabled_analysis = [a[0] for a in cursor.fetchall()]
        if disabled_analysis:
            typified_analysis = list(set(typified_analysis) -
                set(disabled_analysis))

        cursor.execute('SELECT DISTINCT(analysis) '
            'FROM "' + CalculatedTypification._table + '" '
            'WHERE product_type = %s '
                'AND matrix = %s',
            (self.product_type.id, self.matrix.id))
        typified_sets_groups = [a[0] for a in cursor.fetchall()]

        cursor.execute('SELECT id '
            'FROM "' + Analysis._table + '" '
            'WHERE behavior = \'additional\' '
                'AND state = \'active\'')
        additional_analysis = [a[0] for a in cursor.fetchall()]

        return typified_analysis + typified_sets_groups + additional_analysis

    @fields.depends('product_type', 'matrix')
    def on_change_with_typification_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        Typification = Pool().get('lims.typification')

        if not self.product_type or not self.matrix:
            return []

        cursor.execute('SELECT id '
            'FROM "' + Typification._table + '" '
            'WHERE product_type = %s '
                'AND matrix = %s '
                'AND valid',
            (self.product_type.id, self.matrix.id))
        res = cursor.fetchall()
        if not res:
            return []
        return [x[0] for x in res]

    @staticmethod
    def default_product_type_domain():
        cursor = Transaction().connection.cursor()
        Typification = Pool().get('lims.typification')

        cursor.execute('SELECT DISTINCT(product_type) '
            'FROM "' + Typification._table + '" '
            'WHERE valid')
        res = cursor.fetchall()
        if not res:
            return []
        return [x[0] for x in res]

    def on_change_with_product_type_domain(self, name=None):
        return self.default_product_type_domain()

    @fields.depends('product_type')
    def on_change_product_type(self):
        matrix = None
        if self.product_type:
            matrixs = self.on_change_with_matrix_domain()
            if len(matrixs) == 1:
                matrix = matrixs[0]
        self.matrix = matrix

    @fields.depends('product_type')
    def on_change_with_matrix_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        Typification = Pool().get('lims.typification')

        if not self.product_type:
            return []

        cursor.execute('SELECT DISTINCT(matrix) '
            'FROM "' + Typification._table + '" '
            'WHERE product_type = %s '
            'AND valid',
            (self.product_type.id,))
        res = cursor.fetchall()
        if not res:
            return []
        return [x[0] for x in res]

    def get_product_type_matrix_readonly(self, name=None):
        pool = Pool()
        Service = pool.get('lims.service')
        if Service.search_count([('sample', '=', self.id)]) != 0:
            return True
        return False

    @fields.depends('product_type', 'matrix')
    def on_change_with_obj_description(self):
        cursor = Transaction().connection.cursor()
        ObjectiveDescription = Pool().get('lims.objective_description')

        if not self.product_type or not self.matrix:
            return None

        cursor.execute('SELECT id '
            'FROM "' + ObjectiveDescription._table + '" '
            'WHERE product_type = %s '
                'AND matrix = %s',
            (self.product_type.id, self.matrix.id))
        res = cursor.fetchone()
        return res and res[0] or None

    @classmethod
    def check_delete(cls, samples):
        for sample in samples:
            if sample.entry and sample.entry.state != 'draft':
                cls.raise_user_error('delete_sample', (sample.rec_name,))

    @classmethod
    def delete(cls, samples):
        cls.check_delete(samples)
        super(Sample, cls).delete(samples)

    @staticmethod
    def default_entry_view():
        if (Transaction().context.get('entry', 0) > 0):
            return Transaction().context.get('entry')
        return None

    @fields.depends('entry')
    def on_change_with_entry_view(self, name=None):
        if self.entry:
            return self.entry.id
        return None

    @staticmethod
    def default_party():
        if (Transaction().context.get('party', 0) > 0):
            return Transaction().context.get('party')
        return None

    @staticmethod
    def default_zone():
        Party = Pool().get('party.party')

        if (Transaction().context.get('party', 0) > 0):
            party = Party(Transaction().context.get('party'))
            if party.entry_zone:
                return party.entry_zone.id

    @fields.depends('entry')
    def on_change_with_party(self, name=None):
        if self.entry:
            result = self.get_entry_field((self,), ('party',))
            return result['party'][self.id]
        return None

    @classmethod
    def get_views_field(cls, samples, names):
        result = {}
        for name in names:
            field_name = name[:-5]
            result[name] = {}
            for s in samples:
                field = getattr(s, field_name, None)
                result[name][s.id] = field.id if field else None
        return result

    @classmethod
    def search_views_field(cls, name, clause):
        return [(name[:-5],) + tuple(clause[1:])]

    @classmethod
    def get_entry_field(cls, samples, names):
        result = {}
        for name in names:
            result[name] = {}
            for s in samples:
                field = getattr(s.entry, name, None)
                result[name][s.id] = field.id if field else None
        return result

    @classmethod
    def search_entry_field(cls, name, clause):
        return [('entry.' + name,) + tuple(clause[1:])]

    @staticmethod
    def order_product_type_view(tables):
        ProductType = Pool().get('lims.product.type')
        field = ProductType._fields['id']
        table, _ = tables[None]
        product_type_tables = tables.get('product_type')
        if product_type_tables is None:
            product_type = ProductType.__table__()
            product_type_tables = {
                None: (product_type, product_type.id == table.product_type),
                }
            tables['product_type'] = product_type_tables
        return field.convert_order('id', product_type_tables, ProductType)

    @staticmethod
    def order_matrix_view(tables):
        Matrix = Pool().get('lims.matrix')
        field = Matrix._fields['id']
        table, _ = tables[None]
        matrix_tables = tables.get('matrix')
        if matrix_tables is None:
            matrix = Matrix.__table__()
            matrix_tables = {
                None: (matrix, matrix.id == table.matrix),
                }
            tables['matrix'] = matrix_tables
        return field.convert_order('id', matrix_tables, Matrix)

    def get_confirmed(self, name=None):
        if not self.fractions:
            return False
        for fraction in self.fractions:
            if not fraction.confirmed:
                return False
        return True

    def get_icon(self, name):
        if self.has_results_report:
            return 'lims-green'
        if not self.confirmed:
            return 'lims-red'
        return 'lims-white'

    @classmethod
    def order_create_date2(cls, tables):
        return cls.create_date.convert_order('create_date', tables, cls)

    @staticmethod
    def order_party(tables):
        Entry = Pool().get('lims.entry')
        field = Entry._fields['party']
        table, _ = tables[None]
        entry_tables = tables.get('entry')
        if entry_tables is None:
            entry = Entry.__table__()
            entry_tables = {
                None: (entry, entry.id == table.entry),
                }
            tables['entry'] = entry_tables
        return field.convert_order('party', entry_tables, Entry)

    @classmethod
    def get_has_results_report(cls, samples, names):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Fraction = pool.get('lims.fraction')
        Service = pool.get('lims.service')
        NotebookLine = pool.get('lims.notebook.line')

        result = {}
        for name in names:
            result[name] = {}
            for s in samples:
                cursor.execute('SELECT f.sample '
                    'FROM "' + Fraction._table + '" f '
                        'INNER JOIN "' + Service._table + '" s '
                        'ON f.id = s.fraction '
                        'INNER JOIN "' + NotebookLine._table + '" nl '
                        'ON s.id = nl.service '
                    'WHERE f.sample = %s '
                        'AND nl.results_report IS NOT NULL',
                    (s.id,))
                value = False
                if cursor.fetchone():
                    value = True
                result[name][s.id] = value
        return result


class DuplicateSampleStart(ModelView):
    'Copy Sample'
    __name__ = 'lims.sample.duplicate.start'

    sample = fields.Many2One('lims.sample', 'Sample', readonly=True)
    date = fields.DateTime('Date', required=True)
    labels = fields.Text('Labels')


class DuplicateSample(Wizard):
    'Copy Sample'
    __name__ = 'lims.sample.duplicate'

    start = StateView('lims.sample.duplicate.start',
        'lims.lims_duplicate_sample_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Copy', 'duplicate', 'tryton-ok', default=True),
            ])
    duplicate = StateTransition()

    def default_start(self, fields):
        Sample = Pool().get('lims.sample')
        sample = Sample(Transaction().context['active_id'])
        return {
            'sample': sample.id,
            'date': sample.date,
            }

    def transition_duplicate(self):
        Sample = Pool().get('lims.sample')

        sample = self.start.sample
        date = self.start.date
        labels_list = self._get_labels_list(self.start.labels)
        for label in labels_list:
            Sample.copy([sample], default={
                'label': label,
                'date': date,
                })
        return 'end'

    def _get_labels_list(self, labels=None):
        if not labels:
            return [None]
        return labels.split('\n')


class DuplicateSampleFromEntryStart(ModelView):
    'Copy Sample'
    __name__ = 'lims.entry.duplicate_sample.start'

    entry = fields.Many2One('lims.entry', 'Entry')
    sample = fields.Many2One('lims.sample', 'Sample', required=True,
        domain=[('entry', '=', Eval('entry'))], depends=['entry'])
    date = fields.DateTime('Date', required=True)
    labels = fields.Text('Labels')

    @fields.depends('sample')
    def on_change_with_date(self, name=None):
        if self.sample:
            return self.sample.date
        return False


class DuplicateSampleFromEntry(Wizard):
    'Copy Sample'
    __name__ = 'lims.entry.duplicate_sample'

    start = StateView('lims.entry.duplicate_sample.start',
        'lims.lims_duplicate_sample_from_entry_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Copy', 'duplicate', 'tryton-ok', default=True),
            ])
    duplicate = StateTransition()

    def default_start(self, fields):
        return {
            'entry': Transaction().context['active_id'],
            }

    def transition_duplicate(self):
        Sample = Pool().get('lims.sample')

        sample = self.start.sample
        date = self.start.date
        labels_list = self._get_labels_list(self.start.labels)
        for label in labels_list:
            Sample.copy([sample], default={
                'label': label,
                'date': date,
                })
        return 'end'

    def _get_labels_list(self, labels=None):
        if not labels:
            return [None]
        return labels.split('\n')


class ManageServices(Wizard):
    'Manage Services'
    __name__ = 'lims.manage_services'

    start_state = 'check'
    check = StateTransition()
    start = StateView('lims.fraction',
        'lims.lims_manage_services_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Ok', 'ok', 'tryton-ok', default=True),
            ])
    ok = StateTransition()

    @classmethod
    def __setup__(cls):
        super(ManageServices, cls).__setup__()
        cls._error_messages.update({
            'counter_sample_date':
                'Reverse counter sample storage to enter the service ',
            })

    def default_start(self, fields):
        Fraction = Pool().get('lims.fraction')

        fraction = Fraction(Transaction().context['active_id'])
        if not fraction:
            return {}

        not_planned_services_ids = [s.id for s in fraction.services if
            s.manage_service_available]
        analysis_domain_ids = fraction.on_change_with_analysis_domain()
        typification_domain_ids = fraction.on_change_with_typification_domain()

        default = {
            'id': fraction.id,
            'sample': fraction.sample.id,
            'entry': fraction.entry.id,
            'party': fraction.party.id,
            'services': not_planned_services_ids,
            'analysis_domain': analysis_domain_ids,
            'typification_domain': typification_domain_ids,
            'product_type': fraction.product_type.id,
            'matrix': fraction.matrix.id,
            }
        return default

    def transition_check(self):
        Fraction = Pool().get('lims.fraction')

        fraction = Fraction(Transaction().context['active_id'])
        if fraction.countersample_date is None:
            return 'start'
        else:
            self.raise_user_error('counter_sample_date')
        return 'end'

    def transition_ok(self):
        pool = Pool()
        Entry = pool.get('lims.entry')
        Fraction = pool.get('lims.fraction')

        delete_ack_report_cache = False
        fraction = Fraction(Transaction().context['active_id'])

        original_services = [s for s in fraction.services if
            s.manage_service_available]
        actual_services = self.start.services

        for service in original_services:
            if service not in actual_services:
                self.delete_service(service)
                delete_ack_report_cache = True

        for service in actual_services:
            if service not in original_services:
                self.create_service(service, fraction)
                delete_ack_report_cache = True

        for original_service in original_services:
            for actual_service in actual_services:
                if original_service == actual_service:
                    for field in self._get_comparison_fields():
                        if (getattr(original_service, field) !=
                                getattr(actual_service, field)):
                            self.update_service(original_service,
                                actual_service, fraction, field)
                            delete_ack_report_cache = True
                            break

        if delete_ack_report_cache:
            entry = Entry(fraction.entry.id)
            entry.ack_report_format = None
            entry.ack_report_cache = None
            entry.save()

        original_services = [s for s in fraction.services if not s.planned]
        actual_services = self.start.services

        for original_service in original_services:
            for actual_service in actual_services:
                if original_service == actual_service:
                    update_cie_data = True
                    for field in ('analysis', 'laboratory', 'method',
                            'device'):
                        if (getattr(original_service, field) !=
                                getattr(actual_service, field)):
                            update_cie_data = False
                            break
                    if update_cie_data:
                        for detail in actual_service.analysis_detail:
                            detail.save()

        return 'end'

    def create_service(self, service, fraction):
        pool = Pool()
        Service = pool.get('lims.service')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        service_create = [{
            'fraction': fraction.id,
            'sample': service.sample.id,
            'analysis': service.analysis.id,
            'urgent': service.urgent,
            'priority': service.priority,
            'report_date': service.report_date,
            'laboratory': (service.laboratory.id if service.laboratory
                else None),
            'method': service.method.id if service.method else None,
            'device': service.device.id if service.device else None,
            'comments': service.comments,
            'divide': service.divide,
            }]
        with Transaction().set_context(manage_service=True):
            new_service, = Service.create(service_create)

        Service.copy_analysis_comments([new_service])
        Service.set_confirmation_date([new_service])
        analysis_detail = EntryDetailAnalysis.search([
            ('service', '=', new_service.id)])
        if analysis_detail:
            EntryDetailAnalysis.create_notebook_lines(analysis_detail,
                fraction)

        EntryDetailAnalysis.write(analysis_detail, {
            'state': 'unplanned',
            })
        if fraction.cie_fraction_type:
            self._create_blind_samples(analysis_detail, fraction)

        return new_service

    def delete_service(self, service):
        Service = Pool().get('lims.service')
        with Transaction().set_user(0, set_context=True):
            Service.delete([service])

    def update_service(self, original_service, actual_service, fraction,
            field_changed):
        pool = Pool()
        Service = pool.get('lims.service')
        NotebookLine = pool.get('lims.notebook.line')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        service_write = {}
        service_write[field_changed] = getattr(actual_service, field_changed)
        Service.write([original_service], service_write)

        update_details = True if field_changed in ('analysis', 'laboratory',
            'method', 'device') else False

        if update_details:
            notebook_lines = NotebookLine.search([
                ('service', '=', original_service.id),
                ])
            if notebook_lines:
                NotebookLine.delete(notebook_lines)

            analysis_detail = EntryDetailAnalysis.search([
                ('service', '=', original_service.id)])
            if analysis_detail:
                EntryDetailAnalysis.create_notebook_lines(analysis_detail,
                    fraction)

            EntryDetailAnalysis.write(analysis_detail, {
                'state': 'unplanned',
                })
            if fraction.cie_fraction_type:
                self._create_blind_samples(analysis_detail, fraction)

    def _create_blind_samples(self, analysis_detail, fraction):
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        BlindSample = pool.get('lims.blind_sample')
        Date = pool.get('ir.date')

        confirmation_date = Date.today()

        to_create = []
        for detail in analysis_detail:
            nlines = NotebookLine.search([
                ('analysis_detail', '=', detail.id),
                ])
            for nline in nlines:
                record = {
                    'line': nline.id,
                    'entry': nline.fraction.entry.id,
                    'sample': nline.fraction.sample.id,
                    'fraction': nline.fraction.id,
                    'service': nline.service.id,
                    'analysis': nline.analysis.id,
                    'repetition': nline.repetition,
                    'date': confirmation_date,
                    'min_value': detail.cie_min_value,
                    'max_value': detail.cie_max_value,
                    }
                original_fraction = fraction.cie_original_fraction
                if original_fraction:
                    record['original_sample'] = original_fraction.sample.id
                    record['original_fraction'] = original_fraction.id
                    original_line = NotebookLine.search([
                        ('notebook.fraction', '=', original_fraction.id),
                        ('analysis', '=', nline.analysis.id),
                        ('repetition', '=', nline.repetition),
                        ])
                    if original_line:
                        record['original_line'] = original_line[0].id
                        record['original_repetition'] = (
                            original_line[0].repetition)
                to_create.append(record)
        if to_create:
            BlindSample.create(to_create)

    def _get_comparison_fields(self):
        return ('analysis', 'laboratory', 'method', 'device', 'urgent',
            'priority', 'report_date', 'comments', 'divide')


class CompleteServices(Wizard):
    'Complete Services'
    __name__ = 'lims.complete_services'

    start = StateTransition()

    def transition_start(self):
        Fraction = Pool().get('lims.fraction')
        fraction = Fraction(Transaction().context['active_id'])
        for service in fraction.services:
            if service.analysis.behavior != 'additional':
                self.complete_analysis_detail(service)
        return 'end'

    def complete_analysis_detail(self, service):
        'Similar to Service.update_analysis_detail(services)'
        pool = Pool()
        Service = pool.get('lims.service')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        analysis_data = []
        if service.analysis.type == 'analysis':
            laboratory_id = service.laboratory.id
            method_id = service.method.id if service.method else None
            device_id = service.device.id if service.device else None

            analysis_data.append({
                'id': service.analysis.id,
                'origin': service.analysis.code,
                'laboratory': laboratory_id,
                'method': method_id,
                'device': device_id,
                })
        else:
            service_context = {
                'product_type': service.fraction.product_type.id,
                'matrix': service.fraction.matrix.id,
                }

            analysis_data.extend(Service._get_included_analysis(
                service.analysis, service.analysis.code,
                service_context))

        to_create = []
        for analysis in analysis_data:
            if EntryDetailAnalysis.search_count([
                    ('service', '=', service.id),
                    ('analysis', '=', analysis['id']),
                    ]) != 0:
                continue
            values = {}
            values['service'] = service.id
            values['analysis'] = analysis['id']
            values['analysis_origin'] = analysis['origin']
            values['laboratory'] = analysis['laboratory']
            values['method'] = analysis['method']
            values['device'] = analysis['device']
            values['confirmation_date'] = service.confirmation_date
            # from lims_planification
            if 'trytond.modules.lims_planification' in sys.modules:
                values['state'] = 'unplanned'
            to_create.append(values)

        if to_create:
            with Transaction().set_user(0, set_context=True):
                analysis_detail = EntryDetailAnalysis.create(to_create)
            if analysis_detail:
                EntryDetailAnalysis.create_notebook_lines(analysis_detail,
                    service.fraction)


class FractionsByLocationsStart(ModelView):
    'Fractions by Locations'
    __name__ = 'lims.fractions_by_locations.start'

    location = fields.Many2One('stock.location', 'Location',
        required=True)

    @classmethod
    def default_location(cls):
        Location = Pool().get('stock.location')
        locations = Location.search([('type', '=', 'warehouse')])
        if len(locations) == 1:
            return locations[0].id


class FractionsByLocations(Wizard):
    'Fractions by Locations'
    __name__ = 'lims.fractions_by_locations'

    start = StateView('lims.fractions_by_locations.start',
        'lims.fractions_by_locations_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Open', 'open', 'tryton-ok', True),
            ])
    open = StateAction('lims.act_lims_fractions_by_locations')

    def do_open(self, action):
        Location = Pool().get('stock.location')

        childs = Location.search([
            ('parent', 'child_of', [self.start.location.id]),
            ])
        locations = [l.id for l in childs]
        action['pyson_domain'] = PYSONEncoder().encode([
            ('current_location', 'in', locations),
            ])
        action['name'] += ' (%s)' % self.start.location.rec_name
        return action, {}


class CountersampleStorageStart(ModelView):
    'Countersamples Storage'
    __name__ = 'lims.countersample.storage.start'

    report_date_from = fields.Date('Report date from', required=True)
    report_date_to = fields.Date('to', required=True)
    date_from = fields.Date('Date from', required=True)
    date_to = fields.Date('to', required=True)
    location_origin = fields.Many2One('stock.location', 'Origin Location',
        required=True, domain=[('type', '=', 'storage')])
    storage_force = fields.Boolean('Storage force')


class CountersampleStorageEmpty(ModelView):
    'Countersamples Storage'
    __name__ = 'lims.countersample.storage.empty'


class CountersampleStorageResult(ModelView):
    'Countersamples Storage'
    __name__ = 'lims.countersample.storage.result'

    location_destination = fields.Many2One('stock.location',
        'Destination Location', required=True,
        domain=[('type', '=', 'storage')])
    countersample_date = fields.Date('Storage date', required=True)
    fractions = fields.Many2Many('lims.fraction', None, None,
        'Fractions', required=True,
        domain=[('id', 'in', Eval('fraction_domain'))],
        depends=['fraction_domain'])
    fraction_domain = fields.One2Many('lims.fraction', None,
        'Fractions domain')
    shipment = fields.Many2One('stock.shipment.internal', 'Internal Shipment')


class CountersampleStorage(Wizard):
    'Countersamples Storage'
    __name__ = 'lims.countersample.storage'

    start = StateView('lims.countersample.storage.start',
        'lims.lims_countersample_storage_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search', 'search', 'tryton-forward', default=True),
            ])
    search = StateTransition()
    empty = StateView('lims.countersample.storage.empty',
        'lims.lims_countersample_storage_empty_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search again', 'start', 'tryton-forward', default=True),
            ])
    result = StateView('lims.countersample.storage.result',
        'lims.lims_countersample_storage_result_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Storage', 'storage', 'tryton-ok', default=True),
            ])
    storage = StateTransition()
    open = StateAction('stock.act_shipment_internal_form')

    @classmethod
    def __setup__(cls):
        super(CountersampleStorage, cls).__setup__()
        cls._error_messages.update({
            'reference': 'Countersamples Storage',
            })

    def default_start(self, fields):
        res = {}
        for field in ('report_date_from', 'report_date_to',
                'date_from', 'date_to'):
            if (hasattr(self.start, field) and getattr(self.start, field)):
                res[field] = getattr(self.start, field)
        for field in ('location_origin',):
            if (hasattr(self.start, field) and getattr(self.start, field)):
                res[field] = getattr(self.start, field).id
        return res

    def transition_search(self):
        pool = Pool()
        Fraction = pool.get('lims.fraction')
        NotebookLine = pool.get('lims.notebook.line')
        f_list = []
        if self.start.storage_force is True:
            fractions = Fraction.search([
                ('countersample_date', '=', None),
                ('sample.date2', '>=', self.start.date_from),
                ('sample.date2', '<=', self.start.date_to),
                ('current_location', '=', self.start.location_origin.id),
                ])
            if fractions:
                for f in fractions:
                    notebook_lines_ids = (
                        self._get_fraction_notebook_lines_storage_force(f.id))
                    if not notebook_lines_ids:
                        continue
                    notebook_lines = NotebookLine.search([
                        ('id', 'in', notebook_lines_ids),
                        ])
                    if not notebook_lines:
                        continue
                    f_list.append(f)

        else:
            fractions = Fraction.search([
                ('countersample_date', '=', None),
                ('sample.date2', '>=', self.start.date_from),
                ('sample.date2', '<=', self.start.date_to),
                ('has_results_report', '=', True),
                ('current_location', '=', self.start.location_origin.id),
                ])
            if fractions:
                for f in fractions:
                    notebook_lines_ids = self._get_fraction_notebook_lines(
                        f.id)
                    if not notebook_lines_ids:
                        continue
                    notebook_lines = NotebookLine.search([
                        ('id', 'in', notebook_lines_ids),
                        ])
                    if not notebook_lines:
                        continue

                    # Check not accepted (with repetitions)
                    to_check = []
                    oks = []
                    for line in notebook_lines:
                        key = line.analysis.id
                        if not line.accepted:
                            to_check.append(key)
                        else:
                            oks.append(key)
                    to_check = list(set(to_check))
                    oks = list(set(oks))
                    if to_check:
                        for key in oks:
                            if key in to_check:
                                to_check.remove(key)
                    if len(to_check) > 0:
                        continue

                    all_results_reported = True
                    for nl in notebook_lines:
                        if not nl.accepted:
                            continue
                        if not nl.results_report:
                            all_results_reported = False
                            break
                        if not self._get_line_reported(nl,
                                self.start.report_date_from,
                                self.start.report_date_to):
                            all_results_reported = False
                            break
                    if all_results_reported:
                        f_list.append(f)
        if f_list:
            self.result.fractions = f_list
            return 'result'
        return 'empty'

    def _get_fraction_notebook_lines(self, fraction_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        Service = pool.get('lims.service')

        cursor.execute('SELECT nl.id '
            'FROM "' + NotebookLine._table + '" nl '
                'INNER JOIN "' + EntryDetailAnalysis._table + '" ad '
                'ON ad.id = nl.analysis_detail '
                'INNER JOIN "' + Service._table + '" srv '
                'ON srv.id = nl.service '
            'WHERE srv.fraction = %s '
                'AND nl.report = TRUE '
                'AND nl.annulled = FALSE',
            (fraction_id,))
        return [x[0] for x in cursor.fetchall()]

    def _get_line_reported(self, nl, date_from, date_to):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        ReportVersionDetailLine = pool.get(
            'lims.results_report.version.detail.line')
        ReportVersionDetail = pool.get('lims.results_report.version.detail')
        ReportVersion = pool.get('lims.results_report.version')

        cursor.execute('SELECT rvdl.id '
            'FROM "' + ReportVersionDetailLine._table + '" rvdl '
                'INNER JOIN "' + ReportVersionDetail._table + '" rvd '
                'ON rvd.id = rvdl.report_version_detail '
                'INNER JOIN "' + ReportVersion._table + '" rv '
                'ON rv.id = rvd.report_version '
            'WHERE rvdl.notebook_line = %s '
                'AND rv.results_report = %s '
                'AND DATE(COALESCE(rvd.write_date, rvd.create_date)) '
                'BETWEEN %s::date AND %s::date',
            (nl.id, nl.results_report.id, date_from, date_to))
        return cursor.fetchone()

    def default_result(self, fields):
        fractions = [f.id for f in self.result.fractions]
        self.result.fractions = None
        return {
            'fractions': [],
            'fraction_domain': fractions,
            }

    def transition_storage(self):
        Fraction = Pool().get('lims.fraction')

        countersample_location = self.result.location_destination
        countersample_date = self.result.countersample_date
        fractions_to_save = []
        for fraction in self.result.fractions:
            fraction.countersample_location = countersample_location
            fraction.countersample_date = countersample_date
            fraction.expiry_date = countersample_date + relativedelta(
                months=fraction.storage_time)
            fractions_to_save.append(fraction)
        Fraction.save(fractions_to_save)

        moves = self._get_stock_moves(self.result.fractions)
        shipment = self.create_internal_shipment(moves)
        if shipment:
            self.result.shipment = shipment
            return 'open'
        return 'end'

    def create_internal_shipment(self, moves):
        ShipmentInternal = Pool().get('stock.shipment.internal')
        shipment = self._get_internal_shipment()
        if not shipment:
            return
        shipment.moves = moves
        with Transaction().set_context(check_current_location=False):
            shipment.save()
        ShipmentInternal.wait([shipment])
        ShipmentInternal.assign_force([shipment])
        ShipmentInternal.done([shipment])
        return shipment

    def _get_internal_shipment(self):
        pool = Pool()
        User = pool.get('res.user')
        ShipmentInternal = pool.get('stock.shipment.internal')

        company = User(Transaction().user).company
        from_location = self.start.location_origin
        to_location = self.result.location_destination
        planned_date = self.result.countersample_date

        with Transaction().set_user(0, set_context=True):
            shipment = ShipmentInternal()
        shipment.reference = CountersampleStorage.raise_user_error(
            'reference', raise_exception=False)
        shipment.planned_date = planned_date
        shipment.planned_start_date = planned_date
        shipment.company = company
        shipment.from_location = from_location
        shipment.to_location = to_location
        shipment.state = 'draft'
        return shipment

    def _get_stock_moves(self, fractions):
        pool = Pool()
        Config = pool.get('lims.configuration')
        Fraction = pool.get('lims.fraction')
        User = pool.get('res.user')
        Move = pool.get('stock.move')

        config_ = Config(1)
        if config_.fraction_product:
            product = config_.fraction_product
        else:
            Fraction.raise_user_error('missing_fraction_product')
        company = User(Transaction().user).company

        from_location = self.start.location_origin
        to_location = self.result.location_destination
        planned_date = self.result.countersample_date

        moves = []
        for fraction in fractions:
            with Transaction().set_user(0, set_context=True):
                move = Move()
            move.product = product.id
            move.fraction = fraction.id
            move.quantity = fraction.packages_quantity
            move.uom = product.default_uom
            move.from_location = from_location
            move.to_location = to_location
            move.company = company
            move.planned_date = planned_date
            move.origin = fraction
            move.state = 'draft'
            moves.append(move)
        return moves

    def do_open(self, action):
        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', '=', self.result.shipment.id),
            ])
        return action, {}

    def transition_open(self):
        return 'end'

    def _get_fraction_notebook_lines_storage_force(self, fraction_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        Service = pool.get('lims.service')

        cursor.execute('SELECT nl.id '
            'FROM "' + NotebookLine._table + '" nl '
                'INNER JOIN "' + EntryDetailAnalysis._table + '" ad '
                'ON ad.id = nl.analysis_detail '
                'INNER JOIN "' + Service._table + '" srv '
                'ON srv.id = nl.service '
            'WHERE srv.fraction = %s ',
            (fraction_id,))
        return [x[0] for x in cursor.fetchall()]


class CountersampleStorageRevertStart(ModelView):
    'Revert Countersamples Storage'
    __name__ = 'lims.countersample.storage_revert.start'

    date_from = fields.Date('Date from', required=True)
    date_to = fields.Date('Date to', required=True)
    location_origin = fields.Many2One('stock.location', 'Origin Location',
        required=True, domain=[('type', '=', 'storage')])


class CountersampleStorageRevertEmpty(ModelView):
    'Revert Countersamples Storage'
    __name__ = 'lims.countersample.storage_revert.empty'


class CountersampleStorageRevertResult(ModelView):
    'Revert Countersamples Storage'
    __name__ = 'lims.countersample.storage_revert.result'

    location_destination = fields.Many2One('stock.location',
        'Destination Location', required=True,
        domain=[('type', '=', 'storage')])
    fractions = fields.Many2Many('lims.fraction', None, None,
        'Fractions', required=True,
        domain=[('id', 'in', Eval('fraction_domain'))],
        depends=['fraction_domain'])
    fraction_domain = fields.One2Many('lims.fraction', None,
        'Fractions domain')
    shipment = fields.Many2One('stock.shipment.internal', 'Internal Shipment')


class CountersampleStorageRevert(Wizard):
    'Revert Countersamples Storage'
    __name__ = 'lims.countersample.storage_revert'

    start = StateView('lims.countersample.storage_revert.start',
        'lims.lims_countersample_storage_revert_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search', 'search', 'tryton-forward', default=True),
            ])
    search = StateTransition()
    empty = StateView('lims.countersample.storage_revert.empty',
        'lims.lims_countersample_storage_revert_empty_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search again', 'start', 'tryton-forward', default=True),
            ])
    result = StateView('lims.countersample.storage_revert.result',
        'lims.lims_countersample_storage_revert_result_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Revert', 'revert', 'tryton-ok', default=True),
            ])
    revert = StateTransition()
    open = StateAction('stock.act_shipment_internal_form')

    @classmethod
    def __setup__(cls):
        super(CountersampleStorageRevert, cls).__setup__()
        cls._error_messages.update({
            'reference': 'Countersamples Storage Reversion',
            })

    def default_start(self, fields):
        res = {}
        for field in ('date_from', 'date_to'):
            if (hasattr(self.start, field) and getattr(self.start, field)):
                res[field] = getattr(self.start, field)
        for field in ('location_origin',):
            if (hasattr(self.start, field) and getattr(self.start, field)):
                res[field] = getattr(self.start, field).id
        return res

    def transition_search(self):
        Fraction = Pool().get('lims.fraction')

        fractions = Fraction.search([
            ('countersample_date', '>=', self.start.date_from),
            ('countersample_date', '<=', self.start.date_to),
            ('current_location', '=', self.start.location_origin.id),
            ])
        if fractions:
            self.result.fractions = fractions
            return 'result'
        return 'empty'

    def default_result(self, fields):
        fractions = [f.id for f in self.result.fractions]
        self.result.fractions = None
        return {
            'fractions': [],
            'fraction_domain': fractions,
            }

    def transition_revert(self):
        Fraction = Pool().get('lims.fraction')

        fractions_to_save = []
        for fraction in self.result.fractions:
            fraction.countersample_location = None
            fraction.countersample_date = None
            fraction.expiry_date = None
            fractions_to_save.append(fraction)
        Fraction.save(fractions_to_save)

        moves = self._get_stock_moves(self.result.fractions)
        shipment = self.create_internal_shipment(moves)
        if shipment:
            self.result.shipment = shipment
            return 'open'
        return 'end'

    def create_internal_shipment(self, moves):
        ShipmentInternal = Pool().get('stock.shipment.internal')
        shipment = self._get_internal_shipment()
        if not shipment:
            return
        shipment.moves = moves
        with Transaction().set_context(check_current_location=False):
            shipment.save()
        ShipmentInternal.wait([shipment])
        ShipmentInternal.assign_force([shipment])
        ShipmentInternal.done([shipment])
        return shipment

    def _get_internal_shipment(self):
        pool = Pool()
        User = pool.get('res.user')
        Date = pool.get('ir.date')
        ShipmentInternal = pool.get('stock.shipment.internal')

        company = User(Transaction().user).company
        from_location = self.start.location_origin
        to_location = self.result.location_destination
        today = Date.today()

        with Transaction().set_user(0, set_context=True):
            shipment = ShipmentInternal()
        shipment.reference = CountersampleStorageRevert.raise_user_error(
            'reference', raise_exception=False)
        shipment.planned_date = today
        shipment.planned_start_date = today
        shipment.company = company
        shipment.from_location = from_location
        shipment.to_location = to_location
        shipment.state = 'draft'
        return shipment

    def _get_stock_moves(self, fractions):
        pool = Pool()
        Config = pool.get('lims.configuration')
        Fraction = pool.get('lims.fraction')
        User = pool.get('res.user')
        Date = pool.get('ir.date')
        Move = pool.get('stock.move')

        config_ = Config(1)
        if config_.fraction_product:
            product = config_.fraction_product
        else:
            Fraction.raise_user_error('missing_fraction_product')
        company = User(Transaction().user).company

        from_location = self.start.location_origin
        to_location = self.result.location_destination
        today = Date.today()

        moves = []
        for fraction in fractions:
            with Transaction().set_user(0, set_context=True):
                move = Move()
            move.product = product.id
            move.fraction = fraction.id
            move.quantity = fraction.packages_quantity
            move.uom = product.default_uom
            move.from_location = from_location
            move.to_location = to_location
            move.company = company
            move.planned_date = today
            move.origin = fraction
            move.state = 'draft'
            moves.append(move)
        return moves

    def do_open(self, action):
        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', '=', self.result.shipment.id),
            ])
        return action, {}

    def transition_open(self):
        return 'end'


class CountersampleDischargeStart(ModelView):
    'Countersamples Discharge'
    __name__ = 'lims.countersample.discharge.start'

    expiry_date_from = fields.Date('Expiry date from', required=True)
    expiry_date_to = fields.Date('to', required=True)
    date_from = fields.Date('Date from', required=True)
    date_to = fields.Date('to', required=True)
    location_origin = fields.Many2One('stock.location', 'Origin Location',
        required=True, domain=[('type', '=', 'storage')])


class CountersampleDischargeEmpty(ModelView):
    'Countersamples Discharge'
    __name__ = 'lims.countersample.discharge.empty'


class CountersampleDischargeResult(ModelView):
    'Countersamples Discharge'
    __name__ = 'lims.countersample.discharge.result'

    location_destination = fields.Many2One('stock.location',
        'Destination Location', required=True,
        domain=[('type', '=', 'lost_found')])
    discharge_date = fields.Date('Discharge date', required=True)
    fractions = fields.Many2Many('lims.fraction', None, None,
        'Fractions', required=True,
        domain=[('id', 'in', Eval('fraction_domain'))],
        depends=['fraction_domain'])
    fraction_domain = fields.One2Many('lims.fraction', None,
        'Fractions domain')
    shipment = fields.Many2One('stock.shipment.internal', 'Internal Shipment')


class CountersampleDischarge(Wizard):
    'Countersamples Discharge'
    __name__ = 'lims.countersample.discharge'

    start = StateView('lims.countersample.discharge.start',
        'lims.lims_countersample_discharge_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search', 'search', 'tryton-forward', default=True),
            ])
    search = StateTransition()
    empty = StateView('lims.countersample.discharge.empty',
        'lims.lims_countersample_discharge_empty_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search again', 'start', 'tryton-forward', default=True),
            ])
    result = StateView('lims.countersample.discharge.result',
        'lims.lims_countersample_discharge_result_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Discharge', 'discharge', 'tryton-ok', default=True),
            ])
    discharge = StateTransition()
    open = StateAction('stock.act_shipment_internal_form')

    @classmethod
    def __setup__(cls):
        super(CountersampleDischarge, cls).__setup__()
        cls._error_messages.update({
            'reference': 'Countersamples Discharge',
            })

    def default_start(self, fields):
        res = {}
        for field in ('expiry_date_from', 'expiry_date_to',
                'date_from', 'date_to'):
            if (hasattr(self.start, field) and getattr(self.start, field)):
                res[field] = getattr(self.start, field)
        for field in ('location_origin',):
            if (hasattr(self.start, field) and getattr(self.start, field)):
                res[field] = getattr(self.start, field).id
        return res

    def transition_search(self):
        Fraction = Pool().get('lims.fraction')

        fractions = Fraction.search([
            ('discharge_date', '=', None),
            ('sample.date2', '>=', self.start.date_from),
            ('sample.date2', '<=', self.start.date_to),
            ('expiry_date', '>=', self.start.expiry_date_from),
            ('expiry_date', '<=', self.start.expiry_date_to),
            ('current_location', '=', self.start.location_origin.id),
            ])
        if fractions:
            self.result.fractions = fractions
            return 'result'
        return 'empty'

    def default_result(self, fields):
        fractions = [f.id for f in self.result.fractions]
        self.result.fractions = None
        return {
            'fractions': [],
            'fraction_domain': fractions,
            }

    def transition_discharge(self):
        Fraction = Pool().get('lims.fraction')

        discharge_date = self.result.discharge_date
        fractions_to_save = []
        for fraction in self.result.fractions:
            fraction.discharge_date = discharge_date
            fractions_to_save.append(fraction)
        Fraction.save(fractions_to_save)

        moves = self._get_stock_moves(self.result.fractions)
        shipment = self.create_internal_shipment(moves)
        if shipment:
            self.result.shipment = shipment
            return 'open'
        return 'end'

    def create_internal_shipment(self, moves):
        ShipmentInternal = Pool().get('stock.shipment.internal')
        shipment = self._get_internal_shipment()
        if not shipment:
            return
        shipment.moves = moves
        with Transaction().set_context(check_current_location=False):
            shipment.save()
        ShipmentInternal.wait([shipment])
        ShipmentInternal.assign_force([shipment])
        ShipmentInternal.done([shipment])
        return shipment

    def _get_internal_shipment(self):
        pool = Pool()
        User = pool.get('res.user')
        ShipmentInternal = pool.get('stock.shipment.internal')

        company = User(Transaction().user).company
        from_location = self.start.location_origin
        to_location = self.result.location_destination
        planned_date = self.result.discharge_date

        with Transaction().set_user(0, set_context=True):
            shipment = ShipmentInternal()
        shipment.reference = CountersampleDischarge.raise_user_error(
            'reference', raise_exception=False)
        shipment.planned_date = planned_date
        shipment.planned_start_date = planned_date
        shipment.company = company
        shipment.from_location = from_location
        shipment.to_location = to_location
        shipment.state = 'draft'
        return shipment

    def _get_stock_moves(self, fractions):
        pool = Pool()
        Config = pool.get('lims.configuration')
        Fraction = pool.get('lims.fraction')
        User = pool.get('res.user')
        Move = pool.get('stock.move')

        config_ = Config(1)
        if config_.fraction_product:
            product = config_.fraction_product
        else:
            Fraction.raise_user_error('missing_fraction_product')
        company = User(Transaction().user).company

        from_location = self.start.location_origin
        to_location = self.result.location_destination
        planned_date = self.result.discharge_date

        moves = []
        for fraction in fractions:
            with Transaction().set_user(0, set_context=True):
                move = Move()
            move.product = product.id
            move.fraction = fraction.id
            move.quantity = fraction.packages_quantity
            move.uom = product.default_uom
            move.from_location = from_location
            move.to_location = to_location
            move.company = company
            move.planned_date = planned_date
            move.origin = fraction
            move.state = 'draft'
            moves.append(move)
        return moves

    def do_open(self, action):
        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', '=', self.result.shipment.id),
            ])
        return action, {}

    def transition_open(self):
        return 'end'


class FractionDischargeStart(ModelView):
    'Fractions Discharge'
    __name__ = 'lims.fraction.discharge.start'

    date_from = fields.Date('Date from', required=True)
    date_to = fields.Date('Date to', required=True)
    location_origin = fields.Many2One('stock.location', 'Origin Location',
        required=True, domain=[('type', '=', 'storage')])
    discharge_force = fields.Boolean('Discharge force')


class FractionDischargeEmpty(ModelView):
    'Fractions Discharge'
    __name__ = 'lims.fraction.discharge.empty'


class FractionDischargeResult(ModelView):
    'Fractions Discharge'
    __name__ = 'lims.fraction.discharge.result'

    location_destination = fields.Many2One('stock.location',
        'Destination Location', required=True,
        domain=[('type', '=', 'lost_found')])
    discharge_date = fields.Date('Discharge date', required=True)
    fractions = fields.Many2Many('lims.fraction', None, None,
        'Fractions', required=True,
        domain=[('id', 'in', Eval('fraction_domain'))],
        depends=['fraction_domain'])
    fraction_domain = fields.One2Many('lims.fraction', None,
        'Fractions domain')
    shipment = fields.Many2One('stock.shipment.internal', 'Internal Shipment')


class FractionDischarge(Wizard):
    'Fractions Discharge'
    __name__ = 'lims.fraction.discharge'

    start = StateView('lims.fraction.discharge.start',
        'lims.lims_fraction_discharge_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search', 'search', 'tryton-forward', default=True),
            ])
    search = StateTransition()
    empty = StateView('lims.fraction.discharge.empty',
        'lims.lims_fraction_discharge_empty_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search again', 'start', 'tryton-forward', default=True),
            ])
    result = StateView('lims.fraction.discharge.result',
        'lims.lims_fraction_discharge_result_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Discharge', 'discharge', 'tryton-ok', default=True),
            ])
    discharge = StateTransition()
    open = StateAction('stock.act_shipment_internal_form')

    @classmethod
    def __setup__(cls):
        super(FractionDischarge, cls).__setup__()
        cls._error_messages.update({
            'reference': 'Fractions Discharge',
            })

    def default_start(self, fields):
        res = {}
        for field in ('date_from', 'date_to'):
            if (hasattr(self.start, field) and getattr(self.start, field)):
                res[field] = getattr(self.start, field)
        for field in ('location_origin',):
            if (hasattr(self.start, field) and getattr(self.start, field)):
                res[field] = getattr(self.start, field).id
        return res

    def transition_search(self):
        Fraction = Pool().get('lims.fraction')
        if self.start.discharge_force is True:
            fractions = Fraction.search([
                ('discharge_date', '=', None),
                ('sample.date2', '>=', self.start.date_from),
                ('sample.date2', '<=', self.start.date_to),
                ('current_location', '=', self.start.location_origin.id),
                ])
        else:
            fractions = Fraction.search([
                ('discharge_date', '=', None),
                ('sample.date2', '>=', self.start.date_from),
                ('sample.date2', '<=', self.start.date_to),
                ('has_results_report', '=', False),
                ('current_location', '=', self.start.location_origin.id),
                ])

        if fractions:
            self.result.fractions = fractions
            return 'result'
        return 'empty'

    def default_result(self, fields):
        fractions = [f.id for f in self.result.fractions]
        self.result.fractions = None
        return {
            'fractions': [],
            'fraction_domain': fractions,
            }

    def transition_discharge(self):
        Fraction = Pool().get('lims.fraction')

        discharge_date = self.result.discharge_date
        fractions_to_save = []
        for fraction in self.result.fractions:
            fraction.discharge_date = discharge_date
            fractions_to_save.append(fraction)
        Fraction.save(fractions_to_save)

        moves = self._get_stock_moves(self.result.fractions)
        shipment = self.create_internal_shipment(moves)
        if shipment:
            self.result.shipment = shipment
            return 'open'
        return 'end'

    def create_internal_shipment(self, moves):
        ShipmentInternal = Pool().get('stock.shipment.internal')
        shipment = self._get_internal_shipment()
        if not shipment:
            return
        shipment.moves = moves
        with Transaction().set_context(check_current_location=False):
            shipment.save()
        ShipmentInternal.wait([shipment])
        ShipmentInternal.assign_force([shipment])
        ShipmentInternal.done([shipment])
        return shipment

    def _get_internal_shipment(self):
        pool = Pool()
        User = pool.get('res.user')
        ShipmentInternal = pool.get('stock.shipment.internal')

        company = User(Transaction().user).company
        from_location = self.start.location_origin
        to_location = self.result.location_destination
        planned_date = self.result.discharge_date

        with Transaction().set_user(0, set_context=True):
            shipment = ShipmentInternal()
        shipment.reference = FractionDischarge.raise_user_error(
            'reference', raise_exception=False)
        shipment.planned_date = planned_date
        shipment.planned_start_date = planned_date
        shipment.company = company
        shipment.from_location = from_location
        shipment.to_location = to_location
        shipment.state = 'draft'
        return shipment

    def _get_stock_moves(self, fractions):
        pool = Pool()
        Config = pool.get('lims.configuration')
        Fraction = pool.get('lims.fraction')
        User = pool.get('res.user')
        Move = pool.get('stock.move')

        config_ = Config(1)
        if config_.fraction_product:
            product = config_.fraction_product
        else:
            Fraction.raise_user_error('missing_fraction_product')
        company = User(Transaction().user).company

        from_location = self.start.location_origin
        to_location = self.result.location_destination
        planned_date = self.result.discharge_date

        moves = []
        for fraction in fractions:
            with Transaction().set_user(0, set_context=True):
                move = Move()
            move.product = product.id
            move.fraction = fraction.id
            move.quantity = fraction.packages_quantity
            move.uom = product.default_uom
            move.from_location = from_location
            move.to_location = to_location
            move.company = company
            move.planned_date = planned_date
            move.origin = fraction
            move.state = 'draft'
            moves.append(move)
        return moves

    def do_open(self, action):
        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', '=', self.result.shipment.id),
            ])
        return action, {}

    def transition_open(self):
        return 'end'


class FractionDischargeRevertStart(ModelView):
    'Revert Fractions Discharge'
    __name__ = 'lims.fraction.discharge_revert.start'

    date_from = fields.Date('Date from', required=True)
    date_to = fields.Date('Date to', required=True)
    location_origin = fields.Many2One('stock.location', 'Origin Location',
        required=True, domain=[('type', '=', 'lost_found')])


class FractionDischargeRevertEmpty(ModelView):
    'Revert Fractions Discharge'
    __name__ = 'lims.fraction.discharge_revert.empty'


class FractionDischargeRevertResult(ModelView):
    'Revert Fractions Discharge'
    __name__ = 'lims.fraction.discharge_revert.result'

    location_destination = fields.Many2One('stock.location',
        'Destination Location', required=True,
        domain=[('type', '=', 'storage')])
    fractions = fields.Many2Many('lims.fraction', None, None,
        'Fractions', required=True,
        domain=[('id', 'in', Eval('fraction_domain'))],
        depends=['fraction_domain'])
    fraction_domain = fields.One2Many('lims.fraction', None,
        'Fractions domain')
    shipment = fields.Many2One('stock.shipment.internal', 'Internal Shipment')


class FractionDischargeRevert(Wizard):
    'Revert Fractions Discharge'
    __name__ = 'lims.fraction.discharge_revert'

    start = StateView('lims.fraction.discharge_revert.start',
        'lims.lims_fraction_discharge_revert_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search', 'search', 'tryton-forward', default=True),
            ])
    search = StateTransition()
    empty = StateView('lims.fraction.discharge_revert.empty',
        'lims.lims_fraction_discharge_revert_empty_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search again', 'start', 'tryton-forward', default=True),
            ])
    result = StateView('lims.fraction.discharge_revert.result',
        'lims.lims_fraction_discharge_revert_result_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Revert', 'revert', 'tryton-ok', default=True),
            ])
    revert = StateTransition()
    open = StateAction('stock.act_shipment_internal_form')

    @classmethod
    def __setup__(cls):
        super(FractionDischargeRevert, cls).__setup__()
        cls._error_messages.update({
            'reference': 'Fractions Discharge Reversion',
            })

    def default_start(self, fields):
        res = {}
        for field in ('date_from', 'date_to'):
            if (hasattr(self.start, field) and getattr(self.start, field)):
                res[field] = getattr(self.start, field)
        for field in ('location_origin',):
            if (hasattr(self.start, field) and getattr(self.start, field)):
                res[field] = getattr(self.start, field).id
        return res

    def transition_search(self):
        Fraction = Pool().get('lims.fraction')

        fractions = Fraction.search([
            ('discharge_date', '>=', self.start.date_from),
            ('discharge_date', '<=', self.start.date_to),
            ('current_location', '=', self.start.location_origin.id),
            ])
        if fractions:
            self.result.fractions = fractions
            return 'result'
        return 'empty'

    def default_result(self, fields):
        fractions = [f.id for f in self.result.fractions]
        self.result.fractions = None
        return {
            'fractions': [],
            'fraction_domain': fractions,
            }

    def transition_revert(self):
        Fraction = Pool().get('lims.fraction')

        fractions_to_save = []
        for fraction in self.result.fractions:
            fraction.discharge_date = None
            fractions_to_save.append(fraction)
        Fraction.save(fractions_to_save)

        moves = self._get_stock_moves(self.result.fractions)
        shipment = self.create_internal_shipment(moves)
        if shipment:
            self.result.shipment = shipment
            return 'open'
        return 'end'

    def create_internal_shipment(self, moves):
        ShipmentInternal = Pool().get('stock.shipment.internal')
        shipment = self._get_internal_shipment()
        if not shipment:
            return
        shipment.moves = moves
        with Transaction().set_context(check_current_location=False):
            shipment.save()
        ShipmentInternal.wait([shipment])
        ShipmentInternal.assign_force([shipment])
        ShipmentInternal.done([shipment])
        return shipment

    def _get_internal_shipment(self):
        pool = Pool()
        User = pool.get('res.user')
        Date = pool.get('ir.date')
        ShipmentInternal = pool.get('stock.shipment.internal')

        company = User(Transaction().user).company
        from_location = self.start.location_origin
        to_location = self.result.location_destination
        today = Date.today()

        with Transaction().set_user(0, set_context=True):
            shipment = ShipmentInternal()
        shipment.reference = FractionDischargeRevert.raise_user_error(
            'reference', raise_exception=False)
        shipment.planned_date = today
        shipment.planned_start_date = today
        shipment.company = company
        shipment.from_location = from_location
        shipment.to_location = to_location
        shipment.state = 'draft'
        return shipment

    def _get_stock_moves(self, fractions):
        pool = Pool()
        Config = pool.get('lims.configuration')
        Fraction = pool.get('lims.fraction')
        User = pool.get('res.user')
        Date = pool.get('ir.date')
        Move = pool.get('stock.move')

        config_ = Config(1)
        if config_.fraction_product:
            product = config_.fraction_product
        else:
            Fraction.raise_user_error('missing_fraction_product')
        company = User(Transaction().user).company

        from_location = self.start.location_origin
        to_location = self.result.location_destination
        today = Date.today()

        moves = []
        for fraction in fractions:
            with Transaction().set_user(0, set_context=True):
                move = Move()
            move.product = product.id
            move.fraction = fraction.id
            move.quantity = fraction.packages_quantity
            move.uom = product.default_uom
            move.from_location = from_location
            move.to_location = to_location
            move.company = company
            move.planned_date = today
            move.origin = fraction
            move.state = 'draft'
            moves.append(move)
        return moves

    def do_open(self, action):
        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', '=', self.result.shipment.id),
            ])
        return action, {}

    def transition_open(self):
        return 'end'


class CreateSampleStart(ModelView):
    'Create Sample'
    __name__ = 'lims.create_sample.start'

    party = fields.Many2One('party.party', 'Party')
    date = fields.DateTime('Date', required=True)
    producer = fields.Many2One('lims.sample.producer', 'Producer company',
        domain=[('party', '=', Eval('party'))], depends=['party'])
    sample_client_description = fields.Char(
        'Product described by the client', required=True)
    sample_client_description_eng = fields.Char(
        'Product described by the client (English)')
    product_type = fields.Many2One('lims.product.type', 'Product type',
        required=True, states={'readonly': Bool(Eval('services'))},
        domain=[('id', 'in', Eval('product_type_domain'))],
        depends=['product_type_domain', 'services'])
    product_type_domain = fields.Many2Many('lims.product.type', None, None,
        'Product type domain')
    matrix = fields.Many2One('lims.matrix', 'Matrix', required=True,
        states={'readonly': Bool(Eval('services'))},
        domain=[('id', 'in', Eval('matrix_domain'))],
        depends=['matrix_domain', 'services'])
    matrix_domain = fields.Many2Many('lims.matrix', None, None,
        'Matrix domain')
    obj_description = fields.Many2One('lims.objective_description',
        'Objective description', depends=['product_type', 'matrix'],
        domain=[
            ('product_type', '=', Eval('product_type')),
            ('matrix', '=', Eval('matrix')),
            ])
    obj_description_manual = fields.Char(
        'Manual Objective description', depends=['obj_description'],
        states={'readonly': Bool(Eval('obj_description'))})
    obj_description_manual_eng = fields.Char(
        'Manual Objective description (English)', depends=['obj_description'],
        states={'readonly': Bool(Eval('obj_description'))})
    fraction_state = fields.Many2One('lims.packaging.integrity',
        'Package state', required=True)
    package_type = fields.Many2One('lims.packaging.type', 'Package type',
        required=True)
    packages_quantity = fields.Integer('Packages quantity', required=True)
    size = fields.Float('Size')
    size_uom = fields.Many2One('product.uom', 'Size UoM',
        domain=[('category.lims_only_available', '=', True)])
    restricted_entry = fields.Boolean('Restricted entry',
        states={'readonly': True})
    zone = fields.Many2One('lims.zone', 'Zone', required=True)
    trace_report = fields.Boolean('Trace report')
    report_comments = fields.Text('Report comments', translate=True)
    comments = fields.Text('Comments')
    variety = fields.Many2One('lims.variety', 'Variety',
        domain=[('varieties.matrix', '=', Eval('matrix'))],
        depends=['matrix'])
    labels = fields.Text('Labels')
    fraction_type = fields.Many2One('lims.fraction.type', 'Fraction type',
        required=True)
    storage_location = fields.Many2One('stock.location', 'Storage location',
        required=True, domain=[('type', '=', 'storage')])
    storage_time = fields.Integer('Storage time (in months)', required=True)
    weight = fields.Float('Weight')
    weight_uom = fields.Many2One('product.uom', 'Weight UoM',
        domain=[('category.lims_only_available', '=', True)])
    shared = fields.Boolean('Shared')
    analysis_domain = fields.Function(fields.Many2Many('lims.analysis',
        None, None, 'Analysis domain'), 'on_change_with_analysis_domain')
    services = fields.One2Many('lims.create_sample.service', None, 'Services',
        required=True, depends=['analysis_domain', 'product_type', 'matrix'],
        context={
            'analysis_domain': Eval('analysis_domain'),
            'product_type': Eval('product_type'), 'matrix': Eval('matrix'),
            })

    @staticmethod
    def default_date():
        return datetime.now()

    @staticmethod
    def default_restricted_entry():
        return False

    @staticmethod
    def default_zone():
        Entry = Pool().get('lims.entry')
        entry_id = Transaction().context.get('active_id', None)
        if entry_id:
            entry = Entry(entry_id)
            if entry.party.entry_zone:
                return entry.party.entry_zone.id

    @staticmethod
    def default_trace_report():
        return False

    @staticmethod
    def default_storage_time():
        return 3

    @staticmethod
    def default_product_type_domain():
        cursor = Transaction().connection.cursor()
        Typification = Pool().get('lims.typification')

        cursor.execute('SELECT DISTINCT(product_type) '
            'FROM "' + Typification._table + '" '
            'WHERE valid')
        res = cursor.fetchall()
        if not res:
            return []
        return [x[0] for x in res]

    @fields.depends('product_type', 'matrix', 'matrix_domain')
    def on_change_product_type(self):
        matrix_domain = []
        matrix = None
        if self.product_type:
            matrix_domain = self.on_change_with_matrix_domain()
            if len(matrix_domain) == 1:
                matrix = matrix_domain[0]
        self.matrix_domain = matrix_domain
        self.matrix = matrix

    @fields.depends('product_type')
    def on_change_with_matrix_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        Typification = Pool().get('lims.typification')

        if not self.product_type:
            return []

        cursor.execute('SELECT DISTINCT(matrix) '
            'FROM "' + Typification._table + '" '
            'WHERE product_type = %s '
            'AND valid',
            (self.product_type.id,))
        res = cursor.fetchall()
        if not res:
            return []
        return [x[0] for x in res]

    @fields.depends('product_type', 'matrix')
    def on_change_with_analysis_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Typification = pool.get('lims.typification')
        CalculatedTypification = pool.get('lims.typification.calculated')
        Analysis = pool.get('lims.analysis')

        if not self.product_type or not self.matrix:
            return []

        cursor.execute('SELECT DISTINCT(analysis) '
            'FROM "' + Typification._table + '" '
            'WHERE product_type = %s '
                'AND matrix = %s '
                'AND valid',
            (self.product_type.id, self.matrix.id))
        typified_analysis = [a[0] for a in cursor.fetchall()]
        if not typified_analysis:
            return []

        cursor.execute('SELECT id '
            'FROM "' + Analysis._table + '" '
            'WHERE type = \'analysis\' '
                'AND behavior IN (\'normal\', \'internal_relation\') '
                'AND disable_as_individual IS TRUE '
                'AND state = \'active\'')
        disabled_analysis = [a[0] for a in cursor.fetchall()]
        if disabled_analysis:
            typified_analysis = list(set(typified_analysis) -
                set(disabled_analysis))

        cursor.execute('SELECT DISTINCT(analysis) '
            'FROM "' + CalculatedTypification._table + '" '
            'WHERE product_type = %s '
                'AND matrix = %s',
            (self.product_type.id, self.matrix.id))
        typified_sets_groups = [a[0] for a in cursor.fetchall()]

        cursor.execute('SELECT id '
            'FROM "' + Analysis._table + '" '
            'WHERE behavior = \'additional\' '
                'AND state = \'active\'')
        additional_analysis = [a[0] for a in cursor.fetchall()]

        return typified_analysis + typified_sets_groups + additional_analysis

    @fields.depends('product_type', 'matrix', 'zone')
    def on_change_with_restricted_entry(self, name=None):
        return (self.product_type and self.product_type.restricted_entry and
                self.matrix and self.matrix.restricted_entry and
                self.zone and self.zone.restricted_entry)

    @fields.depends('fraction_type', 'package_type', 'fraction_state')
    def on_change_fraction_type(self):
        if self.fraction_type:
            if (not self.package_type and
                    self.fraction_type.default_package_type):
                self.package_type = self.fraction_type.default_package_type
            if (not self.fraction_state and
                    self.fraction_type.default_fraction_state):
                self.fraction_state = self.fraction_type.default_fraction_state

    @fields.depends('fraction_type', 'storage_location')
    def on_change_with_storage_time(self, name=None):
        if self.fraction_type and self.fraction_type.max_storage_time:
            return self.fraction_type.max_storage_time
        if self.storage_location and self.storage_location.storage_time:
            return self.storage_location.storage_time
        return 3

    @fields.depends('product_type', 'matrix')
    def on_change_with_obj_description(self):
        cursor = Transaction().connection.cursor()
        ObjectiveDescription = Pool().get('lims.objective_description')

        if not self.product_type or not self.matrix:
            return None

        cursor.execute('SELECT id '
            'FROM "' + ObjectiveDescription._table + '" '
            'WHERE product_type = %s '
                'AND matrix = %s',
            (self.product_type.id, self.matrix.id))
        res = cursor.fetchone()
        return res and res[0] or None


class CreateSampleService(ModelView):
    'Service'
    __name__ = 'lims.create_sample.service'

    analysis = fields.Many2One('lims.analysis', 'Analysis/Set/Group',
        required=True, domain=[
            ('id', 'in', Eval('context', {}).get('analysis_domain', [])),
            ])
    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        domain=[('id', 'in', Eval('laboratory_domain'))],
        states={'required': Bool(Eval('laboratory_domain'))},
        depends=['laboratory_domain'])
    laboratory_domain = fields.Many2Many('lims.laboratory',
        None, None, 'Laboratory domain')
    method = fields.Many2One('lims.lab.method', 'Method',
        domain=[('id', 'in', Eval('method_domain'))],
        states={'required': Bool(Eval('method_domain'))},
        depends=['method_domain'])
    method_domain = fields.Many2Many('lims.lab.method',
        None, None, 'Method domain')
    device = fields.Many2One('lims.lab.device', 'Device',
        domain=[('id', 'in', Eval('device_domain'))],
        states={'required': Bool(Eval('device_domain'))},
        depends=['device_domain'])
    device_domain = fields.Many2Many('lims.lab.device',
        None, None, 'Device domain')
    urgent = fields.Boolean('Urgent')
    priority = fields.Integer('Priority')
    report_date = fields.Date('Date agreed for result')
    divide = fields.Boolean('Divide')

    @staticmethod
    def default_urgent():
        return False

    @staticmethod
    def default_priority():
        return 0

    @staticmethod
    def default_divide():
        return False

    @fields.depends('analysis')
    def on_change_analysis(self):
        analysis_id = self.analysis.id if self.analysis else None

        product_type_id = Transaction().context.get('product_type', None)
        matrix_id = Transaction().context.get('matrix', None)

        laboratory_id = None
        laboratory_domain = []
        method_id = None
        method_domain = []
        device_id = None
        device_domain = []
        if analysis_id:
            laboratory_domain = self._get_laboratory_domain(analysis_id)
            if len(laboratory_domain) == 1:
                laboratory_id = laboratory_domain[0]

            method_domain = self._get_method_domain(analysis_id,
                product_type_id, matrix_id)
            if len(method_domain) == 1:
                method_id = method_domain[0]

            if laboratory_id:
                device_domain = self._get_device_domain(analysis_id,
                    laboratory_id)
                if len(device_domain) == 1:
                    device_id = device_domain[0]

        self.laboratory_domain = laboratory_domain
        self.laboratory = laboratory_id
        self.method_domain = method_domain
        self.method = method_id
        self.device_domain = device_domain
        self.device = device_id

    @staticmethod
    def _get_laboratory_domain(analysis_id):
        cursor = Transaction().connection.cursor()
        AnalysisLaboratory = Pool().get('lims.analysis-laboratory')

        cursor.execute('SELECT DISTINCT(laboratory) '
            'FROM "' + AnalysisLaboratory._table + '" '
            'WHERE analysis = %s',
            (analysis_id,))
        res = cursor.fetchall()
        if not res:
            return []
        return [x[0] for x in res]

    @staticmethod
    def _get_method_domain(analysis_id, product_type_id, matrix_id):
        cursor = Transaction().connection.cursor()
        Typification = Pool().get('lims.typification')

        cursor.execute('SELECT DISTINCT(method) '
            'FROM "' + Typification._table + '" '
            'WHERE product_type = %s '
                'AND matrix = %s '
                'AND analysis = %s '
                'AND valid',
            (product_type_id, matrix_id, analysis_id))
        res = cursor.fetchall()
        if not res:
            return []
        return [x[0] for x in res]

    @staticmethod
    def _get_device_domain(analysis_id, laboratory_id):
        cursor = Transaction().connection.cursor()
        AnalysisDevice = Pool().get('lims.analysis.device')

        cursor.execute('SELECT DISTINCT(device) '
            'FROM "' + AnalysisDevice._table + '" '
            'WHERE analysis = %s  '
                'AND laboratory = %s '
                'AND by_default = TRUE',
            (analysis_id, laboratory_id))
        res = cursor.fetchall()
        if not res:
            return []
        return [x[0] for x in res]


class CreateSample(Wizard):
    'Create Sample'
    __name__ = 'lims.create_sample'

    start = StateView('lims.create_sample.start',
        'lims.lims_create_sample_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Create', 'create_', 'tryton-ok', default=True),
            ])
    create_ = StateTransition()

    def default_start(self, fields):
        Entry = Pool().get('lims.entry')
        entry = Entry(Transaction().context['active_id'])
        return {
            'party': entry.party.id,
            }

    def transition_create_(self):
        # TODO: Remove logs
        logger = logging.getLogger(__name__)
        logger.info('-- CreateSample().transition_create_():INIT --')
        Sample = Pool().get('lims.sample')

        entry_id = Transaction().context['active_id']
        samples_defaults = self._get_samples_defaults(entry_id)
        logger.info('.. Sample.create(..)')
        sample, = Sample.create(samples_defaults)

        if (hasattr(self.start, 'sample_client_description_eng') and
                getattr(self.start, 'sample_client_description_eng')):
            with Transaction().set_context(language='en'):
                sample_eng = Sample(sample.id)
                sample_eng.sample_client_description = (
                    self.start.sample_client_description_eng)
                sample_eng.save()
        if (hasattr(self.start, 'obj_description_manual_eng') and
                getattr(self.start, 'obj_description_manual_eng')):
            with Transaction().set_context(language='en'):
                sample_eng = Sample(sample.id)
                sample_eng.obj_description_manual = (
                    self.start.obj_description_manual_eng)
                sample_eng.save()

        labels_list = self._get_labels_list(self.start.labels)
        if len(labels_list) > 1:
            logger.info('.. Sample.copy(..): %s' % (len(labels_list) - 1))
            for label in labels_list[1:]:
                Sample.copy([sample], default={
                    'label': label,
                    })

        logger.info('-- CreateSample().transition_create_():END --')
        return 'end'

    def _get_samples_defaults(self, entry_id):
        obj_description_id = None
        if (hasattr(self.start, 'obj_description') and
                getattr(self.start, 'obj_description')):
            obj_description_id = getattr(self.start, 'obj_description').id
        producer_id = None
        if (hasattr(self.start, 'producer') and
                getattr(self.start, 'producer')):
            producer_id = getattr(self.start, 'producer').id
        size = (hasattr(self.start, 'size') and
            getattr(self.start, 'size') or None)
        size_uom_id = None
        if (hasattr(self.start, 'size_uom') and
                getattr(self.start, 'size_uom')):
            size_uom_id = getattr(self.start, 'size_uom').id
        zone_id = None
        if (hasattr(self.start, 'zone') and
                getattr(self.start, 'zone')):
            zone_id = getattr(self.start, 'zone').id
        restricted_entry = (hasattr(self.start, 'restricted_entry') and
            getattr(self.start, 'restricted_entry') or False)
        variety_id = None
        if (hasattr(self.start, 'variety') and
                getattr(self.start, 'variety')):
            variety_id = getattr(self.start, 'variety').id
        weight = (hasattr(self.start, 'weight') and
            getattr(self.start, 'weight') or None)
        weight_uom_id = None
        if (hasattr(self.start, 'weight_uom') and
                getattr(self.start, 'weight_uom')):
            weight_uom_id = getattr(self.start, 'weight_uom').id
        shared = (hasattr(self.start, 'shared') and
            getattr(self.start, 'shared') or False)
        trace_report = (hasattr(self.start, 'trace_report') and
            getattr(self.start, 'trace_report') or False)
        report_comments = (hasattr(self.start, 'report_comments') and
            getattr(self.start, 'report_comments') or None)
        comments = (hasattr(self.start, 'comments') and
            getattr(self.start, 'comments') or None)

        # services data
        services_defaults = []
        for service in self.start.services:
            service_defaults = {
                'analysis': service.analysis.id,
                'laboratory': (service.laboratory.id if service.laboratory
                    else None),
                'method': service.method.id if service.method else None,
                'device': service.device.id if service.device else None,
                'urgent': service.urgent,
                'priority': service.priority,
                'report_date': service.report_date,
                'divide': service.divide,
                }
            services_defaults.append(service_defaults)

        # samples data
        samples_defaults = []
        labels_list = self._get_labels_list(self.start.labels)
        for label in labels_list[:1]:
            # fraction data
            fraction_defaults = {
                'type': self.start.fraction_type.id,
                'storage_location': self.start.storage_location.id,
                'storage_time': self.start.storage_time,
                'weight': weight,
                'weight_uom': weight_uom_id,
                'packages_quantity': self.start.packages_quantity,
                'size': size,
                'size_uom': size_uom_id,
                'shared': shared,
                'package_type': self.start.package_type.id,
                'fraction_state': self.start.fraction_state.id,
                'services': [('create', services_defaults)],
                }

            sample_defaults = {
                'entry': entry_id,
                'date': self.start.date,
                'producer': producer_id,
                'sample_client_description': (
                    self.start.sample_client_description),
                'product_type': self.start.product_type.id,
                'matrix': self.start.matrix.id,
                'obj_description': obj_description_id,
                'obj_description_manual': self.start.obj_description_manual,
                'package_state': self.start.fraction_state.id,
                'package_type': self.start.package_type.id,
                'packages_quantity': self.start.packages_quantity,
                'size': size,
                'size_uom': size_uom_id,
                'restricted_entry': restricted_entry,
                'zone': zone_id,
                'trace_report': trace_report,
                'report_comments': report_comments,
                'comments': comments,
                'variety': variety_id,
                'label': label,
                'fractions': [('create', [fraction_defaults])],
                }

            samples_defaults.append(sample_defaults)

        return samples_defaults

    def _get_labels_list(self, labels=None):
        if not labels:
            return [None]
        return labels.split('\n')


class CountersampleStoragePrintStart(ModelView):
    'Countersamples Storage Report'
    __name__ = 'lims.countersample.storage.print.start'

    report_date_from = fields.Date('Report date from', required=True)
    report_date_to = fields.Date('to', required=True)
    date_from = fields.Date('Date from', required=True)
    date_to = fields.Date('to', required=True)


class CountersampleStoragePrint(Wizard):
    'Countersamples Storage Report'
    __name__ = 'lims.countersample.storage.print'

    start = StateView('lims.countersample.storage.print.start',
        'lims.lims_countersample_storage_print_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print', 'print_', 'tryton-print', default=True),
            ])
    print_ = StateAction('lims.report_countersample_storage')

    def do_print_(self, action):
        data = {
            'report_date_from': self.start.report_date_from,
            'report_date_to': self.start.report_date_to,
            'date_from': self.start.date_from,
            'date_to': self.start.date_to,
            }
        return action, data

    def transition_print_(self):
        return 'end'


class CountersampleStorageReport(Report):
    'Countersamples Storage Report'
    __name__ = 'lims.countersample.storage.report'

    @classmethod
    def get_context(cls, records, data):
        pool = Pool()
        Fraction = pool.get('lims.fraction')
        NotebookLine = pool.get('lims.notebook.line')

        report_context = super(CountersampleStorageReport,
            cls).get_context(records, data)

        report_context['company'] = report_context['user'].company
        report_context['report_date_from'] = data['report_date_from']
        report_context['report_date_to'] = data['report_date_to']
        report_context['date_from'] = data['date_from']
        report_context['date_to'] = data['date_to']

        f_list = []
        fractions = Fraction.search([
            ('countersample_date', '=', None),
            ('sample.date2', '>=', data['date_from']),
            ('sample.date2', '<=', data['date_to']),
            ('has_results_report', '=', True),
            ], order=[('number', 'ASC')])

        for f in fractions:
            notebook_lines_ids = cls._get_fraction_notebook_lines(f.id)
            if not notebook_lines_ids:
                continue
            notebook_lines = NotebookLine.search([
                ('id', 'in', notebook_lines_ids),
                ])
            if not notebook_lines:
                continue

            # Check not accepted (with repetitions)
            to_check = []
            oks = []
            for line in notebook_lines:
                key = line.analysis.id
                if not line.accepted:
                    to_check.append(key)
                else:
                    oks.append(key)
            to_check = list(set(to_check))
            oks = list(set(oks))
            if to_check:
                for key in oks:
                    if key in to_check:
                        to_check.remove(key)
            if len(to_check) > 0:
                continue

            all_results_reported = True
            for nl in notebook_lines:
                if not nl.accepted:
                    continue
                if not nl.results_report:
                    all_results_reported = False
                    break
                if not cls._get_line_reported(nl, data['report_date_from'],
                        data['report_date_to']):
                    all_results_reported = False
                    break
            if all_results_reported:
                f_list.append(f)

        objects = {}
        for fraction in f_list:
            if fraction.current_location.id not in objects:
                objects[fraction.current_location.id] = {
                    'location': fraction.current_location.rec_name,
                    'fractions': [],
                    }
            objects[fraction.current_location.id]['fractions'].append({
                'number': fraction.get_formated_number('pt-m-sy-sn-fn'),
                'type': fraction.type.code,
                'packages': '%s %s' % (fraction.packages_quantity or '',
                    fraction.package_type.description if fraction.package_type
                    else ''),
                'entry_date': fraction.sample.date2,
                'results_reports': cls.get_fraction_results_reports(
                    fraction.id),
                'stp_number': (fraction.sample.entry.project.code
                    if fraction.sample.entry.project else ''),
                'comments': (fraction.comments
                    if fraction.comments else ''),
                })

        ordered_objects = sorted(list(objects.values()),
            key=lambda x: x['location'])

        report_context['objects'] = ordered_objects
        return report_context

    @classmethod
    def _get_fraction_notebook_lines(cls, fraction_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        Service = pool.get('lims.service')

        cursor.execute('SELECT nl.id '
            'FROM "' + NotebookLine._table + '" nl '
                'INNER JOIN "' + EntryDetailAnalysis._table + '" ad '
                'ON ad.id = nl.analysis_detail '
                'INNER JOIN "' + Service._table + '" srv '
                'ON srv.id = nl.service '
            'WHERE srv.fraction = %s '
                'AND nl.report = TRUE '
                'AND nl.annulled = FALSE',
            (fraction_id,))
        return [x[0] for x in cursor.fetchall()]

    @classmethod
    def _get_line_reported(cls, nl, date_from, date_to):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        ReportVersionDetailLine = pool.get(
            'lims.results_report.version.detail.line')
        ReportVersionDetail = pool.get('lims.results_report.version.detail')
        ReportVersion = pool.get('lims.results_report.version')

        cursor.execute('SELECT rvdl.id '
            'FROM "' + ReportVersionDetailLine._table + '" rvdl '
                'INNER JOIN "' + ReportVersionDetail._table + '" rvd '
                'ON rvd.id = rvdl.report_version_detail '
                'INNER JOIN "' + ReportVersion._table + '" rv '
                'ON rv.id = rvd.report_version '
            'WHERE rvdl.notebook_line = %s '
                'AND rv.results_report = %s '
                'AND DATE(COALESCE(rvd.write_date, rvd.create_date)) '
                'BETWEEN %s::date AND %s::date',
            (nl.id, nl.results_report.id, date_from, date_to))
        return cursor.fetchone()

    @classmethod
    def get_fraction_results_reports(cls, fraction_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Service = pool.get('lims.service')
        NotebookLine = pool.get('lims.notebook.line')
        ResultsReport = pool.get('lims.results_report')

        cursor.execute('SELECT DISTINCT(nl.results_report) '
            'FROM "' + Service._table + '" s '
                'INNER JOIN "' + NotebookLine._table + '" nl '
                'ON s.id = nl.service '
            'WHERE s.fraction = %s '
                'AND nl.results_report IS NOT NULL',
            (fraction_id,))
        res = cursor.fetchall()
        if not res:
            return ''
        result = []
        for report_id in res:
            results_report = ResultsReport(report_id[0])
            result.append('%s (%s)' % (results_report.rec_name,
                results_report.create_date2.strftime("%d/%m/%Y")))
        return ' '.join(result)


class CountersampleDischargePrintStart(ModelView):
    'Countersamples Discharge Report'
    __name__ = 'lims.countersample.discharge.print.start'

    expiry_date_from = fields.Date('Expiry date from', required=True)
    expiry_date_to = fields.Date('to', required=True)
    date_from = fields.Date('Date from', required=True)
    date_to = fields.Date('to', required=True)


class CountersampleDischargePrint(Wizard):
    'Countersamples Discharge Report'
    __name__ = 'lims.countersample.discharge.print'

    start = StateView('lims.countersample.discharge.print.start',
        'lims.lims_countersample_discharge_print_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print', 'print_', 'tryton-print', default=True),
            ])
    print_ = StateAction('lims.report_countersample_discharge')

    def do_print_(self, action):
        data = {
            'expiry_date_from': self.start.expiry_date_from,
            'expiry_date_to': self.start.expiry_date_to,
            'date_from': self.start.date_from,
            'date_to': self.start.date_to,
            }
        return action, data

    def transition_print_(self):
        return 'end'


class CountersampleDischargeReport(Report):
    'Countersamples Discharge Report'
    __name__ = 'lims.countersample.discharge.report'

    @classmethod
    def get_context(cls, records, data):
        pool = Pool()
        Fraction = pool.get('lims.fraction')

        report_context = super(CountersampleDischargeReport,
            cls).get_context(records, data)

        report_context['company'] = report_context['user'].company
        report_context['expiry_date_from'] = data['expiry_date_from']
        report_context['expiry_date_to'] = data['expiry_date_to']
        report_context['date_from'] = data['date_from']
        report_context['date_to'] = data['date_to']

        fractions = Fraction.search([
            ('discharge_date', '=', None),
            ('sample.date2', '>=', data['date_from']),
            ('sample.date2', '<=', data['date_to']),
            ('expiry_date', '>=', data['expiry_date_from']),
            ('expiry_date', '<=', data['expiry_date_to']),
            ], order=[('number', 'ASC')])

        objects = {}
        for fraction in fractions:
            if fraction.current_location.id not in objects:
                objects[fraction.current_location.id] = {
                    'location': fraction.current_location.rec_name,
                    'fractions': [],
                    }
            objects[fraction.current_location.id]['fractions'].append({
                'number': fraction.get_formated_number('pt-m-sy-sn-fn'),
                'type': fraction.type.code,
                'packages': '%s %s' % (fraction.packages_quantity or '',
                    fraction.package_type.description if fraction.package_type
                    else ''),
                'entry_date': fraction.sample.date2,
                'results_reports': cls.get_fraction_results_reports(
                    fraction.id),
                'stp_number': (fraction.sample.entry.project.code
                    if fraction.sample.entry.project else ''),
                'countersample_date': fraction.countersample_date or '',
                'expiry_date': fraction.expiry_date or '',
                'comments': (fraction.comments
                    if fraction.comments else ''),
                })

        ordered_objects = sorted(list(objects.values()),
            key=lambda x: x['location'])

        report_context['objects'] = ordered_objects
        return report_context

    @classmethod
    def get_fraction_results_reports(cls, fraction_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Service = pool.get('lims.service')
        NotebookLine = pool.get('lims.notebook.line')
        ResultsReport = pool.get('lims.results_report')

        cursor.execute('SELECT DISTINCT(nl.results_report) '
            'FROM "' + Service._table + '" s '
                'INNER JOIN "' + NotebookLine._table + '" nl '
                'ON s.id = nl.service '
            'WHERE s.fraction = %s '
                'AND nl.results_report IS NOT NULL',
            (fraction_id,))
        res = cursor.fetchall()
        if not res:
            return ''
        result = []
        for report_id in res:
            results_report = ResultsReport(report_id[0])
            result.append('%s (%s)' % (results_report.rec_name,
                results_report.create_date2.strftime("%d/%m/%Y")))
        return ' '.join(result)
