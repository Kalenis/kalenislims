# This file is part of lims_device_maintenance module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from dateutil import relativedelta

from trytond.model import Workflow, ModelView, ModelSQL, fields
from trytond.wizard import Wizard, StateTransition, StateView, StateAction, \
    Button
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from trytond.pyson import PYSONEncoder, Eval
from trytond.exceptions import UserError
from trytond.i18n import gettext

__all__ = ['LabDevice', 'LabDeviceMaintenanceType',
    'LabDeviceMaintenanceActivity', 'LabDeviceMaintenanceProgram',
    'LabDeviceMaintenance', 'LabDeviceGenerateMaintenanceStart',
    'LabDeviceGenerateMaintenance']


class LabDevice(metaclass=PoolMeta):
    __name__ = 'lims.lab.device'

    maintenance_program = fields.One2Many(
        'lims.lab.device.maintenance.program',
        'device', 'Maintenance Program')


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
                raise UserError(gettext(
                    'lims_device_maintenance.msg_delete_maintenance',
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

    @classmethod
    def send_notice(cls):
        pool = Pool()
        TaskTemplate = pool.get('lims.administrative.task.template')
        Date = pool.get('ir.date')

        today = Date.today()
        maintenances = cls.search([
            ('notice_date', '=', today),
            ('state', '=', 'pending'),
            ])
        for maintenance in cls._for_task_device_maintenance(maintenances):
            TaskTemplate.create_tasks('device_maintenance',
                [maintenance], responsible=maintenance.responsible)

    @classmethod
    def _for_task_device_maintenance(cls, maintenances):
        AdministrativeTask = Pool().get('lims.administrative.task')
        res = []
        for maintenance in maintenances:
            if AdministrativeTask.search([
                    ('type', '=', 'device_maintenance'),
                    ('origin', '=', '%s,%s' % (cls.__name__, maintenance.id)),
                    ('state', 'not in', ('done', 'discarded')),
                    ]):
                continue
            res.append(maintenance)
        return res


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
