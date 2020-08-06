# This file is part of lims_administrative_task module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelSingleton, ModelSQL, ModelView, fields
from trytond.pyson import Eval
from trytond.pool import Pool
from trytond.modules.company.model import (
    CompanyMultiValueMixin, CompanyValueMixin)


class Configuration(ModelSingleton, ModelSQL, ModelView,
        CompanyMultiValueMixin):
    'Configuration'
    __name__ = 'lims.administrative.task.configuration'

    task_sequence = fields.MultiValue(fields.Many2One(
        'ir.sequence', 'Task Sequence', required=True,
        domain=[
            ('company', 'in',
                [Eval('context', {}).get('company', -1), None]),
            ('code', '=', 'lims.administrative.task'),
            ]))
    email_responsible_subject = fields.Char('Subject of the task'
        ' assignment email',
        help='In the text will be added suffix with the task number')

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field == 'task_sequence':
            return pool.get('lims.administrative.task.configuration.sequence')
        return super().multivalue_model(field)

    @classmethod
    def default_task_sequence(cls, **pattern):
        return cls.multivalue_model(
            'task_sequence').default_task_sequence()


class ConfigurationSequence(ModelSQL, CompanyValueMixin):
    'Configuration - Sequence'
    __name__ = 'lims.administrative.task.configuration.sequence'

    task_sequence = fields.Many2One('ir.sequence',
        'Task Sequence', depends=['company'], domain=[
            ('company', 'in', [Eval('company', -1), None]),
            ('code', '=', 'lims.administrative.task'),
            ])

    @classmethod
    def default_task_sequence(cls):
        pool = Pool()
        ModelData = pool.get('ir.model.data')
        try:
            return ModelData.get_id('lims.administrative.task', 'seq_task')
        except KeyError:
            return None
