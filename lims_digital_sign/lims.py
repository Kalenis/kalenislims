# -*- coding: utf-8 -*-
# This file is part of lims_digital_sign module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import os
import time
from io import BytesIO
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from PyPDF2 import PdfFileMerger
import logging

from trytond.model import ModelView, fields
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from trytond.tools import get_smtp_server
from trytond.config import config as tconfig
from .tokenclient import GetToken

__all__ = ['ResultsReportVersionDetail', 'ResultsReport',
    'ResultsReportAnnulation']


class ResultsReportVersionDetail(metaclass=PoolMeta):
    __name__ = 'lims.results_report.version.detail'

    def unsign(self):
        '''
        Unsign results report of this detail.
        '''
        results_report = self.report_version.results_report
        if results_report.signed:
            results_report.signed = False
            results_report.signed_date = None
            results_report.sent = False
            results_report.sent_date = None
            results_report.save()
        return True

    @classmethod
    @ModelView.button
    def revise(cls, details):
        super(ResultsReportVersionDetail, cls).revise(details)
        for detail in details:
            detail.unsign()

    @classmethod
    @ModelView.button
    def revise_all_lang(cls, details):
        super(ResultsReportVersionDetail, cls).revise_all_lang(details)
        for detail in details:
            detail.unsign()


class ResultsReport(metaclass=PoolMeta):
    __name__ = 'lims.results_report'

    signed = fields.Boolean('Signed', readonly=True)
    signed_date = fields.DateTime('Signed date', readonly=True)
    sent = fields.Boolean('Sent', readonly=True)
    sent_date = fields.DateTime('Sent date', readonly=True)

    @classmethod
    def __setup__(cls):
        super(ResultsReport, cls).__setup__()
        cls._error_messages.update({
            'polisample': 'Polisample',
            })

    @classmethod
    def _get_modified_fields(cls):
        fields = super(ResultsReport, cls)._get_modified_fields()
        fields.extend([
            'signed',
            'signed_date',
            'sent',
            'sent_date',
            ])
        return fields

    @classmethod
    def cron_digital_signs(cls):
        '''
        Cron - Digital Signs
        '''
        logging.getLogger('lims_digital_sign').info(
                'Cron - Digital Signs:INIT')
        pool = Pool()
        ResultsReport = pool.get('lims.results_report')
        DigitalSign = pool.get('lims_digital_sign.digital_sign', type='wizard')

        results_reports = ResultsReport.search([
                ('signed', '=', False)])

        session_id, _, _ = DigitalSign.create()
        digital_sign = DigitalSign(session_id)
        with Transaction().set_context(active_ids=[results_report.id
                for results_report in results_reports]):
            digital_sign.transition_sign()

        logging.getLogger('lims_digital_sign').info(
                'Cron - Digital Signs:END')
        return True

    def has_report_cached(self, english_report=False):
        '''
        Has Report Cached
        :english_report: boolean
        :return: boolean
        '''
        details = self.details_cached(english_report)
        if not details:
            return False
        return True

    def details_cached(self, english_report=False):
        '''
        Details Cached
        :english_report: boolean
        :return: list of details
        '''
        pool = Pool()
        ResultsReportVersionDetail = pool.get(
            'lims.results_report.version.detail')

        format_field = 'report_format'
        if english_report:
            format_field = 'report_format_eng'
        details = ResultsReportVersionDetail.search([
            ('report_version.results_report.id', '=', self.id),
            ('valid', '=', True),
            (format_field, '=', 'pdf'),
            ])
        return details

    def build_report(self, english_report=False):
        '''
        Build Results Report.
        :english_report: boolean
        '''
        details = self.details_cached(english_report=english_report)
        if not details:
            logging.getLogger('lims_digital_sign').info(
                'No %s details cached to build results report %s'
                % (english_report and 'english' or 'spanish', self.number))  # TODO: Debug line
            return

        output = self._get_global_report(details, english_report)
        output = self.sign_report(output)
        if not output:
            return False
        if english_report:
            self.report_format_eng = 'pdf'
            self.report_cache_eng = output
        else:
            self.report_format = 'pdf'
            self.report_cache = output
        self.save()
        return True

    def _get_global_report(self, details, english_report=False):
        merger = PdfFileMerger()
        if english_report:
            for detail in details:
                filedata = BytesIO(detail.report_cache_eng)
                merger.append(filedata)
        else:
            for detail in details:
                filedata = BytesIO(detail.report_cache)
                merger.append(filedata)
        output = BytesIO()
        merger.write(output)
        return output

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

        with open(os.path.join(path, origin), 'wb') as f:
            f.write(output.getvalue())
        try:
            token = GetToken(listen, origin, target)
            token.signDoc()
        except Exception as msg:
            logging.getLogger('lims_digital_sign').error(
                'Unable to digitally sign for results report %s'
                % (self.number))
            logging.getLogger('lims_digital_sign').error(msg[1])
            return False
        with open(os.path.join(path, target), 'rb') as f:
            f_target = f.read()
        return f_target

    def mail_acknowledgment_of_results_report(self, spanish_report=False,
            english_report=False):
        Config = Pool().get('lims.configuration')

        from_addr = tconfig.get('email', 'from')
        to_addrs = []
        entries = []  # TODO: Debug line
        if self.cie_fraction_type:
            config = Config(1)
            to_addrs.append(config.email_qa)
        else:
            for version in self.versions:
                for detail in version.details:
                    for line in detail.notebook_lines:
                        to_addrs.extend([c.contact.email for c
                            in line.notebook_line.fraction.entry.report_contacts
                            if c.contact.report_contact and not
                            c.entry.invoice_party.block_reports_automatic_sending])
                        entries.append(line.notebook_line.fraction.entry.number)  # TODO: Debug line
        logging.getLogger('lims_digital_sign').info(
            'Cron - Digital Signs:results_report.number:%s:to_addrs:%s'
            % (self.number, to_addrs and ', '.join(list(set(to_addrs))) or 'NONE'))  # TODO: Debug line
        logging.getLogger('lims_digital_sign').info(
            'Cron - Digital Signs:results_report.number:%s:Entries:%s'
            % (self.number, entries and ', '.join(list(set(entries))) or 'NONE'))  # TODO: Debug line
        if not (from_addr and to_addrs):
            return

        to_addrs = list(set(to_addrs))
        subject, body = self.subject_body()
        attachments_data = []
        if spanish_report:
            attachments_data.append(self.attachment())
        if english_report:
            attachments_data.append(self.attachment(
                    english_report=english_report))
        msg = self.create_msg(from_addr, to_addrs, subject,
            body, attachments_data)
        return self.send_msg(from_addr, to_addrs, msg)

    def subject_body(self):
        '''
        Subject Body
        '''
        pool = Pool()
        Config = pool.get('lims.configuration')
        User = pool.get('res.user')
        Lang = pool.get('ir.lang')

        config = Config(1)

        lang = User(Transaction().user).language
        if not lang:
            lang, = Lang.search([
                    ('code', '=', 'en'),
                    ], limit=1)

        sample_list = self._get_sample_list(language=lang.code)
        with Transaction().set_context(language=lang.code):
            if len(sample_list) == 1:
                label = '%s' % sample_list[0]
            else:
                label = self.raise_user_error('polisample',
                    raise_exception=False)
            subject = str('%s %s (%s)' % (
                config.mail_ack_report_subject,
                self.number, label)).strip()
            body = str(config.mail_ack_report_body)

        body = body.replace('<SAMPLES>', '\n'.join(sample_list))
        return subject, body

    def _get_sample_list(self, language):
        ResultsReportVersionDetailLine = Pool().get(
            'lims.results_report.version.detail.line')

        with Transaction().set_context(language=language):
            lines = ResultsReportVersionDetailLine.search([
                ('report_version_detail.report_version.results_report.id',
                    '=', self.id),
                ('report_version_detail.valid', '=', True),
                ])
        if not lines:
            return []

        samples = [l.notebook.label for l in lines]
        return sorted(list(set(samples)), key=lambda x: x)

    def attachment(self, english_report=False):
        suffix = 'eng' if english_report else 'esp'
        data = {
            'content': (
                english_report and
                self.report_cache_eng or
                self.report_cache),
            'format': (
                english_report and
                self.report_format_eng or
                self.report_format),
            'mimetype': 'pdf',
            'filename': str(self.number) + '-' + suffix + '.pdf',
            'name': str(self.number),
            }
        return data

    def create_msg(self, from_addr, to_addrs, subject, body,
            attachments_data=[]):
        if not to_addrs:
            return None

        msg = MIMEMultipart()
        msg['From'] = from_addr
        hidden = True
        if not hidden:
            msg['To'] = ', '.join(to_addrs)
        msg['Subject'] = subject

        msg_body = MIMEBase('text', 'plain')
        msg_body.set_payload(body.encode('UTF-8'), 'UTF-8')
        msg.attach(msg_body)

        for attachment_data in attachments_data:
            attachment = MIMEApplication(
                attachment_data['content'],
                Name=attachment_data['filename'], _subtype="pdf")
            attachment.add_header('content-disposition', 'attachment',
                filename=('utf-8', '', attachment_data['filename']))
            msg.attach(attachment)

        return msg

    def send_msg(self, from_addr, to_addrs, msg):
        to_addrs = list(set(to_addrs))
        success = False
        try:
            server = get_smtp_server()
            server.sendmail(from_addr, to_addrs, msg.as_string())
            server.quit()
            success = True
        except Exception:
            logging.getLogger('lims_digital_sign').error(
                'Unable to deliver mail for results report %s' % (self.number))
        return success

    def attach_report(self, english_report=False):
        '''
        Attach Report file from cache field.
        '''
        pool = Pool()
        Attachment = pool.get('ir.attachment')
        data = self.report_cache
        if english_report:
            data = self.report_cache_eng
        name = '%s_%s.pdf' % ('informe-global-de-resultados',
            'eng' if english_report else 'esp')
        resource = '%s,%s' % (self.__name__, self.id)
        attachment = Attachment.search([
                ('resource', '=', resource),
                ('name', '=', name),
                ])
        values = {
            'name': name,
            'type': 'data',
            'data': data,
            'resource': '%s,%s' % (self.__name__, self.id),
            }
        if attachment:
            Attachment.write(attachment, values)
        else:
            Attachment.create([values])
        return True

    def clean_attachments_reports(self):
        '''
        Remove attachments reports
        '''
        pool = Pool()
        Attachment = pool.get('ir.attachment')
        name = 'informe-global-de-resultados'
        resource = '%s,%s' % (self.__name__, self.id)
        attachment = Attachment.search([
                ('resource', '=', resource),
                ('name', 'like', name + '_%.pdf'),
                ])
        if attachment:
            Attachment.delete(attachment)
        return True


class ResultsReportAnnulation(metaclass=PoolMeta):
    __name__ = 'lims.results_report_annulation'

    def transition_annul(self):
        logging.getLogger('lims_digital_sign').info(
                'transition_annul():INIT')
        super(ResultsReportAnnulation, self).transition_annul()
        logging.getLogger('lims_digital_sign').info(
                'transition_annul():INHERIT')

        ResultsReportVersionDetail = Pool().get(
            'lims.results_report.version.detail')

        # Check if the detail was annulled
        detail_annulled = ResultsReportVersionDetail.search([
            ('id', 'in', Transaction().context['active_ids']),
            ('state', '=', 'annulled'),
            ])
        for detail in detail_annulled:
            detail.unsign()

        # Check if the report is not longer valid details
        if detail_annulled:
            results_report = detail_annulled[0].report_version.results_report
            detail_valid = ResultsReportVersionDetail.search([
                ('report_version.results_report.id', '=', results_report.id),
                ('state', '!=', 'annulled'),
                ('valid', '=', True),
                ])
            if not detail_valid:
                results_report.clean_attachments_reports()

        logging.getLogger('lims_digital_sign').info(
                'transition_annul():END')
        return 'end'
