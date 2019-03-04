# -*- coding: utf-8 -*-
# This file is part of lims_project module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelView, ModelSQL, fields, Unique
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Eval
from trytond.transaction import Transaction

__all__ = ['Project', 'Entry', 'Sample', 'CreateSampleStart', 'CreateSample']


class Project(ModelSQL, ModelView):
    'Project'
    __name__ = 'lims.project'
    _rec_name = 'description'

    code = fields.Char('Code', states={'required': True})
    description = fields.Char('Description', required=True)
    type = fields.Selection([], 'Type', sort=False)
    start_date = fields.Date('Start date')
    end_date = fields.Date('End date')
    client = fields.Many2One('party.party', 'Client')
    storage_time = fields.Integer('Storage time (in months)', required=True)
    comments = fields.Text('Comments')
    external_quality_control = fields.Boolean('External quality control')

    @classmethod
    def __setup__(cls):
        super(Project, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code),
                'Project code must be unique'),
            ]

    @staticmethod
    def default_storage_time():
        return 3

    @staticmethod
    def default_external_quality_control():
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


class Entry(metaclass=PoolMeta):
    __name__ = 'lims.entry'

    project = fields.Many2One('lims.project', 'Project',
        domain=[('client', '=', Eval('party'))], depends=['party'])
    project_type = fields.Function(fields.Selection([],
        'Type', sort=False),
        'on_change_with_project_type')

    @classmethod
    def __setup__(cls):
        super(Entry, cls).__setup__()
        cls.samples.context.update({
            'project': Eval('project', None),
            })
        if 'project' not in cls.samples.depends:
            cls.samples.depends.append('project')

    @fields.depends('project')
    def on_change_with_project_type(self, name=None):
        res = None
        if self.project:
            res = self.project.type
        return res


class Sample(metaclass=PoolMeta):
    __name__ = 'lims.sample'

    project_type = fields.Function(fields.Selection([], 'Type'),
        'on_change_with_project_type')

    @staticmethod
    def default_project_type():
        Project = Pool().get('lims.project')
        if Transaction().context.get('project'):
            return Project(Transaction().context.get('project')).type
        return ''

    @fields.depends('entry')
    def on_change_with_project_type(self, name=None):
        res = ''
        if self.entry and self.entry.project:
            res = self.entry.project.type
        return res


class CreateSampleStart(metaclass=PoolMeta):
    __name__ = 'lims.create_sample.start'

    project_type = fields.Char('Type')


class CreateSample(metaclass=PoolMeta):
    __name__ = 'lims.create_sample'

    def default_start(self, fields):
        Entry = Pool().get('lims.entry')

        defaults = super(CreateSample, self).default_start(fields)
        defaults['project_type'] = ''

        entry = Entry(Transaction().context['active_id'])
        if entry.project:
            defaults['project_type'] = entry.project.type
        return defaults
