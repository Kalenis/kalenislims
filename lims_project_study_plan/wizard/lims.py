# -*- coding: utf-8 -*-
# This file is part of lims_project_study_plan module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from datetime import datetime

from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateTransition, StateView, Button
from trytond.pool import Pool
from trytond.transaction import Transaction

__all__ = ['LimsProjectReOpenStart', 'LimsProjectReOpen']


class LimsProjectReOpenStart(ModelView):
    'Open Project'
    __name__ = 'lims.project.re_open.start'

    reason = fields.Text('Reason', required=True)


class LimsProjectReOpen(Wizard):
    'Open Project'
    __name__ = 'lims.project.re_open'

    start = StateView('lims.project.re_open.start',
        'lims_project_study_plan.lims_project_re_open_start_view_form', [
            Button('Open', 're_open', 'tryton-ok', default=True),
            ])
    re_open = StateTransition()

    def transition_re_open(self):
        LimsProjectChangeLog = Pool().get('lims.project.stp_changelog')
        LimsProjectChangeLog.create([{
            'project': Transaction().context['active_id'],
            'reason': self.start.reason,
            'date': datetime.now(),
            'user': Transaction().user,
            }])
        return 'end'
