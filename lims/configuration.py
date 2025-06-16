# -*- coding: utf-8 -*-
# This file is part of lims module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from datetime import datetime, timedelta
from dateutil import rrule
from sql import Null

from trytond.model import ModelSingleton, ModelView, ModelSQL, fields
from trytond.pyson import Eval, Id
from trytond.transaction import Transaction
from trytond.pool import Pool, PoolMeta
from trytond.modules.company.model import (
    CompanyMultiValueMixin, CompanyValueMixin)
from trytond.exceptions import UserError
from trytond.i18n import gettext

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
        super().__setup__()
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
    signature_image = fields.Binary('Signature')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._context_fields.insert(0, 'laboratory')
        cls._context_fields.insert(0, 'laboratories')

    @classmethod
    def __register__(cls, module_name):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Role = pool.get('res.role')
        RoleGroup = pool.get('res.role-res.group')
        UserRole = pool.get('res.user.role')

        super().__register__(module_name)

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

    @classmethod
    def write(cls, *args):
        super().write(*args)
        actions = iter(args)
        for users, vals in zip(actions, actions):
            if 'active' in vals:
                cls.sync_active_field(users, vals['active'])

    @classmethod
    def sync_active_field(cls, users, active_value):
        pool = Pool()
        Party = pool.get('party.party')
        Employee = pool.get('company.employee')
        Professional = pool.get('lims.laboratory.professional')

        if not users:
            return

        user_ids = [user.id for user in users]
        parties = Party.search([
            ('lims_user', 'in', user_ids),
            ('active', 'in', [True, False]),
            ])
        if not parties:
            return

        Party.write(parties, {'active': active_value})
        party_ids = [party.id for party in parties]

        employees = Employee.search([
            ('party', 'in', party_ids),
            ('active', 'in', [True, False]),
            ])
        if employees:
            Employee.write(employees, {'active': active_value})

        professionals = Professional.search([
            ('party', 'in', party_ids),
            ('active', 'in', [True, False]),
            ])
        if professionals:
            Professional.write(professionals, {'active': active_value})


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
    mail_ack_hide_recipients = fields.Boolean('Hide recipients')
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
            ('sequence_type', '=',
                Id('lims', 'seq_type_planification')),
            ('company', 'in',
                [Eval('context', {}).get('company', -1), None]),
            ]))
    referral_sequence = fields.MultiValue(fields.Many2One(
        'ir.sequence', 'Referral Sequence', required=True,
        domain=[
            ('sequence_type', '=',
                Id('lims', 'seq_type_referral')),
            ('company', 'in',
                [Eval('context', {}).get('company', -1), None]),
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
    invoice_party_relation_type = fields.Many2One('party.relation.type',
        'Invoice Party Relationship Type')
    samples_in_progress = fields.Selection([
        ('result', 'With results'),
        ('accepted', 'With accepted results'),
        ], 'Samples in progress',
        help='Samples allowed for preliminary reports')
    zone_required = fields.Boolean('Zone required')
    entry_default_contacts = fields.Selection([
        ('party', 'Party'),
        ('invoice_party', 'Invoice party'),
        ], 'Default Contacts in Entries',
        help='From which Party takes the contacts for the Entry')
    notebook_lines_acceptance = fields.Selection([
        ('none', 'Do not accept analyzes that have repetition'),
        ('last', 'Accept the last repetition of the analyzes'),
        ], 'Acceptance of notebook lines')
    notebook_lines_acceptance_method = fields.Boolean(
        'Allow to accept the same analysis with different methods')
    notebook_lines_repetition_report = fields.Boolean(
        'Always report repetitions')
    results_report_language = fields.Many2One('ir.lang',
        'Results Report Language', domain=[('translatable', '=', True)])
    mail_referral_subject = fields.Char('Email subject of Referral of Samples',
        help="A suffix with the referral number will be added to the text")
    mail_referral_body = fields.Text('Email body of Referral of Samples')
    sample_fast_copy = fields.Boolean('Fast Sample Creation (Experimental)')
    server_url = fields.Char('Kalenis Server URL')
    results_report_print_not_valid = fields.Boolean(
        'Allow reprinting any version of Result Reports')
    results_report_review_reason_print = fields.Boolean(
        'Print review reason on Result Reports')

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

    @staticmethod
    def default_mail_ack_hide_recipients():
        return True

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field in ['planification_sequence', 'referral_sequence']:
            return pool.get('lims.configuration.sequence')
        return super().multivalue_model(field)

    @classmethod
    def default_planification_sequence(cls, **pattern):
        return cls.multivalue_model(
            'planification_sequence').default_planification_sequence()

    @classmethod
    def default_referral_sequence(cls, **pattern):
        return cls.multivalue_model(
            'referral_sequence').default_referral_sequence()

    @staticmethod
    def default_samples_in_progress():
        return 'result'

    @staticmethod
    def default_zone_required():
        return True

    @staticmethod
    def default_entry_default_contacts():
        return 'party'

    @staticmethod
    def default_notebook_lines_acceptance():
        return 'none'

    @staticmethod
    def default_notebook_lines_acceptance_method():
        return False

    @staticmethod
    def default_notebook_lines_repetition_report():
        return False

    @staticmethod
    def default_results_report_language():
        Lang = Pool().get('ir.lang')
        langs = Lang.search([
            ('translatable', '=', True),
            ('code', '=', 'es'),
            ])
        return langs and langs[0].id or None

    @staticmethod
    def default_sample_fast_copy():
        return False

    @staticmethod
    def default_results_report_print_not_valid():
        return False

    @staticmethod
    def default_results_report_review_reason_print():
        return False

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
            ('sequence_type', '=',
                Id('lims', 'seq_type_planification')),
            ('company', 'in', [Eval('company', -1), None]),
            ])
    referral_sequence = fields.Many2One('ir.sequence',
        'Referral Sequence', depends=['company'], domain=[
            ('sequence_type', '=',
                Id('lims', 'seq_type_referral')),
            ('company', 'in', [Eval('company', -1), None]),
            ])

    @classmethod
    def default_planification_sequence(cls):
        pool = Pool()
        ModelData = pool.get('ir.model.data')
        try:
            return ModelData.get_id('lims.planification', 'seq_planification')
        except KeyError:
            return None

    @classmethod
    def default_referral_sequence(cls):
        pool = Pool()
        ModelData = pool.get('ir.model.data')
        try:
            return ModelData.get_id('lims.referral', 'seq_referral')
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
            ('sequence_type', '=',
                Id('lims', 'seq_type_entry')),
            ('company', 'in',
                [Eval('context', {}).get('company', -1), None]),
            ]))
    sample_sequence = fields.MultiValue(fields.Many2One(
        'ir.sequence', 'Sample Sequence', required=True,
        domain=[
            ('sequence_type', '=',
                Id('lims', 'seq_type_sample')),
            ('company', 'in',
                [Eval('context', {}).get('company', -1), None]),
            ]))
    service_sequence = fields.MultiValue(fields.Many2One(
        'ir.sequence', 'Service Sequence', required=True,
        domain=[
            ('sequence_type', '=',
                Id('lims', 'seq_type_service')),
            ('company', 'in',
                [Eval('context', {}).get('company', -1), None]),
            ]))
    results_report_sequence = fields.MultiValue(fields.Many2One(
        'ir.sequence', 'Results Report Sequence', required=True,
        domain=[
            ('sequence_type', '=',
                Id('lims', 'seq_type_results_report')),
            ('company', 'in',
                [Eval('context', {}).get('company', -1), None]),
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
    shifts = fields.Many2Many('lims.lab.workyear.shift', 'workyear', 'shift',
        'Work shifts')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order.insert(0, ('start_date', 'ASC'))

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field in sequence_names:
            return pool.get('lims.lab.workyear.sequence')
        return super().multivalue_model(field)

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
        super().validate(years)
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
    
    @classmethod
    def get_shift(cls, date_time=None):
        date_time = date_time if date_time else datetime.now()
        if not isinstance(date_time, datetime):
            raise UserError('A datetime is required to get a shift')
        workyear_id = cls.find(date_time.date())
        workyear = cls(workyear_id)
        if not workyear.shifts:
            return None
        
        pool = Pool()
        
        Company = pool.get('company.company')
        company_id = Transaction().context.get('company')
        if not company_id:
            raise UserError(gettext('lims.msg_shift_missing_company'))
        
        company = Company(company_id)
        time = company.convert_timezone_datetime(date_time).time()
        shifts = []

        def inRange(start, end, value):
            if end >= start:
                if value >= start and value <= end:
                    return True
            else:
                if value <= end or value >= start:
                    return True
                else:
                    return False

        for shift in workyear.shifts:
            if(inRange(shift.start_time, shift.end_time, time)):
                shifts.append(shift)
            
        if not shifts:
            return None
        
        # shifts overlap end-start: Select the starting shift
        if len(shifts) > 1:
            shifts = list(filter(lambda shift: shift.start_time == time, shifts))
            # If overlap is not on start-end times, 
            # raise an error cause the shift configuration is wrong
            if not shifts:
                raise UserError(gettext('lims.msg_overlapped_shifts'))
                
        
        return shifts[0]

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
            ('sequence_type', '=',
                Id('lims', 'seq_type_entry')),
            ('company', 'in', [Eval('company', -1), None]),
            ])
    sample_sequence = fields.Many2One('ir.sequence',
        'Sample Sequence', depends=['company'], domain=[
            ('sequence_type', '=',
                Id('lims', 'seq_type_sample')),
            ('company', 'in', [Eval('company', -1), None]),
            ])
    service_sequence = fields.Many2One('ir.sequence',
        'Service Sequence', depends=['company'], domain=[
            ('sequence_type', '=',
                Id('lims', 'seq_type_service')),
            ('company', 'in', [Eval('company', -1), None]),
            ])
    results_report_sequence = fields.Many2One('ir.sequence',
        'Results Report Sequence', depends=['company'], domain=[
            ('sequence_type', '=',
                Id('lims', 'seq_type_results_report')),
            ('company', 'in', [Eval('company', -1), None]),
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
        super().__setup__()
        cls._order.insert(0, ('date', 'ASC'))


class LabWorkYearShift(ModelSQL):
    'Work Year Shift'
    __name__ = 'lims.lab.workyear.shift'

    workyear = fields.Many2One('lims.lab.workyear', 'Work Year',
        required=True, ondelete='CASCADE', select=True)
    shift = fields.Many2One('lims.lab.workshift', 'Work Shift',
        required=True, ondelete='CASCADE', select=True)


class LabWorkShift(ModelSQL, ModelView):
    'Work Shift'
    __name__ = 'lims.lab.workshift'

    name = fields.Char('Name', required=True)
    start_time = fields.Time('Start Time')
    end_time = fields.Time('End Time')
    duration = fields.TimeDelta('Duration', states={'readonly': True})

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order.insert(0, ('start_time', 'ASC'))

    @fields.depends('start_time', 'end_time')
    def on_change_with_duration(self, name=None):
        start_time = self.start_time
        end_time = self.end_time
        if not start_time or not end_time:
            return None
        duration_seconds = (end_time.hour * 60 * 60)
        duration_seconds += (end_time.minute * 60)
        duration_seconds += end_time.second
        if start_time > end_time:
            duration_seconds += (24 * 60 * 60)  # Add 24Hs
        duration_seconds -= (start_time.hour * 60 * 60)
        duration_seconds -= (start_time.minute * 60)
        duration_seconds -= start_time.second
        return timedelta(seconds=duration_seconds)


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


class Sequence(metaclass=PoolMeta):
    __name__ = 'ir.sequence'

    @classmethod
    def _get_substitutions(cls, date):
        pool = Pool()
        Date = pool.get('ir.date')
        res = super(Sequence, cls)._get_substitutions(date)
        if not date:
            date = Date.today()
        res['year2'] = date.strftime('%y')
        return res


class About(ModelSingleton, ModelSQL, ModelView):
    'About'
    __name__ = 'lims.about'

    version = fields.Char('Version', states={'readonly': True})
    release_date = fields.Date('Release Date', states={'readonly': True})
