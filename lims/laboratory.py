# -*- coding: utf-8 -*-
# This file is part of lims module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from sql import Cast
from dateutil import relativedelta

from trytond.model import Workflow, ModelView, ModelSQL, DeactivableMixin, \
    fields, Unique
from trytond.wizard import Wizard, StateTransition, StateView, StateAction, \
    Button
from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.pyson import PYSONEncoder, Eval, Bool
from trytond.exceptions import UserError
from trytond.i18n import gettext
from .formula_parser import FormulaParser

__all__ = ['LaboratoryProfessional', 'Laboratory', 'LaboratoryCVCorrection',
    'LabMethod', 'LabMethodWaitingTime', 'LabDeviceType', 'LabDevice',
    'LabDeviceLaboratory', 'LabDeviceCorrection', 'LabDeviceTypeLabMethod',
    'LabDeviceMaintenanceType', 'LabDeviceMaintenanceActivity',
    'LabDeviceMaintenanceProgram', 'LabDeviceMaintenance',
    'LabDeviceGenerateMaintenanceStart', 'LabDeviceGenerateMaintenance']


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
    maintenance_program = fields.One2Many(
        'lims.lab.device.maintenance.program',
        'device', 'Maintenance Program')
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


class LabDeviceMaintenanceType(ModelSQL, ModelView):
    'Device Maintenance Type'
    __name__ = 'lims.lab.device.maintenance.type'

    name = fields.Char('Name', required=True)


class LabDeviceMaintenanceActivity(ModelSQL, ModelView):
    'Device Maintenance Activity'
    __name__ = 'lims.lab.device.maintenance.activity'

    name = fields.Char('Name', required=True)
    type = fields.Many2One('lims.lab.device.maintenance.type', 'Type')


class LabDeviceMaintenanceProgram(ModelSQL, ModelView):
    'Device Maintenance Program'
    __name__ = 'lims.lab.device.maintenance.program'

    device = fields.Many2One('lims.lab.device', 'Device', required=True,
        ondelete='CASCADE', select=True)
    activity = fields.Many2One('lims.lab.device.maintenance.activity',
        'Activity', required=True)
    frequency = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
        ], 'Frequency', required=True, sort=False)
    responsible = fields.Many2One('res.user', 'Responsible User')
    notice_days = fields.Integer('Days to notify')

    @classmethod
    def __setup__(cls):
        super(LabDeviceMaintenanceProgram, cls).__setup__()
        cls._buttons.update({
            'generate_maintenance': {},
            })

    def get_rec_name(self, name):
        return '%s - %s' % (self.activity.rec_name, self.device.description)

    @classmethod
    @ModelView.button_action(
        'lims.wizard_device_generate_maintenance_calendar')
    def generate_maintenance(cls, programs):
        pass


class LabDeviceMaintenance(Workflow, ModelSQL, ModelView):
    'Device Maintenance Calendar'
    __name__ = 'lims.lab.device.maintenance'

    _states = {'readonly': Eval('state') != 'draft'}
    _depends = ['state']

    device = fields.Many2One('lims.lab.device', 'Device', required=True,
        states=_states, depends=_depends)
    activity = fields.Many2One('lims.lab.device.maintenance.activity',
        'Activity', required=True, states=_states, depends=_depends)
    date = fields.Date('Date', required=True, states=_states, depends=_depends)
    responsible = fields.Many2One('res.user', 'Responsible User',
        states=_states, depends=_depends)
    notice_date = fields.Date('Notice Date', states=_states, depends=_depends)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('done', 'Done'),
        ('discarded', 'Discarded'),
        ], 'State', select=True, readonly=True, required=True)
    comments = fields.Text('Comments')

    @classmethod
    def __setup__(cls):
        super(LabDeviceMaintenance, cls).__setup__()
        cls._order.insert(0, ('date', 'ASC'))
        cls._transitions |= set((
            ('draft', 'pending'),
            ('pending', 'done'),
            ('pending', 'discarded'),
            ))
        cls._buttons.update({
            'pending': {
                'invisible': Eval('state') != 'draft',
                },
            'do': {
                'invisible': Eval('state') != 'pending',
                },
            'discard': {
                'invisible': Eval('state') != 'pending',
                },
            })

    @staticmethod
    def default_state():
        return 'draft'

    def get_rec_name(self, name):
        return '%s - %s' % (self.activity.rec_name, self.device.description)

    @classmethod
    def delete(cls, maintenances):
        cls.check_delete(maintenances)
        super(LabDeviceMaintenance, cls).delete(maintenances)

    @classmethod
    def check_delete(cls, maintenances):
        for m in maintenances:
            if m.state != 'draft':
                raise UserError(gettext('lims.msg_delete_maintenance',
                    maintenance=m.rec_name))

    @classmethod
    @ModelView.button
    @Workflow.transition('pending')
    def pending(cls, maintenances):
        pass

    @classmethod
    @ModelView.button
    @Workflow.transition('done')
    def do(cls, maintenances):
        pass

    @classmethod
    @ModelView.button
    @Workflow.transition('discarded')
    def discard(cls, maintenances):
        pass


class LabDeviceGenerateMaintenanceStart(ModelView):
    'Generate Device Maintenance Calendar'
    __name__ = 'lims.lab.device.maintenance.generate.start'

    start_date = fields.Date('Start Date', required=True)
    end_date = fields.Date('End Date', required=True)
    maintenances = fields.One2Many('lims.lab.device.maintenance',
        None, 'Maintenances')


class LabDeviceGenerateMaintenance(Wizard):
    'Generate Device Maintenance Calendar'
    __name__ = 'lims.lab.device.maintenance.generate'

    start = StateView('lims.lab.device.maintenance.generate.start',
        'lims.lab_device_generate_maintenance_calendar_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Generate', 'generate', 'tryton-ok', default=True),
            ])
    generate = StateTransition()
    open = StateAction('lims.act_lab_device_maintenance_calendar_list')

    def default_start(self, fields):
        Date = Pool().get('ir.date')
        today = Date.today()
        return {
            'start_date': today,
            'end_date': today,
            }

    def transition_generate(self):
        pool = Pool()
        MaintenanceProgram = pool.get('lims.lab.device.maintenance.program')
        Maintenance = pool.get('lims.lab.device.maintenance')

        program = MaintenanceProgram(Transaction().context['active_id'])

        new_maintenances = []
        for date in self._get_dates(self.start.start_date,
                program.frequency, self.start.end_date):
            maintenance = {
                'device': program.device.id,
                'activity': program.activity.id,
                'responsible': (program.responsible and
                    program.responsible.id or None),
                'date': date,
                'state': 'draft',
                }
            if program.notice_days:
                maintenance['notice_date'] = (date +
                    relativedelta.relativedelta(days=-program.notice_days))
            new_maintenances.append(maintenance)

        maintenances = Maintenance.create(new_maintenances)
        if maintenances:
            Maintenance.pending(maintenances)
            self.start.maintenances = maintenances
            return 'open'
        return 'end'

    def _get_dates(self, start_date, frequency, end_date):
        dates = []
        if frequency == 'daily':
            delta = relativedelta.relativedelta(days=1)
        elif frequency == 'weekly':
            delta = relativedelta.relativedelta(days=7)
        elif frequency == 'monthly':
            delta = relativedelta.relativedelta(months=1)
        elif frequency == 'yearly':
            delta = relativedelta.relativedelta(years=1)
        date = start_date
        while date <= end_date:
            dates.append(date)
            date += delta
        return dates

    def do_open(self, action):
        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', 'in', [m.id for m in self.start.maintenances]),
            ])
        return action, {}

    def transition_open(self):
        return 'end'
