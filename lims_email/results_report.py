# This file is part of lims_email module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import logging
from datetime import datetime
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from string import Template

from trytond.model import ModelSQL, ModelView, fields
from trytond.wizard import Wizard, StateView, StateTransition, Button
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from trytond.tools import get_smtp_server
from trytond.config import config as tconfig
from trytond.exceptions import UserError
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
    def do_release(cls, details):
        super().do_release(details)
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
    mailings = fields.One2Many('lims.results_report.mailing',
        'results_report', 'Mailings', readonly=True)

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

    def attach_report(self, report_cache, language):
        '''
        Attach Report file from provided cache
        '''
        pool = Pool()
        Attachment = pool.get('ir.attachment')

        name = '%s_%s.pdf' % ('informe-global-de-resultados', language.code)
        data = report_cache
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

    def get_attached_report(self, report_cache, language):
        filename = self._get_attached_report_filename(language)
        data = {
            'content': report_cache,
            'format': 'pdf',
            'mimetype': 'pdf',
            'filename': '%s.pdf' % filename,
            'name': str(self.number),
            }
        return data

    def _get_attached_report_filename(self, language):
        suffix = language.code
        #filename = str(self.number) + '-' + suffix
        filename = self.get_report_filename() + '-' + suffix
        return filename

    def get_report_filename(self):
        pool = Pool()
        ReportNameFormat = pool.get('lims.result_report.format')
        report_name = Template(ReportNameFormat.get_format(self)).substitute(
            **self._get_name_substitutions())
        return report_name.strip()

    def _get_name_substitutions(self):
        pool = Pool()
        ResultsSample = pool.get('lims.results_report.version.detail.sample')

        samples = ResultsSample.search([
            ('version_detail.report_version.results_report',
                '=', self.id),
            ('version_detail.valid', '=', True),
            ], order=[('id', 'ASC')], limit=1)
        sample = samples and samples[0] or None

        substitutions = {
            'number': getattr(self, 'number', None) or '',
            'sample_number': (sample and
                sample.notebook.fraction.sample.number or ''),
            'party_name': sample and sample.party.rec_name or '',
            }
        for key, value in list(substitutions.items()):
            substitutions[key.upper()] = value.upper()
        return substitutions


class ResultsReportMailing(ModelSQL, ModelView):
    'Results Report Mailing'
    __name__ = 'lims.results_report.mailing'

    results_report = fields.Many2One('lims.results_report', 'Results Report',
        required=True, ondelete='CASCADE', select=True)
    date = fields.Function(fields.DateTime('Date'),
       'get_date', searcher='search_date')
    addresses = fields.Char('Addresses', readonly=True)

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order.insert(0, ('date', 'DESC'))

    def get_date(self, name):
        return self.create_date.replace(microsecond=0)

    @classmethod
    def search_date(cls, name, clause):
        cursor = Transaction().connection.cursor()
        operator_ = clause[1:2][0]
        cursor.execute('SELECT id '
            'FROM "' + cls._table + '" '
            'WHERE create_date' + operator_ + ' %s',
            clause[2:3])
        return [('id', 'in', [x[0] for x in cursor.fetchall()])]

    @classmethod
    def order_date(cls, tables):
        return cls.create_date.convert_order('create_date', tables, cls)


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
            group['to_addrs'] = {}

            for report in group['reports']:
                if not report.ready_to_send:
                    continue
                if not group['cie_fraction_type']:
                    group['reports_ready'].append(report)
                    group['to_addrs'].update(self.get_report_addrs(
                        report))

            if not group['reports_ready']:
                continue

            addresses = ['"%s" <%s>' % (v, k)
                for k, v in group['to_addrs'].items()]
            summary += '%s\n - TO: %s\n\n' % (
                ', '.join([r.number for r in group['reports_ready']]),
                ', '.join(addresses))

        default = {'summary': summary}
        return default

    def transition_send(self):
        logger.info('Send Results Report: INIT')
        pool = Pool()
        Config = pool.get('lims.configuration')
        ResultsReport = pool.get('lims.results_report')
        Lang = pool.get('ir.lang')

        from_addr = tconfig.get('email', 'from')
        if not from_addr:
            logger.warning('Send Results Report: FAILED')
            self.failed.reports_not_ready = []
            self.failed.reports_not_sent = []
            return 'failed'

        config = Config(1)
        hide_recipients = config.mail_ack_report_hide_recipients
        email_qa = config.email_qa

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
            group['to_addrs'] = {}
            group['attachments_data'] = []

            for report in group['reports']:
                logger.info('Send Results Report: %s', report.number)

                if (report.single_sending_report and not
                        report.single_sending_report_ready):
                    logger.warning('Send Results Report: %s: '
                        'IGNORED: NOT READY TO SINGLE SENDING',
                        report.number)
                    continue

                report_cache = {}
                for lang in Lang.search([('translatable', '=', True)]):
                    if not report.has_report_cached(lang):
                        continue
                    report_cache[lang] = None

                    try:
                        report_cache[lang] = report.build_report(lang)
                    except Exception as e:
                        break

                if not report_cache:
                    logger.warning('Send Results Report: %s: '
                        'IGNORED: HAS NO CACHED REPORTS',
                        report.number)
                    continue

                if None in report_cache.values():
                    reports_not_ready.append(report)
                    logger.warning('Send Results Report: %s: '
                        'IGNORED: GLOBAL REPORT BUILD FAILED',
                        report.number)
                    continue

                logger.info('Send Results Report: %s: Build',
                    report.number)
                group['reports_ready'].append(report)

                for lang, cache in report_cache.items():
                    report.attach_report(cache, lang)
                    logger.info('Send Results Report: %s: Attached (%s)' % (
                        report.number, lang.name))
                    group['attachments_data'].append(
                        report.get_attached_report(cache, lang))

                if group['cie_fraction_type']:
                    group['to_addrs'][email_qa] = 'QA'
                else:
                    group['to_addrs'].update(self.get_report_addrs(
                        report))

            if not group['reports_ready']:
                continue

            # Email sending
            to_addrs = list(group['to_addrs'].keys())
            if not to_addrs:
                reports_not_sent.extend(group['reports_ready'])
                logger.warning('Send Results Report: Missing addresses')
                continue
            logger.info('Send Results Report: To addresses: %s',
                ', '.join(to_addrs))

            subject, body = self._get_subject_body(group['reports_ready'])

            msg = self._create_msg(from_addr, to_addrs, subject,
                body, hide_recipients, group['attachments_data'])
            sent = self._send_msg(from_addr, to_addrs, msg)
            if not sent:
                reports_not_sent.extend(group['reports_ready'])
                logger.warning('Send Results Report: Not sent')
                continue
            logger.info('Send Results Report: Sent')

            addresses = ', '.join(['"%s" <%s>' % (v, k)
                    for k, v in group['to_addrs'].items()])
            ResultsReport.write(group['reports_ready'], {
                'sent': True, 'sent_date': datetime.now(),
                'mailings': [('create', [{'addresses': addresses}])],
                })
            Transaction().commit()

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
                if (report.invoice_party and
                        hasattr(report.invoice_party,
                        'block_reports_automatic_sending') and
                        getattr(report.invoice_party,
                        'block_reports_automatic_sending', False)):
                    continue
                res[report.id] = {
                    'cie_fraction_type': report.cie_fraction_type,
                    'reports': [report],
                    }
            return res

        if config.mail_ack_report_grouping == 'party':
            for report in results_reports:
                if (report.invoice_party and
                        hasattr(report.invoice_party,
                        'block_reports_automatic_sending') and
                        getattr(report.invoice_party,
                        'block_reports_automatic_sending', False)):
                    continue
                key = (report.party.id, report.cie_fraction_type)
                if key not in res:
                    res[key] = {
                        'cie_fraction_type': report.cie_fraction_type,
                        'reports': [],
                        }
                res[key]['reports'].append(report)
            return res

        return res

    def get_report_addrs(self, report):
        pool = Pool()
        ResultsSample = pool.get('lims.results_report.version.detail.sample')

        to_addrs = {}

        samples = ResultsSample.search([
            ('version_detail.report_version.results_report', '=', report),
            ])
        for sample in samples:
            entry = sample.notebook.fraction.entry
            if (hasattr(entry.invoice_party,
                    'block_reports_automatic_sending') and
                    getattr(entry.invoice_party,
                        'block_reports_automatic_sending')):
                continue
            for c in entry.report_contacts:
                if c.contact.report_contact:
                    to_addrs[c.contact.email] = (
                        c.contact.party_full_name)
        return to_addrs

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
        body = body.replace('&lt;SAMPLES&gt;', '\n'.join(sample_list))
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
            res = []
            for s in samples:
                res.append(s.notebook.label or s.notebook.rec_name)
            return sorted(list(set(res)), key=lambda x: x)

    def _create_msg(self, from_addr, to_addrs, subject, body,
            hide_recipients, attachments_data=[]):
        if not to_addrs:
            return None

        msg = MIMEMultipart()
        msg['From'] = from_addr
        if not hide_recipients:
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


class ReportNameFormat(ModelSQL, ModelView):
    'Results Report Name Format'
    __name__ = 'lims.result_report.format'

    name = fields.Char('Name')
    format_ = fields.Char('Format', required=True,
        help=("Available variables (also in upper case):"
            "\n- ${number}"
            "\n- ${sample_number}"
            "\n- ${party_name}"))

    @classmethod
    def default_format_(cls):
        return '${number}'

    @classmethod
    def validate(cls, formats):
        super().validate(formats)
        for format_ in formats:
            format_.check_format()

    def check_format(self):
        pool = Pool()
        ResultsReport = pool.get('lims.results_report')
        report = ResultsReport()
        try:
            Template(self.format_).substitute(
                **report._get_name_substitutions())
        except Exception as exception:
            raise UserError(gettext('lims_email.msg_invalid_report_name',
                    format=self.format_,
                    exception=exception)) from exception

    @classmethod
    def get_format(cls, results_report):
        Config = Pool().get('lims.configuration')

        if results_report.party.result_report_format:
            return results_report.party.result_report_format.format_

        config_ = Config(1)
        if config_.result_report_format:
            return config_.result_report_format.format_

        return cls.default_format_()
