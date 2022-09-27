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
from trytond.exceptions import UserError
from trytond.i18n import gettext

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
    def do_release(cls, details):
        super().do_release(details)
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

    def build_report(self, language):
        cache = super().build_report(language)
        cache = self.sign_report(cache)
        self.signed = True
        self.signed_date = datetime.now()
        self.save()
        return cache

    def sign_report(self, cache):
        listen = tconfig.get('token', 'listen')
        path = tconfig.get('token', 'path')

        t = time.strftime("%Y%m%d%H%M%S")
        origin = ''.join(['origin', t, '.pdf'])
        target = ''.join(['target', t, '.pdf'])

        try:
            with open(os.path.join(path, origin), 'wb') as f:
                f.write(cache)

            token = GetToken(listen, origin, target)
            token.signDoc()

            with open(os.path.join(path, target), 'rb') as f:
                f_target = f.read()
            return f_target
        except Exception as e:
            logger.error(str(e))
            raise UserError(gettext('lims_digital_sign.msg_sign_report_error',
                    report=self.number))


class ResultsReportAttachment(metaclass=PoolMeta):
    __name__ = 'lims.results_report.attachment'

    sign = fields.Boolean('Sign')

    @staticmethod
    def default_sign():
        return False

    def get_attachment_data(self):
        data = super().get_attachment_data()
        if data['format'] == 'pdf' and self.sign:
            signed_content = self.sign_attachment(data['content'])
            data['content'] = signed_content
        return data

    def sign_attachment(self, cache):
        listen = tconfig.get('token', 'listen')
        path = tconfig.get('token', 'path')

        t = time.strftime("%Y%m%d%H%M%S")
        origin = ''.join(['origin', t, '.pdf'])
        target = ''.join(['target', t, '.pdf'])

        try:
            with open(os.path.join(path, origin), 'wb') as f:
                f.write(cache)

            token = GetToken(listen, origin, target)
            token.signDoc()

            with open(os.path.join(path, target), 'rb') as f:
                f_target = f.read()
            return f_target
        except Exception as e:
            logger.error(str(e))
            raise UserError(gettext(
                'lims_digital_sign.msg_sign_attachment_error',
                name=self.name, report=self.results_report.number))


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
