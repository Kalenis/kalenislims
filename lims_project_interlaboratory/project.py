# -*- coding: utf-8 -*-
# This file is part of lims_project_interlaboratory module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval, Equal, Bool, Not, And

__all__ = ['Project', 'Entry']

STATES = {
    'required': Bool(Equal(Eval('type'), 'itl')),
}
DEPENDS = ['type']
PROJECT_TYPE = ('itl', 'Interlaboratory')


class Project(metaclass=PoolMeta):
    __name__ = 'lims.project'

    int_itl_party = fields.Many2One('party.party', 'ITL Party',
        states=STATES, depends=DEPENDS)
    int_result_date = fields.Date('Result date')
    int_report_reception = fields.Date('Report reception')
    int_evaluation = fields.Text('Evaluation',
        states={
            'required': And(Equal(Eval('type'), 'itl'),
                Bool(Eval('end_date'))),
            }, depends=['type', 'end_date'])

    @classmethod
    def __setup__(cls):
        super(Project, cls).__setup__()
        project_type = PROJECT_TYPE
        if project_type not in cls.type.selection:
            cls.type.selection.append(project_type)

    @classmethod
    def view_attributes(cls):
        return super(Project, cls).view_attributes() + [
            ('//group[@id="itl"]', 'states', {
                    'invisible': Not(Bool(Equal(Eval('type'), 'itl'))),
                    })]


class Entry(metaclass=PoolMeta):
    __name__ = 'lims.entry'

    @classmethod
    def __setup__(cls):
        super(Entry, cls).__setup__()
        project_type = PROJECT_TYPE
        if project_type not in cls.project_type.selection:
            cls.project_type.selection.append(project_type)
