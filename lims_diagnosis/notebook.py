# This file is part of lims_diagnosis module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction

__all__ = ['Notebook', 'NotebookLine', 'NotebookLineRepeatAnalysisStart',
    'NotebookLineRepeatAnalysis']


class Notebook(metaclass=PoolMeta):
    __name__ = 'lims.notebook'

    diagnostician = fields.Function(fields.Many2One('lims.diagnostician',
        'Diagnostician'), 'get_sample_field')
    diagnosis_warning = fields.Function(fields.Boolean('Diagnosis Warning'),
        'get_diagnosis_warning')

    @classmethod
    def get_diagnosis_warning(cls, notebooks, name):
        NotebookLine = Pool().get('lims.notebook.line')
        result = {}
        for n in notebooks:
            lines = NotebookLine.search_count([
                ('notebook', '=', n.id),
                ('diagnosis_warning', '=', True),
                ])
            if lines > 0:
                result[n.id] = True
            else:
                result[n.id] = False
        return result


class NotebookLine(metaclass=PoolMeta):
    __name__ = 'lims.notebook.line'

    diagnosis_warning = fields.Boolean('Diagnosis Warning', select=True)
    notify_acceptance = fields.Boolean('Notify acceptace')
    notify_acceptance_user = fields.Many2One('res.user', 'Notification User')

    @staticmethod
    def default_notify_acceptance():
        return False

    @classmethod
    def write(cls, *args):
        TaskTemplate = Pool().get('lims.administrative.task.template')
        super(NotebookLine, cls).write(*args)
        actions = iter(args)
        for lines, vals in zip(actions, actions):
            if 'accepted' in vals and vals['accepted']:
                for line in cls._for_task_line_acceptance(lines):
                    TaskTemplate.create_tasks('line_acceptance',
                        [line], responsible=line.notify_acceptance_user)

    @classmethod
    def _for_task_line_acceptance(cls, lines):
        AdministrativeTask = Pool().get('lims.administrative.task')
        res = []
        for line in lines:
            if AdministrativeTask.search([
                    ('type', '=', 'line_acceptance'),
                    ('origin', '=', '%s,%s' % (cls.__name__, line.id)),
                    ('state', 'not in', ('done', 'discarded')),
                    ]):
                continue
            res.append(line)
        return res


class NotebookLineRepeatAnalysisStart(metaclass=PoolMeta):
    __name__ = 'lims.notebook.line.repeat_analysis.start'

    notify_acceptance = fields.Boolean('Notify acceptace',
        help='Notify when analysis is ready')

    @staticmethod
    def default_notify_acceptance():
        return False


class NotebookLineRepeatAnalysis(metaclass=PoolMeta):
    __name__ = 'lims.notebook.line.repeat_analysis'

    def _get_repetition_defaults(self, line):
        defaults = super(NotebookLineRepeatAnalysis,
            self)._get_repetition_defaults(line)
        defaults['notify_acceptance'] = self.start.notify_acceptance
        if self.start.notify_acceptance:
            defaults['notify_acceptance_user'] = Transaction().user
        return defaults
