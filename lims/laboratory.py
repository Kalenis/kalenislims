# -*- coding: utf-8 -*-
# This file is part of lims module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import operator
from sql import Cast

from trytond.model import ModelView, ModelSQL, DeactivableMixin, fields, Unique
from trytond.wizard import Wizard, StateTransition, StateView, Button
from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.pyson import Eval, Bool
from trytond.exceptions import UserError
from trytond.i18n import gettext
from .formula_parser import FormulaParser

__all__ = ['LaboratoryProfessional', 'Laboratory', 'LaboratoryCVCorrection',
    'LabMethod', 'LabMethodWaitingTime', 'LabDeviceType', 'LabDevice',
    'LabDeviceLaboratory', 'LabDeviceCorrection', 'LabDeviceTypeLabMethod',
    'LabDeviceRelateAnalysisStart', 'LabDeviceRelateAnalysis', 'NotebookRule',
    'NotebookRuleCondition']


class Laboratory(ModelSQL, ModelView):
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
    headquarters = fields.Char('Headquarters', translate=True)

    @classmethod
    def __setup__(cls):
        super(Laboratory, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code),
                'lims.msg_laboratory_code_unique_id'),
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


class LaboratoryCVCorrection(ModelSQL, ModelView):
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


class LaboratoryProfessional(ModelSQL, ModelView):
    'Laboratory Professional'
    __name__ = 'lims.laboratory.professional'

    party = fields.Many2One('party.party', 'Party', required=True,
        domain=[('is_lab_professional', '=', True)])
    code = fields.Char('Code')
    role = fields.Char('Signature role', translate=True)
    signature = fields.Binary('Signature')
    methods = fields.One2Many('lims.lab.professional.method', 'professional',
        'Methods')

    @classmethod
    def __setup__(cls):
        super(LaboratoryProfessional, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code),
                'lims.msg_professional_code_unique_id'),
            ('party_uniq', Unique(t, t.party),
                'lims.msg_professional_party_unique_id'),
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


class LabMethod(ModelSQL, ModelView):
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
    results_waiting = fields.One2Many('lims.lab.method.results_waiting',
        'method', 'Waiting times per client')

    @classmethod
    def __setup__(cls):
        super(LabMethod, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code),
                'lims.msg_method_code_unique_id'),
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
        super(LabMethod, cls).write(*args)
        actions = iter(args)
        for methods, vals in zip(actions, actions):
            if 'results_estimated_waiting' in vals:
                cls.update_laboratory_notebook(methods)

    @classmethod
    def update_laboratory_notebook(cls, methods):
        NotebookLine = Pool().get('lims.notebook.line')

        for method in methods:
            waiting_times_parties = [rw.party.id
                for rw in method.results_waiting]
            notebook_lines = NotebookLine.search([
                ('method', '=', method.id),
                ('party', 'not in', waiting_times_parties),
                ('accepted', '=', False),
                ])
            if notebook_lines:
                NotebookLine.write(notebook_lines, {
                    'results_estimated_waiting': (
                        method.results_estimated_waiting),
                    })


class LabMethodWaitingTime(ModelSQL, ModelView):
    'Waiting Time per Client'
    __name__ = 'lims.lab.method.results_waiting'

    method = fields.Many2One('lims.lab.method', 'Method',
        ondelete='CASCADE', select=True, required=True)
    party = fields.Many2One('party.party', 'Party',
        ondelete='CASCADE', select=True, required=True,
        states={'readonly': Bool(Eval('id', 0) > 0)})
    results_estimated_waiting = fields.Integer(
        'Estimated number of days for results', required=True)

    @classmethod
    def __setup__(cls):
        super(LabMethodWaitingTime, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('method_party_uniq', Unique(t, t.method, t.party),
                'lims.msg_method_waiting_time_unique_id'),
            ]

    @classmethod
    def create(cls, vlist):
        waiting_times = super(LabMethodWaitingTime, cls).create(vlist)
        cls.update_laboratory_notebook(waiting_times)
        return waiting_times

    @classmethod
    def write(cls, *args):
        super(LabMethodWaitingTime, cls).write(*args)
        actions = iter(args)
        for waiting_times, vals in zip(actions, actions):
            if 'results_estimated_waiting' in vals:
                cls.update_laboratory_notebook(waiting_times)

    @classmethod
    def update_laboratory_notebook(cls, waiting_times, waiting=None):
        NotebookLine = Pool().get('lims.notebook.line')

        for waiting_time in waiting_times:
            notebook_lines = NotebookLine.search([
                ('method', '=', waiting_time.method.id),
                ('party', '=', waiting_time.party.id),
                ('accepted', '=', False),
                ])
            if notebook_lines:
                results_estimated_waiting = (waiting or
                    waiting_time.results_estimated_waiting)
                NotebookLine.write(notebook_lines, {
                    'results_estimated_waiting': results_estimated_waiting,
                    })

    @classmethod
    def delete(cls, waiting_times):
        waiting = waiting_times[0].method.results_estimated_waiting
        cls.update_laboratory_notebook(waiting_times, waiting)
        super(LabMethodWaitingTime, cls).delete(waiting_times)


class LabDevice(DeactivableMixin, ModelSQL, ModelView):
    'Laboratory Device'
    __name__ = 'lims.lab.device'
    _rec_name = 'description'

    code = fields.Char('Code', required=True)
    description = fields.Char('Description', required=True)
    device_type = fields.Many2One('lims.lab.device.type', 'Device type',
        required=True)
    laboratories = fields.One2Many('lims.lab.device.laboratory', 'device',
        'Laboratories', required=True)
    corrections = fields.One2Many('lims.lab.device.correction', 'device',
        'Corrections')
    serial_number = fields.Char('Serial number')

    @classmethod
    def __setup__(cls):
        super(LabDevice, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code),
                'lims.msg_device_code_unique_id'),
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

    @classmethod
    def write(cls, *args):
        super(LabDevice, cls).write(*args)
        actions = iter(args)
        for devices, vals in zip(actions, actions):
            if 'active' in vals:
                cls.update_active_field(devices, vals['active'])

    @classmethod
    def update_active_field(cls, devices, active):
        AnalysisDevice = Pool().get('lims.analysis.device')
        analysis_devices = AnalysisDevice.search([
            ('device', 'in', devices),
            ('active', '!=', active),
            ])
        fields_to_update = {'active': active}
        if not active:
            fields_to_update['by_default'] = False
        AnalysisDevice.write(analysis_devices, fields_to_update)

    def get_correction(self, value):
        cursor = Transaction().connection.cursor()
        DeviceCorrection = Pool().get('lims.lab.device.correction')

        try:
            value = float(value)
        except ValueError:
            return value

        cursor.execute('SELECT formula '
            'FROM "' + DeviceCorrection._table + '" '
            'WHERE device = %s '
                'AND result_from::float <= %s::float '
                'AND result_to::float >= %s::float',
            (str(self.id), value, value))
        correction = cursor.fetchone()
        if not correction:
            return value

        formula = correction[0]
        for i in (' ', '\t', '\n', '\r'):
            formula = formula.replace(i, '')
        variables = {'X': value}
        parser = FormulaParser(formula, variables)
        return parser.getValue()


class LabDeviceType(ModelSQL, ModelView):
    'Laboratory Device Type'
    __name__ = 'lims.lab.device.type'
    _rec_name = 'description'

    code = fields.Char('Code', required=True)
    description = fields.Char('Description', required=True)
    methods = fields.Many2Many('lims.lab.device.type-lab.method',
        'device_type', 'method', 'Methods')

    @classmethod
    def __setup__(cls):
        super(LabDeviceType, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code),
                'lims.msg_device_type_code_unique_id'),
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


class LabDeviceTypeLabMethod(ModelSQL):
    'Laboratory Device Type - Laboratory Method'
    __name__ = 'lims.lab.device.type-lab.method'

    device_type = fields.Many2One('lims.lab.device.type', 'Device type',
        ondelete='CASCADE', select=True, required=True)
    method = fields.Many2One('lims.lab.method', 'Method',
        ondelete='CASCADE', select=True, required=True)


class LabDeviceLaboratory(ModelSQL, ModelView):
    'Laboratory Device Laboratory'
    __name__ = 'lims.lab.device.laboratory'

    device = fields.Many2One('lims.lab.device', 'Device', required=True,
        ondelete='CASCADE', select=True)
    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        required=True)
    physically_here = fields.Boolean('Physically here')

    @staticmethod
    def default_physically_here():
        return True

    @classmethod
    def validate(cls, laboratories):
        super(LabDeviceLaboratory, cls).validate(laboratories)
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
                raise UserError(gettext('lims.msg_physically_elsewhere'))


class LabDeviceCorrection(ModelSQL, ModelView):
    'Device Correction'
    __name__ = 'lims.lab.device.correction'

    device = fields.Many2One('lims.lab.device', 'Device', required=True,
        ondelete='CASCADE', select=True)
    result_from = fields.Char('From', required=True)
    result_to = fields.Char('To', required=True)
    formula = fields.Char('Correction Formula', required=True,
        help="Correction formula based on the given value (X)")

    @classmethod
    def __setup__(cls):
        super(LabDeviceCorrection, cls).__setup__()
        cls._order.insert(0, ('result_from', 'ASC'))

    @classmethod
    def validate(cls, corrections):
        super(LabDeviceCorrection, cls).validate(corrections)
        for correction in corrections:
            try:
                float(correction.result_from)
                float(correction.result_to)
            except ValueError:
                raise UserError(gettext('lims.msg_device_correction_number'))

    @staticmethod
    def order_result_from(tables):
        table, _ = tables[None]
        return [Cast(table.result_from, 'FLOAT'), table.result_from]

    @staticmethod
    def order_result_to(tables):
        table, _ = tables[None]
        return [Cast(table.result_to, 'FLOAT'), table.result_to]


class LabDeviceRelateAnalysisStart(ModelView):
    'Relate Analysis to Device'
    __name__ = 'lims.lab.device.relate_analysis.start'

    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        required=True, depends=['laboratory_domain'],
        domain=[('id', 'in', Eval('laboratory_domain'))])
    laboratory_domain = fields.One2Many('lims.laboratory',
        None, 'Laboratory domain')
    analysis = fields.Many2Many('lims.analysis', None, None,
        'Analysis', required=True, depends=['analysis_domain'],
        domain=[('id', 'in', Eval('analysis_domain'))])
    analysis_domain = fields.Function(fields.One2Many('lims.analysis',
        None, 'Analysis domain'), 'on_change_with_analysis_domain')

    @fields.depends('laboratory')
    def on_change_with_analysis_domain(self, name=None):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Analysis = pool.get('lims.analysis')
        AnalysisLaboratory = pool.get('lims.analysis-laboratory')

        if not self.laboratory:
            return []

        cursor.execute('SELECT DISTINCT(al.analysis) '
            'FROM "' + AnalysisLaboratory._table + '" al '
                'INNER JOIN "' + Analysis._table + '" a '
                'ON a.id = al.analysis '
            'WHERE al.laboratory = %s '
                'AND a.state = \'active\' '
                'AND a.type = \'analysis\' '
                'AND a.end_date IS NULL',
            (self.laboratory.id,))
        return [x[0] for x in cursor.fetchall()]


class LabDeviceRelateAnalysis(Wizard):
    'Relate Analysis to Device'
    __name__ = 'lims.lab.device.relate_analysis'

    start = StateView('lims.lab.device.relate_analysis.start',
        'lims.lab_device_relate_analysis_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Relate', 'relate', 'tryton-ok', default=True),
            ])
    relate = StateTransition()

    def default_start(self, fields):
        Device = Pool().get('lims.lab.device')

        device = Device(Transaction().context['active_id'])
        default = {
            'laboratory_domain': [l.laboratory.id
                for l in device.laboratories],
            }
        return default

    def transition_relate(self):
        AnalysisDevice = Pool().get('lims.analysis.device')

        device_id = Transaction().context['active_id']
        laboratory_id = self.start.laboratory.id

        to_create = []
        for a in self.start.analysis:
            if AnalysisDevice.search([
                    ('analysis', '=', a.id),
                    ('laboratory', '=', laboratory_id),
                    ('device', '=', device_id),
                    ]):
                continue

            by_default = True
            if (AnalysisDevice.search_count([
                    ('analysis', '=', a.id),
                    ('laboratory', '=', laboratory_id),
                    ('by_default', '=', True),
                    ]) > 0):
                by_default = False
            to_create.append({
                'analysis': a.id,
                'laboratory': laboratory_id,
                'device': device_id,
                'by_default': by_default,
                })

        if to_create:
            AnalysisDevice.create(to_create)
        return 'end'


class NotebookRule(ModelSQL, ModelView):
    'Notebook Rule'
    __name__ = 'lims.rule'

    name = fields.Char('Name', required=True)
    analysis = fields.Many2One('lims.analysis', 'Trigger Analysis',
        required=True, domain=[
            ('state', '=', 'active'),
            ('type', '=', 'analysis'),
            ('behavior', '!=', 'additional'),
            ])
    conditions = fields.One2Many('lims.rule.condition', 'rule', 'Conditions',
        required=True)
    action = fields.Selection([
        ('add', 'Add Analysis'),
        ('edit', 'Edit Analysis'),
        ], 'Action', required=True, sort=False)
    target_analysis = fields.Many2One('lims.analysis', 'Target Analysis',
        required=True, domain=[
            ('state', '=', 'active'),
            ('type', '=', 'analysis'),
            ('behavior', '!=', 'additional'),
            ])
    target_field = fields.Many2One('ir.model.field', 'Target Field',
        domain=[('id', 'in', Eval('target_field_domain'))],
        depends=['target_field_domain', 'action'], states={
            'required': Eval('action') == 'edit',
            'invisible': Eval('action') != 'edit',
            })
    target_field_domain = fields.Function(fields.Many2Many('ir.model.field',
        None, None, 'Target Field domain'), 'get_target_field_domain')
    value = fields.Char('Value', depends=['action'],
        states={
            'required': Eval('action') == 'edit',
            'invisible': Eval('action') != 'edit',
            })

    @staticmethod
    def default_target_field_domain():
        ModelField = Pool().get('ir.model.field')
        _field_list = ['end_date', 'method', 'device', 'initial_concentration',
            'final_concentration', 'initial_unit', 'final_unit',
            'result_modifier', 'result', 'converted_result_modifier',
            'converted_result', 'detection_limit', 'quantification_limit',
            'dilution_factor', 'chromatogram', 'comments',
            'theoretical_concentration', 'concentration_level', 'decimals',
            'backup', 'reference', 'literal_result', 'rm_correction_formula',
            'report', 'uncertainty', 'verification', ]
        fields = ModelField.search([
            ('model.model', '=', 'lims.notebook.line'),
            ('name', 'in', _field_list),
            ])
        return [f.id for f in fields]

    def get_target_field_domain(self, name=None):
        return self.default_target_field_domain()

    def eval_condition(self, line):
        for condition in self.conditions:
            if not condition.eval_condition(line):
                return False
        return True

    def exec_action(self, line):
        if self.action == 'add':
            self._exec_add(line)
        elif self.action == 'edit':
            self._exec_edit(line)

    def _exec_add(self, line):
        pool = Pool()
        Typification = pool.get('lims.typification')
        NotebookLine = pool.get('lims.notebook.line')

        typification = Typification.search([
            ('product_type', '=', line.product_type),
            ('matrix', '=', line.matrix),
            ('analysis', '=', self.target_analysis),
            ('by_default', '=', True),
            ('valid', '=', True),
            ], limit=1)
        if not typification:
            return

        existing_line = NotebookLine.search([
            ('notebook', '=', line.notebook),
            ('analysis', '=', self.target_analysis),
            ], order=[('repetition', 'DESC')], limit=1)
        if not existing_line:
            self._exec_add_service(line, typification[0])
        #else:
            #self._exec_add_repetition(existing_line[0])

    def _exec_add_repetition(self, line):
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        repetition = self._get_line_last_repetition(line)
        line_create = [{
            'notebook': line.notebook.id,
            'analysis_detail': line.analysis_detail.id,
            'service': line.service.id,
            'analysis': self.target_analysis.id,
            'analysis_origin': line.analysis_origin,
            'repetition': repetition + 1,
            'laboratory': line.laboratory.id,
            'method': line.method.id,
            'device': line.device.id if line.device else None,
            'initial_concentration': line.initial_concentration,
            'decimals': line.decimals,
            'report': line.report,
            'concentration_level': (line.concentration_level and
                line.concentration_level.id or None),
            'results_estimated_waiting': line.results_estimated_waiting,
            'department': line.department,
            'final_concentration': line.final_concentration,
            'initial_unit': line.initial_unit and line.initial_unit.id or None,
            'final_unit': line.final_unit and line.final_unit.id or None,
            'detection_limit': line.detection_limit,
            'quantification_limit': line.quantification_limit,
            }]
        NotebookLine.create(line_create)

        details = EntryDetailAnalysis.search([
            ('id', 'in', [line.analysis_detail.id]),
            ])
        if details:
            EntryDetailAnalysis.write(details, {
                'state': 'unplanned',
                })

    def _exec_add_service(self, line, typification):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        AnalysisLaboratory = pool.get('lims.analysis-laboratory')
        AnalysisDevice = pool.get('lims.analysis.device')
        Service = pool.get('lims.service')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')

        cursor.execute('SELECT DISTINCT(laboratory) '
            'FROM "' + AnalysisLaboratory._table + '" '
            'WHERE analysis = %s',
            (self.target_analysis.id,))
        laboratories = [x[0] for x in cursor.fetchall()]
        if not laboratories:
            return
        laboratory_id = laboratories[0]

        method_id = typification.method and typification.method.id or None

        cursor.execute('SELECT DISTINCT(device) '
            'FROM "' + AnalysisDevice._table + '" '
            'WHERE active IS TRUE '
                'AND analysis = %s  '
                'AND laboratory = %s '
                'AND by_default IS TRUE',
            (self.target_analysis.id, laboratory_id))
        devices = [x[0] for x in cursor.fetchall()]
        device_id = devices and devices[0] or None

        service_create = [{
            'fraction': line.fraction.id,
            'analysis': self.target_analysis.id,
            'urgent': True,
            'laboratory': laboratory_id,
            'method': method_id,
            'device': device_id,
            }]
        with Transaction().set_context(manage_service=True):
            new_service, = Service.create(service_create)

        Service.copy_analysis_comments([new_service])
        Service.set_confirmation_date([new_service])
        analysis_detail = EntryDetailAnalysis.search([
            ('service', '=', new_service.id)])
        if analysis_detail:
            EntryDetailAnalysis.create_notebook_lines(analysis_detail,
                line.fraction)
            EntryDetailAnalysis.write(analysis_detail, {
                'state': 'unplanned',
                })

    def _exec_edit(self, line):
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')

        if line.analysis == self.target_analysis:
            notebook_line = NotebookLine(line.id)
        else:
            target_line = NotebookLine.search([
                ('notebook', '=', line.notebook),
                ('analysis', '=', self.target_analysis),
                ], order=[('repetition', 'DESC')], limit=1)
            if not target_line:
                return
            notebook_line = target_line[0]

        if notebook_line.accepted or notebook_line.annulled:
            return

        try:
            setattr(notebook_line, self.target_field.name, self.value)
            notebook_line.save()
        except Exception as e:
            return

    def _get_line_last_repetition(self, line):
        NotebookLine = Pool().get('lims.notebook.line')
        lines = NotebookLine.search([
            ('notebook', '=', line.notebook),
            ('analysis', '=', line.analysis),
            ], order=[('repetition', 'DESC')], limit=1)
        return lines and lines[0].repetition or 0


class NotebookRuleCondition(ModelSQL, ModelView):
    'Notebook Rule Condition'
    __name__ = 'lims.rule.condition'

    rule = fields.Many2One('lims.rule', 'Rule', required=True,
        ondelete='CASCADE', select=True)
    field = fields.Char('Field', required=True, help=("Internal name of the " +
        "field. Relationships are allowed, such as " +
        "\"notebook.product_type.code\""))
    condition = fields.Selection([
        ('eq', '='),
        ('ne', '!='),
        ('gt', '>'),
        ('ge', '>='),
        ('lt', '<'),
        ('le', '<='),
        ], 'Condition', required=True, sort=False)
    value = fields.Char('Value', required=True)

    def eval_condition(self, line):
        path = self.field.split('.')
        field = path.pop(0)
        try:
            value = getattr(line, field)
            while path:
                field = path.pop(0)
                value = getattr(value, field)
        except AttributeError:
            return False

        operator_func = {
            'eq': operator.eq,
            'ne': operator.ne,
            'gt': operator.gt,
            'ge': operator.ge,
            'lt': operator.lt,
            'le': operator.le,
            }
        result = operator_func[self.condition](value, self.value)
        return result

    @classmethod
    def validate(cls, conditions):
        super(NotebookRuleCondition, cls).validate(conditions)
        for c in conditions:
            c.check_field()

    def check_field(self):
        pool = Pool()

        invalid_fields = ('many2one', 'one2one', 'reference',
            'one2many', 'many2many')
        path = self.field.split('.')

        Model = pool.get('lims.notebook.line')
        field_name = path.pop(0)
        if field_name not in Model._fields:
            raise UserError(gettext('lims.msg_rule_condition_field',
                field=self.field))
        field = Model._fields[field_name]
        if not path and field._type in invalid_fields:
            raise UserError(gettext('lims.msg_rule_condition_field',
                field=self.field))

        while path:
            if field._type != 'many2one':
                raise UserError(gettext('lims.msg_rule_condition_field',
                    field=self.field))

            Model = pool.get(field.model_name)
            field_name = path.pop(0)
            if field_name not in Model._fields:
                raise UserError(gettext('lims.msg_rule_condition_field',
                    field=self.field))
            field = Model._fields[field_name]
            if not path and field._type in invalid_fields:
                raise UserError(gettext('lims.msg_rule_condition_field',
                    field=self.field))
