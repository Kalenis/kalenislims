# This file is part of lims_report_html module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from lxml import html as lxml_html
from base64 import b64encode

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

    @classmethod
    def _get_detail_copy(cls, detail):
        detail_default = super(ResultsReportVersionDetail,
            cls)._get_detail_copy(detail)
        if detail.template:
            detail_default['template'] = detail.template.id
        return detail_default


class ResultReport(metaclass=PoolMeta):
    __name__ = 'lims.result_report'

    @classmethod
    def execute(cls, ids, data):
        ResultsDetail = Pool().get('lims.results_report.version.detail')
        if len(ids) > 1:
            raise UserError(gettext('lims.msg_multiple_reports'))

        results_report = ResultsDetail(ids[0])
        if results_report.state == 'annulled':
            raise UserError(gettext('lims.msg_annulled_report'))

        if data is None:
            data = {}
        current_data = data.copy()
        current_data['alt_lang'] = None
        result_orig = cls.execute_html_results_report(ids, current_data)
        current_data['alt_lang'] = 'en'
        result_eng = cls.execute_html_results_report(ids, current_data)

        save = False
        if results_report.english_report:
            if results_report.report_cache_eng:
                result = (results_report.report_format_eng,
                    results_report.report_cache_eng) + result_eng[2:]
            else:
                result = result_eng
                if ('english_report' in current_data and
                        current_data['english_report']):
                    results_report.report_format_eng, \
                        results_report.report_cache_eng = result_eng[:2]
                    save = True
        else:
            if results_report.report_cache:
                result = (results_report.report_format,
                    results_report.report_cache) + result_orig[2:]
            else:
                result = result_orig
                if ('english_report' in current_data and
                        not current_data['english_report']):
                    results_report.report_format, \
                        results_report.report_cache = result_orig[:2]
                    save = True
        if save:
            results_report.save()

        return result

    @classmethod
    def execute_html_results_report(cls, ids, data):
        cls.check_access()
        action, model = cls.get_action(data)

        with Transaction().set_context(html_report=action.id):
            records = []
            if model:
                records = cls._get_records(ids, model, data)
                #records = cls._get_dual_records(ids, model, data)
            oext, content = cls._execute_html_results_report(records, data,
                action)
            if not isinstance(content, str):
                content = bytearray(content) if bytes == str else bytes(
                    content)

        return oext, content, cls.get_direct_print(action), cls.get_name(
            action)

    @classmethod
    def _execute_html_results_report(cls, records, data, action):
        documents = []
        for record in records:
            template = cls.get_results_report_template(action, record.id)
            content = cls.render_results_report_template(action, template,
                record=record, records=[record], data=data)
            if action.extension == 'pdf':
                documents.append(PdfGenerator(content, side_margin=1,
                    extra_vertical_margin=30).render_html())
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
    def get_results_report_template(cls, action, detail_id):
        ResultsDetail = Pool().get('lims.results_report.version.detail')
        detail = ResultsDetail(detail_id)
        content = detail.template and detail.template.content
        if not content:
            content = (action.report_content and
                action.report_content.decode('utf-8'))
            if not content:
                raise UserError(gettext('lims_report_html.msg_no_template'))
        return content

    @classmethod
    def render_results_report_template(cls, action, template_string,
            record=None, records=None, data=None):
        env = cls.get_environment()
        report_template = env.from_string(template_string)
        context = cls.get_context(records, data)
        context.update({
            'report': action,
            'get_image': cls.get_image,
            })
        res = report_template.render(**context)
        res = cls.parse_images(res)
        # print('TEMPLATE:\n', res)
        return res

    @classmethod
    def parse_images(cls, template_string):
        Attachment = Pool().get('ir.attachment')
        root = lxml_html.fromstring(template_string)
        for elem in root.iter('img'):
            # get image from attachments
            if 'id' in elem.attrib:
                img = Attachment.search([('id', '=', int(elem.attrib['id']))])
                if img:
                    elem.attrib['src'] = cls.get_image(img[0].data)
            # set width and height in style attribute
            style = elem.attrib.get('style', '')
            if 'width' in elem.attrib:
                style += ' width: %spx;' % str(elem.attrib['width'])
            if 'height' in elem.attrib:
                style += ' height: %spx;' % str(elem.attrib['height'])
            elem.attrib['style'] = style
        return lxml_html.tostring(root).decode()

    @classmethod
    def get_image(cls, image):
        if not image:
            return ''
        b64_image = b64encode(image).decode()
        return 'data:image/png;base64,%s' % b64_image
