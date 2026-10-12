# This file is part of lims_diagnosis module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

import re
from jinja2 import TemplateSyntaxError

from trytond.model import ModelSQL, ModelView, DeactivableMixin, fields, \
    DictSchemaMixin
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.i18n import gettext

_EXPRESSION = re.compile(r'{{.*?}}', re.DOTALL)


def check_template_syntax(record, text):
    if not text or not any(t in text for t in ('{{', '{%', '{#')):
        return
    ResultReport = Pool().get('lims.result_report', type='report')
    with Transaction().set_context(locale=Transaction().language):
        env = ResultReport.get_lims_environment()
    try:
        env.from_string(text)
    except TemplateSyntaxError as e:
        expression = _get_invalid_expression(env, text)
        if expression:
            raise UserError(gettext(
                'lims_diagnosis.msg_invalid_template_expression',
                record=record.rec_name, expression=expression,
                error=e.message))
        raise UserError(gettext('lims_diagnosis.msg_invalid_template_syntax',
            record=record.rec_name, error=e.message))


def _get_invalid_expression(env, text):
    for match in _EXPRESSION.finditer(text):
        try:
            env.from_string(match.group())
        except TemplateSyntaxError:
            return match.group()


class DiagnosisTemplate(DeactivableMixin, ModelSQL, ModelView):
    'Diagnosis Template'
    __name__ = 'lims.diagnosis.template'

    name = fields.Char('Name', required=True)
    content = fields.Text('Content', required=True)
    diagnosis_states = fields.Many2Many(
        'lims.diagnosis.template-diagnosis.state',
        'template', 'state', 'States')

    @classmethod
    def validate(cls, templates):
        super().validate(templates)
        for template in templates:
            check_template_syntax(template, template.content)


class DiagnosisState(DictSchemaMixin, ModelSQL, ModelView):
    'Diagnosis State'
    __name__ = 'lims.diagnosis.state'
    _rec_name = 'name'

    images = fields.One2Many('lims.diagnosis.state.image',
        'state', 'Images')

    @staticmethod
    def default_type_():
        return 'selection'


class DiagnosisStateImage(ModelSQL, ModelView):
    'Diagnosis State Image'
    __name__ = 'lims.diagnosis.state.image'

    state = fields.Many2One('lims.diagnosis.state', 'State',
        required=True, ondelete='CASCADE', select=True)
    name = fields.Char('Name', required=True)
    image = fields.Binary('Image', required=True)


class DiagnosisTemplateState(ModelSQL):
    'Diagnosis Template - State'
    __name__ = 'lims.diagnosis.template-diagnosis.state'
    _table = 'lims_diagnosis_template_diagnosis_state'

    template = fields.Many2One('lims.diagnosis.template', 'Template',
        required=True, ondelete='CASCADE', select=True)
    state = fields.Many2One('lims.diagnosis.state', 'State',
        required=True, ondelete='CASCADE', select=True)


class ResultsReportTemplate(metaclass=PoolMeta):
    __name__ = 'lims.report.template'

    diagnosis_template = fields.Many2One('lims.diagnosis.template',
        'Diagnosis Template', domain=['OR', ('active', '=', True),
            ('id', '=', Eval('diagnosis_template'))],
        states={'invisible': Eval('type') != 'base'},
        depends=['type'])
    diagnosis_length = fields.Integer('Diagnosis Length',
        states={'invisible': Eval('type') != 'base'},
        depends=['type'],
        help='Maximum number of characters in diagnosis')
