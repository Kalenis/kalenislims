# This file is part of lims_report_html module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from io import BytesIO
from PyPDF2 import PdfFileMerger
from PyPDF2.utils import PdfReadError

from trytond.model import ModelSQL, ModelView, fields
from trytond.pool import Pool
from trytond.pyson import Eval, Bool
from trytond.transaction import Transaction
from trytond.cache import Cache
from trytond.exceptions import UserError
from trytond.i18n import gettext


class ReportTemplate(ModelSQL, ModelView):
    'Results Report Template'
    __name__ = 'lims.result_report.template'
    _history = True

    name = fields.Char('Name', required=True)
    report = fields.Many2One('ir.action.report', 'Report',
        domain=[
            ('report_name', '=', 'lims.result_report'),
            ('template_extension', '!=', 'results'),
            ],
        states={'required': ~Eval('type')}, depends=['type'])
    type = fields.Selection([
        (None, ''),
        ('base', 'HTML'),
        ('header', 'HTML - Header'),
        ('footer', 'HTML - Footer'),
        ], 'Type')
    content = fields.Text('Content',
        states={'required': Bool(Eval('type'))}, depends=['type'])
    header = fields.Many2One('lims.result_report.template', 'Header',
        domain=[('type', '=', 'header')])
    footer = fields.Many2One('lims.result_report.template', 'Footer',
        domain=[('type', '=', 'footer')])
    translations = fields.One2Many('lims.result_report.template.translation',
        'template', 'Translations')
    _translation_cache = Cache('lims.result_report.template.translation',
        size_limit=10240, context=False)
    sections = fields.One2Many('lims.result_report.template.section',
        'template', 'Sections')
    previous_sections = fields.Function(fields.One2Many(
        'lims.result_report.template.section', 'template',
        'Previous Sections', domain=[('position', '=', 'previous')]),
        'get_previous_sections', setter='set_previous_sections')
    following_sections = fields.Function(fields.One2Many(
        'lims.result_report.template.section', 'template',
        'Following Sections', domain=[('position', '=', 'following')]),
        'get_following_sections', setter='set_following_sections')
    trend_charts = fields.One2Many('lims.result_report.template.trend.chart',
        'template', 'Trend Charts')
    charts_x_row = fields.Selection([
        ('1', '1'),
        ('2', '2'),
        ], 'Charts per Row')
    page_orientation = fields.Selection([
        ('portrait', 'Portrait'),
        ('landscape','Landscape'),
        ],'Page orientation',sort=False)
    resultrange_origin = fields.Many2One('lims.range.type', 'Comparison range',
        domain=[('use', '=', 'result_range')])

    @staticmethod
    def default_type():
        return None

    @staticmethod
    def default_charts_x_row():
        return '1'

    @staticmethod
    def default_page_orientation():
        return 'portrait'

    @classmethod
    def view_attributes(cls):
        return super().view_attributes() + [
            ('//page[@id="content"]', 'states', {
                    'invisible': ~Bool(Eval('type')),
                    }),
            ('//page[@id="header_footer"]', 'states', {
                    'invisible': Eval('type') != 'base',
                    }),
            ('//page[@name="translations"]', 'states', {
                    'invisible': ~Bool(Eval('type')),
                    }),
            ('//page[@name="sections"]', 'states', {
                    'invisible': Eval('type') != 'base',
                    }),
            ('//page[@name="trend_charts"]', 'states', {
                    'invisible': Eval('type') != 'base',
                    }),
            ]

    @classmethod
    def gettext(cls, *args, **variables):
        ReportTemplateTranslation = Pool().get(
            'lims.result_report.template.translation')
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
    'Results Report Template Translation'
    __name__ = 'lims.result_report.template.translation'
    _order_name = 'src'

    template = fields.Many2One('lims.result_report.template', 'Template',
        ondelete='CASCADE', select=True, required=True)
    src = fields.Text('Source', required=True)
    value = fields.Text('Translation Value', required=True)
    lang = fields.Selection('get_language', string='Language', required=True)
    _get_language_cache = Cache(
        'lims.result_report.template.translation.get_language')

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
        Template = Pool().get('lims.result_report.template')
        Template._translation_cache.clear()
        return super().create(vlist)

    @classmethod
    def write(cls, *args):
        Template = Pool().get('lims.result_report.template')
        Template._translation_cache.clear()
        return super().write(*args)

    @classmethod
    def delete(cls, translations):
        Template = Pool().get('lims.result_report.template')
        Template._translation_cache.clear()
        return super().delete(translations)


class ReportTemplateSection(ModelSQL, ModelView):
    'Results Report Template Section'
    __name__ = 'lims.result_report.template.section'
    _order_name = 'order'

    template = fields.Many2One('lims.result_report.template', 'Template',
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
    def validate(cls, sections):
        super().validate(sections)
        merger = PdfFileMerger(strict=False)
        for section in sections:
            filedata = BytesIO(section.data)
            try:
                merger.append(filedata)
            except PdfReadError:
                raise UserError(gettext('lims_report_html.msg_section_pdf'))


class ReportTemplateTrendChart(ModelSQL, ModelView):
    'Results Report Template Trend Chart'
    __name__ = 'lims.result_report.template.trend.chart'
    _order_name = 'order'

    template = fields.Many2One('lims.result_report.template', 'Template',
        ondelete='CASCADE', select=True, required=True)
    chart = fields.Many2One('lims.trend.chart', 'Trend Chart',
        required=True, domain=[('active', '=', True)])
    order = fields.Integer('Order')
