# This file is part of lims_interface module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.wizard import Wizard, StateAction
from trytond.pool import Pool
from trytond.pyson import PYSONEncoder
from trytond.transaction import Transaction

__all__ = ['OpenReferralCompilation']


class OpenReferralCompilation(Wizard):
    'Open Compilation'
    __name__ = 'lims.referral.open_compilation'

    start = StateAction('lims_interface.act_lims_interface_compilation_list')

    def do_start(self, action):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        referral_ids = ', '.join(str(r)
            for r in Transaction().context['active_ids'] + [0])
        cursor.execute('SELECT nl.compilation '
            'FROM "' + NotebookLine._table + '" nl '
                'INNER JOIN "' + EntryDetailAnalysis._table + '" d '
                'ON d.id = nl.analysis_detail '
            'WHERE d.referral IN (' + referral_ids + ')')
        res = [x[0] for x in cursor.fetchall()]

        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', 'in', res)])
        return action, {}
