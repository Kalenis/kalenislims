# This file is part of lims_report_html module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import os
from lxml import html as lxml_html
from base64 import b64encode
from babel.support import Translations as BabelTranslations
from jinja2 import contextfilter, Markup
from io import BytesIO
from PyPDF2 import PdfFileMerger
from PyPDF2.utils import PdfReadError

from trytond.model import ModelView, ModelSQL, fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.i18n import gettext
from trytond.modules.html_report.generator import PdfGenerator

__all__ = ['ResultsReportVersionDetail', 'ResultsReportVersionDetailSection',
    'ResultsReportVersionDetailTrendChart',
    'ResultsReportVersionDetailSample', 'ResultReport']


class ResultsReportVersionDetail(metaclass=PoolMeta):
    __name__ = 'lims.results_report.version.detail'

    template = fields.Many2One('lims.result_report.template',
        'Report Template', domain=[('type', '=', 'base')],
        states={'readonly': Eval('state') != 'draft'}, depends=['state'])
    sections = fields.One2Many('lims.results_report.version.detail.section',
        'version_detail', 'Sections')
    previous_sections = fields.Function(fields.One2Many(
        'lims.results_report.version.detail.section', 'version_detail',
        'Previous Sections', domain=[('position', '=', 'previous')]),
        'get_previous_sections', setter='set_previous_sections')
    following_sections = fields.Function(fields.One2Many(
        'lims.results_report.version.detail.section', 'version_detail',
        'Following Sections', domain=[('position', '=', 'following')]),
        'get_following_sections', setter='set_following_sections')
    trend_charts = fields.One2Many(
        'lims.results_report.version.detail.trend.chart',
        'version_detail', 'Trend Charts')
    charts_x_row = fields.Selection([
        ('1', '1'),
        ('2', '2'),
        ], 'Charts per Row')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        if 'invisible' in cls.resultrange_origin.states:
            del cls.resultrange_origin.states['invisible']
        if 'required' in cls.resultrange_origin.states:
            del cls.resultrange_origin.states['required']

    @staticmethod
    def default_charts_x_row():
        return '1'

    @fields.depends('template', '_parent_template.trend_charts',
        '_parent_template.sections')
    def on_change_template(self):
        if self.template and self.template.trend_charts:
            self.trend_charts = [{
                'chart': c.chart.id,
                'order': c.order,
                } for c in self.template.trend_charts]
            self.charts_x_row = self.template.charts_x_row
        if self.template and self.template.sections:
            self.sections = [{
                'name': s.name,
                'data': s.data,
                'data_id': s.data_id,
                'position': s.position,
                'order': s.order,
                } for s in self.template.sections]

    def get_previous_sections(self, name):
        return [s.id for s in self.sections if s.position == 'previous']

    @classmethod
    def set_previous_sections(cls, sections, name, value):
        if not value:
            return
        cls.write(sections, {'sections': value})

    def get_following_sections(self, name):
        return [s.id for s in self.sections if s.position == 'following']

    @classmethod
    def set_following_sections(cls, sections, name, value):
        if not value:
            return
        cls.write(sections, {'sections': value})

    @classmethod
    def _get_fields_from_samples(cls, samples):
        Notebook = Pool().get('lims.notebook')
        detail_default = super()._get_fields_from_samples(samples)
        for sample in samples:
            notebook = Notebook(sample['notebook'])
            result_template = notebook.fraction.sample.result_template
            if result_template:
                detail_default['template'] = result_template.id
                if result_template.trend_charts:
                    detail_default['trend_charts'] = [('create', [{
                        'chart': c.chart.id,
                        'order': c.order,
                        } for c in result_template.trend_charts])]
                    detail_default['charts_x_row'] = (
                        result_template.charts_x_row)
                if result_template.sections:
                    detail_default['sections'] = [('create', [{
                        'name': s.name,
                        'data': s.data,
                        'data_id': s.data_id,
                        'position': s.position,
                        'order': s.order,
                        } for s in result_template.sections])]
            resultrange_origin = notebook.fraction.sample.resultrange_origin
            if resultrange_origin:
                detail_default['resultrange_origin'] = resultrange_origin.id
        return detail_default

    @classmethod
    def _get_fields_from_detail(cls, detail):
        detail_default = super()._get_fields_from_detail(detail)
        if detail.template:
            detail_default['template'] = detail.template.id
        if detail.trend_charts:
            detail_default['trend_charts'] = [('create', [{
                'chart': c.chart.id,
                'order': c.order,
                } for c in detail.trend_charts])]
            detail_default['charts_x_row'] = detail.charts_x_row
        if detail.sections:
            detail_default['sections'] = [('create', [{
                'name': s.name,
                'data': s.data,
                'data_id': s.data_id,
                'position': s.position,
                'order': s.order,
                } for s in detail.sections])]
        return detail_default


class ResultsReportVersionDetailSection(ModelSQL, ModelView):
    'Results Report Version Detail Section'
    __name__ = 'lims.results_report.version.detail.section'
    _order_name = 'order'

    version_detail = fields.Many2One('lims.results_report.version.detail',
        'Report Detail', ondelete='CASCADE', select=True, required=True)
    name = fields.Char('Name', required=True)
    data = fields.Binary('File', filename='name', required=True,
        file_id='data_id', store_prefix='results_report_section')
    data_id = fields.Char('File ID', readonly=True)
    position = fields.Selection([
        ('previous', 'Previous'),
        ('following', 'Following'),
        ], 'Position', required=True)
    order = fields.Integer('Order')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order.insert(0, ('order', 'ASC'))

    @classmethod
    def validate(cls, sections):
        super().validate(sections)
        merger = PdfFileMerger(strict=False)
        for section in sections:
            filedata = BytesIO(section.data)
            try:
                merger.append(filedata)
            except PdfReadError:
                raise UserError(gettext('lims_report_html.msg_section_pdf'))


class ResultsReportVersionDetailTrendChart(ModelSQL, ModelView):
    'Results Report Version Detail Trend Chart'
    __name__ = 'lims.results_report.version.detail.trend.chart'
    _order_name = 'order'

    version_detail = fields.Many2One('lims.results_report.version.detail',
        'Report Detail', ondelete='CASCADE', select=True, required=True)
    chart = fields.Many2One('lims.trend.chart', 'Trend Chart',
        required=True, domain=[('active', '=', True)])
    order = fields.Integer('Order')


class ResultsReportVersionDetailSample(metaclass=PoolMeta):
    __name__ = 'lims.results_report.version.detail.sample'

    trend_charts = fields.Function(fields.Text('Trend Charts'),
        'get_trend_charts')

    def get_trend_charts(self, name):
        pool = Pool()
        OpenTrendChart = pool.get('lims.trend.chart.open', type='wizard')
        ResultReport = pool.get('lims.result_report', type='report')

        if not self.version_detail.trend_charts:
            return ''

        charts = []
        for tc in self.version_detail.trend_charts:
            session_id, _, _ = OpenTrendChart.create()
            open_chart = OpenTrendChart(session_id)
            open_chart.start.chart = tc.chart
            open_chart.start.notebook = self.notebook
            open_chart.transition_compute()
            plot = tc.chart.get_plot(session_id)
            charts.append(plot)

        div_row = '<div>'
        charts_x_row = int(self.version_detail.charts_x_row) or 1
        if charts_x_row == 1:
            div_col = '<div style="float:left; width:100%;">'
        elif charts_x_row == 2:
            div_col = '<div style="float:left; width:50%;">'
        end_div = '</div>'

        content = '<div>'
        count = 0
        for chart in charts:
            if count == 0:
                content += div_row

            content += div_col
            content += ('<img src="' +
                ResultReport.get_image(chart) +
                '" alt="" style="width:100%;">')
            content += end_div

            count += 1
            if count == charts_x_row:
                content += end_div
                count = 0
        if count != 0:
            content += end_div

        content += end_div
        return content


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

        records = []
        if model:
            records = cls._get_records(ids, model, data)
        oext, content = cls._execute_html_results_report(records, data, action)
        if not isinstance(content, str):
            content = bytearray(content) if bytes == str else bytes(content)

        return oext, content, cls.get_direct_print(action), cls.get_name(
            action)

    @classmethod
    def _execute_html_results_report(cls, records, data, action):
        record = records[0]
        template_id, tcontent, theader, tfooter = (
            cls.get_results_report_template(action, record.id))
        context = Transaction().context
        context['template'] = template_id
        if not template_id:
            context['default_translations'] = os.path.join(
                os.path.dirname(__file__), 'report', 'translations')
        with Transaction().set_context(**context):
            content = cls.render_results_report_template(action,
                tcontent, record=record, records=[record],
                data=data)
            header = theader and cls.render_results_report_template(action,
                theader, record=record, records=[record],
                data=data)
            footer = tfooter and cls.render_results_report_template(action,
                tfooter, record=record, records=[record],
                data=data)
        stylesheets = cls.parse_stylesheets(tcontent)
        if theader:
            stylesheets += cls.parse_stylesheets(theader)
        if tfooter:
            stylesheets += cls.parse_stylesheets(tfooter)

        document = PdfGenerator(content,
            header_html=header, footer_html=footer,
            side_margin=1, extra_vertical_margin=30,
            stylesheets=stylesheets).render_html().write_pdf()

        if record.previous_sections or record.following_sections:
            merger = PdfFileMerger(strict=False)
            # Previous Sections
            for section in record.previous_sections:
                filedata = BytesIO(section.data)
                merger.append(filedata)
            # Results Report
            filedata = BytesIO(document)
            merger.append(filedata)
            # Following Sections
            for section in record.following_sections:
                filedata = BytesIO(section.data)
                merger.append(filedata)
            output = BytesIO()
            merger.write(output)
            document = output.getvalue()

        return 'pdf', document

    @classmethod
    def get_results_report_template(cls, action, detail_id):
        ResultsDetail = Pool().get('lims.results_report.version.detail')
        template_id, content, header, footer = None, None, None, None
        detail = ResultsDetail(detail_id)
        if detail.template:
            template_id = detail.template
            content = '<body>%s</body>' % detail.template.content
            header = (detail.template.header and
                '<header id="header">%s</header>' %
                    detail.template.header.content)
            footer = (detail.template.footer and
                '<footer id="footer">%s</footer>' %
                    detail.template.footer.content)
        if not content:
            content = (action.report_content and
                action.report_content.decode('utf-8'))
            if not content:
                raise UserError(gettext('lims_report_html.msg_no_template'))
        return template_id, content, header, footer

    @classmethod
    def render_results_report_template(cls, action, template_string,
            record=None, records=None, data=None):
        User = Pool().get('res.user')
        user = User(Transaction().user)

        if data and data.get('alt_lang'):
            locale = data['alt_lang']
        elif user.language:
            locale = user.language.code
        else:
            locale = Transaction().language
        with Transaction().set_context(locale=locale):
            env = cls.get_results_report_environment()

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
    def get_results_report_environment(cls):
        env = cls.get_environment()
        env.filters.update(cls.get_results_report_filters())

        context = Transaction().context
        locale = context.get('locale').split('_')[0]
        translations = TemplateTranslations(locale)
        env.install_gettext_translations(translations)
        return env

    @classmethod
    def get_results_report_filters(cls):

        @contextfilter
        def subrender(context, value, subobj=None):
            _template = context.eval_ctx.environment.from_string(value)
            if subobj:
                new_context = {'subobj': subobj}
                new_context.update(context)
            else:
                new_context = context
            result = _template.render(**new_context)
            if context.eval_ctx.autoescape:
                result = Markup(result)
            return result

        return {'subrender': subrender}

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
            # get image from TinyMCE widget
            elif 'data-mce-src' in elem.attrib:
                elem.attrib['src'] = elem.attrib['data-mce-src']
                del elem.attrib['data-mce-src']
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

    @classmethod
    def parse_stylesheets(cls, template_string):
        Attachment = Pool().get('ir.attachment')
        root = lxml_html.fromstring(template_string)
        res = []
        # get stylesheets from attachments
        elems = root.xpath("//div[@id='tryton_styles_container']/div")
        for elem in elems:
            css = Attachment.search([('id', '=', int(elem.attrib['id']))])
            if not css:
                continue
            res.append(css[0].data)
        return res


class TemplateTranslations:

    def __init__(self, lang='en'):
        self.cache = {}
        self.env = None
        self.current = None
        self.language = lang
        self.template = None
        self.set_language(lang)

    def set_language(self, lang='en'):
        self.language = lang
        if lang in self.cache:
            self.current = self.cache[lang]
            return
        context = Transaction().context
        if context.get('default_translations'):
            default_translations = context['default_translations']
            if os.path.isdir(default_translations):
                self.current = BabelTranslations.load(
                    dirname=default_translations, locales=[lang])
                self.cache[lang] = self.current
        else:
            self.template = context.get('template', -1)

    def ugettext(self, message):
        ReportTemplate = Pool().get('lims.result_report.template')
        if self.current:
            return self.current.ugettext(message)
        elif self.template:
            return ReportTemplate.gettext(self.template, message,
                self.language)
        return message

    def ngettext(self, singular, plural, n):
        ReportTemplate = Pool().get('lims.result_report.template')
        if self.current:
            return self.current.ugettext(singular, plural, n)
        elif self.template:
            return ReportTemplate.gettext(self.template, singular,
                self.language)
        return singular
