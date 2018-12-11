# -*- coding: utf-8 -*-
# This file is part of lims_digital_sign module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import logging
from datetime import datetime

from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateView, StateTransition, Button
from trytond.pool import Pool
from trytond.transaction import Transaction

__all__ = ['DigitalSignStart', 'DigitalSignSucceed', 'DigitalSignFailed',
    'DigitalSign']


class DigitalSignStart(ModelView):
    "Digital Sign Start"
    __name__ = 'lims_digital_sign.digital_sign.start'


class DigitalSignSucceed(ModelView):
    "Digital Sign Succeed"
    __name__ = 'lims_digital_sign.digital_sign.succeed'


class DigitalSignFailed(ModelView):
    "Digital Sign Failed"
    __name__ = 'lims_digital_sign.digital_sign.failed'

    unsigned_reports = fields.One2Many('lims.results_report', None,
        'Unsigned reports', readonly=True)
    unsent_reports = fields.One2Many('lims.results_report', None,
        'Unsent reports', readonly=True)


class DigitalSign(Wizard):
    'Digital Sign'
    __name__ = 'lims_digital_sign.digital_sign'

    start = StateView('lims_digital_sign.digital_sign.start',
        'lims_digital_sign.view_digital_sign_start', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Sign', 'sign', 'tryton-ok', default=True),
            ])
    sign = StateTransition()
    succeed = StateView('lims_digital_sign.digital_sign.succeed',
        'lims_digital_sign.view_digital_sign_succeed', [
            Button('Ok', 'end', 'tryton-ok', default=True),
            ])
    failed = StateView('lims_digital_sign.digital_sign.failed',
        'lims_digital_sign.view_digital_sign_failed', [
            Button('Ok', 'end', 'tryton-ok', default=True),
            ])

    def transition_sign(self):
        '''
        Digital Sign reports
        '''
        logger = logging.getLogger('lims_digital_sign')
        logger.info('Wizard - Digital Sign:INIT')
        ResultsReport = Pool().get('lims.results_report')

        context = Transaction().context
        model = context.get('active_model', None)
        if model and model == 'ir.ui.menu':
            # If it was executed from `menu item`, then get ids
            # TODO: Include signed but not sent?
            active_ids = [r.id for r in ResultsReport.search([
                    ('signed', '=', False)])]
            logger.info('Wizard - Digital Sign:Processing all Results '
                    'Reports')
        else:
            # If it was executed from `actions` or `cron`, then use context ids
            active_ids = context['active_ids']
            logger.info('Wizard - Digital Sign:Processing context Results '
                    'Reports')

        unsigned_reports = []
        unsent_reports = []
        for active_id in active_ids:
            results_report = ResultsReport(active_id)
            logger.info('Wizard - Digital Sign:results_report.number:%s',
                    results_report.number)
            if (results_report.single_sending_report and not
                    results_report.single_sending_report_ready):
                logger.warn('Wizard - Digital Sign:results_report.number:%s:'
                        'IGNORED:REPORT NOT READY TO SINGLE SENDING',
                        results_report.number)
                continue
            spanish_report = results_report.has_report_cached(
                    english_report=False)
            english_report = results_report.has_report_cached(
                    english_report=True)
            if not spanish_report and not english_report:
                logger.warn('Wizard - Digital Sign:results_report.number:%s:'
                        'IGNORED:NO HAS CACHED REPORTS', results_report.number)
                continue
            signed = True
            if spanish_report:
                signed = signed and results_report.build_report(
                        english_report=False)
            if english_report:
                signed = signed and results_report.build_report(
                        english_report=True)
            if not signed:
                unsigned_reports.append(results_report)
                continue
            else:
                logger.info('Wizard - Digital Sign:results_report.number:'
                        '%s:Signed.', results_report.number)
                if spanish_report:
                    results_report.attach_report(english_report=False)
                if english_report:
                    results_report.attach_report(english_report=True)
                logger.info('Wizard - Digital Sign:results_report.number:'
                        '%s:Attached.', results_report.number)
                results_report.signed = True
                results_report.signed_date = datetime.now()
                results_report.save()
                sent = results_report.mail_acknowledgment_of_results_report(
                        spanish_report=spanish_report,
                        english_report=english_report)
                if not sent:
                    unsent_reports.append(results_report)
                    continue
                else:
                    logger.info('Wizard - Digital Sign:results_report.number:'
                            '%s:Sent.', results_report.number)
                    results_report.sent = True
                    results_report.sent_date = datetime.now()
                    results_report.save()

        if not unsigned_reports and not unsent_reports:
            logger.info('Wizard - Digital Sign:SUCCEED')
            return 'succeed'
        else:
            logger.info('Wizard - Digital Sign:FAILED')
            self.failed.unsigned_reports = unsigned_reports
            self.failed.unsent_reports = unsent_reports
            return 'failed'

    def default_failed(self, fields):
        default = {
            'unsigned_reports': [f.id for f in self.failed.unsigned_reports],
            'unsent_reports': [f.id for f in self.failed.unsent_reports],
            }
        return default
