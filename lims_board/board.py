# This file is part of lims_board module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from dateutil.relativedelta import relativedelta

from trytond.model import ModelSQL, ModelView, fields
from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.i18n import gettext

DEPARTMENTS_LIMIT = 30
SAMPLES_IN_PROGRESS = ['pending_planning', 'planned',
    'in_lab', 'lab_pending_acceptance',
    'pending_report', 'in_report']
SAMPLES_IN_LABORATORY = ['pending_planning', 'planned',
    'in_lab', 'lab_pending_acceptance']


class BoardGeneral(ModelSQL, ModelView):
    'General Dashboard'
    __name__ = 'lims.board.general'

    refresh = fields.Boolean('Refresh')
    date_from = fields.Date('From Date')
    date_to = fields.Date('To Date')
    parties = fields.Many2Many('party.party', None, None, 'Parties')
    departments = fields.Many2Many('company.department', None, None,
        'Departments')
    analysis = fields.Many2Many('lims.analysis', None, None, 'Services',
        domain=[
            ('state', '=', 'active'),
            ('behavior', '!=', 'additional'),
            ('disable_as_individual', '=', False),
            ])

    samples = fields.Many2Many('lims.sample', None, None,
        'Samples in progress', states={'readonly': True})
    samples_state = fields.One2Many('lims.board.general.sample_state',
        None, 'Samples per State', states={'readonly': True})
    samples_department = fields.One2Many(
        'lims.board.general.sample_department', None,
        'Samples per Department', states={'readonly': True})
    samples_report_date = fields.One2Many(
        'lims.board.laboratory.sample_report_date',
        None, 'Samples per Date agreed for result', states={'readonly': True})

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._buttons.update({
            'apply_filter': {},
            })

    _filters = ['refresh', 'date_from', 'date_to', 'parties',
        'departments', 'analysis', 'samples', 'samples_state',
        'samples_department', 'samples_report_date']

    @staticmethod
    def default_refresh():
        return True

    @fields.depends(*_filters)
    def on_change_refresh(self):
        self.apply_filter()

    @ModelView.button_change(*_filters)
    def apply_filter(self):
        self.samples = self.get_samples()
        self.samples_state = self.get_samples_state()
        self.samples_department = self.get_samples_department()
        self.samples_report_date = self.get_samples_report_date()

    def get_samples(self, name=None):
        pool = Pool()
        Sample = pool.get('lims.sample')

        clause = [('state', 'in', SAMPLES_IN_PROGRESS)]
        if self.date_from:
            clause.append(('date2', '>=', self.date_from))
        if self.date_to:
            clause.append(('date2', '<=', self.date_to))
        if self.parties:
            clause.append(('party', 'in', [p.id for p in self.parties]))
        if self.departments:
            clause.append(('department', 'in',
                [d.id for d in self.departments]))
        if self.analysis:
            clause.append(('fractions.services.analysis', 'in',
                [a.id for a in self.analysis]))

        samples = Sample.search(clause + [
            ('fractions.services.urgent', '=', True),
            ])
        records = [s.id for s in samples]

        samples = Sample.search(clause + [
            ('fractions.services.urgent', '=', False),
            ])
        records.extend([s.id for s in samples])

        return records

    def get_samples_state(self):
        pool = Pool()
        Sample = pool.get('lims.sample')

        clause = []
        if self.date_from:
            clause.append(('date2', '>=', self.date_from))
        if self.date_to:
            clause.append(('date2', '<=', self.date_to))
        if self.parties:
            clause.append(('party', 'in', [p.id for p in self.parties]))
        if self.departments:
            clause.append(('department', 'in',
                [d.id for d in self.departments]))
        if self.analysis:
            clause.append(('fractions.services.analysis', 'in',
                [a.id for a in self.analysis]))

        records = []

        for state in SAMPLES_IN_PROGRESS:
            record = {
                's': gettext('lims_board.msg_sample_state_%s' % state),
                }
            record['q'] = Sample.search_count(clause + [
                ('state', '=', state),
                ])
            records.append(record)

        return records

    def get_samples_department(self):
        pool = Pool()
        Sample = pool.get('lims.sample')
        Department = pool.get('company.department')

        clause = [('state', 'in', SAMPLES_IN_PROGRESS)]
        if self.date_from:
            clause.append(('date2', '>=', self.date_from))
        if self.date_to:
            clause.append(('date2', '<=', self.date_to))
        if self.parties:
            clause.append(('party', 'in', [p.id for p in self.parties]))
        if self.departments:
            clause.append(('department', 'in',
                [d.id for d in self.departments]))
        if self.analysis:
            clause.append(('fractions.services.analysis', 'in',
                [a.id for a in self.analysis]))

        records = []

        departments = Department.search([], order=[('id', 'ASC')])
        for d in departments:
            record = {'d': d.name}
            record['q'] = Sample.search_count(clause + [
                ('department', '=', d.id),
                ])
            records.append(record)

        return records

    def get_samples_report_date(self):
        pool = Pool()
        Sample = pool.get('lims.sample')
        Department = pool.get('company.department')
        Date = pool.get('ir.date')

        i = 0
        dep = {None: ''}
        departments = Department.search([], order=[('id', 'ASC')],
            limit=DEPARTMENTS_LIMIT)
        for d in departments:
            i += 1
            dep[d.id] = i

        clause = [('state', 'in', SAMPLES_IN_PROGRESS)]
        if self.date_from:
            clause.append(('date2', '>=', self.date_from))
        if self.date_to:
            clause.append(('date2', '<=', self.date_to))
        if self.parties:
            clause.append(('party', 'in', [p.id for p in self.parties]))
        if self.departments:
            clause.append(('department', 'in',
                [d.id for d in self.departments]))
        if self.analysis:
            clause.append(('fractions.services.analysis', 'in',
                [a.id for a in self.analysis]))

        records = []
        today = Date.today()

        # < -4 d
        report_date = today - relativedelta(days=4)
        record = {'t': '< -4 d'}
        for d_id, d_it in dep.items():
            record['q%s' % d_it] = Sample.search_count(clause + [
                ('report_date', '<=', report_date),
                ('department', '=', d_id),
                ])
        records.append(record)

        # -3 d
        report_date = today - relativedelta(days=3)
        record = {'t': '-3 d'}
        for d_id, d_it in dep.items():
            record['q%s' % d_it] = Sample.search_count(clause + [
                ('report_date', '=', report_date),
                ('department', '=', d_id),
                ])
        records.append(record)

        # -2 d
        report_date = today - relativedelta(days=2)
        record = {'t': '-2 d'}
        for d_id, d_it in dep.items():
            record['q%s' % d_it] = Sample.search_count(clause + [
                ('report_date', '=', report_date),
                ('department', '=', d_id),
                ])
        records.append(record)

        # -1 d
        report_date = today - relativedelta(days=1)
        record = {'t': gettext('lims_board.msg_yesterday')}
        for d_id, d_it in dep.items():
            record['q%s' % d_it] = Sample.search_count(clause + [
                ('report_date', '=', report_date),
                ('department', '=', d_id),
                ])
        records.append(record)

        # t
        record = {'t': gettext('lims_board.msg_today')}
        for d_id, d_it in dep.items():
            record['q%s' % d_it] = Sample.search_count(clause + [
                ('report_date', '=', today),
                ('department', '=', d_id),
                ])
        records.append(record)

        # +1 d
        report_date = today + relativedelta(days=1)
        record = {'t': gettext('lims_board.msg_tomorrow')}
        for d_id, d_it in dep.items():
            record['q%s' % d_it] = Sample.search_count(clause + [
                ('report_date', '=', report_date),
                ('department', '=', d_id),
                ])
        records.append(record)

        # +2 d
        report_date = today + relativedelta(days=2)
        record = {'t': '+2 d'}
        for d_id, d_it in dep.items():
            record['q%s' % d_it] = Sample.search_count(clause + [
                ('report_date', '=', report_date),
                ('department', '=', d_id),
                ])
        records.append(record)

        # +3 d
        report_date = today + relativedelta(days=3)
        record = {'t': '+3 d'}
        for d_id, d_it in dep.items():
            record['q%s' % d_it] = Sample.search_count(clause + [
                ('report_date', '=', report_date),
                ('department', '=', d_id),
                ])
        records.append(record)

        # > +4 d
        report_date = today + relativedelta(days=4)
        record = {'t': '> +4 d'}
        for d_id, d_it in dep.items():
            record['q%s' % d_it] = Sample.search_count(clause + [
                ['OR',
                    ('report_date', '=', None),
                    ('report_date', '>=', report_date),
                    ],
                ('department', '=', d_id),
                ])
        records.append(record)

        return records


class BoardGeneralSampleState(ModelView):
    'General Dashboard - Sample state'
    __name__ = 'lims.board.general.sample_state'

    s = fields.Char('State', readonly=True)
    q = fields.Integer('Samples Qty.', readonly=True)


class BoardGeneralSampleDepartment(ModelView):
    'General Dashboard - Sample department'
    __name__ = 'lims.board.general.sample_department'

    d = fields.Char('Department', readonly=True)
    q = fields.Integer('Samples Qty.', readonly=True)


class BoardLaboratorySampleReportDate(ModelView):
    'Laboratory Dashboard - Sample report date'
    __name__ = 'lims.board.laboratory.sample_report_date'

    t = fields.Char('T', readonly=True)
    q = fields.Integer('Samples Qty.', readonly=True)

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.__rpc__['fields_view_get'].cache = None
        for i in range(1, DEPARTMENTS_LIMIT + 1):
            setattr(cls, 'q%s' % str(i),
                fields.Integer(cls.q.string, readonly=True))

    @classmethod
    def fields_view_get(cls, view_id=None, view_type='form', level=None):
        if Pool().test:
            return

        view_info = getattr(cls, 'get_%s_view' % view_type)()
        res = {
            'view_id': view_id,
            'type': view_info['type'],
            'arch': view_info['arch'],
            'fields': view_info['fields'],
            'field_childs': None,
            }
        return res

    @classmethod
    def get_tree_view(cls):
        pool = Pool()
        Department = pool.get('company.department')
        Translation = pool.get('ir.translation')
        language = Transaction().language

        fields = []
        definition = {}

        fields.append('<field name="t"/>')
        definition['t'] = {
            'name': 't',
            'string': (Translation.get_source('%s,t' % cls.__name__,
                'field', language, cls.t.string) or cls.t.string),
            'type': 'char',
            'readonly': True,
            'help': None,
            }

        fields.append('<field name="q"/>')
        definition['q'] = {
            'name': 'q',
            'string': gettext('lims_board.msg_no_department'),
            'type': 'integer',
            'readonly': True,
            'help': None,
            }

        i = 0
        departments = Department.search([], order=[('id', 'ASC')],
            limit=DEPARTMENTS_LIMIT)
        for d in departments:
            i += 1
            name = 'q%s' % str(i)
            fields.append('<field name="%s"/>' % name)
            definition[name] = {
                'name': name,
                'string': d.name,
                'type': 'integer',
                'readonly': True,
                'help': None,
                }

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

    @classmethod
    def get_graph_view(cls):
        pool = Pool()
        Department = pool.get('company.department')
        Translation = pool.get('ir.translation')
        language = Transaction().language

        fields = []
        definition = {}

        definition['t'] = {
            'name': 't',
            'string': (Translation.get_source('%s,t' % cls.__name__,
                'field', language, cls.t.string) or cls.t.string),
            'type': 'char',
            'readonly': True,
            'help': None,
            }

        fields.append('<field name="q"/>')
        definition['q'] = {
            'name': 'q',
            'string': gettext('lims_board.msg_no_department'),
            'type': 'integer',
            'readonly': True,
            'help': None,
            }

        i = 0
        departments = Department.search([], order=[('id', 'ASC')],
            limit=DEPARTMENTS_LIMIT)
        for d in departments:
            i += 1
            name = 'q%s' % str(i)
            fields.append('<field name="%s"/>' % name)
            definition[name] = {
                'name': name,
                'string': d.name,
                'type': 'integer',
                'readonly': True,
                'help': None,
                }

        xml = ('<?xml version="1.0"?>\n'
            '<graph type="vbar" legend="1">\n'
            '<x><field name="t"/></x>\n'
            '<y>\n''%s\n''</y>\n'
            '</graph>') % ('\n'.join(fields))
        res = {
            'type': 'graph',
            'arch': xml,
            'fields': definition,
            }
        return res


class BoardLaboratory(ModelSQL, ModelView):
    'Laboratory Dashboard'
    __name__ = 'lims.board.laboratory'

    refresh = fields.Boolean('Refresh')
    date_from = fields.Date('From Date')
    date_to = fields.Date('To Date')
    parties = fields.Many2Many('party.party', None, None, 'Parties')
    departments = fields.Many2Many('company.department', None, None,
        'Departments')
    analysis = fields.Many2Many('lims.analysis', None, None, 'Services',
        domain=[
            ('state', '=', 'active'),
            ('behavior', '!=', 'additional'),
            ('disable_as_individual', '=', False),
            ])

    samples = fields.Many2Many('lims.sample', None, None,
        'Samples in Laboratory', states={'readonly': True})
    samples_laboratory_date = fields.One2Many(
        'lims.board.laboratory.sample_laboratory_date',
        None, 'Samples per Laboratory deadline', states={'readonly': True})

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._buttons.update({
            'apply_filter': {},
            })

    _filters = ['refresh', 'date_from', 'date_to', 'parties',
        'departments', 'analysis', 'samples', 'samples_laboratory_date']

    @staticmethod
    def default_refresh():
        return True

    @fields.depends(*_filters)
    def on_change_refresh(self):
        self.apply_filter()

    @ModelView.button_change(*_filters)
    def apply_filter(self):
        self.samples = self.get_samples()
        self.samples_laboratory_date = self.get_samples_laboratory_date()

    def get_samples(self, name=None):
        pool = Pool()
        Sample = pool.get('lims.sample')

        clause = [('state', 'in', SAMPLES_IN_LABORATORY)]
        if self.date_from:
            clause.append(('date2', '>=', self.date_from))
        if self.date_to:
            clause.append(('date2', '<=', self.date_to))
        if self.parties:
            clause.append(('party', 'in', [p.id for p in self.parties]))
        if self.departments:
            clause.append(('department', 'in',
                [d.id for d in self.departments]))
        if self.analysis:
            clause.append(('fractions.services.analysis', 'in',
                [a.id for a in self.analysis]))

        samples = Sample.search(clause + [
            ('fractions.services.urgent', '=', True),
            ])
        records = [s.id for s in samples]

        samples = Sample.search(clause + [
            ('fractions.services.urgent', '=', False),
            ])
        records.extend([s.id for s in samples])

        return records

    def get_samples_laboratory_date(self):
        pool = Pool()
        Sample = pool.get('lims.sample')
        Department = pool.get('company.department')
        Date = pool.get('ir.date')

        i = 0
        dep = {None: ''}
        departments = Department.search([], order=[('id', 'ASC')],
            limit=DEPARTMENTS_LIMIT)
        for d in departments:
            i += 1
            dep[d.id] = i

        clause = [('state', 'in', SAMPLES_IN_LABORATORY)]
        if self.date_from:
            clause.append(('date2', '>=', self.date_from))
        if self.date_to:
            clause.append(('date2', '<=', self.date_to))
        if self.parties:
            clause.append(('party', 'in', [p.id for p in self.parties]))
        if self.departments:
            clause.append(('department', 'in',
                [d.id for d in self.departments]))
        if self.analysis:
            clause.append(('fractions.services.analysis', 'in',
                [a.id for a in self.analysis]))

        records = []
        today = Date.today()

        # < -4 d
        laboratory_date = today - relativedelta(days=4)
        record = {'t': '< -4 d'}
        for d_id, d_it in dep.items():
            record['q%s' % d_it] = Sample.search_count(clause + [
                ('laboratory_date', '<=', laboratory_date),
                ('department', '=', d_id),
                ])
        records.append(record)

        # -3 d
        laboratory_date = today - relativedelta(days=3)
        record = {'t': '-3 d'}
        for d_id, d_it in dep.items():
            record['q%s' % d_it] = Sample.search_count(clause + [
                ('laboratory_date', '=', laboratory_date),
                ('department', '=', d_id),
                ])
        records.append(record)

        # -2 d
        laboratory_date = today - relativedelta(days=2)
        record = {'t': '-2 d'}
        for d_id, d_it in dep.items():
            record['q%s' % d_it] = Sample.search_count(clause + [
                ('laboratory_date', '=', laboratory_date),
                ('department', '=', d_id),
                ])
        records.append(record)

        # -1 d
        laboratory_date = today - relativedelta(days=1)
        record = {'t': gettext('lims_board.msg_yesterday')}
        for d_id, d_it in dep.items():
            record['q%s' % d_it] = Sample.search_count(clause + [
                ('laboratory_date', '=', laboratory_date),
                ('department', '=', d_id),
                ])
        records.append(record)

        # t
        record = {'t': gettext('lims_board.msg_today')}
        for d_id, d_it in dep.items():
            record['q%s' % d_it] = Sample.search_count(clause + [
                ('laboratory_date', '=', today),
                ('department', '=', d_id),
                ])
        records.append(record)

        # +1 d
        laboratory_date = today + relativedelta(days=1)
        record = {'t': gettext('lims_board.msg_tomorrow')}
        for d_id, d_it in dep.items():
            record['q%s' % d_it] = Sample.search_count(clause + [
                ('laboratory_date', '=', laboratory_date),
                ('department', '=', d_id),
                ])
        records.append(record)

        # +2 d
        laboratory_date = today + relativedelta(days=2)
        record = {'t': '+2 d'}
        for d_id, d_it in dep.items():
            record['q%s' % d_it] = Sample.search_count(clause + [
                ('laboratory_date', '=', laboratory_date),
                ('department', '=', d_id),
                ])
        records.append(record)

        # +3 d
        laboratory_date = today + relativedelta(days=3)
        record = {'t': '+3 d'}
        for d_id, d_it in dep.items():
            record['q%s' % d_it] = Sample.search_count(clause + [
                ('laboratory_date', '=', laboratory_date),
                ('department', '=', d_id),
                ])
        records.append(record)

        # > +4 d
        laboratory_date = today + relativedelta(days=4)
        record = {'t': '> +4 d'}
        for d_id, d_it in dep.items():
            record['q%s' % d_it] = Sample.search_count(clause + [
                ['OR',
                    ('laboratory_date', '=', None),
                    ('laboratory_date', '>=', laboratory_date),
                    ],
                ('department', '=', d_id),
                ])
        records.append(record)

        return records


class BoardLaboratorySampleLaboratoryDate(ModelView):
    'Laboratory Dashboard - Sample laboratory date'
    __name__ = 'lims.board.laboratory.sample_laboratory_date'

    t = fields.Char('T', readonly=True)
    q = fields.Integer('Samples Qty.', readonly=True)

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.__rpc__['fields_view_get'].cache = None
        for i in range(1, DEPARTMENTS_LIMIT + 1):
            setattr(cls, 'q%s' % str(i),
                fields.Integer(cls.q.string, readonly=True))

    @classmethod
    def fields_view_get(cls, view_id=None, view_type='form', level=None):
        if Pool().test:
            return

        view_info = getattr(cls, 'get_%s_view' % view_type)()
        res = {
            'view_id': view_id,
            'type': view_info['type'],
            'arch': view_info['arch'],
            'fields': view_info['fields'],
            'field_childs': None,
            }
        return res

    @classmethod
    def get_tree_view(cls):
        pool = Pool()
        Department = pool.get('company.department')
        Translation = pool.get('ir.translation')
        language = Transaction().language

        fields = []
        definition = {}

        fields.append('<field name="t"/>')
        definition['t'] = {
            'name': 't',
            'string': (Translation.get_source('%s,t' % cls.__name__,
                'field', language, cls.t.string) or cls.t.string),
            'type': 'char',
            'readonly': True,
            'help': None,
            }

        fields.append('<field name="q"/>')
        definition['q'] = {
            'name': 'q',
            'string': gettext('lims_board.msg_no_department'),
            'type': 'integer',
            'readonly': True,
            'help': None,
            }

        i = 0
        departments = Department.search([], order=[('id', 'ASC')],
            limit=DEPARTMENTS_LIMIT)
        for d in departments:
            i += 1
            name = 'q%s' % str(i)
            fields.append('<field name="%s"/>' % name)
            definition[name] = {
                'name': name,
                'string': d.name,
                'type': 'integer',
                'readonly': True,
                'help': None,
                }

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

    @classmethod
    def get_graph_view(cls):
        pool = Pool()
        Department = pool.get('company.department')
        Translation = pool.get('ir.translation')
        language = Transaction().language

        fields = []
        definition = {}

        definition['t'] = {
            'name': 't',
            'string': (Translation.get_source('%s,t' % cls.__name__,
                'field', language, cls.t.string) or cls.t.string),
            'type': 'char',
            'readonly': True,
            'help': None,
            }

        fields.append('<field name="q"/>')
        definition['q'] = {
            'name': 'q',
            'string': gettext('lims_board.msg_no_department'),
            'type': 'integer',
            'readonly': True,
            'help': None,
            }

        i = 0
        departments = Department.search([], order=[('id', 'ASC')],
            limit=DEPARTMENTS_LIMIT)
        for d in departments:
            i += 1
            name = 'q%s' % str(i)
            fields.append('<field name="%s"/>' % name)
            definition[name] = {
                'name': name,
                'string': d.name,
                'type': 'integer',
                'readonly': True,
                'help': None,
                }

        xml = ('<?xml version="1.0"?>\n'
            '<graph type="vbar" legend="1">\n'
            '<x><field name="t"/></x>\n'
            '<y>\n''%s\n''</y>\n'
            '</graph>') % ('\n'.join(fields))
        res = {
            'type': 'graph',
            'arch': xml,
            'fields': definition,
            }
        return res
