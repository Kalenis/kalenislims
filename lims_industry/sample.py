# This file is part of lims_industry module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelSQL, ModelView, fields
from trytond.wizard import StateTransition, StateView, Button
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, Bool
from trytond.exceptions import UserError
from trytond.i18n import gettext

__all__ = ['Entry', 'Sample']


class Entry(metaclass=PoolMeta):
    __name__ = 'lims.entry'

    @classmethod
    def confirm(cls, entries):
        Sample = Pool().get('lims.sample')
        super(Entry, cls).confirm(entries)
        samples = [s for e in entries for s in e.samples]
        Sample._confirm_samples(samples)


class Sample(metaclass=PoolMeta):
    __name__ = 'lims.sample'

    missing_data = fields.Boolean('Missing data')

    @classmethod
    def _confirm_samples(cls, samples):
        TaskTemplate = Pool().get('lims.administrative.task.template')
        TaskTemplate.create_tasks('sample_missing_data',
            cls._for_task_missing_data(samples))

    @classmethod
    def _for_task_missing_data(cls, samples):
        AdministrativeTask = Pool().get('lims.administrative.task')
        res = []
        for sample in samples:
            if not sample.missing_data:
                continue
            if AdministrativeTask.search([
                    ('type', '=', 'sample_missing_data'),
                    ('origin', '=', '%s,%s' % (cls.__name__, sample.id)),
                    ('state', 'not in', ('done', 'discarded')),
                    ]):
                continue
            res.append(sample)
        return res
