# This file is part of lims_email module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import unittest
from email import message_from_string

import trytond.tests.test_tryton
from trytond.exceptions import UserError
from trytond.pool import Pool
from trytond.tests.test_tryton import ModuleTestCase, with_transaction


class LimsTestCase(ModuleTestCase):
    'Test lims_email module'
    module = 'lims_email'

    def test_render_mail_html_body(self):
        "Render the HTML body escaping values and exposing the signature"
        from trytond.modules.lims_email.results_report import (
            render_mail_html_body)
        context = {
            'party': 'Fares <Taie>',
            'reports': [{'number': '2026/1'}],
            'samples': [{
                    'label': 'Agua 1', 'number': '2026/10-1',
                    'entry_date': '13/10/2026', 'analyses': ['pH', 'Cloro'],
                    'quotes': ['0049-1/2026'],
                    }],
            }
        template = ('<p>{{ party }}</p>{% for s in samples %}'
            '<li>{{ s.label }}: {{ s.analyses|join(", ") }} '
            '({{ s.quotes|join(", ") }})</li>{% endfor %}{{ signature }}')

        html = render_mail_html_body(template, context, signature=True)
        self.assertIn('Fares &lt;Taie&gt;', html)
        self.assertIn('<li>Agua 1: pH, Cloro (0049-1/2026)</li>', html)
        self.assertIn('cid:signature', html)
        self.assertIn('width="600"', html)
        self.assertIn('max-width: 100%', html)
        self.assertNotIn('cid:signature',
            render_mail_html_body(template, context, signature=False))

    @with_transaction()
    def test_create_msg_html_with_signature(self):
        "HTML emails keep the plain text alternative and the inline signature"
        SendResultsReport = Pool().get('lims_email.send_results_report',
            type='wizard')

        def parts(msg):
            return [p.get_content_type() for p in msg.walk()]

        msg = SendResultsReport._create_msg(None, 'lab@example.com',
            ['client@example.com'], 'Subject', 'Plain body', True)
        self.assertEqual(parts(msg), ['multipart/mixed', 'text/plain'])

        msg = SendResultsReport._create_msg(None, 'lab@example.com',
            ['client@example.com'], 'Subject', 'Plain body', True,
            html_body='<p>HTML body</p>',
            signature=(b'\x89PNG\r\n\x1a\n', 'firma.png'))
        msg = message_from_string(msg.as_string())
        self.assertEqual(parts(msg), ['multipart/mixed',
                'multipart/related', 'multipart/alternative',
                'text/plain', 'text/html', 'image/png'])
        html = [p for p in msg.walk()
            if p.get_content_type() == 'text/html'][0]
        html = html.get_payload(decode=True).decode()
        self.assertIn('cid:signature', html)
        self.assertIn('width="600"', html)
        image = [p for p in msg.walk()
            if p.get_content_type() == 'image/png'][0]
        self.assertEqual(image['Content-ID'], '<signature>')

    @with_transaction()
    def test_invalid_mail_template(self):
        "An HTML template with a syntax error is rejected"
        Configuration = Pool().get('lims.configuration')

        configuration = Configuration()
        configuration.mail_ack_report_html_body = '{% for s in samples %}'
        with self.assertRaises(UserError):
            configuration.check_mail_ack_report_html_body()
        configuration.mail_ack_report_html_body = '{{ party }}'
        configuration.check_mail_ack_report_html_body()


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
            LimsTestCase))
    return suite
