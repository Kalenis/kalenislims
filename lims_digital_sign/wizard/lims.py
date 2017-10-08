# -*- coding: utf-8 -*-
# This file is part of lims_digital_sign module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import logging

from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction

__all__ = ['LimsResultsReportAnnulation']


class LimsResultsReportAnnulation:
    __name__ = 'lims.results_report_annulation'
    __metaclass__ = PoolMeta

    def transition_annul(self):
        logging.getLogger('lims_digital_sign').info(
                'transition_annul():INIT')
        super(LimsResultsReportAnnulation, self).transition_annul()
        logging.getLogger('lims_digital_sign').info(
                'transition_annul():INHERIT')

        LimsResultsReportVersionDetail = Pool().get(
            'lims.results_report.version.detail')

        # Check if the detail was annulled
        detail_annulled = LimsResultsReportVersionDetail.search([
            ('id', 'in', Transaction().context['active_ids']),
            ('state', '=', 'annulled'),
            ])
        for detail in detail_annulled:
            detail.unsign()

        # Check if the report is not longer valid details
        if detail_annulled:
            results_report = detail_annulled[0].report_version.results_report
            detail_valid = LimsResultsReportVersionDetail.search([
                ('report_version.results_report.id', '=', results_report.id),
                ('state', '!=', 'annulled'),
                ('valid', '=', True),
                ])
            if not detail_valid:
                results_report.clean_attachments_reports()

        logging.getLogger('lims_digital_sign').info(
                'transition_annul():END')
        return 'end'
