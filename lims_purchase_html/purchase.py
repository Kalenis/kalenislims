# This file is part of lims_purchase_html module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import logging
from io import BytesIO
from PyPDF2 import PdfFileMerger
from PyPDF2.errors import PdfReadError

from trytond.model import ModelSQL, ModelView, fields
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Eval
from trytond.exceptions import UserError
from trytond.i18n import gettext
from trytond.modules.lims_report_html.html_template import LimsReport

logger = logging.getLogger(__name__)


class Purchase(metaclass=PoolMeta):
    __name__ = 'purchase.purchase'

    template = fields.Many2One('lims.report.template',
        'Purchase Template', domain=[
            ('report_name', '=', 'purchase.purchase'),
            ('type', 'in', [None, 'base']),
            ['OR', ('active', '=', True),
                ('id', '=', Eval('template', -1))],
            ],
        states={'readonly': Eval('state') != 'draft'})
    clause_template = fields.Many2One('purchase.clause.template',
        'Clauses Template',
        states={'readonly': Eval('state') != 'draft'})
    sections = fields.One2Many('purchase.purchase.section', 'purchase',
        'Sections')
    previous_sections = fields.Function(fields.One2Many(
        'purchase.purchase.section', 'purchase', 'Previous Sections',
        domain=[('position', '=', 'previous')]),
        'get_previous_sections', setter='set_previous_sections')
    following_sections = fields.Function(fields.One2Many(
        'purchase.purchase.section', 'purchase', 'Following Sections',
        domain=[('position', '=', 'following')]),
        'get_following_sections', setter='set_following_sections')
    clauses = fields.Text('Clauses',
        states={'readonly': Eval('state') != 'draft'})

    @staticmethod
    def default_template():
        Configuration = Pool().get('purchase.configuration')
        config = Configuration(1)
        if config.default_template:
            return config.default_template.id
        return None

    @fields.depends('template', '_parent_template.sections', 'sections',
        '_parent_template.clause_template',
        methods=['on_change_clause_template'])
    def on_change_template(self):
        if self.template and self.template.sections:
            sections = {}
            for s in self.sections + self.template.sections:
                sections[s.name] = {
                    'name': s.name,
                    'data': s.data,
                    'data_id': s.data_id,
                    'position': s.position,
                    'order': s.order,
                    }
            self.sections = sections.values()
        if self.template and self.template.clause_template:
            self.clause_template = self.template.clause_template
            self.on_change_clause_template()

    @fields.depends('clause_template', '_parent_clause_template.content')
    def on_change_clause_template(self):
        if self.clause_template:
            self.clauses = self.clause_template.content

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


class PurchaseSection(ModelSQL, ModelView):
    'Purchase Section'
    __name__ = 'purchase.purchase.section'
    _order_name = 'order'

    purchase = fields.Many2One('purchase.purchase', 'Purchase',
        ondelete='CASCADE', required=True)
    name = fields.Char('Name', required=True)
    data = fields.Binary('File', filename='name', required=True,
        file_id='data_id', store_prefix='purchase_section')
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


class PurchaseReport(LimsReport, metaclass=PoolMeta):
    __name__ = 'purchase.purchase'

    @classmethod
    def execute(cls, ids, data):
        Purchase = Pool().get('purchase.purchase')

        if data is None:
            data = {}
        current_data = data.copy()

        if len(ids) > 1:
            raise UserError(gettext(
                'lims_report_html.msg_print_multiple_record'))

        purchase = Purchase(ids[0])
        template = purchase.template
        if template and template.type == 'base':  # HTML
            result = cls.execute_html_lims_report(ids, current_data)
        else:
            current_data['action_id'] = None
            if template and template.report:
                current_data['action_id'] = template.report.id
            result = cls.execute_custom_lims_report(ids, current_data)

        return result

    @classmethod
    def get_context(cls, records, header, data):
        current_header = header.copy()
        current_header['company'] = records[0].company
        return super().get_context(records, current_header, data)
