# This file is part of lims_report_html module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelSQL, ModelView, fields
from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.cache import Cache

__all__ = ['ReportTemplate', 'ReportTemplateTranslation']


class ReportTemplate(ModelSQL, ModelView):
    'Results Report Template'
    __name__ = 'lims.result_report.template'

    name = fields.Char('Name', required=True)
    content = fields.Text('Content', required=True)
    translations = fields.One2Many('lims.result_report.template.translation',
        'template', 'Translations')
    _translation_cache = Cache('lims.result_report.template.translation',
        size_limit=10240, context=False)

    @classmethod
    def gettext(cls, *args, **variables):
        ReportTemplateTranslation = Pool().get(
            'lims.result_report.template.translation')
        template, src, lang = args
        key = (template, src, lang)
        text = cls._translation_cache.get(key)
        if text is None:
            translations = ReportTemplateTranslation.search([
                ('template', '=', template),
                ('src', '=', src),
                ('lang', '=', lang),
                ], limit=1)
            if translations:
                text = translations[0].value
            else:
                text = src
            cls._translation_cache.set(key, text)
        return text if not variables else text % variables


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
        return super(ReportTemplateTranslation, cls).create(vlist)

    @classmethod
    def write(cls, *args):
        Template = Pool().get('lims.result_report.template')
        Template._translation_cache.clear()
        return super(ReportTemplateTranslation, cls).write(*args)

    @classmethod
    def delete(cls, translations):
        Template = Pool().get('lims.result_report.template')
        Template._translation_cache.clear()
        return super(ReportTemplateTranslation, cls).delete(translations)
