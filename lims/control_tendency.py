# -*- coding: utf-8 -*-
# This file is part of lims module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import pandas as pd
from io import BytesIO
from math import sqrt
import matplotlib.pyplot as plt

from trytond.model import ModelView, ModelSQL, fields
from trytond.wizard import (Wizard, StateTransition, StateView, StateAction,
    StateReport, Button)
from trytond.pyson import PYSONEncoder, Eval, Bool
from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.report import Report
from trytond.exceptions import UserError
from trytond.i18n import gettext


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

    @staticmethod
    def default_by_default():
        return False

    @classmethod
    def validate(cls, range_types):
        super().validate(range_types)
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
                raise UserError(gettext('lims.msg_default_range_type'))

    @classmethod
    def copy(cls, records, default=None):
        if default is None:
            default = {}
        current_default = default.copy()
        current_default['by_default'] = False
        return super().copy(records, default=current_default)


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


class CopyRangeStart(ModelView):
    'Copy Range'
    __name__ = 'lims.range.copy.start'

    origin_range_type = fields.Many2One('lims.range.type', 'Range type',
        required=True)
    origin_product_type = fields.Many2One('lims.product.type', 'Product type',
        required=True)
    origin_matrix = fields.Many2One('lims.matrix', 'Matrix', required=True)
    destination_type = fields.Many2One('lims.range.type', 'Range type',
        required=True)
    destination_product_type = fields.Many2One('lims.product.type',
        'Product type', required=True)
    destination_matrix = fields.Many2One('lims.matrix', 'Matrix',
        required=True)


class CopyRangeResult(ModelView):
    'Copy Range'
    __name__ = 'lims.range.copy.result'

    message = fields.Text('Message', readonly=True)


class CopyRange(Wizard):
    'Copy Range'
    __name__ = 'lims.range.copy'

    start = StateView('lims.range.copy.start',
        'lims.copy_range_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Confirm', 'confirm', 'tryton-ok', default=True),
            ])
    confirm = StateTransition()
    result = StateView('lims.range.copy.result',
        'lims.copy_range_result_view_form', [
            Button('Ok', 'end', 'tryton-ok', default=True),
            ])

    def transition_confirm(self):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Range = pool.get('lims.range')

        clause = [
            ('range_type', '=', self.start.origin_range_type.id),
            ('product_type', '=', self.start.origin_product_type.id),
            ('matrix', '=', self.start.origin_matrix.id),
            ]
        origins = Range.search(clause)

        range_type_id = self.start.destination_type.id
        product_type_id = self.start.destination_product_type.id
        matrix_id = self.start.destination_matrix.id

        existing_ranges = []
        new_ranges = []
        for origin in origins:
            # check if range already exists
            cursor.execute('SELECT id '
                'FROM "' + Range._table + '" '
                'WHERE range_type = %s '
                    'AND product_type = %s '
                    'AND matrix = %s '
                    'AND analysis = %s',
                (range_type_id, product_type_id, matrix_id,
                    origin.analysis.id))
            res = cursor.fetchone()
            if res:
                existing_ranges.append(res[0])
                continue

            default = {
                'range_type': range_type_id,
                'product_type': product_type_id,
                'matrix': matrix_id,
                }
            r = Range.copy([origin], default=default)
            new_ranges.append(r[0].id)

        self.result.message = '%s' % gettext(
            'lims.msg_range_copy_new_ranges',
            qty=len(new_ranges))
        if len(existing_ranges) > 0:
            self.result.message += '\n%s' % gettext(
                'lims.msg_range_copy_existing_ranges',
                qty=len(existing_ranges))
        return 'result'

    def default_result(self, fields):
        return {
            'message': self.result.message,
            }


class ControlTendency(ModelSQL, ModelView):
    'Control Chart Tendency'
    __name__ = 'lims.control.tendency'

    _states = {'readonly': Bool(Eval('context', {}).get('readonly', False))}

    family = fields.Many2One('lims.analysis.family', 'Family',
        states=_states, select=True)
    product_type = fields.Many2One('lims.product.type', 'Product type',
        states=_states, select=True)
    matrix = fields.Many2One('lims.matrix', 'Matrix',
        states=_states, select=True)
    fraction_type = fields.Many2One('lims.fraction.type', 'Fraction type',
        required=True, states=_states, select=True)
    analysis = fields.Many2One('lims.analysis', 'Analysis',
        required=True, states=_states, select=True)
    concentration_level = fields.Many2One('lims.concentration.level',
        'Concentration level', states=_states, select=True)
    mean = fields.Float('Mean', required=True, states=_states,
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
    # Mobile Range
    mr_avg_abs_diff = fields.Float('Average of Absolute Differences',
        states=_states)
    mr_d3 = fields.Float('D3 Constant')
    mr_d4 = fields.Float('D4 Constant')
    mr_ll = fields.Function(fields.Float('MR LL',
        depends=['mr_avg_abs_diff', 'mr_d3']), 'get_mr_ll')
    mr_ul = fields.Function(fields.Float('MR UL',
        depends=['mr_avg_abs_diff', 'mr_d4']), 'get_mr_ul')
    # Info
    date_from = fields.Date('Date from', readonly=True)
    date_to = fields.Date('Date to', readonly=True)
    range_min = fields.Float('Range Minimum', digits=(16, 3), readonly=True)
    range_max = fields.Float('Range Maximum', digits=(16, 3), readonly=True)
    rules_description = fields.Function(fields.Text('Rules description'),
        'get_rules_description')

    del _states

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order.insert(0, ('rule_4_count', 'DESC'))
        cls._order.insert(1, ('rule_3_count', 'DESC'))
        cls._order.insert(2, ('rule_2_count', 'DESC'))
        cls._order.insert(3, ('rule_1_count', 'DESC'))
        cls._order.insert(4, ('family', 'ASC'))
        cls._order.insert(5, ('product_type', 'ASC'))
        cls._order.insert(6, ('matrix', 'ASC'))
        cls._order.insert(7, ('analysis', 'ASC'))
        cls._order.insert(8, ('concentration_level', 'ASC'))

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

    @staticmethod
    def default_mr_d3():
        return 0

    @staticmethod
    def default_mr_d4():
        return 3.267

    def get_one_sd(self, name=None):
        return round(self.deviation, self.digits)

    def get_two_sd(self, name=None):
        return round(self.deviation * 2, self.digits)

    def get_three_sd(self, name=None):
        return round(self.deviation * 3, self.digits)

    def get_cv(self, name=None):
        if self.mean:
            return round((self.deviation / self.mean) * 100, self.digits)
        return 0

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

    def get_mr_ll(self, name=None):
        if self.mr_avg_abs_diff:
            return round(self.mr_avg_abs_diff * self.mr_d3, self.digits)
        return 0

    def get_mr_ul(self, name=None):
        if self.mr_avg_abs_diff:
            return round(self.mr_avg_abs_diff * self.mr_d4, self.digits)
        return 0

    def get_rules_description(self, name=None):
        return gettext('lims.msg_rules_description')


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
    icon = fields.Function(fields.Char('Icon', depends=['rule']), 'get_icon')
    # Mobile Range
    mr = fields.Float('Mobile Range')

    @classmethod
    def __setup__(cls):
        super().__setup__()
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
            return {
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

    fraction_type = fields.Many2One('lims.fraction.type', 'Fraction type',
        domain=[('control_charts', '=', True)], required=True)
    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        required=True)
    date_from = fields.Date('Date from', required=True)
    date_to = fields.Date('Date to', required=True)
    family = fields.Many2One('lims.analysis.family', 'Family')
    group_by_family = fields.Boolean('Group by Family')
    product_type = fields.Many2One('lims.product.type', 'Product type',
        domain=[('id', 'in', Eval('product_type_domain'))],
        states={'invisible': Bool(Eval('group_by_family'))},
        depends=['product_type_domain', 'group_by_family'])
    product_type_domain = fields.Function(fields.Many2Many(
        'lims.product.type', None, None, 'Product type domain'),
        'on_change_with_product_type_domain')
    matrix = fields.Many2One('lims.matrix', 'Matrix',
        domain=[('id', 'in', Eval('matrix_domain'))],
        states={'invisible': Bool(Eval('group_by_family'))},
        depends=['matrix_domain', 'group_by_family'])
    matrix_domain = fields.Function(fields.Many2Many('lims.matrix',
        None, None, 'Matrix domain'), 'on_change_with_matrix_domain')
    range_min = fields.Float('Range Minimum', digits=(16, 3))
    range_max = fields.Float('Range Maximum', digits=(16, 3))
    concentration_level = fields.Many2One('lims.concentration.level',
        'Concentration level')

    @staticmethod
    def default_group_by_family():
        return False

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

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._buttons.update({
            'select_all': {},
            })

    @ModelView.button_change('lines')
    def select_all(self, name=None):
        for l in self.lines:
            l.update = True


class ControlResultLine(ModelSQL, ModelView):
    'Control Chart Result Line'
    __name__ = 'lims.control.result_line'

    family = fields.Many2One('lims.analysis.family', 'Family',
        readonly=True)
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
        'concentration_level', ]), 'get_prev_field')
    prev_one_sd = fields.Function(fields.Float('Previous 1 SD', depends=[
        'product_type', 'matrix', 'fraction_type', 'analysis',
        'concentration_level', ]), 'get_prev_field')
    prev_two_sd = fields.Function(fields.Float('Previous 2 SD', depends=[
        'product_type', 'matrix', 'fraction_type', 'analysis',
        'concentration_level', ]), 'get_prev_field')
    prev_three_sd = fields.Function(fields.Float('Previous 3 SD', depends=[
        'product_type', 'matrix', 'fraction_type', 'analysis',
        'concentration_level', ]), 'get_prev_field')
    prev_cv = fields.Function(fields.Float('Previous CV (%)', depends=[
        'product_type', 'matrix', 'fraction_type', 'analysis',
        'concentration_level', ]), 'get_prev_field')
    details = fields.One2Many('lims.control.result_line.detail', 'line',
        'Details', readonly=True)
    update = fields.Boolean('Update')
    session_id = fields.Integer('Session ID')
    # Mobile Range
    mr_avg_abs_diff = fields.Float('Average of Absolute Differences',
        readonly=True)
    prev_mr_avg_abs_diff = fields.Function(fields.Float(
        'Previous Average of Absolute Differences', depends=[
            'product_type', 'matrix', 'fraction_type', 'analysis',
            'concentration_level', ]), 'get_prev_field')
    # Info
    date_from = fields.Date('Date from', readonly=True)
    date_to = fields.Date('Date to', readonly=True)
    range_min = fields.Float('Range Minimum', digits=(16, 3), readonly=True)
    range_max = fields.Float('Range Maximum', digits=(16, 3), readonly=True)

    @classmethod
    def __register__(cls, module_name):
        super().__register__(module_name)
        cursor = Transaction().connection.cursor()
        cursor.execute('DELETE FROM "' + cls._table + '"')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order.insert(0, ('family', 'ASC'))
        cls._order.insert(1, ('product_type', 'ASC'))
        cls._order.insert(2, ('matrix', 'ASC'))
        cls._order.insert(3, ('analysis', 'ASC'))
        cls._order.insert(4, ('concentration_level', 'ASC'))

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
        return 0

    @classmethod
    def get_prev_field(cls, tendencies, names):
        pool = Pool()
        ControlTendency = pool.get('lims.control.tendency')

        result = {}
        for name in names:
            field_name = name[5:]
            result[name] = {}
            for t in tendencies:
                result[name][t.id] = 0.0
                prev_tendency = ControlTendency.search([
                    ('family', '=', t.family),
                    ('product_type', '=', t.product_type),
                    ('matrix', '=', t.matrix),
                    ('fraction_type', '=', t.fraction_type),
                    ('analysis', '=', t.analysis),
                    ('concentration_level', '=', t.concentration_level),
                    ])
                if prev_tendency:
                    result[name][t.id] = getattr(prev_tendency[0], field_name)
        return result


class ControlResultLineDetail(ModelSQL, ModelView):
    'Control Chart Result Line Detail'
    __name__ = 'lims.control.result_line.detail'

    line = fields.Many2One('lims.control.result_line', 'Line',
        ondelete='CASCADE', select=True, required=True)
    date = fields.Date('Date')
    fraction = fields.Many2One('lims.fraction', 'Fraction')
    device = fields.Many2One('lims.lab.device', 'Device')
    result = fields.Float('Result')
    #
    mr = fields.Float('Mobile Range')

    @classmethod
    def __setup__(cls):
        super().__setup__()
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
        for field in ('date_from', 'date_to', 'range_min', 'range_max',
                'group_by_family'):
            if (hasattr(self.start, field) and getattr(self.start, field)):
                res[field] = getattr(self.start, field)
        for field in ('family', 'laboratory', 'product_type', 'matrix',
                'fraction_type', 'concentration_level'):
            if (hasattr(self.start, field) and getattr(self.start, field)):
                res[field] = getattr(self.start, field).id
        for field in ('product_type_domain', 'matrix_domain'):
            if (hasattr(self.start, field) and getattr(self.start, field)):
                res[field] = [f.id for f in getattr(self.start, field)]

        return res

    def transition_search(self):
        if self.start.group_by_family:
            res_lines = self._create_grouped_lines()
        else:
            res_lines = self._create_lines()

        if res_lines:
            self.result.lines = res_lines
            return 'result'
        return 'empty'

    def _create_lines(self):
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
        if self.start.concentration_level:
            clause.append(('concentration_level', '=',
                self.start.concentration_level.id))

        lines = NotebookLine.search(clause,
            order=[('end_date', 'ASC'), ('id', 'ASC')])
        if not lines:
            return []

        range_min = self.start.range_min
        range_max = self.start.range_max

        check_line_family = False
        if self.start.family:
            check_line_family = True
            cursor.execute('SELECT product_type, matrix '
                'FROM "' + AnalysisFamilyCertificant._table + '" '
                'WHERE family = %s',
                (self.start.family.id,))
            res = cursor.fetchall()
            families = [(x[0], x[1]) for x in res]

        records = {}
        for line in lines:
            if check_line_family:
                family_key = (line.notebook.product_type.id,
                    line.notebook.matrix.id)
                if family_key not in families:
                    continue
            try:
                result = float(line.result or None)
            except (TypeError, ValueError):
                continue
            if range_min and result < range_min:
                continue
            if range_max and result > range_max:
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
                    'mr_last_result': None,
                    }
            mr = (records[key]['mr_last_result'] and
                abs(result - records[key]['mr_last_result']) or 0.0)
            records[key]['mr_last_result'] = result
            records[key]['details'][line.id] = {
                'date': line.end_date,
                'fraction': line.notebook.fraction.id,
                'device': line.device.id if line.device else None,
                'result': result,
                'mr': mr,
                }
        if not records:
            return []

        to_create = []
        for record in records.values():
            details = [d for d in record['details'].values()]
            to_create.append({
                'session_id': self._session_id,
                'family': None,
                'product_type': record['product_type'],
                'matrix': record['matrix'],
                'fraction_type': record['fraction_type'],
                'analysis': record['analysis'],
                'concentration_level': record['concentration_level'],
                'details': [('create', details)],
                'date_from': self.start.date_from,
                'date_to': self.start.date_to,
                'range_min': range_min,
                'range_max': range_max,
                })
        if to_create:
            res_lines = ControlResultLine.create(to_create)

            to_save = []
            for line in res_lines:
                count = 0
                total = 0.00
                mr_abs_diff = 0.00
                for detail in line.details:
                    count += 1
                    total += detail.result
                    mr_abs_diff += detail.mr
                if count > 2:
                    mr_avg_abs_diff = round(
                        mr_abs_diff / (count - 1), 2)
                else:
                    mr_avg_abs_diff = mr_abs_diff
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
                line.mr_avg_abs_diff = mr_avg_abs_diff
                to_save.append(line)
            ControlResultLine.save(to_save)
            return res_lines
        return []

    def _create_grouped_lines(self):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        ControlResultLine = pool.get('lims.control.result_line')
        AnalysisFamily = pool.get('lims.analysis.family')
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
        if self.start.concentration_level:
            clause.append(('concentration_level', '=',
                self.start.concentration_level.id))

        lines = NotebookLine.search(clause,
            order=[('end_date', 'ASC'), ('id', 'ASC')])
        if not lines:
            return []

        range_min = self.start.range_min
        range_max = self.start.range_max

        if self.start.family:
            all_families = [self.start.family]
        else:
            all_families = AnalysisFamily.search([])

        records = {}
        for family in all_families:
            cursor.execute('SELECT product_type, matrix '
                'FROM "' + AnalysisFamilyCertificant._table + '" '
                'WHERE family = %s',
                (family.id,))
            res = cursor.fetchall()
            families = [(x[0], x[1]) for x in res]

            for line in lines:
                family_key = (line.notebook.product_type.id,
                    line.notebook.matrix.id)
                if family_key not in families:
                    continue
                try:
                    result = float(line.result or None)
                except (TypeError, ValueError):
                    continue
                if range_min and result < range_min:
                    continue
                if range_max and result > range_max:
                    continue

                family_id = family.id
                fraction_type_id = line.notebook.fraction_type.id
                analysis_id = line.analysis.id
                concentration_level_id = (line.concentration_level.id if
                    line.concentration_level else None)

                key = (family_id, analysis_id, concentration_level_id)
                if key not in records:
                    records[key] = {
                        'family': family_id,
                        'fraction_type': fraction_type_id,
                        'analysis': analysis_id,
                        'concentration_level': concentration_level_id,
                        'details': {},
                        'mr_last_result': None,
                        }
                mr = (records[key]['mr_last_result'] and
                    abs(result - records[key]['mr_last_result']) or 0.0)
                records[key]['mr_last_result'] = result
                records[key]['details'][line.id] = {
                    'date': line.end_date,
                    'fraction': line.notebook.fraction.id,
                    'device': line.device.id if line.device else None,
                    'result': result,
                    'mr': mr,
                    }
        if not records:
            return []

        to_create = []
        for record in records.values():
            details = [d for d in record['details'].values()]
            to_create.append({
                'session_id': self._session_id,
                'family': record['family'],
                'product_type': None,
                'matrix': None,
                'fraction_type': record['fraction_type'],
                'analysis': record['analysis'],
                'concentration_level': record['concentration_level'],
                'details': [('create', details)],
                'date_from': self.start.date_from,
                'date_to': self.start.date_to,
                'range_min': range_min,
                'range_max': range_max,
                })
        if to_create:
            res_lines = ControlResultLine.create(to_create)

            to_save = []
            for line in res_lines:
                count = 0
                total = 0.00
                mr_abs_diff = 0.00
                for detail in line.details:
                    count += 1
                    total += detail.result
                    mr_abs_diff += detail.mr
                if count > 2:
                    mr_avg_abs_diff = round(
                        mr_abs_diff / (count - 1), 2)
                else:
                    mr_avg_abs_diff = mr_abs_diff
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
                line.mr_avg_abs_diff = mr_avg_abs_diff
                to_save.append(line)
            ControlResultLine.save(to_save)
            return res_lines
        return []

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
                ('family', '=', line.family),
                ('product_type', '=', line.product_type),
                ('matrix', '=', line.matrix),
                ('fraction_type', '=', line.fraction_type),
                ('analysis', '=', line.analysis),
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
                    'mr_avg_abs_diff': line.mr_avg_abs_diff,
                    'date_from': line.date_from,
                    'date_to': line.date_to,
                    'range_min': line.range_min,
                    'range_max': line.range_max,
                    })
                tendencies.extend(tendency)
            else:
                tendency, = ControlTendency.create([{
                    'family': line.family and line.family.id,
                    'product_type': line.product_type and line.product_type.id,
                    'matrix': line.matrix and line.matrix.id,
                    'fraction_type': line.fraction_type.id,
                    'analysis': line.analysis.id,
                    'concentration_level': concentration_level_id,
                    'mean': line.mean,
                    'deviation': line.deviation,
                    'min_cv': min_cv,
                    'max_cv': max_cv,
                    'min_cv_corr_fact': min_cv_corr_fact,
                    'max_cv_corr_fact': max_cv_corr_fact,
                    'mr_avg_abs_diff': line.mr_avg_abs_diff,
                    'date_from': line.date_from,
                    'date_to': line.date_to,
                    'range_min': line.range_min,
                    'range_max': line.range_max,
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

    fraction_type = fields.Many2One('lims.fraction.type', 'Fraction type',
        domain=[('control_charts', '=', True)], required=True)
    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        required=True)
    date_from = fields.Date('Date from', required=True)
    date_to = fields.Date('Date to', required=True)
    family = fields.Many2One('lims.analysis.family', 'Family')
    group_by_family = fields.Boolean('Group by Family')
    product_type = fields.Many2One('lims.product.type', 'Product type',
        domain=[('id', 'in', Eval('product_type_domain'))],
        states={'invisible': Bool(Eval('group_by_family'))},
        depends=['product_type_domain', 'group_by_family'])
    product_type_domain = fields.Function(fields.Many2Many(
        'lims.product.type', None, None, 'Product type domain'),
        'on_change_with_product_type_domain')
    matrix = fields.Many2One('lims.matrix', 'Matrix',
        domain=[('id', 'in', Eval('matrix_domain'))],
        states={'invisible': Bool(Eval('group_by_family'))},
        depends=['matrix_domain', 'group_by_family'])
    matrix_domain = fields.Function(fields.Many2Many('lims.matrix',
        None, None, 'Matrix domain'), 'on_change_with_matrix_domain')
    concentration_level = fields.Many2One('lims.concentration.level',
        'Concentration level')

    @staticmethod
    def default_group_by_family():
        return False

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
        if self.start.group_by_family:
            if self.start.family:
                clause.append(('family', '=', self.start.family.id))
            else:
                clause.append(('family', '!=', None))
        else:
            clause.append(('family', '=', None))
            if self.start.product_type:
                clause.append(('product_type', '=',
                    self.start.product_type.id))
            if self.start.matrix:
                clause.append(('matrix', '=', self.start.matrix.id))
        if self.start.concentration_level:
            clause.append(('concentration_level', '=',
                self.start.concentration_level.id))

        tendencies = ControlTendency.search(clause)
        if not tendencies:
            return 'end'

        check_tendency_family = False
        if self.start.family and not self.start.group_by_family:
            check_tendency_family = True
            cursor.execute('SELECT product_type, matrix '
                'FROM "' + AnalysisFamilyCertificant._table + '" '
                'WHERE family = %s',
                (self.start.family.id,))
            res = cursor.fetchall()
            families = [(x[0], x[1]) for x in res]

        for tendency in tendencies:
            if check_tendency_family:
                family_key = (tendency.product_type.id, tendency.matrix.id)
                if family_key not in families:
                    continue

            old_details = ControlTendencyDetail.search([
                ('tendency', '=', tendency.id),
                ])
            if old_details:
                ControlTendencyDetail.delete(old_details)

            check_line_family = False
            if tendency.family:
                check_line_family = True
                cursor.execute('SELECT product_type, matrix '
                    'FROM "' + AnalysisFamilyCertificant._table + '" '
                    'WHERE family = %s',
                    (tendency.family.id,))
                res = cursor.fetchall()
                tendency_families = [(x[0], x[1]) for x in res]

            concentration_level_id = (tendency.concentration_level.id if
                tendency.concentration_level else None)
            clause = [
                ('laboratory', '=', self.start.laboratory.id),
                ('notebook.fraction.type', '=', tendency.fraction_type.id),
                ('analysis', '=', tendency.analysis.id),
                ('concentration_level', '=', concentration_level_id),
                ('result', 'not in', [None, '']),
                ('annulled', '=', False),
                ]
            if not check_line_family:
                clause.extend([
                    ('notebook.product_type', '=', tendency.product_type.id),
                    ('notebook.matrix', '=', tendency.matrix.id),
                    ])

            rule_1_count = 0
            rule_2_count = 0
            rule_3_count = 0
            rule_4_count = 0
            all_lines = NotebookLine.search(clause + [
                    ('end_date', '>=', self.start.date_from),
                    ('end_date', '<=', self.start.date_to),
                    ], order=[('end_date', 'ASC'), ('id', 'ASC')])
            if not check_line_family:
                lines = all_lines
            else:
                lines = []
                for line in all_lines:
                    family_key = (line.notebook.product_type.id,
                        line.notebook.matrix.id)
                    if family_key in tendency_families:
                        lines.append(line)
            if lines:
                results = []
                prevs = 8 - len(lines)  # Qty of previous results required
                if prevs > 0:
                    all_prev_lines = NotebookLine.search(clause + [
                            ('end_date', '<', self.start.date_from),
                            ], order=[('end_date', 'ASC'), ('id', 'ASC')],
                            limit=prevs)
                    if not check_line_family:
                        prev_lines = all_prev_lines
                    else:
                        prev_lines = []
                        for line in all_prev_lines:
                            family_key = (line.notebook.product_type.id,
                                line.notebook.matrix.id)
                            if family_key in tendency_families:
                                prev_lines.append(line)
                    if prev_lines:
                        for line in prev_lines:
                            try:
                                result = float(line.result if
                                    line.result else None)
                            except(TypeError, ValueError):
                                continue
                            results.append(result)

                mr_last_result = None
                to_create = []
                for line in lines:
                    try:
                        result = float(line.result if
                            line.result else None)
                    except(TypeError, ValueError):
                        continue
                    mr = (mr_last_result and
                          abs(result - mr_last_result) or 0.0)
                    mr_last_result = result
                    results.append(result)
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
                        'mr': mr,
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


class ControlChartReport(Report):
    'Control Chart'
    __name__ = 'lims.control_chart.report'

    @classmethod
    def get_context(cls, records, header, data):
        pool = Pool()
        Company = pool.get('company.company')
        ControlTendency = pool.get('lims.control.tendency')

        report_context = super().get_context(records, header, data)
        if 'id' in data:
            tendency = ControlTendency(data['id'])
        else:
            tendency = ControlTendency(records[0].id)

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
        objects = {
            'number': {
                'name': gettext('lims.msg_number'), 'order': 1, 'recs': {}},
            'result': {
                'name': gettext('lims.msg_control_chart_result'),
                'order': 2, 'recs': {}},
            'ucl': {'name': gettext('lims.msg_ucl'), 'order': 3, 'recs': {}},
            'uwl': {'name': gettext('lims.msg_uwl'), 'order': 4, 'recs': {}},
            'upl': {'name': gettext('lims.msg_upl'), 'order': 5, 'recs': {}},
            'cl': {'name': gettext('lims.msg_cl'), 'order': 6, 'recs': {}},
            'lpl': {'name': gettext('lims.msg_lpl'), 'order': 7, 'recs': {}},
            'lwl': {'name': gettext('lims.msg_lwl'), 'order': 8, 'recs': {}},
            'lcl': {'name': gettext('lims.msg_lcl'), 'order': 9, 'recs': {}},
            'cv': {'name': gettext('lims.msg_cv'), 'order': 10, 'recs': {}},
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
        index = columns
        cols = []
        ds = {}
        for r in sorted(list(records.values()), key=lambda x: x['order']):
            cols.append(r['name'])
            ds[r['name']] = [r['recs'][col] for col in index]
        df = pd.DataFrame(ds, index=index)
        df = df.reindex(cols, axis=1)

        output = BytesIO()
        try:
            ax = df[[gettext('lims.msg_ucl'),
                ]].plot(kind='line', color='red', rot=45, fontsize=7,
                    figsize=(10, 7.5), linestyle='-')
            ax = df[[gettext('lims.msg_uwl'),
                ]].plot(kind='line', color='orange', rot=45, fontsize=7,
                    figsize=(10, 7.5), linestyle='-', ax=ax)
            ax = df[[gettext('lims.msg_upl'),
                ]].plot(kind='line', color='yellow', rot=45, fontsize=7,
                    figsize=(10, 7.5), linestyle='--', ax=ax)
            ax = df[[gettext('lims.msg_cl'),
                ]].plot(kind='line', color='green', rot=45, fontsize=7,
                    figsize=(10, 7.5), linestyle='-', ax=ax)
            ax = df[[gettext('lims.msg_lpl'),
                ]].plot(kind='line', color='yellow', rot=45, fontsize=7,
                    figsize=(10, 7.5), linestyle='--', ax=ax)
            ax = df[[gettext('lims.msg_lwl'),
                ]].plot(kind='line', color='orange', rot=45, fontsize=7,
                    figsize=(10, 7.5), linestyle='-', ax=ax)
            ax = df[[gettext('lims.msg_lcl'),
                ]].plot(kind='line', color='red', rot=45, fontsize=7,
                    figsize=(10, 7.5), linestyle='-', ax=ax)
            ax = df[[gettext('lims.msg_control_chart_result'),
                ]].plot(kind='line', color='blue', rot=45, fontsize=7,
                    figsize=(10, 7.5), marker='o', linestyle='-', ax=ax)

            ax.legend(loc='center left', bbox_to_anchor=(1.0, 0.5))
            ax.get_figure().savefig(output, bbox_inches='tight', dpi=300)
            image = output.getvalue()
            output.close()
            return image
        except TypeError:
            return output.getvalue()


class TrendChart(ModelSQL, ModelView):
    'Trend Chart'
    __name__ = 'lims.trend.chart'

    name = fields.Char('Name', required=True)
    analysis = fields.One2Many('lims.trend.chart.analysis', 'chart',
        'Analysis', required=True)
    uom = fields.Many2One('product.uom', 'UoM',
        domain=[('category.lims_only_available', '=', True)])
    analysis_y2 = fields.One2Many('lims.trend.chart.analysis2', 'chart',
        'Analysis (Y2)')
    uom_y2 = fields.Many2One('product.uom', 'UoM (Y2)',
        domain=[('category.lims_only_available', '=', True)])
    quantity = fields.Integer('Qty. of Precedents', required=True)
    filter = fields.Selection([
        ('any', 'Any Sample'),
        ('party', 'Same Party'),
        ('sample_producer', 'Same Sample Producer'),
        ], 'Precedents Filter', sort=False, required=True)
    x_axis = fields.Selection([
        ('date', 'Date'),
        ('number', 'Sample'),
        ], 'X Axis', sort=False, required=True)
    x_axis_string = x_axis.translated('x_axis')
    active = fields.Boolean('Active', help='Check to include in future use')

    @classmethod
    def default_active(cls):
        return False

    @staticmethod
    def default_filter():
        return 'any'

    @staticmethod
    def default_x_axis():
        return 'date'

    @classmethod
    def validate(cls, charts):
        super().validate(charts)
        for chart in charts:
            chart.check_analysis_qty()
            chart.check_uom()

    def check_analysis_qty(self):
        limit = 10
        if (len(self.analysis) + len(self.analysis_y2)) > limit:
            raise UserError(gettext('lims.msg_trend_chart_analysis_qty',
                qty=limit))

    def check_uom(self):
        cursor = Transaction().connection.cursor()
        Typification = Pool().get('lims.typification')

        def _check_uom(analysis_ids):
            uoms = []
            for a_id in analysis_ids:
                cursor.execute('SELECT DISTINCT(t.start_uom) '
                    'FROM "' + Typification._table + '" t '
                    'WHERE t.analysis = %s', (str(a_id),))
                typifications = cursor.fetchall()
                if not typifications:
                    raise UserError(gettext(
                        'lims.msg_trend_chart_analysis_uom'))
                analysis_uoms = [x[0] for x in typifications]
                if not uoms:
                    uoms = analysis_uoms
                ok = False
                for a_uom in analysis_uoms:
                    if a_uom in uoms:
                        ok = True
                        break
                if not ok:
                    raise UserError(gettext(
                        'lims.msg_trend_chart_analysis_uom'))
            return uoms

        uoms = _check_uom(a.analysis.id for a in self.analysis)
        if self.uom and self.uom.id not in uoms:
            raise UserError(gettext('lims.msg_trend_chart_analysis_uom'))
        uoms = _check_uom(a.analysis.id for a in self.analysis_y2)
        if self.uom_y2 and self.uom_y2.id not in uoms:
            raise UserError(gettext('lims.msg_trend_chart_analysis_uom'))

    def get_tree_view(self):
        fields = []
        definition = {}

        fields.append('<field name="x_axis"/>')
        definition['x_axis'] = {
            'name': 'x_axis',
            'string': self.x_axis_string,
            'type': 'char',
            'readonly': True,
            'help': None,
            }

        i = 1
        for analysis in self.analysis:
            name = 'analysis%s' % str(i)
            fields.append('<field name="%s"/>' % name)
            definition[name] = {
                'name': name,
                'string': analysis.analysis.description,
                'type': 'char',
                'readonly': True,
                'help': None,
                }
            i += 1
        for analysis in self.analysis_y2:
            name = 'analysis%s' % str(i)
            fields.append('<field name="%s"/>' % name)
            definition[name] = {
                'name': name,
                'string': analysis.analysis.description,
                'type': 'char',
                'readonly': True,
                'help': None,
                }
            i += 1

        xml = ('<?xml version="1.0"?>\n'
            '<tree>\n'
            '%s\n'
            '</tree>') % ('\n'.join(fields))
        res = {
            'type': 'tree',
            'arch': xml,
            'fields': definition,
            }
        return res

    def get_graph_view(self):
        fields = []
        definition = {}

        definition['x_axis'] = {
            'name': 'x_axis',
            'string': self.x_axis_string,
            'type': 'char',
            'readonly': True,
            'help': None,
            }

        i = 1
        for analysis in self.analysis:
            name = 'analysis%s' % str(i)
            fields.append('<field name="%s"/>' % name)
            definition[name] = {
                'name': name,
                'string': analysis.analysis.description,
                'type': 'char',
                'readonly': True,
                'help': None,
                }
            i += 1
        for analysis in self.analysis_y2:
            name = 'analysis%s' % str(i)
            fields.append('<field name="%s" axis="1"/>' % name)
            definition[name] = {
                'name': name,
                'string': analysis.analysis.description,
                'type': 'char',
                'readonly': True,
                'help': None,
                }
            i += 1

        xml = ('<?xml version="1.0"?>\n'
            '<graph string="%s" type="line" legend="1">\n'
            '<x><field name="x_axis"/></x>\n'
            '<y>\n''%s\n''</y>\n'
            '</graph>') % (self.name, '\n'.join(fields))
        res = {
            'type': 'graph',
            'arch': xml,
            'fields': definition,
            }
        return res

    def get_plot(self, session_id):
        pool = Pool()
        TrendChartData = pool.get('lims.trend.chart.data')

        index = []
        cols, cols_y2 = {}, {}
        ds, ds2 = {}, {}

        i = 1
        for analysis in self.analysis:
            name = 'analysis%s' % str(i)
            cols[name] = analysis.analysis.description
            ds[cols[name]] = []
            i += 1
        for analysis in self.analysis_y2:
            name = 'analysis%s' % str(i)
            cols_y2[name] = analysis.analysis.description
            ds2[cols_y2[name]] = []
            i += 1

        records = TrendChartData.search([
            ('session_id', '=', session_id),
            ])
        for r in records:
            index.append(r.x_axis)
            for a_name, a_description in cols.items():
                val = getattr(r, a_name, None)
                ds[a_description].append(float(val)
                    if val is not None else None)
            for a_name, a_description in cols_y2.items():
                val = getattr(r, a_name, None)
                ds2[a_description].append(float(val)
                    if val is not None else None)

        df = pd.DataFrame(ds, index=index)
        df = df.reindex(cols.values(), axis=1)
        try:
            df_interpolated = df.interpolate()
        except TypeError:
            df_interpolated = df
        if ds2:
            df2 = pd.DataFrame(ds2, index=index)
            df2 = df2.reindex(cols_y2.values(), axis=1)
            try:
                df2_interpolated = df2.interpolate()
            except TypeError:
                df2_interpolated = df2

        output = BytesIO()
        try:
            with plt.rc_context(rc={'figure.max_open_warning': 0}):
                ax = df_interpolated.plot(kind='line',
                    rot=45, fontsize=14, figsize=(10, 7.5),
                    linestyle='-', marker=None, legend=None)
                ax = df.plot(kind='line',
                    rot=45, fontsize=14, figsize=(10, 7.5),
                    linestyle='', marker='o', color='black',
                    legend=None, ax=ax)
                ax.set_xlabel(self.x_axis_string)
                if self.uom:
                    ax.set_ylabel(self.uom.symbol)
                if ds2:
                    try:
                        ax = df2_interpolated.plot(kind='line',
                            rot=45, fontsize=14, figsize=(10, 7.5),
                            linestyle='-', marker=None, legend=None,
                            secondary_y=True, ax=ax)
                        ax = df2.plot(kind='line',
                            rot=45, fontsize=14, figsize=(10, 7.5),
                            linestyle='', marker='o', color='black',
                            legend=None, secondary_y=True, ax=ax)
                        if self.uom_y2:
                            ax.set_ylabel(self.uom_y2.symbol)
                    except TypeError:
                        pass

                loc, i = ['upper left', 'upper right'], 0
                for axis in ax.figure.axes:
                    handles, labels = [], []
                    for h, l in zip(*axis.get_legend_handles_labels()):
                        if l in labels:
                            continue
                        handles.append(h)
                        labels.append(l)
                    axis.legend(handles, labels, loc=loc[i])
                    i += 1

                ax.get_figure().savefig(output, bbox_inches='tight', dpi=300)
                image = output.getvalue()
                output.close()
            return image

        except (TypeError, ModuleNotFoundError):
            if ds2:
                try:
                    ax = df2_interpolated.plot(kind='line',
                        rot=45, fontsize=14, figsize=(10, 7.5),
                        linestyle='-', marker=None, legend=None,
                        secondary_y=True)
                    ax = df2.plot(kind='line',
                        rot=45, fontsize=14, figsize=(10, 7.5),
                        linestyle='', marker='o', color='black',
                        legend=None, secondary_y=True, ax=ax)
                    ax.set_xlabel(self.x_axis_string)
                    if self.uom_y2:
                        ax.set_ylabel(self.uom_y2.symbol)

                    loc, i = ['upper left', 'upper right'], 0
                    for axis in ax.figure.axes:
                        handles, labels = [], []
                        for h, l in zip(*axis.get_legend_handles_labels()):
                            if l in labels:
                                continue
                            handles.append(h)
                            labels.append(l)
                        axis.legend(handles, labels, loc=loc[i])
                        i += 1

                    ax.get_figure().savefig(output, bbox_inches='tight',
                        dpi=300)
                    image = output.getvalue()
                    output.close()
                    return image

                except (TypeError, ModuleNotFoundError):
                    pass
            return output.getvalue()

    @classmethod
    def clean(cls):
        TrendChartData = Pool().get('lims.trend.chart.data')
        to_delete = cls.search([('active', '=', False)])
        cls.delete(to_delete)
        to_delete = TrendChartData.search([])
        TrendChartData.delete(to_delete)


class TrendChartAnalysis(ModelSQL, ModelView):
    'Trend Chart Analysis'
    __name__ = 'lims.trend.chart.analysis'

    chart = fields.Many2One('lims.trend.chart', 'Trend Chart',
        ondelete='CASCADE', select=True, required=True)
    analysis = fields.Many2One('lims.analysis', 'Analysis', required=True)
    order = fields.Integer('Order')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order.insert(0, ('order', 'ASC'))


class TrendChartAnalysis2(ModelSQL, ModelView):
    'Trend Chart Analysis'
    __name__ = 'lims.trend.chart.analysis2'

    chart = fields.Many2One('lims.trend.chart', 'Trend Chart',
        ondelete='CASCADE', select=True, required=True)
    analysis = fields.Many2One('lims.analysis', 'Analysis', required=True)
    order = fields.Integer('Order')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order.insert(0, ('order', 'ASC'))


class OpenTrendChartStart(ModelView):
    'Open Trend Chart'
    __name__ = 'lims.trend.chart.open.start'

    chart = fields.Many2One('lims.trend.chart', 'Trend Chart', required=True)
    notebook = fields.Many2One('lims.notebook', 'Sample', required=True)


class OpenTrendChart(Wizard):
    'Open Trend Chart'
    __name__ = 'lims.trend.chart.open'

    start = StateView('lims.trend.chart.open.start',
        'lims.trend_chart_open_start_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Open', 'compute', 'tryton-ok', default=True),
            ])
    compute = StateTransition()
    open = StateAction('lims.act_trend_chart_data')

    def default_start(self, fields):
        chart_id = None
        if Transaction().context.get('active_model') == 'lims.trend.chart':
            chart_id = Transaction().context.get('active_id')
        defaults = {'chart': chart_id}
        return defaults

    def transition_compute(self):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        TrendChartData = pool.get('lims.trend.chart.data')
        Notebook = pool.get('lims.notebook')
        NotebookLine = pool.get('lims.notebook.line')

        session_id = self._session_id
        cursor.execute('DELETE FROM "' + TrendChartData._table + '" '
            'WHERE session_id = \'%s\'', (session_id,))

        chart = self.start.chart
        clause = self._get_clause()
        order = self._get_order()
        reportable_analysis = self._get_reportable_analysis()

        records = []
        notebooks = Notebook.search(clause, order=order, limit=chart.quantity)
        notebooks.reverse()
        for notebook in notebooks:
            record = {
                'session_id': session_id,
                'x_axis': self._get_x_axis(notebook),
                }
            i = 1
            for a in chart.analysis:
                record['analysis%s' % str(i)] = None
                if a.analysis.id not in reportable_analysis:
                    i += 1
                    continue
                line = NotebookLine.search([
                    ('notebook', '=', notebook),
                    ('analysis', '=', a.analysis),
                    ('accepted', '=', True),
                    ('result', 'not in', [None, '']),
                    ])
                if line:
                    record['analysis%s' % str(i)] = line[0].result.replace(
                        ',', '.')
                i += 1
            for a in chart.analysis_y2:
                record['analysis%s' % str(i)] = None
                if a.analysis.id not in reportable_analysis:
                    i += 1
                    continue
                line = NotebookLine.search([
                    ('notebook', '=', notebook),
                    ('analysis', '=', a.analysis),
                    ('accepted', '=', True),
                    ('result', 'not in', [None, '']),
                    ])
                if line:
                    record['analysis%s' % str(i)] = line[0].result.replace(
                        ',', '.')
                i += 1
            records.append(record)
        TrendChartData.create(records)

        if Transaction().context.get('active_model') == 'lims.trend.chart':
            return 'open'
        return 'end'

    def _get_clause(self):
        chart = self.start.chart
        notebook = self.start.notebook
        clause = [
            ('product_type', '=', notebook.product_type),
            ('matrix', '=', notebook.matrix),
            ]

        if chart.filter == 'party':
            clause.append(('party', '=', notebook.party))
        elif chart.filter == 'sample_producer':
            clause.append(('fraction.sample.producer', '=',
                notebook.fraction.sample.producer))

        if chart.x_axis == 'date':
            clause.append(('date', '<=', notebook.date))
        elif chart.x_axis == 'number':
            clause.append(('fraction.sample.number', '<=',
                notebook.fraction.sample.number))
        return clause

    def _get_order(self):
        chart = self.start.chart
        if chart.x_axis == 'date':
            return [('date', 'DESC')]
        elif chart.x_axis == 'number':
            return [('fraction.sample.number', 'DESC')]
        return []

    def _get_reportable_analysis(self):
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')

        lines = NotebookLine.search([
            ('notebook', '=', self.start.notebook),
            ('report', '=', True)
            ])
        return [l.analysis.id for l in lines]

    def _get_x_axis(self, notebook):
        chart = self.start.chart
        if chart.x_axis == 'date':
            return notebook.date2
        return notebook.rec_name

    def do_open(self, action):
        context = {
            'chart_id': self.start.chart.id,
            'session_id': self._session_id,
            }
        domain = [('session_id', '=', self._session_id)]
        action['pyson_context'] = PYSONEncoder().encode(context)
        action['pyson_domain'] = PYSONEncoder().encode(domain)
        action['views'] = [(None, 'graph'), (None, 'tree')]
        action['name'] += ' - %s' % self.start.chart.name
        return action, {}

    def transition_open(self):
        return 'end'


class TrendChartData(ModelSQL, ModelView):
    'Trend Chart'
    __name__ = 'lims.trend.chart.data'

    session_id = fields.Integer('Session ID')
    x_axis = fields.Char('X Axis')
    analysis1 = fields.Char('Analysis 1')
    analysis2 = fields.Char('Analysis 2')
    analysis3 = fields.Char('Analysis 3')
    analysis4 = fields.Char('Analysis 4')
    analysis5 = fields.Char('Analysis 5')
    analysis6 = fields.Char('Analysis 6')
    analysis7 = fields.Char('Analysis 7')
    analysis8 = fields.Char('Analysis 8')
    analysis9 = fields.Char('Analysis 9')
    analysis10 = fields.Char('Analysis 10')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.__rpc__['fields_view_get'].cache = None

    @classmethod
    def fields_view_get(cls, view_id=None, view_type='form', level=None):
        if Pool().test:
            return
        TrendChart = Pool().get('lims.trend.chart')

        chart_id = Transaction().context.get('chart_id', None)
        if not chart_id:
            return

        chart = TrendChart(chart_id)
        view_info = getattr(chart, 'get_%s_view' % view_type)()
        res = {
            'view_id': view_id,
            'type': view_info['type'],
            'arch': view_info['arch'],
            'fields': view_info['fields'],
            'field_childs': None,
            }
        return res


class DownloadTrendChart(Wizard):
    'Download Trend Chart'
    __name__ = 'lims.trend.chart.download'

    start = StateTransition()
    open = StateReport('lims.trend.chart.report')

    def transition_start(self):
        context = Transaction().context
        if context.get('chart_id') and context.get('session_id'):
            return 'open'
        return 'end'

    def do_open(self, action):
        context = Transaction().context
        data = {
            'chart_id': context.get('chart_id'),
            'session_id': context.get('session_id'),
            }
        return action, data

    def transition_open(self):
        return 'end'


class TrendChartReport(Report):
    'Trend Chart'
    __name__ = 'lims.trend.chart.report'

    @classmethod
    def get_context(cls, records, header, data):
        TrendChart = Pool().get('lims.trend.chart')

        report_context = super().get_context(records, header, data)

        chart_id = data.get('chart_id')
        chart = TrendChart(chart_id)

        report_context['title'] = chart.name
        report_context['plot'] = chart.get_plot(data.get('session_id'))
        return report_context
