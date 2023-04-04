# This file is part of lims_report_html module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import os
import operator
from io import BytesIO
from decimal import Decimal
from datetime import date, datetime
from binascii import b2a_base64
from functools import partial
from PyPDF2 import PdfFileMerger
from PyPDF2.utils import PdfReadError
from jinja2 import contextfilter, Markup
from jinja2 import Environment, FunctionLoader
from lxml import html as lxml_html
from base64 import b64encode
from babel.support import Translations as BabelTranslations
from mimetypes import guess_type as mime_guess_type
from sql import Literal

from trytond.model import ModelSQL, ModelView, DeactivableMixin, fields
from trytond.report import Report
from trytond.pool import Pool
from trytond.pyson import Eval, Bool, Or
from trytond.transaction import Transaction
from trytond.cache import Cache
from trytond.exceptions import UserError
from trytond.i18n import gettext
from trytond.tools import file_open
from trytond import backend
from .generator import PdfGenerator


class ReportTemplate(DeactivableMixin, ModelSQL, ModelView):
    'Report Template'
    __name__ = 'lims.report.template'

    report_name = fields.Char('Internal Name', required=True)
    name = fields.Char('Name', required=True)
    type = fields.Selection([
        (None, ''),
        ('base', 'HTML'),
        ('header', 'HTML - Header'),
        ('footer', 'HTML - Footer'),
        ], 'Type')
    report = fields.Many2One('ir.action.report', 'Report',
        domain=[
            ('report_name', '=', Eval('report_name')),
            ('template_extension', '!=', 'lims'),
            ],
        states={
            'required': ~Eval('type'),
            'invisible': Bool(Eval('type')),
            })
    content = fields.Text('Content',
        states={'required': Bool(Eval('type'))})
    header = fields.Many2One('lims.report.template', 'Header',
        domain=[
            ('report_name', '=', Eval('report_name')),
            ('type', '=', 'header'),
            ['OR', ('active', '=', True),
                ('id', '=', Eval('header', -1))],
            ])
    footer = fields.Many2One('lims.report.template', 'Footer',
        domain=[
            ('report_name', '=', Eval('report_name')),
            ('type', '=', 'footer'),
            ['OR', ('active', '=', True),
                ('id', '=', Eval('footer', -1))],
            ])
    translations = fields.One2Many('lims.report.template.translation',
        'template', 'Translations')
    _translation_cache = Cache('lims.report.template.translation',
        size_limit=10240, context=False)
    sections = fields.One2Many('lims.report.template.section',
        'template', 'Sections')
    previous_sections = fields.Function(fields.One2Many(
        'lims.report.template.section', 'template',
        'Previous Sections', domain=[('position', '=', 'previous')]),
        'get_previous_sections', setter='set_previous_sections')
    following_sections = fields.Function(fields.One2Many(
        'lims.report.template.section', 'template',
        'Following Sections', domain=[('position', '=', 'following')]),
        'get_following_sections', setter='set_following_sections')
    page_orientation = fields.Selection([
        ('portrait', 'Portrait'),
        ('landscape', 'Landscape'),
        ], 'Page orientation', sort=False,
        states={'invisible': Eval('type') != 'base'})

    @classmethod
    def __register__(cls, module_name):
        cursor = Transaction().connection.cursor()
        TableHandler = backend.TableHandler
        sql_table = cls.__table__()

        old_table_exist = TableHandler.table_exist(
            'lims_result_report_template')
        if old_table_exist:
            cursor.execute('ALTER TABLE '
                'lims_result_report_template '
                'RENAME TO lims_report_template')
            cursor.execute('ALTER INDEX '
                'lims_result_report_template_pkey '
                'RENAME TO lims_report_template_pkey')
            cursor.execute('ALTER SEQUENCE '
                'lims_result_report_template_id_seq '
                'RENAME TO lims_report_template_id_seq')

        super().__register__(module_name)

        if old_table_exist:
            cursor.execute(*sql_table.update(
                [sql_table.report_name], ['lims.result_report'],
                where=Literal(True)))

    @staticmethod
    def default_type():
        return None

    @staticmethod
    def default_page_orientation():
        return 'portrait'

    @classmethod
    def view_attributes(cls):
        return super().view_attributes() + [
            ('//page[@name="content"]', 'states', {
                    'invisible': ~Bool(Eval('type')),
                    }),
            ('//page[@id="header_footer"]', 'states', {
                    'invisible': Eval('type') != 'base',
                    }),
            ('//page[@name="translations"]', 'states', {
                    'invisible': ~Bool(Eval('type')),
                    }),
            ]

    @classmethod
    def gettext(cls, *args, **variables):
        ReportTemplateTranslation = Pool().get(
            'lims.report.template.translation')
        template, src, lang = args
        key = (template, src, lang)
        text = cls._translation_cache.get(key)
        if text is None:
            template_ids = [template]
            base = cls(template)
            if base.header:
                template_ids.append(base.header.id)
            if base.footer:
                template_ids.append(base.footer.id)
            translations = ReportTemplateTranslation.search([
                ('template', 'in', template_ids),
                ('src', '=', src),
                ('lang', '=', lang),
                ], limit=1)
            if translations:
                text = translations[0].value
            else:
                text = src
            cls._translation_cache.set(key, text)
        return text if not variables else text % variables

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


class ReportTemplateTranslation(ModelSQL, ModelView):
    'Report Template Translation'
    __name__ = 'lims.report.template.translation'
    _order_name = 'src'

    template = fields.Many2One('lims.report.template', 'Template',
        ondelete='CASCADE', select=True, required=True)
    src = fields.Text('Source', required=True)
    value = fields.Text('Translation Value', required=True)
    lang = fields.Selection('get_language', string='Language', required=True)
    _get_language_cache = Cache(
        'lims.report.template.translation.get_language')

    @classmethod
    def __register__(cls, module_name):
        cursor = Transaction().connection.cursor()
        TableHandler = backend.TableHandler

        old_table_exist = TableHandler.table_exist(
            'lims_result_report_template_translation')
        if old_table_exist:
            cursor.execute('ALTER TABLE '
                'lims_result_report_template_translation '
                'RENAME TO lims_report_template_translation')
            cursor.execute('ALTER INDEX '
                'lims_result_report_template_translation_pkey '
                'RENAME TO lims_report_template_translation_pkey')
            cursor.execute('ALTER INDEX '
                'lims_result_report_template_translation_template_index '
                'RENAME TO lims_report_template_translation_template_index')
            cursor.execute('ALTER SEQUENCE '
                'lims_result_report_template_translation_id_seq '
                'RENAME TO lims_report_template_translation_id_seq')

        super().__register__(module_name)

    @staticmethod
    def default_lang():
        return Transaction().language

    @classmethod
    def get_language(cls):
        result = cls._get_language_cache.get(None)
        if result is not None:
            return result
        langs = Pool().get('ir.lang').search([('translatable', '=', True)])
        result = [(lang.code, lang.name) for lang in langs]
        cls._get_language_cache.set(None, result)
        return result

    @classmethod
    def create(cls, vlist):
        Template = Pool().get('lims.report.template')
        Template._translation_cache.clear()
        return super().create(vlist)

    @classmethod
    def write(cls, *args):
        Template = Pool().get('lims.report.template')
        Template._translation_cache.clear()
        return super().write(*args)

    @classmethod
    def delete(cls, translations):
        Template = Pool().get('lims.report.template')
        Template._translation_cache.clear()
        return super().delete(translations)


class ReportTemplateSection(ModelSQL, ModelView):
    'Report Template Section'
    __name__ = 'lims.report.template.section'
    _order_name = 'order'

    template = fields.Many2One('lims.report.template', 'Template',
        ondelete='CASCADE', select=True, required=True)
    name = fields.Char('Name', required=True)
    data = fields.Binary('File', filename='name', required=True,
        file_id='data_id', store_prefix='results_report_template_section')
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
    def __register__(cls, module_name):
        cursor = Transaction().connection.cursor()
        TableHandler = backend.TableHandler

        old_table_exist = TableHandler.table_exist(
            'lims_result_report_template_section')
        if old_table_exist:
            cursor.execute('ALTER TABLE '
                'lims_result_report_template_section '
                'RENAME TO lims_report_template_section ')
            cursor.execute('ALTER INDEX '
                'lims_result_report_template_section_pkey '
                'RENAME TO lims_report_template_section_pkey')
            cursor.execute('ALTER INDEX '
                'lims_result_report_template_section_template_index '
                'RENAME TO lims_report_template_section_template_index')
            cursor.execute('ALTER SEQUENCE '
                'lims_result_report_template_section_id_seq '
                'RENAME TO lims_report_template_section_id_seq')

        super().__register__(module_name)

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


class LimsReport(Report):

    @classmethod
    def execute_custom_lims_report(cls, ids, data):
        pool = Pool()
        ActionReport = pool.get('ir.action.report')
        cls.check_access()

        action_id = data.get('action_id')
        if action_id is None:
            action_reports = ActionReport.search([
                ('report_name', '=', cls.__name__),
                ('template_extension', '!=', 'lims'),
                ])
            assert action_reports, '%s not found' % cls
            action = action_reports[0]
        else:
            action = ActionReport(action_id)

        records = []
        header = {}
        model = action.model or data.get('model')
        if model:
            records = cls._get_records(ids, model, data)
        oext, content = cls._execute(records, header, data, action)
        if not isinstance(content, str):
            content = bytearray(content) if bytes == str else bytes(content)

        record = records[0]
        if oext == 'pdf' and (record.previous_sections or
                record.following_sections):
            merger = PdfFileMerger(strict=False)
            # Previous Sections
            for section in record.previous_sections:
                filedata = BytesIO(section.data)
                merger.append(filedata)
            # Main Report
            filedata = BytesIO(content)
            merger.append(filedata)
            # Following Sections
            for section in record.following_sections:
                filedata = BytesIO(section.data)
                merger.append(filedata)
            output = BytesIO()
            merger.write(output)
            content = output.getvalue()

        return (oext, content, action.direct_print, action.name)

    @classmethod
    def execute_html_lims_report(cls, ids, data):
        pool = Pool()
        ActionReport = pool.get('ir.action.report')
        cls.check_access()

        action_reports = ActionReport.search([
            ('report_name', '=', cls.__name__),
            ('template_extension', '=', 'lims'),
            ])
        assert action_reports, '%s not found' % cls
        action = action_reports[0]

        records = []
        model = action.model or data.get('model')
        if model:
            records = cls._get_records(ids, model, data)
        oext, content = cls._execute_html_lims_report(records, data, action)
        if not isinstance(content, str):
            content = bytearray(content) if bytes == str else bytes(content)
        return (oext, content, action.direct_print, action.name)

    @classmethod
    def _execute_html_lims_report(cls, records, data, action):
        record = records[0]
        template_id, tcontent, theader, tfooter = (
            cls.get_lims_template(action, record))
        context = Transaction().context
        context['template'] = template_id
        if not template_id:
            context['default_translations'] = os.path.join(
                os.path.dirname(__file__), 'report', 'translations')
        with Transaction().set_context(**context):
            content = cls.render_lims_template(action,
                tcontent, record=record, records=[record],
                data=data)
            header = theader and cls.render_lims_template(action,
                theader, record=record, records=[record],
                data=data)
            footer = tfooter and cls.render_lims_template(action,
                tfooter, record=record, records=[record],
                data=data)

        stylesheets = cls.parse_stylesheets(tcontent)
        if theader:
            stylesheets += cls.parse_stylesheets(theader)
        if tfooter:
            stylesheets += cls.parse_stylesheets(tfooter)

        page_orientation = (record.template and
            record.template.page_orientation or 'portrait')

        document = PdfGenerator(content,
            header_html=header, footer_html=footer,
            side_margin=1, extra_vertical_margin=30,
            stylesheets=stylesheets,
            page_orientation=page_orientation).render_html().write_pdf()

        if record.previous_sections or record.following_sections:
            merger = PdfFileMerger(strict=False)
            # Previous Sections
            for section in record.previous_sections:
                filedata = BytesIO(section.data)
                merger.append(filedata)
            # Main Report
            filedata = BytesIO(document)
            merger.append(filedata)
            # Following Sections
            for section in record.following_sections:
                filedata = BytesIO(section.data)
                merger.append(filedata)
            output = BytesIO()
            merger.write(output)
            merger.close()
            document = output.getvalue()
            output.close()

        return 'pdf', document

    @classmethod
    def get_lims_template(cls, action, record):
        template_id, content, header, footer = None, None, None, None
        if record.template:
            template_id = record.template
            content = '<body>%s</body>' % record.template.content
            header = (record.template.header and
                '<header id="header">%s</header>' %
                    record.template.header.content)
            footer = (record.template.footer and
                '<footer id="footer">%s</footer>' %
                    record.template.footer.content)
        if not content:
            content = (action.report_content and
                action.report_content.decode('utf-8'))
            if not content:
                raise UserError(gettext('lims_report_html.msg_no_template'))
        return template_id, content, header, footer

    @classmethod
    def render_lims_template(cls, action, template_string,
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
            env = cls.get_lims_environment()

        header = {}
        report_template = env.from_string(template_string)
        context = cls.get_context(records, header, data=data)
        context.update({
            'report': action,
            'get_image': cls.get_image,
            'operation': cls.operation,
            })
        res = report_template.render(**context)
        res = cls.parse_images(res)
        # print('TEMPLATE:\n', res)
        return res

    @classmethod
    def get_lims_environment(cls):
        extensions = ['jinja2.ext.i18n', 'jinja2.ext.autoescape',
            'jinja2.ext.with_', 'jinja2.ext.loopcontrols', 'jinja2.ext.do']
        env = Environment(extensions=extensions,
            loader=FunctionLoader(lambda name: ''))

        env.filters.update(cls.get_lims_filters())

        locale = Transaction().context.get('locale').split('_')[0]
        translations = TemplateTranslations(locale)
        env.install_gettext_translations(translations)
        return env

    @classmethod
    def get_lims_filters(cls):
        Lang = Pool().get('ir.lang')

        def module_path(name):
            module, path = name.split('/', 1)
            with file_open(os.path.join(module, path)) as f:
                return 'file://%s' % f.name

        def render(value, digits=2, lang=None, filename=None):
            if value is None or value == '':
                return ''

            if isinstance(value, (float, Decimal)):
                return lang.format('%.*f', (digits, value), grouping=True)

            if isinstance(value, int):
                return lang.format('%d', value, grouping=True)

            if isinstance(value, bool):
                if value:
                    return gettext('lims_report_html.msg_yes')
                return gettext('lims_report_html.msg_no')

            if hasattr(value, 'rec_name'):
                return value.rec_name

            if isinstance(value, date):
                return lang.strftime(value)

            if isinstance(value, datetime):
                return '%s %s' % (lang.strftime(value),
                    value.strftime('%H:%M:%S'))

            if isinstance(value, str):
                return value.replace('\n', '<br/>')

            if isinstance(value, bytes):
                b64_value = b2a_base64(value).decode('ascii')
                mimetype = 'image/png'
                if filename:
                    mimetype = mime_guess_type(filename)[0]
                return ('data:%s;base64,%s' % (mimetype, b64_value)).strip()
            return value

        @contextfilter
        def subrender(context, value, subobj=None):
            if value is None or value == '':
                return ''
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

        locale = Transaction().context.get('locale').split('_')[0]
        lang, = Lang.search([('code', '=', locale or 'en')])

        return {
            'modulepath': module_path,
            'render': partial(render, lang=lang),
            'subrender': subrender,
            }

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
    def operation(cls, function, value1, value2):
        return getattr(operator, function)(value1, value2)

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
        ReportTemplate = Pool().get('lims.report.template')
        if self.current:
            return self.current.ugettext(message)
        elif self.template:
            return ReportTemplate.gettext(self.template, message,
                self.language)
        return message

    def ngettext(self, singular, plural, n):
        ReportTemplate = Pool().get('lims.report.template')
        if self.current:
            return self.current.ugettext(singular, plural, n)
        elif self.template:
            return ReportTemplate.gettext(self.template, singular,
                self.language)
        return singular


class ResultsReportTemplate(ReportTemplate):
    __name__ = 'lims.report.template'

    trend_charts = fields.One2Many('lims.report.template.trend.chart',
        'template', 'Trend Charts')
    charts_x_row = fields.Selection([
        ('1', '1'),
        ('2', '2'),
        ], 'Charts per Row')
    resultrange_origin = fields.Many2One('lims.range.type', 'Comparison range',
        domain=[('use', '=', 'result_range')],
        states={
            'invisible': Or(
                Eval('type') != 'base',
                Eval('report_name') != 'lims.result_report',
                ),
            })

    @staticmethod
    def default_charts_x_row():
        return '1'

    @classmethod
    def view_attributes(cls):
        return super().view_attributes() + [
            ('//page[@name="trend_charts"]', 'states', {
                    'invisible': Or(
                        Eval('type') != 'base',
                        Eval('report_name') != 'lims.result_report',
                        )
                    }),
            ]


class ResultsReportTemplateTrendChart(ModelSQL, ModelView):
    'Results Report Template Trend Chart'
    __name__ = 'lims.report.template.trend.chart'
    _order_name = 'order'

    template = fields.Many2One('lims.report.template', 'Template',
        ondelete='CASCADE', select=True, required=True)
    chart = fields.Many2One('lims.trend.chart', 'Trend Chart',
        required=True, domain=[('active', '=', True)])
    order = fields.Integer('Order')

    @classmethod
    def __register__(cls, module_name):
        cursor = Transaction().connection.cursor()
        TableHandler = backend.TableHandler

        old_table_exist = TableHandler.table_exist(
            'lims_result_report_template_trend_chart')
        if old_table_exist:
            cursor.execute('ALTER TABLE '
                'lims_result_report_template_trend_chart '
                'RENAME TO lims_report_template_trend_chart ')
            cursor.execute('ALTER INDEX '
                'lims_result_report_template_trend_chart_pkey '
                'RENAME TO lims_report_template_trend_chart_pkey')
            cursor.execute('ALTER INDEX '
                'lims_result_report_template_trend_chart_template_index '
                'RENAME TO lims_report_template_trend_chart_template_index')
            cursor.execute('ALTER SEQUENCE '
                'lims_result_report_template_trend_chart_id_seq '
                'RENAME TO lims_report_template_trend_chart_id_seq')

        super().__register__(module_name)
