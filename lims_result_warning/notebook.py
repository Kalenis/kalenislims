# This file is part of lims_result_warning module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import Pool, PoolMeta

__all__ = ['NotebookLine']


class NotebookLine(metaclass=PoolMeta):
    __name__ = 'lims.notebook.line'

    result_warning = fields.Char('Result Warning')

    @classmethod
    def write(cls, *args):
        TaskTemplate = Pool().get('lims.administrative.task.template')
        super().write(*args)
        actions = iter(args)
        for lines, vals in zip(actions, actions):
            if vals.get('result_warning', False):
                TaskTemplate.create_tasks('result_warning',
                    cls._for_task_result_warning(lines),
                    description=vals.get('result_warning'))

    @classmethod
    def _for_task_result_warning(cls, lines):
        AdministrativeTask = Pool().get('lims.administrative.task')
        res = []
        for line in lines:
            if not line.result_warning:
                continue
            if AdministrativeTask.search([
                    ('type', '=', 'result_warning'),
                    ('origin', '=', '%s,%s' % (cls.__name__, line.id)),
                    ('state', 'not in', ('done', 'discarded')),
                    ]):
                continue
            res.append(line)
        return res
