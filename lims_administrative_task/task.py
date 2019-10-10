# This file is part of lims_administrative_task module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import logging
from dateutil.relativedelta import relativedelta
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.header import Header

from trytond.model import Workflow, ModelSQL, ModelView, fields
from trytond.pyson import Eval
from trytond.pool import Pool
from trytond.wizard import Wizard, StateTransition, StateView, Button
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.i18n import gettext
from trytond.config import config
from trytond.tools import get_smtp_server

__all__ = ['AdministrativeTaskTemplate', 'AdministrativeTask',
    'EditAdministrativeTaskStart', 'EditAdministrativeTask']
logger = logging.getLogger(__name__)


class AdministrativeTaskTemplate(ModelSQL, ModelView):
    'Administrative Task Configuration'
    __name__ = 'lims.administrative.task.template'

    model = fields.Many2One('ir.model', 'Model', select=True, required=True,
        domain=[('id', 'in', Eval('model_domain'))], depends=['model_domain'])
    model_domain = fields.Function(fields.Many2Many('ir.model', None, None,
        'Model domain'), 'get_model_domain')
    description = fields.Char('Description', required=True)
    expiration_days = fields.Integer('Days to Expiration', required=True)
    responsible = fields.Many2One('res.user', 'Responsible User',
        required=True)

    @classmethod
    def default_model_domain(cls):
        return cls._get_model_domain()

    def get_model_domain(self, name=None):
        return self._get_model_domain()

    @staticmethod
    def _get_model_domain():
        pool = Pool()
        AdministrativeTask = pool.get('lims.administrative.task')
        Model = pool.get('ir.model')

        models = AdministrativeTask._get_origin()
        models = Model.search([
            ('model', 'in', models),
            ])
        return [m.id for m in models]

    @classmethod
    def create_tasks(cls, model_name, records):
        pool = Pool()
        Model = pool.get('ir.model')
        AdministrativeTask = pool.get('lims.administrative.task')
        Date = pool.get('ir.date')

        if not records:
            return
        models = Model.search([('model', '=', model_name)])
        if not models:
            return
        templates = cls.search([('model', '=', models[0])])
        if not templates:
            return

        template = templates[0]
        expiration_date = (Date.today() + relativedelta(
            days=template.expiration_days))
        default_fields = list(AdministrativeTask._fields.keys())

        new_tasks = []
        for record in records:
            value = AdministrativeTask.default_get(default_fields)
            value.update({
                'description': template.description,
                'responsible': template.responsible,
                'expiration_date': expiration_date,
                'origin': '%s,%s' % (model_name, record.id),
                })
            new_tasks.append(AdministrativeTask(**value))
        AdministrativeTask.save(new_tasks)
        AdministrativeTask.pending(new_tasks)


class AdministrativeTask(Workflow, ModelSQL, ModelView):
    'Administrative Task'
    __name__ = 'lims.administrative.task'
    _rec_name = 'number'

    number = fields.Char('Number', select=True, readonly=True)
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
    origin = fields.Reference('Operation Origin', selection='get_origin')
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

    @classmethod
    def __setup__(cls):
        super(AdministrativeTask, cls).__setup__()
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

    @classmethod
    def create(cls, vlist):
        pool = Pool()
        Config = pool.get('lims.administrative.task.configuration')
        Sequence = pool.get('ir.sequence')

        config = Config(1)
        sequence = config.task_sequence
        if not sequence:
            raise UserError(gettext(
                'lims_administrative_task.msg_no_task_sequence'))

        vlist = [x.copy() for x in vlist]
        for values in vlist:
            values['number'] = Sequence.get_id(sequence.id)
        return super(AdministrativeTask, cls).create(vlist)

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
        super(AdministrativeTask, cls).delete(tasks)

    def get_date(self, name):
        return self.create_date.date()

    @classmethod
    def search_date(cls, name, clause):
        cursor = Transaction().connection.cursor()
        operator_ = clause[1:2][0]
        cursor.execute('SELECT id '
            'FROM "' + cls._table + '" '
            'WHERE create_date::date ' + operator_ + ' %s',
            clause[2:3])
        return [('id', 'in', [x[0] for x in cursor.fetchall()])]

    @classmethod
    def order_date(cls, tables):
        return cls.create_date.convert_order('create_date', tables, cls)

    @classmethod
    def _get_origin(cls):
        'Return list of Model names for origin Reference'
        return ['party.party', 'lims.equipment', 'lims.component',
            'sale.sale', 'sale.line']

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
        from_addr = config.get('email', 'from')
        if not from_addr:
            logger.error("Missing configuration to send emails")
            return

        for task in tasks:
            to_addr = task.responsible.email
            if not to_addr:
                logger.error("Missing address for '%s' to send email",
                    task.responsible.rec_name)
                continue

            subject, body = task._get_subject_body()
            msg = cls.create_msg(from_addr, to_addr, subject, body)
            cls.send_msg(from_addr, to_addr, msg, task.number)

    def _get_subject_body(self):
        pool = Pool()
        Config = pool.get('lims.administrative.task.configuration')
        Lang = pool.get('ir.lang')

        config = Config(1)
        lang = Lang.get()

        subject = str('%s (%s)' % (config.email_responsible_subject,
            self.number)).strip()

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
            lang.strftime(self.expiration_date))
        body += '\n%s: %s' % (
            gettext('lims_administrative_task.field_task_priority'),
            str(self.priority_string))
        body += '\n%s: %s' % (
            gettext('lims_administrative_task.field_task_origin'),
            str(self.origin.rec_name))
        return subject, body

    def _get_task_url(self):
        tr = Transaction()
        url_part = {}
        hostname = '%s://%s/' % (
            str(tr.context['_request']['scheme']),
            str(tr.context['_request']['http_host']))
        url_part['hostname'] = hostname
        url_part['database'] = tr.database.name
        url_part['type'] = 'model'
        url_part['name'] = self.__name__
        url_part['id'] = self.id
        return '%(hostname)s#%(database)s/%(type)s/%(name)s/%(id)d' % url_part

    @staticmethod
    def create_msg(from_addr, to_addr, subject, body):
        if not (from_addr or to_addr):
            return None

        msg = MIMEMultipart()
        msg['From'] = from_addr
        msg['To'] = to_addr
        msg['Subject'] = Header(subject, 'utf-8')

        msg_body = MIMEBase('text', 'plain')
        msg_body.set_payload(body.encode('UTF-8'), 'UTF-8')
        msg.attach(msg_body)

        return msg

    @staticmethod
    def send_msg(from_addr, to_addr, msg, task_number):
        success = False
        try:
            server = get_smtp_server()
            server.sendmail(from_addr, [to_addr], msg.as_string())
            server.quit()
            success = True
        except Exception:
            logger.error(
                "Unable to deliver email for task '%s'" % (task_number))
        return success


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
