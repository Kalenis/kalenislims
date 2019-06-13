# -*- coding: utf-8 -*-
# This file is part of lims module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import logging
import operator
from datetime import datetime
from decimal import Decimal
from sql import Literal
from trytond.model import Workflow, ModelView, ModelSQL, fields, Unique
from trytond.wizard import Wizard, StateTransition, StateView, StateAction, \
    Button
from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.pyson import PYSONEncoder, Eval, Equal, Bool, Not, Or, And

__all__ = ['ProductType', 'Matrix', 'ObjectiveDescription', 'Formula',
    'FormulaVariable', 'Analysis', 'Typification', 'TypificationAditional',
    'TypificationReadOnly', 'CalculatedTypification',
    'CalculatedTypificationReadOnly', 'AnalysisIncluded', 'AnalysisLaboratory',
    'AnalysisLabMethod', 'AnalysisDevice', 'CopyTypificationStart',
    'CopyTypification', 'CopyCalculatedTypificationStart',
    'CopyCalculatedTypification', 'RelateAnalysisStart', 'RelateAnalysis',
    'CreateAnalysisProduct', 'OpenTypifications', 'AddTypificationsStart',
    'AddTypifications', 'RemoveTypificationsStart', 'RemoveTypifications']


class Typification(ModelSQL, ModelView):
    'Typification'
    __name__ = 'lims.typification'
    _rec_name = 'initial_concentration'

    product_type = fields.Many2One('lims.product.type', 'Product type',
        required=True, select=True,
        states={'readonly': Bool(Eval('id', 0) > 0)})
    matrix = fields.Many2One('lims.matrix', 'Matrix', required=True,
        select=True, states={'readonly': Bool(Eval('id', 0) > 0)})
    analysis = fields.Many2One('lims.analysis', 'Analysis', required=True,
        domain=[
            ('state', '=', 'active'),
            ('type', '=', 'analysis'),
            ('behavior', '!=', 'additional'),
        ], select=True, states={'readonly': Bool(Eval('id', 0) > 0)})
    method = fields.Many2One('lims.lab.method', 'Method', required=True,
        domain=[('id', 'in', Eval('method_domain'))],
        depends=['method_domain'], select=True)
    method_view = fields.Function(fields.Many2One('lims.lab.method', 'Method'),
        'get_views_field', searcher='search_views_field')
    method_domain = fields.Function(fields.Many2Many('lims.lab.method',
        None, None, 'Method domain'),
        'on_change_with_method_domain')
    detection_limit = fields.Float('Detection limit',
        digits=(16, Eval('limit_digits', 2)), depends=['limit_digits'])
    quantification_limit = fields.Float('Quantification limit',
        digits=(16, Eval('limit_digits', 2)), depends=['limit_digits'])
    limit_digits = fields.Integer('Limit digits')
    check_result_limits = fields.Boolean(
        'Validate limits directly on the result')
    initial_concentration = fields.Char('Initial concentration')
    start_uom = fields.Many2One('product.uom', 'Start UoM',
        domain=[('category.lims_only_available', '=', True)])
    final_concentration = fields.Char('Final concentration')
    end_uom = fields.Many2One('product.uom', 'End UoM',
        domain=[('category.lims_only_available', '=', True)])
    default_repetitions = fields.Integer('Default repetitions',
        required=True)
    technical_scope_versions = fields.Function(fields.One2Many(
        'lims.technical.scope.version', None,
        'Technical scope versions'), 'get_technical_scope_versions')
    comments = fields.Text('Comments')
    additional = fields.Many2One('lims.analysis', 'Additional analysis',
        domain=[('state', '=', 'active'), ('behavior', '=', 'additional')])
    additionals = fields.Many2Many('lims.typification-analysis',
        'typification', 'analysis', 'Additional analysis',
        domain=[('id', 'in', Eval('additionals_domain'))],
        depends=['additionals_domain'])
    additionals_domain = fields.Function(fields.Many2Many('lims.analysis',
        None, None, 'Additional analysis domain'),
        'on_change_with_additionals_domain')
    by_default = fields.Boolean('By default')
    calc_decimals = fields.Integer('Calculation decimals', required=True)
    report = fields.Boolean('Report')
    report_type = fields.Selection([
        ('normal', 'Normal'),
        ('polisample', 'Polisample'),
        ], 'Report type', sort=False)
    report_result_type = fields.Selection([
        ('result', 'Result'),
        ('both', 'Both'),
        ], 'Result type', sort=False)
    valid = fields.Boolean('Active', depends=['valid_readonly'],
        states={'readonly': Bool(Eval('valid_readonly'))})
    valid_view = fields.Function(fields.Boolean('Active'),
        'get_views_field', searcher='search_views_field')
    valid_readonly = fields.Function(fields.Boolean(
        'Field active readonly'),
        'on_change_with_valid_readonly')

    @classmethod
    def __setup__(cls):
        super(Typification, cls).__setup__()
        cls._order.insert(0, ('product_type', 'ASC'))
        cls._order.insert(1, ('matrix', 'ASC'))
        cls._order.insert(2, ('analysis', 'ASC'))
        cls._order.insert(3, ('method', 'ASC'))
        t = cls.__table__()
        cls._sql_constraints += [
            ('product_matrix_analysis_method_uniq',
                Unique(t, t.product_type, t.matrix, t.analysis, t.method),
                'This typification already exists'),
            ]
        cls._error_messages.update({
            'limits': ('Quantification limit must be greater than'
                ' Detection limit'),
            'default_typification': ('There is already a default typification'
                ' for this combination of product type, matrix and analysis'),
            'not_default_typification': ('This typification should be the'
                ' default'),
            })

    @staticmethod
    def default_limit_digits():
        return 2

    @staticmethod
    def default_default_repetitions():
        return 0

    @staticmethod
    def default_by_default():
        return True

    @staticmethod
    def default_calc_decimals():
        return 2

    @staticmethod
    def default_report():
        return True

    @staticmethod
    def default_report_type():
        return 'normal'

    @staticmethod
    def default_report_result_type():
        return 'result'

    @staticmethod
    def default_valid():
        return True

    @staticmethod
    def default_check_result_limits():
        return False

    @staticmethod
    def default_detection_limit():
        return 0.00

    @staticmethod
    def default_quantification_limit():
        return 0.00

    @classmethod
    def get_views_field(cls, typifications, names):
        result = {}
        for name in names:
            field_name = name[:-5]
            result[name] = {}
            if field_name == 'valid':
                for t in typifications:
                    result[name][t.id] = getattr(t, field_name, None)
            else:
                for t in typifications:
                    field = getattr(t, field_name, None)
                    result[name][t.id] = field.id if field else None
        return result

    @classmethod
    def search_views_field(cls, name, clause):
        return [(name[:-5],) + tuple(clause[1:])]

    @fields.depends('analysis')
    def on_change_with_valid_readonly(self, name=None):
        if self.analysis and self.analysis.state == 'disabled':
            return True
        return False

    @fields.depends('analysis')
    def on_change_analysis(self):
        method = None
        if self.analysis:
            methods = self.on_change_with_method_domain()
            if len(methods) == 1:
                method = methods[0]
        self.method = method

    @fields.depends('analysis')
    def on_change_with_method_domain(self, name=None):
        methods = []
        if self.analysis and self.analysis.methods:
            methods = [m.id for m in self.analysis.methods]
        return methods

    def get_technical_scope_versions(self, name=None):
        pool = Pool()
        TechnicalScopeVersionLine = pool.get(
            'lims.technical.scope.version.line')

        version_lines = TechnicalScopeVersionLine.search([
            ('typification', '=', self.id),
            ('version.valid', '=', True),
            ])
        if version_lines:
            return [line.version.id for line in version_lines]
        return []

    @fields.depends('analysis', 'product_type', 'matrix')
    def on_change_with_additionals_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Analysis = pool.get('lims.analysis')
        Typification = pool.get('lims.typification')

        if not self.analysis:
            return []
        if not self.product_type or not self.matrix:
            return []

        cursor.execute('SELECT a.id '
            'FROM "' + Analysis._table + '" a '
                'INNER JOIN "' + Typification._table + '" t '
                'ON a.id = t.analysis '
            'WHERE a.id != %s '
                'AND a.type = \'analysis\' '
                'AND a.behavior != \'additional\' '
                'AND a.state = \'active\' '
                'AND t.product_type = %s '
                'AND t.matrix = %s '
                'AND t.valid IS TRUE',
            (self.analysis.id, self.product_type.id, self.matrix.id))
        res = cursor.fetchall()
        if not res:
            return []
        return [x[0] for x in res]

    def get_rec_name(self, name):
        return self.product_type.rec_name + '-' + self.matrix.rec_name

    @classmethod
    def search_rec_name(cls, name, clause):
        typifications = cls.search(['OR',
            ('product_type',) + tuple(clause[1:]),
            ('matrix',) + tuple(clause[1:]),
            ('analysis',) + tuple(clause[1:]),
            ('method',) + tuple(clause[1:]),
            ], order=[])
        if typifications:
            return [('id', 'in', [t.id for t in typifications])]
        return [(cls._rec_name,) + tuple(clause[1:])]

    @classmethod
    def validate(cls, typifications):
        super(Typification, cls).validate(typifications)
        for t in typifications:
            t.check_limits()
            t.check_default()

    def check_limits(self):
        if (self.detection_limit and
                self.quantification_limit <= self.detection_limit):
            self.raise_user_error('limits')

    def check_default(self):
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
                self.raise_user_error('default_typification')
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
                    self.raise_user_error('not_default_typification')

    @classmethod
    def create(cls, vlist):
        typifications = super(Typification, cls).create(vlist)
        active_typifications = [t for t in typifications if t.valid]
        cls.create_typification_calculated(active_typifications)
        return typifications

    @classmethod
    def create_typification_calculated(cls, typifications):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Analysis = pool.get('lims.analysis')
        CalculatedTypification = pool.get('lims.typification.calculated')

        for typification in typifications:

            cursor.execute('SELECT DISTINCT(analysis) '
                'FROM "' + cls._table + '" '
                'WHERE product_type = %s '
                    'AND matrix = %s '
                    'AND valid',
                (typification.product_type.id, typification.matrix.id))
            typified_analysis = [a[0] for a in cursor.fetchall()]
            typified_analysis_ids = ', '.join(str(a) for a in
                typified_analysis)

            sets_groups_ids = Analysis.get_parents_analysis(
                typification.analysis.id)
            for set_group_id in sets_groups_ids:
                t_set_group = CalculatedTypification.search([
                    ('product_type', '=', typification.product_type.id),
                    ('matrix', '=', typification.matrix.id),
                    ('analysis', '=', set_group_id),
                    ])
                if not t_set_group:

                    ia = Analysis.get_included_analysis_analysis(
                        set_group_id)
                    if not ia:
                        continue
                    included_ids = ', '.join(str(a) for a in ia)

                    cursor.execute('SELECT id '
                        'FROM "' + Analysis._table + '" '
                        'WHERE id IN (' + included_ids + ') '
                            'AND id NOT IN (' + typified_analysis_ids +
                            ')')
                    if cursor.fetchone():
                        typified = False
                    else:
                        typified = True

                    if typified:
                        typification_create = [{
                            'product_type': typification.product_type.id,
                            'matrix': typification.matrix.id,
                            'analysis': set_group_id,
                            }]
                        CalculatedTypification.create(
                            typification_create)

        return typifications

    @classmethod
    def delete(cls, typifications):
        cls.delete_typification_calculated(typifications)
        super(Typification, cls).delete(typifications)

    @classmethod
    def delete_typification_calculated(cls, typifications):
        pool = Pool()
        Analysis = pool.get('lims.analysis')
        CalculatedTypification = pool.get('lims.typification.calculated')

        for typification in typifications:

            others = cls.search([
                ('product_type', '=', typification.product_type.id),
                ('matrix', '=', typification.matrix.id),
                ('analysis', '=', typification.analysis.id),
                ('valid', '=', True),
                ('id', '!=', typification.id),
                ])
            if others:
                continue

            sets_groups_ids = Analysis.get_parents_analysis(
                typification.analysis.id)
            for set_group_id in sets_groups_ids:
                typified_set_group = CalculatedTypification.search([
                    ('product_type', '=', typification.product_type.id),
                    ('matrix', '=', typification.matrix.id),
                    ('analysis', '=', set_group_id),
                    ])
                if typified_set_group:
                    CalculatedTypification.delete(typified_set_group)

    @classmethod
    def write(cls, *args):
        super(Typification, cls).write(*args)
        actions = iter(args)
        for typifications, vals in zip(actions, actions):
            if 'valid' in vals:
                if vals['valid']:
                    cls.create_typification_calculated(typifications)
                else:
                    cls.delete_typification_calculated(typifications)

            fields_check = ('detection_limit', 'quantification_limit',
                'initial_concentration', 'final_concentration', 'start_uom',
                'end_uom', 'calc_decimals', 'report')
            for field in fields_check:
                if field in vals:
                    cls.update_laboratory_notebook(typifications)
                    break

    @classmethod
    def update_laboratory_notebook(cls, typifications):
        NotebookLine = Pool().get('lims.notebook.line')

        for typification in typifications:
            if not typification.valid:
                continue

            # Update not RM
            notebook_lines = NotebookLine.search([
                ('notebook.fraction.special_type', '!=', 'rm'),
                ('notebook.product_type', '=', typification.product_type.id),
                ('notebook.matrix', '=', typification.matrix.id),
                ('analysis', '=', typification.analysis.id),
                ('method', '=', typification.method.id),
                ('end_date', '=', None),
                ])
            if notebook_lines:
                NotebookLine.write(notebook_lines, {
                    'detection_limit': str(
                        typification.detection_limit),
                    'quantification_limit': str(
                        typification.quantification_limit),
                    'initial_concentration': str(
                        typification.initial_concentration or ''),
                    'final_concentration': str(
                        typification.final_concentration or ''),
                    'initial_unit': typification.start_uom,
                    'final_unit': typification.end_uom,
                    'decimals': typification.calc_decimals,
                    'report': typification.report,
                    })

            # Update RM
            notebook_lines = NotebookLine.search([
                ('notebook.fraction.special_type', '=', 'rm'),
                ('notebook.product_type', '=', typification.product_type.id),
                ('notebook.matrix', '=', typification.matrix.id),
                ('analysis', '=', typification.analysis.id),
                ('method', '=', typification.method.id),
                ('end_date', '=', None),
                ])
            if notebook_lines:
                NotebookLine.write(notebook_lines, {
                    'initial_concentration': str(
                        typification.initial_concentration or ''),
                    })


class TypificationAditional(ModelSQL):
    'Typification - Additional analysis'
    __name__ = 'lims.typification-analysis'

    typification = fields.Many2One('lims.typification', 'Typification',
        ondelete='CASCADE', select=True, required=True)
    analysis = fields.Many2One('lims.analysis', 'Analysis',
        ondelete='CASCADE', select=True, required=True)


class TypificationReadOnly(ModelSQL, ModelView):
    'Typification'
    __name__ = 'lims.typification.readonly'

    product_type = fields.Many2One('lims.product.type', 'Product type',
        readonly=True)
    matrix = fields.Many2One('lims.matrix', 'Matrix', readonly=True)
    analysis = fields.Many2One('lims.analysis', 'Analysis', readonly=True)
    method = fields.Many2One('lims.lab.method', 'Method', readonly=True)

    @classmethod
    def __setup__(cls):
        super(TypificationReadOnly, cls).__setup__()
        cls._order.insert(0, ('product_type', 'ASC'))
        cls._order.insert(1, ('matrix', 'ASC'))
        cls._order.insert(2, ('analysis', 'ASC'))
        cls._order.insert(3, ('method', 'ASC'))

    @staticmethod
    def table_query():
        pool = Pool()
        typification = pool.get('lims.typification').__table__()

        columns = [
            typification.id,
            typification.create_uid,
            typification.create_date,
            typification.write_uid,
            typification.write_date,
            typification.product_type,
            typification.matrix,
            typification.analysis,
            typification.method,
            ]
        where = Literal(True)
        return typification.select(*columns, where=where)


class CalculatedTypification(ModelSQL):
    'Calculated Typification'
    __name__ = 'lims.typification.calculated'

    product_type = fields.Many2One('lims.product.type', 'Product type',
        required=True, select=True)
    matrix = fields.Many2One('lims.matrix', 'Matrix', required=True,
        select=True)
    analysis = fields.Many2One('lims.analysis', 'Analysis', required=True,
        ondelete='CASCADE', select=True)

    @classmethod
    def __register__(cls, module_name):
        super(CalculatedTypification, cls).__register__(module_name)
        if cls.search_count([]) == 0:
            cls.populate_typification_calculated()

    @classmethod
    def populate_typification_calculated(cls):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Analysis = pool.get('lims.analysis')
        Typification = pool.get('lims.typification')

        cursor.execute('SELECT DISTINCT(product_type, matrix) '
            'FROM "' + Typification._table + '" '
            'WHERE valid')
        typifications = cursor.fetchall()
        if typifications:
            typifications_count = 0
            typifications_total = len(typifications)
            for typification in typifications:

                typifications_count += 1
                logging.getLogger('lims').info(
                    'Calculating typification %s of %s' %
                    (typifications_count, typifications_total))

                product_type = int(typification[0].split(',')[0][1:])
                matrix = int(typification[0].split(',')[1][:-1])
                cursor.execute('SELECT DISTINCT(analysis) '
                    'FROM "' + Typification._table + '" '
                    'WHERE product_type = %s '
                        'AND matrix = %s '
                        'AND valid',
                    (product_type, matrix))
                typified_analysis = [a[0] for a in cursor.fetchall()]
                typified_analysis_ids = ', '.join(str(a) for a in
                    typified_analysis)

                cursor.execute('SELECT id '
                    'FROM "' + Analysis._table + '" '
                    'WHERE type IN (\'set\', \'group\') '
                        'AND state = \'active\'')
                sets_groups_ids = [x[0] for x in cursor.fetchall()]
                if sets_groups_ids:
                    for set_group_id in sets_groups_ids:
                        typified = True

                        ia = Analysis.get_included_analysis_analysis(
                            set_group_id)
                        if not ia:
                            continue
                        included_ids = ', '.join(str(a) for a in ia)

                        cursor.execute('SELECT id '
                            'FROM "' + Analysis._table + '" '
                            'WHERE id IN (' + included_ids + ') '
                                'AND id NOT IN (' + typified_analysis_ids +
                                ')')
                        if cursor.fetchone():
                            typified = False

                        if typified:
                            typification_create = [{
                                'product_type': product_type,
                                'matrix': matrix,
                                'analysis': set_group_id,
                                }]
                            cls.create(typification_create)


class CalculatedTypificationReadOnly(ModelSQL, ModelView):
    'Calculated Typification'
    __name__ = 'lims.typification.calculated.readonly'

    product_type = fields.Many2One('lims.product.type', 'Product type',
        readonly=True)
    matrix = fields.Many2One('lims.matrix', 'Matrix', readonly=True)
    analysis = fields.Many2One('lims.analysis', 'Analysis', readonly=True)

    @classmethod
    def __setup__(cls):
        super(CalculatedTypificationReadOnly, cls).__setup__()
        cls._order.insert(0, ('product_type', 'ASC'))
        cls._order.insert(1, ('matrix', 'ASC'))
        cls._order.insert(2, ('analysis', 'ASC'))

    @staticmethod
    def table_query():
        pool = Pool()
        typification = pool.get('lims.typification.calculated').__table__()

        columns = [
            typification.id,
            typification.create_uid,
            typification.create_date,
            typification.write_uid,
            typification.write_date,
            typification.product_type,
            typification.matrix,
            typification.analysis,
            ]
        where = Literal(True)
        return typification.select(*columns, where=where)


class ProductType(ModelSQL, ModelView):
    'Product Type'
    __name__ = 'lims.product.type'
    _rec_name = 'description'

    code = fields.Char('Code', required=True)
    description = fields.Char('Description', required=True)
    restricted_entry = fields.Boolean('Restricted entry')

    @classmethod
    def __setup__(cls):
        super(ProductType, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code),
                'Product type code must be unique'),
            ]

    @staticmethod
    def default_restricted_entry():
        return False

    def get_rec_name(self, name):
        if self.code:
            return self.code + ' - ' + self.description
        else:
            return self.description

    @classmethod
    def search_rec_name(cls, name, clause):
        field = None
        for field in ('code', 'description'):
            records = cls.search([(field,) + tuple(clause[1:])], limit=1)
            if records:
                break
        if records:
            return [(field,) + tuple(clause[1:])]
        return [(cls._rec_name,) + tuple(clause[1:])]


class Matrix(ModelSQL, ModelView):
    'Matrix'
    __name__ = 'lims.matrix'
    _rec_name = 'description'

    code = fields.Char('Code', required=True)
    description = fields.Char('Description', required=True)
    restricted_entry = fields.Boolean('Restricted entry')

    @classmethod
    def __setup__(cls):
        super(Matrix, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code),
                'Matrix code must be unique'),
            ]

    @staticmethod
    def default_restricted_entry():
        return False

    def get_rec_name(self, name):
        if self.code:
            return self.code + ' - ' + self.description
        else:
            return self.description

    @classmethod
    def search_rec_name(cls, name, clause):
        field = None
        for field in ('code', 'description'):
            records = cls.search([(field,) + tuple(clause[1:])], limit=1)
            if records:
                break
        if records:
            return [(field,) + tuple(clause[1:])]
        return [(cls._rec_name,) + tuple(clause[1:])]


class ObjectiveDescription(ModelSQL, ModelView):
    'Objective Description'
    __name__ = 'lims.objective_description'
    _rec_name = 'description'

    product_type = fields.Many2One('lims.product.type', 'Product type',
        required=True, select=True,
        states={'readonly': Bool(Eval('id', 0) > 0)})
    matrix = fields.Many2One('lims.matrix', 'Matrix',
        required=True, select=True,
        states={'readonly': Bool(Eval('id', 0) > 0)})
    description = fields.Char('Description', required=True, translate=True)

    @classmethod
    def __setup__(cls):
        super(ObjectiveDescription, cls).__setup__()
        cls._order.insert(0, ('product_type', 'ASC'))
        cls._order.insert(1, ('matrix', 'ASC'))
        cls._order.insert(2, ('description', 'ASC'))
        t = cls.__table__()
        cls._sql_constraints += [
            ('product_matrix_uniq', Unique(t, t.product_type, t.matrix),
                'This objective description already exists'),
            ]


class Formula(ModelSQL, ModelView):
    'Formula'
    __name__ = 'lims.formula'

    name = fields.Char('Name', required=True)
    formula = fields.Char('Formula', required=True)
    variables = fields.One2Many('lims.formula.variable', 'formula',
        'Variables', required=True)


class FormulaVariable(ModelSQL, ModelView):
    'Formula Variable'
    __name__ = 'lims.formula.variable'

    formula = fields.Many2One('lims.formula', 'Formula', required=True,
        ondelete='CASCADE', select=True)
    number = fields.Char('Number', required=True)
    description = fields.Char('Description', required=True)
    fraction_type = fields.Many2One('lims.fraction.type', 'Fraction type')
    constant = fields.Char('Constant')


class Analysis(Workflow, ModelSQL, ModelView):
    'Analysis/Set/Group'
    __name__ = 'lims.analysis'
    _rec_name = 'description'

    code = fields.Char('Code', required=True,
        states={'readonly': Eval('state') != 'draft'}, depends=['state'])
    description = fields.Char('Description', required=True, translate=True,
        states={'readonly': Bool(Equal(Eval('state'), 'disabled'))},
        depends=['state'])
    type = fields.Selection([
        ('analysis', 'Analysis'),
        ('set', 'Set'),
        ('group', 'Group'),
        ], 'Type', sort=False, required=True,
        states={'readonly': Eval('state') != 'draft'}, depends=['state'])
    laboratories = fields.One2Many('lims.analysis-laboratory', 'analysis',
        'Laboratories', context={'type': Eval('type')},
        states={
            'invisible': Or(
                Eval('type').in_(['group']),
                Bool(Equal(Eval('behavior'), 'additional'))),
            'required': Not(Or(
                Eval('type').in_(['set', 'group']),
                Bool(Equal(Eval('behavior'), 'additional')))),
            'readonly': Bool(Equal(Eval('state'), 'disabled')),
            }, depends=['type', 'behavior', 'state'])
    laboratory_domain = fields.Function(fields.Many2Many('lims.laboratory',
        None, None, 'Laboratories'), 'on_change_with_laboratory_domain')
    methods = fields.Many2Many('lims.analysis-lab.method', 'analysis',
        'method', 'Methods', states={
            'invisible': Or(
                Eval('type').in_(['set', 'group']),
                Bool(Equal(Eval('behavior'), 'additional'))),
            'required': Not(Or(
                Eval('type').in_(['set', 'group']),
                Bool(Equal(Eval('behavior'), 'additional')))),
            'readonly': Bool(Equal(Eval('state'), 'disabled')),
            }, depends=['type', 'behavior', 'state'])
    devices = fields.One2Many('lims.analysis.device', 'analysis', 'Devices',
        context={'laboratory_domain': Eval('laboratory_domain')},
        states={
            'invisible': Or(
                Eval('type').in_(['set', 'group']),
                Bool(Equal(Eval('behavior'), 'additional'))),
            'readonly': Bool(Equal(Eval('state'), 'disabled')),
            }, depends=['type', 'behavior', 'laboratory_domain', 'state'])
    start_date = fields.Date('Entry date', readonly=True)
    end_date = fields.Date('Leaving date', readonly=True)
    included_analysis = fields.One2Many('lims.analysis.included', 'analysis',
        'Included analysis', context={
            'analysis': Eval('id'), 'type': Eval('type'),
            'laboratory_domain': Eval('laboratory_domain')},
        states={
            'invisible': Bool(Equal(Eval('type'), 'analysis')),
            'readonly': Bool(Equal(Eval('state'), 'disabled')),
            }, depends=['type', 'laboratory_domain', 'state'])
    all_included_analysis = fields.Function(fields.One2Many('lims.analysis',
        None, 'All included analysis'),
        'on_change_with_all_included_analysis')
    behavior = fields.Selection([
        ('normal', 'Normal'),
        ('internal_relation', 'Internal Relation'),
        ('additional', 'Additional'),
        ], 'Behavior', required=True, sort=False,
        states={
            'readonly': Or(
                Eval('type').in_(['set', 'group']),
                Eval('state') != 'draft',
                ),
            }, depends=['type', 'state'])
    result_formula = fields.Char('Result formula',
        states={
            'invisible': Not(
                Bool(Equal(Eval('behavior'), 'internal_relation'))),
            'required': Bool(Equal(Eval('behavior'), 'internal_relation')),
            'readonly': Bool(Equal(Eval('state'), 'disabled')),
            }, depends=['behavior', 'state'])
    converted_result_formula = fields.Char('Converted result formula',
        states={
            'invisible': Not(
                Bool(Equal(Eval('behavior'), 'internal_relation'))),
            'required': Bool(Equal(Eval('behavior'), 'internal_relation')),
            'readonly': Bool(Equal(Eval('state'), 'disabled')),
            }, depends=['behavior', 'state'])
    gender_species = fields.Text('Gender Species', translate=True,
        states={
            'invisible': Not(And(
                Bool(Equal(Eval('type'), 'analysis')),
                Bool(Equal(Eval('behavior'), 'normal')))),
            'readonly': Bool(Equal(Eval('state'), 'disabled')),
            }, depends=['type', 'behavior', 'state'])
    microbiology = fields.Function(fields.Boolean('Microbiology'),
        'on_change_with_microbiology')
    formula = fields.Many2One('lims.formula', 'Formula',
        states={
            'invisible': Not(And(
                Bool(Equal(Eval('type'), 'analysis')),
                Bool(Equal(Eval('behavior'), 'normal')))),
            'readonly': Bool(Equal(Eval('state'), 'disabled')),
            }, depends=['type', 'behavior', 'state'])
    product = fields.Many2One('product.product', 'Product')
    automatic_acquisition = fields.Boolean('Automatic acquisition',
        states={'readonly': Bool(Equal(Eval('state'), 'disabled'))},
        depends=['state'])
    order = fields.Integer('Order', states={
        'invisible': Not(And(
            Bool(Equal(Eval('type'), 'analysis')),
            Eval('behavior').in_(['normal', 'internal_relation']))),
        'readonly': Bool(Equal(Eval('state'), 'disabled')),
        }, depends=['type', 'behavior', 'state'])
    disable_as_individual = fields.Boolean(
        'Not allowed as individual service', states={
            'invisible': Not(And(
                Bool(Equal(Eval('type'), 'analysis')),
                Eval('behavior').in_(['normal', 'internal_relation']))),
            'readonly': Bool(Equal(Eval('state'), 'disabled')),
            },
        depends=['type', 'behavior', 'state'])
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('disabled', 'Disabled'),
        ], 'State', required=True, readonly=True)
    planning_legend = fields.Char('Planning legend',
    states={
            'invisible': Not(And(
                Bool(Equal(Eval('type'), 'analysis')),
                Bool(Equal(Eval('behavior'), 'normal')))),
            'readonly': Bool(Equal(Eval('state'), 'disabled')),
            }, depends=['type', 'behavior', 'state'])
    comments = fields.Text('Warnings/Comments')
    pending_fractions = fields.Function(fields.Integer('Pending fractions'),
        'get_pending_fractions', searcher='search_pending_fractions')

    @classmethod
    def __setup__(cls):
        super(Analysis, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code),
                'Analysis code must be unique'),
            ]
        cls._error_messages.update({
            'description_uniq': 'Analysis description must be unique',
            'not_laboratory': 'Must define a Laboratory',
            'set_laboratories': ('A Set can be assigned to a single'
                ' laboratory'),
            'analysis_laboratory': ('The "%(analysis)s" analysis is not'
                ' defined in laboratory "%(laboratory)s"'),
            'not_laboratory_change': ('You can not change the laboratory'
                ' because the analysis is included in a set/group with this'
                ' laboratory'),
            'end_date': 'The leaving date cannot be lower than entry date',
            'end_date_wrong': ('End date should not be greater than the '
                'current date'),
            })
        cls._transitions |= set((
            ('draft', 'active'),
            ('active', 'disabled'),
            ))
        cls._buttons.update({
            'relate_analysis': {
                'invisible': (Eval('type') != 'set'),
                'readonly': Bool(Equal(Eval('state'), 'disabled')),
                },
            'activate': {
                'invisible': (Eval('state') != 'draft'),
                },
            'disable': {
                'invisible': (Eval('state') != 'active'),
                },
            })

    @staticmethod
    def default_behavior():
        return 'normal'

    @staticmethod
    def default_automatic_acquisition():
        return False

    @staticmethod
    def default_disable_as_individual():
        return False

    @staticmethod
    def default_state():
        return 'draft'

    @fields.depends('type', 'behavior')
    def on_change_with_behavior(self, name=None):
        if self.type in ('set', 'group'):
            return 'normal'
        return self.behavior

    @fields.depends('laboratories')
    def on_change_with_laboratory_domain(self, name=None):
        if self.laboratories:
            return [l.laboratory.id for l in self.laboratories if l.laboratory]
        return []

    @fields.depends('included_analysis')
    def on_change_with_all_included_analysis(self, name=None):
        Analysis = Pool().get('lims.analysis')
        return Analysis.get_included_analysis(self.id)

    @classmethod
    def view_attributes(cls):
        return [
            ('//page[@id="microbiology"]', 'states', {
                    'invisible': Not(Bool(Eval('microbiology'))),
                    }),
            ('//group[@id="button_holder"]', 'states', {
                    'invisible': Eval('type') != 'set',
                    }),
            ('//page[@id="included_analysis"]', 'states', {
                    'invisible': Bool(Equal(Eval('type'), 'analysis')),
                    }),
            ('//page[@id="devices"]|//page[@id="methods"]',
                'states', {
                    'invisible': Or(
                        Eval('type').in_(['set', 'group']),
                        Bool(Equal(Eval('behavior'), 'additional'))),
                    }),
            ('//page[@id="laboratories"]',
                'states', {
                    'invisible': Or(
                        Eval('type').in_(['group']),
                        Bool(Equal(Eval('behavior'), 'additional'))),
                    }),
            ]

    @classmethod
    def get_included_analysis(cls, analysis_id):
        cursor = Transaction().connection.cursor()
        AnalysisIncluded = Pool().get('lims.analysis.included')

        childs = []
        cursor.execute('SELECT included_analysis '
            'FROM "' + AnalysisIncluded._table + '" '
            'WHERE analysis = %s', (analysis_id,))
        included_analysis_ids = [x[0] for x in cursor.fetchall()]
        if included_analysis_ids:
            for analysis_id in included_analysis_ids:
                if analysis_id not in childs:
                    childs.append(analysis_id)
                    childs.extend(cls.get_included_analysis(analysis_id))
        return childs

    @classmethod
    def get_included_analysis_analysis(cls, analysis_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        AnalysisIncluded = pool.get('lims.analysis.included')
        Analysis = pool.get('lims.analysis')

        childs = []
        cursor.execute('SELECT ia.included_analysis, a.type '
            'FROM "' + AnalysisIncluded._table + '" ia '
                'INNER JOIN "' + Analysis._table + '" a '
                'ON a.id = ia.included_analysis '
            'WHERE analysis = %s', (analysis_id,))
        included_analysis = cursor.fetchall()
        if included_analysis:
            for analysis in included_analysis:
                if analysis[1] == 'analysis' and analysis[0] not in childs:
                    childs.append(analysis[0])
                childs.extend(cls.get_included_analysis_analysis(analysis[0]))
        return childs

    @classmethod
    def get_parents_analysis(cls, analysis_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        AnalysisIncluded = pool.get('lims.analysis.included')
        Analysis = pool.get('lims.analysis')

        parents = []
        cursor.execute('SELECT ia.analysis '
            'FROM "' + AnalysisIncluded._table + '" ia '
                'INNER JOIN "' + Analysis._table + '" a '
                'ON a.id = ia.analysis '
            'WHERE ia.included_analysis = %s '
                'AND a.state = \'active\'', (analysis_id,))
        parents_analysis_ids = [x[0] for x in cursor.fetchall()]
        if parents_analysis_ids:
            for analysis_id in parents_analysis_ids:
                if analysis_id not in parents:
                    parents.append(analysis_id)
                    parents.extend(cls.get_parents_analysis(analysis_id))
        return parents

    def get_rec_name(self, name):
        if self.code:
            return self.code + ' - ' + self.description
        else:
            return self.description

    @classmethod
    def search_rec_name(cls, name, clause):
        field = None
        for field in ('code', 'description'):
            records = cls.search([(field,) + tuple(clause[1:])], limit=1)
            if records:
                break
        if records:
            return [(field,) + tuple(clause[1:])]
        return [(cls._rec_name,) + tuple(clause[1:])]

    @classmethod
    def validate(cls, analysis):
        super(Analysis, cls).validate(analysis)
        for a in analysis:
            cls.check_duplicate_description(a.type, a.description)
            a.check_set()
            a.check_end_date()

    @classmethod
    def check_duplicate_description(cls, type, description, count=1):
        if cls.search_count([
                ('description', '=', description),
                ('type', '=', type),
                ('end_date', '=', None),
                ]) > count:
            cls.raise_user_error('description_uniq')

    def check_set(self):
        if self.type == 'set':
            if self.laboratories and len(self.laboratories) > 1:
                self.raise_user_error('set_laboratories')
            if self.included_analysis and not self.laboratories:
                self.raise_user_error('not_laboratory')
            if self.included_analysis:
                set_laboratory = self.laboratories[0].laboratory
                for ia in self.included_analysis:
                    included_analysis_laboratories = [lab.laboratory
                        for lab in ia.included_analysis.laboratories]
                    if (set_laboratory not in included_analysis_laboratories):
                        self.raise_user_error('analysis_laboratory', {
                            'analysis': ia.included_analysis.rec_name,
                            'laboratory': set_laboratory.rec_name,
                            })

    def check_end_date(self):
        if self.end_date:
            if not self.start_date or self.end_date < self.start_date:
                self.raise_user_error('end_date')
            if not self.start_date or self.end_date > datetime.now().date():
                self.raise_user_error('end_date_wrong')

    @classmethod
    def write(cls, *args):
        actions = iter(args)
        for analysis, vals in zip(actions, actions):
            if vals.get('laboratories'):
                cls.check_laboratory_change(analysis, vals['laboratories'])
            if vals.get('description'):
                for a in analysis:
                    cls.check_duplicate_description(vals.get('type', a.type),
                        vals['description'], 0)
        super(Analysis, cls).write(*args)

    @classmethod
    def check_laboratory_change(cls, analysis, laboratories):
        AnalysisIncluded = Pool().get('lims.analysis.included')

        for a in analysis:
            if a.type == 'analysis':
                for operation in laboratories:
                    if operation[0] == 'unlink':
                        for laboratory in operation[1]:
                            parent = AnalysisIncluded.search([
                                ('included_analysis', '=', a.id),
                                ('laboratory', '=', laboratory),
                                ])
                            if parent:
                                cls.raise_user_error('not_laboratory_change')

    @classmethod
    @ModelView.button_action('lims.wiz_lims_relate_analysis')
    def relate_analysis(cls, analysis):
        pass

    @classmethod
    @ModelView.button
    @Workflow.transition('active')
    def activate(cls, analysis):
        Date = Pool().get('ir.date')
        cls.write(analysis, {'start_date': Date.today()})
        cls.create_typification_calculated(analysis)
        cls.create_product(analysis)

    @classmethod
    @ModelView.button
    @Workflow.transition('disabled')
    def disable(cls, analysis):
        Date = Pool().get('ir.date')
        cls.write(analysis, {'end_date': Date.today()})
        cls.disable_typifications(analysis)
        cls.delete_included_analysis(analysis)
        cls.disable_product(analysis)

    @classmethod
    def create_typification_calculated(cls, analysis):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Analysis = pool.get('lims.analysis')
        Typification = pool.get('lims.typification')
        CalculatedTypification = pool.get('lims.typification.calculated')

        for included in analysis:
            if included.type == 'analysis':
                continue
            sets_groups_ids = [included.id]
            sets_groups_ids.extend(Analysis.get_parents_analysis(
                included.id))
            for set_group_id in sets_groups_ids:

                ia = Analysis.get_included_analysis_analysis(
                    set_group_id)
                if not ia:
                    continue
                included_ids = ', '.join(str(a) for a in ia)

                cursor.execute('SELECT DISTINCT(product_type, matrix) '
                    'FROM "' + Typification._table + '" '
                    'WHERE valid '
                        'AND analysis IN (' + included_ids + ')')
                typifications = cursor.fetchall()
                if not typifications:
                    continue

                for typification in typifications:

                    product_type = int(typification[0].split(',')[0][1:])
                    matrix = int(typification[0].split(',')[1][:-1])
                    cursor.execute('SELECT DISTINCT(analysis) '
                        'FROM "' + Typification._table + '" '
                        'WHERE product_type = %s '
                            'AND matrix = %s '
                            'AND valid',
                        (product_type, matrix))
                    typified_analysis = [a[0] for a in cursor.fetchall()]
                    typified_analysis_ids = ', '.join(str(a) for a in
                        typified_analysis)

                    cursor.execute('SELECT id '
                        'FROM "' + Analysis._table + '" '
                        'WHERE id IN (' + included_ids + ') '
                            'AND id NOT IN (' + typified_analysis_ids +
                            ')')
                    if cursor.fetchone():
                        typified = False
                    else:
                        typified = True

                    if typified:
                        t_set_group = CalculatedTypification.search([
                            ('product_type', '=', product_type),
                            ('matrix', '=', matrix),
                            ('analysis', '=', set_group_id),
                            ])
                        if not t_set_group:
                            typification_create = [{
                                'product_type': product_type,
                                'matrix': matrix,
                                'analysis': set_group_id,
                                }]
                            CalculatedTypification.create(
                                typification_create)
                    else:
                        t_set_group = CalculatedTypification.search([
                            ('product_type', '=', product_type),
                            ('matrix', '=', matrix),
                            ('analysis', '=', set_group_id),
                            ])
                        if t_set_group:
                            CalculatedTypification.delete(t_set_group)

        return analysis

    @classmethod
    def create_product(cls, analysis):
        CreateProduct = Pool().get('lims.create_analysis_product',
            type='wizard')
        s_analysis, = analysis
        session_id, _, _ = CreateProduct.create()
        create_product = CreateProduct(session_id)
        with Transaction().set_context(active_id=s_analysis.id):
            create_product.transition_start()

    @classmethod
    def disable_typifications(cls, analysis):
        pool = Pool()
        Typification = pool.get('lims.typification')
        CalculatedTypification = pool.get('lims.typification.calculated')

        analysis_ids = []
        sets_groups_ids = []
        for a in analysis:
            if a.type == 'analysis':
                analysis_ids.append(a.id)
            else:
                sets_groups_ids.append(a.id)
        if analysis_ids:
            typifications = Typification.search([
                ('analysis', 'in', analysis_ids),
                ])
            if typifications:
                Typification.write(typifications, {'valid': False})
        if sets_groups_ids:
            typifications = CalculatedTypification.search([
                ('analysis', 'in', sets_groups_ids),
                ])
            if typifications:
                CalculatedTypification.delete(typifications)

    @classmethod
    def delete_included_analysis(cls, analysis):
        AnalysisIncluded = Pool().get('lims.analysis.included')
        analysis_ids = [a.id for a in analysis]
        if analysis_ids:
            included_delete = AnalysisIncluded.search([
                ('included_analysis', 'in', analysis_ids),
                ])
            if included_delete:
                AnalysisIncluded.delete(included_delete)

    @classmethod
    def disable_product(cls, analysis):
        pool = Pool()
        Product = pool.get('product.product')
        Template = pool.get('product.template')

        products = []
        templates = []
        for a in analysis:
            if a.product:
                products.append(a.product)
                templates.append(a.product.template)
        if products:
            Product.write(products, {'active': False})
            Template.write(templates, {'active': False})

    @fields.depends('laboratories')
    def on_change_with_microbiology(self, name=None):
        Config = Pool().get('lims.configuration')

        config_ = Config(1)
        if not config_.microbiology_laboratories:
            return False

        if self.laboratories:
            for lab in self.laboratories:
                if lab.laboratory in config_.microbiology_laboratories:
                    return True
        return False

    @staticmethod
    def is_typified(analysis, product_type, matrix):
        pool = Pool()
        Typification = pool.get('lims.typification')
        CalculatedTypification = pool.get('lims.typification.calculated')

        if analysis.type == 'analysis':
            typified_service = Typification.search([
                ('analysis', '=', analysis.id),
                ('product_type', '=', product_type.id),
                ('matrix', '=', matrix.id),
                ('valid', '=', True),
                ])
            if typified_service:
                return True
        else:
            typified_service = CalculatedTypification.search([
                ('analysis', '=', analysis.id),
                ('product_type', '=', product_type.id),
                ('matrix', '=', matrix.id),
                ])
            if typified_service:
                return True
        return False

    @classmethod
    def copy(cls, analysis, default=None):
        if default is None:
            default = {}
        current_default = default.copy()
        current_default['state'] = 'draft'
        current_default['start_date'] = None
        current_default['end_date'] = None
        return super(Analysis, cls).copy(analysis, default=current_default)

    @classmethod
    def get_pending_fractions(cls, records, name):
        context = Transaction().context

        date_from = context.get('date_from') or None
        date_to = context.get('date_to') or None
        calculate = context.get('calculate', True)
        if not (date_from and date_to) or not calculate:
            return dict((r.id, None) for r in records)

        new_context = {}
        new_context['date_from'] = date_from
        new_context['date_to'] = date_to
        with Transaction().set_context(new_context):
            return cls.analysis_pending_fractions([r.id for r in records])

    @classmethod
    def search_pending_fractions(cls, name, domain=None):
        context = Transaction().context

        date_from = context.get('date_from') or None
        date_to = context.get('date_to') or None
        calculate = context.get('calculate', True)
        if not (date_from and date_to) or not calculate:
            return []

        new_context = {}
        new_context['date_from'] = date_from
        new_context['date_to'] = date_to
        with Transaction().set_context(new_context):
            pending_fractions = iter(cls.analysis_pending_fractions().items())

        processed_lines = []
        for analysis, pending in pending_fractions:
            processed_lines.append({
                'analysis': analysis,
                'pending_fractions': pending,
                })

        record_ids = [line['analysis'] for line in processed_lines
            if cls._search_pending_fractions_eval_domain(line, domain)]
        return [('id', 'in', record_ids)]

    @classmethod
    def analysis_pending_fractions(cls, analysis_ids=None):
        cursor = Transaction().connection.cursor()
        context = Transaction().context
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        PlanificationServiceDetail = pool.get(
            'lims.planification.service_detail')
        PlanificationDetail = pool.get('lims.planification.detail')
        Planification = pool.get('lims.planification')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        Analysis = pool.get('lims.analysis')
        Service = pool.get('lims.service')
        Fraction = pool.get('lims.fraction')
        FractionType = pool.get('lims.fraction.type')

        date_from = context.get('date_from')
        date_to = context.get('date_to')

        preplanned_clause = ''
        cursor.execute('SELECT DISTINCT(nl.service) '
            'FROM "' + NotebookLine._table + '" nl '
                'INNER JOIN "' + PlanificationServiceDetail._table +
                '" psd ON psd.notebook_line = nl.id '
                'INNER JOIN "' + PlanificationDetail._table + '" pd '
                'ON psd.detail = pd.id '
                'INNER JOIN "' + Planification._table + '" p '
                'ON pd.planification = p.id '
            'WHERE p.state = \'preplanned\'')
        preplanned_services = [s[0] for s in cursor.fetchall()]
        if preplanned_services:
            preplanned_services_ids = ', '.join(str(s) for s in
                    preplanned_services)
            preplanned_clause = ('AND service.id NOT IN (' +
                preplanned_services_ids + ')')

        not_planned_services_clause = ''
        cursor.execute('SELECT DISTINCT(d.service) '
            'FROM "' + EntryDetailAnalysis._table + '" d '
                'INNER JOIN "' + Analysis._table + '" a '
                'ON a.id = d.analysis '
            'WHERE d.state IN (\'draft\', \'unplanned\') '
                'AND a.behavior != \'internal_relation\'')
        not_planned_services = [s[0] for s in cursor.fetchall()]
        if not_planned_services:
            not_planned_services_ids = ', '.join(str(s) for s in
                not_planned_services)
            not_planned_services_clause = ('AND id IN (' +
                not_planned_services_ids + ')')

        if analysis_ids:
            all_analysis_ids = analysis_ids
        else:
            cursor.execute('SELECT id FROM "' + cls._table + '"')
            all_analysis_ids = [a[0] for a in cursor.fetchall()]

        res = {}
        for analysis_id in all_analysis_ids:
            count = 0
            cursor.execute('SELECT service.id '
                'FROM "' + Service._table + '" service '
                    'INNER JOIN "' + Fraction._table + '" fraction '
                    'ON fraction.id = service.fraction '
                    'INNER JOIN "' + FractionType._table + '" f_type '
                    'ON f_type.id = fraction.type '
                'WHERE service.analysis = %s '
                    'AND confirmation_date::date >= %s::date '
                    'AND confirmation_date::date <= %s::date '
                    'AND fraction.confirmed = TRUE '
                    'AND f_type.plannable = TRUE ' +
                    preplanned_clause,
                (analysis_id, date_from, date_to))
            pending_services = [s[0] for s in cursor.fetchall()]
            if pending_services:
                pending_services_ids = ', '.join(str(s) for s in
                    pending_services)
                cursor.execute('SELECT COUNT(*) '
                    'FROM "' + Service._table + '" '
                    'WHERE id IN (' + pending_services_ids + ') ' +
                        not_planned_services_clause)
                count = cursor.fetchone()[0]

            res[analysis_id] = count
        return res

    @staticmethod
    def _search_pending_fractions_eval_domain(line, domain):
        operator_funcs = {
            '=': operator.eq,
            '>=': operator.ge,
            '>': operator.gt,
            '<=': operator.le,
            '<': operator.lt,
            '!=': operator.ne,
            'in': lambda v, l: v in l,
            'not in': lambda v, l: v not in l,
            }
        field, op, operand = domain
        value = line.get(field)
        return operator_funcs[op](value, operand)


class AnalysisIncluded(ModelSQL, ModelView):
    'Included Analysis'
    __name__ = 'lims.analysis.included'

    analysis = fields.Many2One('lims.analysis', 'Analysis', required=True,
        ondelete='CASCADE', select=True)
    included_analysis = fields.Many2One('lims.analysis', 'Included analysis',
        required=True, depends=['analysis_domain'], domain=[
            ('id', 'in', Eval('analysis_domain')),
            ])
    analysis_domain = fields.Function(fields.Many2Many('lims.analysis',
        None, None, 'Analysis domain'),
        'on_change_with_analysis_domain')
    analysis_type = fields.Function(fields.Selection([
        ('analysis', 'Analysis'),
        ('set', 'Set'),
        ('group', 'Group'),
        ], 'Type', sort=False),
        'on_change_with_analysis_type')
    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        domain=[('id', 'in', Eval('laboratory_domain'))],
        states={
            'required': Or(
                Bool(Equal(Eval('_parent_analysis', {}).get('type'), 'set')),
                And(Bool(Equal(Eval('_parent_analysis', {}).get('type'),
                    'group')),
                    Bool(Equal(Eval('analysis_type'), 'analysis'))),
                Bool(Eval('laboratory_domain'))),
            'readonly': Bool(
                Equal(Eval('_parent_analysis', {}).get('type'), 'set')),
            'invisible': Eval('analysis_type').in_(['set', 'group']),
            },
        depends=['laboratory_domain', 'analysis_type'])
    laboratory_domain = fields.Function(fields.Many2Many('lims.laboratory',
        None, None, 'Laboratory domain'), 'on_change_with_laboratory_domain')

    @classmethod
    def __setup__(cls):
        super(AnalysisIncluded, cls).__setup__()
        cls._error_messages.update({
            'duplicated_analysis': 'The analysis "%s" is already included',
            'not_set_laboratory': 'No Laboratory loaded for the Set',
            })

    @classmethod
    def validate(cls, included_analysis):
        super(AnalysisIncluded, cls).validate(included_analysis)
        for analysis in included_analysis:
            analysis.check_duplicated_analysis()

    def check_duplicated_analysis(self):
        Analysis = Pool().get('lims.analysis')

        analysis_id = self.analysis.id
        included = self.search([
            ('analysis', '=', analysis_id),
            ('id', '!=', self.id)
            ])
        if included:
            analysis_ids = []
            for ai in included:
                if ai.included_analysis:
                    analysis_ids.append(ai.included_analysis.id)
                    analysis_ids.extend(Analysis.get_included_analysis(
                        ai.included_analysis.id))
            if self.included_analysis.id in analysis_ids:
                self.raise_user_error('duplicated_analysis',
                    (self.included_analysis.rec_name,))

    @fields.depends('included_analysis', 'analysis', 'laboratory',
        '_parent_analysis.type', '_parent_analysis.laboratories')
    def on_change_included_analysis(self):
        laboratory = None
        if self.included_analysis:
            laboratories = self.on_change_with_laboratory_domain()
            if len(laboratories) == 1:
                laboratory = laboratories[0]
        self.laboratory = laboratory

    @fields.depends('included_analysis')
    def on_change_with_analysis_type(self, name=None):
        res = ''
        if self.included_analysis:
            res = self.included_analysis.type
        return res

    @staticmethod
    def default_analysis_domain():
        AnalysisIncluded = Pool().get('lims.analysis.included')
        context = Transaction().context
        analysis_id = context.get('analysis', None)
        analysis_type = context.get('type', None)
        laboratories = context.get('laboratory_domain', [])
        return AnalysisIncluded.get_analysis_domain(analysis_id,
            analysis_type, laboratories)

    @fields.depends('analysis', '_parent_analysis.type',
        '_parent_analysis.laboratories')
    def on_change_with_analysis_domain(self, name=None):
        analysis_id = self.analysis.id if self.analysis else None
        analysis_type = self.analysis.type if self.analysis else None
        laboratories = []
        if self.analysis and self.analysis.laboratories:
            laboratories = [l.laboratory.id
                for l in self.analysis.laboratories]
        return self.get_analysis_domain(analysis_id,
            analysis_type, laboratories)

    @staticmethod
    def get_analysis_domain(analysis_id=None, analysis_type=None,
            laboratories=[]):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        AnalysisIncluded = pool.get('lims.analysis.included')
        Analysis = pool.get('lims.analysis')
        AnalysisLaboratory = pool.get('lims.analysis-laboratory')

        if not analysis_type:
            return []

        if analysis_type == 'set':
            if len(laboratories) != 1:
                AnalysisIncluded.raise_user_error('not_set_laboratory')
            set_laboratory_id = laboratories[0]
            not_parent_clause = ''
            if analysis_id:
                not_parent_clause = 'AND al.analysis != ' + str(analysis_id)

            cursor.execute('SELECT DISTINCT(al.analysis) '
                'FROM "' + AnalysisLaboratory._table + '" al '
                    'INNER JOIN "' + Analysis._table + '" a '
                    'ON a.id = al.analysis '
                'WHERE al.laboratory = %s '
                    'AND a.state = \'active\' '
                    'AND a.type = \'analysis\' '
                    'AND a.end_date IS NULL ' +
                    not_parent_clause,
                (set_laboratory_id,))
            res = cursor.fetchall()
            if not res:
                return []
            return [x[0] for x in res]
        else:
            not_parent_clause = ''
            if analysis_id:
                not_parent_clause = 'AND id != ' + str(analysis_id)
            cursor.execute('SELECT id '
                'FROM "' + Analysis._table + '" '
                'WHERE state = \'active\' '
                    'AND type != \'group\' '
                    'AND end_date IS NULL ' +
                    not_parent_clause)
            res = cursor.fetchall()
            if not res:
                return []
            return [x[0] for x in res]

    @staticmethod
    def default_laboratory_domain():
        return Transaction().context.get('laboratory_domain', [])

    @fields.depends('included_analysis', 'analysis', '_parent_analysis.type',
        '_parent_analysis.laboratories', 'laboratory')
    def on_change_with_laboratory_domain(self, name=None):
        laboratories = []
        analysis_laboratories = []
        if self.included_analysis and self.included_analysis.laboratories:
            analysis_laboratories = [l.laboratory.id
                for l in self.included_analysis.laboratories]
        if self.analysis and self.analysis.type == 'set':
            if self.analysis.laboratories:
                set_laboratory = self.analysis.laboratories[0].laboratory.id
                if set_laboratory in analysis_laboratories:
                    laboratories = [set_laboratory]
        else:
            laboratories = analysis_laboratories
        if not laboratories and self.laboratory:
            laboratories = [self.laboratory.id]
        return laboratories

    @classmethod
    def create(cls, vlist):
        included_analysis = super(AnalysisIncluded, cls).create(vlist)
        cls.create_typification_calculated(included_analysis)
        return included_analysis

    @classmethod
    def create_typification_calculated(cls, included_analysis):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Analysis = pool.get('lims.analysis')
        Typification = pool.get('lims.typification')
        CalculatedTypification = pool.get('lims.typification.calculated')

        for included in included_analysis:
            if included.analysis.state != 'active':
                continue
            sets_groups_ids = [included.analysis.id]
            sets_groups_ids.extend(Analysis.get_parents_analysis(
                included.analysis.id))
            for set_group_id in sets_groups_ids:

                ia = Analysis.get_included_analysis_analysis(
                    set_group_id)
                if not ia:
                    continue
                included_ids = ', '.join(str(a) for a in ia)

                cursor.execute('SELECT DISTINCT(product_type, matrix) '
                    'FROM "' + Typification._table + '" '
                    'WHERE valid '
                        'AND analysis IN (' + included_ids + ')')
                typifications = cursor.fetchall()
                if not typifications:
                    continue

                for typification in typifications:

                    product_type = int(typification[0].split(',')[0][1:])
                    matrix = int(typification[0].split(',')[1][:-1])
                    cursor.execute('SELECT DISTINCT(analysis) '
                        'FROM "' + Typification._table + '" '
                        'WHERE product_type = %s '
                            'AND matrix = %s '
                            'AND valid',
                        (product_type, matrix))
                    typified_analysis = [a[0] for a in cursor.fetchall()]
                    typified_analysis_ids = ', '.join(str(a) for a in
                        typified_analysis)

                    cursor.execute('SELECT id '
                        'FROM "' + Analysis._table + '" '
                        'WHERE id IN (' + included_ids + ') '
                            'AND id NOT IN (' + typified_analysis_ids +
                            ')')
                    if cursor.fetchone():
                        typified = False
                    else:
                        typified = True

                    if typified:
                        t_set_group = CalculatedTypification.search([
                            ('product_type', '=', product_type),
                            ('matrix', '=', matrix),
                            ('analysis', '=', set_group_id),
                            ])
                        if not t_set_group:
                            typification_create = [{
                                'product_type': product_type,
                                'matrix': matrix,
                                'analysis': set_group_id,
                                }]
                            CalculatedTypification.create(
                                typification_create)
                    else:
                        t_set_group = CalculatedTypification.search([
                            ('product_type', '=', product_type),
                            ('matrix', '=', matrix),
                            ('analysis', '=', set_group_id),
                            ])
                        if t_set_group:
                            CalculatedTypification.delete(t_set_group)

        return included_analysis

    @classmethod
    def delete(cls, included_analysis):
        cls.delete_typification_calculated(included_analysis)
        super(AnalysisIncluded, cls).delete(included_analysis)

    @classmethod
    def delete_typification_calculated(cls, included_analysis):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Analysis = pool.get('lims.analysis')
        Typification = pool.get('lims.typification')
        CalculatedTypification = pool.get('lims.typification.calculated')

        for included in included_analysis:
            if included.analysis.state != 'active':
                continue
            if included.included_analysis.type == 'analysis':
                deleted_analysis = [included.included_analysis.id]
            else:
                deleted_analysis = (
                    Analysis.get_included_analysis_analysis(
                        included.included_analysis.id))

            sets_groups_ids = [included.analysis.id]
            sets_groups_ids.extend(Analysis.get_parents_analysis(
                included.analysis.id))
            for set_group_id in sets_groups_ids:
                typified = True

                ia = Analysis.get_included_analysis_analysis(
                    set_group_id)
                if deleted_analysis:
                    for da in deleted_analysis:
                        if da in ia:
                            ia.remove(da)
                if not ia:
                    continue
                included_ids = ', '.join(str(a) for a in ia)

                cursor.execute('SELECT DISTINCT(product_type, matrix) '
                    'FROM "' + Typification._table + '" '
                    'WHERE valid '
                        'AND analysis IN (' + included_ids + ')')
                typifications = cursor.fetchall()
                if not typifications:
                    continue

                for typification in typifications:

                    product_type = int(typification[0].split(',')[0][1:])
                    matrix = int(typification[0].split(',')[1][:-1])
                    cursor.execute('SELECT DISTINCT(analysis) '
                        'FROM "' + Typification._table + '" '
                        'WHERE product_type = %s '
                            'AND matrix = %s '
                            'AND valid',
                        (product_type, matrix))
                    typified_analysis = [a[0] for a in cursor.fetchall()]
                    typified_analysis_ids = ', '.join(str(a) for a in
                        typified_analysis)

                    cursor.execute('SELECT id '
                        'FROM "' + Analysis._table + '" '
                        'WHERE id IN (' + included_ids + ') '
                            'AND id NOT IN (' + typified_analysis_ids +
                            ')')
                    if cursor.fetchone():
                        typified = False
                    else:
                        typified = True

                    if typified:
                        t_set_group = CalculatedTypification.search([
                            ('product_type', '=', product_type),
                            ('matrix', '=', matrix),
                            ('analysis', '=', set_group_id),
                            ])
                        if not t_set_group:
                            typification_create = [{
                                'product_type': product_type,
                                'matrix': matrix,
                                'analysis': set_group_id,
                                }]
                            CalculatedTypification.create(
                                typification_create)
                    else:
                        t_set_group = CalculatedTypification.search([
                            ('product_type', '=', product_type),
                            ('matrix', '=', matrix),
                            ('analysis', '=', set_group_id),
                            ])
                        if t_set_group:
                            CalculatedTypification.delete(t_set_group)

    @classmethod
    def search_rec_name(cls, name, clause):
        return ['OR',
            ('included_analysis.code',) + tuple(clause[1:]),
            ('included_analysis.description',) + tuple(clause[1:]),
            ]


class AnalysisLaboratory(ModelSQL, ModelView):
    'Analysis - Laboratory'
    __name__ = 'lims.analysis-laboratory'

    analysis = fields.Many2One('lims.analysis', 'Analysis',
        ondelete='CASCADE', select=True, required=True)
    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        ondelete='CASCADE', select=True, required=True)
    department = fields.Many2One('company.department', 'Department',
        states={'readonly': ~Equal(Eval('context', {}).get('type', ''),
            'analysis')})


class AnalysisLabMethod(ModelSQL):
    'Analysis - Laboratory Method'
    __name__ = 'lims.analysis-lab.method'

    analysis = fields.Many2One('lims.analysis', 'Analysis',
        ondelete='CASCADE', select=True, required=True)
    method = fields.Many2One('lims.lab.method', 'Method',
        ondelete='CASCADE', select=True, required=True)

    @classmethod
    def __setup__(cls):
        super(AnalysisLabMethod, cls).__setup__()
        cls._error_messages.update({
            'typificated_method': ('You can not delete method "%s" because '
                'is typificated'),
            })

    @classmethod
    def delete(cls, methods):
        cls.check_delete(methods)
        super(AnalysisLabMethod, cls).delete(methods)

    @classmethod
    def check_delete(cls, methods):
        Typification = Pool().get('lims.typification')
        for method in methods:
            typifications = Typification.search_count([
                ('analysis', '=', method.analysis.id),
                ('method', '=', method.method.id),
                ('valid', '=', True),
                ])
            if typifications != 0:
                cls.raise_user_error('typificated_method',
                    (method.method.code,))


class AnalysisDevice(ModelSQL, ModelView):
    'Analysis Device'
    __name__ = 'lims.analysis.device'

    analysis = fields.Many2One('lims.analysis', 'Analysis', required=True,
        ondelete='CASCADE', select=True)
    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        required=True, domain=[('id', 'in', Eval('laboratory_domain'))],
        depends=['laboratory_domain'])
    laboratory_domain = fields.Function(fields.Many2Many('lims.laboratory',
        None, None, 'Laboratory domain'),
        'on_change_with_laboratory_domain')
    device = fields.Many2One('lims.lab.device', 'Device', required=True,
        domain=[('laboratories.laboratory', '=', Eval('laboratory'))],
        depends=['laboratory'])
    by_default = fields.Boolean('By default')

    @classmethod
    def __setup__(cls):
        super(AnalysisDevice, cls).__setup__()
        cls._error_messages.update({
            'default_device': ('There is already a default device for this'
            ' analysis on this laboratory'),
            })

    @staticmethod
    def default_by_default():
        return True

    @classmethod
    def validate(cls, devices):
        super(AnalysisDevice, cls).validate(devices)
        for d in devices:
            d.check_default()

    def check_default(self):
        if self.by_default:
            devices = self.search([
                ('analysis', '=', self.analysis.id),
                ('laboratory', '=', self.laboratory.id),
                ('by_default', '=', True),
                ('id', '!=', self.id),
                ])
            if devices:
                self.raise_user_error('default_device')

    @staticmethod
    def default_laboratory_domain():
        return Transaction().context.get('laboratory_domain', [])

    @fields.depends('analysis', '_parent_analysis.laboratories', 'laboratory')
    def on_change_with_laboratory_domain(self, name=None):
        laboratories = []
        if self.analysis and self.analysis.laboratories:
            laboratories = [l.laboratory.id for l in
                self.analysis.laboratories]
        if not laboratories and self.laboratory:
            laboratories = [self.laboratory.id]
        return laboratories

    @classmethod
    def search_rec_name(cls, name, clause):
        return ['OR',
            ('laboratory.code',) + tuple(clause[1:]),
            ('laboratory.description',) + tuple(clause[1:]),
            ]


class CopyTypificationStart(ModelView):
    'Copy/Move Typification'
    __name__ = 'lims.typification.copy.start'

    origin_product_type = fields.Many2One('lims.product.type', 'Product type',
        required=True)
    origin_matrix = fields.Many2One('lims.matrix', 'Matrix', required=True)
    origin_analysis = fields.Many2One('lims.analysis', 'Analysis',
        domain=[
            ('state', '=', 'active'),
            ('type', '=', 'analysis'),
            ('behavior', '!=', 'additional'),
            ])
    origin_method = fields.Many2One('lims.lab.method', 'Method',
        states={'required': Bool(Eval('destination_method'))},
        depends=['destination_method'])
    destination_product_type = fields.Many2One('lims.product.type',
        'Product type', required=True)
    destination_matrix = fields.Many2One('lims.matrix', 'Matrix',
        required=True)
    destination_method = fields.Many2One('lims.lab.method', 'Method')
    action = fields.Selection([
        ('copy', 'Copy'),
        ('move', 'Move'),
        ], 'Action', required=True,
        help='If choose <Move>, the origin typifications will be deactivated')

    @staticmethod
    def default_action():
        return 'copy'


class CopyTypification(Wizard):
    'Copy/Move Typification'
    __name__ = 'lims.typification.copy'

    start = StateView('lims.typification.copy.start',
        'lims.lims_copy_typification_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Confirm', 'confirm', 'tryton-ok', default=True),
            ])
    confirm = StateTransition()

    def transition_confirm(self):
        Typification = Pool().get('lims.typification')

        clause = [
            ('product_type', '=', self.start.origin_product_type.id),
            ('matrix', '=', self.start.origin_matrix.id),
            ('valid', '=', True),
            ]
        if self.start.origin_analysis:
            clause.append(('analysis', '=', self.start.origin_analysis.id))
        if self.start.origin_method:
            clause.append(('method', '=', self.start.origin_method.id))

        product_type_id = self.start.destination_product_type.id
        matrix_id = self.start.destination_matrix.id
        method_id = (self.start.destination_method.id if
            self.start.destination_method else None)

        origins = Typification.search(clause)
        if origins and self.start.action == 'move':
            Typification.write(origins, {
                'valid': False,
                'by_default': False,
                })

        to_copy_1 = []
        to_copy_2 = []
        for origin in origins:
            if Typification.search_count([
                    ('product_type', '=', product_type_id),
                    ('matrix', '=', matrix_id),
                    ('analysis', '=', origin.analysis.id),
                    ('method', '=', method_id or origin.method.id)
                    ]) != 0:
                continue
            if Typification.search_count([
                    ('valid', '=', True),
                    ('product_type', '=', product_type_id),
                    ('matrix', '=', matrix_id),
                    ('analysis', '=', origin.analysis.id),
                    ('by_default', '=', True),
                    ]) != 0:
                to_copy_1.append(origin)
            else:
                to_copy_2.append(origin)

        if to_copy_1:
            default = {
                'valid': True,
                'product_type': product_type_id,
                'matrix': matrix_id,
                'by_default': False,
                }
            if method_id:
                default['method'] = method_id
                for r in to_copy_1:
                    method_domain = [m.id for m in r.analysis.methods]
                    if method_id not in method_domain:
                        to_copy_1.remove(r)
            Typification.copy(to_copy_1, default=default)
        if to_copy_2:
            default = {
                'valid': True,
                'product_type': product_type_id,
                'matrix': matrix_id,
                'by_default': True,
                }
            if method_id:
                default['method'] = method_id
                for r in to_copy_2:
                    method_domain = [m.id for m in r.analysis.methods]
                    if method_id not in method_domain:
                        to_copy_2.remove(r)
            Typification.copy(to_copy_2, default=default)
        return 'end'


class CopyCalculatedTypificationStart(ModelView):
    'Copy Typification'
    __name__ = 'lims.typification.calculated.copy.start'

    origin_product_type = fields.Many2One('lims.product.type', 'Product type',
        required=True)
    origin_matrix = fields.Many2One('lims.matrix', 'Matrix', required=True)
    origin_analysis = fields.Many2One('lims.analysis', 'Set/Group',
        required=True, domain=[
            ('state', '=', 'active'),
            ('type', 'in', ('set', 'group')),
            ])
    destination_product_type = fields.Many2One('lims.product.type',
        'Product type', required=True)
    destination_matrix = fields.Many2One('lims.matrix', 'Matrix',
        required=True)


class CopyCalculatedTypification(Wizard):
    'Copy Typification'
    __name__ = 'lims.typification.calculated.copy'

    start = StateView('lims.typification.calculated.copy.start',
        'lims.lims_copy_calculated_typification_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Confirm', 'confirm', 'tryton-ok', default=True),
            ])
    confirm = StateTransition()

    def transition_confirm(self):
        pool = Pool()
        Analysis = pool.get('lims.analysis')
        Typification = pool.get('lims.typification')

        included_analysis_ids = Analysis.get_included_analysis_analysis(
            self.start.origin_analysis.id)
        if not included_analysis_ids:
            return 'end'

        clause = [
            ('product_type', '=', self.start.origin_product_type.id),
            ('matrix', '=', self.start.origin_matrix.id),
            ('valid', '=', True),
            ('analysis', 'in', included_analysis_ids),
            ]

        product_type_id = self.start.destination_product_type.id
        matrix_id = self.start.destination_matrix.id

        origins = Typification.search(clause)

        to_copy_1 = []
        to_copy_2 = []
        for origin in origins:
            if Typification.search_count([
                    ('product_type', '=', product_type_id),
                    ('matrix', '=', matrix_id),
                    ('analysis', '=', origin.analysis.id),
                    ('method', '=', origin.method.id)
                    ]) != 0:
                continue
            if Typification.search_count([
                    ('valid', '=', True),
                    ('product_type', '=', product_type_id),
                    ('matrix', '=', matrix_id),
                    ('analysis', '=', origin.analysis.id),
                    ('by_default', '=', True),
                    ]) != 0:
                to_copy_1.append(origin)
            else:
                to_copy_2.append(origin)

        if to_copy_1:
            default = {
                'valid': True,
                'product_type': product_type_id,
                'matrix': matrix_id,
                'by_default': False,
                }
            Typification.copy(to_copy_1, default=default)
        if to_copy_2:
            default = {
                'valid': True,
                'product_type': product_type_id,
                'matrix': matrix_id,
                'by_default': True,
                }
            Typification.copy(to_copy_2, default=default)
        return 'end'


class RelateAnalysisStart(ModelView):
    'Relate Analysis'
    __name__ = 'lims.relate_analysis.start'

    analysis = fields.Many2Many('lims.analysis', None, None,
        'Analysis', required=True,
        domain=[('id', 'in', Eval('analysis_domain'))],
        depends=['analysis_domain'])
    analysis_domain = fields.One2Many('lims.analysis', None,
        'Analysis domain')


class RelateAnalysis(Wizard):
    'Relate Analysis'
    __name__ = 'lims.relate_analysis'

    start = StateView('lims.relate_analysis.start',
        'lims.lims_relate_analysis_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Relate', 'relate', 'tryton-ok', default=True),
            ])
    relate = StateTransition()

    @classmethod
    def __setup__(cls):
        super(RelateAnalysis, cls).__setup__()
        cls._error_messages.update({
            'not_set_laboratory': 'No Laboratory loaded for the Set',
            })

    def default_start(self, fields):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Analysis = pool.get('lims.analysis')
        AnalysisLaboratory = pool.get('lims.analysis-laboratory')

        analysis = Analysis(Transaction().context['active_id'])
        default = {
            'analysis_domain': [],
            }
        if len(analysis.laboratories) != 1:
            self.raise_user_error('not_set_laboratory')

        cursor.execute('SELECT DISTINCT(al.analysis) '
            'FROM "' + AnalysisLaboratory._table + '" al '
                'INNER JOIN "' + Analysis._table + '" a '
                'ON a.id = al.analysis '
            'WHERE al.laboratory = %s '
                'AND a.state = \'active\' '
                'AND a.type = \'analysis\' '
                'AND a.end_date IS NULL '
                'AND al.analysis != %s',
            (analysis.laboratories[0].laboratory.id, analysis.id,))
        res = cursor.fetchall()
        if res:
            default['analysis_domain'] = [x[0] for x in res]
        return default

    def transition_relate(self):
        Analysis = Pool().get('lims.analysis')
        analysis = Analysis(Transaction().context['active_id'])

        to_create = [{
            'analysis': analysis.id,
            'included_analysis': al.id,
            'laboratory': analysis.laboratories[0].laboratory.id,
            } for al in self.start.analysis]
        Analysis.write([analysis], {
            'included_analysis': [('create', to_create)],
            })
        return 'end'


class CreateAnalysisProduct(Wizard):
    'Create Analysis Product'
    __name__ = 'lims.create_analysis_product'

    start = StateTransition()

    def transition_start(self):
        pool = Pool()
        Template = pool.get('product.template')
        Product = pool.get('product.product')
        Analysis = pool.get('lims.analysis')
        Template = pool.get('product.template')
        TemplateCategory = pool.get('product.template-product.category')
        Uom = pool.get('product.uom')
        Lang = pool.get('ir.lang')
        Config = pool.get('lims.configuration')

        analysis = Analysis(Transaction().context['active_id'])

        if (analysis.type == 'analysis' and
                analysis.behavior == 'internal_relation'):
            return 'end'

        if analysis.product:
            return 'end'

        config_ = Config(1)
        uom = Uom.search(['OR',
            ('symbol', '=', 'u'),
            ('symbol', '=', 'x 1 u'),
            ])[0]

        template = Template()
        template.name = analysis.description
        template.type = 'service'
        template.list_price = Decimal('1.0')
        template.cost_price = Decimal('1.0')
        template.salable = True
        template.default_uom = uom
        template.sale_uom = uom
        template.account_category = config_.analysis_product_category.id
        template.accounts_category = True

        template.save()

        template_category = TemplateCategory()
        template_category.template = template.id
        template_category.category = config_.analysis_product_category.id
        template_category.save()

        product = Product()
        product.template = template.id
        product.code = analysis.code
        product.save()

        analysis.product = product
        analysis.save()

        lang, = Lang.search([
                ('code', '=', 'en'),
                ], limit=1)
        with Transaction().set_context(language=lang.code):
            template = Template(template.id)
            template.name = Analysis(analysis.id).description
            template.save()

        return 'end'


class OpenTypifications(Wizard):
    'Open Typifications'
    __name__ = 'lims.scope_version.open_typifications'

    start_state = 'open_'
    open_ = StateAction('lims.act_lims_typification_readonly_list')

    def do_open_(self, action):
        cursor = Transaction().connection.cursor()
        TechnicalScopeVersionLine = Pool().get(
            'lims.technical.scope.version.line')

        cursor.execute('SELECT typification '
            'FROM "' + TechnicalScopeVersionLine._table + '" '
            'WHERE version = %s', (Transaction().context['active_id'],))
        t_ids = [x[0] for x in cursor.fetchall()]

        action['pyson_domain'] = PYSONEncoder().encode([('id', 'in', t_ids)])
        return action, {}


class AddTypificationsStart(ModelView):
    'Add Typifications'
    __name__ = 'lims.scope_version.add_typifications.start'

    typifications = fields.Many2Many('lims.typification.readonly',
        None, None, 'Typifications', required=True)


class AddTypifications(Wizard):
    'Add Typifications'
    __name__ = 'lims.scope_version.add_typifications'

    start = StateView('lims.scope_version.add_typifications.start',
        'lims.scope_version_add_typifications_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Add', 'add', 'tryton-ok', default=True),
            ])
    add = StateTransition()

    def transition_add(self):
        TechnicalScopeVersion = Pool().get('lims.technical.scope.version')

        scope_version = TechnicalScopeVersion(
            Transaction().context['active_id'])
        TechnicalScopeVersion.write([scope_version], {
            'version_lines': [('remove',
                [t.id for t in self.start.typifications])],
            })
        TechnicalScopeVersion.write([scope_version], {
            'version_lines': [('add',
                [t.id for t in self.start.typifications])],
            })
        return 'end'


class RemoveTypificationsStart(ModelView):
    'Remove Typifications'
    __name__ = 'lims.scope_version.remove_typifications.start'

    typifications = fields.Many2Many('lims.typification.readonly',
        None, None, 'Typifications', required=True,
        domain=[('id', 'in', Eval('typifications_domain'))],
        depends=['typifications_domain'])
    typifications_domain = fields.One2Many('lims.typification.readonly',
        None, 'Typifications domain')


class RemoveTypifications(Wizard):
    'Remove Typifications'
    __name__ = 'lims.scope_version.remove_typifications'

    start = StateView('lims.scope_version.remove_typifications.start',
        'lims.scope_version_remove_typifications_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Remove', 'remove', 'tryton-ok', default=True),
            ])
    remove = StateTransition()

    def default_start(self, fields):
        cursor = Transaction().connection.cursor()
        TechnicalScopeVersionLine = Pool().get(
            'lims.technical.scope.version.line')

        cursor.execute('SELECT typification '
            'FROM "' + TechnicalScopeVersionLine._table + '" '
            'WHERE version = %s', (Transaction().context['active_id'],))
        t_ids = [x[0] for x in cursor.fetchall()]

        return {'typifications_domain': t_ids}

    def transition_remove(self):
        TechnicalScopeVersion = Pool().get('lims.technical.scope.version')

        scope_version = TechnicalScopeVersion(
            Transaction().context['active_id'])
        TechnicalScopeVersion.write([scope_version], {
            'version_lines': [('remove',
                [t.id for t in self.start.typifications])],
            })
        return 'end'
