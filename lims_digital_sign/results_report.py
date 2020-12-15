# -*- coding: utf-8 -*-
# This file is part of lims_digital_sign module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import logging
import os
import time
from datetime import datetime

from trytond.model import ModelView, fields
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from trytond.config import config as tconfig
from .tokenclient import GetToken

logger = logging.getLogger(__name__)


class ResultsReportVersionDetail(metaclass=PoolMeta):
    __name__ = 'lims.results_report.version.detail'

    def unsign(self):
        results_report = self.report_version.results_report
        if results_report.signed:
            results_report.signed = False
            results_report.signed_date = None
            results_report.save()
        return True

    @classmethod
    @ModelView.button
    def release(cls, details):
        super().release(details)
        for detail in details:
            detail.unsign()

    @classmethod
    @ModelView.button
    def release_all_lang(cls, details):
        super().release_all_lang(details)
        for detail in details:
            detail.unsign()


class ResultsReport(metaclass=PoolMeta):
    __name__ = 'lims.results_report'

    signed = fields.Boolean('Signed', readonly=True)
    signed_date = fields.DateTime('Signed date', readonly=True)

    @classmethod
    def _get_modified_fields(cls):
        fields = super()._get_modified_fields()
        fields.extend([
            'signed',
            'signed_date',
            ])
        return fields

    def build_report(self, english_report=False):
        res = super().build_report(english_report)
        if not res:
            return False
        self.signed = True
        self.signed_date = datetime.now()
        self.save()
        return True

    def _get_global_report(self, details, english_report=False):
        output = super()._get_global_report(details, english_report)
        if not output:
            return False
        return self.sign_report(output)

    def sign_report(self, output):
        '''
        Sign Report
        :output: binary
        :return: binary
        '''
        listen = tconfig.get('token', 'listen')
        path = tconfig.get('token', 'path')

        t = time.strftime("%Y%m%d%H%M%S")
        origin = ''.join(['origin', t, '.pdf'])
        target = ''.join(['target', t, '.pdf'])

        try:
            with open(os.path.join(path, origin), 'wb') as f:
                f.write(output)

            token = GetToken(listen, origin, target)
            token.signDoc()

            with open(os.path.join(path, target), 'rb') as f:
                f_target = f.read()
            return f_target
        except Exception as e:
            logger.error('Send Results Report: '
                'Unable to digitally sign results report %s',
                self.number)
            logger.error(str(e))
            return False


class ResultsReportAnnulation(metaclass=PoolMeta):
    __name__ = 'lims.results_report_annulation'

    def transition_annul(self):
        super().transition_annul()
        ResultsDetail = Pool().get('lims.results_report.version.detail')

        details_annulled = ResultsDetail.search([
            ('id', 'in', Transaction().context['active_ids']),
            ('state', '=', 'annulled'),
            ])
        for detail in details_annulled:
            detail.unsign()
        return 'end'
