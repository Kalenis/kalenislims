# This file is part of lims_report_html module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.i18n import gettext
from trytond.modules.html_report.generator import PdfGenerator

__all__ = ['ResultsReportVersionDetail', 'ResultReport']


class ResultsReportVersionDetail(metaclass=PoolMeta):
    __name__ = 'lims.results_report.version.detail'

    template = fields.Many2One('lims.result_report.template',
        'Report Template', depends=['state'],
        states={'readonly': Eval('state') != 'draft'})

    @classmethod
    def __setup__(cls):
        super(ResultsReportVersionDetail, cls).__setup__()
        if 'invisible' in cls.resultrange_origin.states:
            del cls.resultrange_origin.states['invisible']
        if 'required' in cls.resultrange_origin.states:
            del cls.resultrange_origin.states['required']


class ResultReport(metaclass=PoolMeta):
    __name__ = 'lims.result_report'

    @classmethod
    def execute(cls, ids, data):
        cls.check_access()
        action, model = cls.get_action(data)

        records = []
        with Transaction().set_context(html_report=action.id):
            if model:
                records = cls._get_dual_records(ids, model, data)
            oext, content = cls._execute_html_result_report(records, data,
                action)
            if not isinstance(content, str):
                content = bytearray(content) if bytes == str else bytes(
                    content)

        return oext, content, cls.get_direct_print(action), cls.get_name(
            action)

    @classmethod
    def _execute_html_result_report(cls, records, data, action):
        documents = []
        for record in records:
            template = cls.get_result_report_template(action, record.raw.id)
            content = cls.render_template_jinja(action, template,
            record=record, records=[record], data=data)
            if action.extension == 'pdf':
                documents.append(PdfGenerator(content).render_html())
            else:
                documents.append(content)
        if action.extension == 'pdf':
            document = documents[0].copy([page for doc in documents
                for page in doc.pages])
            document = document.write_pdf()
        else:
            document = ''.join(documents)
        return action.extension, document

    @classmethod
    def get_result_report_template(cls, action, detail_id):
        ResultsDetail = Pool().get('lims.results_report.version.detail')
        detail = ResultsDetail(detail_id)
        content = detail.template and detail.template.content
        if not content:
            content = (action.report_content and
                action.report_content.decode('utf-8'))
            if not content:
                raise UserError(gettext('lims_report_html.msg_no_template'))
        return content
