# This file is part of lims_report_html module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from io import BytesIO
from PyPDF2 import PdfFileMerger
from PyPDF2.utils import PdfReadError

from trytond.model import ModelView, ModelSQL, fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, Not, Bool
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.i18n import gettext
from .html_template import LimsReport


class ResultsReportVersionDetail(metaclass=PoolMeta):
    __name__ = 'lims.results_report.version.detail'

    template = fields.Many2One('lims.report.template',
        'Report Template', domain=[
            ('report_name', '=', 'lims.result_report'),
            ('type', 'in', [None, 'base']),
            ],
        states={'readonly': Eval('state') != 'draft'},
        depends=['state'])
    template_type = fields.Function(fields.Selection([
        (None, ''),
        ('base', 'HTML'),
        ('header', 'HTML - Header'),
        ('footer', 'HTML - Footer'),
        ], 'Report Template Type'), 'get_template_type')
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
    comments_plain = fields.Function(fields.Text('Comments', translate=True),
        'get_comments_plain', setter='set_comments_plain')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        if 'invisible' in cls.resultrange_origin.states:
            del cls.resultrange_origin.states['invisible']
        if 'required' in cls.resultrange_origin.states:
            del cls.resultrange_origin.states['required']

    @classmethod
    def view_attributes(cls):
        return super().view_attributes() + [
            ('//page[@id="comments"]', 'states', {
                    'invisible': Not(Bool(Eval('template_type'))),
                    }),
            ('//page[@id="comments_plain"]', 'states', {
                    'invisible': Eval('template_type') == 'base',
                    }),
            ]

    @staticmethod
    def default_charts_x_row():
        return '1'

    def get_template_type(self, name):
        return self.template and self.template.type or None

    @fields.depends('template', '_parent_template.trend_charts',
        '_parent_template.sections', 'sections', 'resultrange_origin')
    def on_change_template(self):
        if (self.template and self.template.resultrange_origin and
                not self.resultrange_origin):
            self.resultrange_origin = self.template.resultrange_origin.id
        if self.template and self.template.trend_charts:
            self.trend_charts = [{
                'chart': c.chart.id,
                'order': c.order,
                } for c in self.template.trend_charts]
            self.charts_x_row = self.template.charts_x_row
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
    def _get_fields_from_samples(cls, samples, generate_report_form=None):
        pool = Pool()
        Notebook = pool.get('lims.notebook')

        detail_default = super()._get_fields_from_samples(samples,
            generate_report_form)

        result_template = None
        if generate_report_form and generate_report_form.template:
            result_template = generate_report_form.template
        resultrange_origin = None

        for sample in samples:
            nb = Notebook(sample['notebook'])
            if not result_template:
                result_template = cls._get_result_template_from_sample(nb)
            if not resultrange_origin:
                resultrange_origin = nb.fraction.sample.resultrange_origin

        if result_template:
            detail_default['template'] = result_template.id
            if not resultrange_origin:
                resultrange_origin = result_template.resultrange_origin
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

        if resultrange_origin:
            detail_default['resultrange_origin'] = resultrange_origin.id

        return detail_default

    @classmethod
    def _get_result_template_from_sample(cls, notebook):
        Service = Pool().get('lims.service')
        result_template = notebook.fraction.sample.result_template
        if not result_template:
            ok = True
            services = Service.search([
                ('fraction', '=', notebook.fraction),
                ('analysis.type', '=', 'group'),
                ('annulled', '=', False),
                ])
            for service in services:
                if service.analysis.result_template:
                    if not result_template:
                        result_template = service.analysis.result_template
                    elif result_template != service.analysis.result_template:
                        ok = False
                elif result_template:
                    ok = False
            if not ok:
                result_template = None
        return result_template

    @classmethod
    def _get_fields_not_overwrite(cls):
        fields = super()._get_fields_not_overwrite()
        fields.extend(['template', 'trend_charts', 'charts_x_row',
            'sections', 'resultrange_origin'])
        return fields

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

    def get_comments_plain(self, name):
        return self.comments

    @classmethod
    def set_comments_plain(cls, records, name, value):
        cls.write(records, {'comments': value})


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
    attachments = fields.Function(fields.Text('Attachments'),
        'get_attachments')

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

        div_row = '<div style="clear:both;">'
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

    def get_trend_charts_odt(self):
        pool = Pool()
        OpenTrendChart = pool.get('lims.trend.chart.open', type='wizard')

        if not self.version_detail.trend_charts:
            return []

        charts = []
        for tc in self.version_detail.trend_charts:
            session_id, _, _ = OpenTrendChart.create()
            open_chart = OpenTrendChart(session_id)
            open_chart.start.chart = tc.chart
            open_chart.start.notebook = self.notebook
            open_chart.transition_compute()
            plot = tc.chart.get_plot(session_id)
            charts.append(plot)
        return charts

    def _get_resource(self, obj):
        return '%s,%s' % (obj.__name__, obj.id)

    def get_attachments(self, name):
        pool = Pool()
        Attachment = pool.get('ir.attachment')
        ResultReport = pool.get('lims.result_report', type='report')

        resources = []
        resources.append(self._get_resource(self))
        resources.append(self._get_resource(self.notebook))
        resources.append(self._get_resource(self.notebook.fraction))
        resources.append(self._get_resource(
            self.notebook.fraction.sample))
        resources.append(self._get_resource(
            self.notebook.fraction.sample.entry))
        for line in self.notebook_lines:
            resources.append(self._get_resource(line))
            resources.append(self._get_resource(line.notebook_line))

        attachments = Attachment.search([
            ('resource', 'in', resources),
            ])

        div_row = '<div>'
        div_col = '<div style="float:left; width:50%;">'
        end_div = '</div>'

        content = '<div>'
        count = 0
        extensions = ['png', 'jpg']
        for attachment in attachments:
            if not any(x in attachment.name.lower() for x in extensions):
                continue

            if count == 0:
                content += div_row

            content += div_col

            if attachment.title:
                content += '<p style="font-size: 6pt;font-family: arial,\
                    helvetica, sans-serif;">%s</p>' % (
                        attachment.title, )

            content += ('<img src="' +
                ResultReport.get_image(attachment.data) +
                '" alt="" style="width:100%;">')
            content += end_div

            count += 1
            if count == 2:
                content += end_div
                count = 0
        if count != 0:
            content += end_div

        content += end_div
        return content


class ResultReport(LimsReport, metaclass=PoolMeta):
    __name__ = 'lims.result_report'

    @classmethod
    def execute(cls, ids, data):
        ResultsDetail = Pool().get('lims.results_report.version.detail')

        if data is None:
            data = {}
        current_data = data.copy()

        if len(ids) > 1:
            raise UserError(gettext(
                'lims_report_html.msg_print_multiple_record'))

        results_report = ResultsDetail(ids[0])
        if results_report.state == 'annulled':
            raise UserError(gettext('lims.msg_annulled_report'))

        template = results_report.template
        if template and template.type == 'base':  # HTML
            current_data['alt_lang'] = None
            result_orig = cls.execute_html_lims_report(ids, current_data)
            current_data['alt_lang'] = 'en'
            result_eng = cls.execute_html_lims_report(ids, current_data)
        else:
            current_data['action_id'] = None
            if template and template.report:
                current_data['action_id'] = template.report.id
            current_data['alt_lang'] = None
            result_orig = cls.execute_custom_lims_report(ids, current_data)
            current_data['alt_lang'] = 'en'
            result_eng = cls.execute_custom_lims_report(ids, current_data)

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


class GenerateReportStart(metaclass=PoolMeta):
    __name__ = 'lims.notebook.generate_results_report.start'

    template = fields.Many2One('lims.report.template',
        'Report Template', domain=[
            ('report_name', '=', 'lims.result_report'),
            ('type', 'in', [None, 'base']),
            ],
        states={'readonly': Bool(Eval('report'))},
        depends=['report'])


class GenerateReport(metaclass=PoolMeta):
    __name__ = 'lims.notebook.generate_results_report'

    def default_start(self, fields):
        pool = Pool()
        Notebook = pool.get('lims.notebook')

        res = super().default_start(fields)
        res['template'] = None

        if res['report']:
            return res

        template = None
        for notebook in Notebook.browse(Transaction().context['active_ids']):
            if not notebook.fraction.sample.result_template:
                continue
            if not template:
                template = notebook.fraction.sample.result_template.id
            elif template != notebook.fraction.sample.result_template.id:
                return res

        res['template'] = template
        return res
