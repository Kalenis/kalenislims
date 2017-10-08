# -*- coding: utf-8 -*-
# This file is part of lims module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import sys
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import operator
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import logging
from sql import Literal, Join
from sql.functions import CurrentTimestamp

from trytond.model import Workflow, ModelView, ModelSQL, fields, Unique
from trytond.pool import Pool
from trytond.pyson import Eval, Equal, Bool, Not, Or, And, If, Len
from trytond.transaction import Transaction
from trytond.tools import get_smtp_server
from trytond.config import config

__all__ = ['LimsLaboratoryProfessional', 'LimsLaboratory', 'LimsLabMethod',
    'LimsLabDeviceType', 'LimsLabDevice', 'LimsLabDeviceLaboratory',
    'LimsProductType', 'LimsMatrix', 'LimsFormula', 'LimsFractionType',
    'LimsLaboratoryCVCorrection', 'LimsFormulaVariable', 'LimsAnalysis',
    'LimsTypification', 'LimsTypificationAditional',
    'LimsTypificationReadOnly', 'LimsCalculatedTypification',
    'LimsCalculatedTypificationReadOnly', 'LimsPackagingType',
    'LimsAnalysisIncluded', 'LimsAnalysisDevice', 'LimsCertificationType',
    'LimsTechnicalScope', 'LimsTechnicalScopeVersion',
    'LimsTechnicalScopeVersionLine', 'LimsPackagingIntegrity',
    'LimsEntrySuspensionReason', 'LimsEntry', 'LimsZone', 'LimsVariety',
    'LimsSampleProducer', 'LimsSample', 'LimsFraction', 'LimsService',
    'LimsConcentrationLevel', 'LimsEntryDetailAnalysis', 'LimsNotebook',
    'LimsResultsReport', 'LimsPlanification', 'LimsNotebookLine',
    'LimsNotebookLineAllFields', 'LimsNotebookLineProfessional',
    'LimsRangeType', 'LimsResultsReportVersion',
    'LimsResultsReportVersionDetail', 'LimsResultsReportVersionDetailLine',
    'LimsAnalysisFamily', 'LimsAnalysisFamilyCertificant', 'LimsMatrixVariety',
    'LimsLabDeviceTypeLabMethod', 'LimsAnalysisLaboratory',
    'LimsAnalysisLabMethod', 'LimsNotebookLineLaboratoryProfessional',
    'LimsEntryInvoiceContact', 'LimsEntryReportContact',
    'LimsEntryAcknowledgmentContact', 'LimsVolumeConversion',
    'LimsUomConversion', 'LimsRange', 'LimsControlTendency',
    'LimsControlTendencyDetail', 'LimsControlTendencyDetailRule']


class LimsLaboratory(ModelSQL, ModelView):
    'Laboratory'
    __name__ = 'lims.laboratory'
    _rec_name = 'description'

    code = fields.Char('Code', required=True)
    description = fields.Char('Description', required=True)
    default_laboratory_professional = fields.Many2One(
        'lims.laboratory.professional', 'Default professional')
    default_signer = fields.Many2One('lims.laboratory.professional',
        'Default signer', required=True)
    related_location = fields.Many2One('stock.location', 'Related location',
        required=True, domain=[('type', '=', 'storage')])
    cv_corrections = fields.One2Many('lims.laboratory.cv_correction',
        'laboratory', 'CV Corrections',
        help="Corrections for Coefficients of Variation (Control Charts)")
    section = fields.Selection([
        ('amb', 'Ambient'),
        ('for', 'Formulated'),
        ('mi', 'Microbiology'),
        ('rp', 'Agrochemical Residues'),
        ('sq', 'Chemistry'),
        ], 'Section', sort=False)

    @classmethod
    def __setup__(cls):
        super(LimsLaboratory, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code),
                'Laboratory code must be unique'),
            ]

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


class LimsLaboratoryCVCorrection(ModelSQL, ModelView):
    'CV Correction'
    __name__ = 'lims.laboratory.cv_correction'

    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        required=True, ondelete='CASCADE', select=True)
    fraction_type = fields.Many2One('lims.fraction.type', 'Fraction type',
        required=True)
    min_cv = fields.Float('Minimum CV (%)')
    max_cv = fields.Float('Maximum CV (%)')
    min_cv_corr_fact = fields.Float('Correction factor for Minimum CV',
        help="Correction factor for CV between Min and Max")
    max_cv_corr_fact = fields.Float('Correction factor for Maximum CV',
        help="Correction factor for CV greater than Max")


class LimsLaboratoryProfessional(ModelSQL, ModelView):
    'Laboratory Professional'
    __name__ = 'lims.laboratory.professional'
    _rec_name = 'party'

    party = fields.Many2One('party.party', 'Party', required=True,
        domain=[('is_lab_professional', '=', True)])
    code = fields.Char('Code')
    role = fields.Char('Signature role', translate=True)
    signature = fields.Binary('Signature')

    @classmethod
    def __setup__(cls):
        super(LimsLaboratoryProfessional, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code),
                'Professional code must be unique'),
            ('party_uniq', Unique(t, t.party),
                'The party is already associated to a professional'),
            ]

    def get_rec_name(self, name):
        if self.party:
            return self.party.name

    @classmethod
    def search_rec_name(cls, name, clause):
        return [('party',) + tuple(clause[1:])]

    @classmethod
    def get_lab_professional(cls):
        cursor = Transaction().connection.cursor()
        login_user_id = Transaction().user
        cursor.execute('SELECT id '
            'FROM party_party '
            'WHERE is_lab_professional = true '
                'AND lims_user = %s '
            'LIMIT 1', (login_user_id,))
        party_id = cursor.fetchone()
        if not party_id:
            return None
        cursor.execute('SELECT id '
            'FROM "' + cls._table + '" '
            'WHERE party = %s '
            'LIMIT 1', (party_id[0],))
        lab_professional_id = cursor.fetchone()
        if (lab_professional_id):
            return lab_professional_id[0]
        return None


class LimsLabMethod(ModelSQL, ModelView):
    'Laboratory Method'
    __name__ = 'lims.lab.method'

    code = fields.Char('Code', required=True)
    name = fields.Char('Name', required=True, translate=True)
    reference = fields.Char('Reference')
    determination = fields.Char('Determination', required=True)
    requalification_months = fields.Integer('Requalification months',
        required=True)
    supervised_requalification = fields.Boolean('Supervised requalification')
    deprecated_since = fields.Date('Deprecated since')
    pnt = fields.Char('PNT')
    results_estimated_waiting = fields.Integer(
        'Estimated number of days for results')

    @classmethod
    def __setup__(cls):
        super(LimsLabMethod, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code),
                'Method code must be unique'),
            ]

    def get_rec_name(self, name):
        if self.code:
            return self.code + ' - ' + self.name
        else:
            return self.name

    @classmethod
    def search_rec_name(cls, name, clause):
        field = None
        for field in ('code', 'name'):
            records = cls.search([(field,) + tuple(clause[1:])], limit=1)
            if records:
                break
        if records:
            return [(field,) + tuple(clause[1:])]
        return [(cls._rec_name,) + tuple(clause[1:])]

    @classmethod
    def write(cls, *args):
        super(LimsLabMethod, cls).write(*args)
        actions = iter(args)
        for methods, vals in zip(actions, actions):
            if 'results_estimated_waiting' in vals:
                cls.update_laboratory_notebook(methods)

    @classmethod
    def update_laboratory_notebook(cls, methods):
        LimsNotebookLine = Pool().get('lims.notebook.line')

        for method in methods:
            notebook_lines = LimsNotebookLine.search([
                ('method', '=', method.id),
                ('accepted', '=', False),
                ])
            if notebook_lines:
                LimsNotebookLine.write(notebook_lines, {
                    'results_estimated_waiting': (
                        method.results_estimated_waiting),
                    })


class LimsLabDevice(ModelSQL, ModelView):
    'Laboratory Device'
    __name__ = 'lims.lab.device'
    _rec_name = 'description'

    code = fields.Char('Code', required=True)
    description = fields.Char('Description', required=True)
    device_type = fields.Many2One('lims.lab.device.type', 'Device type',
        required=True)
    laboratories = fields.One2Many('lims.lab.device.laboratory', 'device',
        'Laboratories', required=True)
    serial_number = fields.Char('Serial number')

    @classmethod
    def __setup__(cls):
        super(LimsLabDevice, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code),
                'Device code must be unique'),
            ]

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


class LimsLabDeviceType(ModelSQL, ModelView):
    'Laboratory Device Type'
    __name__ = 'lims.lab.device.type'
    _rec_name = 'description'

    code = fields.Char('Code', required=True)
    description = fields.Char('Description', required=True)
    methods = fields.Many2Many('lims.lab.device.type-lab.method',
        'device_type', 'method', 'Methods')

    @classmethod
    def __setup__(cls):
        super(LimsLabDeviceType, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code),
                'Device type code must be unique'),
            ]

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


class LimsLabDeviceTypeLabMethod(ModelSQL):
    'Laboratory Device Type - Laboratory Method'
    __name__ = 'lims.lab.device.type-lab.method'

    device_type = fields.Many2One('lims.lab.device.type', 'Device type',
        ondelete='CASCADE', select=True, required=True)
    method = fields.Many2One('lims.lab.method', 'Method',
        ondelete='CASCADE', select=True, required=True)


class LimsLabDeviceLaboratory(ModelSQL, ModelView):
    'Laboratory Device Laboratory'
    __name__ = 'lims.lab.device.laboratory'

    device = fields.Many2One('lims.lab.device', 'Device', required=True,
        ondelete='CASCADE', select=True)
    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        required=True)
    physically_here = fields.Boolean('Physically here')

    @classmethod
    def __setup__(cls):
        super(LimsLabDeviceLaboratory, cls).__setup__()
        cls._error_messages.update({
            'physically_elsewhere': ('This Device is physically in another'
            ' Laboratory'),
            })

    @staticmethod
    def default_physically_here():
        return True

    @classmethod
    def validate(cls, laboratories):
        super(LimsLabDeviceLaboratory, cls).validate(laboratories)
        for l in laboratories:
            l.check_location()

    def check_location(self):
        if self.physically_here:
            laboratories = self.search([
                ('device', '=', self.device.id),
                ('physically_here', '=', True),
                ('id', '!=', self.id),
                ])
            if laboratories:
                self.raise_user_error('physically_elsewhere')


class LimsTypification(ModelSQL, ModelView):
    'Typification'
    __name__ = 'lims.typification'
    _rec_name = 'analysis'

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
        super(LimsTypification, cls).__setup__()
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
        LimsTechnicalScopeVersionLine = pool.get(
            'lims.technical.scope.version.line')

        version_lines = LimsTechnicalScopeVersionLine.search([
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
        super(LimsTypification, cls).validate(typifications)
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
        typifications = super(LimsTypification, cls).create(vlist)
        active_typifications = [t for t in typifications if t.valid]
        cls.create_typification_calculated(active_typifications)
        return typifications

    @classmethod
    def create_typification_calculated(cls, typifications):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsAnalysis = pool.get('lims.analysis')
        LimsCalculatedTypification = pool.get('lims.typification.calculated')

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

            sets_groups_ids = LimsAnalysis.get_parents_analysis(
                typification.analysis.id)
            for set_group_id in sets_groups_ids:
                t_set_group = LimsCalculatedTypification.search([
                    ('product_type', '=', typification.product_type.id),
                    ('matrix', '=', typification.matrix.id),
                    ('analysis', '=', set_group_id),
                    ])
                if not t_set_group:

                    ia = LimsAnalysis.get_included_analysis_analysis(
                        set_group_id)
                    if not ia:
                        continue
                    included_ids = ', '.join(str(a) for a in ia)

                    cursor.execute('SELECT id '
                        'FROM "' + LimsAnalysis._table + '" '
                        'WHERE id IN (' + included_ids + ') '
                            'AND id NOT IN (' + typified_analysis_ids
                            + ')')
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
                        LimsCalculatedTypification.create(
                            typification_create)

        return typifications

    @classmethod
    def delete(cls, typifications):
        cls.delete_typification_calculated(typifications)
        super(LimsTypification, cls).delete(typifications)

    @classmethod
    def delete_typification_calculated(cls, typifications):
        pool = Pool()
        LimsAnalysis = pool.get('lims.analysis')
        LimsCalculatedTypification = pool.get('lims.typification.calculated')

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

            sets_groups_ids = LimsAnalysis.get_parents_analysis(
                typification.analysis.id)
            for set_group_id in sets_groups_ids:
                typified_set_group = LimsCalculatedTypification.search([
                    ('product_type', '=', typification.product_type.id),
                    ('matrix', '=', typification.matrix.id),
                    ('analysis', '=', set_group_id),
                    ])
                if typified_set_group:
                    LimsCalculatedTypification.delete(typified_set_group)

    @classmethod
    def write(cls, *args):
        super(LimsTypification, cls).write(*args)
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
        LimsNotebookLine = Pool().get('lims.notebook.line')

        for typification in typifications:
            if not typification.valid:
                continue

            # Update not RM
            notebook_lines = LimsNotebookLine.search([
                ('notebook.fraction.special_type', '!=', 'rm'),
                ('notebook.product_type', '=', typification.product_type.id),
                ('notebook.matrix', '=', typification.matrix.id),
                ('analysis', '=', typification.analysis.id),
                ('method', '=', typification.method.id),
                ('end_date', '=', None),
                ])
            if notebook_lines:
                LimsNotebookLine.write(notebook_lines, {
                    'detection_limit': str(
                        typification.detection_limit),
                    'quantification_limit': str(
                        typification.quantification_limit),
                    'initial_concentration': unicode(
                        typification.initial_concentration or ''),
                    'final_concentration': unicode(
                        typification.final_concentration or ''),
                    'initial_unit': typification.start_uom,
                    'final_unit': typification.end_uom,
                    'decimals': typification.calc_decimals,
                    'report': typification.report,
                    })

            # Update RM
            notebook_lines = LimsNotebookLine.search([
                ('notebook.fraction.special_type', '=', 'rm'),
                ('notebook.product_type', '=', typification.product_type.id),
                ('notebook.matrix', '=', typification.matrix.id),
                ('analysis', '=', typification.analysis.id),
                ('method', '=', typification.method.id),
                ('end_date', '=', None),
                ])
            if notebook_lines:
                LimsNotebookLine.write(notebook_lines, {
                    'initial_concentration': unicode(
                        typification.initial_concentration or ''),
                    })


class LimsTypificationAditional(ModelSQL):
    'Typification - Additional analysis'
    __name__ = 'lims.typification-analysis'

    typification = fields.Many2One('lims.typification', 'Typification',
        ondelete='CASCADE', select=True, required=True)
    analysis = fields.Many2One('lims.analysis', 'Analysis',
        ondelete='CASCADE', select=True, required=True)


class LimsTypificationReadOnly(ModelSQL, ModelView):
    'Typification'
    __name__ = 'lims.typification.readonly'

    product_type = fields.Many2One('lims.product.type', 'Product type',
        readonly=True)
    matrix = fields.Many2One('lims.matrix', 'Matrix', readonly=True)
    analysis = fields.Many2One('lims.analysis', 'Analysis', readonly=True)
    method = fields.Many2One('lims.lab.method', 'Method', readonly=True)

    @classmethod
    def __setup__(cls):
        super(LimsTypificationReadOnly, cls).__setup__()
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


class LimsCalculatedTypification(ModelSQL):
    'Calculated Typification'
    __name__ = 'lims.typification.calculated'
    _rec_name = 'analysis'

    product_type = fields.Many2One('lims.product.type', 'Product type',
        required=True, select=True)
    matrix = fields.Many2One('lims.matrix', 'Matrix', required=True,
        select=True)
    analysis = fields.Many2One('lims.analysis', 'Analysis', required=True,
        ondelete='CASCADE', select=True)

    @classmethod
    def __register__(cls, module_name):
        super(LimsCalculatedTypification, cls).__register__(module_name)
        if cls.search_count([]) == 0:
            cls.populate_typification_calculated()

    @classmethod
    def populate_typification_calculated(cls):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsAnalysis = pool.get('lims.analysis')
        LimsTypification = pool.get('lims.typification')

        cursor.execute('SELECT DISTINCT(product_type, matrix) '
            'FROM "' + LimsTypification._table + '" '
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
                    'FROM "' + LimsTypification._table + '" '
                    'WHERE product_type = %s '
                        'AND matrix = %s '
                        'AND valid',
                    (product_type, matrix))
                typified_analysis = [a[0] for a in cursor.fetchall()]
                typified_analysis_ids = ', '.join(str(a) for a in
                    typified_analysis)

                cursor.execute('SELECT id '
                    'FROM "' + LimsAnalysis._table + '" '
                    'WHERE type IN (\'set\', \'group\') '
                        'AND state = \'active\'')
                sets_groups_ids = [x[0] for x in cursor.fetchall()]
                if sets_groups_ids:
                    for set_group_id in sets_groups_ids:
                        typified = True

                        ia = LimsAnalysis.get_included_analysis_analysis(
                            set_group_id)
                        if not ia:
                            continue
                        included_ids = ', '.join(str(a) for a in ia)

                        cursor.execute('SELECT id '
                            'FROM "' + LimsAnalysis._table + '" '
                            'WHERE id IN (' + included_ids + ') '
                                'AND id NOT IN (' + typified_analysis_ids
                                + ')')
                        if cursor.fetchone():
                            typified = False

                        if typified:
                            typification_create = [{
                                'product_type': product_type,
                                'matrix': matrix,
                                'analysis': set_group_id,
                                }]
                            cls.create(typification_create)


class LimsCalculatedTypificationReadOnly(ModelSQL, ModelView):
    'Calculated Typification'
    __name__ = 'lims.typification.calculated.readonly'

    product_type = fields.Many2One('lims.product.type', 'Product type',
        readonly=True)
    matrix = fields.Many2One('lims.matrix', 'Matrix', readonly=True)
    analysis = fields.Many2One('lims.analysis', 'Analysis', readonly=True)

    @classmethod
    def __setup__(cls):
        super(LimsCalculatedTypificationReadOnly, cls).__setup__()
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


class LimsProductType(ModelSQL, ModelView):
    'Product Type'
    __name__ = 'lims.product.type'
    _rec_name = 'description'

    code = fields.Char('Code', required=True)
    description = fields.Char('Description', required=True)
    restricted_entry = fields.Boolean('Restricted entry')

    @classmethod
    def __setup__(cls):
        super(LimsProductType, cls).__setup__()
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


class LimsMatrix(ModelSQL, ModelView):
    'Matrix'
    __name__ = 'lims.matrix'
    _rec_name = 'description'

    code = fields.Char('Code', required=True)
    description = fields.Char('Description', required=True)
    restricted_entry = fields.Boolean('Restricted entry')

    @classmethod
    def __setup__(cls):
        super(LimsMatrix, cls).__setup__()
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


class LimsPackagingType(ModelSQL, ModelView):
    'Packaging Type'
    __name__ = 'lims.packaging.type'
    _rec_name = 'description'

    code = fields.Char('Code', required=True)
    description = fields.Char('Description', required=True, translate=True)

    @classmethod
    def __setup__(cls):
        super(LimsPackagingType, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code),
                'Packaging type code must be unique'),
            ]

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


class LimsFormula(ModelSQL, ModelView):
    'Formula'
    __name__ = 'lims.formula'

    name = fields.Char('Name', required=True)
    formula = fields.Char('Formula', required=True)
    variables = fields.One2Many('lims.formula.variable', 'formula',
        'Variables', required=True)


class LimsFormulaVariable(ModelSQL, ModelView):
    'Formula Variable'
    __name__ = 'lims.formula.variable'

    formula = fields.Many2One('lims.formula', 'Formula', required=True,
        ondelete='CASCADE', select=True)
    number = fields.Char('Number', required=True)
    description = fields.Char('Description', required=True)
    fraction_type = fields.Many2One('lims.fraction.type', 'Fraction type')
    constant = fields.Char('Constant')


class LimsAnalysis(Workflow, ModelSQL, ModelView):
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

    @classmethod
    def __setup__(cls):
        super(LimsAnalysis, cls).__setup__()
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
        LimsAnalysis = Pool().get('lims.analysis')
        return LimsAnalysis.get_included_analysis(self.id)

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
        LimsAnalysisIncluded = Pool().get('lims.analysis.included')

        childs = []
        cursor.execute('SELECT included_analysis '
            'FROM "' + LimsAnalysisIncluded._table + '" '
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
        LimsAnalysisIncluded = pool.get('lims.analysis.included')
        LimsAnalysis = pool.get('lims.analysis')

        childs = []
        cursor.execute('SELECT ia.included_analysis, a.type '
            'FROM "' + LimsAnalysisIncluded._table + '" ia '
                'INNER JOIN "' + LimsAnalysis._table + '" a '
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
        LimsAnalysisIncluded = pool.get('lims.analysis.included')
        LimsAnalysis = pool.get('lims.analysis')

        parents = []
        cursor.execute('SELECT ia.analysis '
            'FROM "' + LimsAnalysisIncluded._table + '" ia '
                'INNER JOIN "' + LimsAnalysis._table + '" a '
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
        super(LimsAnalysis, cls).validate(analysis)
        for a in analysis:
            a.check_description()
            a.check_set()
            a.check_end_date()

    def check_description(self):
        if not self.end_date:
            analysis = self.search([
                ('description', '=', self.description),
                ('type', '=', self.type),
                ('end_date', '=', None),
                ('id', '!=', self.id),
                ])
            if analysis:
                self.raise_user_error('description_uniq')

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
        super(LimsAnalysis, cls).write(*args)

    @classmethod
    def check_laboratory_change(cls, analysis, laboratories):
        LimsAnalysisIncluded = Pool().get('lims.analysis.included')

        for a in analysis:
            if a.type == 'analysis':
                for operation in laboratories:
                    if operation[0] == 'unlink':
                        for laboratory in operation[1]:
                            parent = LimsAnalysisIncluded.search([
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

    @classmethod
    def create_typification_calculated(cls, analysis):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsAnalysis = pool.get('lims.analysis')
        LimsTypification = pool.get('lims.typification')
        LimsCalculatedTypification = pool.get('lims.typification.calculated')

        for included in analysis:
            if included.type == 'analysis':
                continue
            sets_groups_ids = [included.id]
            sets_groups_ids.extend(LimsAnalysis.get_parents_analysis(
                included.id))
            for set_group_id in sets_groups_ids:

                ia = LimsAnalysis.get_included_analysis_analysis(
                    set_group_id)
                if not ia:
                    continue
                included_ids = ', '.join(str(a) for a in ia)

                cursor.execute('SELECT DISTINCT(product_type, matrix) '
                    'FROM "' + LimsTypification._table + '" '
                    'WHERE valid '
                        'AND analysis IN (' + included_ids + ')')
                typifications = cursor.fetchall()
                if not typifications:
                    continue

                for typification in typifications:

                    product_type = int(typification[0].split(',')[0][1:])
                    matrix = int(typification[0].split(',')[1][:-1])
                    cursor.execute('SELECT DISTINCT(analysis) '
                        'FROM "' + LimsTypification._table + '" '
                        'WHERE product_type = %s '
                            'AND matrix = %s '
                            'AND valid',
                        (product_type, matrix))
                    typified_analysis = [a[0] for a in cursor.fetchall()]
                    typified_analysis_ids = ', '.join(str(a) for a in
                        typified_analysis)

                    cursor.execute('SELECT id '
                        'FROM "' + LimsAnalysis._table + '" '
                        'WHERE id IN (' + included_ids + ') '
                            'AND id NOT IN (' + typified_analysis_ids
                            + ')')
                    if cursor.fetchone():
                        typified = False
                    else:
                        typified = True

                    if typified:
                        t_set_group = LimsCalculatedTypification.search([
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
                            LimsCalculatedTypification.create(
                                typification_create)
                    else:
                        t_set_group = LimsCalculatedTypification.search([
                            ('product_type', '=', product_type),
                            ('matrix', '=', matrix),
                            ('analysis', '=', set_group_id),
                            ])
                        if t_set_group:
                            LimsCalculatedTypification.delete(t_set_group)

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
        LimsTypification = pool.get('lims.typification')
        LimsCalculatedTypification = pool.get('lims.typification.calculated')

        analysis_ids = []
        sets_groups_ids = []
        for a in analysis:
            if a.type == 'analysis':
                analysis_ids.append(a.id)
            else:
                sets_groups_ids.append(a.id)
        if analysis_ids:
            typifications = LimsTypification.search([
                ('analysis', 'in', analysis_ids),
                ])
            if typifications:
                LimsTypification.write(typifications, {'valid': False})
        if sets_groups_ids:
            typifications = LimsCalculatedTypification.search([
                ('analysis', 'in', sets_groups_ids),
                ])
            if typifications:
                LimsCalculatedTypification.delete(typifications)

    @classmethod
    def delete_included_analysis(cls, analysis):
        LimsAnalysisIncluded = Pool().get('lims.analysis.included')
        analysis_ids = [a.id for a in analysis]
        if analysis_ids:
            included_delete = LimsAnalysisIncluded.search([
                ('included_analysis', 'in', analysis_ids),
                ])
            if included_delete:
                LimsAnalysisIncluded.delete(included_delete)

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
        LimsTypification = pool.get('lims.typification')
        LimsCalculatedTypification = pool.get('lims.typification.calculated')

        if analysis.type == 'analysis':
            typified_service = LimsTypification.search([
                ('analysis', '=', analysis.id),
                ('product_type', '=', product_type.id),
                ('matrix', '=', matrix.id),
                ('valid', '=', True),
                ])
            if typified_service:
                return True
        else:
            typified_service = LimsCalculatedTypification.search([
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
        return super(LimsAnalysis, cls).copy(analysis, default=current_default)


class LimsAnalysisIncluded(ModelSQL, ModelView):
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
        super(LimsAnalysisIncluded, cls).__setup__()
        cls._error_messages.update({
            'duplicated_analysis': 'The analysis "%s" is already included',
            'not_set_laboratory': 'No Laboratory loaded for the Set',
            })

    @classmethod
    def validate(cls, included_analysis):
        super(LimsAnalysisIncluded, cls).validate(included_analysis)
        for analysis in included_analysis:
            analysis.check_duplicated_analysis()

    def check_duplicated_analysis(self):
        LimsAnalysis = Pool().get('lims.analysis')

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
                    analysis_ids.extend(LimsAnalysis.get_included_analysis(
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
        LimsAnalysisIncluded = Pool().get('lims.analysis.included')
        context = Transaction().context
        analysis_id = context.get('analysis', None)
        analysis_type = context.get('type', None)
        laboratories = context.get('laboratory_domain', [])
        return LimsAnalysisIncluded.get_analysis_domain(analysis_id,
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
        LimsAnalysisIncluded = pool.get('lims.analysis.included')
        LimsAnalysis = pool.get('lims.analysis')
        LimsAnalysisLaboratory = pool.get('lims.analysis-laboratory')

        if not analysis_type:
            return []

        if analysis_type == 'set':
            if len(laboratories) != 1:
                LimsAnalysisIncluded.raise_user_error('not_set_laboratory')
                #return []
            set_laboratory_id = laboratories[0]
            not_parent_clause = ''
            if analysis_id:
                not_parent_clause = 'AND al.analysis != ' + str(analysis_id)

            cursor.execute('SELECT DISTINCT(al.analysis) '
                'FROM "' + LimsAnalysisLaboratory._table + '" al '
                    'INNER JOIN "' + LimsAnalysis._table + '" a '
                    'ON a.id = al.analysis '
                'WHERE al.laboratory = %s '
                    'AND a.state = \'active\' '
                    'AND a.type = \'analysis\' '
                    'AND a.end_date IS NULL '
                    + not_parent_clause,
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
                'FROM "' + LimsAnalysis._table + '" '
                'WHERE state = \'active\' '
                    'AND type != \'group\' '
                    'AND end_date IS NULL '
                    + not_parent_clause)
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
        included_analysis = super(LimsAnalysisIncluded, cls).create(vlist)
        cls.create_typification_calculated(included_analysis)
        return included_analysis

    @classmethod
    def create_typification_calculated(cls, included_analysis):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsAnalysis = pool.get('lims.analysis')
        LimsTypification = pool.get('lims.typification')
        LimsCalculatedTypification = pool.get('lims.typification.calculated')

        for included in included_analysis:
            if included.analysis.state != 'active':
                continue
            sets_groups_ids = [included.analysis.id]
            sets_groups_ids.extend(LimsAnalysis.get_parents_analysis(
                included.analysis.id))
            for set_group_id in sets_groups_ids:

                ia = LimsAnalysis.get_included_analysis_analysis(
                    set_group_id)
                if not ia:
                    continue
                included_ids = ', '.join(str(a) for a in ia)

                cursor.execute('SELECT DISTINCT(product_type, matrix) '
                    'FROM "' + LimsTypification._table + '" '
                    'WHERE valid '
                        'AND analysis IN (' + included_ids + ')')
                typifications = cursor.fetchall()
                if not typifications:
                    continue

                for typification in typifications:

                    product_type = int(typification[0].split(',')[0][1:])
                    matrix = int(typification[0].split(',')[1][:-1])
                    cursor.execute('SELECT DISTINCT(analysis) '
                        'FROM "' + LimsTypification._table + '" '
                        'WHERE product_type = %s '
                            'AND matrix = %s '
                            'AND valid',
                        (product_type, matrix))
                    typified_analysis = [a[0] for a in cursor.fetchall()]
                    typified_analysis_ids = ', '.join(str(a) for a in
                        typified_analysis)

                    cursor.execute('SELECT id '
                        'FROM "' + LimsAnalysis._table + '" '
                        'WHERE id IN (' + included_ids + ') '
                            'AND id NOT IN (' + typified_analysis_ids
                            + ')')
                    if cursor.fetchone():
                        typified = False
                    else:
                        typified = True

                    if typified:
                        t_set_group = LimsCalculatedTypification.search([
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
                            LimsCalculatedTypification.create(
                                typification_create)
                    else:
                        t_set_group = LimsCalculatedTypification.search([
                            ('product_type', '=', product_type),
                            ('matrix', '=', matrix),
                            ('analysis', '=', set_group_id),
                            ])
                        if t_set_group:
                            LimsCalculatedTypification.delete(t_set_group)

        return included_analysis

    @classmethod
    def delete(cls, included_analysis):
        cls.delete_typification_calculated(included_analysis)
        super(LimsAnalysisIncluded, cls).delete(included_analysis)

    @classmethod
    def delete_typification_calculated(cls, included_analysis):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsAnalysis = pool.get('lims.analysis')
        LimsTypification = pool.get('lims.typification')
        LimsCalculatedTypification = pool.get('lims.typification.calculated')

        for included in included_analysis:
            if included.analysis.state != 'active':
                continue
            if included.included_analysis.type == 'analysis':
                deleted_analysis = [included.included_analysis.id]
            else:
                deleted_analysis = (
                    LimsAnalysis.get_included_analysis_analysis(
                        included.included_analysis.id))

            sets_groups_ids = [included.analysis.id]
            sets_groups_ids.extend(LimsAnalysis.get_parents_analysis(
                included.analysis.id))
            for set_group_id in sets_groups_ids:
                typified = True

                ia = LimsAnalysis.get_included_analysis_analysis(
                    set_group_id)
                if deleted_analysis:
                    for da in deleted_analysis:
                        if da in ia:
                            ia.remove(da)
                if not ia:
                    continue
                included_ids = ', '.join(str(a) for a in ia)

                cursor.execute('SELECT DISTINCT(product_type, matrix) '
                    'FROM "' + LimsTypification._table + '" '
                    'WHERE valid '
                        'AND analysis IN (' + included_ids + ')')
                typifications = cursor.fetchall()
                if not typifications:
                    continue

                for typification in typifications:

                    product_type = int(typification[0].split(',')[0][1:])
                    matrix = int(typification[0].split(',')[1][:-1])
                    cursor.execute('SELECT DISTINCT(analysis) '
                        'FROM "' + LimsTypification._table + '" '
                        'WHERE product_type = %s '
                            'AND matrix = %s '
                            'AND valid',
                        (product_type, matrix))
                    typified_analysis = [a[0] for a in cursor.fetchall()]
                    typified_analysis_ids = ', '.join(str(a) for a in
                        typified_analysis)

                    cursor.execute('SELECT id '
                        'FROM "' + LimsAnalysis._table + '" '
                        'WHERE id IN (' + included_ids + ') '
                            'AND id NOT IN (' + typified_analysis_ids
                            + ')')
                    if cursor.fetchone():
                        typified = False
                    else:
                        typified = True

                    if typified:
                        t_set_group = LimsCalculatedTypification.search([
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
                            LimsCalculatedTypification.create(
                                typification_create)
                    else:
                        t_set_group = LimsCalculatedTypification.search([
                            ('product_type', '=', product_type),
                            ('matrix', '=', matrix),
                            ('analysis', '=', set_group_id),
                            ])
                        if t_set_group:
                            LimsCalculatedTypification.delete(t_set_group)

    @classmethod
    def search_rec_name(cls, name, clause):
        return ['OR',
            ('included_analysis.code',) + tuple(clause[1:]),
            ('included_analysis.description',) + tuple(clause[1:]),
            ]


class LimsAnalysisLaboratory(ModelSQL, ModelView):
    'Analysis - Laboratory'
    __name__ = 'lims.analysis-laboratory'

    analysis = fields.Many2One('lims.analysis', 'Analysis',
        ondelete='CASCADE', select=True, required=True)
    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        ondelete='CASCADE', select=True, required=True)
    department = fields.Many2One('company.department', 'Department',
        states={'readonly': ~Equal(Eval('context', {}).get('type', ''),
            'analysis')})


class LimsAnalysisLabMethod(ModelSQL):
    'Analysis - Laboratory Method'
    __name__ = 'lims.analysis-lab.method'

    analysis = fields.Many2One('lims.analysis', 'Analysis',
        ondelete='CASCADE', select=True, required=True)
    method = fields.Many2One('lims.lab.method', 'Method',
        ondelete='CASCADE', select=True, required=True)

    @classmethod
    def __setup__(cls):
        super(LimsAnalysisLabMethod, cls).__setup__()
        cls._error_messages.update({
            'typificated_method': ('You can not delete method "%s" because '
                'is typificated'),
            })

    @classmethod
    def delete(cls, methods):
        cls.check_delete(methods)
        super(LimsAnalysisLabMethod, cls).delete(methods)

    @classmethod
    def check_delete(cls, methods):
        LimsTypification = Pool().get('lims.typification')
        for method in methods:
            typifications = LimsTypification.search_count([
                ('analysis', '=', method.analysis.id),
                ('method', '=', method.method.id),
                ('valid', '=', True),
                ])
            if typifications != 0:
                cls.raise_user_error('typificated_method',
                    (method.method.code,))


class LimsAnalysisDevice(ModelSQL, ModelView):
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
        super(LimsAnalysisDevice, cls).__setup__()
        cls._error_messages.update({
            'default_device': ('There is already a default device for this'
            ' analysis on this laboratory'),
            })

    @staticmethod
    def default_by_default():
        return True

    @classmethod
    def validate(cls, devices):
        super(LimsAnalysisDevice, cls).validate(devices)
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


class LimsFractionType(ModelSQL, ModelView):
    'Fraction Type'
    __name__ = 'lims.fraction.type'
    _rec_name = 'description'

    code = fields.Char('Code', required=True)
    description = fields.Char('Description', required=True)
    max_storage_time = fields.Integer('Maximum storage time (in months)')
    requalify = fields.Boolean('Requalify')
    control_charts = fields.Boolean('Available for Control Charts')
    report = fields.Boolean('Available for Results Report')

    @classmethod
    def __setup__(cls):
        super(LimsFractionType, cls).__setup__()
        t = cls.__table__()
        cls._order.insert(0, ('code', 'ASC'))
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code),
                'Fraction type code must be unique'),
            ]

    @staticmethod
    def default_requalify():
        return False

    @staticmethod
    def default_control_charts():
        return False

    @staticmethod
    def default_report():
        return True

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


class LimsCertificationType(ModelSQL, ModelView):
    'Certification Type'
    __name__ = 'lims.certification.type'
    _rec_name = 'description'

    code = fields.Char('Code', required=True)
    description = fields.Char('Description', required=True)
    report = fields.Boolean('Report')

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


class LimsTechnicalScope(ModelSQL, ModelView):
    'Technical Scope'
    __name__ = 'lims.technical.scope'
    _rec_name = 'party'

    party = fields.Many2One('party.party', 'Party', required=True)
    certification_type = fields.Many2One('lims.certification.type',
        'Certification type')
    versions = fields.One2Many('lims.technical.scope.version',
        'technical_scope', 'Versions')

    def get_rec_name(self, name):
        if self.party:
            return self.party.rec_name

    @classmethod
    def search_rec_name(cls, name, clause):
        return [('party',) + tuple(clause[1:])]


class LimsTechnicalScopeVersion(ModelSQL, ModelView):
    'Technical Scope Version'
    __name__ = 'lims.technical.scope.version'
    _rec_name = 'number'

    technical_scope = fields.Many2One('lims.technical.scope',
        'Technical scope', required=True)
    number = fields.Char('Number', required=True)
    date = fields.Date('Date', required=True)
    expiration_date = fields.Date('Expiration date')
    version_lines = fields.Many2Many('lims.technical.scope.version.line',
        'version', 'typification', 'Typifications')
    valid = fields.Boolean('Active')

    @classmethod
    def __setup__(cls):
        super(LimsTechnicalScopeVersion, cls).__setup__()
        cls._error_messages.update({
            'active_version': ('Only one version can be active for each '
                'technical scope'),
            })
        cls._buttons.update({
            'open_typifications': {},
            'add_typifications': {
                'invisible': ~Eval('valid'),
                },
            'remove_typifications': {
                'invisible': ~Eval('valid'),
                },
            })

    @staticmethod
    def default_valid():
        return True

    @classmethod
    def validate(cls, versions):
        super(LimsTechnicalScopeVersion, cls).validate(versions)
        for version in versions:
            version.check_active()

    def check_active(self):
        if self.valid:
            versions = self.search([
                    ('technical_scope', '=', self.technical_scope.id),
                    ('valid', '=', True),
                    ('id', '!=', self.id),
                    ])
            if versions:
                self.raise_user_error('active_version')

    @classmethod
    @ModelView.button_action('lims.act_open_typifications')
    def open_typifications(cls, versions):
        pass

    @classmethod
    @ModelView.button_action('lims.act_add_typifications')
    def add_typifications(cls, versions):
        pass

    @classmethod
    @ModelView.button_action('lims.act_remove_typifications')
    def remove_typifications(cls, versions):
        pass


class LimsTechnicalScopeVersionLine(ModelSQL):
    'Technical Scope Version Line'
    __name__ = 'lims.technical.scope.version.line'

    version = fields.Many2One('lims.technical.scope.version',
        'Technical scope version', ondelete='CASCADE', select=True,
        required=True)
    typification = fields.Many2One('lims.typification', 'Typification',
        ondelete='CASCADE', select=True, required=True)


class LimsService(ModelSQL, ModelView):
    'Service'
    __name__ = 'lims.service'
    _rec_name = 'number'

    number = fields.Char('Number', select=True, readonly=True)
    create_date2 = fields.Function(fields.DateTime('Create Date'),
       'get_create_date2', searcher='search_create_date2')
    fraction = fields.Many2One('lims.fraction', 'Fraction', required=True,
        ondelete='CASCADE', select=True, depends=['number'],
        states={'readonly': Or(Bool(Eval('number')),
            Bool(Eval('context', {}).get('readonly', True))),
            })
    fraction_view = fields.Function(fields.Many2One('lims.fraction',
        'Fraction', states={'invisible': Not(Bool(Eval('_parent_fraction')))}),
        'on_change_with_fraction_view')
    sample = fields.Function(fields.Many2One('lims.sample', 'Sample'),
        'get_fraction_field',
        searcher='search_fraction_field')
    entry = fields.Function(fields.Many2One('lims.entry', 'Entry'),
        'get_fraction_field',
        searcher='search_fraction_field')
    party = fields.Function(fields.Many2One('party.party', 'Party'),
        'get_fraction_field',
        searcher='search_fraction_field')
    analysis = fields.Many2One('lims.analysis', 'Analysis/Set/Group',
        required=True, depends=['analysis_domain'],
        domain=[('id', 'in', Eval('analysis_domain'))],
        states={'readonly': Bool(Eval('context', {}).get('readonly', True))})
    analysis_view = fields.Function(fields.Many2One('lims.analysis',
        'Analysis/Set/Group'), 'get_views_field',
        searcher='search_views_field')
    analysis_domain = fields.Function(fields.Many2Many('lims.analysis',
        None, None, 'Analysis domain'),
        'on_change_with_analysis_domain')
    typification_domain = fields.Function(fields.Many2Many(
        'lims.typification', None, None, 'Typification domain'),
        'on_change_with_typification_domain')
    analysis_type = fields.Function(fields.Selection([
        ('analysis', 'Analysis'),
        ('set', 'Set'),
        ('group', 'Group'),
        ], 'Type', sort=False),
        'on_change_with_analysis_type', searcher='search_analysis_field')
    urgent = fields.Boolean('Urgent',
        states={'readonly': Bool(Eval('context', {}).get('readonly', True))})
    priority = fields.Integer('Priority',
        states={'readonly': Bool(Eval('context', {}).get('readonly', True))})
    report_date = fields.Date('Date agreed for result')
    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        domain=[('id', 'in', Eval('laboratory_domain'))],
        states={
            'required': Bool(Eval('laboratory_domain')),
            'readonly': Bool(Eval('context', {}).get('readonly', True)),
            },
        depends=['laboratory_domain'])
    laboratory_view = fields.Function(fields.Many2One('lims.laboratory',
        'Laboratory'), 'get_views_field')
    laboratory_domain = fields.Function(fields.Many2Many('lims.laboratory',
        None, None, 'Laboratory domain'),
        'on_change_with_laboratory_domain')
    method = fields.Many2One('lims.lab.method', 'Method',
        domain=[('id', 'in', Eval('method_domain'))],
        states={
            'required': Bool(Eval('method_domain')),
            'readonly': Bool(Eval('context', {}).get('readonly', True)),
            },
        depends=['method_domain'])
    method_view = fields.Function(fields.Many2One('lims.lab.method',
        'Method'), 'get_views_field')
    method_domain = fields.Function(fields.Many2Many('lims.lab.method',
        None, None, 'Method domain'), 'on_change_with_method_domain')
    device = fields.Many2One('lims.lab.device', 'Device',
        domain=[('id', 'in', Eval('device_domain'))],
        states={
            'required': Bool(Eval('device_domain')),
            'readonly': Bool(Eval('context', {}).get('readonly', True)),
            },
        depends=['device_domain'])
    device_view = fields.Function(fields.Many2One('lims.lab.device',
        'Device'), 'get_views_field')
    device_domain = fields.Function(fields.Many2Many('lims.lab.device',
        None, None, 'Device domain'), 'on_change_with_device_domain')
    comments = fields.Text('Comments',
        states={'readonly': Bool(Eval('context', {}).get('readonly', True))})
    analysis_detail = fields.One2Many('lims.entry.detail.analysis',
        'service', 'Analysis detail')
    confirmed = fields.Function(fields.Boolean('Confirmed'), 'get_confirmed',
        searcher='search_confirmed')
    confirmation_date = fields.Date('Confirmation date', readonly=True)
    divide = fields.Boolean('Divide')
    has_results_report = fields.Function(fields.Boolean('Results Report'),
        'get_has_results_report')
    manage_service_available = fields.Function(fields.Boolean(
        'Available for Manage services'), 'get_manage_service_available')

    @classmethod
    def __setup__(cls):
        super(LimsService, cls).__setup__()
        cls._order.insert(0, ('number', 'DESC'))
        cls._error_messages.update({
            'no_service_sequence': ('There is no service sequence for '
                'the work year "%s".'),
            'delete_service': ('You can not delete service "%s" because '
                'its fraction is confirmed'),
            'duplicated_analysis': ('The analysis "%(analysis)s" is assigned '
                'more than once to the fraction "%(fraction)s"'),
            })

    @staticmethod
    def default_urgent():
        return False

    @staticmethod
    def default_priority():
        return 0

    @staticmethod
    def default_divide():
        return False

    @classmethod
    def validate(cls, services):
        super(LimsService, cls).validate(services)
        for service in services:
            service.check_duplicated_analysis()

    def check_duplicated_analysis(self):
        LimsAnalysis = Pool().get('lims.analysis')

        fraction_id = self.fraction.id
        services = self.search([
            ('fraction', '=', fraction_id),
            ('id', '!=', self.id)
            ])
        if services:
            analysis_ids = []
            for service in services:
                if service.analysis:
                    analysis_ids.append(service.analysis.id)
                    analysis_ids.extend(LimsAnalysis.get_included_analysis(
                        service.analysis.id))

            new_analysis_ids = [self.analysis.id]
            new_analysis_ids.extend(LimsAnalysis.get_included_analysis(
                self.analysis.id))
            for a_id in new_analysis_ids:
                if a_id in analysis_ids:
                    analysis = LimsAnalysis(a_id)
                    self.raise_user_error('duplicated_analysis', {
                        'analysis': analysis.rec_name,
                        'fraction': self.fraction.rec_name,
                        })

    @classmethod
    def create(cls, vlist):
        pool = Pool()
        LimsLabWorkYear = pool.get('lims.lab.workyear')
        Sequence = pool.get('ir.sequence')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        workyear_id = LimsLabWorkYear.find()
        workyear = LimsLabWorkYear(workyear_id)
        sequence = workyear.get_sequence('service')
        if not sequence:
            cls.raise_user_error('no_service_sequence',
                (workyear.rec_name,))

        vlist = [x.copy() for x in vlist]
        for values in vlist:
            values['number'] = Sequence.get_id(sequence.id)
        services = super(LimsService, cls).create(vlist)

        if not Transaction().context.get('copying', False):
            cls.update_analysis_detail(services)
            aditional_services = cls.create_aditional_services(services)

            # Aditional processing for Manage Services
            if aditional_services and Transaction().context.get(
                    'manage_service', False):
                cls.copy_analysis_comments(aditional_services)
                cls.set_confirmation_date(aditional_services)
                analysis_detail = EntryDetailAnalysis.search([
                    ('service', 'in', [s.id for s in aditional_services])])
                if analysis_detail:
                    fraction = analysis_detail[0].fraction
                    EntryDetailAnalysis.create_notebook_lines(analysis_detail,
                        fraction)
                    # from lims_planification
                    if 'trytond.modules.lims_planification' in sys.modules:
                        EntryDetailAnalysis.write(analysis_detail, {
                            'state': 'unplanned',
                            })
                # from lims_account_invoice
                if 'trytond.modules.lims_account_invoice' in sys.modules:
                    for aditional_service in aditional_services:
                        aditional_service.create_invoice_line('out')

        return services

    @classmethod
    def write(cls, *args):
        super(LimsService, cls).write(*args)
        actions = iter(args)
        for services, vals in zip(actions, actions):
            change_detail = False
            for field in ('analysis', 'laboratory', 'method', 'device'):
                if vals.get(field):
                    change_detail = True
                    break
            if change_detail:
                cls.update_analysis_detail(services)

    @classmethod
    def delete(cls, services):
        if Transaction().user != 0:
            cls.check_delete(services)
        super(LimsService, cls).delete(services)

    @classmethod
    def check_delete(cls, services):
        for service in services:
            if service.fraction and service.fraction.confirmed:
                cls.raise_user_error('delete_service', (service.rec_name,))

    @staticmethod
    def update_analysis_detail(services):
        pool = Pool()
        LimsService = pool.get('lims.service')
        LimsEntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        for service in services:
            to_delete = LimsEntryDetailAnalysis.search([
                ('service', '=', service.id),
                ])
            if to_delete:
                with Transaction().set_user(0, set_context=True):
                    LimsEntryDetailAnalysis.delete(to_delete)

            if service.analysis.behavior == 'additional':
                continue

            to_create = []
            service_context = {
                'product_type': service.fraction.product_type.id,
                'matrix': service.fraction.matrix.id,
                }
            analysis_data = []
            if service.analysis.type == 'analysis':
                laboratory_id = service.laboratory.id
                method_id = service.method.id if service.method else None
                device_id = service.device.id if service.device else None

                analysis_data.append({
                    'id': service.analysis.id,
                    'origin': service.analysis.code,
                    'laboratory': laboratory_id,
                    'method': method_id,
                    'device': device_id,
                    })
            else:
                analysis_data.extend(LimsService._get_included_analysis(
                    service.analysis, service.analysis.code,
                    service_context))

            if analysis_data:
                for analysis in analysis_data:
                    values = {}
                    values['service'] = service.id
                    values['analysis'] = analysis['id']
                    values['analysis_origin'] = analysis['origin']
                    values['laboratory'] = analysis['laboratory']
                    values['method'] = analysis['method']
                    values['device'] = analysis['device']
                    to_create.append(values)

            if to_create:
                with Transaction().set_user(0, set_context=True):
                    LimsEntryDetailAnalysis.create(to_create)

    @staticmethod
    def _get_included_analysis(analysis, analysis_origin='',
            service_context=None):
        LimsTypification = Pool().get('lims.typification')

        childs = []
        if analysis.included_analysis:
            for included in analysis.included_analysis:
                if (analysis.type == 'set' and
                        included.included_analysis.type == 'analysis'):
                    origin = analysis_origin
                else:
                    origin = (analysis_origin + ' > ' +
                        included.included_analysis.code)
                if included.included_analysis.type == 'analysis':

                    laboratory_id = included.laboratory.id

                    typifications = LimsTypification.search([
                        ('product_type', '=', service_context['product_type']),
                        ('matrix', '=', service_context['matrix']),
                        ('analysis', '=', included.included_analysis),
                        ('by_default', '=', True),
                        ('valid', '=', True),
                        ])
                    method_id = (typifications[0].method.id if typifications
                        else None)

                    device_id = None
                    if included.included_analysis.devices:
                        for d in included.included_analysis.devices:
                            if (d.laboratory.id == laboratory_id
                                    and d.by_default is True):
                                device_id = d.device.id

                    childs.append({
                        'id': included.included_analysis.id,
                        'origin': origin,
                        'laboratory': laboratory_id,
                        'method': method_id,
                        'device': device_id,
                        })
                childs.extend(LimsService._get_included_analysis(
                    included.included_analysis, origin, service_context))
        return childs

    @staticmethod
    def create_aditional_services(services):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsEntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        LimsTypification = pool.get('lims.typification')
        LimsAnalysisLaboratory = pool.get('lims.analysis-laboratory')
        LimsAnalysisDevice = pool.get('lims.analysis.device')
        LimsService = pool.get('lims.service')

        aditional_services = {}
        for service in services:
            entry_details = LimsEntryDetailAnalysis.search([
                ('service', '=', service.id),
                ])
            for detail in entry_details:
                typifications = LimsTypification.search([
                    ('product_type', '=', service.fraction.product_type.id),
                    ('matrix', '=', service.fraction.matrix.id),
                    ('analysis', '=', detail.analysis.id),
                    ('method', '=', detail.method),
                    ('valid', '=', True),
                    ])
                if not typifications:
                    continue
                typification = typifications[0]

                if typification.additional:
                    if service.fraction.id not in aditional_services:
                        aditional_services[service.fraction.id] = {}
                    if (typification.additional.id not in
                            aditional_services[service.fraction.id]):

                        aditional_services[service.fraction.id][
                                typification.additional.id] = {
                            'laboratory': None,
                            'method': None,
                            'device': None,
                            }

                if typification.additionals:
                    if service.fraction.id not in aditional_services:
                        aditional_services[service.fraction.id] = {}
                    for additional in typification.additionals:
                        if (additional.id not in
                                aditional_services[service.fraction.id]):

                            cursor.execute('SELECT laboratory '
                                'FROM "' + LimsAnalysisLaboratory._table + '" '
                                'WHERE analysis = %s', (additional.id,))
                            res = cursor.fetchone()
                            laboratory_id = res and res[0] or None

                            cursor.execute('SELECT method '
                                'FROM "' + LimsTypification._table + '" '
                                'WHERE product_type = %s '
                                    'AND matrix = %s '
                                    'AND analysis = %s '
                                    'AND valid IS TRUE '
                                    'AND by_default IS TRUE',
                                (service.fraction.product_type.id,
                                    service.fraction.matrix.id, additional.id))
                            res = cursor.fetchone()
                            method_id = res and res[0] or None

                            cursor.execute('SELECT device '
                                'FROM "' + LimsAnalysisDevice._table + '" '
                                'WHERE analysis = %s '
                                    'AND laboratory = %s '
                                    'AND by_default IS TRUE',
                                (additional.id, laboratory_id))
                            res = cursor.fetchone()
                            device_id = res and res[0] or None

                            aditional_services[service.fraction.id][
                                    additional.id] = {
                                'laboratory': laboratory_id,
                                'method': method_id,
                                'device': device_id,
                                }

        if aditional_services:
            services_default = []
            for fraction_id, analysis in aditional_services.iteritems():
                for analysis_id, service_data in analysis.iteritems():
                    if not LimsService.search([
                            ('fraction', '=', fraction_id),
                            ('analysis', '=', analysis_id),
                            ]):
                        services_default.append({
                            'fraction': fraction_id,
                            'analysis': analysis_id,
                            'laboratory': service_data['laboratory'],
                            'method': service_data['method'],
                            'device': service_data['device'],
                            })
            return LimsService.create(services_default)

    @classmethod
    def view_attributes(cls):
        return [
            ('//group[@id="invisible_fields"]', 'states', {
                    'invisible': True,
                    }),
            ('/tree', 'colors',
                If(Bool(Eval('has_results_report')), 'blue',
                If(Bool(Eval('confirmed')), 'black', 'red'))),
            ]

    @classmethod
    def copy(cls, services, default=None):
        if default is None:
            default = {}

        new_services = []
        for service in sorted(services, key=lambda x: x.number):
            current_default = default.copy()
            current_default['confirmation_date'] = None

            with Transaction().set_context(copying=True):
                new_service, = super(LimsService, cls).copy([service],
                    default=current_default)
            new_services.append(new_service)
        return new_services

    @staticmethod
    def copy_analysis_comments(services):
        pool = Pool()
        Fraction = pool.get('lims.fraction')

        comments = {}
        for service in services:
            if service.analysis.comments:
                fraction_id = service.fraction.id
                if fraction_id not in comments:
                    comments[fraction_id] = ''
                if comments[fraction_id]:
                    comments[fraction_id] += '\n'
                comments[fraction_id] += service.analysis.comments
        if comments:
            fractions_to_save = []
            for fraction_id, comment in comments.iteritems():
                fraction = Fraction(fraction_id)
                if fraction.comments:
                    fraction.comments += '\n' + comment
                else:
                    fraction.comments = comment
                fractions_to_save.append(fraction)
            if fractions_to_save:
                Fraction.save(fractions_to_save)

    @staticmethod
    def set_confirmation_date(services, confirmation_date=None):
        pool = Pool()
        Date = pool.get('ir.date')
        LimsService = pool.get('lims.service')
        LimsEntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        if not confirmation_date:
            confirmation_date = Date.today()
        LimsService.write(services, {
            'confirmation_date': confirmation_date,
            })
        analysis_details = LimsEntryDetailAnalysis.search([
            ('service', 'in', [s.id for s in services]),
            ])
        if analysis_details:
            LimsEntryDetailAnalysis.write(analysis_details, {
                'confirmation_date': confirmation_date,
                })

    @fields.depends('analysis', 'fraction', 'typification_domain',
        'laboratory')
    def on_change_analysis(self):
        LimsLaboratory = Pool().get('lims.laboratory')
        laboratory = None
        method = None
        device = None
        if self.analysis:
            laboratories = self.on_change_with_laboratory_domain()
            if len(laboratories) == 1:
                laboratory = laboratories[0]
            methods = self.on_change_with_method_domain()
            if len(methods) == 1:
                method = methods[0]
            devices = self._on_change_with_device_domain(self.analysis,
                LimsLaboratory(laboratory), True)
            if len(devices) == 1:
                device = devices[0]
        self.laboratory = laboratory
        self.method = method
        self.device = device

    @staticmethod
    def default_analysis_domain():
        return Transaction().context.get('analysis_domain', [])

    @fields.depends('fraction')
    def on_change_with_analysis_domain(self, name=None):
        if Transaction().context.get('analysis_domain'):
            return Transaction().context.get('analysis_domain')
        if self.fraction:
            return self.fraction.on_change_with_analysis_domain()
        return []

    @staticmethod
    def default_typification_domain():
        return Transaction().context.get('typification_domain', [])

    @fields.depends('fraction')
    def on_change_with_typification_domain(self, name=None):
        if Transaction().context.get('typification_domain'):
            return Transaction().context.get('typification_domain')
        if self.fraction:
            return self.fraction.on_change_with_typification_domain()
        return []

    @fields.depends('analysis')
    def on_change_with_analysis_type(self, name=None):
        if self.analysis:
            return self.analysis.type
        return ''

    @staticmethod
    def default_fraction_view():
        if (Transaction().context.get('fraction') > 0):
            return Transaction().context.get('fraction')
        return None

    @fields.depends('fraction')
    def on_change_with_fraction_view(self, name=None):
        if self.fraction:
            return self.fraction.id
        return None

    @staticmethod
    def default_sample():
        if (Transaction().context.get('sample') > 0):
            return Transaction().context.get('sample')
        return None

    @fields.depends('fraction')
    def on_change_with_sample(self, name=None):
        if self.fraction:
            result = self.get_fraction_field((self,), ('sample',))
            return result['sample'][self.id]
        return None

    @staticmethod
    def default_entry():
        if (Transaction().context.get('entry') > 0):
            return Transaction().context.get('entry')
        return None

    @fields.depends('fraction')
    def on_change_with_entry(self, name=None):
        if self.fraction:
            result = self.get_fraction_field((self,), ('entry',))
            return result['entry'][self.id]
        return None

    @staticmethod
    def default_party():
        if (Transaction().context.get('party') > 0):
            return Transaction().context.get('party')
        return None

    @fields.depends('fraction')
    def on_change_with_party(self, name=None):
        if self.fraction:
            result = self.get_fraction_field((self,), ('party',))
            return result['party'][self.id]
        return None

    @fields.depends('analysis', 'laboratory')
    def on_change_laboratory(self):
        device = None
        if self.analysis and self.laboratory:
            devices = self._on_change_with_device_domain(self.analysis,
                self.laboratory, True)
            if len(devices) == 1:
                device = devices[0]
        self.device = device

    @fields.depends('analysis')
    def on_change_with_laboratory_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        LimsAnalysisLaboratory = Pool().get('lims.analysis-laboratory')

        if not self.analysis:
            return []

        cursor.execute('SELECT DISTINCT(laboratory) '
            'FROM "' + LimsAnalysisLaboratory._table + '" '
            'WHERE analysis = %s',
            (self.analysis.id,))
        res = cursor.fetchall()
        if not res:
            return []
        return [x[0] for x in res]

    @fields.depends('analysis', 'typification_domain')
    def on_change_with_method_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        LimsTypification = Pool().get('lims.typification')

        if not self.analysis:
            return []

        typification_ids = ', '.join(str(t) for t in
            self.on_change_with_typification_domain())
        if not typification_ids:
            return []
        cursor.execute('SELECT DISTINCT(method) '
            'FROM "' + LimsTypification._table + '" '
            'WHERE id IN (' + typification_ids + ') '
                'AND analysis = %s',
            (self.analysis.id,))
        res = cursor.fetchall()
        if not res:
            return []
        return [x[0] for x in res]

    @fields.depends('analysis', 'laboratory')
    def on_change_with_device_domain(self, name=None):
        return self._on_change_with_device_domain(self.analysis,
            self.laboratory)

    @staticmethod
    def _on_change_with_device_domain(analysis=None, laboratory=None,
            by_default=False):
        cursor = Transaction().connection.cursor()
        LimsAnalysisDevice = Pool().get('lims.analysis.device')

        if not analysis or not laboratory:
            return []

        if by_default:
            by_default_clause = 'AND by_default = TRUE'
        else:
            by_default_clause = ''
        cursor.execute('SELECT DISTINCT(device) '
            'FROM "' + LimsAnalysisDevice._table + '" '
            'WHERE analysis = %s  '
                'AND laboratory = %s '
                + by_default_clause,
            (analysis.id, laboratory.id))
        res = cursor.fetchall()
        if not res:
            return []
        return [x[0] for x in res]

    @classmethod
    def get_views_field(cls, services, names):
        result = {}
        for name in names:
            field_name = name[:-5]
            result[name] = {}
            for s in services:
                field = getattr(s, field_name, None)
                result[name][s.id] = field.id if field else None
        return result

    @classmethod
    def search_views_field(cls, name, clause):
        return [(name[:-5],) + tuple(clause[1:])]

    @classmethod
    def search_analysis_field(cls, name, clause):
        if name == 'analysis_type':
            name = 'type'
        return [('analysis.' + name,) + tuple(clause[1:])]

    @classmethod
    def search_create_date2(cls, name, clause):
        cursor = Transaction().connection.cursor()
        operator_ = clause[1:2][0]
        cursor.execute('SELECT id '
                'FROM "' + cls._table + '" '
                'WHERE create_date' + operator_ + ' %s',
                clause[2:3])
        return [('id', 'in', [x[0] for x in cursor.fetchall()])]

    @classmethod
    def get_fraction_field(cls, services, names):
        result = {}
        for name in names:
            result[name] = {}
            if name == 'label':
                for s in services:
                    result[name][s.id] = getattr(s.fraction, name, None)
            else:
                for s in services:
                    field = getattr(s.fraction, name, None)
                    result[name][s.id] = field.id if field else None
        return result

    def get_create_date2(self, name):
        return self.create_date.replace(microsecond=0)

    @classmethod
    def search_fraction_field(cls, name, clause):
        return [('fraction.' + name,) + tuple(clause[1:])]

    @classmethod
    def order_create_date2(cls, tables):
        return cls.create_date.convert_order('create_date', tables, cls)

    def _order_analysis_field(name):
        def order_field(tables):
            Analysis = Pool().get('lims.analysis')
            field = Analysis._fields[name]
            table, _ = tables[None]
            analysis_tables = tables.get('analysis')
            if analysis_tables is None:
                analysis = Analysis.__table__()
                analysis_tables = {
                    None: (analysis, analysis.id == table.analysis),
                    }
                tables['analysis'] = analysis_tables
            return field.convert_order(name, analysis_tables, Analysis)
        return staticmethod(order_field)
    # Redefine convert_order function with 'order_%s' % field
    order_analysis_view = _order_analysis_field('id')
    order_analysis_type = _order_analysis_field('type')

    def _order_fraction_field(name):
        def order_field(tables):
            Fraction = Pool().get('lims.fraction')
            field = Fraction._fields[name]
            table, _ = tables[None]
            fraction_tables = tables.get('fraction')
            if fraction_tables is None:
                fraction = Fraction.__table__()
                fraction_tables = {
                    None: (fraction, fraction.id == table.fraction),
                    }
                tables['fraction'] = fraction_tables
            return field.convert_order(name, fraction_tables, Fraction)
        return staticmethod(order_field)
    # Redefine convert_order function with 'order_%s' % field
    order_sample = _order_fraction_field('sample')
    order_entry = _order_fraction_field('entry')
    order_party = _order_fraction_field('party')

    def get_confirmed(self, name=None):
        if self.fraction:
            return self.fraction.confirmed
        return False

    @classmethod
    def search_confirmed(cls, name, clause):
        return [('fraction.confirmed',) + tuple(clause[1:])]

    @classmethod
    def get_has_results_report(cls, services, names):
        cursor = Transaction().connection.cursor()
        LimsNotebookLine = Pool().get('lims.notebook.line')

        result = {}
        for name in names:
            result[name] = {}
            for s in services:
                cursor.execute('SELECT service '
                    'FROM "' + LimsNotebookLine._table + '" '
                    'WHERE service = %s '
                        'AND results_report IS NOT NULL',
                    (s.id,))
                value = False
                if cursor.fetchone():
                    value = True
                result[name][s.id] = value
        return result

    def get_manage_service_available(self, name=None):
        LimsNotebookLine = Pool().get('lims.notebook.line')

        planned_notebook_lines = LimsNotebookLine.search([
            ('service', '=', self.id),
            ('planification', '!=', None),
            ])
        if planned_notebook_lines:
            return False
        return True


class LimsFraction(ModelSQL, ModelView):
    'Fraction'
    __name__ = 'lims.fraction'
    _rec_name = 'number'

    number = fields.Char('Number', select=True, readonly=True)
    create_date2 = fields.Function(fields.DateTime('Create Date'),
       'get_create_date2', searcher='search_create_date2')
    sample = fields.Many2One('lims.sample', 'Sample', required=True,
        ondelete='CASCADE', select=True, depends=['number'],
        states={'readonly': Bool(Eval('number'))})
    sample_view = fields.Function(fields.Many2One('lims.sample', 'Sample',
        states={'invisible': Not(Bool(Eval('_parent_sample')))}),
        'on_change_with_sample_view')
    entry = fields.Function(fields.Many2One('lims.entry', 'Entry'),
        'get_sample_field',
        searcher='search_sample_field')
    party = fields.Function(fields.Many2One('party.party', 'Party'),
        'get_sample_field',
        searcher='search_sample_field')
    label = fields.Function(fields.Char('Label'), 'get_sample_field',
        searcher='search_sample_field')
    type = fields.Many2One('lims.fraction.type', 'Fraction type',
        required=True)
    storage_location = fields.Many2One('stock.location', 'Storage location',
        required=True, domain=[('type', '=', 'storage')])
    storage_time = fields.Integer('Storage time (in months)', required=True)
    weight = fields.Float('Weight')
    weight_uom = fields.Many2One('product.uom', 'Weight UoM',
        domain=[('category.lims_only_available', '=', True)])
    packages_quantity = fields.Integer('Packages quantity', required=True)
    package_type = fields.Many2One('lims.packaging.type', 'Package type',
        required=True)
    size = fields.Float('Size')
    size_uom = fields.Many2One('product.uom', 'Size UoM',
        domain=[('category.lims_only_available', '=', True)])
    expiry_date = fields.Date('Expiry date', states={'readonly': True})
    discharge_date = fields.Date('Discharge date')
    countersample_location = fields.Many2One('stock.location',
        'Countersample location', readonly=True)
    countersample_date = fields.Date('Countersample date', readonly=True)
    fraction_state = fields.Many2One('lims.packaging.integrity',
        'Fraction state', required=True)
    services = fields.One2Many('lims.service', 'fraction', 'Services',
        states={'readonly': Bool(Eval('button_manage_services_available'))},
        context={
            'analysis_domain': Eval('analysis_domain'),
            'typification_domain': Eval('typification_domain'),
            'product_type': Eval('product_type'), 'matrix': Eval('matrix'),
            'fraction': Eval('id'), 'sample': Eval('sample'),
            'entry': Eval('entry'), 'party': Eval('party'),
            'readonly': False,
            },
        depends=['button_manage_services_available', 'analysis_domain',
            'typification_domain', 'product_type', 'matrix', 'sample',
            'entry', 'party',
            ])
    shared = fields.Boolean('Shared')
    comments = fields.Text('Comments')
    analysis_domain = fields.Function(fields.Many2Many('lims.analysis',
        None, None, 'Analysis domain'),
        'on_change_with_analysis_domain')
    typification_domain = fields.Function(fields.Many2Many(
        'lims.typification', None, None, 'Typification domain'),
        'on_change_with_typification_domain')
    product_type = fields.Function(fields.Many2One('lims.product.type',
        'Product type'),
        'on_change_with_product_type')
    matrix = fields.Function(fields.Many2One('lims.matrix', 'Matrix'),
        'on_change_with_matrix')
    button_manage_services_available = fields.Function(fields.Boolean(
        'Button manage services available'),
        'on_change_with_button_manage_services_available')
    confirmed = fields.Boolean('Confirmed')
    button_confirm_available = fields.Function(fields.Boolean(
        'Button confirm available'),
        'on_change_with_button_confirm_available')
    current_location = fields.Function(fields.Many2One('stock.location',
        'Current Location'), 'get_current_location',
        searcher='search_current_location')
    duplicated_analysis_message = fields.Text('Message', readonly=True,
        states={'invisible': Not(Bool(Eval('duplicated_analysis_message')))})
    has_results_report = fields.Function(fields.Boolean('Results Report'),
        'get_has_results_report', searcher='search_has_results_report')
    has_all_results_reported = fields.Function(fields.Boolean(
        'All results reported'), 'get_has_all_results_reported')
    waiting_confirmation = fields.Boolean('Waiting confirmation')
    entry_state = fields.Function(fields.Selection([
        ('draft', 'Draft'),
        ('ongoing', 'Ongoing'),
        ('pending', 'Administration pending'),
        ('closed', 'Closed'),
        ], 'Entry State'), 'get_entry_state', searcher='search_entry_state')

    @classmethod
    def __setup__(cls):
        super(LimsFraction, cls).__setup__()
        cls._order.insert(0, ('number', 'DESC'))
        cls._buttons.update({
            'manage_services': {
                'invisible': ~Eval('button_manage_services_available'),
                },
            'complete_services': {
                'invisible': ~Eval('button_manage_services_available'),
                },
            'confirm': {
                'invisible': ~Eval('button_confirm_available'),
                },
            })
        cls._error_messages.update({
            'missing_fraction_product': ('Missing "Fraction product" '
                'on Lims configuration'),
            'delete_fraction': ('You can not delete fraction "%s" because '
                'it is confirmed'),
            'duplicated_analysis': ('The analysis "%s" is assigned more'
                ' than once'),
            'not_services': ('You can not confirm fraction "%s" because '
                'has not services'),
            'not_divided': ('You can not confirm fraction because '
                'is not yet divided'),
            })

    @staticmethod
    def default_packages_quantity():
        return 1

    @staticmethod
    def default_storage_time():
        return 3

    @staticmethod
    def default_confirmed():
        return False

    @staticmethod
    def default_waiting_confirmation():
        return False

    @classmethod
    def get_next_number(cls, sample_id, f_count):
        LimsSample = Pool().get('lims.sample')

        samples = LimsSample.search([('id', '=', sample_id)])
        sample_number = samples[0].number
        fraction_number = cls.search_count([('sample', '=', sample_id)])
        fraction_number += f_count
        return '%s-%s' % (sample_number, fraction_number)

    @classmethod
    def create(cls, vlist):
        vlist = [x.copy() for x in vlist]
        f_count = {}
        for values in vlist:
            if not values['sample'] in f_count:
                f_count[values['sample']] = 0
            f_count[values['sample']] += 1
            values['number'] = cls.get_next_number(values['sample'],
                f_count[values['sample']])
        return super(LimsFraction, cls).create(vlist)

    @classmethod
    def view_attributes(cls):
        return [
            ('//group[@id="button_confirm"]', 'states', {
                    'invisible': ~Eval('button_confirm_available'),
                    }),
            ('/tree', 'colors',
                If(Bool(Eval('has_results_report')), 'blue',
                If(Bool(Eval('confirmed')), 'black', 'red'))),
            ]

    @classmethod
    def copy(cls, fractions, default=None):
        if default is None:
            default = {}

        new_fractions = []
        for fraction in sorted(fractions, key=lambda x: x.number):
            current_default = default.copy()
            current_default['confirmed'] = False
            current_default['waiting_confirmation'] = False
            current_default['expiry_date'] = None
            current_default['countersample_date'] = None
            current_default['countersample_location'] = None

            new_fraction, = super(LimsFraction, cls).copy([fraction],
                default=current_default)
            new_fractions.append(new_fraction)
        return new_fractions

    @classmethod
    def check_delete(cls, fractions):
        for fraction in fractions:
            if fraction.confirmed:
                cls.raise_user_error('delete_fraction', (fraction.rec_name,))

    @classmethod
    def delete(cls, fractions):
        cls.check_delete(fractions)
        super(LimsFraction, cls).delete(fractions)

    @fields.depends('type', 'storage_location')
    def on_change_with_storage_time(self, name=None):
        if (self.type and self.type.max_storage_time):
            return self.type.max_storage_time
        if (self.storage_location and self.storage_location.storage_time):
            return self.storage_location.storage_time
        return 3

    @staticmethod
    def default_analysis_domain():
        return Transaction().context.get('analysis_domain', [])

    @fields.depends('sample')
    def on_change_with_analysis_domain(self, name=None):
        if Transaction().context.get('analysis_domain'):
            return Transaction().context.get('analysis_domain')
        if self.sample:
            return self.sample.on_change_with_analysis_domain()
        return []

    @staticmethod
    def default_typification_domain():
        return Transaction().context.get('typification_domain', [])

    @fields.depends('sample')
    def on_change_with_typification_domain(self, name=None):
        if Transaction().context.get('typification_domain'):
            return Transaction().context.get('typification_domain')
        if self.sample:
            return self.sample.on_change_with_typification_domain()
        return []

    @staticmethod
    def default_product_type():
        return Transaction().context.get('product_type', None)

    @fields.depends('sample')
    def on_change_with_product_type(self, name=None):
        if Transaction().context.get('product_type'):
            return Transaction().context.get('product_type')
        if self.sample and self.sample.product_type:
            return self.sample.product_type.id
        return None

    @staticmethod
    def default_matrix():
        return Transaction().context.get('matrix', None)

    @fields.depends('sample')
    def on_change_with_matrix(self, name=None):
        if Transaction().context.get('matrix'):
            return Transaction().context.get('matrix')
        if self.sample and self.sample.matrix:
            return self.sample.matrix.id
        return None

    @staticmethod
    def default_sample_view():
        if (Transaction().context.get('sample') > 0):
            return Transaction().context.get('sample')
        return None

    @fields.depends('sample')
    def on_change_with_sample_view(self, name=None):
        if self.sample:
            return self.sample.id
        return None

    @staticmethod
    def default_entry():
        if (Transaction().context.get('entry') > 0):
            return Transaction().context.get('entry')
        return None

    @fields.depends('sample')
    def on_change_with_entry(self, name=None):
        if self.sample:
            result = self.get_sample_field((self,), ('entry',))
            return result['entry'][self.id]
        return None

    @staticmethod
    def default_party():
        if (Transaction().context.get('party') > 0):
            return Transaction().context.get('party')
        return None

    @fields.depends('sample')
    def on_change_with_party(self, name=None):
        if self.sample:
            result = self.get_sample_field((self,), ('party',))
            return result['party'][self.id]
        return None

    @staticmethod
    def default_label():
        return Transaction().context.get('label', '')

    @fields.depends('sample')
    def on_change_with_label(self, name=None):
        if self.sample:
            result = self.get_sample_field((self,), ('label',))
            return result['label'][self.id]
        return ''

    @staticmethod
    def default_package_type():
        if (Transaction().context.get('package_type') > 0):
            return Transaction().context.get('package_type')
        return None

    @fields.depends('sample')
    def on_change_with_package_type(self, name=None):
        if self.sample:
            result = self.get_sample_field((self,), ('package_type',))
            return result['package_type'][self.id]
        return None

    @staticmethod
    def default_size():
        return Transaction().context.get('size', None)

    @fields.depends('sample')
    def on_change_with_size(self, name=None):
        if self.sample:
            result = self.get_sample_field((self,), ('size',))
            return result['size'][self.id]
        return None

    @staticmethod
    def default_size_uom():
        if (Transaction().context.get('size_uom') > 0):
            return Transaction().context.get('size_uom')
        return None

    @fields.depends('sample')
    def on_change_with_size_uom(self, name=None):
        if self.sample:
            result = self.get_sample_field((self,), ('size_uom',))
            return result['size_uom'][self.id]
        return None

    @staticmethod
    def default_fraction_state():
        if (Transaction().context.get('fraction_state') > 0):
            return Transaction().context.get('fraction_state')
        return None

    @fields.depends('sample')
    def on_change_with_fraction_state(self, name=None):
        if self.sample:
            result = self.get_sample_field((self,), ('fraction_state',))
            return result['fraction_state'][self.id]
        return None

    @classmethod
    def get_sample_field(cls, fractions, names):
        result = {}
        for name in names:
            result[name] = {}
            if name in ('label', 'size'):
                for f in fractions:
                    result[name][f.id] = getattr(f.sample, name, None)
            elif name == 'fraction_state':
                for f in fractions:
                    field = getattr(f.sample, 'package_state', None)
                    result[name][f.id] = field.id if field else None
            else:
                for f in fractions:
                    field = getattr(f.sample, name, None)
                    result[name][f.id] = field.id if field else None
        return result

    @classmethod
    def search_sample_field(cls, name, clause):
        return [('sample.' + name,) + tuple(clause[1:])]

    @classmethod
    def get_entry_state(cls, fractions, name):
        result = {}
        for f in fractions:
            result[f.id] = getattr(f.entry, 'state', None)
        return result

    @classmethod
    def search_entry_state(cls, name, clause):
        return [('sample.entry.state',) + tuple(clause[1:])]

    @fields.depends('confirmed')
    def on_change_with_button_manage_services_available(self, name=None):
        if self.confirmed:
            return True
        return False

    @classmethod
    @ModelView.button_action('lims.wiz_lims_manage_services')
    def manage_services(cls, fractions):
        pass

    @classmethod
    @ModelView.button_action('lims.wiz_lims_complete_services')
    def complete_services(cls, fractions):
        pass

    @fields.depends('confirmed', 'sample')
    def on_change_with_button_confirm_available(self, name=None):
        if (not self.confirmed and self.sample and self.sample.entry and
                (self.sample.entry.state == 'ongoing')):
            return True
        return False

    @classmethod
    def check_divided_report(cls, fractions):
        pool = Pool()
        LimsService = pool.get('lims.service')
        LimsEntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        services = LimsService.search([
            ('fraction', 'in', [f.id for f in fractions]),
            ('divide', '=', True),
            ])
        if services:
            if (LimsEntryDetailAnalysis.search_count([
                    ('service', 'in', [s.id for s in services]),
                    ('report_grouper', '!=', 0),
                    ]) == 0):
                cls.raise_user_error('not_divided')

    @classmethod
    @ModelView.button
    def confirm(cls, fractions):
        pool = Pool()
        Config = pool.get('lims.configuration')
        Service = pool.get('lims.service')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        confirm_background = Config(1).entry_confirm_background

        cls.check_divided_report(fractions)
        fractions_to_save = []
        for fraction in fractions:
            services = Service.search([('fraction', '=', fraction.id)])
            Service.copy_analysis_comments(services)
            Service.set_confirmation_date(services)
            fraction.create_laboratory_notebook()
            analysis_detail = EntryDetailAnalysis.search([
                ('fraction', '=', fraction.id)])
            if analysis_detail:
                EntryDetailAnalysis.create_notebook_lines(analysis_detail,
                    fraction)

            fraction.confirmed = True
            if confirm_background:
                fraction.waiting_confirmation = True
            else:
                fraction.create_stock_move()
            fractions_to_save.append(fraction)
        cls.save(fractions_to_save)

    def create_laboratory_notebook(self):
        pool = Pool()
        LimsNotebook = pool.get('lims.notebook')
        with Transaction().set_user(0):
            notebook = LimsNotebook(
                fraction=self.id,
                )
            notebook.save()

    def create_stock_move(self):
        Move = Pool().get('stock.move')
        move = self._get_stock_move()
        if not move:
            return
        with Transaction().set_context(check_current_location=False):
            move.save()
            Move.assign([move])
            Move.do([move])

    def _get_stock_move(self):
        pool = Pool()
        Config = pool.get('lims.configuration')
        Date = pool.get('ir.date')
        User = pool.get('res.user')
        Location = pool.get('stock.location')
        Move = pool.get('stock.move')

        config_ = Config(1)
        if config_.fraction_product:
            product = config_.fraction_product
        else:
            self.raise_user_error('missing_fraction_product')
        today = Date.today()
        company = User(Transaction().user).company
        if self.sample.entry.party.customer_location:
            from_location = self.sample.entry.party.customer_location
        else:
            locations = Location.search([('type', '=', 'customer')])
            from_location = locations[0] if len(locations) == 1 else None

        with Transaction().set_user(0, set_context=True):
            move = Move()
        move.product = product.id
        move.fraction = self.id
        move.quantity = self.packages_quantity
        move.uom = product.default_uom
        move.from_location = from_location
        move.to_location = self.storage_location
        move.company = company
        move.planned_date = today
        move.origin = self
        move.state = 'draft'
        return move

    @classmethod
    def confirm_waiting_fractions(cls):
        '''
        Cron - Confirm Waiting Fractions
        '''
        logger = logging.getLogger('lims')

        fractions = cls.search([
            ('waiting_confirmation', '=', True),
            ], order=[('id', 'ASC')])
        if fractions:
            logger.info('Cron - Confirming fractions:INIT')
            fractions_to_save = []
            for fraction in fractions:
                fraction.create_stock_move()
                fraction.waiting_confirmation = False
                fractions_to_save.append(fraction)
            cls.save(fractions_to_save)
            logger.info('Cron - Confirming fractions:END')

    @fields.depends('services')
    def on_change_services(self, name=None):
        LimsAnalysis = Pool().get('lims.analysis')
        self.duplicated_analysis_message = ''
        if self.services:
            analysis_ids = []
            for service in self.services:
                if service.analysis:
                    new_analysis_ids = [service.analysis.id]
                    new_analysis_ids.extend(LimsAnalysis.get_included_analysis(
                        service.analysis.id))

                    for a_id in new_analysis_ids:
                        if a_id in analysis_ids:
                            analysis = LimsAnalysis(a_id)
                            self.duplicated_analysis_message = (
                                self.raise_user_error('duplicated_analysis',
                                    (analysis.rec_name,),
                                    raise_exception=False))
                            return
                    analysis_ids.extend(new_analysis_ids)

    def get_create_date2(self, name):
        return self.create_date.replace(microsecond=0)

    @classmethod
    def search_create_date2(cls, name, clause):
        cursor = Transaction().connection.cursor()
        operator_ = clause[1:2][0]
        cursor.execute('SELECT id '
                'FROM "' + cls._table + '" '
                'WHERE create_date' + operator_ + ' %s',
                clause[2:3])
        return [('id', 'in', [x[0] for x in cursor.fetchall()])]

    @fields.depends('countersample_date', 'storage_time')
    def on_change_with_expiry_date(self, name=None):
        if self.countersample_date:
            return self.countersample_date + relativedelta(
                months=self.storage_time)
        return None

    @classmethod
    def get_current_location(cls, fractions, name=None):
        cursor = Transaction().connection.cursor()
        Move = Pool().get('stock.move')

        result = {}
        for f in fractions:
            cursor.execute('SELECT to_location '
                'FROM "' + Move._table + '" '
                'WHERE fraction = %s '
                    'AND state IN (\'assigned\', \'done\') '
                'ORDER BY effective_date DESC, id DESC '
                'LIMIT 1', (f.id,))
            location = cursor.fetchone()
            result[f.id] = location[0] if location else None
        return result

    @classmethod
    def search_current_location(cls, name, domain=None):
        if not Transaction().context.get('check_current_location', True):
            return []

        def _search_current_location_eval_domain(line, domain):
            operator_funcs = {
                '=': operator.eq,
                '>=': operator.ge,
                '>': operator.gt,
                '<=': operator.le,
                '<': operator.lt,
                '!=': operator.ne,
                'in': lambda v, l: v in l,
                'not in': lambda v, l: v not in l,
                'ilike': lambda v, l: False,
                }
            field, op, operand = domain
            value = line.get(field)
            return operator_funcs[op](value, operand)

        if domain and domain[1] == 'ilike':
            Location = Pool().get('stock.location')
            locations = Location.search([
                ('code', '=', domain[2]),
                ], order=[])
            if not locations:
                locations = Location.search([
                    ('name',) + tuple(domain[1:]),
                    ], order=[])
                if not locations:
                    return []
            domain = ('current_location', 'in', [l.id for l in locations])

        all_fractions = cls.search([])
        current_locations = cls.get_current_location(all_fractions).iteritems()

        processed_lines = [{
            'fraction': fraction,
            'current_location': location,
            } for fraction, location in current_locations]

        record_ids = [line['fraction'] for line in processed_lines
            if _search_current_location_eval_domain(line, domain)]
        return [('id', 'in', record_ids)]

    @classmethod
    def order_create_date2(cls, tables):
        return cls.create_date.convert_order('create_date', tables, cls)

    def _order_sample_field(name):
        def order_field(tables):
            Sample = Pool().get('lims.sample')
            field = Sample._fields[name]
            table, _ = tables[None]
            sample_tables = tables.get('sample')
            if sample_tables is None:
                sample = Sample.__table__()
                sample_tables = {
                    None: (sample, sample.id == table.sample),
                    }
                tables['sample'] = sample_tables
            return field.convert_order(name, sample_tables, Sample)
        return staticmethod(order_field)
    # Redefine convert_order function with 'order_%s' % field
    order_entry = _order_sample_field('entry')
    order_party = _order_sample_field('party')
    order_label = _order_sample_field('label')
    order_product_type = _order_sample_field('product_type')
    order_matrix = _order_sample_field('matrix')

    @classmethod
    def get_has_results_report(cls, fractions, names):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsService = pool.get('lims.service')
        LimsNotebookLine = pool.get('lims.notebook.line')

        result = {}
        for name in names:
            result[name] = {}
            for f in fractions:
                cursor.execute('SELECT s.fraction '
                    'FROM "' + LimsService._table + '" s '
                        'INNER JOIN "' + LimsNotebookLine._table + '" nl '
                        'ON s.id = nl.service '
                    'WHERE s.fraction = %s '
                        'AND nl.results_report IS NOT NULL',
                    (f.id,))
                value = False
                if cursor.fetchone():
                    value = True
                result[name][f.id] = value
        return result

    @classmethod
    def search_has_results_report(cls, name, clause):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsService = pool.get('lims.service')
        LimsNotebookLine = pool.get('lims.notebook.line')

        cursor.execute('SELECT DISTINCT(s.fraction) '
            'FROM "' + LimsService._table + '" s '
                'INNER JOIN "' + LimsNotebookLine._table + '" nl '
                'ON s.id = nl.service '
            'WHERE nl.results_report IS NOT NULL')
        has_results_report = [x[0] for x in cursor.fetchall()]

        field, op, operand = clause
        if (op, operand) in (('=', True), ('!=', False)):
            return [('id', 'in', has_results_report)]
        elif (op, operand) in (('=', False), ('!=', True)):
            return [('id', 'not in', has_results_report)]
        else:
            return []

    def get_has_all_results_reported(self, name=None):
        LimsNotebookLine = Pool().get('lims.notebook.line')
        notebook_lines = LimsNotebookLine.search([
            ('analysis_detail.service.fraction', '=', self.id),
            ('report', '=', True),
            ('annulled', '=', False),
            ])
        if not notebook_lines:
            return False
        for nl in notebook_lines:
            if not nl.accepted:
                return False
            if not nl.results_report:
                return False
        return True

    def get_formated_number(self, format):
        formated_number = self.number

        number_parts = self.number.split('/')
        number_parts2 = number_parts[1].split('-')
        if len(number_parts2) < 2:         # 2014: "0000097-1/2014"
            number_parts2 = number_parts[0].split('-')
            sample_number = number_parts2[0]
            sample_year = number_parts[1]
            fraction_number = number_parts2[1]
        else:                              # 2015: "2015/0000017-1"
            sample_number = number_parts2[0]
            sample_year = number_parts[0]
            fraction_number = number_parts2[1]

        if format == 'sn-sy-fn':
            formated_number = (sample_number + '-' + sample_year + '-' +
                fraction_number)

        elif format == 'sy-sn-fn':
            formated_number = (sample_year + '-' + sample_number + '-' +
                fraction_number)

        elif format == 'pt-m-sn-sy-fn':
            formated_number = (self.product_type.code + '-' +
                self.matrix.code + '-' + sample_number + '-' +
                sample_year + '-' + fraction_number)

        elif format == 'pt-m-sy-sn-fn':
            formated_number = (self.product_type.code + '-' +
                self.matrix.code + '-' + sample_year + '-' +
                sample_number + '-' + fraction_number)

        return formated_number


class LimsSample(ModelSQL, ModelView):
    'Sample'
    __name__ = 'lims.sample'
    _rec_name = 'number'

    number = fields.Char('Number', select=True, readonly=True)
    create_date2 = fields.Function(fields.DateTime('Create Date'),
       'get_create_date2', searcher='search_create_date2')
    date = fields.DateTime('Date', required=True)
    date2 = fields.Function(fields.Date('Date'), 'get_date',
        searcher='search_date')
    entry = fields.Many2One('lims.entry', 'Entry', required=True,
        ondelete='CASCADE', select=True, depends=['number'],
        states={'readonly': Bool(Eval('number'))})
    entry_view = fields.Function(fields.Many2One('lims.entry', 'Entry',
        states={'invisible': Not(Bool(Eval('_parent_entry')))}),
        'on_change_with_entry_view')
    party = fields.Function(fields.Many2One('party.party', 'Party'),
        'get_entry_field',
        searcher='search_entry_field')
    producer = fields.Many2One('lims.sample.producer', 'Producer company',
        domain=[('party', '=', Eval('party'))], depends=['party'])
    label = fields.Char('Label', translate=True)
    sample_client_description = fields.Char('Product described by the client',
        translate=True)
    product_type = fields.Many2One('lims.product.type', 'Product type',
        states={'readonly': Bool(Eval('product_type_matrix_readonly'))},
        required=True, domain=[
            ('id', 'in', Eval('product_type_domain')),
            ], depends=['product_type_domain', 'product_type_matrix_readonly'])
    product_type_view = fields.Function(fields.Many2One('lims.product.type',
        'Product type'), 'get_views_field', searcher='search_views_field')
    product_type_domain = fields.Function(fields.Many2Many(
        'lims.product.type', None, None, 'Product type domain'),
        'on_change_with_product_type_domain')
    matrix = fields.Many2One('lims.matrix', 'Matrix', required=True,
        states={'readonly': Bool(Eval('product_type_matrix_readonly'))},
        domain=[
            ('id', 'in', Eval('matrix_domain')),
            ], depends=['matrix_domain', 'product_type_matrix_readonly'])
    matrix_view = fields.Function(fields.Many2One('lims.matrix',
        'Matrix'), 'get_views_field', searcher='search_views_field')
    matrix_domain = fields.Function(fields.Many2Many('lims.matrix',
        None, None, 'Matrix domain'),
        'on_change_with_matrix_domain')
    product_type_matrix_readonly = fields.Function(fields.Boolean(
        'Product type and Matrix readonly'),
        'get_product_type_matrix_readonly')
    package_state = fields.Many2One('lims.packaging.integrity',
        'Package state')
    package_type = fields.Many2One('lims.packaging.type', 'Package type')
    packages_quantity = fields.Integer('Packages quantity', required=True)
    size = fields.Float('Size')
    size_uom = fields.Many2One('product.uom', 'Size UoM',
        domain=[('category.lims_only_available', '=', True)])
    restricted_entry = fields.Boolean('Restricted entry',
        states={'readonly': True})
    zone = fields.Many2One('lims.zone', 'Zone', required=True)
    trace_report = fields.Boolean('Trace report')
    fractions = fields.One2Many('lims.fraction', 'sample', 'Fractions',
        context={
            'analysis_domain': Eval('analysis_domain'),
            'typification_domain': Eval('typification_domain'),
            'product_type': Eval('product_type'), 'matrix': Eval('matrix'),
            'sample': Eval('id'), 'entry': Eval('entry'),
            'party': Eval('party'), 'label': Eval('label'),
            'package_type': Eval('package_type'), 'size': Eval('size'),
            'size_uom': Eval('size_uom'),
            'fraction_state': Eval('package_state'),
            },
        depends=['analysis_domain', 'typification_domain', 'entry',
            'party', 'label'])
    report_comments = fields.Text('Report comments', translate=True)
    comments = fields.Text('Comments')
    variety = fields.Many2One('lims.variety', 'Variety',
        domain=[('varieties.matrix', '=', Eval('matrix'))],
        depends=['matrix'])
    analysis_domain = fields.Function(fields.Many2Many('lims.analysis',
        None, None, 'Analysis domain'), 'on_change_with_analysis_domain')
    typification_domain = fields.Function(fields.Many2Many(
        'lims.typification', None, None, 'Typification domain'),
        'on_change_with_typification_domain')
    confirmed = fields.Function(fields.Boolean('Confirmed'), 'get_confirmed')
    has_results_report = fields.Function(fields.Boolean('Results Report'),
        'get_has_results_report')

    @classmethod
    def __setup__(cls):
        super(LimsSample, cls).__setup__()
        cls._order.insert(0, ('number', 'DESC'))
        cls._error_messages.update({
            'no_sample_sequence': ('There is no sample sequence for '
                'the work year "%s".'),
            'duplicated_label': ('The label "%s" is already present in '
                'another sample'),
            'delete_sample': ('You can not delete sample "%s" because '
                'its entry is not in draft state'),
            })

    @staticmethod
    def default_date():
        return datetime.now()

    @staticmethod
    def default_restricted_entry():
        return False

    @staticmethod
    def default_trace_report():
        return False

    @classmethod
    def copy(cls, samples, default=None):
        if default is None:
            default = {}

        new_samples = []
        for sample in sorted(samples, key=lambda x: x.number):
            new_sample, = super(LimsSample, cls).copy([sample],
                default=default)
            new_samples.append(new_sample)
        return new_samples

    def get_date(self, name):
        pool = Pool()
        Company = pool.get('company.company')

        date = self.date
        company_id = Transaction().context.get('company')
        if company_id:
            date = Company(company_id).convert_timezone_datetime(date)
        return date.date()

    def get_create_date2(self, name):
        return self.create_date.replace(microsecond=0)

    @classmethod
    def search_date(cls, name, clause):
        pool = Pool()
        Company = pool.get('company.company')
        cursor = Transaction().connection.cursor()

        timezone = None
        company_id = Transaction().context.get('company')
        if company_id:
            timezone = Company(company_id).timezone
        timezone_datetime = 'date::timestamp AT TIME ZONE \'UTC\''
        if timezone:
            timezone_datetime += ' AT TIME ZONE \'' + timezone + '\''

        operator_ = clause[1:2][0]
        cursor.execute('SELECT id '
                'FROM "' + cls._table + '" '
                'WHERE (' + timezone_datetime + ')::date '
                + operator_ + ' %s::date', clause[2:3])
        return [('id', 'in', [x[0] for x in cursor.fetchall()])]

    @classmethod
    def search_create_date2(cls, name, clause):
        cursor = Transaction().connection.cursor()
        operator_ = clause[1:2][0]
        cursor.execute('SELECT id '
                'FROM "' + cls._table + '" '
                'WHERE create_date' + operator_ + ' %s',
                clause[2:3])
        return [('id', 'in', [x[0] for x in cursor.fetchall()])]

    @classmethod
    def create(cls, vlist):
        pool = Pool()
        LimsLabWorkYear = pool.get('lims.lab.workyear')
        Sequence = pool.get('ir.sequence')

        workyear_id = LimsLabWorkYear.find()
        workyear = LimsLabWorkYear(workyear_id)
        sequence = workyear.get_sequence('sample')
        if not sequence:
            cls.raise_user_error('no_sample_sequence',
                (workyear.rec_name,))

        vlist = [x.copy() for x in vlist]
        for values in vlist:
            values['number'] = Sequence.get_id(sequence.id)
        samples = super(LimsSample, cls).create(vlist)
        for sample in samples:
            sample.warn_duplicated_label()
        return samples

    def warn_duplicated_label(self):
        return  # deactivated
        if self.label:
            duplicated = self.search([
                ('entry', '=', self.entry.id),
                ('label', '=', self.label),
                ('id', '!=', self.id),
                ])
            if duplicated:
                self.raise_user_warning('lims_sample_label@%s' %
                    self.number, 'duplicated_label', self.label)

    @classmethod
    def write(cls, *args):
        super(LimsSample, cls).write(*args)
        actions = iter(args)
        for samples, vals in zip(actions, actions):
            if vals.get('label'):
                for sample in samples:
                    sample.warn_duplicated_label()

    @fields.depends('product_type', 'matrix', 'zone')
    def on_change_with_restricted_entry(self, name=None):
        return (self.product_type and self.product_type.restricted_entry
            and self.matrix and self.matrix.restricted_entry
            and self.zone and self.zone.restricted_entry)

    @fields.depends('product_type', 'matrix')
    def on_change_with_analysis_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsTypification = pool.get('lims.typification')
        LimsCalculatedTypification = pool.get('lims.typification.calculated')
        LimsAnalysis = pool.get('lims.analysis')

        if not self.product_type or not self.matrix:
            return []

        cursor.execute('SELECT DISTINCT(analysis) '
            'FROM "' + LimsTypification._table + '" '
            'WHERE product_type = %s '
                'AND matrix = %s '
                'AND valid',
            (self.product_type.id, self.matrix.id))
        typified_analysis = [a[0] for a in cursor.fetchall()]
        if not typified_analysis:
            return []

        cursor.execute('SELECT id '
            'FROM "' + LimsAnalysis._table + '" '
            'WHERE type = \'analysis\' '
                'AND behavior IN (\'normal\', \'internal_relation\') '
                'AND disable_as_individual IS TRUE '
                'AND state = \'active\'')
        disabled_analysis = [a[0] for a in cursor.fetchall()]
        if disabled_analysis:
            typified_analysis = list(set(typified_analysis)
                - set(disabled_analysis))

        cursor.execute('SELECT DISTINCT(analysis) '
            'FROM "' + LimsCalculatedTypification._table + '" '
            'WHERE product_type = %s '
                'AND matrix = %s',
            (self.product_type.id, self.matrix.id))
        typified_sets_groups = [a[0] for a in cursor.fetchall()]

        cursor.execute('SELECT id '
            'FROM "' + LimsAnalysis._table + '" '
            'WHERE behavior = \'additional\' '
                'AND state = \'active\'')
        additional_analysis = [a[0] for a in cursor.fetchall()]

        return typified_analysis + typified_sets_groups + additional_analysis

    @fields.depends('product_type', 'matrix')
    def on_change_with_typification_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        LimsTypification = Pool().get('lims.typification')

        if not self.product_type or not self.matrix:
            return []

        cursor.execute('SELECT id '
            'FROM "' + LimsTypification._table + '" '
            'WHERE product_type = %s '
                'AND matrix = %s '
                'AND valid',
            (self.product_type.id, self.matrix.id))
        res = cursor.fetchall()
        if not res:
            return []
        return [x[0] for x in res]

    @staticmethod
    def default_product_type_domain():
        cursor = Transaction().connection.cursor()
        LimsTypification = Pool().get('lims.typification')

        cursor.execute('SELECT DISTINCT(product_type) '
            'FROM "' + LimsTypification._table + '" '
            'WHERE valid')
        res = cursor.fetchall()
        if not res:
            return []
        return [x[0] for x in res]

    def on_change_with_product_type_domain(self, name=None):
        return self.default_product_type_domain()

    @fields.depends('product_type')
    def on_change_product_type(self):
        matrix = None
        if self.product_type:
            matrixs = self.on_change_with_matrix_domain()
            if len(matrixs) == 1:
                matrix = matrixs[0]
        self.matrix = matrix

    @fields.depends('product_type')
    def on_change_with_matrix_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        LimsTypification = Pool().get('lims.typification')

        if not self.product_type:
            return []

        cursor.execute('SELECT DISTINCT(matrix) '
            'FROM "' + LimsTypification._table + '" '
            'WHERE product_type = %s '
            'AND valid',
            (self.product_type.id,))
        res = cursor.fetchall()
        if not res:
            return []
        return [x[0] for x in res]

    def get_product_type_matrix_readonly(self, name=None):
        pool = Pool()
        LimsService = pool.get('lims.service')
        if LimsService.search_count([('sample', '=', self.id)]) != 0:
            return True
        return False

    @classmethod
    def check_delete(cls, samples):
        for sample in samples:
            if sample.entry and sample.entry.state != 'draft':
                cls.raise_user_error('delete_sample', (sample.rec_name,))

    @classmethod
    def delete(cls, samples):
        cls.check_delete(samples)
        super(LimsSample, cls).delete(samples)

    @staticmethod
    def default_entry_view():
        if (Transaction().context.get('entry') > 0):
            return Transaction().context.get('entry')
        return None

    @fields.depends('entry')
    def on_change_with_entry_view(self, name=None):
        if self.entry:
            return self.entry.id
        return None

    @staticmethod
    def default_party():
        if (Transaction().context.get('party') > 0):
            return Transaction().context.get('party')
        return None

    @staticmethod
    def default_zone():
        Party = Pool().get('party.party')

        if (Transaction().context.get('party') > 0):
            party = Party(Transaction().context.get('party'))
            if party.entry_zone:
                return party.entry_zone.id

    @fields.depends('entry')
    def on_change_with_party(self, name=None):
        if self.entry:
            result = self.get_entry_field((self,), ('party',))
            return result['party'][self.id]
        return None

    @classmethod
    def get_views_field(cls, samples, names):
        result = {}
        for name in names:
            field_name = name[:-5]
            result[name] = {}
            for s in samples:
                field = getattr(s, field_name, None)
                result[name][s.id] = field.id if field else None
        return result

    @classmethod
    def search_views_field(cls, name, clause):
        return [(name[:-5],) + tuple(clause[1:])]

    @classmethod
    def get_entry_field(cls, samples, names):
        result = {}
        for name in names:
            result[name] = {}
            for s in samples:
                field = getattr(s.entry, name, None)
                result[name][s.id] = field.id if field else None
        return result

    @classmethod
    def search_entry_field(cls, name, clause):
        return [('entry.' + name,) + tuple(clause[1:])]

    @staticmethod
    def order_product_type_view(tables):
        ProductType = Pool().get('lims.product.type')
        field = ProductType._fields['id']
        table, _ = tables[None]
        product_type_tables = tables.get('product_type')
        if product_type_tables is None:
            product_type = ProductType.__table__()
            product_type_tables = {
                None: (product_type, product_type.id == table.product_type),
                }
            tables['product_type'] = product_type_tables
        return field.convert_order('id', product_type_tables, ProductType)

    @staticmethod
    def order_matrix_view(tables):
        Matrix = Pool().get('lims.matrix')
        field = Matrix._fields['id']
        table, _ = tables[None]
        matrix_tables = tables.get('matrix')
        if matrix_tables is None:
            matrix = Matrix.__table__()
            matrix_tables = {
                None: (matrix, matrix.id == table.matrix),
                }
            tables['matrix'] = matrix_tables
        return field.convert_order('id', matrix_tables, Matrix)

    def get_confirmed(self, name=None):
        if not self.fractions:
            return False
        for fraction in self.fractions:
            if not fraction.confirmed:
                return False
        return True

    @classmethod
    def view_attributes(cls):
        return [('/tree', 'colors',
                If(Bool(Eval('has_results_report')), 'blue',
                If(Bool(Eval('confirmed')), 'black', 'red')))]

    @classmethod
    def order_create_date2(cls, tables):
        return cls.create_date.convert_order('create_date', tables, cls)

    @staticmethod
    def order_party(tables):
        Entry = Pool().get('lims.entry')
        field = Entry._fields['party']
        table, _ = tables[None]
        entry_tables = tables.get('entry')
        if entry_tables is None:
            entry = Entry.__table__()
            entry_tables = {
                None: (entry, entry.id == table.entry),
                }
            tables['entry'] = entry_tables
        return field.convert_order('party', entry_tables, Entry)

    @classmethod
    def get_has_results_report(cls, samples, names):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LimsFraction = pool.get('lims.fraction')
        LimsService = pool.get('lims.service')
        LimsNotebookLine = pool.get('lims.notebook.line')

        result = {}
        for name in names:
            result[name] = {}
            for s in samples:
                cursor.execute('SELECT f.sample '
                    'FROM "' + LimsFraction._table + '" f '
                        'INNER JOIN "' + LimsService._table + '" s '
                        'ON f.id = s.fraction '
                        'INNER JOIN "' + LimsNotebookLine._table + '" nl '
                        'ON s.id = nl.service '
                    'WHERE f.sample = %s '
                        'AND nl.results_report IS NOT NULL',
                    (s.id,))
                value = False
                if cursor.fetchone():
                    value = True
                result[name][s.id] = value
        return result


class LimsNotebook(ModelSQL, ModelView):
    'Laboratory Notebook'
    __name__ = 'lims.notebook'
    _rec_name = 'fraction'

    fraction = fields.Many2One('lims.fraction', 'Fraction', required=True,
        readonly=True, ondelete='CASCADE', select=True)
    lines = fields.One2Many('lims.notebook.line', 'notebook', 'Lines')
    product_type = fields.Function(fields.Many2One('lims.product.type',
        'Product type'), 'get_sample_field', searcher='search_sample_field')
    matrix = fields.Function(fields.Many2One('lims.matrix', 'Matrix'),
        'get_sample_field', searcher='search_sample_field')
    party = fields.Function(fields.Many2One('party.party', 'Party'),
        'get_sample_field', searcher='search_sample_field')
    party_code = fields.Function(fields.Char('Party'), 'get_party_code',
        searcher='search_party_code')
    label = fields.Function(fields.Char('Label'), 'get_sample_field',
        searcher='search_sample_field')
    date = fields.Function(fields.DateTime('Date'), 'get_sample_field',
        searcher='search_sample_field')
    date2 = fields.Function(fields.Date('Date'), 'get_sample_field',
        searcher='search_sample_field')
    fraction_type = fields.Function(fields.Many2One('lims.fraction.type',
        'Fraction type'), 'get_fraction_field',
        searcher='search_fraction_field')
    fraction_comments = fields.Function(fields.Text('Fraction Comments'),
        'get_fraction_field')
    shared = fields.Function(fields.Boolean('Shared'), 'get_fraction_field',
        searcher='search_fraction_field')
    current_location = fields.Function(fields.Many2One('stock.location',
        'Current Location'), 'get_current_location',
        searcher='search_current_location')
    divided_report = fields.Function(fields.Boolean('Divided report'),
        'get_divided_report')

    @classmethod
    def __setup__(cls):
        super(LimsNotebook, cls).__setup__()
        cls._order.insert(0, ('fraction', 'DESC'))

    def get_rec_name(self, name):
        if self.fraction:
            return self.fraction.rec_name

    @classmethod
    def search_rec_name(cls, name, clause):
        return [('fraction',) + tuple(clause[1:])]

    @classmethod
    def get_sample_field(cls, notebooks, names):
        result = {}
        for name in names:
            result[name] = {}
            if name in ('label', 'date', 'date2'):
                for n in notebooks:
                    result[name][n.id] = getattr(n.fraction.sample, name, None)
            else:
                for n in notebooks:
                    field = getattr(n.fraction.sample, name, None)
                    result[name][n.id] = field.id if field else None
        return result

    @classmethod
    def search_sample_field(cls, name, clause):
        return [('fraction.sample.' + name,) + tuple(clause[1:])]

    @classmethod
    def get_party_code(cls, notebooks, name):
        result = {}
        for n in notebooks:
            result[n.id] = n.party.code
        return result

    @classmethod
    def search_party_code(cls, name, clause):
        return [('fraction.sample.entry.party.code',) + tuple(clause[1:])]

    @classmethod
    def get_fraction_field(cls, notebooks, names):
        result = {}
        for name in names:
            result[name] = {}
            if name == 'fraction_type':
                for n in notebooks:
                    field = getattr(n.fraction, 'type', None)
                    result[name][n.id] = field.id if field else None
            elif name == 'fraction_comments':
                for n in notebooks:
                    result[name][n.id] = getattr(n.fraction, 'comments', None)
            else:
                for n in notebooks:
                    result[name][n.id] = getattr(n.fraction, name, None)
        return result

    @classmethod
    def search_fraction_field(cls, name, clause):
        if name == 'fraction_type':
            name = 'type'
        return [('fraction.' + name,) + tuple(clause[1:])]

    def get_divided_report(self, name):
        if not self.fraction or not self.fraction.services:
            return False
        for s in self.fraction.services:
            if s.divide:
                return True
        return False

    @classmethod
    def get_current_location(cls, notebooks, name=None):
        cursor = Transaction().connection.cursor()
        Move = Pool().get('stock.move')

        result = {}
        for n in notebooks:
            cursor.execute('SELECT to_location '
                'FROM "' + Move._table + '" '
                'WHERE fraction = %s '
                    'AND state IN (\'assigned\', \'done\') '
                'ORDER BY effective_date DESC, id DESC '
                'LIMIT 1', (n.fraction.id,))
            location = cursor.fetchone()
            result[n.id] = location[0] if location else None
        return result

    @classmethod
    def search_current_location(cls, name, domain=None):

        def _search_current_location_eval_domain(line, domain):
            operator_funcs = {
                '=': operator.eq,
                '>=': operator.ge,
                '>': operator.gt,
                '<=': operator.le,
                '<': operator.lt,
                '!=': operator.ne,
                'in': lambda v, l: v in l,
                'not in': lambda v, l: v not in l,
                'ilike': lambda v, l: False,
                }
            field, op, operand = domain
            value = line.get(field)
            return operator_funcs[op](value, operand)

        if domain and domain[1] == 'ilike':
            Location = Pool().get('stock.location')
            locations = Location.search([
                ('code', '=', domain[2]),
                ], order=[])
            if not locations:
                locations = Location.search([
                    ('name',) + tuple(domain[1:]),
                    ], order=[])
                if not locations:
                    return []
            domain = ('current_location', 'in', [l.id for l in locations])

        all_notebooks = cls.search([])
        current_locations = cls.get_current_location(all_notebooks).iteritems()

        processed_lines = [{
            'fraction': fraction,
            'current_location': location,
            } for fraction, location in current_locations]

        record_ids = [line['notebook'] for line in processed_lines
            if _search_current_location_eval_domain(line, domain)]
        return [('id', 'in', record_ids)]

    @classmethod
    def view_attributes(cls):
        return [
            ('/tree', 'colors',
                If(Len(Eval('fraction_comments')) > 0, 'blue', 'black')),
            ]


class LimsNotebookLine(ModelSQL, ModelView):
    'Laboratory Notebook Line'
    __name__ = 'lims.notebook.line'
    _rec_name = 'analysis'

    notebook = fields.Many2One('lims.notebook', 'Laboratory notebook',
        ondelete='CASCADE', select=True, required=True)
    analysis_detail = fields.Many2One('lims.entry.detail.analysis',
        'Analysis detail', select=True)
    service = fields.Many2One('lims.service', 'Service', readonly=True,
        ondelete='CASCADE', select=True)
    analysis = fields.Many2One('lims.analysis', 'Analysis', required=True,
        readonly=True)
    repetition = fields.Integer('Repetition', readonly=True)
    start_date = fields.Date('Start date', readonly=True)
    end_date = fields.Date('End date', states={
        'readonly': Or(~Bool(Eval('start_date')), Bool(Eval('accepted'))),
        }, depends=['start_date', 'accepted'])
    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        readonly=True)
    method = fields.Many2One('lims.lab.method', 'Method',
        required=True, domain=['OR', ('id', '=', Eval('method')),
            ('id', 'in', Eval('method_domain'))],
        depends=['method_domain'])
    method_view = fields.Function(fields.Many2One('lims.lab.method',
        'Method'), 'get_views_field')
    method_domain = fields.Function(fields.Many2Many('lims.lab.method',
        None, None, 'Method domain'),
        'on_change_with_method_domain')
    device = fields.Many2One('lims.lab.device', 'Device',
        domain=['OR', ('id', '=', Eval('device')),
            ('id', 'in', Eval('device_domain'))],
        depends=['device_domain'])
    device_view = fields.Function(fields.Many2One('lims.lab.device',
        'Device'), 'get_views_field')
    device_domain = fields.Function(fields.Many2Many('lims.lab.device',
        None, None, 'Device domain'), 'on_change_with_device_domain')
    analysis_origin = fields.Char('Analysis origin', readonly=True)
    initial_concentration = fields.Char('Initial concentration')
    final_concentration = fields.Char('Final concentration')
    laboratory_professionals = fields.Many2Many(
        'lims.notebook.line-laboratory.professional', 'notebook_line',
        'professional', 'Preparation professionals')
    initial_unit = fields.Many2One('product.uom', 'Initial unit',
        domain=[('category.lims_only_available', '=', True)],
        states={'readonly': Bool(Eval('accepted'))}, depends=['accepted'])
    final_unit = fields.Many2One('product.uom', 'Final unit',
        domain=[('category.lims_only_available', '=', True)],
        states={'readonly': Bool(Eval('accepted'))}, depends=['accepted'])
    result_modifier = fields.Selection([
        ('eq', '='),
        ('low', '<'),
        ('nd', 'nd'),
        ('na', 'na'),
        ('pos', 'Positive'),
        ('neg', 'Negative'),
        ('ni', 'ni'),
        ('abs', 'Absence'),
        ('pre', 'Presence'),
        ], 'Result modifier', sort=False,
        states={'readonly': Bool(Eval('accepted'))}, depends=['accepted'])
    result_modifier_string = result_modifier.translated('result_modifier')
    converted_result_modifier = fields.Selection([
        ('eq', '='),
        ('low', '<'),
        ('nd', 'nd'),
        ('pos', 'Positive'),
        ('neg', 'Negative'),
        ('ni', 'ni'),
        ], 'Converted result modifier', sort=False,
        states={'readonly': Bool(Eval('accepted'))}, depends=['accepted'])
    converted_result_modifier_string = converted_result_modifier.translated(
        'converted_result_modifier')
    result = fields.Char('Result',
        states={'readonly': Bool(Eval('accepted'))}, depends=['accepted'])
    converted_result = fields.Char('Converted result',
        states={'readonly': Bool(Eval('accepted'))}, depends=['accepted'])
    detection_limit = fields.Char('Detection limit',
        states={'readonly': Bool(Eval('accepted'))}, depends=['accepted'])
    quantification_limit = fields.Char('Quantification limit',
        states={'readonly': Bool(Eval('accepted'))}, depends=['accepted'])
    check_result_limits = fields.Function(fields.Boolean(
        'Validate limits directly on the result'), 'get_typification_field')
    chromatogram = fields.Char('Chromatogram')
    professionals = fields.One2Many('lims.notebook.line.professional',
        'notebook_line', 'Analytic professionals')
    comments = fields.Text('Entry comments')
    theoretical_concentration = fields.Char('Theoretical concentration')
    concentration_level = fields.Many2One('lims.concentration.level',
        'Concentration level')
    decimals = fields.Integer('Decimals')
    backup = fields.Char('Backup')
    reference = fields.Char('Reference')
    literal_result = fields.Char('Literal result', translate=True,
        states={'readonly': Bool(Eval('accepted'))}, depends=['accepted'])
    rm_correction_formula = fields.Char('RM Correction Formula')
    report = fields.Boolean('Report')
    uncertainty = fields.Char('Uncertainty')
    verification = fields.Char('Verification')
    analysis_order = fields.Function(fields.Integer('Order'),
        'get_analysis_order')
    dilution_factor = fields.Float('Dilution factor')
    accepted = fields.Boolean('Accepted')
    acceptance_date = fields.DateTime('Acceptance date',
        states={'readonly': True})
    not_accepted_message = fields.Text('Message', readonly=True,
        states={'invisible': Not(Bool(Eval('not_accepted_message')))})
    annulled = fields.Boolean('Annulled', states={'readonly': True})
    annulment_date = fields.DateTime('Annulment date',
        states={'readonly': True})
    results_report = fields.Many2One('lims.results_report', 'Results Report',
        readonly=True)
    planification = fields.Many2One('lims.planification', 'Planification',
        readonly=True)
    urgent = fields.Function(fields.Boolean('Urgent'), 'get_service_field',
        searcher='search_service_field')
    priority = fields.Function(fields.Integer('Priority'),
        'get_service_field', searcher='search_service_field')
    report_date = fields.Function(fields.Date('Date agreed for result'),
        'get_service_field', searcher='search_service_field')
    fraction = fields.Function(fields.Many2One('lims.fraction', 'Fraction'),
        'get_service_field', searcher='search_service_field')
    fraction_type = fields.Function(fields.Many2One('lims.fraction.type',
        'Fraction type'), 'get_fraction_field',
        searcher='search_fraction_field')
    party = fields.Function(fields.Many2One('party.party', 'Party'),
        'get_fraction_field', searcher='search_fraction_field')
    product_type = fields.Function(fields.Many2One('lims.product.type',
        'Product type'), 'get_sample_field', searcher='search_sample_field')
    matrix = fields.Function(fields.Many2One('lims.matrix', 'Matrix'),
        'get_sample_field', searcher='search_sample_field')
    label = fields.Function(fields.Char('Label'), 'get_sample_field',
        searcher='search_sample_field')
    date = fields.Function(fields.DateTime('Date'), 'get_sample_field',
        searcher='search_sample_field')
    date2 = fields.Function(fields.Date('Date'), 'get_sample_field',
        searcher='search_sample_field')
    report_type = fields.Function(fields.Char('Report type'),
        'get_typification_field', searcher='search_typification_field')
    report_result_type = fields.Function(fields.Char('Result type'),
        'get_typification_field', searcher='search_typification_field')
    results_estimated_waiting = fields.Integer(
        'Estimated number of days for results', states={'readonly': True})
    results_estimated_date = fields.Function(fields.Date(
        'Estimated date of result'), 'get_results_estimated_date')
    department = fields.Many2One('company.department', 'Department',
        readonly=True)

    @classmethod
    def __setup__(cls):
        super(LimsNotebookLine, cls).__setup__()
        cls._order.insert(0, ('analysis_order', 'ASC'))
        cls._order.insert(1, ('repetition', 'ASC'))
        cls._error_messages.update({
            'end_date': 'The end date cannot be lower than start date',
            'end_date_wrong': ('End date should not be greater than the '
                'current date'),
            'accepted': 'The analysis "%s" is already accepted',
            'not_accepted_1': 'The analysis is not reported',
            'not_accepted_2': 'The analysis is annulled',
            'not_accepted_3': 'The analysis has not End date',
            'not_accepted_4': 'The analysis has not Result / Converted result',
            'not_accepted_5': 'The Converted result modifier is invalid',
            'not_accepted_6': 'The Result modifier is invalid',
            'not_accepted_7': ('The Converted result / Converted result '
                'modifier is invalid'),
            'accepted_1': 'The analysis is already reported (%s)',
            })

    @staticmethod
    def default_repetition():
        return 0

    @staticmethod
    def default_result_modifier():
        return 'eq'

    @staticmethod
    def default_converted_result_modifier():
        return 'eq'

    @staticmethod
    def default_decimals():
        return 2

    @staticmethod
    def default_report():
        return True

    @staticmethod
    def default_dilution_factor():
        return 1.0

    @staticmethod
    def default_accepted():
        return False

    @staticmethod
    def default_annulled():
        return False

    @classmethod
    def write(cls, *args):
        super(LimsNotebookLine, cls).write(*args)
        actions = iter(args)
        for lines, vals in zip(actions, actions):
            if vals.get('not_accepted_message'):
                cls.write(lines, {
                    'not_accepted_message': None,
                    })
            if 'accepted' in vals:
                cls.update_detail_analysis(lines, vals['accepted'])

    @staticmethod
    def update_detail_analysis(lines, accepted):
        LimsEntryDetailAnalysis = Pool().get('lims.entry.detail.analysis')

        details = [nl.analysis_detail.id for nl in lines]
        if accepted:
            analysis_details = LimsEntryDetailAnalysis.search([
                ('id', 'in', details),
                ])
            if analysis_details:
                LimsEntryDetailAnalysis.write(analysis_details, {
                    'state': 'done',
                    })
        else:
            analysis_details = LimsEntryDetailAnalysis.search([
                ('id', 'in', details),
                ('analysis.behavior', '!=', 'internal_relation'),
                ])
            if analysis_details:
                LimsEntryDetailAnalysis.write(analysis_details, {
                    'state': 'planned',
                    })
            analysis_details = LimsEntryDetailAnalysis.search([
                ('id', 'in', details),
                ('analysis.behavior', '=', 'internal_relation'),
                ])
            if analysis_details:
                LimsEntryDetailAnalysis.write(analysis_details, {
                    'state': 'unplanned',
                    })

    @classmethod
    def validate(cls, notebook_lines):
        super(LimsNotebookLine, cls).validate(notebook_lines)
        for line in notebook_lines:
            line.check_end_date()
            line.check_accepted()

    def check_end_date(self):
        if self.end_date:
            if not self.start_date or self.end_date < self.start_date:
                self.raise_user_error('end_date')
            if not self.start_date or self.end_date > datetime.now().date():
                self.raise_user_error('end_date_wrong')

    def check_accepted(self):
        if self.accepted:
            accepted_lines = self.search([
                ('notebook', '=', self.notebook.id),
                ('analysis', '=', self.analysis.id),
                ('accepted', '=', True),
                ('id', '!=', self.id),
                ])
            if accepted_lines:
                self.raise_user_error('accepted', (self.analysis.rec_name,))

    @classmethod
    def get_analysis_order(cls, notebook_lines, name):
        result = {}
        for nl in notebook_lines:
            analysis = getattr(nl, 'analysis', None)
            result[nl.id] = analysis.order if analysis else None
        return result

    @staticmethod
    def order_analysis_order(tables):
        LimsAnalysis = Pool().get('lims.analysis')
        field = LimsAnalysis._fields['order']
        table, _ = tables[None]
        analysis_tables = tables.get('analysis')
        if analysis_tables is None:
            analysis = LimsAnalysis.__table__()
            analysis_tables = {
                None: (analysis, analysis.id == table.analysis),
                }
            tables['analysis'] = analysis_tables
        return field.convert_order('order', analysis_tables, LimsAnalysis)

    @classmethod
    def get_views_field(cls, notebook_lines, names):
        result = {}
        for name in names:
            field_name = name[:-5]
            result[name] = {}
            for nl in notebook_lines:
                field = getattr(nl, field_name, None)
                result[name][nl.id] = field.id if field else None
        return result

    @classmethod
    def get_service_field(cls, notebook_lines, names):
        result = {}
        for name in names:
            result[name] = {}
            if name == 'fraction':
                for nl in notebook_lines:
                    field = getattr(nl.service, name, None)
                    result[name][nl.id] = field.id if field else None
            else:
                for nl in notebook_lines:
                    result[name][nl.id] = getattr(nl.service, name, None)
        return result

    @classmethod
    def search_service_field(cls, name, clause):
        return [('service.' + name,) + tuple(clause[1:])]

    @classmethod
    def get_fraction_field(cls, notebook_lines, names):
        result = {}
        for name in names:
            result[name] = {}
            if name == 'fraction_type':
                for nl in notebook_lines:
                    fraction = getattr(nl.service, 'fraction', None)
                    if fraction:
                        field = getattr(fraction, 'type', None)
                        result[name][nl.id] = field.id if field else None
                    else:
                        result[name][nl.id] = None
            else:
                for nl in notebook_lines:
                    fraction = getattr(nl.service, 'fraction', None)
                    if fraction:
                        field = getattr(fraction, name, None)
                        result[name][nl.id] = field.id if field else None
                    else:
                        result[name][nl.id] = None
        return result

    @classmethod
    def search_fraction_field(cls, name, clause):
        if name == 'fraction_type':
            name = 'type'
        return [('service.fraction.' + name,) + tuple(clause[1:])]

    @classmethod
    def get_sample_field(cls, notebook_lines, names):
        result = {}
        for name in names:
            result[name] = {}
            for nl in notebook_lines:
                result[name][nl.id] = None
                fraction = getattr(nl.service, 'fraction', None)
                if fraction:
                    sample = getattr(fraction, 'sample', None)
                    if sample:
                        field = getattr(fraction, name, None)
                        if name in ('label', 'date', 'date2'):
                            result[name][nl.id] = field
                        else:
                            result[name][nl.id] = field.id if field else None
        return result

    @classmethod
    def search_sample_field(cls, name, clause):
        return [('service.fraction.sample.' + name,) + tuple(clause[1:])]

    def get_rec_name(self, name):
        if self.analysis:
            return self.analysis.rec_name

    @classmethod
    def search_rec_name(cls, name, clause):
        return [('analysis',) + tuple(clause[1:])]

    @classmethod
    def view_attributes(cls):
        return [('/tree', 'colors',
                If(Bool(Eval('report_date')), 'red', 'black'))]

    @classmethod
    def fields_view_get(cls, view_id=None, view_type='form'):
        pool = Pool()
        User = pool.get('res.user')
        Config = pool.get('lims.configuration')
        UiView = pool.get('ir.ui.view')

        result = super(LimsNotebookLine, cls).fields_view_get(view_id=view_id,
            view_type=view_type)

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
                    'annulled', 'annulment_date'):
                fields.add(field)
            xml += '</tree>'
            result['arch'] = xml
            result['fields'] = cls.fields_get(fields_names=list(fields))
        return result

    @fields.depends('result', 'converted_result', 'converted_result_modifier',
        'backup', 'verification', 'uncertainty', 'end_date')
    def on_change_result(self):
        self.converted_result = None
        self.converted_result_modifier = 'eq'
        self.backup = None
        self.verification = None
        self.uncertainty = None
        self.end_date = None

    @fields.depends('accepted', 'report', 'annulled', 'result',
        'converted_result', 'literal_result', 'result_modifier',
        'converted_result_modifier', 'end_date', 'acceptance_date')
    def on_change_accepted(self):
        self.not_accepted_message = ''
        if self.accepted:
            if not self.report:
                self.accepted = False
                self.not_accepted_message = self.raise_user_error(
                    'not_accepted_1', raise_exception=False)
            elif self.annulled:
                self.accepted = False
                self.not_accepted_message = self.raise_user_error(
                    'not_accepted_2', raise_exception=False)
            elif not self.end_date:
                self.accepted = False
                self.not_accepted_message = self.raise_user_error(
                    'not_accepted_3', raise_exception=False)
            elif not (self.result or self.converted_result
                    or self.literal_result
                    or self.result_modifier in
                    ('nd', 'pos', 'neg', 'ni', 'abs', 'pre')
                    or self.converted_result_modifier in
                    ('nd', 'pos', 'neg', 'ni', 'abs', 'pre')):
                self.accepted = False
                self.not_accepted_message = self.raise_user_error(
                    'not_accepted_4', raise_exception=False)
            else:
                if (self.converted_result and self.converted_result_modifier
                        not in ('ni', 'eq', 'low')):
                    self.accepted = False
                    self.not_accepted_message = self.raise_user_error(
                        'not_accepted_5', raise_exception=False)
                elif (self.result and self.result_modifier
                        not in ('ni', 'eq', 'low')):
                    self.accepted = False
                    self.not_accepted_message = self.raise_user_error(
                        'not_accepted_6', raise_exception=False)
                elif (self.result_modifier == 'ni' and
                        not self.literal_result and
                        (not self.converted_result_modifier or
                            not self.converted_result) and
                        self.converted_result_modifier != 'nd'):
                    self.accepted = False
                    self.not_accepted_message = self.raise_user_error(
                        'not_accepted_7', raise_exception=False)
                else:
                    self.acceptance_date = datetime.now()
        else:
            LimsResultsReportVersionDetailLine = Pool().get(
                'lims.results_report.version.detail.line')
            report_lines = LimsResultsReportVersionDetailLine.search([
                ('notebook_line', '=', self.id),
                ('report_version_detail.state', '!=', 'annulled'),
                ])
            if report_lines:
                self.accepted = True
                report_detail = report_lines[0].report_version_detail
                self.not_accepted_message = self.raise_user_error('accepted_1',
                    (report_detail.report_version.results_report.number,),
                    raise_exception=False)
            else:
                self.acceptance_date = None

    @fields.depends('result_modifier', 'annulled', 'annulment_date', 'report')
    def on_change_result_modifier(self):
        if self.result_modifier == 'na' and not self.annulled:
            self.annulled = True
            self.annulment_date = datetime.now()
            self.report = False
        elif self.result_modifier != 'na' and self.annulled:
            self.annulled = False
            self.annulment_date = None
            self.report = True

    @classmethod
    def get_typification_field(cls, notebook_lines, names):
        LimsTypification = Pool().get('lims.typification')
        result = dict((name, {}) for name in names)
        for nl in notebook_lines:
            typifications = LimsTypification.search([
                ('product_type', '=', nl.notebook.product_type.id),
                ('matrix', '=', nl.notebook.matrix.id),
                ('analysis', '=', nl.analysis.id),
                ('method', '=', nl.method.id),
                ('valid', '=', True),
                ])
            typification = (typifications[0] if len(typifications) == 1
                else None)
            for name in names:
                if typification:
                    result[name][nl.id] = getattr(typification, name, None)
                else:
                    if name == 'report_type':
                        result[name][nl.id] = 'normal'
                    elif name == 'report_result_type':
                        result[name][nl.id] = 'result'
                    elif name == 'check_result_limits':
                        result[name][nl.id] = False
                    else:
                        result[name][nl.id] = None
        return result

    @classmethod
    def search_typification_field(cls, name, clause):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Notebook = pool.get('lims.notebook')
        Fraction = pool.get('lims.fraction')
        LimsSample = pool.get('lims.sample')
        LimsTypification = pool.get('lims.typification')

        operator_ = clause[1:2][0]
        cursor.execute('SELECT nl.id '
            'FROM "' + cls._table + '" nl '
                'INNER JOIN "' + Notebook._table + '" n '
                'ON nl.notebook = n.id '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON n.fraction = f.id '
                'INNER JOIN "' + LimsSample._table + '" s '
                'ON f.sample = s.id '
                'INNER JOIN "' + LimsTypification._table + '" t '
                'ON (nl.analysis = t.analysis AND nl.method = t.method '
                'AND s.product_type = t.product_type AND t.matrix = t.matrix) '
            'WHERE t.valid = TRUE '
                'AND t.' + name + ' ' + operator_ + ' %s',
            clause[2:3])
        return [('id', 'in', [x[0] for x in cursor.fetchall()])]

    @fields.depends('method')
    def on_change_with_results_estimated_waiting(self, name=None):
        if self.method:
            return self.method.results_estimated_waiting
        return None

    @classmethod
    def get_results_estimated_date(cls, notebook_lines, name):
        result = {}
        for nl in notebook_lines:
            result[nl.id] = None
            detail = getattr(nl, 'analysis_detail', None)
            if not detail:
                continue
            confirmation_date = getattr(detail, 'confirmation_date', None)
            if not confirmation_date:
                continue
            estimated_waiting = getattr(nl, 'results_estimated_waiting', None)
            if not estimated_waiting:
                continue
            result[nl.id] = cls._get_results_estimated_date(confirmation_date,
                estimated_waiting)
        return result

    @staticmethod
    def _get_results_estimated_date(confirmation_date, estimated_waiting):
        date = confirmation_date
        number = 0
        while number < estimated_waiting:
            date += timedelta(1)
            if date.weekday() < 5:
                number += 1
        return date

    @fields.depends('analysis')
    def on_change_with_method_domain(self, name=None):
        methods = []
        if self.analysis and self.analysis.methods:
            methods = [m.id for m in self.analysis.methods]
        return methods

    @fields.depends('analysis', 'laboratory')
    def on_change_with_device_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        LimsAnalysisDevice = Pool().get('lims.analysis.device')

        if not self.analysis or not self.laboratory:
            return []

        cursor.execute('SELECT DISTINCT(device) '
            'FROM "' + LimsAnalysisDevice._table + '" '
            'WHERE analysis = %s  '
                'AND laboratory = %s',
            (self.analysis.id, self.laboratory.id))
        res = cursor.fetchall()
        if not res:
            return []
        return [x[0] for x in res]


class LimsNotebookLineAllFields(ModelSQL, ModelView):
    'Laboratory Notebook Line'
    __name__ = 'lims.notebook.line.all_fields'

    line = fields.Many2One('lims.notebook.line', 'Notebook Line')
    fraction = fields.Many2One('lims.fraction', 'Fraction', readonly=True)
    fraction_type = fields.Many2One('lims.fraction.type', 'Fraction type',
        readonly=True)
    party = fields.Many2One('party.party', 'Party', readonly=True)
    party_code = fields.Char('Party', readonly=True)
    product_type = fields.Many2One('lims.product.type', 'Product type',
        readonly=True)
    matrix = fields.Many2One('lims.matrix', 'Matrix', readonly=True)
    label = fields.Char('Label', readonly=True)
    date = fields.DateTime('Date', readonly=True)
    analysis = fields.Many2One('lims.analysis', 'Analysis', readonly=True)
    repetition = fields.Integer('Repetition', readonly=True)
    start_date = fields.Date('Start date', readonly=True)
    end_date = fields.Date('End date', readonly=True)
    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        readonly=True)
    method = fields.Many2One('lims.lab.method', 'Method', readonly=True)
    device = fields.Many2One('lims.lab.device', 'Device', readonly=True)
    service = fields.Many2One('lims.service', 'Service', readonly=True)
    analysis_origin = fields.Char('Analysis origin', readonly=True)
    urgent = fields.Boolean('Urgent', readonly=True)
    priority = fields.Integer('Priority', readonly=True)
    report_date = fields.Date('Date agreed for result', readonly=True)
    initial_concentration = fields.Char('Initial concentration', readonly=True)
    final_concentration = fields.Char('Final concentration', readonly=True)
    laboratory_professionals = fields.Function(fields.Many2Many(
        'lims.laboratory.professional', None, None,
        'Preparation professionals'), 'get_line_field',
        searcher='search_line_field')
    initial_unit = fields.Many2One('product.uom', 'Initial unit',
        readonly=True)
    final_unit = fields.Many2One('product.uom', 'Final unit', readonly=True)
    result_modifier = fields.Selection([
        ('eq', '='),
        ('low', '<'),
        ('nd', 'nd'),
        ('na', 'na'),
        ('pos', 'Positive'),
        ('neg', 'Negative'),
        ('ni', 'ni'),
        ('abs', 'Absence'),
        ('pre', 'Presence'),
        ], 'Result modifier', readonly=True)
    converted_result_modifier = fields.Selection([
        ('eq', '='),
        ('low', '<'),
        ('nd', 'nd'),
        ('pos', 'Positive'),
        ('neg', 'Negative'),
        ('ni', 'ni'),
        ], 'Converted result modifier', readonly=True)
    result_modifier_string = result_modifier.translated('result_modifier')
    converted_result_modifier_string = converted_result_modifier.translated(
        'converted_result_modifier')
    result = fields.Char('Result', readonly=True)
    converted_result = fields.Char('Converted result', readonly=True)
    detection_limit = fields.Char('Detection limit', readonly=True)
    quantification_limit = fields.Char('Quantification limit', readonly=True)
    chromatogram = fields.Char('Chromatogram', readonly=True)
    professionals = fields.Function(fields.One2Many(
        'lims.notebook.line.professional', None,
        'Analytic professionals'), 'get_line_field',
        searcher='search_line_field')
    comments = fields.Text('Entry comments', readonly=True)
    theoretical_concentration = fields.Char('Theoretical concentration',
        readonly=True)
    concentration_level = fields.Many2One('lims.concentration.level',
        'Concentration level', readonly=True)
    decimals = fields.Integer('Decimals', readonly=True)
    backup = fields.Char('Backup', readonly=True)
    reference = fields.Char('Reference', readonly=True)
    literal_result = fields.Char('Literal result', readonly=True)
    rm_correction_formula = fields.Char('RM Correction Formula', readonly=True)
    report = fields.Boolean('Report', readonly=True)
    uncertainty = fields.Char('Uncertainty', readonly=True)
    verification = fields.Char('Verification', readonly=True)
    dilution_factor = fields.Float('Dilution factor', readonly=True)
    accepted = fields.Boolean('Accepted', readonly=True)
    acceptance_date = fields.DateTime('Acceptance date', readonly=True)
    annulled = fields.Boolean('Annulled', readonly=True)
    annulment_date = fields.DateTime('Annulment date', readonly=True)
    results_report = fields.Many2One('lims.results_report', 'Results Report',
        readonly=True)
    planification = fields.Many2One('lims.planification', 'Planification',
        readonly=True)
    confirmation_date = fields.Date('Confirmation date', readonly=True)
    results_estimated_waiting = fields.Integer(
        'Estimated number of days for results')
    results_estimated_date = fields.Function(fields.Date(
        'Estimated date of result'), 'get_line_field')
    department = fields.Many2One('company.department', 'Department',
        readonly=True)

    @classmethod
    def __setup__(cls):
        super(LimsNotebookLineAllFields, cls).__setup__()
        cls._order.insert(0, ('fraction', 'DESC'))
        cls._order.insert(1, ('analysis', 'ASC'))
        cls._order.insert(2, ('repetition', 'ASC'))

    @staticmethod
    def table_query():
        pool = Pool()
        line = pool.get('lims.notebook.line').__table__()
        detail = pool.get('lims.entry.detail.analysis').__table__()
        service = pool.get('lims.service').__table__()
        fraction = pool.get('lims.fraction').__table__()
        sample = pool.get('lims.sample').__table__()
        entry = pool.get('lims.entry').__table__()
        party = pool.get('party.party').__table__()

        join1 = Join(line, service)
        join1.condition = join1.right.id == line.service
        join2 = Join(join1, fraction)
        join2.condition = join2.right.id == join1.right.fraction
        join3 = Join(join2, sample)
        join3.condition = join3.right.id == join2.right.sample
        join4 = Join(join3, entry)
        join4.condition = join4.right.id == join3.right.entry
        join5 = Join(join4, party)
        join5.condition = join5.right.id == join4.right.party
        join6 = Join(join5, detail)
        join6.condition = join6.right.id == join1.left.analysis_detail

        columns = [
            line.id,
            line.create_uid,
            line.create_date,
            line.write_uid,
            line.write_date,
            line.id.as_('line'),
            service.fraction,
            entry.party,
            party.code.as_('party_code'),
            sample.product_type,
            sample.matrix,
            sample.label,
            fraction.type.as_('fraction_type'),
            sample.date,
            line.analysis,
            line.repetition,
            line.start_date,
            line.end_date,
            line.laboratory,
            line.method,
            line.device,
            line.service,
            line.analysis_origin,
            service.urgent,
            service.priority,
            service.report_date,
            line.initial_concentration,
            line.final_concentration,
            line.initial_unit,
            line.final_unit,
            line.result_modifier,
            line.converted_result_modifier,
            line.result,
            line.converted_result,
            line.detection_limit,
            line.quantification_limit,
            line.dilution_factor,
            line.chromatogram,
            line.comments,
            line.theoretical_concentration,
            line.concentration_level,
            line.decimals,
            line.backup,
            line.reference,
            line.literal_result,
            line.rm_correction_formula,
            line.report,
            line.uncertainty,
            line.verification,
            line.accepted,
            line.acceptance_date,
            line.annulled,
            line.annulment_date,
            line.results_report,
            line.planification,
            detail.confirmation_date,
            line.results_estimated_waiting,
            line.department,
            ]
        where = Literal(True)
        return join6.select(*columns, where=where)

    @classmethod
    def get_line_field(cls, notebook_lines, names):
        result = dict((name, {}) for name in names)
        for nl in notebook_lines:
            for name in names:
                field = getattr(nl.line, name, None)
                if isinstance(field, ModelSQL):
                    result[name][nl.id] = field.id if field else None
                elif isinstance(field, tuple):
                    result[name][nl.id] = [f.id for f in field]
                else:
                    result[name][nl.id] = field
        return result

    @classmethod
    def search_line_field(cls, name, clause):
        return [('line.' + name,) + tuple(clause[1:])]


class LimsNotebookLineLaboratoryProfessional(ModelSQL):
    'Laboratory Notebook Line - Laboratory Professional'
    __name__ = 'lims.notebook.line-laboratory.professional'

    notebook_line = fields.Many2One('lims.notebook.line', 'Notebook Line',
        ondelete='CASCADE', select=True, required=True)
    professional = fields.Many2One('lims.laboratory.professional',
        'Laboratory professional', ondelete='CASCADE', select=True,
        required=True)


class LimsNotebookLineProfessional(ModelSQL, ModelView):
    'Laboratory Notebook Line Professional'
    __name__ = 'lims.notebook.line.professional'

    notebook_line = fields.Many2One('lims.notebook.line', 'Notebook Line',
        ondelete='CASCADE', select=True, required=True)
    professional = fields.Many2One('lims.laboratory.professional',
        'Laboratory professional', required=True)


class LimsEntry(Workflow, ModelSQL, ModelView):
    'Entry'
    __name__ = 'lims.entry'
    _rec_name = 'number'

    number = fields.Char('Number', select=True, readonly=True)
    create_date2 = fields.Function(fields.DateTime('Create Date'),
       'get_create_date2', searcher='search_create_date2')
    date = fields.DateTime('Date')
    date2 = fields.Function(fields.Date('Date'), 'get_date',
        searcher='search_date')
    party = fields.Many2One('party.party', 'Party', required=True,
        states={'readonly': Eval('state') != 'draft'}, depends=['state'])
    invoice_party = fields.Many2One('party.party', 'Invoice party',
        domain=[('id', 'in', Eval('invoice_party_domain'))],
        depends=['invoice_party_domain', 'state'], required=True,
        states={'readonly': Eval('state') != 'draft'})
    invoice_party_view = fields.Function(fields.Many2One('party.party',
        'Invoice party'), 'get_views_field',
        searcher='search_views_field')
    invoice_party_domain = fields.Function(fields.Many2Many('party.party',
        None, None, 'Invoice party domain'),
        'on_change_with_invoice_party_domain')
    invoice_contacts = fields.One2Many('lims.entry.invoice_contacts',
        'entry', 'Invoice contacts')
    report_contacts = fields.One2Many('lims.entry.report_contacts',
        'entry', 'Report contacts')
    acknowledgment_contacts = fields.One2Many(
        'lims.entry.acknowledgment_contacts', 'entry',
        'Acknowledgment contacts')
    carrier = fields.Many2One('carrier', 'Carrier')
    package_type = fields.Many2One('lims.packaging.type', 'Package type')
    package_state = fields.Many2One('lims.packaging.integrity',
        'Package state')
    packages_quantity = fields.Integer('Packages quantity')
    email_report = fields.Boolean('Email report')
    single_sending_report = fields.Boolean('Single sending of report')
    english_report = fields.Boolean('English report')
    no_acknowledgment_of_receipt = fields.Boolean(
        'No acknowledgment of receipt')
    samples = fields.One2Many('lims.sample', 'entry', 'Samples',
        context={
            'entry': Eval('id'), 'party': Eval('party'),
            }, depends=['party'])
    invoice_comments = fields.Text('Invoice comments')
    report_comments = fields.Text('Report comments', translate=True)
    transfer_comments = fields.Text('Transfer comments')
    comments = fields.Text('Comments')
    pending_reason = fields.Many2One('lims.entry.suspension.reason',
        'Pending reason', states={
            'invisible': Not(Bool(Equal(Eval('state'), 'pending'))),
            'required': Bool(Equal(Eval('state'), 'pending')),
            }, depends=['state'])
    state = fields.Selection([
        ('draft', 'Draft'),
        ('ongoing', 'Ongoing'),
        ('pending', 'Administration pending'),
        ('closed', 'Closed'),
        ], 'State', required=True, readonly=True)
    ack_report_cache = fields.Binary('Acknowledgment report cache',
        readonly=True)
    ack_report_format = fields.Char('Acknowledgment report format',
        readonly=True)
    confirmed = fields.Function(fields.Boolean('Confirmed'), 'get_confirmed')
    sent_date = fields.DateTime('Sent date', readonly=True)
    result_cron = fields.Selection([
        ('', ''),
        ('failed_print', 'Failed to print'),
        ('failed_send', 'Failed to send'),
        ('sent', 'Sent'),
        ], 'Result cron', sort=False, readonly=True)

    @classmethod
    def __setup__(cls):
        super(LimsEntry, cls).__setup__()
        cls._order.insert(0, ('number', 'DESC'))
        cls._transitions |= set((
            ('draft', 'ongoing'),
            ('draft', 'pending'),
            ('pending', 'ongoing'),
            ('ongoing', 'closed'),
            ))
        cls._buttons.update({
            'create_sample': {
                'invisible': ~Eval('state').in_(['draft']),
                },
            'confirm': {
                'invisible': ~Eval('state').in_(['draft', 'pending']),
                },
            'on_hold': {
                'invisible': ~Eval('state').in_(['draft']),
                },
            })
        cls._error_messages.update({
            'no_entry_sequence': ('There is no entry sequence for '
                'the work year "%s".'),
            'delete_entry': ('You can not delete entry "%s" because '
                'it is not in draft state'),
            'not_fraction': ('You can not confirm entry "%s" because '
                'has not fractions'),
            'missing_entry_contacts': ('Missing contacts in entry "%s"'),
            'enac_acredited': ('The analysis marked with * are not '
                'covered by the Accreditation.'),
            'english_report': ('Do not forget to load the translations '
                'into English'),
            })

    @staticmethod
    def default_date():
        return datetime.now()

    @staticmethod
    def default_email_report():
        return False

    @staticmethod
    def default_single_sending_report():
        return False

    @staticmethod
    def default_english_report():
        return False

    @staticmethod
    def default_no_acknowledgment_of_receipt():
        return False

    @staticmethod
    def default_result_cron():
        return ''

    @staticmethod
    def default_state():
        return 'draft'

    def get_date(self, name):
        pool = Pool()
        Company = pool.get('company.company')

        date = self.date
        company_id = Transaction().context.get('company')
        if company_id:
            date = Company(company_id).convert_timezone_datetime(date)
        return date.date()

    def get_create_date2(self, name):
        return self.create_date.replace(microsecond=0)

    @classmethod
    def search_date(cls, name, clause):
        pool = Pool()
        Company = pool.get('company.company')
        cursor = Transaction().connection.cursor()

        timezone = None
        company_id = Transaction().context.get('company')
        if company_id:
            timezone = Company(company_id).timezone
        timezone_datetime = 'date::timestamp AT TIME ZONE \'UTC\''
        if timezone:
            timezone_datetime += ' AT TIME ZONE \'' + timezone + '\''

        operator_ = clause[1:2][0]
        cursor.execute('SELECT id '
                'FROM "' + cls._table + '" '
                'WHERE (' + timezone_datetime + ')::date '
                + operator_ + ' %s::date', clause[2:3])
        return [('id', 'in', [x[0] for x in cursor.fetchall()])]

    @classmethod
    def search_create_date2(cls, name, clause):
        cursor = Transaction().connection.cursor()
        operator_ = clause[1:2][0]
        cursor.execute('SELECT id '
                'FROM "' + cls._table + '" '
                'WHERE create_date' + operator_ + ' %s',
                clause[2:3])
        return [('id', 'in', [x[0] for x in cursor.fetchall()])]

    @fields.depends('party', 'invoice_party', 'invoice_contacts',
        'report_contacts', 'acknowledgment_contacts')
    def on_change_party(self):
        pool = Pool()
        ReportContacts = pool.get('lims.entry.report_contacts')
        AcknowledgmentContacts = pool.get('lims.entry.acknowledgment_contacts')

        email = False
        single_sending = False
        english = False
        no_ack = False
        invoice_contacts = []
        a_report_contacts = []
        report_contacts = []
        a_acknowledgment_contacts = []
        acknowledgment_contacts = []
        parties = []
        if self.party:
            parties.append(self.party.id)
        if self.invoice_party:
            parties.append(self.invoice_party.id)

        if self.invoice_contacts:
            for c in self.invoice_contacts:
                if c.contact.party.id in parties:
                    invoice_contacts.append(c)
        if self.report_contacts:
            for c in self.report_contacts:
                if c.contact.party.id in parties:
                    report_contacts.append(c)
                    a_report_contacts.append(c.contact)
        if self.acknowledgment_contacts:
            for c in self.acknowledgment_contacts:
                if c.contact.party.id in parties:
                    acknowledgment_contacts.append(c)
                    a_acknowledgment_contacts.append(c.contact)

        if self.party:
            email = self.party.email_report
            single_sending = self.party.single_sending_report
            english = self.party.english_report
            no_ack = self.party.no_acknowledgment_of_receipt
            if self.party.addresses:
                for c in self.party.addresses:
                    if (c.report_contact_default and c not
                            in a_report_contacts):
                        value = ReportContacts(**ReportContacts.default_get(
                            ReportContacts._fields.keys()))
                        value.contact = c
                        report_contacts.append(value)
                    if (c.acknowledgment_contact_default and c not
                            in a_acknowledgment_contacts):
                        value = AcknowledgmentContacts(
                            **AcknowledgmentContacts.default_get(
                                AcknowledgmentContacts._fields.keys()))
                        value.contact = c
                        acknowledgment_contacts.append(value)

        self.email_report = email
        self.single_sending_report = single_sending
        self.english_report = english
        self.no_acknowledgment_of_receipt = no_ack
        self.invoice_contacts = invoice_contacts
        self.report_contacts = report_contacts
        self.acknowledgment_contacts = acknowledgment_contacts
        if self.party and not self.invoice_party:
            invoice_party_domain = self.on_change_with_invoice_party_domain()
            if len(invoice_party_domain) == 1:
                self.invoice_party = invoice_party_domain[0]
                self.on_change_invoice_party()

    @fields.depends('party', 'invoice_party', 'invoice_contacts',
        'report_contacts', 'acknowledgment_contacts')
    def on_change_invoice_party(self):
        pool = Pool()
        InvoiceContacts = pool.get('lims.entry.invoice_contacts')

        a_invoice_contacts = []
        invoice_contacts = []
        report_contacts = []
        acknowledgment_contacts = []
        parties = []
        if self.party:
            parties.append(self.party.id)
        if self.invoice_party:
            parties.append(self.invoice_party.id)

        if self.invoice_contacts:
            for c in self.invoice_contacts:
                if c.contact.party.id in parties:
                    invoice_contacts.append(c)
                    a_invoice_contacts.append(c.contact)
        if self.report_contacts:
            for c in self.report_contacts:
                if c.contact.party.id in parties:
                    report_contacts.append(c)
        if self.acknowledgment_contacts:
            for c in self.acknowledgment_contacts:
                if c.contact.party.id in parties:
                    acknowledgment_contacts.append(c)

        if self.invoice_party:
            if self.invoice_party.addresses:
                for c in self.invoice_party.addresses:
                    if (c.invoice_contact_default and c not
                            in a_invoice_contacts):
                        value = InvoiceContacts(**InvoiceContacts.default_get(
                            InvoiceContacts._fields.keys()))
                        value.contact = c
                        invoice_contacts.append(value)

        self.invoice_contacts = invoice_contacts
        self.report_contacts = report_contacts
        self.acknowledgment_contacts = acknowledgment_contacts

    @classmethod
    def get_views_field(cls, parties, names):
        result = {}
        for name in names:
            field_name = name[:-5]
            result[name] = {}
            for p in parties:
                field = getattr(p, field_name, None)
                result[name][p.id] = field.id if field else None
        return result

    @classmethod
    def search_views_field(cls, name, clause):
        return [(name[:-5],) + tuple(clause[1:])]

    @fields.depends('party')
    def on_change_with_invoice_party_domain(self, name=None):
        Config = Pool().get('lims.configuration')

        config_ = Config(1)
        parties = []
        if self.party:
            parties.append(self.party.id)
            if config_.invoice_party_relation_type:
                parties.extend([r.to.id for r in self.party.relations
                    if r.type == config_.invoice_party_relation_type])
        return parties

    @classmethod
    def create(cls, vlist):
        pool = Pool()
        LimsLabWorkYear = pool.get('lims.lab.workyear')
        Sequence = pool.get('ir.sequence.strict')

        workyear_id = LimsLabWorkYear.find()
        workyear = LimsLabWorkYear(workyear_id)
        sequence = workyear.get_sequence('entry')
        if not sequence:
            cls.raise_user_error('no_entry_sequence',
                (workyear.rec_name,))

        vlist = [x.copy() for x in vlist]
        for values in vlist:
            values['number'] = Sequence.get_id(sequence.id)
        return super(LimsEntry, cls).create(vlist)

    @classmethod
    def view_attributes(cls):
        return [('/tree', 'colors',
                If(Bool(Eval('confirmed')), 'black', 'red'))]

    @classmethod
    def copy(cls, entries, default=None):
        if default is None:
            default = {}

        new_entries = []
        for entry in entries:
            invoice_contacts = [{
                'contact': c.contact.id,
                } for c in entry.invoice_contacts]
            report_contacts = [{
                'contact': c.contact.id,
                } for c in entry.report_contacts]
            acknowledgment_contacts = [{
                'contact': c.contact.id,
                } for c in entry.acknowledgment_contacts]
            current_default = default.copy()
            current_default['state'] = 'draft'
            current_default['ack_report_cache'] = None
            current_default['ack_report_format'] = None
            current_default['sent_date'] = None
            current_default['result_cron'] = ''
            current_default['invoice_contacts'] = [('create',
                invoice_contacts)]
            current_default['report_contacts'] = [('create',
                report_contacts)]
            current_default['acknowledgment_contacts'] = [('create',
                acknowledgment_contacts)]

            new_entry, = super(LimsEntry, cls).copy([entry],
                default=current_default)
            new_entries.append(new_entry)
        return new_entries

    @classmethod
    @ModelView.button_action('lims.wiz_lims_create_sample')
    def create_sample(cls, entries):
        pass

    @classmethod
    @ModelView.button
    @Workflow.transition('ongoing')
    def confirm(cls, entries):
        for entry in entries:
            entry.check_contacts()
            entry.warn_english_report()
            entry._confirm()

    @classmethod
    def cron_acknowledgment_of_receipt(cls):
        '''
        Cron - Acknowledgment Of Receipt (Samples)
        '''
        logging.getLogger('lims').info(
                'Cron - Acknowledgment Of Receipt (Samples):INIT')
        pool = Pool()
        LimsForwardAcknowledgmentOfReceipt = pool.get(
            'lims.entry.acknowledgment.forward', type='wizard')
        LimsEntry = pool.get('lims.entry')
        entries = LimsEntry.search([
            ('result_cron', '!=', 'sent'),
            ('no_acknowledgment_of_receipt', '=', False),
            ('state', '=', 'ongoing'),
            ])
        session_id, _, _ = LimsForwardAcknowledgmentOfReceipt.create()
        acknowledgment_forward = LimsForwardAcknowledgmentOfReceipt(session_id)
        with Transaction().set_context(active_ids=[entry.id for entry
                in entries]):
            data = acknowledgment_forward.transition_start()
        if data:
            logging.getLogger('lims').info('data:%s' % data)  # debug
        logging.getLogger('lims').info(
                'Cron - Acknowledgment Of Receipt (Samples):END')

    @classmethod
    @ModelView.button
    def on_hold(cls, entries):
        pool = Pool()
        LimsEntrySuspensionReason = pool.get('lims.entry.suspension.reason')

        for entry in entries:
            entry.check_contacts()
        default_pending_reason = None
        reasons = LimsEntrySuspensionReason.search([
            ('by_default', '=', True),
            ])
        if reasons:
            default_pending_reason = reasons[0].id
        cls.pending_reason.states['required'] = False
        cls.write(entries, {
            'state': 'pending',
            'pending_reason': default_pending_reason,
            })
        cls.pending_reason.states['required'] = (
            Bool(Equal(Eval('state'), 'pending')))

    @classmethod
    @Workflow.transition('closed')
    def close(cls, entries):
        pass

    def check_contacts(self):
        if (not self.invoice_contacts
                or not self.report_contacts
                or not self.acknowledgment_contacts):
            self.raise_user_error('missing_entry_contacts', (self.rec_name,))

    def warn_english_report(self):
        if self.english_report:
            self.raise_user_warning('lims_english_report@%s' %
                    self.number, 'english_report')

    def print_report(self):
        if self.ack_report_cache:
            return
        LimsAcknowledgmentOfReceipt = Pool().get(
            'lims.entry.acknowledgment.report', type='report')
        success = False
        try:
            LimsAcknowledgmentOfReceipt.execute([self.id], {})
            success = True
        except Exception:
            logging.getLogger('lims').error(
                'Unable to print report Acknowledgment of receipt for '
                'Entry:%s' % (self.number))
        return success

    def mail_acknowledgment_of_receipt(self):
        if not self.ack_report_cache:
            return

        from_addr = config.get('email', 'from')
        to_addrs = [c.contact.email for c in self.acknowledgment_contacts]
        if not (from_addr and to_addrs):
            return

        subject, body = self.subject_body()
        attachment_data = self.attachment()
        msg = self.create_msg(from_addr, to_addrs, subject,
            body, attachment_data)
        return self.send_msg(from_addr, to_addrs, msg)

    def subject_body(self):
        pool = Pool()
        Config = pool.get('lims.configuration')
        User = pool.get('res.user')
        Lang = pool.get('ir.lang')

        config = Config(1)

        lang = User(Transaction().user).language
        if not lang:
            lang, = Lang.search([
                    ('code', '=', 'en'),
                    ], limit=1)

        with Transaction().set_context(language=lang.code):
            subject = unicode('%s %s' % (config.mail_ack_subject,
                    self.number)).strip()
            body = unicode(config.mail_ack_body)

        return subject, body

    def attachment(self):
        data = {
            'content': self.ack_report_cache,
            'format': self.ack_report_format,
            'mimetype': self.ack_report_format == 'pdf' and 'pdf'
                    or 'vnd.oasis.opendocument.text',
            'filename': (unicode(self.number) + '.'
                    + str(self.ack_report_format)),
            'name': unicode(self.number),
            }
        return data

    def create_msg(self, from_addr, to_addrs, subject, body, attachment_data):
        if not to_addrs:
            return None

        msg = MIMEMultipart()
        msg['From'] = from_addr
        hidden = True  # TODO: HARDCODE!
        if not hidden:
            msg['To'] = ', '.join(to_addrs)
        msg['Subject'] = subject

        msg_body = MIMEBase('text', 'plain')
        msg_body.set_payload(body.encode('UTF-8'), 'UTF-8')
        msg.attach(msg_body)

        attachment = MIMEApplication(
            attachment_data['content'],
            Name=attachment_data['filename'], _subtype="pdf")
        attachment.add_header('content-disposition', 'attachment',
            filename=('utf-8', '', attachment_data['filename']))
        msg.attach(attachment)

        return msg

    def send_msg(self, from_addr, to_addrs, msg):
        to_addrs = list(set(to_addrs))
        success = False
        try:
            server = get_smtp_server()
            server.sendmail(from_addr, to_addrs, msg.as_string())
            server.quit()
            success = True
        except Exception:
            logging.getLogger('lims').error(
                'Unable to deliver mail for entry %s' % (self.number))
        return success

    def _confirm(self):
        LimsFraction = Pool().get('lims.fraction')
        fractions = LimsFraction.search([
            ('entry', '=', self.id),
            ('confirmed', '=', False),
            ], order=[
            ('sample', 'ASC'), ('id', 'ASC'),
            ])
        if not fractions:
            Company = Pool().get('company.company')
            companies = Company.search([])
            if self.party.id not in [c.party.id for c in companies]:
                self.raise_user_error('not_fraction', (self.rec_name,))
        LimsFraction.confirm(fractions)

    @classmethod
    def check_delete(cls, entries):
        for entry in entries:
            if entry.state != 'draft':
                cls.raise_user_error('delete_entry', (entry.rec_name,))

    @classmethod
    def delete(cls, entries):
        cls.check_delete(entries)
        super(LimsEntry, cls).delete(entries)

    def get_confirmed(self, name=None):
        if not self.samples:
            return False
        for sample in self.samples:
            if not sample.fractions:
                return False
            for fraction in sample.fractions:
                if not fraction.confirmed:
                    return False
        return True

    @classmethod
    def order_create_date2(cls, tables):
        return cls.create_date.convert_order('create_date', tables, cls)


class LimsEntryInvoiceContact(ModelSQL, ModelView):
    'Entry Invoice Contact'
    __name__ = 'lims.entry.invoice_contacts'

    entry = fields.Many2One('lims.entry', 'Entry',
        ondelete='CASCADE', select=True, required=True)
    contact = fields.Many2One('party.address', 'Contact', required=True,
        domain=[
            ('party', 'in', [Eval('_parent_entry', {}).get('party'),
                Eval('_parent_entry', {}).get('invoice_party')]),
            ('invoice_contact', '=', True),
        ])


class LimsEntryReportContact(ModelSQL, ModelView):
    'Entry Report Contact'
    __name__ = 'lims.entry.report_contacts'

    entry = fields.Many2One('lims.entry', 'Entry',
        ondelete='CASCADE', select=True, required=True)
    contact = fields.Many2One('party.address', 'Contact', required=True,
        domain=[
            ('party', 'in', [Eval('_parent_entry', {}).get('party'),
                Eval('_parent_entry', {}).get('invoice_party')]),
            ('report_contact', '=', True),
        ])


class LimsEntryAcknowledgmentContact(ModelSQL, ModelView):
    'Entry Acknowledgment Contact'
    __name__ = 'lims.entry.acknowledgment_contacts'

    entry = fields.Many2One('lims.entry', 'Entry',
        ondelete='CASCADE', select=True, required=True)
    contact = fields.Many2One('party.address', 'Contact', required=True,
        domain=[
            ('party', 'in', [Eval('_parent_entry', {}).get('party'),
                Eval('_parent_entry', {}).get('invoice_party')]),
            ('acknowledgment_contact', '=', True),
        ])


class LimsAnalysisFamily(ModelSQL, ModelView):
    'Analysis Family'
    __name__ = 'lims.analysis.family'
    _rec_name = 'description'

    code = fields.Char('Code', required=True)
    description = fields.Char('Description', required=True)
    party = fields.Many2One('party.party', 'Certificant party')
    certificants = fields.One2Many('lims.analysis.family.certificant',
        'family', 'Product Type - Matrix')

    @classmethod
    def __setup__(cls):
        super(LimsAnalysisFamily, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code),
                'Analysis family code must be unique'),
            ]

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


class LimsAnalysisFamilyCertificant(ModelSQL, ModelView):
    'Product Type - Matrix'
    __name__ = 'lims.analysis.family.certificant'

    family = fields.Many2One('lims.analysis.family', 'Family', required=True)
    product_type = fields.Many2One('lims.product.type', 'Product type',
        required=True)
    matrix = fields.Many2One('lims.matrix', 'Matrix', required=True)

    @classmethod
    def __setup__(cls):
        super(LimsAnalysisFamilyCertificant, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('product_matrix_uniq',
                Unique(t, t.family, t.product_type, t.matrix),
                'This record already exists'),
            ]


class LimsZone(ModelSQL, ModelView):
    'Zone/Region'
    __name__ = 'lims.zone'
    _rec_name = 'description'

    code = fields.Char('Code', required=True)
    description = fields.Char('Description', required=True)
    restricted_entry = fields.Boolean('Restricted entry')

    @classmethod
    def __setup__(cls):
        super(LimsZone, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code),
                'Zone code must be unique'),
            ]

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


class LimsVariety(ModelSQL, ModelView):
    'Variety'
    __name__ = 'lims.variety'
    _rec_name = 'description'

    code = fields.Char('Code', required=True)
    description = fields.Char('Description', required=True)
    varieties = fields.One2Many('lims.matrix.variety', 'variety',
        'Product Type - Matrix')

    @classmethod
    def __setup__(cls):
        super(LimsVariety, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code),
                'Variety code must be unique'),
            ]

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


class LimsMatrixVariety(ModelSQL, ModelView):
    'Product Type - Matrix - Variety'
    __name__ = 'lims.matrix.variety'

    product_type = fields.Many2One('lims.product.type', 'Product type',
        required=True)
    matrix = fields.Many2One('lims.matrix', 'Matrix', required=True)
    variety = fields.Many2One('lims.variety', 'Variety', required=True)


class LimsPackagingIntegrity(ModelSQL, ModelView):
    'Packaging Integrity'
    __name__ = 'lims.packaging.integrity'
    _rec_name = 'description'

    code = fields.Char('Code', required=True)
    description = fields.Char('Description', required=True, translate=True)

    @classmethod
    def __setup__(cls):
        super(LimsPackagingIntegrity, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code),
                'Packaging integrity code must be unique'),
            ]

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


class LimsEntrySuspensionReason(ModelSQL, ModelView):
    'Entry Suspension Reason'
    __name__ = 'lims.entry.suspension.reason'
    _rec_name = 'description'

    code = fields.Char('Code', required=True)
    description = fields.Char('Description', required=True)
    by_default = fields.Boolean('By default')

    @classmethod
    def __setup__(cls):
        super(LimsEntrySuspensionReason, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code),
                'Suspension reason code must be unique'),
            ]
        cls._error_messages.update({
            'default_suspension_reason': 'There is already a default '
                'suspension reason',
            })

    @staticmethod
    def default_by_default():
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

    @classmethod
    def validate(cls, reasons):
        super(LimsEntrySuspensionReason, cls).validate(reasons)
        for sr in reasons:
            sr.check_default()

    def check_default(self):
        if self.by_default:
            reasons = self.search([
                ('by_default', '=', True),
                ('id', '!=', self.id),
                ])
            if reasons:
                self.raise_user_error('default_suspension_reason')


class LimsEntryDetailAnalysis(ModelSQL, ModelView):
    'Entry Detail Analysis'
    __name__ = 'lims.entry.detail.analysis'

    service = fields.Many2One('lims.service', 'Service', required=True,
        ondelete='CASCADE', select=True, readonly=True)
    service_view = fields.Function(fields.Many2One('lims.service',
        'Service', states={'invisible': Not(Bool(Eval('_parent_service')))}),
        'on_change_with_service_view')
    create_date2 = fields.Function(fields.DateTime('Create Date'),
       'get_create_date2', searcher='search_create_date2')
    fraction = fields.Function(fields.Many2One('lims.fraction', 'Fraction'),
        'get_service_field', searcher='search_service_field')
    sample = fields.Function(fields.Many2One('lims.sample', 'Sample'),
        'get_service_field', searcher='search_service_field')
    entry = fields.Function(fields.Many2One('lims.entry', 'Entry'),
        'get_service_field', searcher='search_service_field')
    party = fields.Function(fields.Many2One('party.party', 'Party'),
        'get_service_field', searcher='search_service_field')
    analysis = fields.Many2One('lims.analysis', 'Analysis', required=True,
        states={'readonly': True})
    analysis_type = fields.Function(fields.Selection([
        ('analysis', 'Analysis'),
        ('set', 'Set'),
        ('group', 'Group'),
        ], 'Type', sort=False),
        'on_change_with_analysis_type')
    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        states={'readonly': True})
    method = fields.Many2One('lims.lab.method', 'Method',
        states={'readonly': True})
    device = fields.Many2One('lims.lab.device', 'Device',
        states={'readonly': True})
    analysis_origin = fields.Char('Analysis origin',
        states={'readonly': True})
    confirmation_date = fields.Date('Confirmation date', readonly=True)
    report_grouper = fields.Integer('Report Grouper')
    results_report = fields.Function(fields.Many2One('lims.results_report',
        'Results Report'), 'get_results_report')
    report = fields.Function(fields.Boolean('Report'), 'get_report',
        searcher='search_report')

    @classmethod
    def __setup__(cls):
        super(LimsEntryDetailAnalysis, cls).__setup__()
        cls._order.insert(0, ('service', 'DESC'))
        cls._error_messages.update({
            'delete_detail': ('You can not delete the analysis detail because '
                'its fraction is confirmed'),
            })

    @classmethod
    def copy(cls, details, default=None):
        if default is None:
            default = {}
        current_default = default.copy()
        current_default['confirmation_date'] = None
        return super(LimsEntryDetailAnalysis, cls).copy(details,
            default=current_default)

    @classmethod
    def check_delete(cls, details):
        for detail in details:
            if detail.fraction and detail.fraction.confirmed:
                cls.raise_user_error('delete_detail')

    @classmethod
    def delete(cls, details):
        if Transaction().user != 0:
            cls.check_delete(details)
        super(LimsEntryDetailAnalysis, cls).delete(details)

    @classmethod
    def create_notebook_lines(cls, details, fraction):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Typification = pool.get('lims.typification')
        Method = pool.get('lims.lab.method')
        AnalysisLaboratory = pool.get('lims.analysis-laboratory')
        Fraction = pool.get('lims.fraction')
        Notebook = pool.get('lims.notebook')
        Company = pool.get('company.company')

        lines_create = []

        for detail in details:
            cursor.execute('SELECT default_repetitions, '
                    'initial_concentration, final_concentration, start_uom, '
                    'end_uom, detection_limit, quantification_limit, '
                    'calc_decimals, report '
                'FROM "' + Typification._table + '" '
                'WHERE product_type = %s '
                    'AND matrix = %s '
                    'AND analysis = %s '
                    'AND method = %s '
                    'AND valid',
                (fraction.product_type.id, fraction.matrix.id,
                    detail.analysis.id, detail.method.id))
            typifications = cursor.fetchall()
            typification = (typifications[0] if len(typifications) == 1
                else None)
            if typification:
                repetitions = typification[0]
                initial_concentration = unicode(typification[1] or '')
                final_concentration = unicode(typification[2] or '')
                initial_unit = typification[3]
                final_unit = typification[4]
                detection_limit = str(typification[5])
                quantification_limit = str(typification[6])
                decimals = typification[7]
                report = typification[8]
            else:
                repetitions = 0
                initial_concentration = None
                final_concentration = None
                initial_unit = None
                final_unit = None
                detection_limit = None
                quantification_limit = None
                decimals = 2
                report = False

            cursor.execute('SELECT results_estimated_waiting '
                'FROM "' + Method._table + '" '
                'WHERE id = %s', (detail.method.id,))
            res = cursor.fetchone()
            results_estimated_waiting = res and res[0] or None

            cursor.execute('SELECT department '
                'FROM "' + AnalysisLaboratory._table + '" '
                'WHERE analysis = %s '
                    'AND laboratory = %s',
                    (detail.analysis.id, detail.laboratory.id))
            res = cursor.fetchone()
            department = res and res[0] or None

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
                    'decimals': decimals,
                    'report': report,
                    'results_estimated_waiting': results_estimated_waiting,
                    'department': department,
                    }
                lines_create.append(notebook_line)

        if not lines_create:
            companies = Company.search([])
            if fraction.party.id not in [c.party.id for c in companies]:
                Fraction.raise_user_error('not_services',
                    (fraction.rec_name,))

        with Transaction().set_user(0):
            notebook = Notebook.search([
                ('fraction', '=', fraction.id),
                ])
            Notebook.write(notebook, {
                'lines': [('create', lines_create)],
                })

    @staticmethod
    def default_service_view():
        if (Transaction().context.get('service') > 0):
            return Transaction().context.get('service')
        return None

    @fields.depends('service')
    def on_change_with_service_view(self, name=None):
        if self.service:
            return self.service.id
        return None

    @staticmethod
    def default_fraction():
        if (Transaction().context.get('fraction') > 0):
            return Transaction().context.get('fraction')
        return None

    @staticmethod
    def default_sample():
        if (Transaction().context.get('sample') > 0):
            return Transaction().context.get('sample')
        return None

    @staticmethod
    def default_entry():
        if (Transaction().context.get('entry') > 0):
            return Transaction().context.get('entry')
        return None

    @staticmethod
    def default_party():
        if (Transaction().context.get('party') > 0):
            return Transaction().context.get('party')
        return None

    @staticmethod
    def default_report_grouper():
        return 0

    @fields.depends('analysis')
    def on_change_with_analysis_type(self, name=None):
        if self.analysis:
            return self.analysis.type
        return ''

    @classmethod
    def get_service_field(cls, details, names):
        result = {}
        for name in names:
            result[name] = {}
            for d in details:
                field = getattr(d.service, name, None)
                result[name][d.id] = field.id if field else None
        return result

    @classmethod
    def get_create_date2(cls, details, name):
        result = {}
        for d in details:
            result[d.id] = d.create_date.replace(microsecond=0)
        return result

    @classmethod
    def search_create_date2(cls, name, clause):
        cursor = Transaction().connection.cursor()
        operator_ = clause[1:2][0]
        cursor.execute('SELECT id '
                'FROM "' + cls._table + '" '
                'WHERE create_date' + operator_ + ' %s',
                clause[2:3])
        return [('id', 'in', [x[0] for x in cursor.fetchall()])]

    @classmethod
    def search_service_field(cls, name, clause):
        return [('service.' + name,) + tuple(clause[1:])]

    @classmethod
    def order_create_date2(cls, tables):
        return cls.create_date.convert_order('create_date', tables, cls)

    def _order_service_field(name):
        def order_field(tables):
            Service = Pool().get('lims.service')
            field = Service._fields[name]
            table, _ = tables[None]
            service_tables = tables.get('service')
            if service_tables is None:
                service = Service.__table__()
                service_tables = {
                    None: (service, service.id == table.service),
                    }
                tables['service'] = service_tables
            return field.convert_order(name, service_tables, Service)
        return staticmethod(order_field)
    # Redefine convert_order function with 'order_%s' % field
    order_fraction = _order_service_field('fraction')
    order_sample = _order_service_field('sample')
    order_entry = _order_service_field('entry')
    order_party = _order_service_field('party')

    @classmethod
    def get_results_report(cls, details, name):
        cursor = Transaction().connection.cursor()
        LimsNotebookLine = Pool().get('lims.notebook.line')

        result = {}
        for d in details:
            cursor.execute('SELECT results_report '
                'FROM "' + LimsNotebookLine._table + '" '
                'WHERE analysis_detail = %s '
                    'AND results_report IS NOT NULL '
                'ORDER BY id ASC LIMIT 1',
                (d.id,))
            value = cursor.fetchone()
            result[d.id] = value[0] if value else None
        return result

    @classmethod
    def get_report(cls, details, name):
        cursor = Transaction().connection.cursor()
        LimsNotebookLine = Pool().get('lims.notebook.line')

        result = {}
        for d in details:
            cursor.execute('SELECT report '
                'FROM "' + LimsNotebookLine._table + '" '
                'WHERE analysis_detail = %s '
                'ORDER BY id DESC LIMIT 1',
                (d.id,))
            value = cursor.fetchone()
            result[d.id] = value[0] if value else False
        return result

    @classmethod
    def search_report(cls, name, clause):
        cursor = Transaction().connection.cursor()
        LimsNotebookLine = Pool().get('lims.notebook.line')

        cursor.execute('SELECT detail.id '
            'FROM "' + cls._table + '" detail '
                'INNER JOIN ( '
                    'SELECT DISTINCT ON (analysis_detail) '
                    'analysis_detail, report '
                    'FROM "' + LimsNotebookLine._table + '" '
                    'ORDER BY analysis_detail, id DESC '
                ') last_nbl '
                'ON detail.id = last_nbl.analysis_detail '
            'WHERE last_nbl.report = TRUE')
        to_report = cursor.fetchall()

        field, op, operand = clause
        if (op, operand) in (('=', True), ('!=', False)):
            return [('id', 'in', to_report)]
        elif (op, operand) in (('=', False), ('!=', True)):
            return [('id', 'not in', to_report)]
        else:
            return []


class LimsVolumeConversion(ModelSQL, ModelView):
    'Volume Conversion'
    __name__ = 'lims.volume.conversion'

    brix = fields.Float('Brix', required=True, digits=(16,
        Eval('brix_digits', 2)), depends=['brix_digits'])
    density = fields.Float('Density', required=True, digits=(16,
        Eval('density_digits', 2)), depends=['density_digits'])
    soluble_solids = fields.Float('Soluble solids', required=True,
        digits=(16, Eval('soluble_solids_digits', 2)),
        depends=['soluble_solids_digits'])
    brix_digits = fields.Function(fields.Integer('Brix digits'),
        'get_configuration_field')
    density_digits = fields.Function(fields.Integer('Density digits'),
        'get_configuration_field')
    soluble_solids_digits = fields.Function(fields.Integer(
        'Soluble solids digits'), 'get_configuration_field')

    @classmethod
    def __setup__(cls):
        super(LimsVolumeConversion, cls).__setup__()
        cls._order.insert(0, ('brix', 'ASC'))

    @staticmethod
    def default_brix_digits():
        Config = Pool().get('lims.configuration')
        config = Config(1)
        return getattr(config, 'brix_digits', 2)

    @staticmethod
    def default_density_digits():
        Config = Pool().get('lims.configuration')
        config = Config(1)
        return getattr(config, 'density_digits', 2)

    @staticmethod
    def default_soluble_solids_digits():
        Config = Pool().get('lims.configuration')
        config = Config(1)
        return getattr(config, 'soluble_solids_digits', 2)

    @classmethod
    def get_configuration_field(cls, volume_conversions, names):
        Config = Pool().get('lims.configuration')
        config = Config(1)

        result = {}
        for name in names:
            value = getattr(config, name, 2)
            result[name] = dict((vc.id, value)
                for vc in volume_conversions)
        return result

    @classmethod
    def brixToDensity(cls, brix):
        if not brix:
            return None
        brix = float(brix)

        values = cls.search([
            ('brix', '=', brix),
            ], limit=1)
        if values:
            return values[0].density

        intrpltn = {
            'x_a': 0,
            'y_a': 0,
            'x_b': 0,
            'y_b': 0,
            }
        lower_values = cls.search([
            ('brix', '<', brix),
            ], order=[('brix', 'DESC')], limit=1)
        if not lower_values:
            return None
        intrpltn['x_a'] = lower_values[0].brix
        intrpltn['y_a'] = lower_values[0].density

        upper_values = cls.search([
            ('brix', '>', brix),
            ], order=[('brix', 'ASC')], limit=1)
        if not upper_values:
            return None
        intrpltn['x_b'] = upper_values[0].brix
        intrpltn['y_b'] = upper_values[0].density

        value = (intrpltn['y_a'] + (brix - intrpltn['x_a']) * (
            (intrpltn['y_b'] - intrpltn['y_a']) /
            (intrpltn['x_b'] - intrpltn['x_a'])))
        return value

    @classmethod
    def brixToSolubleSolids(cls, brix):
        if not brix:
            return None
        brix = float(brix)

        values = cls.search([
            ('brix', '=', brix),
            ], limit=1)
        if values:
            return values[0].soluble_solids

        intrpltn = {
            'x_a': 0,
            'y_a': 0,
            'x_b': 0,
            'y_b': 0,
            }
        lower_values = cls.search([
            ('brix', '<', brix),
            ], order=[('brix', 'DESC')], limit=1)
        if not lower_values:
            return None
        intrpltn['x_a'] = lower_values[0].brix
        intrpltn['y_a'] = lower_values[0].soluble_solids

        upper_values = cls.search([
            ('brix', '>', brix),
            ], order=[('brix', 'ASC')], limit=1)
        if not upper_values:
            return None
        intrpltn['x_b'] = upper_values[0].brix
        intrpltn['y_b'] = upper_values[0].soluble_solids

        value = (intrpltn['y_a'] + (brix - intrpltn['x_a']) * (
            (intrpltn['y_b'] - intrpltn['y_a']) /
            (intrpltn['x_b'] - intrpltn['x_a'])))
        return value


class LimsUomConversion(ModelSQL, ModelView):
    'Uom Conversion'
    __name__ = 'lims.uom.conversion'

    initial_uom = fields.Many2One('product.uom', 'Initial UoM', required=True,
        domain=[('category.lims_only_available', '=', True)])
    final_uom = fields.Many2One('product.uom', 'Final UoM', required=True,
        domain=[('category.lims_only_available', '=', True)])
    initial_uom_volume = fields.Boolean('Volume involved in Initial UoM')
    final_uom_volume = fields.Boolean('Volume involved in Final UoM')
    conversion_formula = fields.Char('Conversion formula')

    @classmethod
    def get_conversion_formula(cls, initial_uom, final_uom):
        if not initial_uom or not final_uom:
            return None
        values = cls.search([
            ('initial_uom', '=', initial_uom),
            ('final_uom', '=', final_uom),
            ])
        if values:
            return values[0].conversion_formula
        return None


class LimsRangeType(ModelSQL, ModelView):
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
        super(LimsRangeType, cls).__setup__()
        cls._error_messages.update({
            'default_range_type': 'There is already a default origin'
                ' for this use',
            })

    @staticmethod
    def default_by_default():
        return False

    @classmethod
    def validate(cls, range_types):
        super(LimsRangeType, cls).validate(range_types)
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


class LimsRange(ModelSQL, ModelView):
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


class LimsControlTendency(ModelSQL, ModelView):
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
        super(LimsControlTendency, cls).__setup__()
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


class LimsControlTendencyDetail(ModelSQL, ModelView):
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

    @classmethod
    def __setup__(cls):
        super(LimsControlTendencyDetail, cls).__setup__()
        cls._order.insert(0, ('date', 'ASC'))
        cls._order.insert(1, ('fraction', 'ASC'))
        cls._order.insert(2, ('device', 'ASC'))

    def get_rules2(self, name=None):
        rules = ''
        if self.rules:
            rules = ', '.join(str(r.rule) for r in self.rules)
        return rules

    @classmethod
    def view_attributes(cls):
        return [('/tree', 'colors',
                If(Equal(Eval('rule', ''), '1'), 'green',
                    If(Equal(Eval('rule', ''), '2'), 'blue',
                    If(Equal(Eval('rule', ''), '3'), 'brown',
                    If(Equal(Eval('rule', ''), '4'), 'red', 'black')))))]


class LimsControlTendencyDetailRule(ModelSQL):
    'Control Chart Tendency Detail Rule'
    __name__ = 'lims.control.tendency.detail.rule'

    detail = fields.Many2One('lims.control.tendency.detail', 'Detail',
        ondelete='CASCADE', select=True, required=True)
    rule = fields.Char('Rule')


class LimsConcentrationLevel(ModelSQL, ModelView):
    'Concentration Level'
    __name__ = 'lims.concentration.level'
    _rec_name = 'description'

    code = fields.Char('Code', required=True)
    description = fields.Char('Description', required=True)

    @classmethod
    def __setup__(cls):
        super(LimsConcentrationLevel, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code),
                'Concentration level code must be unique'),
            ]

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


class LimsResultsReport(ModelSQL, ModelView):
    'Results Report'
    __name__ = 'lims.results_report'
    _rec_name = 'number'

    number = fields.Char('Number', select=True, readonly=True)
    versions = fields.One2Many('lims.results_report.version',
        'results_report', 'Laboratories')
    report_grouper = fields.Integer('Report Grouper')
    generation_type = fields.Char('Generation type')
    cie_fraction_type = fields.Boolean('QA', readonly=True)
    party = fields.Many2One('party.party', 'Party', readonly=True)
    notebook = fields.Many2One('lims.notebook', 'Laboratory notebook')
    report_cache = fields.Binary('Report cache', readonly=True)
    report_format = fields.Char('Report format', readonly=True)
    report_cache_eng = fields.Binary('Report cache', readonly=True)
    report_format_eng = fields.Char('Report format', readonly=True)
    single_sending_report = fields.Function(fields.Boolean(
        'Single sending'), 'get_single_sending_report',
        searcher='search_single_sending_report')
    single_sending_report_ready = fields.Function(fields.Boolean(
        'Single sending Ready'), 'get_single_sending_report_ready')
    english_report = fields.Boolean('English report')
    create_date2 = fields.Function(fields.DateTime('Create Date'),
       'get_create_date2', searcher='search_create_date2')
    write_date2 = fields.DateTime('Write Date', readonly=True)
    attachments = fields.One2Many('ir.attachment', 'resource', 'Attachments')

    @classmethod
    def __setup__(cls):
        super(LimsResultsReport, cls).__setup__()
        cls._order.insert(0, ('number', 'DESC'))
        cls._error_messages.update({
            'no_sequence': ('There is no results report sequence for '
            'the work year "%s".'),
            'missing_module': 'Missing PyPDF2 module',
            'empty_report': 'The report has not details to print',
            })

    @staticmethod
    def default_report_grouper():
        return 0

    @classmethod
    def create(cls, vlist):
        pool = Pool()
        LimsLabWorkYear = pool.get('lims.lab.workyear')
        Sequence = pool.get('ir.sequence.strict')

        workyear_id = LimsLabWorkYear.find()
        workyear = LimsLabWorkYear(workyear_id)
        sequence = workyear.get_sequence('results_report')
        if not sequence:
            cls.raise_user_error('no_sequence',
                (workyear.rec_name,))

        vlist = [x.copy() for x in vlist]
        for values in vlist:
            values['number'] = Sequence.get_id(sequence.id)
        return super(LimsResultsReport, cls).create(vlist)

    @classmethod
    def write(cls, *args):
        actions = iter(args)
        for reports, vals in zip(actions, actions):
            fields_check = cls._get_modified_fields()
            for field in fields_check:
                if field in vals:
                    vals['write_date2'] = CurrentTimestamp()
                    break
        super(LimsResultsReport, cls).write(*args)

    @staticmethod
    def _get_modified_fields():
        return [
            'number',
            'versions',
            'report_grouper',
            'generation_type',
            'cie_fraction_type',
            'party',
            'notebook',
            'english_report',
            'attachments',
            ]

    def get_single_sending_report(self, name):
        pool = Pool()
        LimsNotebook = pool.get('lims.notebook')

        if self.notebook:
            with Transaction().set_user(0):
                notebook = LimsNotebook(self.notebook.id)
                return notebook.fraction.sample.entry.single_sending_report
        return False

    @classmethod
    def search_single_sending_report(cls, name, clause):
        return [('notebook.fraction.sample.entry.' + name,) +
            tuple(clause[1:])]

    def get_single_sending_report_ready(self, name):
        pool = Pool()
        LimsNotebook = pool.get('lims.notebook')
        LimsEntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        if not self.single_sending_report:
            return False
        with Transaction().set_user(0):
            notebook = LimsNotebook(self.notebook.id)
        if LimsEntryDetailAnalysis.search([
                ('fraction', '=', notebook.fraction.id),
                ('report', '=', True),
                ('report_grouper', '=', self.report_grouper),
                ('state', '!=', 'reported'),
                ]):
            return False
        return True

    def get_create_date2(self, name):
        return self.create_date.replace(microsecond=0)

    @classmethod
    def search_create_date2(cls, name, clause):
        cursor = Transaction().connection.cursor()
        operator_ = clause[1:2][0]
        cursor.execute('SELECT id '
                'FROM "' + cls._table + '" '
                'WHERE create_date' + operator_ + ' %s',
                clause[2:3])
        return [('id', 'in', [x[0] for x in cursor.fetchall()])]

    @classmethod
    def order_create_date2(cls, tables):
        return cls.create_date.convert_order('create_date', tables, cls)


class LimsResultsReportVersion(ModelSQL, ModelView):
    'Results Report Version'
    __name__ = 'lims.results_report.version'
    _rec_name = 'number'

    results_report = fields.Many2One('lims.results_report', 'Results Report',
        required=True, ondelete='CASCADE', select=True)
    number = fields.Char('Number', select=True, readonly=True)
    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        required=True, readonly=True)
    details = fields.One2Many('lims.results_report.version.detail',
        'report_version', 'Detail lines')
    report_type = fields.Function(fields.Char('Report type'),
        'get_report_type')

    @classmethod
    def __setup__(cls):
        super(LimsResultsReportVersion, cls).__setup__()
        cls._order.insert(0, ('number', 'DESC'))

    def get_report_type(self, name):
        LimsResultsReportVersionDetail = Pool().get(
            'lims.results_report.version.detail')
        valid_detail = LimsResultsReportVersionDetail.search([
            ('report_version.id', '=', self.id),
            ], order=[('id', 'DESC')], limit=1)
        if valid_detail:
            return valid_detail[0].report_type
        return None

    @classmethod
    def get_number(cls, results_report_id, laboratory_id):
        pool = Pool()
        LimsResultsReport = pool.get('lims.results_report')
        LimsLaboratory = pool.get('lims.laboratory')

        results_reports = LimsResultsReport.search([
            ('id', '=', results_report_id),
            ])
        report_number = results_reports[0].number

        laboratories = LimsLaboratory.search([
            ('id', '=', laboratory_id),
            ])
        laboratory_code = laboratories[0].code

        return '%s-%s' % (report_number, laboratory_code)

    @classmethod
    def create(cls, vlist):
        vlist = [x.copy() for x in vlist]
        for values in vlist:
            values['number'] = cls.get_number(values['results_report'],
                values['laboratory'])
        return super(LimsResultsReportVersion, cls).create(vlist)


class LimsResultsReportVersionDetail(ModelSQL, ModelView):
    'Results Report Version Detail'
    __name__ = 'lims.results_report.version.detail'
    _rec_name = 'report_version'

    report_version = fields.Many2One('lims.results_report.version',
        'Report', required=True, readonly=True,
        ondelete='CASCADE', select=True)
    laboratory = fields.Function(fields.Many2One('lims.laboratory',
        'Laboratory'), 'get_version_field', searcher='search_version_field')
    number = fields.Char('Version', select=True, readonly=True)
    valid = fields.Boolean('Active', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('revised', 'Revised'),
        ('annulled', 'Annulled'),
        ], 'State', readonly=True)
    notebook_lines = fields.One2Many('lims.results_report.version.detail.line',
        'report_version_detail', 'Lines', depends=['state'],
        states={'readonly': Eval('state') != 'draft'})
    report_section = fields.Function(fields.Char('Section'),
        'get_report_section')
    report_type_forced = fields.Selection([
        ('none', 'None'),
        ('normal', 'Normal'),
        ('polisample', 'Polisample'),
        ], 'Forced Report type', sort=False, depends=['state'],
        states={'readonly': Eval('state') != 'draft'})
    report_type = fields.Function(fields.Selection([
        ('normal', 'Normal'),
        ('polisample', 'Polisample'),
        ], 'Report type', sort=False), 'on_change_with_report_type')
    report_result_type_forced = fields.Selection([
        ('none', 'None'),
        ('result', 'Result'),
        ('both', 'Both'),
        ('result_range', 'Result and Ranges'),
        ], 'Forced Result type', sort=False, depends=['state'],
        states={'readonly': Eval('state') != 'draft'})
    report_result_type = fields.Function(fields.Selection([
        ('result', 'Result'),
        ('both', 'Both'),
        ('result_range', 'Result and Ranges'),
        ], 'Result type', sort=False), 'on_change_with_report_result_type')
    english_report = fields.Function(fields.Boolean('English report'),
        'get_report_field', searcher='search_report_field')
    signer = fields.Many2One('lims.laboratory.professional', 'Signer',
        states={'readonly': Eval('state') != 'draft'},
        domain=[('id', 'in', Eval('signer_domain'))],
        depends=['state', 'signer_domain'])
    signer_domain = fields.Function(fields.Many2Many(
        'lims.laboratory.professional', None, None, 'Signer domain'),
        'on_change_with_signer_domain')
    comments = fields.Text('Comments', translate=True, depends=['state'],
        states={'readonly': ~Eval('state').in_(['draft', 'revised'])})
    report_cache = fields.Binary('Report cache', readonly=True)
    report_format = fields.Char('Report format', readonly=True)
    report_cache_eng = fields.Binary('Report cache', readonly=True)
    report_format_eng = fields.Char('Report format', readonly=True)
    report_cache_odt = fields.Binary('Transcription Report cache',
        readonly=True)
    report_format_odt = fields.Char('Transcription Report format',
        readonly=True)
    report_cache_odt_eng = fields.Binary('Transcription Report cache',
        readonly=True)
    report_format_odt_eng = fields.Char('Transcription Report format',
        readonly=True)
    annulment_reason = fields.Text('Annulment reason', readonly=True)
    annulment_date = fields.DateTime('Annulment date', readonly=True)
    date = fields.Function(fields.Date('Date'), 'get_date',
        searcher='search_date')
    party = fields.Function(fields.Many2One('party.party', 'Party'),
       'get_report_field', searcher='search_report_field')
    cie_fraction_type = fields.Function(fields.Boolean('QA'),
       'get_report_field', searcher='search_report_field')
    create_date2 = fields.Function(fields.DateTime('Create Date'),
       'get_create_date2', searcher='search_create_date2')
    write_date2 = fields.Function(fields.DateTime('Write Date'),
       'get_write_date2', searcher='search_write_date2')
    resultrange_origin = fields.Many2One('lims.range.type', 'Origin',
        domain=[('use', '=', 'result_range')],
        depends=['report_result_type', 'state'], states={
            'invisible': Eval('report_result_type') != 'result_range',
            'required': Eval('report_result_type') == 'result_range',
            'readonly': Eval('state') != 'draft',
            })
    fraction_comments = fields.Function(fields.Text('Fraction comments'),
        'get_fraction_comments')

    @classmethod
    def __setup__(cls):
        super(LimsResultsReportVersionDetail, cls).__setup__()
        cls._order.insert(0, ('report_version', 'DESC'))
        cls._order.insert(1, ('number', 'DESC'))
        cls._buttons.update({
            'revise': {
                'invisible': (Eval('state') != 'draft'),
                },
            'annul': {
                'invisible': Or(Eval('state') != 'revised', ~Eval('valid')),
                },
            'revise_all_lang': {
                'invisible': Not(If(Bool(Eval('english_report')),
                    Bool(And(
                        ~Bool(Eval('report_cache_eng')),
                        Bool(Eval('report_cache')),
                        )),
                    Bool(And(
                        ~Bool(Eval('report_cache')),
                        Bool(Eval('report_cache_eng')),
                        )),
                    )),
                },
            })
        cls._error_messages.update({
            'delete_detail': ('You can not delete a detail that is not in '
                'draft state'),
            'multiple_reports': 'Please, select only one report to print',
            'annulled_report': 'This report is annulled',
            'empty_report': 'The report has not lines to print',
            'replace_number': u'Supplants the Results Report N° %s',
            'quantification_limit': '< LoQ = %s',
            'detection_limit': '(LoD = %s %s)',
            'uncertainty': u'(U± %s %s)',
            'obs_uncert': 'U = Uncertainty.',
            'neg': 'Negative',
            'pos': 'Positive',
            'nd': 'Not detected',
            'pre': 'Presence',
            'abs': 'Absence',
            'enac_all_acredited': ('Uncertainty for the analysis covered '
                'by the Accreditation is available.'),
            'enac_acredited': ('The analysis marked with * are not '
                'covered by the Accreditation. Uncertainty for the '
                'analysis covered by the Accreditation is available.'),
            'concentration_label_1': ('(Expressed at the concentration of '
                'the received sample)'),
            'concentration_label_2': u'(Expressed at %s° Brix)',
            'concentration_label_3': '(Expressed at %s)',
            'final_unit_label_1': 'Expressed at %s %% Alcohol',
            'final_unit_label_2': 'Expressed at %s',
            'final_unit_label_3': 'Expressed at %s Bx',
            'final_unit_label_4': 'Expressed at dry matter',
            'obs_ql': 'LoQ= Limit of Quantitation.',
            'obs_dl': 'LoD= Limit of Detection.',
            'caa_min': 'min: %s',
            'caa_max': 'max: %s',
            'obs_rm_c_f': ('Elements results are reported without recovery '
                'correction.'),
            'data_not_specified': 'NOT SPECIFIED BY THE CLIENT',
            })

    @staticmethod
    def default_report_type_forced():
        return 'none'

    @staticmethod
    def default_report_result_type_forced():
        return 'none'

    @classmethod
    def get_next_number(cls, report_version_id, d_count):
        detail_number = cls.search_count([
            ('report_version', '=', report_version_id),
            ])
        detail_number += d_count
        return '%s' % detail_number

    @classmethod
    def create(cls, vlist):
        vlist = [x.copy() for x in vlist]
        d_count = {}
        for values in vlist:
            key = values['report_version']
            if not key in d_count:
                d_count[key] = 0
            d_count[key] += 1
            values['number'] = cls.get_next_number(key, d_count[key])
        return super(LimsResultsReportVersionDetail, cls).create(vlist)

    @staticmethod
    def default_valid():
        return False

    @staticmethod
    def default_state():
        return 'draft'

    def get_report_section(self, name):
        if self.laboratory:
            return self.laboratory.section
        return None

    @fields.depends('report_type_forced')
    def on_change_with_report_type(self, name=None):
        if self.report_type_forced != 'none':
            return self.report_type_forced
        report_type = {
            'normal': 0,
            'polisample': 0,
            }
        cursor = Transaction().connection.cursor()

        cursor.execute('SELECT COUNT(*), t.report_type '
            'FROM lims_results_report_version_detail_l d, '
            'lims_notebook_line l, lims_typification t, '
            'lims_notebook n, lims_fraction f, lims_sample s '
            'WHERE d.report_version_detail = %s '
                'AND d.notebook_line = l.id '
                'AND s.product_type = t.product_type '
                'AND s.matrix = t.matrix '
                'AND l.analysis = t.analysis '
                'AND l.method = t.method '
                'AND t.valid = true '
                'AND l.notebook = n.id '
                'AND n.fraction = f.id '
                'AND f.sample = s.id '
            'GROUP BY t.report_type',
            (self.id, ))
        res = cursor.fetchall()
        for type_ in res:
            if type_[0]:
                report_type[type_[1]] = type_[0]

        if report_type['polisample'] > report_type['normal']:
            return 'polisample'
        return 'normal'

    @fields.depends('report_result_type_forced')
    def on_change_with_report_result_type(self, name=None):
        if self.report_result_type_forced != 'none':
            return self.report_result_type_forced
        report_res_type = {
            'result': 0,
            'both': 0,
            }
        cursor = Transaction().connection.cursor()

        cursor.execute('SELECT COUNT(*), t.report_result_type '
            'FROM lims_results_report_version_detail_l d, '
            'lims_notebook_line l, lims_typification t, '
            'lims_notebook n, lims_fraction f, lims_sample s '
            'WHERE d.report_version_detail = %s '
                'AND d.notebook_line = l.id '
                'AND s.product_type = t.product_type '
                'AND s.matrix = t.matrix '
                'AND l.analysis = t.analysis '
                'AND l.method = t.method '
                'AND t.valid = true '
                'AND l.notebook = n.id '
                'AND n.fraction = f.id '
                'AND f.sample = s.id '
            'GROUP BY t.report_result_type',
            (self.id, ))
        res = cursor.fetchall()
        for type_ in res:
            if type_[0]:
                report_res_type[type_[1]] = type_[0]

        if report_res_type['both'] > report_res_type['result']:
            return 'both'
        return 'result'

    @fields.depends('report_result_type_forced', 'resultrange_origin')
    def on_change_report_result_type_forced(self):
        pool = Pool()
        LimsRangeType = pool.get('lims.range.type')

        if (self.report_result_type_forced == 'result_range'
                and not self.resultrange_origin):
            ranges = LimsRangeType.search([
                ('use', '=', 'result_range'),
                ('by_default', '=', True),
                ])
            if ranges:
                self.resultrange_origin = ranges[0].id

    @fields.depends('laboratory')
    def on_change_with_signer_domain(self, name=None):
        pool = Pool()
        LimsUserLaboratory = pool.get('lims.user-laboratory')
        LimsLaboratoryProfessional = pool.get('lims.laboratory.professional')

        if not self.laboratory:
            return []
        users = LimsUserLaboratory.search([
            ('laboratory', '=', self.laboratory.id),
            ])
        if not users:
            return []
        professionals = LimsLaboratoryProfessional.search([
            ('party.lims_user', 'in', [u.user.id for u in users]),
            ('role', '!=', ''),
            ])
        if not professionals:
            return []
        return [p.id for p in professionals]

    @classmethod
    @ModelView.button
    def revise(cls, details):
        LimsResultsReportVersionDetailLine = Pool().get(
            'lims.results_report.version.detail.line')

        cls.revise_notebook_lines(details)
        for detail in details:
            defaults = {
                'state': 'revised',
                'valid': True,
                }
            valid_details = cls.search([
                ('report_version', '=', detail.report_version.id),
                ('valid', '=', True),
                ])
            if valid_details:
                vd_ids = []
                notebook_lines = []
                for vd in valid_details:
                    vd_ids.append(vd.id)
                    for nline in vd.notebook_lines:
                        notebook_lines.append({
                            'notebook_line': nline.notebook_line.id,
                            })
                if notebook_lines:
                    defaults['notebook_lines'] = [('create', notebook_lines)]

                cls.write(valid_details, {
                    'valid': False,
                    })
                old_lines = LimsResultsReportVersionDetailLine.search([
                    ('report_version_detail.id', 'in', vd_ids),
                    ])
                LimsResultsReportVersionDetailLine.delete(old_lines)

            cls.write([detail], defaults)
            detail.generate_report()

    @classmethod
    def revise_notebook_lines(cls, details):
        pool = Pool()
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsEntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        for detail in details:
            revised_lines = []
            revised_entry_details = []
            for nline in detail.notebook_lines:
                revised_lines.append(nline.notebook_line.id)
                revised_entry_details.append(
                        nline.notebook_line.analysis_detail.id)

            notebook_lines = LimsNotebookLine.search([
                ('id', 'in', revised_lines),
                ])
            if notebook_lines:
                LimsNotebookLine.write(notebook_lines, {
                    'results_report': detail.report_version.results_report.id,
                    })

            entry_details = LimsEntryDetailAnalysis.search([
                ('id', 'in', revised_entry_details),
                ])
            if entry_details:
                LimsEntryDetailAnalysis.write(entry_details, {
                    'state': 'reported',
                    })

    @classmethod
    @ModelView.button_action('lims.wiz_lims_results_report_annulation')
    def annul(cls, details):
        pass

    @classmethod
    def annul_notebook_lines(cls, details):
        pool = Pool()
        LimsNotebookLine = pool.get('lims.notebook.line')
        LimsEntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        for detail in details:
            annulled_lines = []
            annulled_entry_details = []
            for nline in detail.notebook_lines:
                annulled_lines.append(nline.notebook_line.id)
                annulled_entry_details.append(
                        nline.notebook_line.analysis_detail.id)

            notebook_lines = LimsNotebookLine.search([
                ('id', 'in', annulled_lines),
                ('results_report', '=',
                    detail.report_version.results_report.id),
                ])
            if notebook_lines:
                LimsNotebookLine.write(notebook_lines, {
                    'results_report': None,
                    })

            entry_details = LimsEntryDetailAnalysis.search([
                ('id', 'in', annulled_entry_details),
                ])
            if entry_details:
                LimsEntryDetailAnalysis.write(entry_details, {
                    'state': 'done',
                    })

    @classmethod
    @ModelView.button
    def revise_all_lang(cls, details):
        for detail in details:
            detail.generate_report()

    def generate_report(self):
        pool = Pool()
        LimsResultReport = pool.get('lims.result_report', type='report')
        LimsResultReportTranscription = pool.get(
            'lims.result_report.transcription', type='report')

        LimsResultReport.execute([self.id], {
            'english_report': self.english_report,
            })
        LimsResultReportTranscription.execute([self.id], {
            'english_report': self.english_report,
            })

    def get_date(self, name):
        pool = Pool()
        Company = pool.get('company.company')

        date = self.write_date if self.write_date else self.create_date
        company_id = Transaction().context.get('company')
        if company_id:
            date = Company(company_id).convert_timezone_datetime(date)
        return date.date()

    @classmethod
    def search_date(cls, name, clause):
        pool = Pool()
        Company = pool.get('company.company')
        cursor = Transaction().connection.cursor()

        timezone = None
        company_id = Transaction().context.get('company')
        if company_id:
            timezone = Company(company_id).timezone
        timezone_datetime = ('COALESCE(write_date, create_date)::timestamp'
            ' AT TIME ZONE \'UTC\'')
        if timezone:
            timezone_datetime += ' AT TIME ZONE \'' + timezone + '\''

        operator_ = clause[1:2][0]
        cursor.execute('SELECT id '
                'FROM "' + cls._table + '" '
                'WHERE (' + timezone_datetime + ')::date '
                + operator_ + ' %s::date', clause[2:3])
        return [('id', 'in', [x[0] for x in cursor.fetchall()])]

    @classmethod
    def get_version_field(cls, details, names):
        result = {}
        for name in names:
            result[name] = {}
            for d in details:
                field = getattr(d.report_version, name, None)
                result[name][d.id] = field.id if field else None
        return result

    @classmethod
    def search_version_field(cls, name, clause):
        return [('report_version.' + name,) + tuple(clause[1:])]

    @classmethod
    def get_report_field(cls, details, names):
        result = {}
        for name in names:
            result[name] = {}
            if name in ('cie_fraction_type', 'english_report'):
                for d in details:
                    field = getattr(d.report_version.results_report, name,
                        False)
                    result[name][d.id] = field
            else:
                for d in details:
                    field = getattr(d.report_version.results_report, name,
                        None)
                    result[name][d.id] = field.id if field else None
        return result

    @classmethod
    def search_report_field(cls, name, clause):
        return [('report_version.results_report.' + name,) + tuple(clause[1:])]

    @classmethod
    def get_create_date2(cls, details, name):
        result = {}
        for d in details:
            create_date = getattr(d, 'create_date', None)
            result[d.id] = (create_date.replace(microsecond=0)
                if create_date else None)
        return result

    @classmethod
    def search_create_date2(cls, name, clause):
        cursor = Transaction().connection.cursor()
        operator_ = clause[1:2][0]
        cursor.execute('SELECT id '
                'FROM "' + cls._table + '" '
                'WHERE create_date' + operator_ + ' %s',
                clause[2:3])
        return [('id', 'in', [x[0] for x in cursor.fetchall()])]

    @classmethod
    def order_create_date2(cls, tables):
        return cls.create_date.convert_order('create_date', tables, cls)

    @classmethod
    def get_write_date2(cls, details, name):
        result = {}
        for d in details:
            write_date = getattr(d, 'write_date', None)
            result[d.id] = (write_date.replace(microsecond=0)
                if write_date else None)
        return result

    @classmethod
    def search_write_date2(cls, name, clause):
        cursor = Transaction().connection.cursor()
        operator_ = clause[1:2][0]
        cursor.execute('SELECT id '
                'FROM "' + cls._table + '" '
                'WHERE write_date' + operator_ + ' %s',
                clause[2:3])
        return [('id', 'in', [x[0] for x in cursor.fetchall()])]

    @classmethod
    def order_write_date2(cls, tables):
        return cls.write_date.convert_order('write_date', tables, cls)

    @classmethod
    def delete(cls, details):
        cls.check_delete(details)
        super(LimsResultsReportVersionDetail, cls).delete(details)

    @classmethod
    def check_delete(cls, details):
        for detail in details:
            if detail.state != 'draft':
                cls.raise_user_error('delete_detail')

    @classmethod
    def get_fraction_comments(cls, details, name):
        result = {}
        for d in details:
            result[d.id] = None
            notebook = getattr(d.report_version.results_report,
                'notebook', None)
            if notebook:
                result[d.id] = getattr(notebook, 'fraction_comments')
        return result

    @classmethod
    def view_attributes(cls):
        return [
            ('/tree', 'colors',
                If(Len(Eval('fraction_comments')) > 0, 'blue', 'black')),
            ]


class LimsResultsReportVersionDetailLine(ModelSQL, ModelView):
    'Results Report Version Detail Line'
    __name__ = 'lims.results_report.version.detail.line'
    _table = 'lims_results_report_version_detail_l'

    report_version_detail = fields.Many2One(
        'lims.results_report.version.detail', 'Report Detail',
        required=True, ondelete='CASCADE', select=True)
    notebook_line = fields.Many2One('lims.notebook.line', 'Notebook Line',
        required=True)
    notebook = fields.Function(fields.Many2One('lims.notebook',
        'Laboratory notebook'), 'get_nline_field')
    party = fields.Function(fields.Many2One('party.party', 'Party'),
        'get_nline_field')
    analysis = fields.Function(fields.Many2One('lims.analysis', 'Analysis'),
        'get_nline_field')
    repetition = fields.Function(fields.Integer('Repetition'),
        'get_nline_field')
    start_date = fields.Function(fields.Date('Start date'), 'get_nline_field')
    end_date = fields.Function(fields.Date('End date'), 'get_nline_field')
    laboratory = fields.Function(fields.Many2One('lims.laboratory',
        'Laboratory'), 'get_nline_field')
    method = fields.Function(fields.Many2One('lims.lab.method', 'Method'),
        'get_nline_field')
    device = fields.Function(fields.Many2One('lims.lab.device', 'Device'),
        'get_nline_field')
    analysis_origin = fields.Function(fields.Char('Analysis origin'),
        'get_nline_field')
    urgent = fields.Function(fields.Boolean('Urgent'), 'get_nline_field')
    priority = fields.Function(fields.Integer('Priority'), 'get_nline_field')
    report_date = fields.Function(fields.Date('Date agreed for result'),
        'get_nline_field')
    result_modifier = fields.Function(fields.Selection([
        ('eq', '='),
        ('low', '<'),
        ('nd', 'nd'),
        ('na', 'na'),
        ('pos', 'Positive'),
        ('neg', 'Negative'),
        ('ni', 'ni'),
        ('abs', 'Absence'),
        ('pre', 'Presence'),
        ], 'Result modifier'), 'get_nline_field')
    converted_result_modifier = fields.Function(fields.Selection([
        ('eq', '='),
        ('low', '<'),
        ('nd', 'nd'),
        ('na', 'na'),
        ('pos', 'Positive'),
        ('neg', 'Negative'),
        ('ni', 'ni'),
        ], 'Converted result modifier'), 'get_nline_field')
    result = fields.Function(fields.Char('Result'), 'get_nline_field')
    converted_result = fields.Function(fields.Char('Converted result'),
        'get_nline_field')
    initial_unit = fields.Function(fields.Many2One('product.uom',
        'Initial unit'), 'get_nline_field')
    final_unit = fields.Function(fields.Many2One('product.uom',
        'Final unit'), 'get_nline_field')
    comments = fields.Function(fields.Text('Entry comments'),
        'get_nline_field')
    literal_result = fields.Function(fields.Char('Literal result'),
        'get_nline_field')

    @classmethod
    def get_nline_field(cls, details, names):
        result = {}
        for name in names:
            result[name] = {}
            if name in ('notebook', 'party', 'analysis', 'laboratory',
                    'method', 'device', 'initial_unit', 'final_unit'):
                for d in details:
                    field = getattr(d.notebook_line, name, None)
                    result[name][d.id] = field.id if field else None
            else:
                for d in details:
                    result[name][d.id] = getattr(d.notebook_line, name, None)
        return result


class LimsSampleProducer(ModelSQL, ModelView):
    'Sample Producer'
    __name__ = 'lims.sample.producer'

    party = fields.Many2One('party.party', 'Party', required=True)
    name = fields.Char('Name', required=True)


class LimsPlanification(ModelSQL):
    'Planification'
    __name__ = 'lims.planification'
