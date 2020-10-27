# This file is part of lims_email module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import logging
from io import BytesIO
from datetime import datetime
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from PyPDF2 import PdfFileMerger

from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateView, StateTransition, Button
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from trytond.tools import get_smtp_server
from trytond.config import config as tconfig
from trytond.i18n import gettext

logger = logging.getLogger(__name__)


class ResultsReportVersionDetail(metaclass=PoolMeta):
    __name__ = 'lims.results_report.version.detail'

    def unsend(self):
        results_report = self.report_version.results_report
        if results_report.sent:
            results_report.sent = False
            results_report.sent_date = None
            results_report.save()
        return True

    @classmethod
    @ModelView.button
    def release(cls, details):
        super().release(details)
        for detail in details:
            detail.unsend()

    @classmethod
    @ModelView.button
    def release_all_lang(cls, details):
        super().release_all_lang(details)
        for detail in details:
            detail.unsend()


class ResultsReport(metaclass=PoolMeta):
    __name__ = 'lims.results_report'

    sent = fields.Boolean('Sent', readonly=True)
    sent_date = fields.DateTime('Sent date', readonly=True)

    @classmethod
    def _get_modified_fields(cls):
        fields = super()._get_modified_fields()
        fields.extend([
            'sent',
            'sent_date',
            ])
        return fields

    @classmethod
    def cron_send_results_report(cls):
        '''
        Cron - Send Results Report
        '''
        logger.info('Cron - Send Results Report: INIT')
        pool = Pool()
        SendResultsReport = pool.get('lims_email.send_results_report',
            type='wizard')

        results_reports = cls.search([('sent', '=', False)])

        session_id, _, _ = SendResultsReport.create()
        send_results_report = SendResultsReport(session_id)
        with Transaction().set_context(active_ids=[results_report.id
                for results_report in results_reports]):
            send_results_report.transition_send()

        logger.info('Cron - Send Results Report: END')
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
        ResultsDetail = pool.get('lims.results_report.version.detail')

        format_field = 'report_format'
        if english_report:
            format_field = 'report_format_eng'

        details = ResultsDetail.search([
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
        details = self.details_cached(english_report)
        if not details:
            logger.info('No %s details cached to build results report %s'
                % (english_report and 'english' or 'spanish', self.number))
            return False

        output = self._get_global_report(details, english_report)
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
        all_cache = []
        if english_report:
            for detail in details:
                if detail.report_cache_eng:
                    all_cache.append(detail.report_cache_eng)
        else:
            for detail in details:
                if detail.report_cache:
                    all_cache.append(detail.report_cache)
        if not all_cache:
            return False

        merger = PdfFileMerger(strict=False)
        for cache in all_cache:
            filedata = BytesIO(cache)
            merger.append(filedata)
        output = BytesIO()
        merger.write(output)
        return bytearray(output.getvalue())

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

        values = {
            'name': name,
            'type': 'data',
            'data': data,
            'resource': '%s,%s' % (self.__name__, self.id),
            }

        attachment = Attachment.search([
            ('resource', '=', resource),
            ('name', '=', name),
            ])
        if attachment:
            Attachment.write(attachment, values)
        else:
            Attachment.create([values])
        return True

    def clean_attached_reports(self):
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

    def get_attached_report(self, english_report=False):
        filename = self._get_attached_report_filename(english_report)
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
            'filename': '%s.pdf' % filename,
            'name': str(self.number),
            }
        return data

    def _get_attached_report_filename(self, english_report=False):
        suffix = 'eng' if english_report else 'esp'
        filename = str(self.number) + '-' + suffix
        return filename


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
            detail.unsend()

        # Check if the report is not longer valid details
        if details_annulled:
            results_report = details_annulled[0].report_version.results_report
            details_valid = ResultsDetail.search([
                ('report_version.results_report.id', '=', results_report.id),
                ('state', '!=', 'annulled'),
                ('valid', '=', True),
                ])
            if not details_valid:
                results_report.clean_attached_reports()
        return 'end'


class SendResultsReportStart(ModelView):
    "Send Results Report"
    __name__ = 'lims_email.send_results_report.start'

    summary = fields.Text('Summary', readonly=True)


class SendResultsReportSucceed(ModelView):
    "Send Results Report"
    __name__ = 'lims_email.send_results_report.succeed'


class SendResultsReportFailed(ModelView):
    "Send Results Report"
    __name__ = 'lims_email.send_results_report.failed'

    reports_not_ready = fields.Many2Many('lims.results_report',
        None, None, 'Reports not ready', readonly=True)
    reports_not_sent = fields.Many2Many('lims.results_report',
        None, None, 'Reports not sent', readonly=True)


class SendResultsReport(Wizard):
    'Send Results Report'
    __name__ = 'lims_email.send_results_report'

    start = StateView('lims_email.send_results_report.start',
        'lims_email.send_results_report_start_view', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Send', 'send', 'tryton-ok', default=True),
            ])
    send = StateTransition()
    succeed = StateView('lims_email.send_results_report.succeed',
        'lims_email.send_results_report_succeed_view', [
            Button('Ok', 'end', 'tryton-ok', default=True),
            ])
    failed = StateView('lims_email.send_results_report.failed',
        'lims_email.send_results_report_failed_view', [
            Button('Ok', 'end', 'tryton-ok', default=True),
            ])

    def default_start(self, fields):
        pool = Pool()
        ResultsReport = pool.get('lims.results_report')
        ResultsSample = pool.get('lims.results_report.version.detail.sample')

        summary = ''

        context = Transaction().context
        model = context.get('active_model', None)
        if model and model == 'ir.ui.menu':
            # If it was executed from `menu item`, then search ids
            active_ids = [r.id for r in ResultsReport.search(
                    [('sent', '=', False)])]
        else:
            # If it was executed from `actions`, then use context ids
            active_ids = context['active_ids']

        for group in self.get_grouped_reports(active_ids).values():
            group['reports_ready'] = []
            group['to_addrs'] = []

            for report in group['reports']:
                if (report.single_sending_report and not
                        report.single_sending_report_ready):
                    continue

                spanish_report = report.has_report_cached(
                    english_report=False)
                english_report = report.has_report_cached(
                    english_report=True)
                if not spanish_report and not english_report:
                    continue

                if not group['cie_fraction_type']:
                    group['reports_ready'].append(report)
                    samples = ResultsSample.search([
                        ('version_detail.report_version.results_report',
                            '=', report),
                        ])
                    for sample in samples:
                        entry = sample.notebook.fraction.entry
                        if (hasattr(entry.invoice_party,
                                'block_reports_automatic_sending') and
                                getattr(entry.invoice_party,
                                    'block_reports_automatic_sending')):
                            continue
                        group['to_addrs'].extend([c.contact.email
                                for c in entry.report_contacts
                                if c.contact.report_contact])

            if not group['reports_ready']:
                continue

            to_addrs = list(set(group['to_addrs']))

            summary += '%s\n - TO: %s\n\n' % (
                ', '.join([r.number for r in group['reports_ready']]),
                ', '.join(to_addrs))

        default = {'summary': summary}
        return default

    def transition_send(self):
        logger.info('Send Results Report: INIT')
        pool = Pool()
        Config = pool.get('lims.configuration')
        ResultsReport = pool.get('lims.results_report')
        ResultsSample = pool.get('lims.results_report.version.detail.sample')

        from_addr = tconfig.get('email', 'from')
        if not from_addr:
            logger.warning('Send Results Report: FAILED')
            self.failed.reports_not_ready = []
            self.failed.reports_not_sent = []
            return 'failed'

        config = Config(1)

        context = Transaction().context
        model = context.get('active_model', None)
        if model and model == 'ir.ui.menu':
            # If it was executed from `menu item`, then search ids
            active_ids = [r.id for r in ResultsReport.search(
                    [('sent', '=', False)])]
            logger.info('Send Results Report: '
                'Processing all Results Reports')
        else:
            # If it was executed from `actions` or `cron`, then use context ids
            active_ids = context['active_ids']
            logger.info('Send Results Report: '
                'Processing context Results Reports')

        reports_not_ready = []
        reports_not_sent = []
        for group in self.get_grouped_reports(active_ids).values():
            group['reports_ready'] = []
            group['to_addrs'] = []

            for report in group['reports']:
                logger.info('Send Results Report: %s', report.number)

                if (report.single_sending_report and not
                        report.single_sending_report_ready):
                    logger.warning('Send Results Report: %s: '
                        'IGNORED: NOT READY TO SINGLE SENDING',
                        report.number)
                    continue

                spanish_report = report.has_report_cached(
                    english_report=False)
                english_report = report.has_report_cached(
                    english_report=True)
                if not spanish_report and not english_report:
                    logger.warning('Send Results Report: %s: '
                        'IGNORED: HAS NO CACHED REPORTS',
                        report.number)
                    continue

                ready = True
                if spanish_report:
                    ready = ready and report.build_report(
                        english_report=False)
                if english_report:
                    ready = ready and report.build_report(
                        english_report=True)
                if not ready:
                    reports_not_ready.append(report)
                    logger.warning('Send Results Report: %s: '
                        'IGNORED: GLOBAL REPORT BUILD FAILED',
                        report.number)
                    continue

                logger.info('Send Results Report: %s: Build',
                    report.number)
                group['reports_ready'].append(
                    (report, spanish_report, english_report))

                if spanish_report:
                    report.attach_report(english_report=False)
                if english_report:
                    report.attach_report(english_report=True)
                logger.info('Send Results Report: %s: Attached',
                    report.number)

                if group['cie_fraction_type']:
                    group['to_addrs'].append(config.email_qa)
                else:
                    samples = ResultsSample.search([
                        ('version_detail.report_version.results_report',
                            '=', report),
                        ])
                    for sample in samples:
                        entry = sample.notebook.fraction.entry
                        if (hasattr(entry.invoice_party,
                                'block_reports_automatic_sending') and
                                getattr(entry.invoice_party,
                                    'block_reports_automatic_sending')):
                            continue
                        group['to_addrs'].extend([c.contact.email
                                for c in entry.report_contacts
                                if c.contact.report_contact])

            if not group['reports_ready']:
                continue

            # Email sending
            to_addrs = list(set(group['to_addrs']))
            if not to_addrs:
                reports_not_sent.extend(
                    [r[0] for r in group['reports_ready']])
                logger.warning('Send Results Report: Missing addresses')
                continue
            logger.info('Send Results Report: To addresses: %s',
                ', '.join(to_addrs))

            subject, body = self._get_subject_body(
                [r[0] for r in group['reports_ready']])

            attachments_data = []
            for r in group['reports_ready']:
                if r[1]:  # spanish_report
                    attachments_data.append(r[0].get_attached_report(
                        english_report=False))
                if r[2]:  # english_report
                    attachments_data.append(r[0].get_attached_report(
                        english_report=True))

            msg = self._create_msg(from_addr, to_addrs, subject,
                body, attachments_data)
            sent = self._send_msg(from_addr, to_addrs, msg)
            if not sent:
                reports_not_sent.extend(
                    [r[0] for r in group['reports_ready']])
                logger.warning('Send Results Report: Not sent')
                continue
            logger.info('Send Results Report: Sent')

            ResultsReport.write(
                [r[0] for r in group['reports_ready']],
                {'sent': True, 'sent_date': datetime.now()})

        if reports_not_ready or reports_not_sent:
            logger.warning('Send Results Report: FAILED')
            self.failed.reports_not_ready = reports_not_ready
            self.failed.reports_not_sent = reports_not_sent
            return 'failed'

        logger.info('Send Results Report: SUCCEED')
        return 'succeed'

    def get_grouped_reports(self, report_ids):
        pool = Pool()
        Config = pool.get('lims.configuration')
        ResultsReport = pool.get('lims.results_report')

        config = Config(1)

        res = {}
        results_reports = ResultsReport.browse(report_ids)

        if not config.mail_ack_report_grouping:
            for report in results_reports:
                res[report.id] = {
                    'cie_fraction_type': report.cie_fraction_type,
                    'reports': [report],
                    }
            return res

        if config.mail_ack_report_grouping == 'party':
            for report in results_reports:
                key = (report.party.id, report.cie_fraction_type)
                if key not in res:
                    res[key] = {
                        'cie_fraction_type': report.cie_fraction_type,
                        'reports': [],
                        }
                res[key]['reports'].append(report)
            return res

        return res

    def _get_subject_body(self, reports):
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

        report_list = ', '.join([r.number for r in reports])
        sample_list = self._get_sample_list(reports, language=lang.code)
        with Transaction().set_context(language=lang.code):
            if len(sample_list) == 1:
                label = '%s' % sample_list[0]
            else:
                label = gettext('lims_email.msg_polisample')
            subject = str('%s %s (%s)' % (
                config.mail_ack_report_subject,
                report_list, label)).strip()
            body = str(config.mail_ack_report_body)

        body = body.replace('<SAMPLES>', '\n'.join(sample_list))
        return subject, body

    def _get_sample_list(self, reports, language):
        pool = Pool()
        ResultsSample = pool.get('lims.results_report.version.detail.sample')

        with Transaction().set_context(language=language):
            samples = ResultsSample.search([
                ('version_detail.report_version.results_report',
                    'in', reports),
                ('version_detail.valid', '=', True),
                ])
            if not samples:
                return []
            samples = [s.notebook.label for s in samples]
            return sorted(list(set(samples)), key=lambda x: x)

    def _create_msg(self, from_addr, to_addrs, subject, body,
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

    def _send_msg(self, from_addr, to_addrs, msg):
        to_addrs = list(set(to_addrs))
        success = False
        try:
            server = get_smtp_server()
            server.sendmail(from_addr, to_addrs, msg.as_string())
            server.quit()
            success = True
        except Exception as e:
            logger.error('Send Results Report: Unable to deliver mail')
            logger.error(str(e))
        return success

    def default_failed(self, fields):
        default = {
            'reports_not_ready': [f.id for f in self.failed.reports_not_ready],
            'reports_not_sent': [f.id for f in self.failed.reports_not_sent],
            }
        return default
