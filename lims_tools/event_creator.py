# This file is part of lims_tools module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from datetime import datetime
from dateutil import rrule

from trytond.model import Model, fields
from trytond.pool import Pool
from trytond.pyson import Eval
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.i18n import gettext


FREQUENCE_OPTIONS = [
    ('hourly', 'Hourly'),
    ('daily', 'Daily'),
    ('weekly', 'Weekly'),
    ('15_days', 'Every 15 days'),
    ('monthly', 'Monthly'),
    ('yearly', 'Yearly'),
    ('workshift', 'By work shift'),
    ('customize', 'Customize'),
    ]

FREQUENCE_OPTIONS_VALUE_MAP = {
    'hourly': (1, 'hours'),
    'daily': (1, 'days'),
    'weekly': (1, 'weeks'),
    '15_days': (15, 'days'),
    'monthly': (1, 'months'),
    'yearly': (1, 'years'),
    'workshift': (1, 'days'),
    'customize': (None, None),
    }

DETAIL_FREQUENCE_OPTIONS = [
    (None, ''),
    ('minutes', 'Minutes'),
    ('hours', 'Hours'),
    ('days', 'Days'),
    ('weeks', 'Weeks'),
    ('months', 'Months'),
    ('years', 'Years'),
    ]

WEEK_DAYS = [
    (None, ''),
    ('0', 'Monday'),
    ('1', 'Tuesday'),
    ('2', 'Wednesday'),
    ('3', 'Thursday'),
    ('4', 'Friday'),
    ('5', 'Saturday'),
    ('6', 'Sunday'),
    ]


class EventCreator(Model):
    'Event Creator'

    start_date = fields.DateTime('Start Date')
    frequence_selection = fields.Selection(FREQUENCE_OPTIONS,
        'Select Frequence', sort=False)
    detail_frequence = fields.Float('Frequence', required=True,
        states={'readonly': Eval('frequence_selection') == 'workshift'},
        depends=['frequence_selection'])
    detail_frequence_selection = fields.Selection(DETAIL_FREQUENCE_OPTIONS,
        'Frequence', sort=False, required=True,
        states={'readonly': Eval('frequence_selection') == 'workshift'},
        depends=['frequence_selection'])
    specific_day = fields.Selection([
        (None, ''),
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday')
        ], 'Specific Day',
        states={'invisible': Eval('frequence_selection') != 'weekly'},
        depends=['frequence_selection'])
    specific_event_time = fields.DateTime('Specific Time',
        states={'invisible': Eval('frequence_selection') != 'daily'},
        depends=['frequence_selection'])
    shifts = fields.MultiSelection('get_workyear_shifts', 'Work shifts',
        sort=False,
        states={'invisible': Eval('frequence_selection') != 'workshift'},
        depends=['frequence_selection'])
    shift_time = fields.Selection([
        (None, ''),
        ('start', 'At start'),
        ('end', 'At end'),
        ('start_end', 'At start and end'),
        ], 'Time of the shift', sort=False,
        states={'invisible': Eval('frequence_selection') != 'workshift'},
        depends=['frequence_selection'])
    only_workdays = fields.Boolean('Allow working days only')
    finish_selection = fields.Selection([
        (None, ''),
        ('date', 'Date'),
        ('quantity', 'Quantity'),
        ], 'Ends on', sort=False)
    end_repetition = fields.Integer('Repetition Qty.',
        states={
            'invisible': Eval('finish_selection') != 'quantity',
            'required': Eval('finish_selection') == 'quantity',
            })
    end_date = fields.DateTime('End Date',
        states={
            'invisible': Eval('finish_selection') != 'date',
            'required': Eval('finish_selection') == 'date',
            })

    @fields.depends('frequence_selection')
    def on_change_frequence_selection(self):
        if (self.frequence_selection and
                self.frequence_selection in FREQUENCE_OPTIONS_VALUE_MAP):
            self.detail_frequence, self.detail_frequence_selection = (
                FREQUENCE_OPTIONS_VALUE_MAP[self.frequence_selection])

    @classmethod
    def get_workyear_shifts(cls):
        pool = Pool()
        LabWorkYear = pool.get('lims.lab.workyear')
        WorkShift = pool.get('lims.lab.workyear.shift')
        workyear_shifts = WorkShift.search([
            ('workyear', '=', LabWorkYear.find()),
            ])
        result = [(ws.shift.id, ws.shift.name) for ws in workyear_shifts]
        return result

    @classmethod
    def create_events(cls, records, create_method,
            start_date=None, include_start_date=True):
        events = []
        for record in records:
            if record.finish_selection == 'quantity':
                if record.frequence_selection == 'workshift':
                    events.extend(cls.create_workshift_fixed_events(
                        record, create_method, start_date, include_start_date))
                else:
                    events.extend(cls.create_fixed_events(
                        record, create_method, start_date, include_start_date))
            elif record.finish_selection == 'date':
                if record.frequence_selection == 'workshift':
                    events.extend(cls.create_workshift_events_until_date(
                        record, create_method, start_date, include_start_date))
                else:
                    events.extend(cls.create_events_until_date(
                        record, create_method, start_date, include_start_date))
            else:
                raise UserError(gettext(
                    'lims_tools.missing_end_condition'))
                #events.append(create_method(record))
        return events

    @classmethod
    def create_fixed_events(cls, record, create_method,
            start_date=None, include_start_date=True):
        pool = Pool()
        LabWorkYear = pool.get('lims.lab.workyear')

        workyear_id = LabWorkYear.find()
        workyear = LabWorkYear(workyear_id)

        ruleset = rrule.rruleset()
        byweekday = None
        if record.only_workdays:
            # TODO: handle minutes and hours
            min_time = datetime.min.time()
            for h in workyear.holidays:
                ruleset.exdate(datetime.combine(h.date, min_time))
            byweekday = workyear.workdays

        freq = {
            'minutes': rrule.MINUTELY,
            'hours': rrule.HOURLY,
            'days': rrule.DAILY,
            'weeks': rrule.WEEKLY,
            'months': rrule.MONTHLY,
            'years': rrule.YEARLY,
            }[record.detail_frequence_selection]
        count = record.detail_frequence + 1

        if not start_date:
            start_date = record.start_date
        date = start_date

        if not include_start_date:
            ruleset.rrule(rrule.rrule(freq, count=count,
                dtstart=date, byweekday=byweekday))
            date = ruleset[-1]

        events = []
        while len(events) < record.end_repetition:
            event = {}
            if record.specific_event_time:
                date = date.replace(
                    hour=record.specific_event_time.hour,
                    minute=record.specific_event_time.minute,
                    second=record.specific_event_time.second
                    )
            event['scheduled_date'] = date
            event['week_day'] = date.weekday()
            new_event = create_method(record, event)
            if new_event:
                events.append(new_event)

            ruleset.rrule(rrule.rrule(freq, count=count,
                dtstart=date, byweekday=byweekday))
            date = ruleset[-1]

        return events

    @classmethod
    def create_workshift_fixed_events(cls, record, create_method,
            start_date=None, include_start_date=True):
        pool = Pool()
        Company = pool.get('company.company')
        LabWorkYear = pool.get('lims.lab.workyear')
        WorkShift = pool.get('lims.lab.workyear.shift')

        workyear_id = LabWorkYear.find()
        workyear = LabWorkYear(workyear_id)

        workyear_shifts = WorkShift.search([
            ('workyear', '=', workyear_id),
            ('shift', 'in', [s for s in record.shifts]),
            ])
        if not workyear_shifts:
            return []

        company = Company(Transaction().context.get('company'))
        company_timezone = company.get_timezone()

        ruleset = rrule.rruleset()
        byweekday = None
        if record.only_workdays:
            # TODO: handle minutes and hours
            min_time = datetime.min.time()
            for h in workyear.holidays:
                ruleset.exdate(datetime.combine(h.date, min_time))
            byweekday = workyear.workdays

        freq = {
            'minutes': rrule.MINUTELY,
            'hours': rrule.HOURLY,
            'days': rrule.DAILY,
            'weeks': rrule.WEEKLY,
            'months': rrule.MONTHLY,
            'years': rrule.YEARLY,
            }[record.detail_frequence_selection]
        count = record.detail_frequence + 1

        specific_times = []
        for ws in workyear_shifts:
            if record.shift_time in ['start', 'start_end']:
                specific_times.append(ws.shift.start_time)
            if record.shift_time in ['end', 'start_end']:
                specific_times.append(ws.shift.end_time)

        if not start_date:
            start_date = record.start_date
        date = start_date

        if not include_start_date:
            ruleset.rrule(rrule.rrule(freq, count=count,
                dtstart=date, byweekday=byweekday))
            date = ruleset[-1]

        events = []
        while len(events) < record.end_repetition:
            for specific_time in specific_times:
                event = {}
                event_date = company_timezone.localize(date.replace(
                    hour=specific_time.hour,
                    minute=specific_time.minute,
                    second=specific_time.second
                    ))
                event['scheduled_date'] = event_date
                event['week_day'] = date.weekday()
                new_event = create_method(record, event)
                if new_event:
                    events.append(new_event)
                if len(events) == record.end_repetition:
                    break

            ruleset.rrule(rrule.rrule(freq, count=count,
                dtstart=date, byweekday=byweekday))
            date = ruleset[-1]

        return events

    @classmethod
    def create_events_until_date(cls, record, create_method,
            start_date=None, include_start_date=True):
        pool = Pool()
        LabWorkYear = pool.get('lims.lab.workyear')

        workyear_id = LabWorkYear.find()
        workyear = LabWorkYear(workyear_id)

        ruleset = rrule.rruleset()
        byweekday = None
        if record.only_workdays:
            # TODO: handle minutes and hours
            min_time = datetime.min.time()
            for h in workyear.holidays:
                ruleset.exdate(datetime.combine(h.date, min_time))
            byweekday = workyear.workdays

        freq = {
            'minutes': rrule.MINUTELY,
            'hours': rrule.HOURLY,
            'days': rrule.DAILY,
            'weeks': rrule.WEEKLY,
            'months': rrule.MONTHLY,
            'years': rrule.YEARLY,
            }[record.detail_frequence_selection]
        count = record.detail_frequence + 1

        max_time = datetime.max.time()
        end_date = datetime.combine(record.end_date, max_time)

        if not start_date:
            start_date = record.start_date
        date = start_date

        if not include_start_date:
            ruleset.rrule(rrule.rrule(freq, count=count,
                dtstart=date, byweekday=byweekday))
            date = ruleset[-1]

        events = []
        while date < end_date:
            event = {}
            event['scheduled_date'] = date
            event['week_day'] = date.weekday()
            new_event = create_method(record, event)
            if new_event:
                events.append(new_event)

            ruleset.rrule(rrule.rrule(freq, count=count,
                dtstart=date, byweekday=byweekday))
            date = ruleset[-1]

        return events

    @classmethod
    def create_workshift_events_until_date(cls, record, create_method,
            start_date=None, include_start_date=True):
        pool = Pool()
        Company = pool.get('company.company')
        LabWorkYear = pool.get('lims.lab.workyear')
        WorkShift = pool.get('lims.lab.workyear.shift')

        workyear_id = LabWorkYear.find()
        workyear = LabWorkYear(workyear_id)

        workyear_shifts = WorkShift.search([
            ('workyear', '=', workyear_id),
            ('shift', 'in', [s for s in record.shifts]),
            ])
        if not workyear_shifts:
            return []

        company = Company(Transaction().context.get('company'))
        company_timezone = company.get_timezone()

        ruleset = rrule.rruleset()
        byweekday = None
        if record.only_workdays:
            # TODO: handle minutes and hours
            min_time = datetime.min.time()
            for h in workyear.holidays:
                ruleset.exdate(datetime.combine(h.date, min_time))
            byweekday = workyear.workdays

        freq = {
            'minutes': rrule.MINUTELY,
            'hours': rrule.HOURLY,
            'days': rrule.DAILY,
            'weeks': rrule.WEEKLY,
            'months': rrule.MONTHLY,
            'years': rrule.YEARLY,
            }[record.detail_frequence_selection]
        count = record.detail_frequence + 1

        specific_times = []
        for ws in workyear_shifts:
            if record.shift_time in ['start', 'start_end']:
                specific_times.append(ws.shift.start_time)
            if record.shift_time in ['end', 'start_end']:
                specific_times.append(ws.shift.end_time)

        max_time = datetime.max.time()
        end_date = datetime.combine(record.end_date, max_time)

        if not start_date:
            start_date = record.start_date
        date = start_date

        if not include_start_date:
            ruleset.rrule(rrule.rrule(freq, count=count,
                dtstart=date, byweekday=byweekday))
            date = ruleset[-1]

        events = []
        while date < end_date:
            for specific_time in specific_times:
                event = {}
                event_date = company_timezone.localize(date.replace(
                    hour=specific_time.hour,
                    minute=specific_time.minute,
                    second=specific_time.second
                    ))
                event['scheduled_date'] = event_date
                event['week_day'] = date.weekday()
                new_event = create_method(record, event)
                if new_event:
                    events.append(new_event)

            ruleset.rrule(rrule.rrule(freq, count=count,
                dtstart=date, byweekday=byweekday))
            date = ruleset[-1]

        return events


class Event():
    name = fields.Char('Name')
    description = fields.Text('Description')
    scheduled_date = fields.DateTime('Scheduled Date')
    week_day = fields.Selection(WEEK_DAYS, 'Week Day', readonly=True)
    responsible_user = fields.Many2One('res.user', 'User')
    notification = fields.Boolean('Notificate user')
    notification_timing = fields.Float('Notification Timing')
    notification_timing_unit = fields.Selection(DETAIL_FREQUENCE_OPTIONS,
        'Notification Timing unit')
