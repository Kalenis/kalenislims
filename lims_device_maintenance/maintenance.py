# This file is part of lims_device_maintenance module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from dateutil import relativedelta

from trytond.model import Workflow, ModelView, ModelSQL, fields
from trytond.wizard import Wizard, StateAction
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from trytond.pyson import PYSONEncoder, Eval
from trytond.exceptions import UserError
from trytond.i18n import gettext
from trytond.modules.lims_tools.event_creator import EventCreator


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


class LabDeviceMaintenanceProgram(EventCreator, ModelSQL, ModelView):
    'Device Maintenance Program'
    __name__ = 'lims.lab.device.maintenance.program'

    asset = fields.Selection([
        ('device', 'Device'),
        ('product', 'Product'),
        ], 'Asset', select=True, required=True)
    device = fields.Many2One('lims.lab.device', 'Device',
        select=True, depends=['asset'],
        states={
            'required': Eval('asset') == 'device',
            'invisible': Eval('asset') != 'device',
            })
    product = fields.Many2One('product.product', 'Product',
        domain=[('type', 'in', ['goods', 'assets'])],
        depends=['asset'],
        states={
            'required': Eval('asset') == 'product',
            'invisible': Eval('asset') != 'product',
            })
    lot = fields.Many2One('stock.lot', 'Lot',
        domain=[('product', '=', Eval('product'))],
        depends=['asset', 'product'],
        states={
            'required': Eval('asset') == 'product',
            'invisible': Eval('asset') != 'product',
            })
    activity = fields.Many2One('lims.lab.device.maintenance.activity',
        'Activity', required=True)
    responsible = fields.Many2One('res.user', 'Responsible User')
    notice_days = fields.Integer('Days to notify')
    latest_date = fields.Function(fields.Date('Latest scheduled date'),
        'get_latest_date')
    comments = fields.Text('Comments')

    @classmethod
    def __register__(cls, module_name):
        table_h = cls.__table_handler__(module_name)
        frequency_exist = table_h.column_exist('frequency')
        super().__register__(module_name)
        if frequency_exist:
            cursor = Transaction().connection.cursor()
            cursor.execute('UPDATE "' + cls._table + '" '
                'SET frequence_selection = \'daily\', '
                    'detail_frequence = 1, '
                    'detail_frequence_selection = \'days\' '
                'WHERE frequency = \'daily\'')
            cursor.execute('UPDATE "' + cls._table + '" '
                'SET frequence_selection = \'weekly\', '
                    'detail_frequence = 1, '
                    'detail_frequence_selection = \'weeks\' '
                'WHERE frequency = \'weekly\'')
            cursor.execute('UPDATE "' + cls._table + '" '
                'SET frequence_selection = \'monthly\', '
                    'detail_frequence = 1, '
                    'detail_frequence_selection = \'months\' '
                'WHERE frequency = \'monthly\'')
            cursor.execute('UPDATE "' + cls._table + '" '
                'SET frequence_selection = \'yearly\', '
                    'detail_frequence = 1, '
                    'detail_frequence_selection = \'years\' '
                'WHERE frequency = \'yearly\'')
            table_h.drop_column('frequency')

    @staticmethod
    def default_asset():
        return 'device'

    def get_rec_name(self, name):
        asset_name = (self.product.rec_name
            if self.asset == 'product'
            else self.device.description)
        return '%s - %s' % (self.activity.rec_name, asset_name)

    @classmethod
    def get_latest_date(cls, programs, name):
        pool = Pool()
        Maintenance = pool.get('lims.lab.device.maintenance')

        result = {}
        for p in programs:
            clause = [
                ('activity', '=', p.activity),
                ('state', '=', 'pending'),
                ]
            if p.asset == 'product':
                clause.extend([
                    ('product', '=', p.product),
                    ('lot', '=', p.lot),
                    ])
            else:
                clause.extend([
                    ('device', '=', p.device),
                    ])
            latest_maintenance = Maintenance.search(clause,
                order=[('date', 'DESC')], limit=1)
            result[p.id] = (latest_maintenance and
                latest_maintenance[0].date or None)
        return result

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._buttons.update({
            'create_maintenances': {
                },
            })

    @classmethod
    @ModelView.button_action(
        'lims_device_maintenance.wizard_device_generate_maintenance_calendar')
    def create_maintenances(cls, programs):
        pass

    @classmethod
    def _create_maintenances(cls, program, schedule_info):
        pool = Pool()
        Maintenance = pool.get('lims.lab.device.maintenance')

        maintenance = Maintenance()
        maintenance.asset = program.asset
        maintenance.device = program.device
        maintenance.product = program.product
        maintenance.lot = program.lot
        maintenance.activity = program.activity
        maintenance.responsible = program.responsible
        maintenance.date = schedule_info['scheduled_date'].date()
        if program.notice_days:
            maintenance.notice_date = (maintenance.date +
                relativedelta.relativedelta(days=-program.notice_days))
        maintenance.state = 'draft'
        return maintenance


class LabDeviceMaintenance(Workflow, ModelSQL, ModelView):
    'Device Maintenance Calendar'
    __name__ = 'lims.lab.device.maintenance'

    _states = {'readonly': Eval('state') != 'draft'}
    _depends = ['state']

    asset = fields.Selection([
        ('device', 'Device'),
        ('product', 'Product'),
        ], 'Asset', select=True, required=True,
        states=_states, depends=_depends)
    device = fields.Many2One('lims.lab.device', 'Device',
        select=True, depends=['asset', 'state'],
        states={
            'required': Eval('asset') == 'device',
            'invisible': Eval('asset') != 'device',
            'readonly': Eval('state') != 'draft',
            })
    product = fields.Many2One('product.product', 'Product',
        domain=[('type', 'in', ['goods', 'assets'])],
        depends=['asset', 'state'],
        states={
            'required': Eval('asset') == 'product',
            'invisible': Eval('asset') != 'product',
            'readonly': Eval('state') != 'draft',
            })
    lot = fields.Many2One('stock.lot', 'Lot',
        domain=[('product', '=', Eval('product'))],
        depends=['asset', 'product', 'state'],
        states={
            'required': Eval('asset') == 'product',
            'invisible': Eval('asset') != 'product',
            'readonly': Eval('state') != 'draft',
            })
    asset_name = fields.Function(fields.Char('Asset'), 'get_asset_name')
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
    color = fields.Function(fields.Char('Color'), 'get_color')
    device_active = fields.Function(fields.Boolean('Device active',
        states={'invisible': Eval('asset') != 'device'},
        depends=['asset']), 'get_device_active')

    del _states, _depends

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order.insert(0, ('date', 'DESC'))
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
    def default_asset():
        return 'device'

    @staticmethod
    def default_state():
        return 'draft'

    def get_asset_name(self, name=None):
        asset_name = (self.product.rec_name
            if self.asset == 'product'
            else self.device.description)
        return asset_name

    def get_rec_name(self, name):
        asset_name = self.get_asset_name()
        return '%s - %s' % (self.activity.rec_name, asset_name)

    def get_color(self, name):
        if self.state in ('done', 'discarded'):
            return 'lightgray'
        return 'lightblue'

    def get_device_active(self, name=None):
        if self.device:
            return self.device.active
        return True

    @classmethod
    def delete(cls, maintenances):
        cls.check_delete(maintenances)
        super().delete(maintenances)

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


class LabDeviceGenerateMaintenance(Wizard):
    'Generate Device Maintenance Calendar'
    __name__ = 'lims.lab.device.maintenance.generate'

    start_state = 'open'
    open = StateAction(
        'lims_device_maintenance.act_lab_device_maintenance_calendar_related')

    def do_open(self, action):
        pool = Pool()
        MaintenanceProgram = pool.get('lims.lab.device.maintenance.program')
        Maintenance = pool.get('lims.lab.device.maintenance')

        programs = MaintenanceProgram.browse(
            Transaction().context['active_ids'])
        maintenances = MaintenanceProgram.create_events(programs,
            MaintenanceProgram._create_maintenances)
        if maintenances:
            Maintenance.save(maintenances)
            Maintenance.pending(maintenances)

        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', 'in', [m.id for m in maintenances]),
            ])
        return action, {}

    def transition_open(self):
        return 'end'


class Cron(metaclass=PoolMeta):
    __name__ = 'ir.cron'

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.method.selection.extend([
            ('lims.lab.device.maintenance|send_notice',
                'Device Maintenance Calendar Notice'),
            ])
