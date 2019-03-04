# -*- coding: utf-8 -*-
# This file is part of lims module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import logging
from io import BytesIO
from math import sqrt

from trytond.model import ModelView, ModelSQL, fields
from trytond.wizard import Wizard, StateTransition, StateView, StateAction, \
    Button
from trytond.pyson import PYSONEncoder, Eval, Bool
from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.report import Report

__all__ = ['RangeType', 'Range', 'ControlTendency', 'ControlTendencyDetail',
    'ControlTendencyDetailRule', 'MeansDeviationsCalcStart',
    'MeansDeviationsCalcEmpty', 'MeansDeviationsCalcResult',
    'ControlResultLine', 'ControlResultLineDetail',
    'MeansDeviationsCalcResult2', 'MeansDeviationsCalc',
    'TendenciesAnalysisStart', 'TendenciesAnalysisResult',
    'TendenciesAnalysis', 'PrintControlChart', 'ControlChartReport']

CAN_PLOT = False
try:
    import pandas as pd
    CAN_PLOT = True
except ImportError:
    logging.getLogger(__name__).warning(
        'Unable to import pandas. Plotting disabled.', exc_info=True)


class RangeType(ModelSQL, ModelView):
    'Origins'
    __name__ = 'lims.range.type'

    code = fields.Char('Code', required=True)
    name = fields.Char('Name', required=True)
    use = fields.Selection([
        ('results_verification', 'Results verification'),
        ('uncertainty_calc', 'Uncertainty calculation'),
        ('repeatability_calc', 'Repeatability calculation'),
        ('result_range', 'Result and Ranges'),
        ], 'Use', sort=False, required=True)
    use_string = use.translated('use')
    by_default = fields.Boolean('By default')
    resultrange_title = fields.Char('Column Title in Results report',
        translate=True, states={'invisible': Eval('use') != 'result_range'},
        depends=['use'])
    resultrange_comments = fields.Char('Comments in Results report',
        translate=True, states={'invisible': Eval('use') != 'result_range'},
        depends=['use'])

    @classmethod
    def __setup__(cls):
        super(RangeType, cls).__setup__()
        cls._error_messages.update({
            'default_range_type':
                'There is already a default origin'
                ' for this use',
            })

    @staticmethod
    def default_by_default():
        return False

    @classmethod
    def validate(cls, range_types):
        super(RangeType, cls).validate(range_types)
        for rt in range_types:
            rt.check_default()

    def check_default(self):
        if self.by_default:
            range_types = self.search([
                ('use', '=', self.use),
                ('by_default', '=', True),
                ('id', '!=', self.id),
                ])
            if range_types:
                self.raise_user_error('default_range_type')


class Range(ModelSQL, ModelView):
    'Range'
    __name__ = 'lims.range'

    range_type = fields.Many2One('lims.range.type', 'Origin', required=True)
    analysis = fields.Many2One('lims.analysis', 'Analysis', required=True)
    product_type = fields.Many2One('lims.product.type', 'Product type',
        required=True)
    matrix = fields.Many2One('lims.matrix', 'Matrix', required=True)
    uom = fields.Many2One('product.uom', 'UoM', required=True,
        domain=[('category.lims_only_available', '=', True)])
    concentration = fields.Char('Concentration', required=True)
    min = fields.Float('Minimum', digits=(16, 3))
    max = fields.Float('Maximum', digits=(16, 3))
    reference = fields.Char('Reference', translate=True)
    min95 = fields.Float('Minimum 95', digits=(16, 3))
    max95 = fields.Float('Maximum 95', digits=(16, 3))
    low_level = fields.Float('Low level', digits=(16, 3),
        states={'required': Bool(Eval('low_level_value'))},
        depends=['low_level_value'])
    middle_level = fields.Float('Middle level', digits=(16, 3),
        states={'required': Bool(Eval('middle_level_value'))},
        depends=['middle_level_value'])
    high_level = fields.Float('High level', digits=(16, 3),
        states={'required': Bool(Eval('high_level_value'))},
        depends=['high_level_value'])
    low_level_value = fields.Float('Low level value', digits=(16, 3))
    middle_level_value = fields.Float('Middle level value', digits=(16, 3))
    high_level_value = fields.Float('High level value', digits=(16, 3))
    factor = fields.Float('Factor', digits=(16, 3))
    low_level_coefficient_variation = fields.Float(
        'Low level coefficient of variation', digits=(16, 3))
    middle_level_coefficient_variation = fields.Float(
        'Middle level coefficient of variation', digits=(16, 3))
    high_level_coefficient_variation = fields.Float(
        'High level coefficient of variation', digits=(16, 3))


class ControlTendency(ModelSQL, ModelView):
    'Control Chart Tendency'
    __name__ = 'lims.control.tendency'

    product_type = fields.Many2One('lims.product.type', 'Product type',
        required=True, states={
            'readonly': Bool(Eval('context', {}).get('readonly', False))})
    matrix = fields.Many2One('lims.matrix', 'Matrix', required=True,
        states={'readonly': Bool(Eval('context', {}).get('readonly', False))})
    fraction_type = fields.Many2One('lims.fraction.type', 'Fraction type',
        required=True, states={
            'readonly': Bool(Eval('context', {}).get('readonly', False))})
    analysis = fields.Many2One('lims.analysis', 'Analysis', required=True,
        states={'readonly': Bool(Eval('context', {}).get('readonly', False))})
    concentration_level = fields.Many2One('lims.concentration.level',
        'Concentration level', states={
            'readonly': Bool(Eval('context', {}).get('readonly', False))})
    mean = fields.Float('Mean', required=True,
        states={'readonly': Bool(Eval('context', {}).get('readonly', False))},
        digits=(16, Eval('digits', 2)), depends=['digits'])
    deviation = fields.Float('Standard Deviation', required=True,
        digits=(16, Eval('digits', 2)), depends=['digits'])
    one_sd = fields.Function(fields.Float('1 SD', digits=(16,
        Eval('digits', 2)), depends=['deviation', 'digits']), 'get_one_sd')
    two_sd = fields.Function(fields.Float('2 SD', digits=(16,
        Eval('digits', 2)), depends=['deviation', 'digits']), 'get_two_sd')
    three_sd = fields.Function(fields.Float('3 SD', digits=(16,
        Eval('digits', 2)), depends=['deviation', 'digits']), 'get_three_sd')
    cv = fields.Function(fields.Float('CV (%)', digits=(16, Eval('digits', 2)),
        depends=['deviation', 'mean', 'digits']), 'get_cv')
    min_cv = fields.Float('Minimum CV (%)', digits=(16, Eval('digits', 2)),
        depends=['digits'])
    max_cv = fields.Float('Maximum CV (%)', digits=(16, Eval('digits', 2)),
        depends=['digits'])
    min_cv_corr_fact = fields.Float('Correction factor for Minimum CV',
        digits=(16, Eval('digits', 2)), depends=['digits'])
    max_cv_corr_fact = fields.Float('Correction factor for Maximum CV',
        digits=(16, Eval('digits', 2)), depends=['digits'])
    one_sd_adj = fields.Function(fields.Float('1 SD Adjusted',
        digits=(16, Eval('digits', 2)), depends=['cv', 'one_sd', 'min_cv',
        'max_cv', 'min_cv_corr_fact', 'max_cv_corr_fact', 'digits']),
        'get_one_sd_adj')
    two_sd_adj = fields.Function(fields.Float('2 SD Adjusted',
        digits=(16, Eval('digits', 2)), depends=['cv', 'two_sd', 'min_cv',
        'max_cv', 'min_cv_corr_fact', 'max_cv_corr_fact', 'digits']),
        'get_two_sd_adj')
    three_sd_adj = fields.Function(fields.Float('3 SD Adjusted',
        digits=(16, Eval('digits', 2)), depends=['cv', 'three_sd', 'min_cv',
        'max_cv', 'min_cv_corr_fact', 'max_cv_corr_fact', 'digits']),
        'get_three_sd_adj')
    ucl = fields.Function(fields.Float('UCL', digits=(16, Eval('digits', 2)),
        depends=['mean', 'three_sd_adj', 'digits']), 'get_ucl')
    uwl = fields.Function(fields.Float('UWL', digits=(16, Eval('digits', 2)),
        depends=['mean', 'two_sd_adj', 'digits']), 'get_uwl')
    upl = fields.Function(fields.Float('UPL', digits=(16, Eval('digits', 2)),
        depends=['mean', 'one_sd_adj', 'digits']), 'get_upl')
    lcl = fields.Function(fields.Float('LCL', digits=(16, Eval('digits', 2)),
        depends=['mean', 'three_sd_adj', 'digits']), 'get_lcl')
    lwl = fields.Function(fields.Float('LWL', digits=(16, Eval('digits', 2)),
        depends=['mean', 'two_sd_adj', 'digits']), 'get_lwl')
    lpl = fields.Function(fields.Float('LPL', digits=(16, Eval('digits', 2)),
        depends=['mean', 'one_sd_adj', 'digits']), 'get_lpl')
    cl = fields.Function(fields.Float('CL', digits=(16, Eval('digits', 2)),
        depends=['mean', 'digits']), 'get_cl')
    details = fields.One2Many('lims.control.tendency.detail', 'tendency',
        'Details', readonly=True)
    rule_1_count = fields.Integer('Rule 1', readonly=True)
    rule_2_count = fields.Integer('Rule 2', readonly=True)
    rule_3_count = fields.Integer('Rule 3', readonly=True)
    rule_4_count = fields.Integer('Rule 4', readonly=True)
    digits = fields.Integer('Digits')

    @classmethod
    def __setup__(cls):
        super(ControlTendency, cls).__setup__()
        cls._order.insert(0, ('rule_4_count', 'DESC'))
        cls._order.insert(1, ('rule_3_count', 'DESC'))
        cls._order.insert(2, ('rule_2_count', 'DESC'))
        cls._order.insert(3, ('rule_1_count', 'DESC'))
        cls._order.insert(4, ('product_type', 'ASC'))
        cls._order.insert(5, ('matrix', 'ASC'))
        cls._order.insert(6, ('analysis', 'ASC'))
        cls._order.insert(7, ('concentration_level', 'ASC'))

    @staticmethod
    def default_rule_1_count():
        return 0

    @staticmethod
    def default_rule_2_count():
        return 0

    @staticmethod
    def default_rule_3_count():
        return 0

    @staticmethod
    def default_rule_4_count():
        return 0

    @staticmethod
    def default_digits():
        return 2

    @staticmethod
    def default_min_cv():
        return 1

    @staticmethod
    def default_max_cv():
        return 1

    @staticmethod
    def default_min_cv_corr_fact():
        return 1

    @staticmethod
    def default_max_cv_corr_fact():
        return 1

    def get_one_sd(self, name=None):
        return round(self.deviation, self.digits)

    def get_two_sd(self, name=None):
        return round(self.deviation * 2, self.digits)

    def get_three_sd(self, name=None):
        return round(self.deviation * 3, self.digits)

    def get_cv(self, name=None):
        if self.mean:
            return round((self.deviation / self.mean) * 100, self.digits)

    def get_one_sd_adj(self, name=None):
        if self.cv < self.min_cv:
            return round(self.one_sd, self.digits)
        elif self.cv < self.max_cv:
            if self.min_cv_corr_fact:
                return round(self.one_sd / self.min_cv_corr_fact, self.digits)
        else:
            if self.max_cv_corr_fact:
                return round(self.one_sd / self.max_cv_corr_fact, self.digits)

    def get_two_sd_adj(self, name=None):
        if self.cv < self.min_cv:
            return round(self.two_sd, self.digits)
        elif self.cv < self.max_cv:
            if self.min_cv_corr_fact:
                return round(self.two_sd / self.min_cv_corr_fact, self.digits)
        else:
            if self.max_cv_corr_fact:
                return round(self.two_sd / self.max_cv_corr_fact, self.digits)

    def get_three_sd_adj(self, name=None):
        if self.cv < self.min_cv:
            return round(self.three_sd, self.digits)
        elif self.cv < self.max_cv:
            if self.min_cv_corr_fact:
                return round(self.three_sd / self.min_cv_corr_fact,
                    self.digits)
        else:
            if self.max_cv_corr_fact:
                return round(self.three_sd / self.max_cv_corr_fact,
                    self.digits)

    def get_ucl(self, name=None):
        return round(self.mean + self.three_sd_adj, self.digits)

    def get_uwl(self, name=None):
        return round(self.mean + self.two_sd_adj, self.digits)

    def get_upl(self, name=None):
        return round(self.mean + self.one_sd_adj, self.digits)

    def get_lcl(self, name=None):
        return round(self.mean - self.three_sd_adj, self.digits)

    def get_lwl(self, name=None):
        return round(self.mean - self.two_sd_adj, self.digits)

    def get_lpl(self, name=None):
        return round(self.mean - self.one_sd_adj, self.digits)

    def get_cl(self, name=None):
        return round(self.mean, self.digits)


class ControlTendencyDetail(ModelSQL, ModelView):
    'Control Chart Tendency Detail'
    __name__ = 'lims.control.tendency.detail'

    tendency = fields.Many2One('lims.control.tendency', 'Tendency',
        ondelete='CASCADE', select=True, required=True)
    notebook_line = fields.Many2One('lims.notebook.line', 'Notebook Line')
    date = fields.Date('Date')
    fraction = fields.Many2One('lims.fraction', 'Fraction')
    device = fields.Many2One('lims.lab.device', 'Device')
    result = fields.Float('Result')
    rule = fields.Char('Rule')
    rules = fields.One2Many('lims.control.tendency.detail.rule',
        'detail', 'Rules')
    rules2 = fields.Function(fields.Char('Rules', depends=['rules']),
        'get_rules2')
    icon = fields.Function(fields.Char("Icon"), 'get_icon')

    @classmethod
    def __setup__(cls):
        super(ControlTendencyDetail, cls).__setup__()
        cls._order.insert(0, ('date', 'ASC'))
        cls._order.insert(1, ('fraction', 'ASC'))
        cls._order.insert(2, ('device', 'ASC'))

    def get_rules2(self, name=None):
        rules = ''
        if self.rules:
            rules = ', '.join(str(r.rule) for r in self.rules)
        return rules

    def get_icon(self, name):
        if self.rule in ['1', '2', '3', '4']:
            return \
                {
                    '1': 'lims-green',
                    '2': 'lims-blue',
                    '3': 'lims-yellow',
                    '4': 'lims-red',
                }[self.rule]


class ControlTendencyDetailRule(ModelSQL):
    'Control Chart Tendency Detail Rule'
    __name__ = 'lims.control.tendency.detail.rule'

    detail = fields.Many2One('lims.control.tendency.detail', 'Detail',
        ondelete='CASCADE', select=True, required=True)
    rule = fields.Char('Rule')


class MeansDeviationsCalcStart(ModelView):
    'Calculation of Means and Deviations'
    __name__ = 'lims.control.means_deviations_calc.start'

    date_from = fields.Date('Date from', required=True)
    date_to = fields.Date('Date to', required=True)
    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        required=True)
    family = fields.Many2One('lims.analysis.family', 'Family')
    product_type = fields.Many2One('lims.product.type', 'Product type',
        domain=[('id', 'in', Eval('product_type_domain'))],
        depends=['product_type_domain'])
    product_type_domain = fields.Function(fields.Many2Many(
        'lims.product.type', None, None, 'Product type domain'),
        'on_change_with_product_type_domain')
    matrix = fields.Many2One('lims.matrix', 'Matrix',
        domain=[('id', 'in', Eval('matrix_domain'))],
        depends=['matrix_domain'])
    matrix_domain = fields.Function(fields.Many2Many('lims.matrix',
        None, None, 'Matrix domain'), 'on_change_with_matrix_domain')
    fraction_type = fields.Many2One('lims.fraction.type', 'Fraction type',
        domain=[('control_charts', '=', True)], required=True)

    @staticmethod
    def default_product_type_domain():
        cursor = Transaction().connection.cursor()
        Typification = Pool().get('lims.typification')

        cursor.execute('SELECT DISTINCT(product_type) '
            'FROM "' + Typification._table + '" '
            'WHERE valid')
        return [x[0] for x in cursor.fetchall()]

    @fields.depends('family')
    def on_change_with_product_type_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        AnalysisFamilyCertificant = Pool().get(
            'lims.analysis.family.certificant')

        if not self.family:
            return self.default_product_type_domain()

        cursor.execute('SELECT DISTINCT(product_type) '
            'FROM "' + AnalysisFamilyCertificant._table + '" '
            'WHERE family = %s',
            (self.family.id,))
        return [x[0] for x in cursor.fetchall()]

    @fields.depends('product_type', 'family')
    def on_change_with_matrix_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        AnalysisFamilyCertificant = pool.get(
            'lims.analysis.family.certificant')
        Typification = pool.get('lims.typification')

        if not self.product_type:
            return []

        if not self.family:
            cursor.execute('SELECT DISTINCT(matrix) '
                'FROM "' + Typification._table + '" '
                'WHERE product_type = %s '
                'AND valid',
                (self.product_type.id,))
            return [x[0] for x in cursor.fetchall()]
        else:
            cursor.execute('SELECT DISTINCT(matrix) '
                'FROM "' + AnalysisFamilyCertificant._table + '" '
                'WHERE product_type = %s '
                'AND family = %s',
                (self.product_type.id, self.family.id))
            return [x[0] for x in cursor.fetchall()]


class MeansDeviationsCalcEmpty(ModelView):
    'Calculation of Means and Deviations'
    __name__ = 'lims.control.means_deviations_calc.empty'


class MeansDeviationsCalcResult(ModelView):
    'Calculation of Means and Deviations'
    __name__ = 'lims.control.means_deviations_calc.result'

    lines = fields.One2Many('lims.control.result_line', None, 'Results')


class ControlResultLine(ModelSQL, ModelView):
    'Control Chart Result Line'
    __name__ = 'lims.control.result_line'

    product_type = fields.Many2One('lims.product.type', 'Product type',
        readonly=True)
    matrix = fields.Many2One('lims.matrix', 'Matrix', readonly=True)
    fraction_type = fields.Many2One('lims.fraction.type', 'Fraction type',
        readonly=True)
    analysis = fields.Many2One('lims.analysis', 'Analysis', readonly=True)
    concentration_level = fields.Many2One('lims.concentration.level',
        'Concentration level', readonly=True)
    mean = fields.Float('Mean', readonly=True)
    deviation = fields.Float('Standard Deviation', readonly=True)
    one_sd = fields.Function(fields.Float('1 SD', depends=['deviation']),
        'get_one_sd')
    two_sd = fields.Function(fields.Float('2 SD', depends=['deviation']),
        'get_two_sd')
    three_sd = fields.Function(fields.Float('3 SD', depends=['deviation']),
        'get_three_sd')
    cv = fields.Function(fields.Float('CV (%)', depends=['deviation',
        'mean']), 'get_cv')
    prev_mean = fields.Function(fields.Float('Previous Mean', depends=[
        'product_type', 'matrix', 'fraction_type', 'analysis',
        'concentration_level', ]), 'get_prev_mean')
    prev_one_sd = fields.Function(fields.Float('Previous 1 SD', depends=[
        'product_type', 'matrix', 'fraction_type', 'analysis',
        'concentration_level', ]), 'get_prev_one_sd')
    prev_two_sd = fields.Function(fields.Float('Previous 2 SD', depends=[
        'product_type', 'matrix', 'fraction_type', 'analysis',
        'concentration_level', ]), 'get_prev_two_sd')
    prev_three_sd = fields.Function(fields.Float('Previous 3 SD', depends=[
        'product_type', 'matrix', 'fraction_type', 'analysis',
        'concentration_level', ]), 'get_prev_three_sd')
    prev_cv = fields.Function(fields.Float('Previous CV (%)', depends=[
        'product_type', 'matrix', 'fraction_type', 'analysis',
        'concentration_level', ]), 'get_prev_cv')
    details = fields.One2Many('lims.control.result_line.detail', 'line',
        'Details', readonly=True)
    update = fields.Boolean('Update')
    session_id = fields.Integer('Session ID')

    @classmethod
    def __register__(cls, module_name):
        super(ControlResultLine,
            cls).__register__(module_name)
        cursor = Transaction().connection.cursor()
        cursor.execute('DELETE FROM "' + cls._table + '"')

    @classmethod
    def __setup__(cls):
        super(ControlResultLine, cls).__setup__()
        cls._order.insert(0, ('product_type', 'ASC'))
        cls._order.insert(1, ('matrix', 'ASC'))
        cls._order.insert(2, ('analysis', 'ASC'))
        cls._order.insert(3, ('concentration_level', 'ASC'))

    @staticmethod
    def default_update():
        return False

    def get_one_sd(self, name=None):
        return self.deviation

    def get_two_sd(self, name=None):
        return self.deviation * 2

    def get_three_sd(self, name=None):
        return self.deviation * 3

    def get_cv(self, name=None):
        if self.mean:
            return (self.deviation / self.mean) * 100

    def get_prev_mean(self, name=None):
        ControlTendency = Pool().get('lims.control.tendency')
        tendency = ControlTendency.search([
            ('product_type', '=', self.product_type.id),
            ('matrix', '=', self.matrix.id),
            ('fraction_type', '=', self.fraction_type.id),
            ('analysis', '=', self.analysis.id),
            ('concentration_level', '=', self.concentration_level),
            ])
        if tendency:
            return tendency[0].mean
        return 0.00

    def get_prev_one_sd(self, name=None):
        ControlTendency = Pool().get('lims.control.tendency')
        tendency = ControlTendency.search([
            ('product_type', '=', self.product_type.id),
            ('matrix', '=', self.matrix.id),
            ('fraction_type', '=', self.fraction_type.id),
            ('analysis', '=', self.analysis.id),
            ('concentration_level', '=', self.concentration_level),
            ])
        if tendency:
            return tendency[0].one_sd
        return 0.00

    def get_prev_two_sd(self, name=None):
        ControlTendency = Pool().get('lims.control.tendency')
        tendency = ControlTendency.search([
            ('product_type', '=', self.product_type.id),
            ('matrix', '=', self.matrix.id),
            ('fraction_type', '=', self.fraction_type.id),
            ('analysis', '=', self.analysis.id),
            ('concentration_level', '=', self.concentration_level),
            ])
        if tendency:
            return tendency[0].two_sd
        return 0.00

    def get_prev_three_sd(self, name=None):
        ControlTendency = Pool().get('lims.control.tendency')
        tendency = ControlTendency.search([
            ('product_type', '=', self.product_type.id),
            ('matrix', '=', self.matrix.id),
            ('fraction_type', '=', self.fraction_type.id),
            ('analysis', '=', self.analysis.id),
            ('concentration_level', '=', self.concentration_level),
            ])
        if tendency:
            return tendency[0].three_sd
        return 0.00

    def get_prev_cv(self, name=None):
        ControlTendency = Pool().get('lims.control.tendency')
        tendency = ControlTendency.search([
            ('product_type', '=', self.product_type.id),
            ('matrix', '=', self.matrix.id),
            ('fraction_type', '=', self.fraction_type.id),
            ('analysis', '=', self.analysis.id),
            ('concentration_level', '=', self.concentration_level),
            ])
        if tendency:
            return tendency[0].cv
        return 0.00


class ControlResultLineDetail(ModelSQL, ModelView):
    'Control Chart Result Line Detail'
    __name__ = 'lims.control.result_line.detail'

    line = fields.Many2One('lims.control.result_line', 'Line',
        ondelete='CASCADE', select=True, required=True)
    date = fields.Date('Date')
    fraction = fields.Many2One('lims.fraction', 'Fraction')
    device = fields.Many2One('lims.lab.device', 'Device')
    result = fields.Float('Result')

    @classmethod
    def __setup__(cls):
        super(ControlResultLineDetail, cls).__setup__()
        cls._order.insert(0, ('date', 'ASC'))
        cls._order.insert(1, ('fraction', 'ASC'))
        cls._order.insert(2, ('device', 'ASC'))


class MeansDeviationsCalcResult2(ModelView):
    'Calculation of Means and Deviations'
    __name__ = 'lims.control.means_deviations_calc.result2'

    tendencies = fields.One2Many('lims.control.tendency', None, 'Tendencies',
        readonly=True)


class MeansDeviationsCalc(Wizard):
    'Calculation of Means and Deviations'
    __name__ = 'lims.control.means_deviations_calc'

    start = StateView('lims.control.means_deviations_calc.start',
        'lims.lims_control_means_deviations_calc_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search', 'search', 'tryton-forward', default=True),
            ])
    search = StateTransition()
    empty = StateView('lims.control.means_deviations_calc.empty',
        'lims.lims_control_means_deviations_calc_empty_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Search again', 'start', 'tryton-forward', default=True),
            ])
    result = StateView('lims.control.means_deviations_calc.result',
        'lims.lims_control_means_deviations_calc_result_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Update', 'update', 'tryton-forward', default=True),
            ])
    update = StateTransition()
    result2 = StateView('lims.control.means_deviations_calc.result2',
        'lims.lims_control_means_deviations_calc_result2_view_form', [])
    open = StateAction('lims.act_lims_control_tendency2')

    def default_start(self, fields):
        res = {}
        for field in ('date_from', 'date_to'):
            if (hasattr(self.start, field) and getattr(self.start, field)):
                res[field] = getattr(self.start, field)
        for field in ('family', 'laboratory', 'product_type', 'matrix',
                'fraction_type'):
            if (hasattr(self.start, field) and getattr(self.start, field)):
                res[field] = getattr(self.start, field).id
        for field in ('product_type_domain', 'matrix_domain'):
            if (hasattr(self.start, field) and getattr(self.start, field)):
                res[field] = [f.id for f in getattr(self.start, field)]

        return res

    def transition_search(self):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        ControlResultLine = pool.get('lims.control.result_line')
        AnalysisFamilyCertificant = pool.get(
            'lims.analysis.family.certificant')
        NotebookLine = pool.get('lims.notebook.line')

        clause = [
            ('laboratory', '=', self.start.laboratory.id),
            ('end_date', '>=', self.start.date_from),
            ('end_date', '<=', self.start.date_to),
            ('notebook.fraction.type', '=', self.start.fraction_type.id),
            ('analysis.behavior', '=', 'normal'),
            ('result', 'not in', [None, '']),
            ('annulled', '=', False),
            ]
        if self.start.product_type:
            clause.append(('notebook.product_type', '=',
                self.start.product_type.id))
        if self.start.matrix:
            clause.append(('notebook.matrix', '=', self.start.matrix.id))
        check_family = False
        if self.start.family:
            check_family = True
            families = []
            cursor.execute('SELECT product_type, matrix '
                'FROM "' + AnalysisFamilyCertificant._table + '" '
                'WHERE family = %s',
                (self.start.family.id,))
            res = cursor.fetchall()
            if res:
                families = [(x[0], x[1]) for x in res]

        lines = NotebookLine.search(clause)
        if lines:
            records = {}
            for line in lines:
                try:
                    result = float(line.result or None)
                except (TypeError, ValueError):
                    continue

                if check_family:
                    family_key = (line.notebook.product_type.id,
                        line.notebook.matrix.id)
                    if family_key not in families:
                        continue

                product_type_id = line.notebook.product_type.id
                matrix_id = line.notebook.matrix.id
                fraction_type_id = line.notebook.fraction_type.id
                analysis_id = line.analysis.id
                concentration_level_id = (line.concentration_level.id if
                    line.concentration_level else None)

                key = (product_type_id, matrix_id, analysis_id,
                    concentration_level_id)
                if key not in records:
                    records[key] = {
                        'product_type': product_type_id,
                        'matrix': matrix_id,
                        'fraction_type': fraction_type_id,
                        'analysis': analysis_id,
                        'concentration_level': concentration_level_id,
                        'details': {},
                        }
                records[key]['details'][line.id] = {
                    'date': line.end_date,
                    'fraction': line.notebook.fraction.id,
                    'device': line.device.id if line.device else None,
                    'result': result,
                    }
            if records:
                to_create = []
                for record in records.values():
                    details = [d for d in record['details'].values()]
                    to_create.append({
                        'session_id': self._session_id,
                        'product_type': record['product_type'],
                        'matrix': record['matrix'],
                        'fraction_type': record['fraction_type'],
                        'analysis': record['analysis'],
                        'concentration_level': record['concentration_level'],
                        'details': [('create', details)],
                        })
                if to_create:
                    res_lines = ControlResultLine.create(to_create)

                    to_save = []
                    for line in res_lines:
                        count = 0.00
                        total = 0.00
                        for detail in line.details:
                            count += 1
                            total += detail.result
                        mean = round(total / count, 2)
                        total = 0.00
                        for detail in line.details:
                            total += (detail.result - mean) ** 2
                        # Se toma correcion poblacional Bessel n-1
                        if count > 1:
                            deviation = round(sqrt(total / (count - 1)), 2)
                        else:
                            deviation = 0.00
                        line.mean = mean
                        line.deviation = deviation
                        to_save.append(line)
                    ControlResultLine.save(to_save)

                    self.result.lines = res_lines
                    return 'result'
        return 'empty'

    def default_result(self, fields):
        lines = [l.id for l in self.result.lines]
        self.result.lines = None
        return {
            'lines': lines,
            }

    def transition_update(self):
        pool = Pool()
        ControlResultLine = pool.get('lims.control.result_line')
        ControlTendency = pool.get('lims.control.tendency')
        LaboratoryCVCorrection = pool.get('lims.laboratory.cv_correction')

        res_lines_ids = [rl.id for rl in self.result.lines if rl.update]
        self.result.lines = None
        res_lines = ControlResultLine.search([
            ('session_id', '=', self._session_id),
            ('id', 'in', res_lines_ids),
            ])
        if not res_lines:
            return 'empty'

        cv_correction = LaboratoryCVCorrection.search([
            ('laboratory', '=', self.start.laboratory.id),
            ('fraction_type', '=', self.start.fraction_type.id),
            ])
        if cv_correction:
            min_cv = cv_correction[0].min_cv or 1
            max_cv = cv_correction[0].max_cv or 1
            min_cv_corr_fact = cv_correction[0].min_cv_corr_fact or 1
            max_cv_corr_fact = cv_correction[0].max_cv_corr_fact or 1
        else:
            min_cv = 1
            max_cv = 1
            min_cv_corr_fact = 1
            max_cv_corr_fact = 1

        tendencies = []
        for line in res_lines:
            concentration_level_id = (line.concentration_level.id if
                line.concentration_level else None)
            tendency = ControlTendency.search([
                ('product_type', '=', line.product_type.id),
                ('matrix', '=', line.matrix.id),
                ('fraction_type', '=', line.fraction_type.id),
                ('analysis', '=', line.analysis.id),
                ('concentration_level', '=', concentration_level_id),
                ])
            if tendency:
                ControlTendency.write(tendency, {
                    'mean': line.mean,
                    'deviation': line.deviation,
                    'min_cv': min_cv,
                    'max_cv': max_cv,
                    'min_cv_corr_fact': min_cv_corr_fact,
                    'max_cv_corr_fact': max_cv_corr_fact,
                    'rule_1_count': 0,
                    'rule_2_count': 0,
                    'rule_3_count': 0,
                    'rule_4_count': 0,
                    })
                tendencies.extend(tendency)
            else:
                tendency, = ControlTendency.create([{
                    'product_type': line.product_type.id,
                    'matrix': line.matrix.id,
                    'fraction_type': line.fraction_type.id,
                    'analysis': line.analysis.id,
                    'concentration_level': concentration_level_id,
                    'mean': line.mean,
                    'deviation': line.deviation,
                    'min_cv': min_cv,
                    'max_cv': max_cv,
                    'min_cv_corr_fact': min_cv_corr_fact,
                    'max_cv_corr_fact': max_cv_corr_fact,
                    }])
                tendencies.append(tendency)
        self.result2.tendencies = tendencies
        return 'open'

    def do_open(self, action):
        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', 'in', [t.id for t in self.result2.tendencies]),
            ])
        action['pyson_context'] = PYSONEncoder().encode({
            'readonly': True,
            })
        self.result2.tendencies = None
        return action, {}


class TendenciesAnalysisStart(ModelView):
    'Tendencies Analysis'
    __name__ = 'lims.control.tendencies_analysis.start'

    date_from = fields.Date('Date from', required=True)
    date_to = fields.Date('Date to', required=True)
    family = fields.Many2One('lims.analysis.family', 'Family')
    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        required=True)
    product_type = fields.Many2One('lims.product.type', 'Product type',
        domain=[('id', 'in', Eval('product_type_domain'))],
        depends=['product_type_domain'])
    product_type_domain = fields.Function(fields.Many2Many(
        'lims.product.type', None, None, 'Product type domain'),
        'on_change_with_product_type_domain')
    matrix = fields.Many2One('lims.matrix', 'Matrix',
        domain=[('id', 'in', Eval('matrix_domain'))],
        depends=['matrix_domain'])
    matrix_domain = fields.Function(fields.Many2Many('lims.matrix',
        None, None, 'Matrix domain'), 'on_change_with_matrix_domain')
    fraction_type = fields.Many2One('lims.fraction.type', 'Fraction type',
        domain=[('control_charts', '=', True)], required=True)

    @staticmethod
    def default_product_type_domain():
        cursor = Transaction().connection.cursor()
        Typification = Pool().get('lims.typification')

        cursor.execute('SELECT DISTINCT(product_type) '
            'FROM "' + Typification._table + '" '
            'WHERE valid')
        return [x[0] for x in cursor.fetchall()]

    @fields.depends('family')
    def on_change_with_product_type_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        AnalysisFamilyCertificant = Pool().get(
            'lims.analysis.family.certificant')

        if not self.family:
            return self.default_product_type_domain()

        cursor.execute('SELECT DISTINCT(product_type) '
            'FROM "' + AnalysisFamilyCertificant._table + '" '
            'WHERE family = %s',
            (self.family.id,))
        return [x[0] for x in cursor.fetchall()]

    @fields.depends('product_type', 'family')
    def on_change_with_matrix_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        AnalysisFamilyCertificant = pool.get(
            'lims.analysis.family.certificant')
        Typification = pool.get('lims.typification')

        if not self.product_type:
            return []

        if not self.family:
            cursor.execute('SELECT DISTINCT(matrix) '
                'FROM "' + Typification._table + '" '
                'WHERE product_type = %s '
                'AND valid',
                (self.product_type.id,))
            return [x[0] for x in cursor.fetchall()]
        else:
            cursor.execute('SELECT DISTINCT(matrix) '
                'FROM "' + AnalysisFamilyCertificant._table + '" '
                'WHERE product_type = %s '
                'AND family = %s',
                (self.product_type.id, self.family.id))
            return [x[0] for x in cursor.fetchall()]


class TendenciesAnalysisResult(ModelView):
    'Tendencies Analysis'
    __name__ = 'lims.control.tendencies_analysis.result'

    tendencies = fields.One2Many('lims.control.tendency', None, 'Tendencies',
        readonly=True)


class TendenciesAnalysis(Wizard):
    'Tendencies Analysis'
    __name__ = 'lims.control.tendencies_analysis'

    start = StateView('lims.control.tendencies_analysis.start',
        'lims.lims_control_tendencies_analysis_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Open', 'search', 'tryton-ok', True),
            ])
    search = StateTransition()
    result = StateView('lims.control.tendencies_analysis.result',
        'lims.lims_control_tendencies_analysis_result_view_form', [])
    open = StateAction('lims.act_lims_control_tendency3')

    def transition_search(self):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        ControlTendency = pool.get('lims.control.tendency')
        ControlTendencyDetail = pool.get('lims.control.tendency.detail')
        AnalysisFamilyCertificant = pool.get(
            'lims.analysis.family.certificant')
        NotebookLine = pool.get('lims.notebook.line')

        tendency_result = []

        clause = [
            ('fraction_type', '=', self.start.fraction_type.id),
            ]
        if self.start.product_type:
            clause.append(('product_type', '=', self.start.product_type.id))
        if self.start.matrix:
            clause.append(('matrix', '=', self.start.matrix.id))

        tendencies = ControlTendency.search(clause)
        if tendencies:
            check_family = False
            if self.start.family:
                check_family = True
                families = []
                cursor.execute('SELECT product_type, matrix '
                    'FROM "' + AnalysisFamilyCertificant._table + '" '
                    'WHERE family = %s',
                    (self.start.family.id,))
                res = cursor.fetchall()
                if res:
                    families = [(x[0], x[1]) for x in res]

            for tendency in tendencies:
                if check_family:
                    family_key = (tendency.product_type.id, tendency.matrix.id)
                    if family_key not in families:
                        continue

                old_details = ControlTendencyDetail.search([
                    ('tendency', '=', tendency.id),
                    ])
                if old_details:
                    ControlTendencyDetail.delete(old_details)

                concentration_level_id = (tendency.concentration_level.id if
                    tendency.concentration_level else None)
                clause = [
                    ('laboratory', '=', self.start.laboratory.id),
                    ('notebook.fraction.type', '=', tendency.fraction_type.id),
                    ('notebook.product_type', '=', tendency.product_type.id),
                    ('notebook.matrix', '=', tendency.matrix.id),
                    ('analysis', '=', tendency.analysis.id),
                    ('concentration_level', '=', concentration_level_id),
                    ('result', 'not in', [None, '']),
                    ('annulled', '=', False),
                    ]

                rule_1_count = 0
                rule_2_count = 0
                rule_3_count = 0
                rule_4_count = 0
                lines = \
                    NotebookLine.search(clause + [
                        ('end_date', '>=', self.start.date_from),
                        ('end_date', '<=', self.start.date_to),
                    ], order=[('end_date', 'ASC'), ('id', 'ASC')])
                if lines:
                    results = []
                    prevs = 8 - len(lines)  # Qty of previous results required
                    if prevs > 0:
                        prev_lines = \
                            NotebookLine.search(clause + [
                                ('end_date', '<', self.start.date_from),
                                ], order=[('end_date', 'ASC'), ('id', 'ASC')],
                                limit=prevs)
                        if prev_lines:
                            for line in prev_lines:
                                result = float(line.result if
                                    line.result else None)
                                results.append(result)

                    to_create = []
                    for line in lines:
                        try:
                            result = float(line.result if
                                line.result else None)
                            results.append(result)
                        except(TypeError, ValueError):
                            continue
                        rules = self.get_rules(results, tendency)
                        rules_to_create = []
                        for r in rules:
                            if r == '':
                                continue
                            rules_to_create.append({'rule': r})
                            if r == '1':
                                rule_1_count += 1
                            elif r == '2':
                                rule_2_count += 1
                            elif r == '3':
                                rule_3_count += 1
                            elif r == '4':
                                rule_4_count += 1

                        record = {
                            'notebook_line': line.id,
                            'tendency': tendency.id,
                            'date': line.end_date,
                            'fraction': line.notebook.fraction.id,
                            'device': line.device.id if line.device else None,
                            'result': result,
                            'rule': rules[0],
                            }
                        if rules_to_create:
                            record['rules'] = [('create', rules_to_create)]
                        to_create.append(record)

                    ControlTendencyDetail.create(to_create)
                    tendency_result.append(tendency)

                ControlTendency.write([tendency], {
                    'rule_1_count': rule_1_count,
                    'rule_2_count': rule_2_count,
                    'rule_3_count': rule_3_count,
                    'rule_4_count': rule_4_count,
                    })

            if tendency_result:
                self.result.tendencies = tendency_result
                return 'open'
        return 'end'

    def get_rules(self, results, tendency):

        rules = []

        # Check rule 4
        # 1 value above or below the mean +/- 3 SD
        upper_parameter = tendency.mean + tendency.three_sd_adj
        lower_parameter = tendency.mean - tendency.three_sd_adj
        occurrences = 1
        total = 1
        if self._check_rule(results, upper_parameter, lower_parameter,
                occurrences, total):
            rules.append('4')

        # Check rule 3
        # 2 of 3 consecutive values above or below the mean +/- 2 SD
        upper_parameter = tendency.mean + tendency.two_sd_adj
        lower_parameter = tendency.mean - tendency.two_sd_adj
        occurrences = 2
        total = 3
        if self._check_rule(results, upper_parameter, lower_parameter,
                occurrences, total):
            rules.append('3')

        # Check rule 2
        # 4 of 5 consecutive values above or below the mean +/- 1 SD
        upper_parameter = tendency.mean + tendency.one_sd_adj
        lower_parameter = tendency.mean - tendency.one_sd_adj
        occurrences = 4
        total = 5
        if self._check_rule(results, upper_parameter, lower_parameter,
                occurrences, total):
            rules.append('2')

        # Check rule 1
        # 8 consecutive values above or below the mean
        upper_parameter = tendency.mean
        lower_parameter = tendency.mean
        occurrences = 8
        total = 8
        if self._check_rule(results, upper_parameter, lower_parameter,
                occurrences, total):
            rules.append('1')

        if not rules:
            rules.append('')

        return rules

    def _check_rule(self, results, upper_parameter, lower_parameter,
            occurrences, total):

        if len(results) < total:
            return False

        total_counter = 0
        upper_counter = 0
        lower_counter = 0
        for result in reversed(results):

            total_counter += 1
            if result > upper_parameter:
                upper_counter += 1
                if total_counter == total:
                    if (upper_counter >= occurrences or
                            lower_counter >= occurrences):
                        return True
                    return False
                lower_counter = 0
            elif result < lower_parameter:
                lower_counter += 1
                if total_counter == total:
                    if (lower_counter >= occurrences or
                            upper_counter >= occurrences):
                        return True
                    return False
                upper_counter = 0
            else:
                if total_counter == total:
                    if (upper_counter >= occurrences or
                            lower_counter >= occurrences):
                        return True
                    return False
                upper_counter = 0
                lower_counter = 0
        return False

    def do_open(self, action):
        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', 'in', [t.id for t in self.result.tendencies]),
            ])
        action['pyson_context'] = PYSONEncoder().encode({
            'readonly': True,
            'print_available': True,
            })
        self.result.tendencies = None
        return action, {}


class PrintControlChart(Wizard):
    'Control Chart'
    __name__ = 'lims.control_chart.print'

    start = StateTransition()
    print_ = StateAction('lims.report_control_chart')

    def transition_start(self):
        if Transaction().context.get('print_available'):
            return 'print_'
        return 'end'

    def do_print_(self, action):
        data = {}
        data['id'] = Transaction().context['active_ids'].pop()
        data['ids'] = [data['id']]
        return action, data

    def transition_print_(self):
        if Transaction().context.get('active_ids'):
            return 'start'
        return 'end'

    @classmethod
    def __setup__(cls):
        super(PrintControlChart, cls).__setup__()
        cls._error_messages.update({
            'number': 'Measurement',
            'result': 'Result',
            'ucl': 'UCL (M+3D)',
            'uwl': 'UWL (M+2D)',
            'upl': 'UPL (M+D)',
            'cl': 'CL (M)',
            'lpl': 'LPL (M-D)',
            'lwl': 'LWL (M-2D)',
            'lcl': 'LCL (M-3D)',
            'cv': 'CV (%)',
            })


class ControlChartReport(Report):
    'Control Chart'
    __name__ = 'lims.control_chart.report'

    @classmethod
    def get_context(cls, reports, data):
        report_context = super(ControlChartReport, cls).get_context(
                reports, data)
        pool = Pool()
        Company = pool.get('company.company')
        ControlTendency = pool.get('lims.control.tendency')

        if 'id' in data:
            tendency = ControlTendency(data['id'])
        else:
            tendency = ControlTendency(reports[0].id)

        company = Company(Transaction().context.get('company'))
        report_context['company'] = company
        report_context['title'] = tendency.analysis.rec_name

        columns = [x for x in range(1, len(tendency.details) + 1)]
        report_context['columns'] = columns

        records = cls._get_objects(tendency)
        report_context['records'] = records

        report_context['plot'] = cls._get_plot(columns, records)
        return report_context

    @classmethod
    def _get_objects(cls, tendency):
        pool = Pool()
        PrintControlChart = pool.get('lims.control_chart.print',
            type='wizard')

        objects = {
            'number': {'name': PrintControlChart.raise_user_error('number',
                raise_exception=False), 'order': 1, 'recs': {}},
            'result': {'name': PrintControlChart.raise_user_error('result',
                raise_exception=False), 'order': 2, 'recs': {}},
            'ucl': {'name': PrintControlChart.raise_user_error('ucl',
                raise_exception=False), 'order': 3, 'recs': {}},
            'uwl': {'name': PrintControlChart.raise_user_error('uwl',
                raise_exception=False), 'order': 4, 'recs': {}},
            'upl': {'name': PrintControlChart.raise_user_error('upl',
                raise_exception=False), 'order': 5, 'recs': {}},
            'cl': {'name': PrintControlChart.raise_user_error('cl',
                raise_exception=False), 'order': 6, 'recs': {}},
            'lpl': {'name': PrintControlChart.raise_user_error('lpl',
                raise_exception=False), 'order': 7, 'recs': {}},
            'lwl': {'name': PrintControlChart.raise_user_error('lwl',
                raise_exception=False), 'order': 8, 'recs': {}},
            'lcl': {'name': PrintControlChart.raise_user_error('lcl',
                raise_exception=False), 'order': 9, 'recs': {}},
            'cv': {'name': PrintControlChart.raise_user_error('cv',
                raise_exception=False), 'order': 10, 'recs': {}},
            }
        count = 1
        for detail in tendency.details:
            objects['number']['recs'][count] = count
            objects['result']['recs'][count] = detail.result
            objects['ucl']['recs'][count] = tendency.ucl
            objects['uwl']['recs'][count] = tendency.uwl
            objects['upl']['recs'][count] = tendency.upl
            objects['cl']['recs'][count] = tendency.cl
            objects['lpl']['recs'][count] = tendency.lpl
            objects['lwl']['recs'][count] = tendency.lwl
            objects['lcl']['recs'][count] = tendency.lcl
            objects['cv']['recs'][count] = tendency.cv
            count += 1
        return objects

    @classmethod
    def _get_plot(cls, columns, records):
        if not CAN_PLOT:
            return None
        pool = Pool()
        PrintControlChart = pool.get('lims.control_chart.print',
            type='wizard')

        index = columns
        cols = []
        ds = {}
        for r in sorted(list(records.values()), key=lambda x: x['order']):
            cols.append(r['name'])
            ds[r['name']] = [r['recs'][col] for col in index]
        df = pd.DataFrame(ds, index=index)
        df = df.reindex_axis(cols, axis=1)

        try:
            ax = df[[
                PrintControlChart.raise_user_error('ucl',
                    raise_exception=False),
                ]].plot(kind='line', color='red', rot=45, fontsize=7,
                    figsize=(10, 7.5), linestyle='-')
            ax = df[[
                PrintControlChart.raise_user_error('uwl',
                    raise_exception=False),
                ]].plot(kind='line', color='orange', rot=45, fontsize=7,
                    figsize=(10, 7.5), linestyle='-', ax=ax)
            ax = df[[
                PrintControlChart.raise_user_error('upl',
                    raise_exception=False),
                ]].plot(kind='line', color='yellow', rot=45, fontsize=7,
                    figsize=(10, 7.5), linestyle='--', ax=ax)
            ax = df[[
                PrintControlChart.raise_user_error('cl',
                    raise_exception=False),
                ]].plot(kind='line', color='green', rot=45, fontsize=7,
                    figsize=(10, 7.5), linestyle='-', ax=ax)
            ax = df[[
                PrintControlChart.raise_user_error('lpl',
                    raise_exception=False),
                ]].plot(kind='line', color='yellow', rot=45, fontsize=7,
                    figsize=(10, 7.5), linestyle='--', ax=ax)
            ax = df[[
                PrintControlChart.raise_user_error('lwl',
                    raise_exception=False),
                ]].plot(kind='line', color='orange', rot=45, fontsize=7,
                    figsize=(10, 7.5), linestyle='-', ax=ax)
            ax = df[[
                PrintControlChart.raise_user_error('lcl',
                    raise_exception=False),
                ]].plot(kind='line', color='red', rot=45, fontsize=7,
                    figsize=(10, 7.5), linestyle='-', ax=ax)
            ax = df[[
                PrintControlChart.raise_user_error('result',
                    raise_exception=False),
                ]].plot(kind='line', color='blue', rot=45, fontsize=7,
                    figsize=(10, 7.5), marker='o', linestyle='-', ax=ax)

            output = BytesIO()
            ax.legend(loc='center left', bbox_to_anchor=(1.0, 0.5))
            ax.get_figure().savefig(output, bbox_inches='tight', dpi=300)
            image = output.getvalue()
            output.close()
            return image
        except TypeError:
            return output.getvalue()
