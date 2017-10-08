# -*- coding: utf-8 -*-
# This file is part of lims module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond import backend
from trytond.model import ModelSingleton, ModelView, ModelSQL, fields
from trytond.pyson import Eval
from trytond.transaction import Transaction
from trytond.pool import Pool, PoolMeta
from trytond.tools.multivalue import migrate_property
from trytond.modules.company.model import (
    CompanyMultiValueMixin, CompanyValueMixin)

__all__ = ['LimsLaboratory2', 'LimsNotebookView', 'LimsNotebookViewColumn',
    'LimsUserRole', 'LimsUserRoleGroup', 'LimsPrinter', 'User',
    'LimsUserLaboratory', 'LimsConfiguration', 'LimsConfigurationLaboratory',
    'LimsLabWorkYear', 'LimsLabWorkYearSequence']
sequence_names = [
    'entry_sequence', 'sample_sequence', 'service_sequence',
    'results_report_sequence']


class LimsLaboratory2(ModelSQL):
    'Laboratory'
    __name__ = 'lims.laboratory'


class LimsNotebookView(ModelSQL, ModelView):
    'Laboratory Notebook View'
    __name__ = 'lims.notebook.view'

    name = fields.Char('Name', required=True)
    columns = fields.One2Many('lims.notebook.view.column', 'view', 'Columns',
        required=True)


class LimsNotebookViewColumn(ModelSQL, ModelView):
    'Laboratory Notebook View Column'
    __name__ = 'lims.notebook.view.column'

    view = fields.Many2One('lims.notebook.view', 'View', required=True,
        ondelete='CASCADE', select=True)
    field = fields.Many2One('ir.model.field', 'Field', required=True,
        domain=[('model.model', '=', 'lims.notebook.line')])
    sequence = fields.Integer('Sequence', required=True, select=True)

    @classmethod
    def __setup__(cls):
        super(LimsNotebookViewColumn, cls).__setup__()
        cls._order.insert(0, ('sequence', 'ASC'))


class LimsUserRole(ModelSQL, ModelView):
    'User Role'
    __name__ = 'lims.user.role'

    name = fields.Char('Name', required=True)
    groups = fields.Many2Many('lims.user.role-res.group',
        'role', 'group', 'Groups')


class LimsUserRoleGroup(ModelSQL):
    'User Role - Group'
    __name__ = 'lims.user.role-res.group'

    role = fields.Many2One('lims.user.role', 'Role',
        ondelete='CASCADE', select=True, required=True)
    group = fields.Many2One('res.group', 'Group',
        ondelete='CASCADE', select=True, required=True)

    @classmethod
    def create(cls, vlist):
        role_groups = super(LimsUserRoleGroup, cls).create(vlist)
        cls._create_user_groups(role_groups)
        return role_groups

    @classmethod
    def _create_user_groups(cls, role_groups):
        pool = Pool()
        User = pool.get('res.user')
        UserGroup = pool.get('res.user-res.group')

        for role_group in role_groups:
            users = User.search([
                ('role', '=', role_group.role),
                ])
            for user in users:
                if not UserGroup.search([
                        ('user', '=', user),
                        ('group', '=', role_group.group),
                        ]):
                    UserGroup.create([{
                        'user': user,
                        'group': role_group.group,
                        }])

    @classmethod
    def delete(cls, role_groups):
        cls._delete_user_groups(role_groups)
        super(LimsUserRoleGroup, cls).delete(role_groups)

    @classmethod
    def _delete_user_groups(cls, role_groups):
        pool = Pool()
        User = pool.get('res.user')
        UserGroup = pool.get('res.user-res.group')

        for role_group in role_groups:
            users = User.search([
                ('role', '=', role_group.role),
                ])
            if users:
                user_groups = UserGroup.search([
                    ('user', 'in', users),
                    ('group', '=', role_group.group),
                    ])
                if user_groups:
                    UserGroup.delete(user_groups)


class LimsPrinter(ModelSQL, ModelView):
    'Printer'
    __name__ = 'lims.printer'

    name = fields.Char('Name', required=True)


class User:
    __name__ = 'res.user'
    __metaclass__ = PoolMeta

    notebook_view = fields.Many2One('lims.notebook.view', 'Notebook view')
    role = fields.Many2One('lims.user.role', 'Role')
    laboratories = fields.Many2Many('lims.user-laboratory',
        'user', 'laboratory', 'Laboratories')
    laboratory = fields.Many2One('lims.laboratory', 'Main Laboratory',
        domain=[('id', 'in', Eval('laboratories'))], depends=['laboratories'])
    printer = fields.Many2One('lims.printer', 'Printer')

    @classmethod
    def __setup__(cls):
        super(User, cls).__setup__()
        cls._context_fields.insert(0, 'laboratory')
        cls._context_fields.insert(0, 'laboratories')

    @classmethod
    def create(cls, vlist):
        users = super(User, cls).create(vlist)
        cls._create_user_groups(users)
        return users

    @classmethod
    def _create_user_groups(cls, users):
        pool = Pool()
        RoleGroup = pool.get('lims.user.role-res.group')
        UserGroup = pool.get('res.user-res.group')

        for user in users:
            if user.role:
                role_groups = RoleGroup.search([
                    ('role', '=', user.role),
                    ])
                for role_group in role_groups:
                    if not UserGroup.search([
                            ('user', '=', user),
                            ('group', '=', role_group.group),
                            ]):
                        UserGroup.create([{
                            'user': user,
                            'group': role_group.group,
                            }])

    @classmethod
    def write(cls, *args):
        actions = iter(args)
        for users, vals in zip(actions, actions):
            if 'role' in vals:
                cls._update_user_groups(users, vals['role'])
        super(User, cls).write(*args)

    @classmethod
    def _update_user_groups(cls, users, new_role=None):
        pool = Pool()
        RoleGroup = pool.get('lims.user.role-res.group')
        UserGroup = pool.get('res.user-res.group')

        for user in users:
            # delete old groups
            if user.role:
                role_groups = RoleGroup.search([
                    ('role', '=', user.role),
                    ])
                for role_group in role_groups:
                    user_groups = UserGroup.search([
                        ('user', '=', user),
                        ('group', '=', role_group.group),
                        ])
                    if user_groups:
                        UserGroup.delete(user_groups)
            # create new groups
            if new_role:
                role_groups = RoleGroup.search([
                    ('role', '=', new_role),
                    ])
                for role_group in role_groups:
                    if not UserGroup.search([
                            ('user', '=', user),
                            ('group', '=', role_group.group),
                            ]):
                        UserGroup.create([{
                            'user': user,
                            'group': role_group.group,
                            }])

    def get_status_bar(self, name):
        status = self.name
        if self.company:
            status = '%s - %s' % (self.company.rec_name, status)
        if self.laboratory:
            status += ' [%s]' % self.laboratory.rec_name
        return status


class LimsUserLaboratory(ModelSQL):
    'User - Laboratory'
    __name__ = 'lims.user-laboratory'

    user = fields.Many2One('res.user', 'User',
        ondelete='CASCADE', select=True, required=True)
    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        ondelete='CASCADE', select=True, required=True)


class LimsConfiguration(ModelSingleton, ModelSQL, ModelView):
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
    invoice_party_relation_type = fields.Many2One('party.relation.type',
        'Invoice Party Relation Type')
    email_qa = fields.Char('QA Email')
    analysis_product_category = fields.Many2One('product.category',
        'Analysis Product Category', states={'required': True})
    entry_confirm_background = fields.Boolean(
        'Confirm Entries in Background')

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


class LimsConfigurationLaboratory(ModelSQL):
    'Configuration - Laboratory'
    __name__ = 'lims.configuration-laboratory'

    configuration = fields.Many2One('lims.configuration', 'Configuration',
        ondelete='CASCADE', select=True, required=True)
    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        ondelete='CASCADE', select=True, required=True)


class LimsLabWorkYear(ModelSQL, ModelView, CompanyMultiValueMixin):
    'Work Year'
    __name__ = 'lims.lab.workyear'
    _rec_name = 'code'

    code = fields.Char('Code', required=True)
    start_date = fields.Date('Start date', required=True)
    end_date = fields.Date('End date', required=True)
    entry_sequence = fields.MultiValue(fields.Many2One(
        'ir.sequence.strict', 'Entry Sequence', required=True,
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
        'ir.sequence.strict', 'Results Report Sequence', required=True,
        domain=[
            ('company', 'in',
                [Eval('context', {}).get('company', -1), None]),
            ('code', '=', 'lims.results_report'),
            ]))

    @classmethod
    def __setup__(cls):
        super(LimsLabWorkYear, cls).__setup__()
        cls._order.insert(0, ('start_date', 'ASC'))
        cls._error_messages.update({
                'workyear_overlaps': ('Work year "%(first)s" and '
                    '"%(second)s" overlap.'),
                'no_workyear_date': 'No work year defined for "%s".',
                })

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field in sequence_names:
            return pool.get('lims.lab.workyear.sequence')
        return super(LimsLabWorkYear, cls).multivalue_model(field)

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

    @classmethod
    def validate(cls, years):
        super(LimsLabWorkYear, cls).validate(years)
        for year in years:
            year.check_dates()

    def check_dates(self):
        cursor = Transaction().connection.cursor()
        table = self.__table__()
        cursor.execute(*table.select(table.id,
                where=(((table.start_date <= self.start_date)
                        & (table.end_date >= self.start_date))
                    | ((table.start_date <= self.end_date)
                        & (table.end_date >= self.end_date))
                    | ((table.start_date >= self.start_date)
                        & (table.end_date <= self.end_date)))
                & (table.id != self.id)))
        second_id = cursor.fetchone()
        if second_id:
            second = self.__class__(second_id[0])
            self.raise_user_error('workyear_overlaps', {
                    'first': self.rec_name,
                    'second': second.rec_name,
                    })

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
                language = Transaction().language
                languages = Lang.search([('code', '=', language)])
                if not languages:
                    languages = Lang.search([('code', '=', 'en')])
                language, = languages
                formatted = Lang.strftime(date, language.code, language.date)
                cls.raise_user_error('no_workyear_date', (formatted,))
            else:
                return None
        return workyears[0].id

    def get_sequence(self, type):
        sequence = getattr(self, type + '_sequence')
        if sequence:
            return sequence


class LimsLabWorkYearSequence(ModelSQL, CompanyValueMixin):
    'Work Year Sequence'
    __name__ = 'lims.lab.workyear.sequence'

    workyear = fields.Many2One('lims.lab.workyear', 'Work Year',
        ondelete='CASCADE', select=True)
    entry_sequence = fields.Many2One('ir.sequence.strict',
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
    results_report_sequence = fields.Many2One('ir.sequence.strict',
        'Results Report Sequence', depends=['company'], domain=[
            ('company', 'in', [Eval('company', -1), None]),
            ('code', '=', 'lims.results_report'),
            ])

    @classmethod
    def __register__(cls, module_name):
        TableHandler = backend.get('TableHandler')
        exist = TableHandler.table_exist(cls._table)

        super(LimsLabWorkYearSequence, cls).__register__(module_name)

        if not exist:
            cls._migrate_property([], [], [])

    @classmethod
    def _migrate_property(cls, field_names, value_names, fields):
        field_names.extend(sequence_names)
        value_names.extend(sequence_names)
        fields.append('company')
        migrate_property(
            'lims.lab.workyear', field_names, cls, value_names,
            parent='workyear', fields=fields)

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
