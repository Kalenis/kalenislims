# -*- coding: utf-8 -*-
# This file is part of lims module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from datetime import datetime
from dateutil import rrule
from sql import Null

from trytond.model import ModelSingleton, ModelView, ModelSQL, fields
from trytond.pyson import Eval
from trytond.transaction import Transaction
from trytond.pool import Pool, PoolMeta
from trytond.modules.company.model import (
    CompanyMultiValueMixin, CompanyValueMixin)
from trytond.exceptions import UserError
from trytond.i18n import gettext

__all__ = ['NotebookView', 'NotebookViewColumn', 'Printer', 'User',
    'UserLaboratory', 'Configuration', 'ConfigurationLaboratory',
    'ConfigurationSequence', 'ConfigurationProductCategory', 'LabWorkYear',
    'LabWorkYearSequence', 'LabWorkYearHoliday', 'Cron', 'ModelDoc', 'Model']
sequence_names = [
    'entry_sequence', 'sample_sequence', 'service_sequence',
    'results_report_sequence']


def get_print_date():
    Company = Pool().get('company.company')

    date = datetime.now()
    company_id = Transaction().context.get('company')
    if company_id:
        date = Company(company_id).convert_timezone_datetime(date)
    return date


class NotebookView(ModelSQL, ModelView):
    'Laboratory Notebook View'
    __name__ = 'lims.notebook.view'

    name = fields.Char('Name', required=True)
    columns = fields.One2Many('lims.notebook.view.column', 'view', 'Columns',
        required=True)


class NotebookViewColumn(ModelSQL, ModelView):
    'Laboratory Notebook View Column'
    __name__ = 'lims.notebook.view.column'

    view = fields.Many2One('lims.notebook.view', 'View', required=True,
        ondelete='CASCADE', select=True)
    field = fields.Many2One('ir.model.field', 'Field', required=True,
        domain=[('model.model', '=', 'lims.notebook.line')])
    sequence = fields.Integer('Sequence', required=True, select=True)

    @classmethod
    def __setup__(cls):
        super(NotebookViewColumn, cls).__setup__()
        cls._order.insert(0, ('sequence', 'ASC'))


class Printer(ModelSQL, ModelView):
    'Printer'
    __name__ = 'lims.printer'

    name = fields.Char('Name', required=True)


class User(metaclass=PoolMeta):
    __name__ = 'res.user'

    notebook_view = fields.Many2One('lims.notebook.view', 'Notebook view')
    laboratories = fields.Many2Many('lims.user-laboratory',
        'user', 'laboratory', 'Laboratories')
    laboratory = fields.Many2One('lims.laboratory', 'Main Laboratory',
        domain=[('id', 'in', Eval('laboratories'))], depends=['laboratories'])
    printer = fields.Many2One('lims.printer', 'Printer')
    departments = fields.One2Many('user.department', 'user', 'Departments')

    @classmethod
    def __setup__(cls):
        super(User, cls).__setup__()
        cls._context_fields.insert(0, 'laboratory')
        cls._context_fields.insert(0, 'laboratories')

    @classmethod
    def __register__(cls, module_name):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Role = pool.get('res.role')
        RoleGroup = pool.get('res.role-res.group')
        UserRole = pool.get('res.user.role')

        super(User, cls).__register__(module_name)

        user_sql_table = cls.__table__()
        user_table = cls.__table_handler__(module_name)
        if user_table.column_exist('role'):
            role = Role.__table__()
            role_group = RoleGroup.__table__()
            user_role = UserRole.__table__()

            cursor.execute('SELECT id, name '
                'FROM lims_user_role')
            for role_id, role_name in cursor.fetchall():
                cursor.execute(*role.insert(
                    [role.id, role.name],
                    [[role_id, role_name]]))

                cursor.execute('SELECT "group" '
                    'FROM "lims_user_role-res_group" '
                    'WHERE role = %s', (role_id, ))
                for (group_id, ) in cursor.fetchall():
                    cursor.execute(*role_group.insert(
                        [role_group.role, role_group.group],
                        [[role_id, group_id]]))

            cursor.execute(*user_sql_table.select(
                user_sql_table.id, user_sql_table.role,
                where=user_sql_table.role != Null))
            for user_id, role_id in cursor.fetchall():
                cursor.execute(*user_role.insert(
                    [user_role.user, user_role.role],
                    [[user_id, role_id]]))

            user_table.drop_column('role')

    def get_status_bar(self, name):
        status = self.name
        if self.company:
            status = '%s - %s' % (self.company.rec_name, status)
        if self.laboratory:
            status += ' [%s]' % self.laboratory.rec_name
        return status


class UserLaboratory(ModelSQL):
    'User - Laboratory'
    __name__ = 'lims.user-laboratory'

    user = fields.Many2One('res.user', 'User',
        ondelete='CASCADE', select=True, required=True)
    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        ondelete='CASCADE', select=True, required=True)


class Configuration(ModelSingleton, ModelSQL, ModelView,
        CompanyMultiValueMixin):
    'Configuration'
    __name__ = 'lims.configuration'

    fraction_product = fields.Many2One('product.product', 'Fraction product',
        states={'required': True})
    mail_ack_subject = fields.Char('Email subject of Acknowledgment of Samples'
        ' Receipt',
        help="In the text will be added suffix with the entry report number")
    mail_ack_body = fields.Text('Email body of Acknowledgment of Samples'
        ' Receipt')
    microbiology_laboratories = fields.Many2Many(
        'lims.configuration-laboratory', 'configuration',
        'laboratory', 'Microbiology Laboratories')
    default_notebook_view = fields.Many2One('lims.notebook.view',
        'Default Notebook view', required=True)
    brix_digits = fields.Integer('Brix digits')
    density_digits = fields.Integer('Density digits')
    soluble_solids_digits = fields.Integer('Soluble solids digits')
    rm_start_uom = fields.Many2One('product.uom', 'RM Start UoM',
        domain=[('category.lims_only_available', '=', True)])
    email_qa = fields.Char('QA Email')
    analysis_product_category = fields.Many2One('product.category',
        'Analysis Product Category', states={'required': True})
    entry_confirm_background = fields.Boolean(
        'Confirm Entries in Background')
    planification_sequence = fields.MultiValue(fields.Many2One(
        'ir.sequence', 'Planification Sequence', required=True,
        domain=[
            ('company', 'in',
                [Eval('context', {}).get('company', -1), None]),
            ('code', '=', 'lims.planification'),
            ]))
    mcl_fraction_type = fields.Many2One('lims.fraction.type',
        'MCL fraction type')
    con_fraction_type = fields.Many2One('lims.fraction.type',
        'Control fraction type')
    bmz_fraction_type = fields.Many2One('lims.fraction.type',
        'BMZ fraction type')
    rm_fraction_type = fields.Many2One('lims.fraction.type',
        'RM fraction type')
    bre_fraction_type = fields.Many2One('lims.fraction.type',
        'BRE fraction type')
    mrt_fraction_type = fields.Many2One('lims.fraction.type',
        'MRT fraction type')
    coi_fraction_type = fields.Many2One('lims.fraction.type',
        'COI fraction type')
    mrc_fraction_type = fields.Many2One('lims.fraction.type',
        'MRC fraction type')
    sla_fraction_type = fields.Many2One('lims.fraction.type',
        'SLA fraction type')
    itc_fraction_type = fields.Many2One('lims.fraction.type',
        'ITC fraction type')
    itl_fraction_type = fields.Many2One('lims.fraction.type',
        'ITL fraction type')
    reagents = fields.Many2Many('lims.configuration-product.category',
        'configuration', 'category', 'Reagents')
    planification_process_background = fields.Boolean(
        'Process Planifications in Background')
    invoice_party_relation_type = fields.Many2One('party.relation.type',
        'Invoice Party Relation Type')
    samples_in_progress = fields.Selection([
        ('result', 'With results'),
        ('accepted', 'With accepted results'),
        ], 'Samples in progress',
        help='Samples allowed for preliminary reports')
    zone_required = fields.Boolean('Zone required')

    @staticmethod
    def default_brix_digits():
        return 2

    @staticmethod
    def default_density_digits():
        return 2

    @staticmethod
    def default_soluble_solids_digits():
        return 2

    @staticmethod
    def default_entry_confirm_background():
        return False

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field == 'planification_sequence':
            return pool.get('lims.configuration.sequence')
        return super(Configuration, cls).multivalue_model(field)

    @classmethod
    def default_planification_sequence(cls, **pattern):
        return cls.multivalue_model(
            'planification_sequence').default_planification_sequence()

    @staticmethod
    def default_planification_process_background():
        return False

    @staticmethod
    def default_samples_in_progress():
        return 'result'

    @staticmethod
    def default_zone_required():
        return True

    def get_reagents(self):
        res = []
        if self.reagents:
            for r in self.reagents:
                res.append(r.id)
                res.extend(self.get_reagent_childs(r.id))
        return res

    def get_reagent_childs(self, reagent_id):
        Category = Pool().get('product.category')

        res = []
        categories = Category.search([
            ('parent', '=', reagent_id),
            ])
        if categories:
            for c in categories:
                res.append(c.id)
                res.extend(self.get_reagent_childs(c.id))
        return res


class ConfigurationLaboratory(ModelSQL):
    'Configuration - Laboratory'
    __name__ = 'lims.configuration-laboratory'

    configuration = fields.Many2One('lims.configuration', 'Configuration',
        ondelete='CASCADE', select=True, required=True)
    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        ondelete='CASCADE', select=True, required=True)


class ConfigurationSequence(ModelSQL, CompanyValueMixin):
    'Configuration Sequence'
    __name__ = 'lims.configuration.sequence'

    planification_sequence = fields.Many2One('ir.sequence',
        'Planification Sequence', depends=['company'], domain=[
            ('company', 'in', [Eval('company', -1), None]),
            ('code', '=', 'lims.planification'),
            ])

    @classmethod
    def default_planification_sequence(cls):
        pool = Pool()
        ModelData = pool.get('ir.model.data')
        try:
            return ModelData.get_id('lims.planification', 'seq_planification')
        except KeyError:
            return None


class ConfigurationProductCategory(ModelSQL):
    'Configuration - Product Category'
    __name__ = 'lims.configuration-product.category'

    configuration = fields.Many2One('lims.configuration', 'Configuration',
        ondelete='CASCADE', select=True, required=True)
    category = fields.Many2One('product.category', 'Category',
        ondelete='CASCADE', select=True, required=True)


class LabWorkYear(ModelSQL, ModelView, CompanyMultiValueMixin):
    'Work Year'
    __name__ = 'lims.lab.workyear'
    _rec_name = 'code'

    code = fields.Char('Code', required=True)
    start_date = fields.Date('Start date', required=True)
    end_date = fields.Date('End date', required=True)
    entry_sequence = fields.MultiValue(fields.Many2One(
        'ir.sequence', 'Entry Sequence', required=True,
        domain=[
            ('company', 'in',
                [Eval('context', {}).get('company', -1), None]),
            ('code', '=', 'lims.entry'),
            ]))
    sample_sequence = fields.MultiValue(fields.Many2One(
        'ir.sequence', 'Sample Sequence', required=True,
        domain=[
            ('company', 'in',
                [Eval('context', {}).get('company', -1), None]),
            ('code', '=', 'lims.sample'),
            ]))
    service_sequence = fields.MultiValue(fields.Many2One(
        'ir.sequence', 'Service Sequence', required=True,
        domain=[
            ('company', 'in',
                [Eval('context', {}).get('company', -1), None]),
            ('code', '=', 'lims.service'),
            ]))
    results_report_sequence = fields.MultiValue(fields.Many2One(
        'ir.sequence', 'Results Report Sequence', required=True,
        domain=[
            ('company', 'in',
                [Eval('context', {}).get('company', -1), None]),
            ('code', '=', 'lims.results_report'),
            ]))
    sequences = fields.One2Many('lims.lab.workyear.sequence',
        'workyear', 'Sequences')
    default_entry_control = fields.Many2One('lims.entry',
        'Default entry control')
    workdays = fields.MultiSelection([
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
        ], 'Working days', sort=False)
    holidays = fields.One2Many('lims.lab.workyear.holiday', 'workyear',
        'Holidays')

    @classmethod
    def __setup__(cls):
        super(LabWorkYear, cls).__setup__()
        cls._order.insert(0, ('start_date', 'ASC'))

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field in sequence_names:
            return pool.get('lims.lab.workyear.sequence')
        return super(LabWorkYear, cls).multivalue_model(field)

    @classmethod
    def default_entry_sequence(cls, **pattern):
        return cls.multivalue_model(
            'entry_sequence').default_entry_sequence()

    @classmethod
    def default_sample_sequence(cls, **pattern):
        return cls.multivalue_model(
            'sample_sequence').default_sample_sequence()

    @classmethod
    def default_service_sequence(cls, **pattern):
        return cls.multivalue_model(
            'service_sequence').default_service_sequence()

    @staticmethod
    def default_workdays():
        return (0, 1, 2, 3, 4)

    @classmethod
    def validate(cls, years):
        super(LabWorkYear, cls).validate(years)
        for year in years:
            year.check_dates()

    def check_dates(self):
        cursor = Transaction().connection.cursor()
        table = self.__table__()
        cursor.execute(*table.select(table.id,
                where=(((table.start_date <= self.start_date) &
                        (table.end_date >= self.start_date)) |
                    ((table.start_date <= self.end_date) &
                        (table.end_date >= self.end_date)) |
                    ((table.start_date >= self.start_date) &
                        (table.end_date <= self.end_date))) &
                (table.id != self.id)))
        second_id = cursor.fetchone()
        if second_id:
            second = self.__class__(second_id[0])
            raise UserError(gettext('lims.msg_workyear_overlaps',
                    first=self.rec_name,
                    second=second.rec_name,
                    ))

    @classmethod
    def find(cls, date=None, exception=True):
        pool = Pool()
        Lang = pool.get('ir.lang')
        Date = pool.get('ir.date')

        if not date:
            date = Date.today()
        workyears = cls.search([
            ('start_date', '<=', date),
            ('end_date', '>=', date),
            ], order=[('start_date', 'DESC')], limit=1)
        if not workyears:
            if exception:
                lang = Lang.get()
                formatted = lang.strftime(date)
                raise UserError(gettext(
                    'lims.msg_no_workyear_date', date=formatted))
            else:
                return None
        return workyears[0].id

    def get_sequence(self, type):
        sequence = getattr(self, type + '_sequence')
        if sequence:
            return sequence

    def get_target_date(self, start_date, days):
        total_days = days + 1  # plus 1 because start_date is included
        ruleset = rrule.rruleset()

        min_time = datetime.min.time()
        for h in self.holidays:
            ruleset.exdate(datetime.combine(h.date, min_time))

        count = total_days
        ruleset.rrule(rrule.rrule(rrule.DAILY, byweekday=self.workdays,
            dtstart=start_date, count=count))
        while(ruleset.count() < total_days):  # because holidays subtract days
            count += 1
            ruleset.rrule(rrule.rrule(rrule.DAILY, byweekday=self.workdays,
                dtstart=start_date, count=count))

        return ruleset[-1].date()


class LabWorkYearSequence(ModelSQL, CompanyValueMixin):
    'Work Year Sequence'
    __name__ = 'lims.lab.workyear.sequence'

    workyear = fields.Many2One('lims.lab.workyear', 'Work Year',
        ondelete='CASCADE', select=True)
    entry_sequence = fields.Many2One('ir.sequence',
        'Entry Sequence', depends=['company'], domain=[
            ('company', 'in', [Eval('company', -1), None]),
            ('code', '=', 'lims.entry'),
            ])
    sample_sequence = fields.Many2One('ir.sequence',
        'Sample Sequence', depends=['company'], domain=[
            ('company', 'in', [Eval('company', -1), None]),
            ('code', '=', 'lims.sample'),
            ])
    service_sequence = fields.Many2One('ir.sequence',
        'Service Sequence', depends=['company'], domain=[
            ('company', 'in', [Eval('company', -1), None]),
            ('code', '=', 'lims.service'),
            ])
    results_report_sequence = fields.Many2One('ir.sequence',
        'Results Report Sequence', depends=['company'], domain=[
            ('company', 'in', [Eval('company', -1), None]),
            ('code', '=', 'lims.results_report'),
            ])

    @classmethod
    def default_entry_sequence(cls):
        pool = Pool()
        ModelData = pool.get('ir.model.data')
        try:
            return ModelData.get_id('lims.entry', 'seq_entry')
        except KeyError:
            return None

    @classmethod
    def default_sample_sequence(cls):
        pool = Pool()
        ModelData = pool.get('ir.model.data')
        try:
            return ModelData.get_id('lims.sample', 'seq_sample')
        except KeyError:
            return None

    @classmethod
    def default_service_sequence(cls):
        pool = Pool()
        ModelData = pool.get('ir.model.data')
        try:
            return ModelData.get_id('lims.service', 'seq_service')
        except KeyError:
            return None


class LabWorkYearHoliday(ModelSQL, ModelView):
    'Work Year Holiday'
    __name__ = 'lims.lab.workyear.holiday'

    workyear = fields.Many2One('lims.lab.workyear', 'Work Year',
        required=True, ondelete='CASCADE', select=True)
    name = fields.Char('Name', required=True)
    date = fields.Date('Date', required=True)

    @classmethod
    def __setup__(cls):
        super(LabWorkYearHoliday, cls).__setup__()
        cls._order.insert(0, ('date', 'ASC'))


class Cron(metaclass=PoolMeta):
    __name__ = 'ir.cron'

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.method.selection.extend([
                ('lims.entry|cron_acknowledgment_of_receipt',
                    "Lims Acknowledgment of Receipt (Samples)"),
                ('lims.fraction|confirm_waiting_fractions',
                    "Lims Confirm Waiting Entries"),
                ('lims.planification|process_waiting_planifications',
                    "Lims Process Waiting Planification"),
                ('lims.trend.chart|clean',
                    "Lims Clean Inactive Trend Charts"),
                ])


class ModelDoc(ModelSQL, ModelView):
    'Model Doc'
    __name__ = 'ir.model.doc'

    model = fields.Many2One('ir.model', 'Model')
    doc = fields.Text('Documentation', translate=True)
    kind = fields.Selection([
        ('base', 'Base'),
        ('extended', 'Extended'),
        ], 'Kind')
    name = fields.Function(fields.Char('Name'), 'get_name')

    def get_name(self, name):
        return self.model.name


class Model(metaclass=PoolMeta):
    __name__ = 'ir.model'

    docs = fields.One2Many('ir.model.doc', 'model', 'Docs')
