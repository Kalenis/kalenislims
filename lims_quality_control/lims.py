# This file is part of lims_quality_control module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from datetime import datetime

from trytond.model import fields, Index
from trytond.pyson import Eval, Equal, Bool
from trytond.transaction import Transaction
from trytond.pool import Pool, PoolMeta
from trytond.exceptions import UserError
from trytond.i18n import gettext
from trytond.modules.lims.analysis import FUNCTIONS
from .function import custom_functions

FUNCTIONS.update(custom_functions)


class Configuration(metaclass=PoolMeta):
    __name__ = 'lims.configuration'

    qc_fraction_type = fields.Many2One('lims.fraction.type',
        'QC fraction type')


class Method(metaclass=PoolMeta):
    __name__ = 'lims.lab.method'

    specification = fields.Text('Specification',
        states={'readonly': Eval('state') != 'draft'})

    def _get_new_version_fields(self):
        fields = super()._get_new_version_fields()
        return fields + ['specification']


class MethodVersion(metaclass=PoolMeta):
    __name__ = 'lims.lab.method.version'

    specification = fields.Text('Specification', readonly=True)


class Analysis(metaclass=PoolMeta):
    __name__ = 'lims.analysis'

    quality_type = fields.Selection([
        ('qualitative', 'Qualitative'),
        ('quantitative', 'Quantitative'),
        ], 'Quality Type', required=True)
    quality_possible_values = fields.One2Many('lims.quality.qualitative.value',
        'analysis', 'Possible Values',
        states={
            'invisible': ~Equal(Eval('quality_type'), 'qualitative'),
            'required': Equal(Eval('quality_type'), 'qualitative'),
            })

    @staticmethod
    def default_quality_type():
        return 'quantitative'


class Typification(metaclass=PoolMeta):
    __name__ = 'lims.typification'
    _history = True

    specification = fields.Text('Specification')
    quality = fields.Boolean('Quality')
    quality_template = fields.Many2One('lims.quality.template',
        'Quality Template')
    quality_type = fields.Function(fields.Selection([
        ('qualitative', 'Qualitative'),
        ('quantitative', 'Quantitative')
        ], 'Quality Type', states={'invisible': True}),
        'on_change_with_quality_type')
    valid_value = fields.Many2One('lims.quality.qualitative.value',
        'Valid Value',
        states={
            'invisible': ~Equal(Eval('quality_type'), 'qualitative'),
            'required': Equal(Eval('quality_type'), 'qualitative'),
            },
        domain=[('id', 'in', Eval('valid_value_domain'))])
    valid_value_domain = fields.Function(fields.Many2Many(
        'lims.quality.qualitative.value',
        None, None, 'Valid Value domain',
        states={'invisible': True}), 'on_change_with_valid_value_domain')
    quality_test_report = fields.Boolean('Quality Test Report')
    quality_order = fields.Integer('Quality Order')
    quality_min = fields.Float('Min', digits=(16, Eval('limit_digits', 2)),
        states={
            'invisible': ~Equal(Eval('quality_type'), 'quantitative'),
            'required': Equal(Eval('quality_type'), 'quantitative'),
            })
    quality_max = fields.Float('Max', digits=(16, Eval('limit_digits', 2)),
        states={
            'invisible': ~Equal(Eval('quality_type'), 'quantitative'),
            'required': Equal(Eval('quality_type'), 'quantitative'),
            })
    interface = fields.Function(fields.Many2One('lims.interface',
        'Interface'), 'get_interface')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._sql_constraints = []
        cls.start_uom.states = {
            'invisible': ~Equal(Eval('quality_type'), 'quantitative'),
            'required': Equal(Eval('quality_type'), 'quantitative'),
            }
        cls.end_uom.states = {
            'invisible': ~Equal(Eval('quality_type'), 'quantitative'),
            }
        cls.initial_concentration.states = {
            'invisible': ~Equal(Eval('quality_type'), 'quantitative'),
            }
        cls.final_concentration.states = {
            'invisible': ~Equal(Eval('quality_type'), 'quantitative'),
            }
        cls.limit_digits.states = {
            'invisible': ~Equal(Eval('quality_type'), 'quantitative'),
            }
        cls.calc_decimals.states = {
            'invisible': ~Equal(Eval('quality_type'), 'quantitative'),
            }

    @classmethod
    def __register__(cls, module_name):
        super().__register__(module_name)
        table = cls.__table_handler__(module_name)
        table.drop_constraint('product_matrix_analysis_method_uniq')

    @fields.depends('analysis')
    def on_change_with_valid_value_domain(self, name=None):
        values = []
        if self.analysis and self.analysis.quality_possible_values:
            for value in self.analysis.quality_possible_values:
                values.append(value.id)
        return values

    @fields.depends('analysis')
    def on_change_with_quality_type(self, name=None):
        if self.analysis:
            return self.analysis.quality_type

    @fields.depends('method')
    def on_change_method(self):
        if self.method:
            self.specification = self.method.specification

    def check_default(self):
        if self.quality:
            return
        if self.by_default:
            typifications = self.search([
                ('product_type', '=', self.product_type.id),
                ('matrix', '=', self.matrix.id),
                ('analysis', '=', self.analysis.id),
                ('valid', '=', True),
                ('by_default', '=', True),
                ('id', '!=', self.id),
                ])
            if typifications:
                raise UserError(gettext('lims.msg_default_typification'))
        else:
            if self.valid:
                typifications = self.search([
                    ('product_type', '=', self.product_type.id),
                    ('matrix', '=', self.matrix.id),
                    ('analysis', '=', self.analysis.id),
                    ('valid', '=', True),
                    ('id', '!=', self.id),
                    ])
                if not typifications:
                    raise UserError(
                        gettext('lims.msg_not_default_typification'))

    @classmethod
    def get_interface(cls, typifications, name):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Template = pool.get('lims.template.analysis_sheet')
        TemplateAnalysis = pool.get('lims.template.analysis_sheet.analysis')

        result = {}
        for t in typifications:
            cursor.execute('SELECT t.id '
                'FROM "' + Template._table + '" t '
                    'INNER JOIN "' + TemplateAnalysis._table + '" ta '
                    'ON t.id = ta.template '
                'WHERE t.active IS TRUE '
                    'AND ta.analysis = %s '
                    'AND ta.method = %s',
                (t.analysis.id, t.method.id))
            template_id = cursor.fetchone()
            result[t.id] = None
            if not template_id:
                cursor.execute('SELECT t.id '
                    'FROM "' + Template._table + '" t '
                        'INNER JOIN "' + TemplateAnalysis._table + '" ta '
                        'ON t.id = ta.template '
                    'WHERE t.active IS TRUE '
                        'AND ta.analysis = %s '
                        'AND ta.method IS NULL',
                    (t.analysis.id,))
                template_id = cursor.fetchone()
            if template_id:
                template = Template(template_id[0])
                result[t.id] = template.interface.id
        return result

    @classmethod
    def create(cls, vlist):
        Template = Pool().get('lims.quality.template')

        vlist = [x.copy() for x in vlist]
        for values in vlist:
            if values.get('quality_template'):
                template, = Template.browse([values.get('quality_template')])
                values['product_type'] = template.product.product_type.id
                values['matrix'] = template.product.matrix.id
        return super().create(vlist)


class NotebookLine(metaclass=PoolMeta):
    __name__ = 'lims.notebook.line'

    typification = fields.Many2One('lims.typification', 'Typification')
    quality_test = fields.Many2One('lims.quality.test', 'Quality Test')
    test_value = fields.Many2One('lims.quality.qualitative.value',
        'Test Value', states={'readonly': True})
    qualitative_value = fields.Many2One('lims.quality.qualitative.value',
        'Qualitative Value',
        domain=[('analysis', '=', Eval('analysis'))])
    success = fields.Function(fields.Boolean('Success'),
        'get_success')
    success_icon = fields.Function(fields.Char('Success Icon'),
        'get_success_icon')
    quality_min = fields.Float('Min',
        digits=(16, Eval('decimals', 2)))
    quality_max = fields.Float('Max',
        digits=(16, Eval('decimals', 2)))
    quality_test_report = fields.Boolean('Quality Test Report')
    specification = fields.Text('Specification', readonly=True)
    test_result = fields.Function(fields.Char('Test Result'),
        'get_test_result')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.result.states = {
            'invisible': Bool(Eval('qualitative_value')),
            'readonly': Bool(Eval('accepted')),
            }
        t = cls.__table__()
        #cls._sql_indexes.update({
            #Index(t, (t.quality_test, Index.Equality())),
            #})

    @staticmethod
    def default_quality_test_report():
        return True

    @classmethod
    def get_test_result(cls, lines, name):
        result = {}
        for line in lines:
            result[line.id] = line.formated_result
        return result

    @classmethod
    def get_success(self, lines, name):
        res = {}
        for line in lines:
            res[line.id] = False
            if line.analysis.quality_type == 'quantitative':
                if line.result:
                    value = float(line.result)
                    quality_min = line.quality_min
                    if not isinstance(quality_min, (int, float)):
                        quality_min = float('-inf')
                    quality_max = line.quality_max
                    if not isinstance(quality_max, (int, float)):
                        quality_max = float('inf')
                    if (value >= quality_min and value <= quality_max):
                        res[line.id] = True
            else:
                if line.qualitative_value == line.test_value:
                    res[line.id] = True
        return res

    def get_success_icon(self, name):
        if not self.accepted:
            return 'lims-white'
        if self.success:
            return 'lims-green'
        return 'lims-red'

    @fields.depends('qualitative_value')
    def on_change_qualitative_value(self):
        if self.qualitative_value:
            self.literal_result = self.qualitative_value.name

    @classmethod
    def fields_view_get(cls, view_id=None, view_type='form'):
        pool = Pool()
        User = pool.get('res.user')
        Config = pool.get('lims.configuration')
        UiView = pool.get('ir.ui.view')

        result = super().fields_view_get(view_id=view_id, view_type=view_type)

        # All Notebook Lines view
        if view_id and UiView(view_id).name == 'notebook_line_all_list':
            return result

        notebook_view = User(Transaction().user).notebook_view
        if not notebook_view:
            notebook_view = Config(1).default_notebook_view
            if not notebook_view:
                return result

        if view_type == 'tree':
            xml = '<?xml version="1.0"?>\n' \
                '<tree editable="1">\n'
            fields = set()
            for column in notebook_view.columns:
                fields.add(column.field.name)
                attrs = []
                if column.field.name == 'analysis':
                    attrs.append('icon="icon"')
                if column.field.name == 'success':
                    attrs.append('icon="success_icon"')
                if column.field.name in ('acceptance_date', 'annulment_date'):
                    attrs.append('widget="date"')
                xml += ('<field name="%s" %s/>\n'
                    % (column.field.name, ' '.join(attrs)))
                for depend in getattr(cls, column.field.name).depends:
                    fields.add(depend)
            for field in ('report_date', 'result', 'converted_result',
                    'result_modifier', 'converted_result_modifier',
                    'literal_result', 'backup', 'verification', 'uncertainty',
                    'accepted', 'acceptance_date', 'end_date', 'report',
                    'annulled', 'annulment_date', 'icon'):
                fields.add(field)
            xml += '</tree>'
            result['arch'] = xml
            result['fields'] = cls.fields_get(fields_names=list(fields))
        return result


class NotebookRepeatAnalysis(metaclass=PoolMeta):
    __name__ = 'lims.notebook.repeat_analysis'

    def _get_repetition_defaults(self, line):
        defaults = super()._get_repetition_defaults(line)
        defaults.update({
            'typification': (line.typification and
                line.typification.id or None),
            'quality_test': (line.quality_test and
                line.quality_test.id or None),
            'test_value': (line.test_value and
                line.test_value.id or None),
            'qualitative_value': (line.qualitative_value and
                line.qualitative_value.id or None),
            'quality_min': line.quality_min,
            'quality_max': line.quality_max,
            'quality_test_report': line.quality_test_report,
            'specification': line.specification,
            })
        return defaults


class NotebookLineRepeatAnalysis(metaclass=PoolMeta):
    __name__ = 'lims.notebook.line.repeat_analysis'

    def _get_repetition_defaults(self, line):
        defaults = super()._get_repetition_defaults(line)
        defaults.update({
            'typification': (line.typification and
                line.typification.id or None),
            'quality_test': (line.quality_test and
                line.quality_test.id or None),
            'test_value': (line.test_value and
                line.test_value.id or None),
            'qualitative_value': (line.qualitative_value and
                line.qualitative_value.id or None),
            'quality_min': line.quality_min,
            'quality_max': line.quality_max,
            'quality_test_report': line.quality_test_report,
            'specification': line.specification,
            })
        return defaults


class Entry(metaclass=PoolMeta):
    __name__ = 'lims.entry'

    @classmethod
    def _get_update_entries_state_exclude(cls):
        pool = Pool()
        LabWorkYear = pool.get('lims.lab.workyear')

        res = super()._get_update_entries_state_exclude()

        workyear_id = LabWorkYear.find()
        workyear = LabWorkYear(workyear_id)
        if workyear.default_entry_quality:
            res.append(workyear.default_entry_quality.id)
        return res


class EntryDetailAnalysis(metaclass=PoolMeta):
    __name__ = 'lims.entry.detail.analysis'

    @classmethod
    def create_notebook_lines(cls, details, fraction):
        pool = Pool()
        Company = pool.get('company.company')

        lines = super().create_notebook_lines(details, fraction)
        if not lines:
            companies = Company.search([])
            if fraction.party.id not in [c.party.id for c in companies]:
                raise UserError(gettext(
                    'lims.msg_not_services', fraction=fraction.rec_name))
        return lines

    @classmethod
    def _get_notebook_line(cls, detail, fraction, notebook):
        to_create, t = super()._get_notebook_line(detail, fraction, notebook)
        template_id = Transaction().context.get('template', None)
        if template_id and t:
            test_value = t.valid_value and t.valid_value.id or None
            quality_test = Transaction().context.get('test')
            for notebook_line in to_create:
                notebook_line['typification'] = t.id
                notebook_line['test_value'] = test_value
                notebook_line['quality_test'] = quality_test
                notebook_line['quality_min'] = t.quality_min
                notebook_line['quality_max'] = t.quality_max
                notebook_line['quality_test_report'] = t.quality_test_report
                notebook_line['specification'] = t.specification
        return to_create, t

    @classmethod
    def _get_notebook_line_valid_typification(cls, detail, fraction):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Typification = pool.get('lims.typification')

        template_id = Transaction().context.get('template', None)
        if not template_id:
            return Typification.get_valid_typification(
                fraction.product_type.id, fraction.matrix.id,
                detail.analysis.id, detail.method.id, detail.laboratory.id)

        cursor.execute('SELECT id '
            'FROM "' + Typification._table + '" '
            'WHERE product_type = %s '
                'AND matrix = %s '
                'AND analysis = %s '
                'AND method = %s '
                'AND quality_template = %s '
                'AND valid',
            (fraction.product_type.id, fraction.matrix.id,
                detail.analysis.id, detail.method.id, template_id))
        res = cursor.fetchone()
        return res and Typification(res[0]) or None


class AnalysisSheet(metaclass=PoolMeta):
    __name__ = 'lims.analysis_sheet'

    @classmethod
    def delete(cls, sheets):
        raise UserError(gettext('lims_quality_control.delete_sheet'))


class ResultReport(metaclass=PoolMeta):
    __name__ = 'lims.result_report'

    @classmethod
    def get_reference(cls, range_type, notebook_line, language,
            report_section):
        res = super().get_reference(range_type, notebook_line, language,
            report_section)
        if res:
            return res

        res = ''
        if notebook_line.quality_min:
            with Transaction().set_context(language=language):
                resf = float(notebook_line.quality_min)
                resd = abs(resf) - abs(int(resf))
                if resd > 0:
                    res1 = str(round(notebook_line.quality_min, 2))
                else:
                    res1 = str(int(notebook_line.quality_min))
                res = gettext('lims.msg_caa_min', min=res1)

        if notebook_line.quality_max:
            if res:
                res += ' - '
            with Transaction().set_context(language=language):
                resf = float(notebook_line.quality_max)
                resd = abs(resf) - abs(int(resf))
                if resd > 0:
                    res1 = str(round(notebook_line.quality_max, 2))
                else:
                    res1 = str(int(notebook_line.quality_max))

                res += gettext('lims.msg_caa_max', max=res1)
        return res


class NotebookLoadResultsManualLine(metaclass=PoolMeta):
    __name__ = 'lims.notebook.load_results_manual.line'

    qualitative_value = fields.Many2One('lims.quality.qualitative.value',
        'Qualitative Value',
        domain=[('analysis', '=', Eval('analysis'))])
    analysis = fields.Function(fields.Many2One('lims.analysis', 'Analysis'),
        'get_analysis')

    def get_analysis(self, name):
        return self.line.analysis.id if self.line else None

    @fields.depends('result', 'literal_result', 'result_modifier', 'end_date',
        'qualitative_value')
    def on_change_with_end_date(self):
        pool = Pool()
        Date = pool.get('ir.date')
        if self.end_date:
            return self.end_date
        if (self.result or self.literal_result or self.qualitative_value or
                (self.result_modifier and self.result_modifier.code != 'low')):
            return Date.today()
        return None

    @fields.depends('qualitative_value')
    def on_change_qualitative_value(self):
        if self.qualitative_value:
            self.literal_result = self.qualitative_value.name


class NotebookLoadResultsManual(metaclass=PoolMeta):
    __name__ = 'lims.notebook.load_results_manual'

    def transition_confirm_(self):
        pool = Pool()
        NotebookLoadResultsManualLine = pool.get(
            'lims.notebook.load_results_manual.line')
        NotebookLine = pool.get('lims.notebook.line')
        LabProfessionalMethod = pool.get('lims.lab.professional.method')
        LabProfessionalMethodRequalification = pool.get(
            'lims.lab.professional.method.requalification')
        Date = pool.get('ir.date')

        # Write Results to Notebook lines
        actions = NotebookLoadResultsManualLine.search([
            ('session_id', '=', self._session_id),
            ])

        for data in actions:
            notebook_line = NotebookLine(data.line.id)
            if not notebook_line:
                continue
            notebook_line_write = {
                'result': data.result,
                'qualitative_value': data.qualitative_value,
                'result_modifier': (data.result_modifier.id if
                    data.result_modifier else None),
                'end_date': data.end_date,
                'chromatogram': data.chromatogram,
                'initial_unit': (data.initial_unit.id if
                    data.initial_unit else None),
                'comments': data.comments,
                'literal_result': data.literal_result,
                'converted_result': None,
                'converted_result_modifier': None,
                'backup': None,
                'verification': None,
                'uncertainty': None,
                }
            if data.result_modifier and data.result_modifier.code == 'na':
                notebook_line_write['annulled'] = True
                notebook_line_write['annulment_date'] = datetime.now()
                notebook_line_write['report'] = False
            professionals = [{'professional': self.result.professional.id}]
            notebook_line_write['professionals'] = (
                [('delete', [p.id for p in notebook_line.professionals])] +
                [('create', professionals)])
            NotebookLine.write([notebook_line], notebook_line_write)

        # Write Supervisors to Notebook lines
        supervisor_lines = {}
        if hasattr(self.sit2, 'supervisor'):
            supervisor_lines[self.sit2.supervisor.id] = [
                l.id for l in self.sit2.lines]
        for prof_id, lines in supervisor_lines.items():
            notebook_lines = NotebookLine.search([
                ('id', 'in', lines),
                ])
            if notebook_lines:
                professionals = [{'professional': prof_id}]
                notebook_line_write = {
                    'professionals': [('create', professionals)],
                    }
                NotebookLine.write(notebook_lines, notebook_line_write)

        # Write the execution of method
        all_prof = {}
        key = (self.result.professional.id, self.result.method.id)
        all_prof[key] = []
        if hasattr(self.sit2, 'supervisor'):
            for detail in self.sit2.lines:
                key = (self.sit2.supervisor.id, detail.method.id)
                if key not in all_prof:
                    all_prof[key] = []
                key = (self.result.professional.id, detail.method.id)
                if self.sit2.supervisor.id not in all_prof[key]:
                    all_prof[key].append(self.sit2.supervisor.id)

        today = Date.today()
        for key, sup in all_prof.items():
            professional_method, = LabProfessionalMethod.search([
                ('professional', '=', key[0]),
                ('method', '=', key[1]),
                ('type', '=', 'analytical'),
                ])
            if professional_method.state == 'training':
                history = LabProfessionalMethodRequalification.search([
                    ('professional_method', '=', professional_method.id),
                    ('type', '=', 'training'),
                    ])
                if history:
                    prev_supervisors = [s.supervisor.id for s in
                        history[0].supervisors]
                    supervisors = [{'supervisor': s} for s in sup
                        if s not in prev_supervisors]
                    LabProfessionalMethodRequalification.write(history, {
                        'last_execution_date': today,
                        'supervisors': [('create', supervisors)],
                        })
                else:
                    supervisors = [{'supervisor': s} for s in sup]
                    to_create = [{
                        'professional_method': professional_method.id,
                        'type': 'training',
                        'date': today,
                        'last_execution_date': today,
                        'supervisors': [('create', supervisors)],
                        }]
                    LabProfessionalMethodRequalification.create(to_create)

            elif professional_method.state == 'qualified':
                history = LabProfessionalMethodRequalification.search([
                    ('professional_method', '=', professional_method.id),
                    ('type', '=', 'qualification'),
                    ])
                if history:
                    LabProfessionalMethodRequalification.write(history, {
                        'last_execution_date': today,
                        })
                else:
                    to_create = [{
                        'professional_method': professional_method.id,
                        'type': 'qualification',
                        'date': today,
                        'last_execution_date': today,
                        }]
                    LabProfessionalMethodRequalification.create(to_create)

            else:
                history = LabProfessionalMethodRequalification.search([
                    ('professional_method', '=', professional_method.id),
                    ('type', '=', 'requalification'),
                    ])
                if history:
                    LabProfessionalMethodRequalification.write(history, {
                        'last_execution_date': today,
                        })
                else:
                    to_create = [{
                        'professional_method': professional_method.id,
                        'type': 'requalification',
                        'date': today,
                        'last_execution_date': today,
                        }]
                    LabProfessionalMethodRequalification.create(to_create)

        return 'end'
