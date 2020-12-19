# This file is part of lims_quality_control module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from datetime import datetime

from trytond.model import fields
from trytond.pyson import Eval, Equal, Bool
from trytond.transaction import Transaction
from trytond.pool import Pool, PoolMeta
from trytond.exceptions import UserError
from trytond.i18n import gettext
from trytond.modules.lims_interface.interface import FUNCTIONS
from .function import custom_functions

FUNCTIONS.update(custom_functions)


class Configuration(metaclass=PoolMeta):
    __name__ = 'lims.configuration'

    qc_fraction_type = fields.Many2One('lims.fraction.type',
        'QC fraction type')


class Method(metaclass=PoolMeta):
    __name__ = 'lims.lab.method'

    specification = fields.Text('Specification')


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
            }, depends=['quality_type'])

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
        domain=[('id', 'in', Eval('valid_value_domain'))],
        depends=['valid_value_domain', 'quality_type'])
    valid_value_domain = fields.Function(fields.Many2Many(
        'lims.quality.qualitative.value',
        None, None, 'Valid Value domain',
        states={'invisible': True}), 'on_change_with_valid_value_domain')
    quality_test_report = fields.Boolean('Quality Test Report')
    quality_order = fields.Integer('Quality Order')
    quality_min = fields.Float('Min',
        digits=(16, Eval('limit_digits', 2)),
        states={
            'invisible': ~Equal(Eval('quality_type'), 'quantitative'),
            'required': Equal(Eval('quality_type'), 'quantitative'),
            }, depends=['quality_type', 'limit_digits'])
    quality_max = fields.Float('Max',
        digits=(16, Eval('limit_digits', 2)),
        states={
            'invisible': ~Equal(Eval('quality_type'), 'quantitative'),
            'required': Equal(Eval('quality_type'), 'quantitative'),
            }, depends=['quality_type', 'limit_digits'])
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
        cls.start_uom.depends = ['quality_type']
        cls.end_uom.states = {
            'invisible': ~Equal(Eval('quality_type'), 'quantitative'),
            }
        cls.end_uom.depends = ['quality_type']
        cls.initial_concentration.states = {
            'invisible': ~Equal(Eval('quality_type'), 'quantitative'),
            }
        cls.initial_concentration.depends = ['quality_type']
        cls.final_concentration.states = {
            'invisible': ~Equal(Eval('quality_type'), 'quantitative'),
            }
        cls.final_concentration.depends = ['quality_type']
        cls.limit_digits.states = {
            'invisible': ~Equal(Eval('quality_type'), 'quantitative'),
            }
        cls.limit_digits.depends = ['quality_type']
        cls.calc_decimals.states = {
            'invisible': ~Equal(Eval('quality_type'), 'quantitative'),
            }
        cls.calc_decimals.depends = ['quality_type']

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
            cursor.execute('SELECT template '
                'FROM "' + TemplateAnalysis._table + '" '
                'WHERE analysis = %s '
                'AND (method = %s OR method IS NULL)',
                (t.analysis.id, t.method.id))
            template_id = cursor.fetchone()
            result[t.id] = None
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
    quality_test = fields.Many2One('lims.quality.test', 'Quality Test',
        select=True)
    test_value = fields.Many2One('lims.quality.qualitative.value',
        'Test Value',
        states={
            'readonly': True,
            })
    qualitative_value = fields.Many2One('lims.quality.qualitative.value',
        'Qualitative Value',
        domain=[
            ('analysis', '=', Eval('analysis')),
            ], depends=['analysis'])
    success = fields.Function(fields.Boolean('Success',
        depends=['success_icon']), 'get_success')
    success_icon = fields.Function(fields.Char('Success Icon',
        depends=['success']), 'get_success_icon')
    quality_min = fields.Float('Min',
        digits=(16, Eval('decimals', 2)), depends=['decimals'])
    quality_max = fields.Float('Max',
        digits=(16, Eval('decimals', 2)), depends=['decimals'])
    quality_test_report = fields.Boolean('Quality Test Report')
    specification = fields.Text('Specification', readonly=True)

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.result.states = {
            'invisible': Bool(Eval('qualitative_value')),
            'readonly': Bool(Eval('accepted')),
            }
        cls.result.depends = ['accepted', 'qualitative_value']

    @staticmethod
    def default_quality_test_report():
        return True

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
                '<tree editable="bottom">\n'
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


class EntryDetailAnalysis(metaclass=PoolMeta):
    __name__ = 'lims.entry.detail.analysis'

    @classmethod
    def create_notebook_lines(cls, details, fraction):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Typification = pool.get('lims.typification')
        Method = pool.get('lims.lab.method')
        WaitingTime = pool.get('lims.lab.method.results_waiting')
        AnalysisLaboratory = pool.get('lims.analysis-laboratory')
        ProductType = pool.get('lims.product.type')
        Notebook = pool.get('lims.notebook')
        Company = pool.get('company.company')

        def _str_value(val=None):
            return str(val) if val is not None else None

        lines_create = []

        template_id = None
        if Transaction().context.get('template'):
            template_id = Transaction().context.get('template')
        for detail in details:
            query = 'SELECT default_repetitions, ' \
                    'initial_concentration, final_concentration, start_uom, ' \
                    'end_uom, detection_limit, quantification_limit, ' \
                    'lower_limit, upper_limit, calc_decimals, report, id ' \
                'FROM "' + Typification._table + '" ' \
                'WHERE product_type = %s ' \
                    'AND matrix = %s ' \
                    'AND analysis = %s ' \
                    'AND method = %s ' \
                    'AND valid'

            if template_id:
                query += ' AND quality_template = %s'
                cursor.execute(query,
                    (fraction.product_type.id, fraction.matrix.id,
                        detail.analysis.id, detail.method.id, template_id))
            else:
                cursor.execute(query,
                    (fraction.product_type.id, fraction.matrix.id,
                        detail.analysis.id, detail.method.id))
            typifications = cursor.fetchall()
            typification = (typifications[0] if len(typifications) == 1
                else None)
            if typification:
                repetitions = typification[0]
                initial_concentration = _str_value(typification[1])
                final_concentration = _str_value(typification[2])
                initial_unit = typification[3] or None
                final_unit = typification[4] or None
                detection_limit = _str_value(typification[5])
                quantification_limit = _str_value(typification[6])
                lower_limit = _str_value(typification[7])
                upper_limit = _str_value(typification[8])
                decimals = typification[9]
                report = typification[10]
            else:
                repetitions = 0
                initial_concentration = None
                final_concentration = None
                initial_unit = None
                final_unit = None
                detection_limit = None
                quantification_limit = None
                lower_limit = None
                upper_limit = None
                decimals = 2
                report = False

            results_estimated_waiting = None
            cursor.execute('SELECT results_estimated_waiting '
                'FROM "' + WaitingTime._table + '" '
                'WHERE method = %s '
                    'AND party = %s',
                (detail.method.id, detail.party.id))
            res = cursor.fetchone()
            if res:
                results_estimated_waiting = res[0]
            else:
                cursor.execute('SELECT results_estimated_waiting '
                    'FROM "' + Method._table + '" '
                    'WHERE id = %s', (detail.method.id,))
                res = cursor.fetchone()
                if res:
                    results_estimated_waiting = res[0]

            department = None
            cursor.execute('SELECT department '
                'FROM "' + AnalysisLaboratory._table + '" '
                'WHERE analysis = %s '
                    'AND laboratory = %s',
                    (detail.analysis.id, detail.laboratory.id))
            res = cursor.fetchone()
            if res and res[0]:
                department = res[0]
            else:
                cursor.execute('SELECT department '
                    'FROM "' + ProductType._table + '" '
                    'WHERE id = %s', (fraction.product_type.id,))
                res = cursor.fetchone()
                if res and res[0]:
                    department = res[0]

            for i in range(0, repetitions + 1):
                notebook_line = {
                    'analysis_detail': detail.id,
                    'service': detail.service.id,
                    'analysis': detail.analysis.id,
                    'analysis_origin': detail.analysis_origin,
                    'repetition': i,
                    'laboratory': detail.laboratory.id,
                    'method': detail.method.id,
                    'device': detail.device.id if detail.device else None,
                    'initial_concentration': initial_concentration,
                    'final_concentration': final_concentration,
                    'initial_unit': initial_unit,
                    'final_unit': final_unit,
                    'detection_limit': detection_limit,
                    'quantification_limit': quantification_limit,
                    'lower_limit': lower_limit,
                    'upper_limit': upper_limit,
                    'decimals': decimals,
                    'report': report,
                    'results_estimated_waiting': results_estimated_waiting,
                    'department': department,
                    }
                if template_id:
                    quality_typification = Typification(typification[11])
                    notebook_line['typification'] = quality_typification.id
                    notebook_line['test_value'] = \
                        quality_typification.valid_value.id \
                        if quality_typification.valid_value else None
                    notebook_line['quality_test'] = Transaction().context.get(
                        'test')
                    notebook_line['quality_min'] = \
                        quality_typification.quality_min
                    notebook_line['quality_max'] = \
                        quality_typification.quality_max
                    notebook_line['quality_test_report'] = \
                        quality_typification.quality_test_report
                    notebook_line['specification'] = \
                        quality_typification.specification
                lines_create.append(notebook_line)

        if not lines_create:
            companies = Company.search([])
            if fraction.party.id not in [c.party.id for c in companies]:
                raise UserError(gettext(
                    'lims.msg_not_services', fraction=fraction.rec_name))

        with Transaction().set_user(0):
            notebook = Notebook.search([
                ('fraction', '=', fraction.id),
                ])
            Notebook.write(notebook, {
                'lines': [('create', lines_create)],
                })


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
        domain=[
            ('analysis', '=', Eval('analysis')),
            ], depends=['analysis'])
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
                self.result_modifier not in ('eq', 'low')):
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
                'result_modifier': data.result_modifier,
                'end_date': data.end_date,
                'chromatogram': data.chromatogram,
                'initial_unit': (data.initial_unit.id if
                    data.initial_unit else None),
                'comments': data.comments,
                'literal_result': data.literal_result,
                'converted_result': None,
                'converted_result_modifier': 'eq',
                'backup': None,
                'verification': None,
                'uncertainty': None,
                }
            if data.result_modifier == 'na':
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
