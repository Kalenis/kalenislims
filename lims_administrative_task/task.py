# This file is part of lims_administrative_task module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import logging
from dateutil.relativedelta import relativedelta
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.header import Header

from trytond.model import Workflow, ModelSQL, ModelView, fields
from trytond.pyson import PYSONEncoder, Eval
from trytond.pool import Pool, PoolMeta
from trytond.wizard import Wizard, StateTransition, StateView, StateAction, \
    Button
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.i18n import gettext
from trytond.config import config as tconfig
from trytond.tools import get_smtp_server
from trytond.modules.lims_tools.event_creator import EventCreator

logger = logging.getLogger(__name__)


class AdministrativeTaskTemplate(ModelSQL, ModelView):
    'Administrative Task Configuration'
    __name__ = 'lims.administrative.task.template'

    type = fields.Selection('get_types', 'Type', required=True)
    description = fields.Char('Description', required=True)
    expiration_days = fields.Integer('Days to Expiration', required=True)
    responsible = fields.Many2One('res.user', 'Responsible User',
        required=True)

    @classmethod
    def get_types(cls):
        return []

    @classmethod
    def create_tasks(cls, type, records, description=None, responsible=None):
        pool = Pool()
        AdministrativeTask = pool.get('lims.administrative.task')
        Date = pool.get('ir.date')

        if not records:
            return
        templates = cls.search([('type', '=', type)])
        if not templates:
            return

        template = templates[0]
        desc = template.description
        if description:
            desc += ': %s' % str(description)
        if not responsible:
            responsible = template.responsible
        expiration_date = (Date.today() + relativedelta(
            days=template.expiration_days))
        default_fields = list(AdministrativeTask._fields.keys())

        new_tasks = []
        for record in records:
            value = AdministrativeTask.default_get(default_fields,
                with_rec_name=False)
            value.update({
                'type': type,
                'description': desc,
                'responsible': responsible,
                'expiration_date': expiration_date,
                'origin': '%s,%s' % (record.__name__, record.id),
                })
            new_tasks.append(AdministrativeTask(**value))
        AdministrativeTask.save(new_tasks)
        AdministrativeTask.pending(new_tasks)


class AdministrativeTask(Workflow, ModelSQL, ModelView):
    'Administrative Task'
    __name__ = 'lims.administrative.task'
    _rec_name = 'number'

    number = fields.Char('Number', select=True, readonly=True)
    type = fields.Char('Type', readonly=True)
    date = fields.Function(fields.Date('Create Date'), 'get_date',
        searcher='search_date')
    expiration_date = fields.Date('Expiration Date')
    closing_date = fields.Date('Closing Date', readonly=True)
    priority = fields.Selection([
        ('1', 'Very Low'),
        ('2', 'Low'),
        ('3', 'Normal'),
        ('4', 'High'),
        ('5', 'Very High'),
        ], 'Priority', sort=False, required=True)
    priority_string = priority.translated('priority')
    origin = fields.Reference('Operation Origin', selection='get_origin',
        readonly=True)
    description = fields.Char('Description', required=True)
    responsible = fields.Many2One('res.user', 'Responsible User',
        select=True, required=True)
    rejection_reason = fields.Char('Rejection/Stand By Reason',
        states={
            'invisible': ~Eval('state').in_(['rejected', 'standby']),
            'required': Eval('state').in_(['rejected', 'standby']),
            },
        depends=['state'])
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('rejected', 'Rejected'),
        ('ongoing', 'Ongoing'),
        ('standby', 'Stand By'),
        ('done', 'Done'),
        ('discarded', 'Discarded'),
        ], 'State', select=True, readonly=True, required=True)
    icon = fields.Function(fields.Char('Icon'), 'get_icon')
    comments = fields.Text('Comments')
    scheduled = fields.Boolean('Scheduled', readonly=True)
    color = fields.Function(fields.Char('Color'), 'get_color')
    notified_users = fields.Many2Many('lims.administrative.task.user',
        'task', 'user', 'Notified Users')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order.insert(0, ('id', 'DESC'))
        cls._transitions |= set((
            ('draft', 'pending'),
            ('pending', 'rejected'),
            ('rejected', 'pending'),
            ('pending', 'ongoing'),
            ('ongoing', 'standby'),
            ('standby', 'ongoing'),
            ('standby', 'discarded'),
            ('standby', 'done'),
            ('ongoing', 'discarded'),
            ('ongoing', 'done'),
            ))
        cls._buttons.update({
            'pending': {
                'invisible': ~Eval('state').in_(['draft', 'rejected']),
                },
            'reject': {
                'invisible': Eval('state') != 'pending',
                },
            'ongoing': {
                'invisible': ~Eval('state').in_(['pending', 'standby']),
                },
            'standby': {
                'invisible': Eval('state') != 'ongoing',
                },
            'discard': {
                'invisible': ~Eval('state').in_(['standby', 'ongoing']),
                },
            'do': {
                'invisible': ~Eval('state').in_(['standby', 'ongoing']),
                },
            })

    @staticmethod
    def default_state():
        return 'draft'

    @staticmethod
    def default_priority():
        return '3'

    @staticmethod
    def default_scheduled():
        return False

    @classmethod
    def create(cls, vlist):
        pool = Pool()
        Config = pool.get('lims.administrative.task.configuration')

        config = Config(1)
        sequence = config.task_sequence
        if not sequence:
            raise UserError(gettext(
                'lims_administrative_task.msg_no_task_sequence'))

        vlist = [x.copy() for x in vlist]
        for values in vlist:
            values['number'] = sequence.get()
        return super().create(vlist)

    @classmethod
    def check_delete(cls, tasks):
        for t in tasks:
            if t.state != 'draft':
                raise UserError(gettext(
                    'lims_administrative_task.msg_delete_task',
                    task=t.rec_name))

    @classmethod
    def delete(cls, tasks):
        cls.check_delete(tasks)
        super().delete(tasks)

    @classmethod
    def write(cls, *args):
        super().write(*args)
        states_to_check = cls._get_states_to_check()
        fields_to_check = cls._get_fields_to_check()
        actions = iter(args)
        for tasks, vals in zip(actions, actions):
            send_email_update = False
            if 'state' in vals and vals['state'] in states_to_check:
                send_email_update = True
            if not send_email_update:
                for field in fields_to_check:
                    if field in vals:
                        send_email_update = True
                        break
            if send_email_update:
                cls.send_email_update(tasks)

    @staticmethod
    def _get_states_to_check():
        return ['rejected', 'ongoing', 'standby', 'done', 'discarded']

    @staticmethod
    def _get_fields_to_check():
        return [
            'expiration_date',
            'priority',
            'description',
            'responsible',
            'comments',
            ]

    def get_date(self, name):
        if self.scheduled:
            return self.expiration_date
        return self.create_date.date()

    @classmethod
    def search_date(cls, name, clause):
        cursor = Transaction().connection.cursor()
        operator_ = clause[1:2][0]
        value = clause[2:3][0]
        cursor.execute('SELECT id '
            'FROM "' + cls._table + '" '
            'WHERE (scheduled IS FALSE AND create_date::date '
                + operator_ + ' %s) '
            'OR (scheduled IS TRUE AND expiration_date::date '
                + operator_ + ' %s)',
            (value, value))
        return [('id', 'in', [x[0] for x in cursor.fetchall()])]

    @classmethod
    def order_date(cls, tables):
        return cls.create_date.convert_order('create_date', tables, cls)

    @classmethod
    def _get_origin(cls):
        return []

    @classmethod
    def get_origin(cls):
        Model = Pool().get('ir.model')
        models = cls._get_origin()
        models = Model.search([
            ('model', 'in', models),
            ])
        return [('', '')] + [(m.model, m.name) for m in models]

    @classmethod
    def get_icon(cls, tasks, name):
        Date = Pool().get('ir.date')
        today = Date.today()

        result = {}
        for t in tasks:
            result[t.id] = None
            if (t.state in ('pending', 'rejected', 'ongoing', 'standby') and
                    t.expiration_date and t.expiration_date < today):
                result[t.id] = 'lims-red'
        return result

    @classmethod
    def get_color(cls, tasks, name):
        result = {}
        for t in tasks:
            result[t.id] = 'lightgray'
            if t.state in ('pending', 'ongoing', 'standby'):
                result[t.id] = 'lightblue'
        return result

    @classmethod
    def check_transition(cls, records, state):
        filtered = []
        for record in records:
            transition = (record.state, state)
            if transition in cls._transitions:
                filtered.append(record)
        return filtered

    @classmethod
    @ModelView.button
    def pending(cls, tasks):
        records = cls.check_transition(tasks, 'pending')
        cls.write(records, {
            'state': 'pending',
            'rejection_reason': None,
            })
        cls.send_email_responsible(records)

    @classmethod
    @ModelView.button
    def reject(cls, tasks):
        records = cls.check_transition(tasks, 'rejected')
        _required_state = cls.rejection_reason.states['required']
        cls.rejection_reason.states['required'] = False
        for record in records:
            responsible = record.responsible.superior or record.responsible
            cls.write([record], {
                'state': 'rejected',
                'responsible': responsible.id,
                })
        cls.rejection_reason.states['required'] = _required_state
        cls.send_email_responsible(records)

    @classmethod
    @ModelView.button
    def ongoing(cls, tasks):
        records = cls.check_transition(tasks, 'ongoing')
        cls.write(records, {
            'state': 'ongoing',
            'rejection_reason': None,
            })

    @classmethod
    @ModelView.button
    def standby(cls, tasks):
        records = cls.check_transition(tasks, 'standby')
        _required_state = cls.rejection_reason.states['required']
        cls.rejection_reason.states['required'] = False
        cls.write(records, {'state': 'standby'})
        cls.rejection_reason.states['required'] = _required_state

    @classmethod
    @ModelView.button
    def discard(cls, tasks):
        records = cls.check_transition(tasks, 'discarded')
        Date = Pool().get('ir.date')
        today = Date.today()
        cls.write(records, {
            'state': 'discarded',
            'rejection_reason': None,
            'closing_date': today,
            })

    @classmethod
    @ModelView.button
    def do(cls, tasks):
        records = cls.check_transition(tasks, 'done')
        Date = Pool().get('ir.date')
        today = Date.today()
        cls.write(records, {
            'state': 'done',
            'rejection_reason': None,
            'closing_date': today,
            })

    @classmethod
    def send_email_responsible(cls, tasks):
        pool = Pool()
        Config = pool.get('lims.administrative.task.configuration')

        from_addr = tconfig.get('email', 'from')
        if not from_addr:
            logger.error("Missing configuration to send emails")
            return

        config_ = Config(1)

        for task in tasks:
            to_addrs = []
            if task.responsible.email:
                to_addrs.append(task.responsible.email)
            if not to_addrs:
                logger.error("Missing address for '%s' to send email",
                    task.responsible.rec_name)
                continue
            if task.scheduled:
                continue

            subject = str('%s (%s)' % (config_.email_responsible_subject,
                task.number)).strip()
            body = task._get_mail_body()
            msg = cls._create_msg(from_addr, to_addrs, subject, body)
            cls._send_msg(from_addr, to_addrs, msg, task.number)

    @classmethod
    def send_email_update(cls, tasks):
        pool = Pool()
        Config = pool.get('lims.administrative.task.configuration')

        from_addr = tconfig.get('email', 'from')
        if not from_addr:
            logger.error("Missing configuration to send emails")
            return

        config_ = Config(1)

        for task in tasks:
            to_addrs = []
            if task.responsible.email:
                to_addrs.append(task.responsible.email)
            if task.create_uid.email:
                to_addrs.append(task.create_uid.email)
            for user in task.notified_users:
                to_addrs.append(user.email)
            if not to_addrs:
                logger.error("Missing address for '%s' to send email",
                    task.responsible.rec_name)
                continue

            subject = str('%s (%s)' % (config_.email_update_subject,
                task.number)).strip()
            body = task._get_mail_body()
            msg = cls._create_msg(from_addr, to_addrs, subject, body)
            cls._send_msg(from_addr, to_addrs, msg, task.number)

    def _get_mail_body(self):
        pool = Pool()
        Lang = pool.get('ir.lang')

        lang = Lang.get()

        body = str(self.description)
        body += '\n%s: %s' % (
            gettext('lims_administrative_task.field_task_number'),
            str(self.number))
        body += '\n%s: %s' % (
            gettext('lims_administrative_task.field_task_url'),
            str(self._get_task_url()))
        body += '\n%s: %s' % (
            gettext('lims_administrative_task.field_task_date'),
            lang.strftime(self.date))
        body += '\n%s: %s' % (
            gettext('lims_administrative_task.field_task_expiration_date'),
            self.expiration_date and lang.strftime(self.expiration_date) or '')
        body += '\n%s: %s' % (
            gettext('lims_administrative_task.field_task_priority'),
            str(self.priority_string))
        if self.origin:
            body += '\n%s: %s' % (
                gettext('lims_administrative_task.field_task_origin'),
                str(self.origin.rec_name))
        return body

    def _get_task_url(self):
        pool = Pool()
        Config = pool.get('lims.configuration')

        config_ = Config(1)
        tr = Transaction()
        url_part = {}
        if '_request' in tr.context:
            hostname = '%s://%s/' % (
                str(tr.context['_request']['scheme']),
                str(tr.context['_request']['http_host']))
        else:
            hostname = '%s/' % (config_.server_url or '')
        url_part['hostname'] = hostname
        url_part['database'] = tr.database.name
        url_part['type'] = 'model'
        url_part['name'] = self.__name__
        url_part['id'] = self.id
        return '%(hostname)s#%(database)s/%(type)s/%(name)s/%(id)d' % url_part

    @staticmethod
    def _create_msg(from_addr, to_addrs, subject, body):
        if not (from_addr and to_addrs):
            return None
        to_addrs = list(set(to_addrs))

        msg = MIMEMultipart()
        msg['From'] = from_addr
        msg['To'] = ', '.join(to_addrs)
        msg['Subject'] = Header(subject, 'utf-8')

        msg_body = MIMEBase('text', 'plain')
        msg_body.set_payload(body.encode('UTF-8'), 'UTF-8')
        msg.attach(msg_body)
        return msg

    @staticmethod
    def _send_msg(from_addr, to_addrs, msg, task_number):
        to_addrs = list(set(to_addrs))
        success = False
        try:
            server = get_smtp_server()
            server.sendmail(from_addr, to_addrs, msg.as_string())
            server.quit()
            success = True
        except Exception:
            logger.error(
                "Unable to deliver email for task '%s'" % (task_number))
        return success

    @classmethod
    def control_expiring_tasks(cls):
        pool = Pool()
        Config = pool.get('lims.administrative.task.configuration')
        Date = pool.get('ir.date')

        from_addr = tconfig.get('email', 'from')
        if not from_addr:
            logger.error("Missing configuration to send emails")
            return

        config_ = Config(1)
        today = Date.today()

        expiring_tasks = cls.search([
            ('state', 'in', ['pending', 'rejected', 'ongoing', 'standby']),
            ('expiration_date', '=', today),
            ], order=[('expiration_date', 'ASC')])
        for task in expiring_tasks:
            to_addrs = []
            if task.responsible.email:
                to_addrs.append(task.responsible.email)
            if task.create_uid.email:
                to_addrs.append(task.create_uid.email)
            for user in task.notified_users:
                to_addrs.append(user.email)
            if not to_addrs:
                logger.error("Missing address for '%s' to send email",
                    task.responsible.rec_name)
                continue

            subject = str('%s (%s)' % (config_.email_expiration_subject,
                task.number)).strip()
            body = task._get_mail_body()
            msg = cls._create_msg(from_addr, to_addrs, subject, body)
            cls._send_msg(from_addr, to_addrs, msg, task.number)

    @classmethod
    def control_overdue_tasks(cls):
        pool = Pool()
        Date = pool.get('ir.date')

        from_addr = tconfig.get('email', 'from')
        if not from_addr:
            logger.error("Missing configuration to send emails")
            return

        today = Date.today()

        grouped_tasks = {}
        overdue_tasks = cls.search([
            ('state', 'in', ['pending', 'rejected', 'ongoing', 'standby']),
            ('expiration_date', '<', today),
            ], order=[('expiration_date', 'ASC')])
        for task in overdue_tasks:
            key = task.responsible.email
            if not key:
                continue
            if key not in grouped_tasks:
                grouped_tasks[key] = []
            grouped_tasks[key].append(task)
        if not grouped_tasks:
            return

        subject = gettext('lims_administrative_task.lbl_overdue_task_subject')
        body = gettext('lims_administrative_task.lbl_overdue_task_body')
        for to_addr, tasks in grouped_tasks.items():
            body_ = body + '\n'
            for task in tasks:
                body_ += '\n [%s] (%s) %s' % (
                    task.expiration_date.strftime('%d/%m/%Y'),
                    task.number, task.description)
            body_ += '\n\nTotal: %s' % len(tasks)
            msg = cls._create_msg(from_addr, [to_addr], subject, body_)
            cls._send_msg(from_addr, [to_addr], msg, task.number)


class AdministrativeTaskUser(ModelSQL):
    'Administrative Task User'
    __name__ = 'lims.administrative.task.user'

    task = fields.Many2One('lims.administrative.task', 'Task',
        ondelete='CASCADE', select=True, required=True)
    user = fields.Many2One('res.user', 'User',
        ondelete='CASCADE', select=True, required=True)


class EditAdministrativeTaskStart(ModelView):
    'Edit Administrative Task'
    __name__ = 'lims.administrative.task.edit.start'

    priority = fields.Selection([
        (None, ''),
        ('1', 'Very Low'),
        ('2', 'Low'),
        ('3', 'Normal'),
        ('4', 'High'),
        ('5', 'Very High'),
        ], 'Priority', sort=False)
    expiration_date = fields.Date('Expiration Date')
    responsible = fields.Many2One('res.user', 'Responsible User')


class EditAdministrativeTask(Wizard):
    'Edit Administrative Task'
    __name__ = 'lims.administrative.task.edit'

    start = StateView('lims.administrative.task.edit.start',
        'lims_administrative_task.edit_task_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Confirm', 'confirm', 'tryton-ok', default=True),
            ])
    confirm = StateTransition()

    def default_start(self, fields):
        return {
            'priority': None,
            'expiration_date': None,
            'responsible': None,
            }

    def transition_confirm(self):
        pool = Pool()
        AdministrativeTask = pool.get('lims.administrative.task')

        to_write = {}
        if self.start.priority:
            to_write['priority'] = self.start.priority
        if self.start.expiration_date:
            to_write['expiration_date'] = self.start.expiration_date
        if self.start.responsible:
            to_write['responsible'] = self.start.responsible.id

        tasks = AdministrativeTask.browse(Transaction().context['active_ids'])

        if tasks and to_write:
            AdministrativeTask.write(tasks, to_write)
            if 'responsible' in to_write:
                AdministrativeTask.send_email_responsible(tasks)

        return 'end'


class AdministrativeTaskProgram(EventCreator, ModelSQL, ModelView):
    'Administrative Task Scheduling'
    __name__ = 'lims.administrative.task.program'
    _rec_name = 'description'

    type = fields.Selection('get_types', 'Type', required=True)
    description = fields.Char('Description', required=True)
    responsible = fields.Many2One('res.user', 'Responsible User',
        required=True)
    latest_date = fields.Function(fields.Date('Latest scheduled date'),
        'get_latest_date')

    @classmethod
    def __register__(cls, module_name):
        table_h = cls.__table_handler__(module_name)
        super().__register__(module_name)
        if table_h.column_exist('frequency'):
            table_h.drop_column('frequency')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._buttons.update({
            'create_tasks': {
                },
            })

    @classmethod
    def get_types(cls):
        AdministrativeTaskTemplate = Pool().get(
            'lims.administrative.task.template')
        return AdministrativeTaskTemplate.get_types()

    @classmethod
    def get_latest_date(cls, programs, name):
        AdministrativeTask = Pool().get('lims.administrative.task')
        result = {}
        for p in programs:
            latest_task = AdministrativeTask.search([
                ('type', '=', p.type),
                ('responsible', '=', p.responsible.id),
                ('state', '=', 'pending'),
                ], order=[('date', 'DESC')], limit=1)
            result[p.id] = (latest_task and
                latest_task[0].date or None)
        return result

    @classmethod
    @ModelView.button_action(
        'lims_administrative_task.wizard_generate_task_calendar')
    def create_tasks(cls, programs):
        pass

    @classmethod
    def _create_tasks(cls, program, schedule_info):
        pool = Pool()
        AdministrativeTask = pool.get('lims.administrative.task')

        task = AdministrativeTask()
        task.type = program.type
        task.description = program.description
        task.responsible = program.responsible
        task.expiration_date = schedule_info['scheduled_date'].date()
        task.priority = '3'
        task.state = 'draft'
        task.scheduled = True
        return task


class GenerateAdministrativeTask(Wizard):
    'Generate Administrative Tasks Calendar'
    __name__ = 'lims.administrative.task.generate'

    start_state = 'open'
    open = StateAction('lims_administrative_task.act_task')

    def do_open(self, action):
        pool = Pool()
        TaskProgram = pool.get('lims.administrative.task.program')
        AdministrativeTask = pool.get('lims.administrative.task')

        programs = TaskProgram.browse(Transaction().context['active_ids'])
        tasks = TaskProgram.create_events(programs, TaskProgram._create_tasks)
        if tasks:
            AdministrativeTask.save(tasks)
            AdministrativeTask.pending(tasks)

        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', 'in', [t.id for t in tasks]),
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
            ('lims.administrative.task|control_expiring_tasks',
                'Control Expiring Administrative Tasks'),
            ('lims.administrative.task|control_overdue_tasks',
                'Control Overdue Administrative Tasks'),
            ])
