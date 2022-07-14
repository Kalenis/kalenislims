# -*- coding: utf-8 -*-
# This file is part of lims module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import logging
import operator
from datetime import datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from sql.conditionals import Case
from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from trytond.model import ModelView, ModelSQL, fields, Unique, DictSchemaMixin
from trytond.wizard import Wizard, StateTransition, StateView, StateAction, \
    Button
from trytond.pool import Pool
from trytond.pyson import PYSONEncoder, Eval, Equal, Bool, Not, Or, If
from trytond.transaction import Transaction
from trytond.report import Report
from trytond.exceptions import UserError
from trytond.i18n import gettext
from trytond.rpc import RPC
from trytond.config import config as tconfig
from trytond.tools import get_smtp_server
from trytond import backend

logger = logging.getLogger(__name__)


class Zone(ModelSQL, ModelView):
    'Zone/Region'
    __name__ = 'lims.zone'
    _rec_name = 'description'

    code = fields.Char('Code', required=True)
    description = fields.Char('Description', required=True)
    restricted_entry = fields.Boolean('Restricted entry')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code),
                'lims.msg_zone_code_unique_id'),
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
        super().__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code),
                'lims.msg_variety_code_unique_id'),
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
        super().__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code),
                'lims.msg_packaging_integrity_code_unique_id'),
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
    capacity = fields.Float('Capacity')
    capacity_uom = fields.Many2One('product.uom', 'Capacity UoM',
        domain=[('category.lims_only_available', '=', True)])

    @classmethod
    def __setup__(cls):
        super().__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code),
                'lims.msg_packaging_type_code_unique_id'),
            ]

    def get_rec_name(self, name):
        rec_name = '%s - %s' % (self.code, self.description)
        if self.capacity and self.capacity_uom:
            rec_name += ' (%s %s)' % (
                str(self.capacity), self.capacity_uom.symbol)
        return rec_name

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
    plannable = fields.Boolean('Plannable', select=True)
    cie_fraction_type = fields.Boolean('Available for Blind Samples')
    without_services = fields.Boolean('Allows entries without services')
    default_package_type = fields.Many2One('lims.packaging.type',
        'Default Package type')
    default_fraction_state = fields.Many2One('lims.packaging.integrity',
        'Default Fraction state')
    default_storage_location = fields.Many2One('stock.location',
        'Default Storage location', domain=[('type', '=', 'storage')])

    @classmethod
    def __setup__(cls):
        super().__setup__()
        t = cls.__table__()
        cls._order.insert(0, ('code', 'ASC'))
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code),
                'lims.msg_fraction_type_code_unique_id'),
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

    @staticmethod
    def default_cie_fraction_type():
        return False

    @staticmethod
    def default_without_services():
        return False

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

    @classmethod
    def copy(cls, records, default=None):
        if default is None:
            default = {}
        current_default = default.copy()

        new_records = []
        for record in records:
            current_default['code'] = '%s (copy)' % record.code
            new_record, = super().copy([record], default=current_default)
            new_records.append(new_record)
        return new_records


class SampleProducer(ModelSQL, ModelView):
    'Sample Producer'
    __name__ = 'lims.sample.producer'

    party = fields.Many2One('party.party', 'Party', required=True)
    name = fields.Char('Name', required=True)


class SampleAttribute(DictSchemaMixin, ModelSQL, ModelView):
    'Sample Attribute'
    __name__ = 'lims.sample.attribute'


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
    sample = fields.Function(fields.Many2One('lims.sample', 'Sample',
        states={'readonly': True}),
        'get_fraction_field', setter='set_fraction_field',
        searcher='search_fraction_field')
    entry = fields.Function(fields.Many2One('lims.entry', 'Entry'),
        'get_fraction_field',
        searcher='search_fraction_field')
    party = fields.Function(fields.Many2One('party.party', 'Party'),
        'get_fraction_field',
        searcher='search_fraction_field')
    analysis = fields.Many2One('lims.analysis', 'Analysis/Set/Group',
        required=True, select=True, depends=['analysis_domain'],
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
        (None, ''),
        ('analysis', 'Analysis'),
        ('set', 'Set'),
        ('group', 'Group'),
        ], 'Type', sort=False),
        'on_change_with_analysis_type', searcher='search_analysis_field')
    urgent = fields.Boolean('Urgent')
    priority = fields.Integer('Priority')
    estimated_waiting_laboratory = fields.Integer(
        'Number of days for Laboratory',
        states={'readonly': Or(
            Bool(Eval('context', {}).get('readonly', True)),
            ~Eval('report_date_readonly'))},
        depends=['report_date_readonly'])
    estimated_waiting_report = fields.Integer(
        'Number of days for Reporting',
        states={'readonly': Or(
            Bool(Eval('context', {}).get('readonly', True)),
            ~Eval('report_date_readonly'))},
        depends=['report_date_readonly'])
    laboratory_date = fields.Date('Laboratory deadline',
        states={'readonly': Or(
            Bool(Eval('context', {}).get('readonly', True)),
            Bool(Eval('report_date_readonly')))},
        depends=['report_date_readonly'])
    report_date = fields.Date('Date agreed for result',
        states={'readonly': Or(
            Bool(Eval('context', {}).get('readonly', True)),
            Bool(Eval('report_date_readonly')))},
        depends=['report_date_readonly'])
    report_date_readonly = fields.Function(fields.Boolean(
        'Report deadline Readonly'), 'get_report_date_readonly')
    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        domain=['OR', ('id', '=', Eval('laboratory')),
            ('id', 'in', Eval('laboratory_domain'))],
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
        domain=['OR', ('id', '=', Eval('device')),
            ('id', 'in', Eval('device_domain'))],
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
    divide = fields.Boolean('Divide Report')
    not_divided_message = fields.Char('Message', readonly=True,
        states={'invisible': Not(Bool(Eval('not_divided_message')))})
    has_results_report = fields.Function(fields.Boolean('Results Report'),
        'get_has_results_report')
    manage_service_available = fields.Function(fields.Boolean(
        'Available for Manage services'), 'get_manage_service_available')
    icon = fields.Function(fields.Char("Icon"), 'get_icon')
    planned = fields.Function(fields.Boolean('Planned'), 'get_planned',
        searcher='search_planned')
    annulled = fields.Boolean('Annulled', states={'readonly': True})
    is_additional = fields.Boolean('Is Additional', readonly=True)
    additional_origins = fields.Many2Many('lims.service.additional_origin',
        'service', 'origin', 'Origins of additional')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order.insert(0, ('number', 'DESC'))

    @classmethod
    def __register__(cls, module_name):
        cursor = Transaction().connection.cursor()
        TableHandler = backend.TableHandler

        table_h = cls.__table_handler__(module_name)
        migrate_additional_origin = (
            table_h.column_exist('additional_origin') and
            TableHandler.table_exist('lims_service_additional_origin'))

        super().__register__(module_name)

        if migrate_additional_origin:
            cursor.execute(
                'INSERT INTO "lims_service_additional_origin" '
                '(service, origin) '
                'SELECT id, additional_origin '
                'FROM lims_service '
                'WHERE additional_origin IS NOT NULL')
            cursor.execute(
                'UPDATE lims_service '
                'SET is_additional = TRUE '
                'WHERE additional_origin IS NOT NULL')
            table_h.drop_column('additional_origin')

    @staticmethod
    def default_urgent():
        return False

    @staticmethod
    def default_priority():
        return 0

    @staticmethod
    def default_divide():
        return False

    @staticmethod
    def default_annulled():
        return False

    @classmethod
    def check_duplicated_analysis(cls, new_services):
        """
        Checks that the new service is not already loaded for the sample
        """
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Fraction = pool.get('lims.fraction')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        Analysis = pool.get('lims.analysis')
        Typification = pool.get('lims.typification')

        existing_analysis = []
        for new_service in new_services:

            fraction = Fraction(new_service['fraction'])
            details = EntryDetailAnalysis.search([
                ('fraction', '=', fraction.id),
                ('state', '!=', 'annulled'),
                ])
            for d in details:
                existing_analysis.append([d.analysis.id, d.method.id])

            new_analysis = [(new_service['analysis'], new_service['method'])]
            new_analysis.extend(Analysis.get_included_analysis_method(
                new_service['analysis']))
            new_analysis = [list(a) for a in new_analysis]
            for a in new_analysis:
                if a[1]:
                    continue
                cursor.execute('SELECT method '
                    'FROM "' + Typification._table + '" '
                    'WHERE product_type = %s '
                        'AND matrix = %s '
                        'AND analysis = %s '
                        'AND valid IS TRUE '
                        'AND by_default IS TRUE',
                    (fraction.product_type.id, fraction.matrix.id, a[0]))
                res = cursor.fetchone()
                if res:
                    a[1] = res[0]

            for a in new_analysis:
                if a in existing_analysis:
                    raise UserError(gettext(
                        'lims.msg_duplicated_analysis_service',
                        analysis=Analysis(a[0]).rec_name,
                        fraction=fraction.rec_name,
                        ))
            existing_analysis.extend(new_analysis)

    @classmethod
    def create(cls, vlist):
        pool = Pool()
        LabWorkYear = pool.get('lims.lab.workyear')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        Sample = pool.get('lims.sample')

        workyear_id = LabWorkYear.find()
        workyear = LabWorkYear(workyear_id)
        sequence = workyear.get_sequence('service')
        if not sequence:
            raise UserError(gettext('lims.msg_no_service_sequence',
                work_year=workyear.rec_name))

        vlist = [x.copy() for x in vlist]
        cls.check_duplicated_analysis(vlist)
        for values in vlist:
            values['number'] = sequence.get()
        services = super().create(vlist)

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
                if hasattr(aditional_services[0].fraction.type,
                        'invoiceable'):
                    for aditional_service in aditional_services:
                        aditional_service.create_invoice_line()

        fractions_ids = list(set(s.fraction.id for s in services))
        cls.set_shared_fraction(fractions_ids)
        sample_ids = list(set(s.sample.id for s in services))
        Sample.update_samples_state(sample_ids)
        return services

    @classmethod
    def write(cls, *args):
        Sample = Pool().get('lims.sample')
        super().write(*args)
        actions = iter(args)
        for services, vals in zip(actions, actions):
            if vals.get('not_divided_message'):
                cls.write(services, {'not_divided_message': None})
            check_duplicated = False
            for field in ('analysis', 'method'):
                if vals.get(field):
                    check_duplicated = True
                    break
            if check_duplicated:
                cls.check_duplicated_analysis([{
                    'fraction': s.fraction.id,
                    'analysis': s.analysis.id,
                    'method': s.method.id,
                    } for s in services])
            change_detail = False
            for field in cls._get_update_details():
                if field in vals:
                    change_detail = True
                    break
            if change_detail:
                cls.update_analysis_detail(services)
                fractions_ids = list(set(s.fraction.id for s in services))
                cls.set_shared_fraction(fractions_ids)
            update_samples_state = False
            for field in ('laboratory_date', 'report_date',
                    'confirmation_date'):
                if field in vals:
                    update_samples_state = True
                    break
            if update_samples_state:
                sample_ids = list(set(s.sample.id for s in services))
                Sample.update_samples_state(sample_ids)

    @classmethod
    def _get_update_details(cls):
        return ('analysis', 'laboratory', 'method', 'device')

    @classmethod
    def delete(cls, services):
        Sample = Pool().get('lims.sample')
        if Transaction().user != 0:
            cls.check_delete(services)
        fractions_ids = list(set(s.fraction.id for s in services))
        sample_ids = list(set(s.sample.id for s in services))
        super().delete(services)
        cls.delete_additional_services()
        cls.set_shared_fraction(fractions_ids)
        Sample.update_samples_state(sample_ids)

    @classmethod
    def check_delete(cls, services):
        for service in services:
            if service.fraction and service.fraction.confirmed:
                raise UserError(gettext(
                    'lims.msg_delete_service', service=service.rec_name))

    @classmethod
    def delete_additional_services(cls):
        additionals_to_delete = cls.search([
            ('is_additional', '=', True),
            ('additional_origins', '=', None),
            ])
        if additionals_to_delete:
            cls.delete(additionals_to_delete)

    @staticmethod
    def update_analysis_detail(services):
        pool = Pool()
        Service = pool.get('lims.service')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        for service in services:
            if service.annulled:
                continue
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
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Typification = pool.get('lims.typification')

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

                    laboratory_id = None
                    cursor.execute('SELECT laboratory '
                        'FROM "' + Typification._table + '" '
                        'WHERE product_type = %s '
                            'AND matrix = %s '
                            'AND analysis = %s '
                            'AND valid IS TRUE '
                            'AND by_default IS TRUE '
                            'AND laboratory IS NOT NULL',
                        (service_context['product_type'],
                            service_context['matrix'],
                            included.included_analysis.id))
                    res = cursor.fetchone()
                    if res:
                        laboratory_id = res[0]
                    if not laboratory_id:
                        for l in included.included_analysis.laboratories:
                            if l.by_default is True:
                                laboratory_id = l.laboratory.id

                    method_id = (included.method.id
                        if included.method else None)
                    if not method_id:
                        cursor.execute('SELECT method '
                            'FROM "' + Typification._table + '" '
                            'WHERE product_type = %s '
                                'AND matrix = %s '
                                'AND analysis = %s '
                                'AND valid IS TRUE '
                                'AND by_default IS TRUE',
                            (service_context['product_type'],
                                service_context['matrix'],
                                included.included_analysis.id))
                        res = cursor.fetchone()
                        if res:
                            method_id = res[0]

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
                            'additional_origins': set(),
                            }
                    aditional_services[service.fraction.id][
                        typification.additional.id]['additional_origins'].add(
                            service.id)

                if typification.additionals:
                    if service.fraction.id not in aditional_services:
                        aditional_services[service.fraction.id] = {}
                    for additional in typification.additionals:
                        if (additional.id not in
                                aditional_services[service.fraction.id]):

                            cursor.execute('SELECT laboratory '
                                'FROM "' + AnalysisLaboratory._table + '" '
                                'WHERE analysis = %s '
                                    'AND by_default = TRUE '
                                'ORDER BY id', (additional.id,))
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

                            if not method_id:
                                raise UserError(gettext(
                                    'lims.msg_additional_no_method',
                                    additional=additional.rec_name,
                                    analysis=typification.analysis.rec_name))

                            cursor.execute('SELECT device '
                                'FROM "' + AnalysisDevice._table + '" '
                                'WHERE active IS TRUE '
                                    'AND analysis = %s '
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
                                'additional_origins': set(),
                                }
                        aditional_services[service.fraction.id][
                            additional.id]['additional_origins'].add(
                                service.id)

        if aditional_services:
            services_default = []
            for fraction_id, analysis in aditional_services.items():
                for analysis_id, service_data in analysis.items():
                    if EntryDetailAnalysis.search([
                            ('fraction', '=', fraction_id),
                            ('analysis', '=', analysis_id),
                            ]):
                        continue
                    if Service.search([
                            ('fraction', '=', fraction_id),
                            ('analysis', '=', analysis_id),
                            ]):
                        continue
                    services_default.append({
                        'fraction': fraction_id,
                        'analysis': analysis_id,
                        'laboratory': service_data['laboratory'],
                        'method': service_data['method'],
                        'device': service_data['device'],
                        'is_additional': True,
                        'additional_origins': [('add', list(
                            service_data['additional_origins']))],
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
        for included in analysis.included_analysis:
            if included.included_analysis.type == 'analysis':
                for l in included.included_analysis.laboratories:
                    if l.by_default is True:
                        childs.append(l.laboratory.id)
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
        if not Transaction().context.get('create_sample', False):
            current_default['report_date'] = None
        current_default['analysis_detail'] = None
        current_default['is_additional'] = False
        current_default['additional_origins'] = None

        detail_default = {}
        if current_default.get('method', None):
            detail_default['method'] = current_default['method']
        if current_default.get('device', None):
            detail_default['device'] = current_default['device']

        new_services = []
        for service in sorted(services, key=lambda x: x.number):
            with Transaction().set_context(copying=True):
                new_service, = super().copy([service],
                    default=current_default)
            detail_default['service'] = new_service.id
            detail_default['state'] = ('annulled' if service.annulled
                else 'draft')
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
        'laboratory', '_parent_fraction.id',
        methods=['_get_default_laboratory', '_get_default_method',
        'on_change_with_method_domain', '_on_change_with_device_domain'])
    def on_change_analysis(self):
        pool = Pool()
        Laboratory = pool.get('lims.laboratory')

        laboratory = None
        method = None
        device = None
        if self.analysis:
            default_laboratory = self._get_default_laboratory()
            if default_laboratory:
                laboratory = default_laboratory
            default_method = self._get_default_method()
            if default_method:
                method = default_method
            else:
                methods = self.on_change_with_method_domain()
                if len(methods) == 1:
                    method = methods[0]
            devices = self._on_change_with_device_domain(self.analysis,
                Laboratory(laboratory), True)
            if len(devices) == 1:
                device = devices[0]
            self.estimated_waiting_laboratory = (
                self.analysis.estimated_waiting_laboratory)
            self.estimated_waiting_report = (
                self.analysis.estimated_waiting_report)
        self.laboratory = laboratory
        self.method = method
        self.device = device

    @staticmethod
    def default_analysis_domain():
        return Transaction().context.get('analysis_domain', [])

    @fields.depends('fraction', '_parent_fraction.id')
    def on_change_with_analysis_domain(self, name=None):
        if Transaction().context.get('analysis_domain'):
            return Transaction().context.get('analysis_domain')
        return []

    @staticmethod
    def default_typification_domain():
        return Transaction().context.get('typification_domain', [])

    @fields.depends('fraction', '_parent_fraction.id')
    def on_change_with_typification_domain(self, name=None):
        if Transaction().context.get('typification_domain'):
            return Transaction().context.get('typification_domain')
        return []

    @fields.depends('analysis', '_parent_analysis.type')
    def on_change_with_analysis_type(self, name=None):
        return self.analysis and self.analysis.type or None

    @staticmethod
    def default_fraction_view():
        if (Transaction().context.get('fraction', 0) > 0):
            return Transaction().context.get('fraction')
        return None

    @fields.depends('fraction', '_parent_fraction.id')
    def on_change_with_fraction_view(self, name=None):
        if self.fraction:
            return self.fraction.id
        return None

    @staticmethod
    def default_sample():
        if (Transaction().context.get('sample', 0) > 0):
            return Transaction().context.get('sample')
        return None

    @fields.depends('fraction', '_parent_fraction.sample')
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

    @fields.depends('fraction', '_parent_fraction.entry')
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

    @fields.depends('fraction', '_parent_fraction.party')
    def on_change_with_party(self, name=None):
        if self.fraction:
            result = self.get_fraction_field((self,), ('party',))
            return result['party'][self.id]
        return None

    @staticmethod
    def default_report_date_readonly():
        return True

    @classmethod
    def get_report_date_readonly(cls, services, name):
        readonly = cls.default_report_date_readonly()
        result = {}
        for s in services:
            result[s.id] = readonly
        return result

    @fields.depends('estimated_waiting_laboratory')
    def on_change_with_laboratory_date(self, name=None):
        pool = Pool()
        LabWorkYear = pool.get('lims.lab.workyear')
        Date = pool.get('ir.date')
        if self.estimated_waiting_laboratory:
            date_ = Date.today()
            workyear = LabWorkYear(LabWorkYear.find(date_))
            date_ = workyear.get_target_date(date_,
                self.estimated_waiting_laboratory)
            return date_
        return None

    @fields.depends('estimated_waiting_laboratory', 'estimated_waiting_report')
    def on_change_with_report_date(self, name=None):
        pool = Pool()
        LabWorkYear = pool.get('lims.lab.workyear')
        Date = pool.get('ir.date')
        if self.estimated_waiting_laboratory or self.estimated_waiting_report:
            date_ = Date.today()
            workyear = LabWorkYear(LabWorkYear.find(date_))
            if self.estimated_waiting_laboratory:
                date_ = workyear.get_target_date(date_,
                    self.estimated_waiting_laboratory)
            if self.estimated_waiting_report:
                date_ = workyear.get_target_date(date_,
                    self.estimated_waiting_report)
            return date_
        return None

    @fields.depends('analysis', 'laboratory',
        methods=['_on_change_with_device_domain'])
    def on_change_laboratory(self):
        device = None
        if self.analysis and self.laboratory:
            devices = self._on_change_with_device_domain(self.analysis,
                self.laboratory, True)
            if len(devices) == 1:
                device = devices[0]
        self.device = device

    @fields.depends('analysis', '_parent_fraction.product_type',
        '_parent_fraction.matrix')
    def _get_default_laboratory(self):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        AnalysisLaboratory = pool.get('lims.analysis-laboratory')
        Typification = pool.get('lims.typification')

        if not self.analysis or self.analysis.type != 'analysis':
            return None

        cursor.execute('SELECT laboratory '
            'FROM "' + Typification._table + '" '
            'WHERE product_type = %s '
                'AND matrix = %s '
                'AND analysis = %s '
                'AND valid IS TRUE '
                'AND by_default IS TRUE '
                'AND laboratory IS NOT NULL',
            (self.fraction.product_type.id, self.fraction.matrix.id,
                self.analysis.id))
        res = cursor.fetchone()
        if res:
            return res[0]

        cursor.execute('SELECT laboratory '
            'FROM "' + AnalysisLaboratory._table + '" '
            'WHERE analysis = %s '
                'AND by_default = TRUE '
            'ORDER BY id', (self.analysis.id,))
        res = cursor.fetchone()
        if res:
            return res[0]

        return None

    @fields.depends('analysis', '_parent_fraction.product_type',
        '_parent_fraction.matrix')
    def on_change_with_laboratory_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        AnalysisLaboratory = pool.get('lims.analysis-laboratory')

        if not self.analysis or self.analysis.type != 'analysis':
            return []

        cursor.execute('SELECT DISTINCT(laboratory) '
            'FROM "' + AnalysisLaboratory._table + '" '
            'WHERE analysis = %s',
            (self.analysis.id,))
        res = cursor.fetchall()
        if not res:
            return []
        return [x[0] for x in res]

    @fields.depends('analysis', '_parent_fraction.product_type',
        '_parent_fraction.matrix')
    def _get_default_method(self):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Typification = pool.get('lims.typification')

        if not self.analysis or self.analysis.type != 'analysis':
            return None

        cursor.execute('SELECT method '
            'FROM "' + Typification._table + '" '
            'WHERE product_type = %s '
                'AND matrix = %s '
                'AND analysis = %s '
                'AND valid IS TRUE '
                'AND by_default IS TRUE',
            (self.fraction.product_type.id, self.fraction.matrix.id,
                self.analysis.id))
        res = cursor.fetchone()
        if res:
            return res[0]

        return None

    @fields.depends('analysis', 'typification_domain')
    def on_change_with_method_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Typification = pool.get('lims.typification')

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

    @fields.depends('analysis', 'laboratory',
    methods=['_on_change_with_device_domain'])
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
            by_default_clause = 'AND by_default IS TRUE'
        else:
            by_default_clause = ''
        cursor.execute('SELECT DISTINCT(device) '
            'FROM "' + AnalysisDevice._table + '" '
            'WHERE active IS TRUE '
                'AND analysis = %s  '
                'AND laboratory = %s ' +
                by_default_clause,
            (analysis.id, laboratory.id))
        res = cursor.fetchall()
        if not res:
            return []
        return [x[0] for x in res]

    @fields.depends('divide')
    def on_change_divide(self):
        if self.divide:
            self.not_divided_message = gettext('lims.msg_divide_report')
        else:
            self.not_divided_message = ''

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

    @classmethod
    def set_fraction_field(cls, records, name, value):
        return

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
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')

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
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
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

    @classmethod
    def is_service_urgent(cls, fraction_id, analysis_id):
        service = cls.search([
            ('fraction', '=', fraction_id),
            ('analysis', '=', analysis_id),
            ])
        if service:
            return service[0].urgent
        return False


class ServiceOrigin(ModelSQL):
    'Service Origin'
    __name__ = 'lims.service.additional_origin'

    service = fields.Many2One('lims.service', 'Service',
        ondelete='CASCADE', select=True, required=True)
    origin = fields.Many2One('lims.service', 'Origin',
        ondelete='CASCADE', select=True, required=True)


class Fraction(ModelSQL, ModelView):
    'Fraction'
    __name__ = 'lims.fraction'
    _rec_name = 'number'

    _states = {'readonly': Bool(Eval('has_results_report'))}
    _depends = ['has_results_report']

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
    date = fields.Function(fields.DateTime('Date'), 'get_sample_field',
        searcher='search_sample_field')
    type = fields.Many2One('lims.fraction.type', 'Fraction type',
        required=True, select=True, states=_states, depends=_depends)
    storage_location = fields.Many2One('stock.location', 'Storage location',
        required=True, domain=[('type', '=', 'storage')],
        states=_states, depends=_depends)
    storage_time = fields.Integer('Storage time (in months)', required=True,
        states=_states, depends=_depends)
    packages_quantity = fields.Integer('Packages quantity', required=True,
        states=_states, depends=_depends)
    package_type = fields.Many2One('lims.packaging.type', 'Package type',
        required=True, states=_states, depends=_depends)
    expiry_date = fields.Date('Expiry date', states={'readonly': True})
    discharge_date = fields.Date('Discharge date', readonly=True)
    countersample_location = fields.Many2One('stock.location',
        'Countersample location', readonly=True)
    countersample_date = fields.Date('Countersample date', readonly=True)
    fraction_state = fields.Many2One('lims.packaging.integrity',
        'Fraction state', required=True, states=_states, depends=_depends)
    services = fields.One2Many('lims.service', 'fraction', 'Services',
        states={'readonly': Bool(Eval('button_manage_services_available'))},
        context={
            'analysis_domain': Eval('analysis_domain'),
            'typification_domain': Eval('typification_domain'),
            'product_type': Eval('product_type'), 'matrix': Eval('matrix'),
            'fraction': Eval('id'), 'sample': Eval('sample'),
            'entry': Eval('entry'), 'party': Eval('party'),
            'readonly': Bool(Eval('button_manage_services_available')),
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
        'on_change_with_product_type', searcher='search_sample_field')
    matrix = fields.Function(fields.Many2One('lims.matrix', 'Matrix'),
        'on_change_with_matrix', searcher='search_sample_field')
    button_manage_services_available = fields.Function(fields.Boolean(
        'Button manage services available'),
        'on_change_with_button_manage_services_available')
    confirmed = fields.Boolean('Confirmed', select=True)
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

    del _states, _depends

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order.insert(0, ('number', 'DESC'))
        cls._buttons.update({
            'manage_services': {
                'invisible': ~Eval('button_manage_services_available'),
                'readonly': Bool(Eval('context', {}).get('from_entry', False)),
                },
            'complete_services': {
                'invisible': ~Eval('button_manage_services_available'),
                'readonly': Bool(Eval('context', {}).get('from_entry', False)),
                },
            'confirm': {
                'invisible': ~Eval('button_confirm_available'),
                },
            'load_services': {
                'invisible': Or(Bool(Eval('button_manage_services_available')),
                    Bool(Eval('services'))),
                'readonly': Bool(Eval('context', {}).get('from_entry', False)),
                },
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
                    }),
            ]

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
        return super().create(vlist)

    @classmethod
    def write(cls, *args):
        super().write(*args)
        actions = iter(args)
        for fractions, vals in zip(actions, actions):
            if vals.get('type'):
                cls.update_details_plannable(fractions, vals.get('type'))

    @classmethod
    def update_details_plannable(cls, fractions, fraction_type_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        FractionType = pool.get('lims.fraction.type')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        Service = pool.get('lims.service')

        plannable = ('TRUE' if FractionType(fraction_type_id).plannable
            else 'FALSE')
        fractions_ids = ', '.join(str(f.id) for f in fractions)

        cursor.execute('UPDATE "' + EntryDetailAnalysis._table + '" d '
            'SET plannable = ' + plannable + ' FROM '
            '"' + Service._table + '" srv '
            'WHERE d.service = srv.id '
            'AND d.state IN (\'draft\', \'unplanned\') '
            'AND d.referable = FALSE '
            'AND srv.fraction IN (' + fractions_ids + ')')

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

                new_fraction, = super().copy([fraction],
                    default=current_default)
                new_fractions.append(new_fraction)
        return new_fractions

    @classmethod
    def check_delete(cls, fractions):
        for fraction in fractions:
            if fraction.confirmed:
                raise UserError(gettext(
                    'lims.msg_delete_fraction', fraction=fraction.rec_name))

    @classmethod
    def delete(cls, fractions):
        cls.check_delete(fractions)
        super().delete(fractions)

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

    @fields.depends('sample', '_parent_sample.id')
    def on_change_with_analysis_domain(self, name=None):
        if Transaction().context.get('analysis_domain'):
            return Transaction().context.get('analysis_domain')
        if self.sample:
            return self.sample.on_change_with_analysis_domain()
        return []

    @staticmethod
    def default_typification_domain():
        return Transaction().context.get('typification_domain', [])

    @fields.depends('sample', '_parent_sample.id')
    def on_change_with_typification_domain(self, name=None):
        if Transaction().context.get('typification_domain'):
            return Transaction().context.get('typification_domain')
        if self.sample:
            return self.sample.on_change_with_typification_domain()
        return []

    @staticmethod
    def default_product_type():
        return Transaction().context.get('product_type', None)

    @fields.depends('sample', '_parent_sample.product_type')
    def on_change_with_product_type(self, name=None):
        if Transaction().context.get('product_type'):
            return Transaction().context.get('product_type')
        if self.sample and self.sample.product_type:
            return self.sample.product_type.id
        return None

    @staticmethod
    def default_matrix():
        return Transaction().context.get('matrix', None)

    @fields.depends('sample', '_parent_sample.matrix')
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
        if clause[1] in ('=', '!='):
            types = [clause[2]]
        elif clause[1] in ('in', 'not in'):
            types = clause[2]
        else:
            return []
        if not types:
            return []
        res_type = cls._get_special_type(types)
        if clause[1] in ('=', '!='):
            return [('type', clause[1], res_type[0])]
        elif clause[1] in ('in', 'not in'):
            return [('type', clause[1], res_type)]
        return []

    @classmethod
    def _get_special_type(cls, types):
        Config = Pool().get('lims.configuration')
        config = Config(1)
        res_type = []
        for type_ in types:
            if type_ == 'mcl':
                res_type.append(config.mcl_fraction_type)
            elif type_ == 'con':
                res_type.append(config.con_fraction_type)
            elif type_ == 'bmz':
                res_type.append(config.bmz_fraction_type)
            elif type_ == 'rm':
                res_type.append(config.rm_fraction_type)
            elif type_ == 'bre':
                res_type.append(config.bre_fraction_type)
            elif type_ == 'mrt':
                res_type.append(config.mrt_fraction_type)
            elif type_ == 'coi':
                res_type.append(config.coi_fraction_type)
            elif type_ == 'mrc':
                res_type.append(config.mrc_fraction_type)
            elif type_ == 'sla':
                res_type.append(config.sla_fraction_type)
            elif type_ == 'itc':
                res_type.append(config.itc_fraction_type)
            elif type_ == 'itl':
                res_type.append(config.itl_fraction_type)
        return res_type

    @fields.depends('sample', '_parent_sample.id')
    def on_change_with_sample_view(self, name=None):
        if self.sample:
            return self.sample.id
        return None

    @staticmethod
    def default_entry():
        if (Transaction().context.get('entry', 0) > 0):
            return Transaction().context.get('entry')
        return None

    @fields.depends('sample', '_parent_sample.entry')
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

    @fields.depends('sample', '_parent_sample.party')
    def on_change_with_party(self, name=None):
        if self.sample:
            result = self.get_sample_field((self,), ('party',))
            return result['party'][self.id]
        return None

    @staticmethod
    def default_label():
        return Transaction().context.get('label', '')

    @fields.depends('sample', 'special_type', 'con_original_fraction',
        'services', 'create_date', '_parent_sample.label')
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

    @fields.depends('sample', '_parent_sample.package_type')
    def on_change_with_package_type(self, name=None):
        if self.sample:
            result = self.get_sample_field((self,), ('package_type',))
            return result['package_type'][self.id]
        return None

    @staticmethod
    def default_fraction_state():
        if Transaction().context.get('fraction_state'):
            return Transaction().context.get('fraction_state')
        return None

    @fields.depends('sample', '_parent_sample.package_state')
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
            if name == 'fraction_state':
                for f in fractions:
                    field = getattr(f.sample, 'package_state', None)
                    result[name][f.id] = field.id if field else None
            elif cls._fields[name]._type == 'many2one':
                for f in fractions:
                    field = getattr(f.sample, name, None)
                    result[name][f.id] = field.id if field else None
            else:
                for f in fractions:
                    result[name][f.id] = getattr(f.sample, name, None)
        return result

    @classmethod
    def search_sample_field(cls, name, clause):
        return [('sample.' + name,) + tuple(clause[1:])]

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
    order_date = _order_sample_field('date')

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

    @fields.depends('confirmed', 'type', '_parent_type.cie_fraction_type')
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

    @fields.depends('confirmed', 'sample', '_parent_sample.entry')
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
            ('annulled', '=', False),
            ])
        for service in services:
            if (EntryDetailAnalysis.search_count([
                    ('service', '=', service.id),
                    ('report_grouper', '!=', 0),
                    ]) == 0):
                raise UserError(gettext('lims.msg_not_divided'))

    @classmethod
    @ModelView.button
    def confirm(cls, fractions):
        pool = Pool()
        Config = pool.get('lims.configuration')
        Service = pool.get('lims.service')
        Company = pool.get('company.company')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        Move = pool.get('stock.move')

        confirm_background = Config(1).entry_confirm_background

        cls.check_divided_report(fractions)
        fractions_to_save = []
        stock_moves_to_create = []
        for fraction in fractions:
            services = Service.search([
                ('fraction', '=', fraction.id),
                ('annulled', '=', False),
                ])
            if not services and not fraction.type.without_services:
                companies = Company.search([])
                if fraction.party.id not in [c.party.id for c in companies]:
                    raise UserError(gettext(
                        'lims.msg_not_services', fraction=fraction.rec_name))
            Service.copy_analysis_comments(services)
            Service.set_confirmation_date(services)
            fraction.create_laboratory_notebook()
            analysis_detail = EntryDetailAnalysis.search([
                ('fraction', '=', fraction.id),
                ('state', '!=', 'annulled'),
                ])
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
            raise UserError(gettext('lims.msg_missing_fraction_product'))
        today = Date.today()
        company = User(Transaction().user).company
        if self.sample.party.customer_location:
            from_location = self.sample.party.customer_location
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
        if move.on_change_with_unit_price_required():
            move.unit_price = 0
            move.currency = company.currency
        move.state = 'draft'
        return move

    @classmethod
    def confirm_waiting_fractions(cls):
        '''
        Cron - Confirm Waiting Fractions
        '''
        Move = Pool().get('stock.move')

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
        if not self.services:
            return
        analysis = []
        for service in self.services:
            if not service.analysis:
                continue
            if service.annulled:
                continue
            new_analysis = [(service.analysis.id,
                service.method and service.method.id or None)]
            new_analysis.extend(Analysis.get_included_analysis_method(
                service.analysis.id))
            for a in new_analysis:
                if a in analysis:
                    self.duplicated_analysis_message = gettext(
                        'lims.msg_duplicated_analysis',
                        analysis=Analysis(a[0]).rec_name)
                    return
            analysis.extend(new_analysis)

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
            ('state', '!=', 'annulled'),
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
    party = fields.Many2One('party.party', 'Party', required=True,
        states={'readonly': True})
    multi_party = fields.Function(fields.Boolean('Multi Party'),
        'get_entry_field', searcher='search_entry_field')
    invoice_party = fields.Function(fields.Many2One('party.party',
        'Invoice Party'), 'get_entry_field', searcher='search_entry_field')
    producer = fields.Many2One('lims.sample.producer', 'Producer company',
        domain=['OR', ('id', '=', Eval('producer')),
            ('party', '=', Eval('party'))],
        depends=['party'])
    label = fields.Char('Label')
    sample_client_description = fields.Char('Product described by the client',
        translate=True)
    product_type = fields.Many2One('lims.product.type', 'Product type',
        required=True,
        domain=['OR', ('id', '=', Eval('product_type')),
            ('id', 'in', Eval('product_type_domain'))],
        states={'readonly': Bool(Eval('product_type_matrix_readonly'))},
        depends=['product_type_domain', 'product_type_matrix_readonly'])
    product_type_view = fields.Function(fields.Many2One('lims.product.type',
        'Product type'), 'get_views_field', searcher='search_views_field')
    product_type_domain = fields.Function(fields.Many2Many(
        'lims.product.type', None, None, 'Product type domain'),
        'on_change_with_product_type_domain')
    matrix = fields.Many2One('lims.matrix', 'Matrix', required=True,
        domain=['OR', ('id', '=', Eval('matrix')),
            ('id', 'in', Eval('matrix_domain'))],
        states={'readonly': Bool(Eval('product_type_matrix_readonly'))},
        depends=['matrix_domain', 'product_type_matrix_readonly'])
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
    restricted_entry = fields.Boolean('Restricted entry',
        states={'readonly': True})
    zone = fields.Many2One('lims.zone', 'Zone',
        states={'required': Bool(Eval('zone_required'))},
        depends=['zone_required'])
    zone_required = fields.Function(fields.Boolean('Zone required'),
        'get_zone_required')
    trace_report = fields.Boolean('Trace report')
    fractions = fields.One2Many('lims.fraction', 'sample', 'Fractions',
        context={
            'analysis_domain': Eval('analysis_domain'),
            'typification_domain': Eval('typification_domain'),
            'product_type': Eval('product_type'), 'matrix': Eval('matrix'),
            'sample': Eval('id'), 'entry': Eval('entry'),
            'party': Eval('party'), 'label': Eval('label'),
            'package_type': Eval('package_type'),
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
    urgent = fields.Function(fields.Boolean('Urgent'), 'get_urgent',
        searcher='search_urgent')
    completion_percentage = fields.Function(fields.Numeric('Complete',
        digits=(1, 4), domain=[
            ('completion_percentage', '>=', 0),
            ('completion_percentage', '<=', 1),
            ]),
        'get_completion_percentage')
    department = fields.Function(fields.Many2One('company.department',
        'Department'), 'get_department', searcher='search_department')
    attributes = fields.Dict('lims.sample.attribute', 'Attributes')
    attributes_keys_string = attributes.translated('attributes', 'keys')
    attributes_values_string = attributes.translated('attributes')
    confirmation_date = fields.Date('Confirmation date', readonly=True)
    laboratory_date = fields.Date('Laboratory deadline', readonly=True)
    report_date = fields.Date('Date agreed for result', readonly=True)
    laboratory_start_date = fields.Date('Laboratory start date', readonly=True)
    laboratory_end_date = fields.Date('Laboratory end date', readonly=True)
    laboratory_acceptance_date = fields.Date('Laboratory acceptance date',
        readonly=True)
    results_report_create_date = fields.Date('Report start date',
        readonly=True)
    results_report_release_date = fields.Date('Report release date',
        readonly=True)
    results_reports_list = fields.Function(fields.Char('Results Reports'),
        'get_results_reports_list', searcher='search_results_reports_list')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('annulled', 'Annulled'),
        ('pending_planning', 'Pending Planification'),
        ('planned', 'Planned'),
        ('in_lab', 'In Laboratory'),
        ('lab_pending_acceptance', 'Pending Laboratory Acceptance'),
        ('pending_report', 'Pending Reporting'),
        ('in_report', 'In Report'),
        ('report_released', 'Report Released'),
        ], 'State')
    qty_lines_pending = fields.Integer('Pending lines')
    qty_lines_pending_acceptance = fields.Integer('Lines pending acceptance')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order.insert(0, ('number', 'DESC'))
        cls.__rpc__.update({
            'update_samples_state': RPC(readonly=False, instantiate=0),
            })

    @classmethod
    def __register__(cls, module_name):
        cursor = Transaction().connection.cursor()
        Entry = Pool().get('lims.entry')
        table_h = cls.__table_handler__(module_name)
        qty_lines_pending_exist = table_h.column_exist('qty_lines_pending')
        qty_lines_pending_acceptance_exist = table_h.column_exist(
            'qty_lines_pending_acceptance')
        party_exist = table_h.column_exist('party')
        super().__register__(module_name)
        if (not qty_lines_pending_exist or
                not qty_lines_pending_acceptance_exist):
            logger.info('Updating Pending lines in Samples...')
            for sample in cls.search([]):
                sample.update_qty_lines()
        if not party_exist:
            logger.info('Updating Party in Samples...')
            cursor.execute('UPDATE "' + cls._table + '" s '
                'SET party = e.party FROM '
                '"' + Entry._table + '" e '
                'WHERE e.id = s.entry')

    @staticmethod
    def default_date():
        return datetime.now()

    @staticmethod
    def default_restricted_entry():
        return False

    @staticmethod
    def default_trace_report():
        Party = Pool().get('party.party')
        if (Transaction().context.get('party', 0) > 0):
            party = Party(Transaction().context.get('party'))
            return party.trace_report
        return False

    @staticmethod
    def default_state():
        return 'draft'

    @staticmethod
    def default_qty_lines_pending():
        return None

    @staticmethod
    def default_qty_lines_pending_acceptance():
        return None

    @classmethod
    def copy(cls, samples, default=None):
        if default is None:
            default = {}
        current_default = default.copy()
        current_default['qty_lines_pending'] = None
        current_default['qty_lines_pending_acceptance'] = None

        new_samples = []
        for sample in sorted(samples, key=lambda x: x.number):
            new_sample, = super().copy([sample],
                default=current_default)
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
        EntryPreAssignedSample = pool.get('lims.entry.pre_assigned_sample')

        workyear_id = LabWorkYear.find()
        workyear = LabWorkYear(workyear_id)
        sequence = workyear.get_sequence('sample')
        if not sequence:
            raise UserError(gettext('lims.msg_no_sample_sequence',
                work_year=workyear.rec_name))

        vlist = [x.copy() for x in vlist]
        for values in vlist:
            number = EntryPreAssignedSample.get_next_number(values['entry'])
            if not number:
                number = sequence.get()
            values['number'] = number
        samples = super().create(vlist)
        for sample in samples:
            sample.warn_duplicated_label()
        return samples

    def warn_duplicated_label(self):
        return  # deactivated
        Warning = Pool().get('res.user.warning')
        if self.label:
            duplicated = self.search([
                ('entry', '=', self.entry.id),
                ('label', '=', self.label),
                ('id', '!=', self.id),
                ])
            if duplicated:
                key = 'lims_sample_label@%s' % self.number
                if Warning.check(key):
                    raise UserWarning(gettext(
                        'lims.duplicated_label', label=self.label))

    @classmethod
    def write(cls, *args):
        super().write(*args)
        actions = iter(args)
        for samples, vals in zip(actions, actions):
            if vals.get('label'):
                for sample in samples:
                    sample.warn_duplicated_label()

    @classmethod
    def view_attributes(cls):
        return [
            ('/tree/field[@name="qty_lines_pending_acceptance"]',
                'visual', If(Eval('qty_lines_pending_acceptance', 0) > 0,
                'danger', '')),
            ]

    @fields.depends('product_type', 'matrix', 'zone',
        '_parent_product_type.restricted_entry',
        '_parent_matrix.restricted_entry', '_parent_zone.restricted_entry')
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
                raise UserError(
                    gettext('lims.msg_delete_sample', sample=sample.rec_name))

    @classmethod
    def delete(cls, samples):
        cls.check_delete(samples)
        super().delete(samples)

    @staticmethod
    def default_entry_view():
        if (Transaction().context.get('entry', 0) > 0):
            return Transaction().context.get('entry')
        return None

    @fields.depends('entry', '_parent_entry.id')
    def on_change_with_entry_view(self, name=None):
        if self.entry:
            return self.entry.id
        return None

    @staticmethod
    def default_party():
        if (Transaction().context.get('party', 0) > 0):
            return Transaction().context.get('party')
        return None

    @fields.depends('entry', '_parent_entry.party')
    def on_change_with_party(self, name=None):
        if self.entry:
            result = self.get_entry_field((self,), ('party',))
            return result['party'][self.id]
        return None

    @staticmethod
    def default_zone_required():
        Config = Pool().get('lims.configuration')
        return Config(1).zone_required

    def get_zone_required(self, name=None):
        return self.default_zone_required()

    @staticmethod
    def default_zone():
        Party = Pool().get('party.party')
        if (Transaction().context.get('party', 0) > 0):
            party = Party(Transaction().context.get('party'))
            if party.entry_zone:
                return party.entry_zone.id

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
            if cls._fields[name]._type == 'many2one':
                for s in samples:
                    field = getattr(s.entry, name, None)
                    result[name][s.id] = field.id if field else None
            else:
                for s in samples:
                    result[name][s.id] = getattr(s.entry, name, None)
        return result

    @classmethod
    def search_entry_field(cls, name, clause):
        return [('entry.' + name,) + tuple(clause[1:])]

    def _order_entry_field(name):
        def order_field(tables):
            Entry = Pool().get('lims.entry')
            field = Entry._fields[name]
            table, _ = tables[None]
            entry_tables = tables.get('entry')
            if entry_tables is None:
                entry = Entry.__table__()
                entry_tables = {
                    None: (entry, entry.id == table.entry),
                    }
                tables['entry'] = entry_tables
            return field.convert_order(name, entry_tables, Entry)
        return staticmethod(order_field)
    order_invoice_party = _order_entry_field('invoice_party')

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

    @staticmethod
    def order_state(tables):
        table, _ = tables[None]
        order = [Case((table.state == 'draft', 1),
            else_=Case((table.state == 'annulled', 2),
            else_=Case((table.state == 'pending_planning', 3),
            else_=Case((table.state == 'planned', 4),
            else_=Case((table.state == 'in_lab', 5),
            else_=Case((table.state == 'lab_pending_acceptance', 6),
            else_=Case((table.state == 'pending_report', 7),
            else_=Case((table.state == 'in_report', 8),
            else_=Case((table.state == 'report_released', 9),
            else_=0)))))))))]
        return order

    def get_confirmed(self, name=None):
        if not self.fractions:
            return False
        for fraction in self.fractions:
            if not fraction.confirmed:
                return False
        return True

    @classmethod
    def get_icon(cls, samples, name):
        result = {}
        for s in samples:
            if s.state == 'report_released':
                result[s.id] = 'lims-green'
            elif s.state == 'draft':
                result[s.id] = 'lims-red'
            else:
                result[s.id] = 'lims-white'
        return result

    @classmethod
    def order_create_date2(cls, tables):
        return cls.create_date.convert_order('create_date', tables, cls)

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

    @classmethod
    def get_urgent(cls, samples, name):
        pool = Pool()
        Service = pool.get('lims.service')

        result = {}
        for s in samples:
            services = Service.search_count([
                ('sample', '=', s.id),
                ('urgent', '=', True),
                ])
            result[s.id] = True if services > 0 else False
        return result

    @classmethod
    def search_urgent(cls, name, clause):
        field, op, operand = clause
        if (op, operand) in (('=', True), ('!=', False)):
            return [('fractions.services.urgent', '=', True)]
        elif (op, operand) in (('=', False), ('!=', True)):
            urgents = cls.search([('fractions.services.urgent', '=', True)])
            return [('id', 'not in', [u.id for u in urgents])]
        return []

    def get_completion_percentage(self, name=None):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Config = pool.get('lims.configuration')
        NotebookLine = pool.get('lims.notebook.line')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        Notebook = pool.get('lims.notebook')
        Fraction = pool.get('lims.fraction')
        FractionType = pool.get('lims.fraction.type')

        _ZERO = Decimal(0)
        samples_in_progress = Config(1).samples_in_progress
        digits = Sample.completion_percentage.digits[1]

        cursor.execute('SELECT nl.notebook, nl.analysis, nl.method, '
                'nl.accepted, nl.result, nl.literal_result, '
                'nl.result_modifier '
            'FROM "' + NotebookLine._table + '" nl '
                'INNER JOIN "' + EntryDetailAnalysis._table + '" d '
                'ON d.id = nl.analysis_detail '
                'INNER JOIN "' + Notebook._table + '" n '
                'ON n.id = nl.notebook '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON f.id = n.fraction '
                'INNER JOIN "' + FractionType._table + '" ft '
                'ON ft.id = f.type '
            'WHERE ft.report = TRUE '
                'AND f.sample = %s '
                'AND nl.report = TRUE '
                'AND nl.annulled = FALSE',
            (self.id,))
        notebook_lines = cursor.fetchall()
        total = len(notebook_lines)
        if not total:
            return _ZERO

        # Check repetitions
        oks, to_check = [], []

        if samples_in_progress == 'accepted':
            for line in notebook_lines:
                key = (line[0], line[1], line[2])
                if line[3]:
                    oks.append(key)
                else:
                    to_check.append(key)

        elif samples_in_progress == 'result':
            for line in notebook_lines:
                key = (line[0], line[1], line[2])
                if (line[4] not in [None, ''] or
                        line[5] not in [None, ''] or
                        line[6] in ['d', 'nd', 'pos',
                        'neg', 'ni', 'abs', 'pre', 'na']):
                    oks.append(key)
                else:
                    to_check.append(key)

        accepted = len(oks)
        if not accepted:
            return _ZERO

        for key in to_check:
            if key in oks:
                total -= 1

        return Decimal(
            Decimal(accepted) / Decimal(total)
            ).quantize(Decimal(str(10 ** -digits)))

    @classmethod
    def get_department(cls, samples, name):
        result = {}
        for s in samples:
            field = getattr(s.product_type, name, None)
            result[s.id] = field.id if field else None
        return result

    @classmethod
    def search_department(cls, name, clause):
        return [('product_type.' + name,) + tuple(clause[1:])]

    @staticmethod
    def order_department(tables):
        ProductType = Pool().get('lims.product.type')
        field = ProductType._fields['department']
        table, _ = tables[None]
        product_type_tables = tables.get('product_type')
        if product_type_tables is None:
            product_type = ProductType.__table__()
            product_type_tables = {
                None: (product_type, product_type.id == table.product_type),
                }
            tables['product_type'] = product_type_tables
        return field.convert_order('department', product_type_tables,
            ProductType)

    @classmethod
    def get_results_reports_list(cls, samples, name):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        ResultsReport = pool.get('lims.results_report')
        ResultsVersion = pool.get('lims.results_report.version')
        ResultsDetail = pool.get('lims.results_report.version.detail')
        ResultsSample = pool.get('lims.results_report.version.detail.sample')
        Notebook = pool.get('lims.notebook')
        Fraction = pool.get('lims.fraction')

        result = {}
        for s in samples:
            result[s.id] = ''
            cursor.execute('SELECT r.number '
                'FROM "' + ResultsReport._table + '" r '
                    'INNER JOIN "' + ResultsVersion._table + '" rv '
                    'ON r.id = rv.results_report '
                    'INNER JOIN "' + ResultsDetail._table + '" rd '
                    'ON rv.id = rd.report_version '
                    'INNER JOIN "' + ResultsSample._table + '" rs '
                    'ON rd.id = rs.version_detail '
                    'INNER JOIN "' + Notebook._table + '" n '
                    'ON n.id = rs.notebook '
                    'INNER JOIN "' + Fraction._table + '" f '
                    'ON f.id = n.fraction '
                'WHERE f.sample = %s',
                (s.id,))
            details = [x[0] for x in cursor.fetchall()]
            if details:
                result[s.id] = ', '.join(details)
        return result

    @classmethod
    def search_results_reports_list(cls, name, clause):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        ResultsReport = pool.get('lims.results_report')
        ResultsVersion = pool.get('lims.results_report.version')
        ResultsDetail = pool.get('lims.results_report.version.detail')
        ResultsSample = pool.get('lims.results_report.version.detail.sample')
        Notebook = pool.get('lims.notebook')
        Fraction = pool.get('lims.fraction')

        value = clause[2]
        cursor.execute('SELECT f.sample '
            'FROM "' + ResultsReport._table + '" r '
                'INNER JOIN "' + ResultsVersion._table + '" rv '
                'ON r.id = rv.results_report '
                'INNER JOIN "' + ResultsDetail._table + '" rd '
                'ON rv.id = rd.report_version '
                'INNER JOIN "' + ResultsSample._table + '" rs '
                'ON rd.id = rs.version_detail '
                'INNER JOIN "' + Notebook._table + '" n '
                'ON n.id = rs.notebook '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON f.id = n.fraction '
            'WHERE r.number ILIKE %s',
            (value,))
        samples_ids = [x[0] for x in cursor.fetchall()]
        if not samples_ids:
            return [('id', '=', -1)]
        return [('id', 'in', samples_ids)]

    @classmethod
    def update_samples_state(cls, sample_ids):
        samples = cls.browse(sample_ids)
        for sample in samples:
            sample.update_sample_dates()
            sample.update_sample_state()
            sample.update_qty_lines()

    def update_sample_dates(self):
        dates = self._get_sample_dates()
        for field, value in dates.items():
            setattr(self, field, value)
        self.save()

    def _get_sample_dates(self):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Fraction = pool.get('lims.fraction')
        Service = pool.get('lims.service')
        Notebook = pool.get('lims.notebook')
        NotebookLine = pool.get('lims.notebook.line')
        ResultsReport = pool.get('lims.results_report')
        ResultsVersion = pool.get('lims.results_report.version')
        ResultsDetail = pool.get('lims.results_report.version.detail')
        ResultsSample = pool.get('lims.results_report.version.detail.sample')

        res = {}

        # Confirmation date
        cursor.execute('SELECT MIN(s.confirmation_date) '
            'FROM "' + Service._table + '" s '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON f.id = s.fraction '
            'WHERE f.sample = %s',
            (self.id,))
        res['confirmation_date'] = cursor.fetchone()[0] or None

        # Laboratory deadline
        cursor.execute('SELECT MAX(s.laboratory_date) '
            'FROM "' + Service._table + '" s '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON f.id = s.fraction '
            'WHERE f.sample = %s',
            (self.id,))
        res['laboratory_date'] = cursor.fetchone()[0] or None

        # Date agreed for result
        cursor.execute('SELECT MAX(s.report_date) '
            'FROM "' + Service._table + '" s '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON f.id = s.fraction '
            'WHERE f.sample = %s',
            (self.id,))
        res['report_date'] = cursor.fetchone()[0] or None

        # Laboratory start date
        cursor.execute('SELECT MIN(nl.start_date) '
            'FROM "' + NotebookLine._table + '" nl '
                'INNER JOIN "' + Service._table + '" s '
                'ON s.id = nl.service '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON f.id = s.fraction '
            'WHERE f.sample = %s',
            (self.id,))
        res['laboratory_start_date'] = cursor.fetchone()[0] or None

        # Laboratory end date
        laboratory_end_date = None
        cursor.execute('SELECT COUNT(*) '
            'FROM "' + NotebookLine._table + '" nl '
                'INNER JOIN "' + Service._table + '" s '
                'ON s.id = nl.service '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON f.id = s.fraction '
            'WHERE f.sample = %s '
                'AND nl.report = TRUE '
                'AND nl.annulled = FALSE '
                'AND nl.end_date IS NULL',
            (self.id,))
        if cursor.fetchone()[0] == 0:
            cursor.execute('SELECT MAX(nl.end_date) '
                'FROM "' + NotebookLine._table + '" nl '
                    'INNER JOIN "' + Service._table + '" s '
                    'ON s.id = nl.service '
                    'INNER JOIN "' + Fraction._table + '" f '
                    'ON f.id = s.fraction '
                'WHERE f.sample = %s',
                (self.id,))
            laboratory_end_date = cursor.fetchone()[0] or None
        res['laboratory_end_date'] = laboratory_end_date

        # Laboratory acceptance date
        laboratory_acceptance_date = None
        cursor.execute('SELECT COUNT(*) '
            'FROM "' + NotebookLine._table + '" nl '
                'INNER JOIN "' + Service._table + '" s '
                'ON s.id = nl.service '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON f.id = s.fraction '
            'WHERE f.sample = %s '
                'AND nl.report = TRUE '
                'AND nl.annulled = FALSE '
                'AND nl.acceptance_date IS NULL',
            (self.id,))
        if cursor.fetchone()[0] == 0:
            cursor.execute('SELECT MAX(nl.acceptance_date::date) '
                'FROM "' + NotebookLine._table + '" nl '
                    'INNER JOIN "' + Service._table + '" s '
                    'ON s.id = nl.service '
                    'INNER JOIN "' + Fraction._table + '" f '
                    'ON f.id = s.fraction '
                'WHERE f.sample = %s',
                (self.id,))
            laboratory_acceptance_date = cursor.fetchone()[0] or None
        res['laboratory_acceptance_date'] = laboratory_acceptance_date

        # Report start date
        cursor.execute('SELECT MIN(r.create_date::date) '
            'FROM "' + ResultsReport._table + '" r '
                'INNER JOIN "' + ResultsVersion._table + '" rv '
                'ON rv.results_report = r.id '
                'INNER JOIN "' + ResultsDetail._table + '" rd '
                'ON rd.report_version = rv.id '
                'INNER JOIN "' + ResultsSample._table + '" rs '
                'ON rs.version_detail = rd.id '
                'INNER JOIN "' + Notebook._table + '" n '
                'ON n.id = rs.notebook '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON f.id = n.fraction '
            'WHERE f.sample = %s '
                'AND rd.type != \'preliminary\'',
            (self.id,))
        res['results_report_create_date'] = cursor.fetchone()[0] or None

        # Report release date
        cursor.execute('SELECT MAX(rd.release_date::date) '
            'FROM "' + ResultsDetail._table + '" rd '
                'INNER JOIN "' + ResultsSample._table + '" rs '
                'ON rs.version_detail = rd.id '
                'INNER JOIN "' + Notebook._table + '" n '
                'ON n.id = rs.notebook '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON f.id = n.fraction '
            'WHERE f.sample = %s '
                'AND rd.valid '
                'AND rd.type != \'preliminary\'',
            (self.id,))
        res['results_report_release_date'] = cursor.fetchone()[0] or None

        return res

    def update_sample_state(self):
        state = self._get_sample_state()
        if self.state != state:
            self.state = state
            self.save()

    def _get_sample_state(self):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Fraction = pool.get('lims.fraction')
        Service = pool.get('lims.service')
        NotebookLine = pool.get('lims.notebook.line')

        if self.results_report_release_date:
            return 'report_released'
        if self.results_report_create_date:
            return 'in_report'
        if self.laboratory_acceptance_date:
            return 'pending_report'
        cursor.execute('SELECT COUNT(*) '
            'FROM "' + NotebookLine._table + '" nl '
                'INNER JOIN "' + Service._table + '" s '
                'ON s.id = nl.service '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON f.id = s.fraction '
            'WHERE f.sample = %s '
                'AND nl.annulled = TRUE',
            (self.id,))
        annulled_lines = cursor.fetchone()[0]
        if annulled_lines > 0:
            cursor.execute('SELECT COUNT(*) '
                'FROM "' + NotebookLine._table + '" nl '
                    'INNER JOIN "' + Service._table + '" s '
                    'ON s.id = nl.service '
                    'INNER JOIN "' + Fraction._table + '" f '
                    'ON f.id = s.fraction '
                'WHERE f.sample = %s',
                (self.id,))
            if cursor.fetchone()[0] == annulled_lines:
                return 'annulled'
        if self.laboratory_end_date:
            return 'lab_pending_acceptance'
        if self.laboratory_start_date:
            cursor.execute('SELECT COUNT(*) '
                'FROM "' + NotebookLine._table + '" nl '
                    'INNER JOIN "' + Service._table + '" s '
                    'ON s.id = nl.service '
                    'INNER JOIN "' + Fraction._table + '" f '
                    'ON f.id = s.fraction '
                'WHERE f.sample = %s '
                    'AND nl.report = TRUE '
                    'AND nl.annulled = FALSE '
                    'AND nl.end_date IS NOT NULL',
                (self.id,))
            if cursor.fetchone()[0] > 0:
                return 'in_lab'
            return 'planned'
        if self.confirmation_date:
            return 'pending_planning'
        return 'draft'

    def update_qty_lines(self):
        save = False
        qty = self._get_qty_lines_pending()
        if self.qty_lines_pending != qty:
            self.qty_lines_pending = qty
            save = True
        qty = self._get_qty_lines_pending_acceptance()
        if self.qty_lines_pending_acceptance != qty:
            self.qty_lines_pending_acceptance = qty
            save = True
        if save:
            self.save()

    def _get_qty_lines_pending(self):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Fraction = pool.get('lims.fraction')
        Service = pool.get('lims.service')
        NotebookLine = pool.get('lims.notebook.line')

        cursor.execute('SELECT COUNT(*) '
            'FROM "' + NotebookLine._table + '" nl '
                'INNER JOIN "' + Service._table + '" s '
                'ON s.id = nl.service '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON f.id = s.fraction '
            'WHERE f.sample = %s '
                'AND nl.report = TRUE '
                'AND nl.annulled = FALSE '
                'AND nl.end_date IS NULL',
            (self.id,))
        return cursor.fetchone()[0]

    def _get_qty_lines_pending_acceptance(self):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Fraction = pool.get('lims.fraction')
        Service = pool.get('lims.service')
        NotebookLine = pool.get('lims.notebook.line')

        cursor.execute('SELECT COUNT(*) '
            'FROM "' + NotebookLine._table + '" nl '
                'INNER JOIN "' + Service._table + '" s '
                'ON s.id = nl.service '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON f.id = s.fraction '
            'WHERE f.sample = %s '
                'AND nl.report = TRUE '
                'AND nl.annulled = FALSE '
                'AND nl.end_date IS NOT NULL '
                'AND nl.acceptance_date IS NULL',
            (self.id,))
        return cursor.fetchone()[0]


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

    def end(self):
        return 'reload'


class DuplicateSampleFromEntryStart(ModelView):
    'Copy Sample'
    __name__ = 'lims.entry.duplicate_sample.start'

    entry = fields.Many2One('lims.entry', 'Entry')
    sample = fields.Many2One('lims.sample', 'Sample', required=True,
        domain=[('entry', '=', Eval('entry'))], depends=['entry'])
    date = fields.DateTime('Date', required=True)
    labels = fields.Text('Labels')

    @fields.depends('sample', '_parent_sample.date')
    def on_change_with_date(self, name=None):
        if self.sample:
            return self.sample.date
        return None


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


class ManageServicesAckOfReceipt(ModelView):
    'Manage Services'
    __name__ = 'lims.manage_services.ack_of_receipt'


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
    send_ack_of_receipt = StateView('lims.manage_services.ack_of_receipt',
        'lims.lims_manage_services_ack_of_receipt_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Send', 'send_ack', 'tryton-ok', default=True),
            ])
    send_ack = StateTransition()

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
            raise UserError(gettext('lims.msg_counter_sample_date'))
        return 'end'

    def transition_ok(self):
        pool = Pool()
        Entry = pool.get('lims.entry')
        Fraction = pool.get('lims.fraction')

        delete_ack_report_cache = False
        fraction = Fraction(Transaction().context['active_id'])

        actual_services_ids = [s.id for s in self.start.services]
        other_services_ids = [s.id for s in fraction.services if
            not s.manage_service_available]
        actual_services = []
        for s in self.start.services:
            if not s.is_additional:
                actual_services.append(s)
            else:
                for origin in s.additional_origins:
                    if origin.id in actual_services_ids:
                        actual_services.append(s)
                        break
                    if origin.id in other_services_ids:
                        actual_services.append(s)
                        break
        original_services = [s for s in fraction.services if
            s.manage_service_available]
        services_to_delete = []

        for service in original_services:
            if service not in actual_services:
                services_to_delete.append(service)
                delete_ack_report_cache = True
        if services_to_delete:
            self.delete_services(services_to_delete)

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
                            #break

        if delete_ack_report_cache:
            entry = Entry(fraction.entry.id)
            entry.ack_report_format = None
            entry.ack_report_cache = None
            entry.save()

        if self._send_ack_of_receipt():
            return 'send_ack_of_receipt'

        return 'end'

    def create_service(self, service, fraction):
        pool = Pool()
        Service = pool.get('lims.service')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        service_create = [{
            'fraction': fraction.id,
            'sample': service.sample.id,
            'analysis': service.analysis.id,
            'laboratory': (service.laboratory.id if service.laboratory
                else None),
            'method': service.method.id if service.method else None,
            'device': service.device.id if service.device else None,
            'urgent': service.urgent,
            'priority': service.priority,
            'estimated_waiting_laboratory': (
                service.estimated_waiting_laboratory),
            'estimated_waiting_report': (
                service.estimated_waiting_report),
            'laboratory_date': service.laboratory_date,
            'report_date': service.report_date,
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

    def delete_services(self, services):
        Service = Pool().get('lims.service')
        with Transaction().set_user(0, set_context=True):
            Service.delete(services)

    def update_service(self, original_service, actual_service, fraction,
            field_changed):
        pool = Pool()
        Service = pool.get('lims.service')
        NotebookLine = pool.get('lims.notebook.line')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        service_write = {}
        service_write[field_changed] = getattr(actual_service, field_changed)
        Service.write([original_service], service_write)

        update_details = (True if field_changed in self._get_update_details()
            else False)

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
                    'confirmation_date': original_service.confirmation_date,
                    })
            if fraction.cie_fraction_type:
                self._create_blind_samples(analysis_detail, fraction)

    def _get_update_details(self):
        return ('analysis', 'laboratory', 'method', 'device')

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
            'priority', 'estimated_waiting_laboratory',
            'estimated_waiting_report', 'report_date', 'comments', 'divide')

    def _send_ack_of_receipt(self):
        Cron = Pool().get('ir.cron')
        if Cron.search([
                ('method', '=', 'lims.entry|cron_acknowledgment_of_receipt'),
                ('active', '=', True),
                ]):
            return True
        return False

    def transition_send_ack(self):
        pool = Pool()
        Fraction = pool.get('lims.fraction')
        ForwardAcknowledgmentOfReceipt = pool.get(
            'lims.entry.acknowledgment.forward', type='wizard')

        fraction = Fraction(Transaction().context['active_id'])
        entry_ids = [fraction.sample.entry.id]

        session_id, _, _ = ForwardAcknowledgmentOfReceipt.create()
        acknowledgment_forward = ForwardAcknowledgmentOfReceipt(session_id)
        with Transaction().set_context(active_ids=entry_ids):
            acknowledgment_forward.transition_start()
        return 'end'


class CompleteServices(Wizard):
    'Complete Services'
    __name__ = 'lims.complete_services'

    start = StateTransition()

    def transition_start(self):
        Fraction = Pool().get('lims.fraction')
        fraction = Fraction(Transaction().context['active_id'])
        analysis_domain_ids = fraction.on_change_with_analysis_domain()
        for service in fraction.services:
            if service.analysis.id not in analysis_domain_ids:
                raise UserError(gettext('lims.msg_not_typified',
                    analysis=service.analysis.rec_name,
                    product_type=fraction.product_type.rec_name,
                    matrix=fraction.matrix.rec_name,
                    ))
            self.complete_analysis_detail(service)
        return 'end'

    def complete_analysis_detail(self, service):
        'Similar to Service.update_analysis_detail(services)'
        pool = Pool()
        Service = pool.get('lims.service')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        if service.annulled:
            return
        to_delete = EntryDetailAnalysis.search([
            ('service', '=', service.id),
            ('state', 'in', ('draft', 'unplanned')),
            ])
        if to_delete:
            with Transaction().set_user(0, set_context=True):
                EntryDetailAnalysis.delete(to_delete)
        if service.analysis.behavior == 'additional':
            return

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
                    ('fraction', '=', service.fraction.id),
                    ('analysis', '=', analysis['id']),
                    ('method', '=', analysis['method']),
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
            values['state'] = 'unplanned'
            to_create.append(values)

        if to_create:
            with Transaction().set_user(0, set_context=True):
                analysis_detail = EntryDetailAnalysis.create(to_create)
            if analysis_detail:
                EntryDetailAnalysis.create_notebook_lines(analysis_detail,
                    service.fraction)


class LoadServices(Wizard):
    'Load Services'
    __name__ = 'lims.load_services'

    start_state = 'check'
    check = StateTransition()
    load = StateTransition()

    def transition_check(self):
        Fraction = Pool().get('lims.fraction')

        fraction = Fraction(Transaction().context['active_id'])
        if (not fraction or not fraction.cie_fraction_type or
                not fraction.cie_original_fraction):
            return 'end'
        return 'load'

    def transition_load(self):
        pool = Pool()
        Fraction = pool.get('lims.fraction')
        Service = pool.get('lims.service')
        Analysis = pool.get('lims.analysis')

        new_fraction = Fraction(Transaction().context['active_id'])
        original_fraction = new_fraction.cie_original_fraction

        # new services
        services = Service.search([
            ('fraction', '=', original_fraction),
            ('annulled', '=', False),
            ])
        for service in services:
            if not Analysis.is_typified(service.analysis,
                    new_fraction.product_type, new_fraction.matrix):
                continue
            new_service, = Service.copy([service], default={
                'fraction': new_fraction.id,
                })
        return 'end'


class AddSampleServiceStart(ModelView):
    'Add Sample Services'
    __name__ = 'lims.sample.add_service.start'

    product_type = fields.Many2One('lims.product.type', 'Product type')
    matrix = fields.Many2One('lims.matrix', 'Matrix')
    analysis_domain = fields.Many2Many('lims.analysis', None, None,
        'Analysis domain')
    services = fields.One2Many('lims.create_sample.service', None, 'Services',
        required=True, depends=['analysis_domain', 'product_type', 'matrix'],
        context={
            'analysis_domain': Eval('analysis_domain'),
            'product_type': Eval('product_type'), 'matrix': Eval('matrix'),
            })


class AddSampleServiceAckOfReceipt(ModelView):
    'Add Sample Services'
    __name__ = 'lims.sample.add_service.ack_of_receipt'


class AddSampleService(Wizard):
    'Add Sample Services'
    __name__ = 'lims.sample.add_service'

    start = StateView('lims.sample.add_service.start',
        'lims.add_sample_service_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Confirm', 'confirm', 'tryton-ok', default=True),
            ])
    confirm = StateTransition()
    send_ack_of_receipt = StateView('lims.sample.add_service.ack_of_receipt',
        'lims.add_sample_service_ack_of_receipt_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Send', 'send_ack', 'tryton-ok', default=True),
            ])
    send_ack = StateTransition()

    def default_start(self, fields):
        Sample = Pool().get('lims.sample')

        sample = Sample(Transaction().context['active_id'])
        if not sample:
            return {}

        analysis_domain_ids = sample.on_change_with_analysis_domain()

        default = {
            'product_type': sample.product_type.id,
            'matrix': sample.matrix.id,
            'analysis_domain': analysis_domain_ids,
            'services': [],
            }
        return default

    def transition_confirm(self):
        pool = Pool()
        Sample = pool.get('lims.sample')
        Entry = pool.get('lims.entry')

        for sample in Sample.browse(Transaction().context['active_ids']):
            delete_ack_report_cache = False
            for fraction in sample.fractions:
                original_analysis = []
                for service in fraction.services:
                    if service.annulled:
                        continue
                    key = (service.analysis.id,
                        service.method and service.method.id or None)
                    original_analysis.append(key)
                for service in self.start.services:
                    key = (service.analysis.id,
                        service.method and service.method.id or None)
                    if key not in original_analysis:
                        self.create_service(service, fraction)
                        delete_ack_report_cache = True

            if delete_ack_report_cache:
                entry = Entry(sample.entry.id)
                entry.ack_report_format = None
                entry.ack_report_cache = None
                entry.save()

        if self._send_ack_of_receipt():
            return 'send_ack_of_receipt'

        return 'end'

    def create_service(self, service, fraction):
        pool = Pool()
        Service = pool.get('lims.service')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        service_create = [{
            'fraction': fraction.id,
            'sample': fraction.sample.id,
            'analysis': service.analysis.id,
            'laboratory': (service.laboratory.id if service.laboratory
                else None),
            'method': service.method.id if service.method else None,
            'device': service.device.id if service.device else None,
            'urgent': service.urgent,
            'priority': service.priority,
            'estimated_waiting_laboratory': (
                service.estimated_waiting_laboratory),
            'estimated_waiting_report': (
                service.estimated_waiting_report),
            'laboratory_date': service.laboratory_date,
            'report_date': service.report_date,
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

        return new_service

    def _send_ack_of_receipt(self):
        Cron = Pool().get('ir.cron')
        if Cron.search([
                ('method', '=', 'lims.entry|cron_acknowledgment_of_receipt'),
                ('active', '=', True),
                ]):
            return True
        return False

    def transition_send_ack(self):
        pool = Pool()
        Sample = pool.get('lims.sample')
        ForwardAcknowledgmentOfReceipt = pool.get(
            'lims.entry.acknowledgment.forward', type='wizard')

        entry_ids = set()
        for sample in Sample.browse(Transaction().context['active_ids']):
            entry_ids.add(sample.entry.id)

        session_id, _, _ = ForwardAcknowledgmentOfReceipt.create()
        acknowledgment_forward = ForwardAcknowledgmentOfReceipt(session_id)
        with Transaction().set_context(active_ids=list(entry_ids)):
            acknowledgment_forward.transition_start()
        return 'end'


class EditSampleServiceStart(ModelView):
    'Edit Sample Services'
    __name__ = 'lims.sample.edit_service.start'

    product_type = fields.Many2One('lims.product.type', 'Product type')
    matrix = fields.Many2One('lims.matrix', 'Matrix')
    analysis_domain = fields.Many2Many('lims.analysis', None, None,
        'Analysis domain')
    services = fields.One2Many('lims.create_sample.service', None, 'Services',
        required=True, depends=['analysis_domain', 'product_type', 'matrix'],
        context={
            'analysis_domain': Eval('analysis_domain'),
            'product_type': Eval('product_type'), 'matrix': Eval('matrix'),
            })


class EditSampleServiceAckOfReceipt(ModelView):
    'Edit Sample Services'
    __name__ = 'lims.sample.edit_service.ack_of_receipt'


class EditSampleService(Wizard):
    'Edit Sample Services'
    __name__ = 'lims.sample.edit_service'

    start = StateView('lims.sample.edit_service.start',
        'lims.edit_sample_service_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Confirm', 'confirm', 'tryton-ok', default=True),
            ])
    confirm = StateTransition()
    send_ack_of_receipt = StateView('lims.sample.edit_service.ack_of_receipt',
        'lims.edit_sample_service_ack_of_receipt_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Send', 'send_ack', 'tryton-ok', default=True),
            ])
    send_ack = StateTransition()

    def default_start(self, fields):
        Sample = Pool().get('lims.sample')

        sample = Sample(Transaction().context['active_id'])
        if not sample:
            return {}

        analysis_domain_ids = sample.on_change_with_analysis_domain()
        services = []
        for f in sample.fractions:
            for s in f.services:
                if s.annulled:
                    continue
                services.append({
                    'analysis_locked': True,
                    'laboratory_locked': True,
                    'analysis': s.analysis.id,
                    'laboratory': s.laboratory and s.laboratory.id or None,
                    'method': s.method and s.method.id or None,
                    'device': s.device and s.device.id or None,
                    'urgent': s.urgent,
                    'priority': s.priority,
                    'estimated_waiting_laboratory': (
                        s.estimated_waiting_laboratory),
                    'estimated_waiting_report': (
                        s.estimated_waiting_report),
                    'laboratory_date': s.laboratory_date,
                    'report_date': s.report_date,
                    'divide': s.divide,
                    })

        default = {
            'product_type': sample.product_type.id,
            'matrix': sample.matrix.id,
            'analysis_domain': analysis_domain_ids,
            'services': services,
            }
        return default

    def transition_confirm(self):
        pool = Pool()
        Sample = pool.get('lims.sample')
        Entry = pool.get('lims.entry')

        actual_analysis = [(s.analysis.id, s.method and s.method.id or None)
            for s in self.start.services]

        for sample in Sample.browse(Transaction().context['active_ids']):
            delete_ack_report_cache = False
            for fraction in sample.fractions:
                original_analysis = []
                for service in fraction.services:
                    if service.annulled:
                        continue
                    key = (service.analysis.id,
                        service.method and service.method.id or None)
                    original_analysis.append(key)
                    if key not in actual_analysis:
                        self.annul_service(service)
                        delete_ack_report_cache = True
                for service in self.start.services:
                    key = (service.analysis.id,
                        service.method and service.method.id or None)
                    if key not in original_analysis:
                        self.create_service(service, fraction)
                        delete_ack_report_cache = True
                self.update_fraction_services(fraction)

            if delete_ack_report_cache:
                entry = Entry(sample.entry.id)
                entry.ack_report_format = None
                entry.ack_report_cache = None
                entry.save()

        if self._send_ack_of_receipt():
            return 'send_ack_of_receipt'

        return 'end'

    def annul_service(self, service):
        service.annulled = True
        service.save()

    def create_service(self, service, fraction):
        pool = Pool()
        Service = pool.get('lims.service')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        service_create = [{
            'fraction': fraction.id,
            'sample': fraction.sample.id,
            'analysis': service.analysis.id,
            'laboratory': (service.laboratory.id if service.laboratory
                else None),
            'method': service.method.id if service.method else None,
            'device': service.device.id if service.device else None,
            'urgent': service.urgent,
            'priority': service.priority,
            'estimated_waiting_laboratory': (
                service.estimated_waiting_laboratory),
            'estimated_waiting_report': (
                service.estimated_waiting_report),
            'laboratory_date': service.laboratory_date,
            'report_date': service.report_date,
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

        return new_service

    def update_fraction_services(self, fraction):
        pool = Pool()
        Service = pool.get('lims.service')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        NotebookLine = pool.get('lims.notebook.line')

        annulled_services = Service.search([
            ('fraction', '=', fraction),
            ('annulled', '=', True),
            ])
        for annulled_service in annulled_services:
            original_details = EntryDetailAnalysis.search([
                ('service', '=', annulled_service),
                ])
            for original_detail in original_details:
                duplicated_details = self._get_duplicated_details(
                    original_detail)
                if duplicated_details:
                    self._migrate_detail(original_detail,
                        duplicated_details[0])
                    with Transaction().set_user(0, set_context=True):
                        duplicated_nlines = NotebookLine.search([
                            ('analysis_detail', 'in', duplicated_details),
                            ])
                        NotebookLine.delete(duplicated_nlines)
                        EntryDetailAnalysis.delete(duplicated_details)
                else:
                    self._annul_detail(original_detail)

    def _get_duplicated_details(self, original):
        EntryDetailAnalysis = Pool().get('lims.entry.detail.analysis')
        duplicated_details = EntryDetailAnalysis.search([
            ('fraction', '=', original.fraction),
            ('analysis', '=', original.analysis),
            ('method', '=', original.method),
            ('service', '!=', original.service),
            ])
        return duplicated_details

    def _migrate_detail(self, original, duplicated):
        NotebookLine = Pool().get('lims.notebook.line')

        original.service = duplicated.service
        original.analysis_origin = duplicated.analysis_origin
        #original.device = duplicated.device
        original.save()

        with Transaction().set_user(0, set_context=True):
            notebook_lines = NotebookLine.search([
                ('analysis_detail', '=', original),
                ])
            NotebookLine.write(notebook_lines, {
                'service': original.service.id,
                'analysis_origin': original.analysis_origin,
                #'device': original.device and original.device.id or None,
                })

    def _annul_detail(self, original):
        NotebookLine = Pool().get('lims.notebook.line')

        if NotebookLine.search_count([
                ('analysis_detail', '=', original),
                ('results_report', '!=', None),
                ]) > 0:
            raise UserError(gettext('lims.msg_annul_analysis',
                analysis=original.analysis.rec_name))

        with Transaction().set_user(0, set_context=True):
            notebook_lines = NotebookLine.search([
                ('analysis_detail', '=', original),
                ])
            NotebookLine.write(notebook_lines, {
                'annulled': True,
                'annulment_date': datetime.now(),
                'accepted': False,
                'acceptance_date': None,
                'report': False,
                })

        original.state = 'annulled'
        original.save()

    def _send_ack_of_receipt(self):
        Cron = Pool().get('ir.cron')
        if Cron.search([
                ('method', '=', 'lims.entry|cron_acknowledgment_of_receipt'),
                ('active', '=', True),
                ]):
            return True
        return False

    def transition_send_ack(self):
        pool = Pool()
        Sample = pool.get('lims.sample')
        ForwardAcknowledgmentOfReceipt = pool.get(
            'lims.entry.acknowledgment.forward', type='wizard')

        entry_ids = set()
        for sample in Sample.browse(Transaction().context['active_ids']):
            entry_ids.add(sample.entry.id)

        session_id, _, _ = ForwardAcknowledgmentOfReceipt.create()
        acknowledgment_forward = ForwardAcknowledgmentOfReceipt(session_id)
        with Transaction().set_context(active_ids=list(entry_ids)):
            acknowledgment_forward.transition_start()
        return 'end'


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

                    # Check repetitions
                    oks, to_check = [], []
                    for line in notebook_lines:
                        key = (line.analysis.id, line.method.id)
                        if not line.accepted:
                            to_check.append(key)
                        else:
                            oks.append(key)

                    to_check = list(set(to_check) - set(oks))
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
        ResultsLine = pool.get('lims.results_report.version.detail.line')
        ResultsSample = pool.get('lims.results_report.version.detail.sample')
        ResultsDetail = pool.get('lims.results_report.version.detail')
        ResultsVersion = pool.get('lims.results_report.version')

        cursor.execute('SELECT rvdl.id '
            'FROM "' + ResultsLine._table + '" rvdl '
                'INNER JOIN "' + ResultsSample._table + '" rvds '
                'ON rvds.id = rvdl.detail_sample '
                'INNER JOIN "' + ResultsDetail._table + '" rvd '
                'ON rvd.id = rvds.version_detail '
                'INNER JOIN "' + ResultsVersion._table + '" rv '
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
        shipment.reference = gettext('lims.msg_reference')
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
        User = pool.get('res.user')
        Move = pool.get('stock.move')

        config_ = Config(1)
        if config_.fraction_product:
            product = config_.fraction_product
        else:
            raise UserError(gettext('lims.msg_missing_fraction_product'))
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
            if move.on_change_with_unit_price_required():
                move.unit_price = 0
                move.currency = company.currency
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
        shipment.reference = gettext('lims.msg_reference_reversion')
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
        User = pool.get('res.user')
        Date = pool.get('ir.date')
        Move = pool.get('stock.move')

        config_ = Config(1)
        if config_.fraction_product:
            product = config_.fraction_product
        else:
            raise UserError(gettext('lims.msg_missing_fraction_product'))
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
            if move.on_change_with_unit_price_required():
                move.unit_price = 0
                move.currency = company.currency
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
        shipment.reference = gettext('lims.msg_reference_discharge')
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
        User = pool.get('res.user')
        Move = pool.get('stock.move')

        config_ = Config(1)
        if config_.fraction_product:
            product = config_.fraction_product
        else:
            raise UserError(gettext('lims.msg_missing_fraction_product'))
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
            if move.on_change_with_unit_price_required():
                move.unit_price = 0
                move.currency = company.currency
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
        shipment.reference = gettext('lims.msg_reference_fractions_discharge')
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
        User = pool.get('res.user')
        Move = pool.get('stock.move')

        config_ = Config(1)
        if config_.fraction_product:
            product = config_.fraction_product
        else:
            raise UserError(gettext('lims.msg_missing_fraction_product'))
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
            if move.on_change_with_unit_price_required():
                move.unit_price = 0
                move.currency = company.currency
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
        shipment.reference = gettext('lims.msg_reference')
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
        User = pool.get('res.user')
        Date = pool.get('ir.date')
        Move = pool.get('stock.move')

        config_ = Config(1)
        if config_.fraction_product:
            product = config_.fraction_product
        else:
            raise UserError(gettext('lims.msg_missing_fraction_product'))
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
            if move.on_change_with_unit_price_required():
                move.unit_price = 0
                move.currency = company.currency
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

    party = fields.Many2One('party.party', 'Party', required=True,
        states={'invisible': ~Eval('multi_party')},
        domain=[('id', 'in', Eval('party_domain'))],
        depends=['party_domain', 'multi_party'])
    party_domain = fields.Many2Many('party.party',
        None, None, 'Party domain')
    multi_party = fields.Boolean('Multi Party')
    date = fields.DateTime('Date', required=True)
    producer = fields.Many2One('lims.sample.producer', 'Producer company',
        domain=[('party', '=', Eval('party'))], depends=['party'])
    sample_client_description = fields.Char(
        'Product described by the client', required=True)
    sample_client_description_lang = fields.Char(
        'Product described by the client (foreign language)',
        states={'readonly': ~Eval('foreign_language')},
        depends=['foreign_language'])
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
    obj_description_manual_lang = fields.Char(
        'Manual Objective description (foreign language)',
        states={
            'readonly': Or(
                Bool(Eval('obj_description')),
                ~Eval('foreign_language')),
            },
        depends=['obj_description', 'foreign_language'])
    fraction_state = fields.Many2One('lims.packaging.integrity',
        'Package state', required=True)
    package_type = fields.Many2One('lims.packaging.type', 'Package type',
        required=True)
    packages_quantity = fields.Integer('Packages quantity', required=True)
    restricted_entry = fields.Boolean('Restricted entry',
        states={'readonly': True})
    zone = fields.Many2One('lims.zone', 'Zone',
        states={'required': Bool(Eval('zone_required'))},
        depends=['zone_required'])
    zone_required = fields.Boolean('Zone required',
        states={'readonly': True})
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
    shared = fields.Boolean('Shared')
    analysis_domain = fields.Function(fields.Many2Many('lims.analysis',
        None, None, 'Analysis domain'), 'on_change_with_analysis_domain')
    services = fields.One2Many('lims.create_sample.service', None, 'Services',
        states={'required': ~Eval('without_services')},
        context={
            'analysis_domain': Eval('analysis_domain'),
            'product_type': Eval('product_type'), 'matrix': Eval('matrix'),
            },
        depends=['analysis_domain', 'product_type', 'matrix',
            'without_services'])
    without_services = fields.Boolean('Without services')
    attributes = fields.Dict('lims.sample.attribute', 'Attributes')
    foreign_language = fields.Boolean('Foreign Language')

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

    @fields.depends('product_type', 'matrix', 'zone',
        '_parent_product_type.restricted_entry',
        '_parent_matrix.restricted_entry', '_parent_zone.restricted_entry')
    def on_change_with_restricted_entry(self, name=None):
        return (self.product_type and self.product_type.restricted_entry and
                self.matrix and self.matrix.restricted_entry and
                self.zone and self.zone.restricted_entry)

    @fields.depends('fraction_type', 'storage_location', 'package_type',
        'fraction_state')
    def on_change_fraction_type(self):
        if not self.fraction_type:
            return
        if (not self.storage_location and
                self.fraction_type.default_storage_location):
            self.storage_location = self.fraction_type.default_storage_location
        if (not self.package_type and
                self.fraction_type.default_package_type):
            self.package_type = self.fraction_type.default_package_type
        if (not self.fraction_state and
                self.fraction_type.default_fraction_state):
            self.fraction_state = self.fraction_type.default_fraction_state

    @fields.depends('fraction_type', 'storage_location',
        '_parent_fraction_type.max_storage_time',
        '_parent_storage_location.storage_time')
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
    estimated_waiting_laboratory = fields.Integer(
        'Number of days for Laboratory',
        states={'readonly': ~Eval('report_date_readonly')},
        depends=['report_date_readonly'])
    estimated_waiting_report = fields.Integer(
        'Number of days for Reporting',
        states={'readonly': ~Eval('report_date_readonly')},
        depends=['report_date_readonly'])
    laboratory_date = fields.Date('Laboratory deadline',
        states={'readonly': Bool(Eval('report_date_readonly'))},
        depends=['report_date_readonly'])
    report_date = fields.Date('Date agreed for result',
        states={'readonly': Bool(Eval('report_date_readonly'))},
        depends=['report_date_readonly'])
    report_date_readonly = fields.Boolean('Report deadline Readonly')
    divide = fields.Boolean('Divide Report')
    analysis_locked = fields.Boolean('Analysis/Set/Group Locked')
    laboratory_locked = fields.Boolean('Laboratory Locked')
    explode_analysis = fields.Boolean(
        'Load included analyzes individually',
        states={'invisible': Bool(Eval('explode_analysis_invisible'))},
        depends=['explode_analysis_invisible'])
    explode_analysis_invisible = fields.Boolean(
        'Load included analyzes individually Invisible')

    @staticmethod
    def default_explode_analysis():
        return False

    @staticmethod
    def default_explode_analysis_invisible():
        ModelData = Pool().get('ir.model.data')
        # check if called from wizard Create Sample
        action_id = Transaction().context.get('action_id')
        if (action_id and action_id == ModelData.get_id(
                'lims', 'wiz_lims_create_sample')):
            return False
        return True

    @staticmethod
    def default_analysis_locked():
        return False

    @staticmethod
    def default_laboratory_locked():
        return False

    @staticmethod
    def default_urgent():
        return False

    @staticmethod
    def default_priority():
        return 0

    @staticmethod
    def default_divide():
        return False

    @staticmethod
    def default_report_date_readonly():
        return True

    @fields.depends('analysis', 'analysis_locked')
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
            default_laboratory = self._get_default_laboratory(analysis_id,
                product_type_id, matrix_id)
            if default_laboratory:
                laboratory_id = default_laboratory
            laboratory_domain = self._get_laboratory_domain(analysis_id)
            default_method = self._get_default_method(analysis_id,
                product_type_id, matrix_id)
            method_domain = self._get_method_domain(analysis_id,
                product_type_id, matrix_id)
            if default_method:
                method_id = default_method
            elif len(method_domain) == 1:
                method_id = method_domain[0]
            if laboratory_id:
                device_domain = self._get_device_domain(analysis_id,
                    laboratory_id)
                if len(device_domain) == 1:
                    device_id = device_domain[0]
            self.estimated_waiting_laboratory = (
                self.analysis.estimated_waiting_laboratory)
            self.estimated_waiting_report = (
                self.analysis.estimated_waiting_report)

        self.laboratory_domain = laboratory_domain
        self.method_domain = method_domain
        self.device_domain = device_domain
        if not self.analysis_locked:
            self.laboratory = laboratory_id
            self.method = method_id
            self.device = device_id
        self.analysis_locked = False

    @fields.depends('analysis', 'laboratory', 'laboratory_locked')
    def on_change_laboratory(self):
        analysis_id = self.analysis.id if self.analysis else None
        laboratory_id = self.laboratory.id if self.laboratory else None

        device_id = None
        device_domain = []
        if analysis_id and laboratory_id:
            device_domain = self._get_device_domain(analysis_id,
                laboratory_id)
            if len(device_domain) == 1:
                device_id = device_domain[0]

        self.device_domain = device_domain
        if self.laboratory_locked:
            self.device = device_id
        self.laboratory_locked = False

    @staticmethod
    def _get_default_laboratory(analysis_id, product_type_id, matrix_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Analysis = pool.get('lims.analysis')
        AnalysisLaboratory = pool.get('lims.analysis-laboratory')
        Typification = pool.get('lims.typification')

        if Analysis(analysis_id).type != 'analysis':
            return None

        cursor.execute('SELECT laboratory '
            'FROM "' + Typification._table + '" '
            'WHERE product_type = %s '
                'AND matrix = %s '
                'AND analysis = %s '
                'AND valid IS TRUE '
                'AND by_default IS TRUE '
                'AND laboratory IS NOT NULL',
            (product_type_id, matrix_id, analysis_id))
        res = cursor.fetchone()
        if res:
            return res[0]

        cursor.execute('SELECT laboratory '
            'FROM "' + AnalysisLaboratory._table + '" '
            'WHERE analysis = %s '
                'AND by_default = TRUE '
            'ORDER BY id', (analysis_id,))
        res = cursor.fetchone()
        if res:
            return res[0]

        return None

    @staticmethod
    def _get_laboratory_domain(analysis_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Analysis = pool.get('lims.analysis')
        AnalysisLaboratory = pool.get('lims.analysis-laboratory')

        if Analysis(analysis_id).type != 'analysis':
            return []

        cursor.execute('SELECT DISTINCT(laboratory) '
            'FROM "' + AnalysisLaboratory._table + '" '
            'WHERE analysis = %s',
            (analysis_id,))
        res = cursor.fetchall()
        if not res:
            return []
        return [x[0] for x in res]

    @staticmethod
    def _get_default_method(analysis_id, product_type_id, matrix_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Analysis = pool.get('lims.analysis')
        Typification = pool.get('lims.typification')

        if Analysis(analysis_id).type != 'analysis':
            return None

        cursor.execute('SELECT method '
            'FROM "' + Typification._table + '" '
            'WHERE product_type = %s '
                'AND matrix = %s '
                'AND analysis = %s '
                'AND valid IS TRUE '
                'AND by_default IS TRUE',
            (product_type_id, matrix_id, analysis_id))
        res = cursor.fetchone()
        if res:
            return res[0]

        return None

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
            'WHERE active IS TRUE '
                'AND analysis = %s '
                'AND laboratory = %s '
                'AND by_default IS TRUE',
            (analysis_id, laboratory_id))
        res = cursor.fetchall()
        if not res:
            return []
        return [x[0] for x in res]

    @fields.depends('analysis', 'estimated_waiting_laboratory')
    def on_change_with_laboratory_date(self, name=None):
        pool = Pool()
        LabWorkYear = pool.get('lims.lab.workyear')
        Date = pool.get('ir.date')
        if self.estimated_waiting_laboratory:
            date_ = Date.today()
            workyear = LabWorkYear(LabWorkYear.find(date_))
            date_ = workyear.get_target_date(date_,
                self.estimated_waiting_laboratory)
            return date_
        return None

    @fields.depends('analysis', 'estimated_waiting_laboratory',
        'estimated_waiting_report')
    def on_change_with_report_date(self, name=None):
        pool = Pool()
        LabWorkYear = pool.get('lims.lab.workyear')
        Date = pool.get('ir.date')
        if self.estimated_waiting_laboratory or self.estimated_waiting_report:
            date_ = Date.today()
            workyear = LabWorkYear(LabWorkYear.find(date_))
            if self.estimated_waiting_laboratory:
                date_ = workyear.get_target_date(date_,
                    self.estimated_waiting_laboratory)
            if self.estimated_waiting_report:
                date_ = workyear.get_target_date(date_,
                    self.estimated_waiting_report)
            return date_
        return None


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
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Entry = pool.get('lims.entry')
        Config = pool.get('lims.configuration')
        PartyRelation = pool.get('party.relation')
        Typification = pool.get('lims.typification')

        config_ = Config(1)

        defaults = {
            'date': datetime.now(),
            'restricted_entry': False,
            'zone_required': config_.zone_required,
            'storage_time': 3,
            'without_services': False,
            }

        entry = Entry(Transaction().context['active_id'])
        if entry.multi_party:
            party_domain = [entry.invoice_party.id]
            relations = PartyRelation.search([
                ('to', '=', entry.invoice_party),
                ('type', '=', config_.invoice_party_relation_type)
                ])
            party_domain.extend([r.from_.id for r in relations])
            party_domain = list(set(party_domain))
            party_id = party_domain[0] if len(party_domain) == 1 else None
        else:
            party_domain = [entry.party.id]
            party_id = entry.party.id

        defaults['trace_report'] = entry.party.trace_report
        if entry.party.entry_zone:
            defaults['zone'] = entry.party.entry_zone.id

        cursor.execute('SELECT DISTINCT(product_type) '
            'FROM "' + Typification._table + '" '
            'WHERE valid')
        res = cursor.fetchall()
        if res:
            defaults['product_type_domain'] = [x[0] for x in res]

        defaults['party'] = party_id
        defaults['party_domain'] = party_domain
        defaults['multi_party'] = entry.multi_party
        defaults['foreign_language'] = (entry.report_language !=
            config_.results_report_language)
        return defaults

    def transition_create_(self):
        # TODO: Remove logs
        logger.info('-- CreateSample().transition_create_():INIT --')
        pool = Pool()
        Sample = pool.get('lims.sample')
        Entry = pool.get('lims.entry')

        entry_id = Transaction().context['active_id']
        entry = Entry(entry_id)
        samples_defaults = self._get_samples_defaults(entry_id)
        logger.info('.. Sample.create(..)')
        sample, = Sample.create(samples_defaults)

        foreign_language = entry.report_language.code
        if (hasattr(self.start, 'sample_client_description_lang') and
                getattr(self.start, 'sample_client_description_lang')):
            with Transaction().set_context(language=foreign_language):
                sample_lang = Sample(sample.id)
                sample_lang.sample_client_description = (
                    self.start.sample_client_description_lang)
                sample_lang.save()
        if (hasattr(self.start, 'obj_description_manual_lang') and
                getattr(self.start, 'obj_description_manual_lang')):
            with Transaction().set_context(language=foreign_language):
                sample_lang = Sample(sample.id)
                sample_lang.obj_description_manual = (
                    self.start.obj_description_manual_lang)
                sample_lang.save()

        labels_list = self._get_labels_list(self.start.labels)
        if len(labels_list) > 1:
            logger.info('.. Sample.copy(..): %s' % (len(labels_list) - 1))
            for label in labels_list[1:]:
                if not label:
                    continue
                with Transaction().set_context(create_sample=True):
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
        shared = (hasattr(self.start, 'shared') and
            getattr(self.start, 'shared') or False)
        trace_report = (hasattr(self.start, 'trace_report') and
            getattr(self.start, 'trace_report') or False)
        report_comments = (hasattr(self.start, 'report_comments') and
            getattr(self.start, 'report_comments') or None)
        comments = (hasattr(self.start, 'comments') and
            getattr(self.start, 'comments') or None)
        attributes = (hasattr(self.start, 'attributes') and
            getattr(self.start, 'attributes') or None)

        # services data
        services_defaults = []
        if hasattr(self.start, 'services'):
            for service in self.start.services:
                estimated_waiting_laboratory = (
                    hasattr(service, 'estimated_waiting_laboratory') and
                    getattr(service, 'estimated_waiting_laboratory') or None)
                estimated_waiting_report = (
                    hasattr(service, 'estimated_waiting_report') and
                    getattr(service, 'estimated_waiting_report') or None)
                explode_analysis = (hasattr(service, 'explode_analysis') and
                    getattr(service, 'explode_analysis') or False)
                if (explode_analysis and
                        service.analysis.type in ('set', 'group')):
                    for included_analysis in self._get_included_analysis(
                            service.analysis):
                        services_defaults.append({
                            'analysis': included_analysis['analysis'],
                            'laboratory': included_analysis['laboratory'],
                            'method': included_analysis['method'],
                            'device': included_analysis['device'],
                            'urgent': service.urgent,
                            'priority': service.priority,
                            'estimated_waiting_laboratory': (
                                estimated_waiting_laboratory),
                            'estimated_waiting_report': (
                                estimated_waiting_report),
                            'laboratory_date': service.laboratory_date,
                            'report_date': service.report_date,
                            'divide': service.divide,
                            })
                else:
                    services_defaults.append({
                        'analysis': service.analysis.id,
                        'laboratory': (service.laboratory.id
                            if service.laboratory else None),
                        'method': (service.method.id if service.method
                            else None),
                        'device': (service.device.id if service.device
                            else None),
                        'urgent': service.urgent,
                        'priority': service.priority,
                        'estimated_waiting_laboratory': (
                            estimated_waiting_laboratory),
                        'estimated_waiting_report': (
                            estimated_waiting_report),
                        'laboratory_date': service.laboratory_date,
                        'report_date': service.report_date,
                        'divide': service.divide,
                        })

        # samples data
        samples_defaults = []
        labels_list = self._get_labels_list(self.start.labels)
        for label in labels_list[:1]:
            # fraction data
            fraction_defaults = {
                'type': self.start.fraction_type.id,
                'storage_location': self.start.storage_location.id,
                'storage_time': self.start.storage_time,
                'packages_quantity': self.start.packages_quantity,
                'shared': shared,
                'package_type': self.start.package_type.id,
                'fraction_state': self.start.fraction_state.id,
                }
            if services_defaults:
                fraction_defaults['services'] = [('create', services_defaults)]

            sample_defaults = {
                'entry': entry_id,
                'party': self.start.party.id,
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
                'restricted_entry': restricted_entry,
                'zone': zone_id,
                'trace_report': trace_report,
                'report_comments': report_comments,
                'comments': comments,
                'variety': variety_id,
                'label': label,
                'fractions': [('create', [fraction_defaults])],
                'attributes': attributes,
                }

            samples_defaults.append(sample_defaults)

        return samples_defaults

    def _get_included_analysis(self, analysis):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Typification = pool.get('lims.typification')

        childs = []
        if analysis.included_analysis:
            for included in analysis.included_analysis:
                if included.included_analysis.type == 'analysis':

                    laboratory_id = None
                    cursor.execute('SELECT laboratory '
                        'FROM "' + Typification._table + '" '
                        'WHERE product_type = %s '
                            'AND matrix = %s '
                            'AND analysis = %s '
                            'AND valid IS TRUE '
                            'AND by_default IS TRUE '
                            'AND laboratory IS NOT NULL',
                        (self.start.product_type.id,
                            self.start.matrix.id,
                            included.included_analysis.id))
                    res = cursor.fetchone()
                    if res:
                        laboratory_id = res[0]
                    if not laboratory_id:
                        for l in included.included_analysis.laboratories:
                            if l.by_default is True:
                                laboratory_id = l.laboratory.id

                    method_id = (included.method.id
                        if included.method else None)
                    if not method_id:
                        cursor.execute('SELECT method '
                            'FROM "' + Typification._table + '" '
                            'WHERE product_type = %s '
                                'AND matrix = %s '
                                'AND analysis = %s '
                                'AND valid IS TRUE '
                                'AND by_default IS TRUE',
                            (self.start.product_type.id,
                                self.start.matrix.id,
                                included.included_analysis.id))
                        res = cursor.fetchone()
                        if res:
                            method_id = res[0]

                    device_id = None
                    if included.included_analysis.devices:
                        for d in included.included_analysis.devices:
                            if (d.laboratory.id == laboratory_id and
                                    d.by_default is True):
                                device_id = d.device.id

                    childs.append({
                        'analysis': included.included_analysis.id,
                        'laboratory': laboratory_id,
                        'method': method_id,
                        'device': device_id,
                        })
                childs.extend(self._get_included_analysis(
                    included.included_analysis))
        return childs

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
    def get_context(cls, records, header, data):
        pool = Pool()
        Fraction = pool.get('lims.fraction')
        NotebookLine = pool.get('lims.notebook.line')

        report_context = super().get_context(records, header, data)

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

            # Check repetitions
            oks, to_check = [], []
            for line in notebook_lines:
                key = (line.analysis.id, line.method.id)
                if not line.accepted:
                    to_check.append(key)
                else:
                    oks.append(key)

            to_check = list(set(to_check) - set(oks))
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

        report_context['records'] = ordered_objects
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
        ResultsLine = pool.get('lims.results_report.version.detail.line')
        ResultsSample = pool.get('lims.results_report.version.detail.sample')
        ResultsDetail = pool.get('lims.results_report.version.detail')
        ResultsVersion = pool.get('lims.results_report.version')

        cursor.execute('SELECT rvdl.id '
            'FROM "' + ResultsLine._table + '" rvdl '
                'INNER JOIN "' + ResultsSample._table + '" rvds '
                'ON rvds.id = rvdl.detail_sample '
                'INNER JOIN "' + ResultsDetail._table + '" rvd '
                'ON rvd.id = rvds.version_detail '
                'INNER JOIN "' + ResultsVersion._table + '" rv '
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
    def get_context(cls, records, header, data):
        pool = Pool()
        Fraction = pool.get('lims.fraction')

        report_context = super().get_context(records, header, data)

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

        report_context['records'] = ordered_objects
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


class Referral(ModelSQL, ModelView):
    'Referral of Services'
    __name__ = 'lims.referral'
    _rec_name = 'number'

    _states = {'readonly': Eval('state') != 'draft'}
    _depends = ['state']

    number = fields.Char('Number', select=True, readonly=True)
    date = fields.Date('Date', required=True,
        states=_states, depends=_depends)
    sent_date = fields.Date('Sent date', readonly=True)
    laboratory = fields.Many2One('party.party', 'Destination Laboratory',
        required=True, states=_states, depends=_depends)
    carrier = fields.Many2One('carrier', 'Carrier',
        states=_states, depends=_depends)
    comments = fields.Text('Comments', states=_states, depends=_depends)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('done', 'Done'),
        ], 'State', required=True, readonly=True)
    services = fields.One2Many('lims.entry.detail.analysis',
        'referral', 'Services',
        states=_states, depends=_depends,
        add_remove=[
            ('state', '=', 'unplanned'),
            ('referral', '=', None),
            ])

    del _states, _depends

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order.insert(0, ('number', 'DESC'))
        cls._buttons.update({
            'send': {
                'invisible': Eval('state') != 'draft',
                'depends': ['state'],
                },
            })

    @staticmethod
    def default_date():
        Date = Pool().get('ir.date')
        return Date.today()

    @staticmethod
    def default_state():
        return 'draft'

    def get_rec_name(self, name):
        return self.laboratory.name

    @classmethod
    def search_rec_name(cls, name, clause):
        return [('laboratory',) + tuple(clause[1:])]

    @fields.depends('laboratory')
    def on_change_laboratory(self):
        if self.laboratory and self.laboratory.carrier:
            self.carrier = self.laboratory.carrier

    @classmethod
    def create(cls, vlist):
        pool = Pool()
        Config = pool.get('lims.configuration')

        config_ = Config(1)
        vlist = [x.copy() for x in vlist]
        for values in vlist:
            values['number'] = config_.referral_sequence.get()
        return super().create(vlist)

    @classmethod
    @ModelView.button
    def send(cls, referrals):
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        Date = pool.get('ir.date')

        for referral in referrals:
            details = [s for s in referral.services]
            lines = NotebookLine.search([
                ('analysis_detail', 'in', details),
                ('end_date', '=', None),
                ])
            NotebookLine.write(lines, {'start_date': referral.date})
            EntryDetailAnalysis.write(details, {'state': 'referred'})

        cls.write(referrals, {'state': 'sent', 'sent_date': Date.today()})
        cls.send_email_laboratory(referrals)

    @classmethod
    def send_email_laboratory(cls, referrals):
        from_addr = tconfig.get('email', 'from')
        if not from_addr:
            logger.error("Missing configuration to send emails")
            return

        for referral in referrals:
            to_addrs = referral._get_mail_recipients()
            if not to_addrs:
                logger.error("Missing address for '%s' to send email",
                    referral.laboratory.rec_name)
                continue

            subject, body = referral._get_mail_subject_body()
            attachment_data = referral._get_mail_attachment()
            msg = cls.create_msg(from_addr, to_addrs, subject,
                body, attachment_data)
            cls.send_msg(from_addr, to_addrs, msg, referral.number)

    def _get_mail_recipients(self):
        address = self.laboratory.address_get('delivery')
        if address:
            return [address.email]
        return []

    def _get_mail_subject_body(self):
        pool = Pool()
        Config = pool.get('lims.configuration')
        Lang = pool.get('ir.lang')

        config_ = Config(1)
        lang = Lang.get()

        with Transaction().set_context(language=lang.code):
            subject = str('%s %s' % (config_.mail_referral_subject,
                    self.number)).strip()
            body = str(config_.mail_referral_body)

        return subject, body

    def _get_mail_attachment(self):
        ReferralReport = Pool().get('lims.referral.report', type='report')

        result = ReferralReport.execute([self.id], {})
        report_format, report_cache = result[:2]

        data = {
            'content': report_cache,
            'format': report_format,
            'mimetype': (report_format == 'pdf' and 'pdf' or
                'vnd.oasis.opendocument.text'),
            'filename': '%s.%s' % (str(self.number), str(report_format)),
            'name': str(self.number),
            }
        return data

    @staticmethod
    def create_msg(from_addr, to_addrs, subject, body, attachment_data):
        if not (from_addr and to_addrs):
            return None

        msg = MIMEMultipart('mixed')
        msg['From'] = from_addr
        msg['To'] = ', '.join(to_addrs)
        msg['Subject'] = subject

        msg_body = MIMEText('text', 'plain')
        msg_body.set_payload(body.encode('UTF-8'), 'UTF-8')
        msg.attach(msg_body)

        attachment = MIMEBase('application', 'octet-stream')
        attachment.set_payload(attachment_data['content'])
        encoders.encode_base64(attachment)
        attachment.add_header('Content-Disposition', 'attachment',
            filename=attachment_data['filename'])
        msg.attach(attachment)
        return msg

    @staticmethod
    def send_msg(from_addr, to_addrs, msg, referral_number):
        to_addrs = list(set(to_addrs))
        success = False
        try:
            server = get_smtp_server()
            server.sendmail(from_addr, to_addrs, msg.as_string())
            server.quit()
            success = True
        except Exception:
            logger.error(
                "Unable to deliver mail for referral '%s'" % (referral_number))
        return success


class ReferralReport(Report):
    'Referral of Services Report'
    __name__ = 'lims.referral.report'


class ReferServiceStart(ModelView):
    'Refer Service'
    __name__ = 'lims.referral.service.start'

    date = fields.Date('Date', required=True)
    laboratory = fields.Many2One('party.party', 'Destination Laboratory',
        required=True)
    services = fields.Many2Many('lims.entry.detail.analysis',
        None, None, 'Services', readonly=True)
    referral = fields.Many2One('lims.referral', 'Referral')


class ReferService(Wizard):
    'Refer Service'
    __name__ = 'lims.referral.service'

    start = StateView('lims.referral.service.start',
        'lims.referral_service_start_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Confirm', 'confirm', 'tryton-ok', default=True),
            ])
    confirm = StateTransition()
    open_ = StateAction('lims.act_referral_list')

    def default_start(self, fields):
        Date = Pool().get('ir.date')
        default = {}
        default['date'] = Date.today()
        default['laboratory'] = None
        default['services'] = self._get_services()
        return default

    def _get_services(self):
        EntryDetailAnalysis = Pool().get('lims.entry.detail.analysis')
        details = EntryDetailAnalysis.search([
            ('id', 'in', Transaction().context['active_ids']),
            ('referable', '=', True),
            ('referral', '=', None),
            ('state', '=', 'unplanned'),
            ])
        return [d.id for d in details]

    def transition_confirm(self):
        EntryDetailAnalysis = Pool().get('lims.entry.detail.analysis')

        if not self.start.services:
            return 'end'

        referral = self._get_referral()

        EntryDetailAnalysis.write([s for s in self.start.services], {
            'referral': referral.id,
            })
        self.start.referral = referral
        return 'open_'

    def _get_referral(self):
        Referral = Pool().get('lims.referral')

        referrals = Referral.search([
            ('laboratory', '=', self.start.laboratory.id),
            ('date', '=', self.start.date),
            ('state', '=', 'draft'),
            ], limit=1)
        if referrals:
            return referrals[0]

        referrals = Referral.create([{
            'laboratory': self.start.laboratory.id,
            'carrier': (self.start.laboratory.carrier and
                self.start.laboratory.carrier.id or None),
            'date': self.start.date,
            'state': 'draft',
            }])
        return referrals[0]

    def do_open_(self, action):
        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', '=', self.start.referral.id),
            ])
        return action, {}

    def transition_open_(self):
        return 'end'
