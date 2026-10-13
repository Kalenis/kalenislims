# This file is part of lims_email module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from jinja2 import TemplateSyntaxError
from jinja2.sandbox import SandboxedEnvironment

from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.exceptions import UserError
from trytond.i18n import gettext


def get_mail_template_environment():
    return SandboxedEnvironment(autoescape=True)


class Configuration(metaclass=PoolMeta):
    __name__ = 'lims.configuration'

    mail_ack_report_grouping = fields.Selection([
        (None, 'None'),
        ('party', 'Party'),
        ], 'Grouping of Results reports by Email')
    mail_ack_report_subject = fields.Char('Email subject of Acknowledgment of'
        ' results report',
        help='In the text will be added suffix with the results report number')
    mail_ack_report_body = fields.Text('Email body of Acknowledgment of'
        ' results report',
        help='<SAMPLES> will be replaced by the list of sample\'s labels')
    mail_ack_report_hide_recipients = fields.Boolean('Hide recipients')
    mail_ack_report_html_body = fields.Text('Email HTML body of '
        'Acknowledgment of results report',
        help='Jinja template. When set, the email is sent as HTML and the '
        'plain text body is kept as alternative. Available variables: '
        'party, reports (number) and samples (label, number, entry_date, '
        'analyses, quotes). The signature is added at the end unless '
        '{{ signature }} is used.')
    mail_ack_report_signature = fields.Binary('Email signature',
        filename='mail_ack_report_signature_name',
        help='Image added to the HTML email')
    mail_ack_report_signature_name = fields.Char('Email signature name')
    result_report_format = fields.Many2One('lims.result_report.format',
        'Default Results Report Name Format')

    @staticmethod
    def default_mail_ack_report_grouping():
        return None

    @staticmethod
    def default_mail_ack_report_hide_recipients():
        return True

    @classmethod
    def validate(cls, configurations):
        super().validate(configurations)
        for configuration in configurations:
            configuration.check_mail_ack_report_html_body()

    def check_mail_ack_report_html_body(self):
        if not self.mail_ack_report_html_body:
            return
        try:
            get_mail_template_environment().parse(
                self.mail_ack_report_html_body)
        except TemplateSyntaxError as e:
            raise UserError(gettext('lims_email.msg_invalid_mail_template',
                    line=e.lineno, error=e.message))


class Cron(metaclass=PoolMeta):
    __name__ = 'ir.cron'

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.method.selection.extend([
                ('lims.results_report|cron_send_results_report',
                    "Send Results Report"),
                ])
