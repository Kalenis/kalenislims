# This file is part of lims_tools module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from datetime import timedelta

from trytond.model import Model, fields
from trytond.pyson import Eval
from trytond.exceptions import UserError
from trytond.i18n import gettext


FREQUENCE_OPTIONS = [
    ('hourly', 'Hourly'),
    ('daily', 'Daily'),
    ('weekly', 'Weekly'),
    ('15_days', 'Every 15 days'),
    ('monthly', 'Monthly'),
    ('yearly', 'Yearly'),
    ('customize', 'Customize'),
    ]

FREQUENCE_OPTIONS_VALUE_MAP = {
    'hourly': (1, 'hours'),
    'daily': (1, 'days'),
    'weekly': (1, 'weeks'),
    '15_days': (15, 'days'),
    'monthly': (1, 'months'),
    'yearly': (1, 'years'),
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


class EventCreator(Model):
    'Event Creator'

    start_date = fields.DateTime('Start Date', required=True)
    frequence_selection = fields.Selection(
        FREQUENCE_OPTIONS,
        'Select Frequence', sort=False)
    detail_frequence = fields.Float('Frequence', required=True)
    detail_frequence_selection = fields.Selection(
        DETAIL_FREQUENCE_OPTIONS,
        'Frequence', required=True, sort=False)
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
        states={
            'invisible': Eval('frequence_selection') != 'weekly',
            },
        depends=['frequence_selection'])
    specific_time = fields.Time('Specific Time',
        states={
            'invisible': Eval('frequence_selection') != 'daily',
            },
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
            },
        depends=['finish_selection'])
    end_date = fields.DateTime('End Date',
        states={
            'invisible': Eval('finish_selection') != 'date',
            'required': Eval('finish_selection') == 'date',
            },
        depends=['finish_selection'])

    @fields.depends('frequence_selection')
    def on_change_frequence_selection(self):
        if self.frequence_selection:
            self.detail_frequence, self.detail_frequence_selection = (
                FREQUENCE_OPTIONS_VALUE_MAP[self.frequence_selection])

    @classmethod
    def create_events(cls, records, create_method, start_date=None, include_start_date=True):
        events = []
        for record in records:
            if record.finish_selection == 'quantity':
                events.extend(
                    cls.create_fixed_events(record, create_method, start_date, include_start_date))
            elif record.finish_selection == 'date':
                events.extend(
                    cls.create_events_until_date(record, create_method, start_date, include_start_date))
            else:
                raise UserError(gettext(
                    'lims_tools.missing_end_condition'))
                #events.append(create_method(record))
        return events

    @classmethod
    def create_fixed_events(cls, record, create_method, start_date=None, include_start_date=True):
        events = []
        if not start_date:
            start_date = record.start_date
        frequence = record.detail_frequence
        frequence_selection = record.detail_frequence_selection

        date = start_date
        if not include_start_date:
            date = date + cls.get_delta(frequence, frequence_selection)
        while len(events) < record.end_repetition:
            event = {}
            event['scheduled_date'] = date
            event['week_day'] = date.weekday()
            date = date + cls.get_delta(frequence, frequence_selection)
            new_event = create_method(record, event)
            if new_event:
                events.append(new_event)
        return events

    @classmethod
    def create_events_until_date(cls, record, create_method, start_date=None, include_start_date=True):
        events = []
        if not start_date:
            start_date = record.start_date
        frequence = record.detail_frequence
        frequence_selection = record.detail_frequence_selection

        date = start_date
        if not include_start_date:
            date = date + cls.get_delta(frequence, frequence_selection)
        while date < record.end_date:
            event = {}
            event['scheduled_date'] = date
            event['week_day'] = date.weekday()
            date = date + cls.get_delta(frequence, frequence_selection)
            new_event = create_method(record, event)
            if new_event:
                events.append(new_event)
        return events

    @classmethod
    def get_delta(cls, frequence, unit):
        if unit == 'minutes':
            return timedelta(minutes=frequence)
        elif unit == 'hours':
            return timedelta(hours=frequence)
        elif unit == 'days':
            return timedelta(days=frequence)
        elif unit == 'weeks':
            return timedelta(weeks=frequence)
        elif unit == 'months':
            return timedelta(days=frequence * 30)
        elif unit == 'years':
            return timedelta(days=frequence * 365)
        return timedelta()
