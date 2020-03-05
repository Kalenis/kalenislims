# -*- coding: utf-8 -*-
# This file is part of lims_interface module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import sql
import formulas
import schedula
import unidecode
import io
import csv
import hashlib
from openpyxl import load_workbook
from decimal import Decimal
from datetime import datetime, date, time
from dateutil import relativedelta

from trytond.config import config
from trytond.model import (Workflow, ModelView, ModelSQL, fields,
    sequence_ordered, Unique)
from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.pyson import Eval, Bool, Not, And, Or
from trytond.i18n import gettext
from trytond.exceptions import UserError
from .function import custom_functions


__all__ = ['Interface', 'Column', 'Compilation', 'CompilationOrigin']


FUNCTIONS = formulas.get_functions()
FUNCTIONS.update(custom_functions)

FIELD_TYPES = [
    ('char', 'char', 'Text (single-line)', 'fields.Char', 'VARCHAR', str,
        None),
    ('multiline', 'text', 'Text (multi-line)', 'fields.Text', 'VARCHAR',
        str, None),
    ('integer', 'integer', 'Integer', 'fields.Integer', 'INTEGER', int, None),
    ('float', 'float', 'Float', 'fields.Float', 'FLOAT', float, None),
    ('numeric', 'numeric', 'Numeric', 'fields.Numeric', 'NUMERIC', Decimal,
        None),
    ('boolean', 'boolean', 'Boolean', 'fields.Boolean', 'BOOLEAN', bool,
        None),
    ('many2one', 'many2one', 'Link To Kalenis', 'fields.Many2One', 'INTEGER',
        int, None),
    ('date', 'date', 'Date', 'fields.Date', 'DATE', date, None),
    ('datetime', 'datetime', 'Date Time', 'fields.DateTime', 'DATETIME',
        datetime, None),
    ('time', 'time', 'Time', 'fields.Time', 'TIME', time, None),
    ('timestamp', 'timestamp', 'Timestamp', 'fields.Timestamp', 'TIMESTAMP',
        datetime, None),
    ('timedelta', 'timedelta', 'Time Interval', 'fields.TimeDelta', 'INTERVAL',
        relativedelta, None),
    ('icon', 'char', 'Icon', 'fields.Char', 'VARCHAR', str, None),
    ('image', 'binary', 'Image', 'fields.Binary', 'BLOB', bytes, bytearray),
    ('binary', 'binary', 'File', 'fields.Binary', 'BLOB', bytes, bytearray),
    ('reference', 'reference', 'Reference', 'fields.Reference', 'VARCHAR', str,
        None),
    ]

FIELD_TYPE_SELECTION = [(x[0], x[2]) for x in FIELD_TYPES]
FIELD_TYPE_SQL = dict([(x[0], x[4]) for x in FIELD_TYPES])
FIELD_TYPE_CLASS = dict([(x[0], x[3]) for x in FIELD_TYPES])
FIELD_TYPE_PYTHON = dict([(x[0], x[5]) for x in FIELD_TYPES])
FIELD_TYPE_TRYTON = dict([(x[0], x[1]) for x in FIELD_TYPES])
FIELD_TYPE_CAST = dict([(x[0], x[6]) for x in FIELD_TYPES])

VALID_FIRST_SYMBOLS = 'abcdefghijklmnopqrstuvwxyz'
VALID_NEXT_SYMBOLS = '_0123456789'
VALID_SYMBOLS = VALID_FIRST_SYMBOLS + VALID_NEXT_SYMBOLS

BLOCKSIZE = 65536

INTERFACE_STATES = [
    ('draft', 'Draft'),
    ('active', 'Active'),
    ('canceled', 'Canceled'),
    ]

if config.getboolean('lims_interface', 'filestore', default=False):
    file_id = 'origin_file_id'
    store_prefix = config.get('lims_interface', 'store_prefix', default=None)
else:
    file_id = None
    store_prefix = None


def convert_to_symbol(text):
    if not text:
        return 'x'
    text = unidecode.unidecode(text)
    text = text.lower()
    first = text[0]
    symbol = first
    if first not in VALID_FIRST_SYMBOLS:
        symbol = '_'
        if symbol in VALID_SYMBOLS:
            symbol += first

    for x in text[1:]:
        if x not in VALID_SYMBOLS and symbol[-1] != '_':
            symbol += '_'
        else:
            symbol += x
    return symbol


class Interface(Workflow, ModelSQL, ModelView):
    'Interface'
    __name__ = 'lims.interface'

    _controller_states = {
        'invisible': Eval('kind') != 'controller',
        'required': Eval('kind') == 'controller',
        'readonly': Eval('state') != 'draft'
        }
    _template_states = {
        'invisible': Eval('kind') != 'template',
        'required': Eval('kind') == 'template',
        'readonly': Eval('state') != 'draft',
        }
    _depends = ['kind', 'state']

    name = fields.Char('Name', required=True)
    revision = fields.Integer('Revision', required=True, readonly=True)
    language = fields.Many2One('ir.lang', 'Language',
        states={'readonly': Eval('state') != 'draft'}, depends=['state'],
        domain=[('translatable', '=', True)])
    kind = fields.Selection([
        ('template', 'Template'),
        ('controller', 'Controller'),
        ], 'Kind', required=True, states={
            'readonly': Eval('state') != 'draft',
            }, depends=['state'])
    state = fields.Selection(INTERFACE_STATES, 'State',
        readonly=True, required=True)
    controller_name = fields.Selection([(None, '')], 'Controller Name',
        sort=False, states=_controller_states, depends=_depends)
    columns = fields.One2Many('lims.interface.column', 'interface', 'Columns',
        states={
            'readonly': Eval('state') != 'draft',
            'invisible': Eval('kind') != 'template',
            }, depends=_depends)
    table = fields.Many2One('lims.interface.table', 'Table', readonly=True)
    template_type = fields.Selection([
        (None, ''),
        ('excel', 'Excel'),
        ('csv', 'Comma Separated Values'),
        ('txt', 'Text File'),
        ], 'Template Type',
        states=_template_states, depends=_depends)
    first_row = fields.Integer('First Row',
        states=_template_states, depends=_depends)
    field_separator = fields.Selection([
        ('comma', 'Comma (,)'),
        ('colon', 'Colon (:)'),
        ('semicolon', 'Semicolon (;)'),
        ('tab', 'Tab'),
        ('space', 'Space'),
        ('other', 'Other')],
        'Field separator',
        states={
            'required': And(Eval('kind') == 'template',
                Eval('template_type') == 'csv'),
            'invisible': Or(Eval('kind') != 'template',
                Eval('template_type') != 'csv'),
            'readonly': Eval('state') != 'draft',
        }, depends=['kind', 'template_type', 'state'])
    field_separator_other = fields.Char('Other',
        states={
            'required': And(Eval('template_type') == 'csv',
                Eval('field_separator') == 'other'),
            'invisible': Or(Eval('template_type') != 'csv',
                Eval('field_separator') != 'other'),
            'readonly': Eval('state') != 'draft',
            }, depends=['template_type', 'field_separator', 'state'])
    analysis_field = fields.Many2One('lims.interface.column',
        'Analysis field',
        domain=[('interface', '=', Eval('id'))],
        states={
            'readonly': Eval('state') != 'draft',
            }, depends=['state', 'id'])
    fraction_field = fields.Many2One('lims.interface.column',
        'Fraction field',
        domain=[('interface', '=', Eval('id'))],
        states={
            'readonly': Eval('state') != 'draft',
            }, depends=['state', 'id'])
    repetition_field = fields.Many2One('lims.interface.column',
        'Repetition field',
        domain=[('interface', '=', Eval('id'))],
        states={
            'readonly': Eval('state') != 'draft',
            }, depends=['state', 'id'])
    notebook_line_field = fields.Many2One('lims.interface.column',
        'Notebook line field',
        domain=[('interface', '=', Eval('id'))],
        states={
            'readonly': Eval('state') != 'draft',
            }, depends=['state', 'id'])
    charset = fields.Selection([
        (None, ''),
        ('utf-8', 'UTF-8'),
        ('iso-8859', 'ISO-8859')], 'Charset')
    # methods = fields.Many2Many('lims.interface-lims.lab.method',
    #     'interface', 'method', 'Method')

    @classmethod
    def __setup__(cls):
        super(Interface, cls).__setup__()
        cls._transitions |= set((
            ('draft', 'active'),
            ('active', 'canceled'),
            ('active', 'draft'),
            ))
        cls._buttons.update({
            'draft': {
                'icon': 'tryton-undo',
                'invisible': Eval('state') != 'active',
                },
            'activate': {
                'icon': 'tryton-ok',
                'invisible': Eval('state') != 'draft',
                },
            })

    @staticmethod
    def default_revision():
        return 0

    @staticmethod
    def default_kind():
        return 'template'

    @staticmethod
    def default_charset():
        return 'utf-8'

    @staticmethod
    def default_field_separator():
        return 'semicolon'

    @staticmethod
    def default_state():
        return 'draft'

    @property
    def data_table_name(self):
        return ('lims.interface.table.data.%d.%d' % (self.id or 0,
                self.revision)).replace('.', '_')

    @classmethod
    @ModelView.button
    @Workflow.transition('draft')
    def draft(cls, interfaces):
        pass

    @classmethod
    @ModelView.button
    @Workflow.transition('active')
    def activate(cls, interfaces):
        pool = Pool()
        Table = pool.get('lims.interface.table')
        Field = pool.get('lims.interface.table.field')

        for interface in interfaces:
            # interface.check_formulas()
            # interface.check_icons()

            interface.revision += 1
            table = Table()
            table.name = interface.data_table_name
            fields = []
            for column in interface.columns:
                if not column.type_:
                    continue
                fields.append(Field(
                        name=column.alias,
                        string=column.name,
                        type=column.type_,
                        help=column.expression,
                        related_model=column.related_model,
                        formula=(column.expression if column.expression and
                            column.expression.startswith('=') else None),
                        ))
            table.fields_ = fields
            table.create_table()
            table.save()
            interface.table = table

        cls.save(interfaces)
        cls.set_views(interfaces)

    @classmethod
    def set_views(cls, interfaces):
        View = Pool().get('lims.interface.table.view')

        to_delete = []
        to_save = []
        for interface in interfaces:
            if interface.table:
                to_delete += View.search([
                    ('table', '=', interface.table),
                    ])

            for view_type in ['tree', 'form']:
                view = View()
                view.table = interface.table
                view_info = getattr(interface, 'get_%s_view' % view_type)()
                view.arch = view_info['arch']
                view.type = view_info['type']
                to_save.append(view)

        if to_delete:
            View.delete(to_delete)
        if to_save:
            View.save(to_save)

    def get_tree_view(self):
        fields = []
        current_icon = None
        for line in self.table.fields_:
            if line.type in ('datetime', 'timestamp'):
                fields.append('<field name="%s" widget="date"/>\n' %
                    line.name)
                fields.append('<field name="%s" widget="time"/>\n' %
                    line.name)
                continue
            if line.type == 'icon':
                current_icon = line.name
                continue
            attributes = []
            if current_icon:
                attributes.append('icon="%s"' % current_icon)
                current_icon = None
            if line.type == 'image':
                attributes.append('widget="image"')

            fields.append('<field name="%s" %s/>\n' % (line.name,
                    ' '.join(attributes)))

        xml = ('<?xml version="1.0"?>\n'
            '<tree editable="bottom">\n'
            '%s'
            '</tree>') % ('\n'.join(fields))
        return {
            'type': 'tree',
            'arch': xml,
            }

    def get_form_view(self):
        fields = []
        for line in self.table.fields_:
            fields.append('<label name="%s"/>' % line.name)
            if line.type in ('datetime', 'timestamp'):
                fields.append('<group col="2">'
                    '<field name="%s" widget="date"/>'
                    '<field name="%s" widget="time"/>'
                    '</group>' % (line.name, line.name))
                continue
            if line.type == 'icon':
                fields.append('<image name="%s"/>\n' %
                        (line.name))
                continue

            attributes = []
            if line.type == 'image':
                attributes.append('widget="image"')

            fields.append('<field name="%s" %s/>\n' % (line.name,
                    ' '.join(attributes)))

        xml = ('<?xml version="1.0"?>\n'
            '<form>\n'
            '%s'
            '</form>') % '\n'.join(fields)
        return {
            'type': 'form',
            'arch': xml,
            }


class Column(sequence_ordered(), ModelSQL, ModelView):
    'Column'
    __name__ = 'lims.interface.column'

    interface = fields.Many2One('lims.interface', 'Interface',
        required=True, ondelete='CASCADE')
    name = fields.Char('Name', required=True)
    alias = fields.Char('Alias', required=True,
        states={'readonly': Eval('interface_state') != 'draft'},
        depends=['interface_state'])
    evaluation_order = fields.Integer('Evaluation order')
    expression = fields.Char('Formula')
    expression_icon = fields.Function(fields.Char('Expression Icon'),
        'on_change_with_expression_icon')
    type_ = fields.Selection([
        (None, ''),
        ('char', 'Text (single-line)'),
        ('multiline', 'Text (multi-line)'),
        ('integer', 'Integer'),
        ('float', 'Float'),
        ('numeric', 'Numeric'),
        ('boolean', 'Boolean'),
        ('many2one', 'Link To Kalenis'),
        ('date', 'Date'),
        ('datetime', 'Date Time'),
        ('time', 'Time'),
        ('timestamp', 'Timestamp'),
        ('timedelta', 'Time Interval'),
        ('icon', 'Icon'),
        ('image', 'Image'),
        ('binary', 'File'),
        ('reference', 'Reference'),
        ], 'Field Type')
    related_model = fields.Many2One('ir.model', 'Related Model',
        states={
            'required': Eval('type_') == 'many2one',
            'invisible': Eval('type_') != 'many2one',
        }, depends=['type_'])
    source_start = fields.Integer('Field start',
        states={
            'required': Eval('_parent_interface',
                {}).get('template_type') == 'txt',
            'invisible': Eval('_parent_interface',
                {}).get('template_type') != 'txt',
        })
    source_end = fields.Integer('Field end',
        states={
            'required': Eval('_parent_interface',
                {}).get('template_type') == 'txt',
            'invisible': Eval('_parent_interface',
                {}).get('template_type') != 'txt',
        })
    source_column = fields.Integer('Column',
        help='Mapped column in source file')
    singleton = fields.Boolean('Is a singleton value',
        help='Is a fixed value (column:row) in source file')
    source_row = fields.Integer('Row',
        states={
            'required': Bool(Eval('singleton')),
            'invisible': Not(Eval('singleton'))
        }, depends=['singleton'])
    transfer_field = fields.Boolean('Transfer field',
        help='Check if value have to be transferred to notebook line')
    related_line_field = fields.Many2One('ir.model.field', 'Related field',
        domain=[('model.model', '=', 'lims.notebook.line')],
        states={
            'required': Bool(Eval('transfer_field')),
            'invisible': Not(Eval('transfer_field'))
        }, depends=['transfer_field'])
    interface_state = fields.Function(fields.Selection(INTERFACE_STATES,
        'Interface State'), 'on_change_with_interface_state')
    # device_type = fields.Many2One('lims.lab.device.type', 'Device Type')

    @classmethod
    def __setup__(cls):
        super(Column, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('interface_alias_uniq',
                Unique(t, t.interface, sql.Column(t, 'alias')),
                'There cannot be two columns with the same alias '
                'in an interface.')
            ]

    @fields.depends('name', 'alias', 'interface',
        '_parent_interface.columns', 'evaluation_order')
    def on_change_name(self):
        if not self.alias:
            self.alias = convert_to_symbol(self.name)
        if not self.evaluation_order and self.interface:
            self.evaluation_order = len(self.interface.columns)

    @fields.depends('interface', '_parent_interface.state')
    def on_change_with_interface_state(self, name=None):
        if self.interface:
            return self.interface.state

    @classmethod
    def validate(cls, columns):
        for column in columns:
            column.check_alias()

    def check_alias(self):
        for symbol in self.alias:
            if symbol not in VALID_SYMBOLS:
                raise UserError(gettext('lims_interface.invalid_alias',
                    symbol=symbol, name=self.name))

    def formula_error(self):
        if not self.expression:
            return
        if not self.expression.startswith('='):
            return
        parser = formulas.Parser()
        try:
            builder = parser.ast(self.expression)[1]
            # Find missing methods:
            # https://github.com/vinci1it2000/formulas/issues/19#issuecomment-429793111
            missing_methods = [k for k, v in builder.dsp.function_nodes.items()
                if v['function'] is formulas.functions.not_implemented]
            if missing_methods:
                # When there are two occurrences of the same missing method,
                # the function name returned looks like this:
                #
                # Sample formula: A(x) + A(y)
                # missing_methods: ['A', 'A<0>']
                #
                # So in the line below we remove the '<0>' suffix
                missing_methods = {x.split('<')[0] for x in missing_methods}
                if len(missing_methods) == 1:
                    msg = 'Unknown method: '
                else:
                    msg = 'Unknown methods: '
                msg += (', '.join(missing_methods))
                return ('error', msg)

            ast = builder.compile()
            missing = (set([x.lower() for x in ast.inputs]) -
                self.previous_formulas())
            if not missing:
                return
            return ('warning', 'Referenced alias "%s" not found. Ensure it is '
                'declared before this formula.' % ', '.join(missing))
        except formulas.errors.FormulaError as error:
            msg = error.msg.replace('\n', ' ')
            if error.args[1:]:
                msg = msg % error.args[1:]
            return ('error', msg)

    def previous_formulas(self):
        res = []
        for formula in self.interface.columns:
            if formula == self:
                break
            res.append(formula.alias)
        return set(res)

    @fields.depends('expression', 'interface', '_parent_interface.columns')
    def on_change_with_expression_icon(self, name=None):
        if not self.expression:
            return ''
        if not self.expression.startswith('='):
            return ''
        error = self.formula_error()
        if not error:
            return 'lims-green'
        if error[0] == 'warning':
            return 'lims-yellow'
        return 'lims-red'


class Compilation(Workflow, ModelSQL, ModelView):
    'Interface Compilation'
    __name__ = 'lims.interface.compilation'

    date_time = fields.DateTime('Date', required=True, select=True)
    interface = fields.Many2One('lims.interface', 'Device Interface',
        domain=[('state', '=', 'active')])
    revision = fields.Integer('Revision', states={
            'readonly': Eval('state') != 'draft',
            }, depends=['state'])
    table_name = fields.Char('Table name')
    table = fields.Function(fields.Many2One('lims.interface.table',
        'Table'), 'get_table')
    device = fields.Many2One('lims.lab.device', 'Device')
    data = fields.One2Many('lims.interface.data', 'compilation', 'Data')
    origins = fields.One2Many('lims.interface.compilation.origin',
       'compilation', 'Origins')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('validated', 'Validated'),
        ('done', 'Done'),
        ], 'State', readonly=True, required=True)

    @classmethod
    def __setup__(cls):
        super(Compilation, cls).__setup__()
        cls._transitions |= set((
            ('draft', 'active'),
            ('active', 'draft'),
            ('active', 'validated'),
            ('validated', 'done'),
            ))
        cls._buttons.update({
            'view_data': {
                'invisible': Eval('state') == 'draft',
                },
            'draft': {
                'invisible': Eval('state') != 'active',
                },
            'activate': {
                'invisible': Eval('state') != 'draft',
                },
            'collect': {
                'invisible': Eval('state') != 'active',
                },
            'validate_': {
                'invisible': Eval('state') != 'active',
                },
            'confirm': {
                'invisible': Eval('state') != 'validated',
                },
            })

    def get_rec_name(self, name):
        return self.interface.rec_name + ' / ' + str(self.revision)

    @staticmethod
    def default_date_time():
        return datetime.now()

    @staticmethod
    def default_state():
        return 'draft'

    def get_table(self, name):
        Table = Pool().get('lims.interface.table')
        if not self.interface or not self.revision:
            return None
        table_name = ('lims_interface_table_data_%d_%d' % (
            self.interface.id, self.revision))
        table_id = Table.search([('name', '=', table_name)])
        return table_id[0] if table_id else None

    @fields.depends('interface', 'revision')
    def on_change_interface(self):
        self.revision = self.interface.revision if self.interface else None

    @classmethod
    @ModelView.button_action('lims_interface.act_open_compilation_data')
    def view_data(cls, compilations):
        pass

    @classmethod
    @ModelView.button
    @Workflow.transition('draft')
    def draft(cls, compilations):
        pass

    @classmethod
    @ModelView.button
    @Workflow.transition('active')
    def activate(cls, compilations):
        pass

    @classmethod
    @ModelView.button_action('lims_interface.act_open_compilation_data')
    def collect(cls, compilations):
        for c in compilations:
            if c.interface.kind == 'template':
                getattr(c, 'collect_%s' % c.interface.template_type)()

    def collect_csv(self):
        pool = Pool()
        Origin = pool.get('lims.interface.compilation.origin')
        Data = pool.get('lims.interface.data')

        data = []
        schema, formula_fields = self._get_schema()
        schema_keys = list(schema.keys())
        separator = {
            'comma': ',',
            'colon': ':',
            'semicolon': ';',
            'tab': '\t',
            'space': ' ',
            'other': self.interface.field_separator_other,
            }
        delimiter = separator[self.interface.field_separator]
        first_row = self.interface.first_row - 1
        with Transaction().set_context(
                lims_interface_table=self.interface.table):
            imported_files = []
            for origin in self.origins:
                if origin.imported:
                    continue
                filedata = io.BytesIO(origin.origin_file)
                wrapper = io.TextIOWrapper(filedata, encoding='utf-8')
                str_data = io.StringIO(wrapper.read())
                reader = csv.reader(str_data, delimiter=delimiter)
                count = 0
                for row in reader:
                    if count < first_row:
                        count += 1
                        continue
                    if len(row) == 0:
                        continue
                    line = {'compilation': self.id}
                    for k in schema_keys:
                        col = schema[k]['col']
                        if not row[col - 1] or not str(row[col - 1]).strip():
                            line[k] = None
                            continue
                        if schema[k]['type'] == 'integer':
                            line[k] = int(row[col - 1])
                        elif schema[k]['type'] == 'float':
                            line[k] = float(row[col - 1])
                        elif schema[k]['type'] == 'date':
                            line[k] = self.str2date(
                                str(row[col - 1]), self.interface.language)
                        else:
                            line[k] = str(row[col - 1])

                    f_fields = sorted(formula_fields.items(),
                        key=lambda x: x[1]['evaluation_order'])
                    for field in f_fields:
                        line[field[0]] = self._get_formula_value(field, line)

                    nb_line = self._get_notebook_line(line)
                    if nb_line and self.interface.notebook_line_field:
                        nbl_alias = self.interface.notebook_line_field.alias
                        line[nbl_alias] = nb_line.id
                    data.append(line)
                    count += 1
                imported_files.append(origin)

            if imported_files:
                Origin.write(imported_files, {'imported': True})
            if data:
                Data.create(data)

    def collect_excel(self):
        pool = Pool()
        Origin = pool.get('lims.interface.compilation.origin')
        Data = pool.get('lims.interface.data')

        data = []
        schema, formula_fields = self._get_schema()
        schema_keys = list(schema.keys())
        first_row = self.interface.first_row
        with Transaction().set_context(
                lims_interface_table=self.interface.table):
            imported_files = []
            for origin in self.origins:
                if origin.imported:
                    continue
                filedata = io.BytesIO(origin.origin_file)
                book = load_workbook(filename=filedata)
                sheet = book.active
                max_row = sheet.max_row + 1
                if first_row <= max_row:
                    for i in range(first_row, max_row):
                        line = {'compilation': self.id}
                        for k in schema_keys:
                            col = schema[k]['col']
                            row = i
                            if schema[k]['singleton']:
                                row = schema[k]['row']
                            value = sheet.cell(row=row, column=col).value
                            if value is None:
                                line[k] = None
                                continue
                            if schema[k]['type'] == 'integer':
                                line[k] = int(value)
                            elif schema[k]['type'] == 'float':
                                line[k] = float(value)
                            elif schema[k]['type'] == 'date':
                                if isinstance(value, datetime):
                                    line[k] = value
                                else:
                                    line[k] = None
                            else:
                                line[k] = str(value)

                        f_fields = sorted(formula_fields.items(),
                            key=lambda x: x[1]['evaluation_order'])
                        for field in f_fields:
                            line[field[0]] = self._get_formula_value(
                                field, line)

                        nb_line = self._get_notebook_line(line)
                        if nb_line and self.interface.notebook_line_field:
                            nbl_alias = \
                                self.interface.notebook_line_field.alias
                            line[nbl_alias] = nb_line.id
                        data.append(line)

                imported_files.append(origin)

            if imported_files:
                Origin.write(imported_files, {'imported': True})
            if data:
                Data.create(data)

    def _get_schema(self):
        schema = {}
        formula_fields = {}
        for column in self.interface.columns:
            if column.source_column:
                schema[column.alias] = {
                    'col': column.source_column,
                    'type': column.type_,
                    'singleton': False,
                    }
                if column.singleton:
                    schema[column.alias].update({
                        'singleton': True,
                        'row': column.source_row,
                        })
            if column.expression:
                formula_fields[column.alias] = {
                    'type': column.type_,
                    'formula': column.expression,
                    'evaluation_order': column.evaluation_order,
                    }
        return schema, formula_fields

    def _get_formula_value(self, field, line):
        parser = formulas.Parser()
        ast = parser.ast(
            field[1]['formula'])[1].compile()
        inputs = (' '.join([x for x in ast.inputs])
            ).lower().split()
        inputs = [line[x] for x in inputs]
        try:
            value = ast(*inputs)
        except schedula.utils.exc.DispatcherError as e:
            self.raise_user_error(e.args[0] % e.args[1:])

        if isinstance(value, list):
            value = str(value)
        elif (not isinstance(value, str) and
                not isinstance(value, int) and
                not isinstance(value, float) and
                not isinstance(value, type(None))):
            value = value.tolist()
        if isinstance(value, formulas.tokens.operand.XlError):
            value = None
        return value

    def _get_notebook_line(self, line):
        pool = Pool()
        Fraction = pool.get('lims.fraction')
        Analysis = pool.get('lims.analysis')
        Notebook = pool.get('lims.notebook')
        NotebookLine = pool.get('lims.notebook.line')

        if (self.interface.analysis_field and
                self.interface.fraction_field and
                self.interface.repetition_field and
                self.interface.notebook_line_field):
            analysis_value = line[self.interface.analysis_field.alias]
            fraction_value = line[self.interface.fraction_field.alias]
            repetition_value = line[self.interface.repetition_field.alias]

            fraction = Fraction.search([
                ('number', '=', fraction_value)
                ])
            if fraction and repetition_value is not None:
                nb = Notebook.search([
                    ('fraction', '=', fraction[0].id)
                    ])
                analysis = Analysis.search([
                    ('code', '=', analysis_value),
                    ('automatic_acquisition', '=', True),
                    ])
                if nb and analysis:
                    nb_line = NotebookLine.search([
                        ('notebook', '=', nb[0].id),
                        ('analysis', '=', analysis[0].id),
                        ('repetition', '=', repetition_value),
                        ])
                    if nb_line:
                        return nb_line[0]
        return None

    @staticmethod
    def str2date(value, lang=None):
        Lang = Pool().get('ir.lang')
        if lang is None:
            lang = Lang.get()
        try:
            return datetime.strptime(value, lang.date)
        except:
            return datetime.strptime(value, '%Y/%m/%d')

    @classmethod
    @ModelView.button
    @Workflow.transition('validated')
    def validate_(cls, compilations):
        pool = Pool()
        Data = pool.get('lims.interface.data')

        for c in compilations:
            nbl_alias = None
            if c.interface.notebook_line_field:
                nbl_alias = c.interface.notebook_line_field.alias
            if not nbl_alias:
                raise UserError(gettext(
                    'lims_interface.no_notebook_line_field_defined'))
            result_fields = {}
            for column in c.interface.columns:
                if column.transfer_field:
                    result_fields[column.alias] = {
                        'type': column.type_,
                        'field_name': column.related_line_field.name,
                        }
            with Transaction().set_context(
                    lims_interface_table=c.interface.table):
                lines = Data.search([
                    ('compilation', '=', c.id)
                    ])
                for l in lines:
                    nbl_id = getattr(l, nbl_alias)
                    print('*** nbl_id: ', nbl_id)
                    if result_fields:
                        for res in result_fields:
                            # TODO: check values and correct type
                            value = getattr(l, res)
                            print('RES: ', res, ': ', value, ' - ',
                                  result_fields[res]['type'],
                                  result_fields[res]['field_name'])

    @classmethod
    @ModelView.button
    @Workflow.transition('done')
    def confirm(cls, compilations):
        pool = Pool()
        Data = pool.get('lims.interface.data')
        NotebookLine = pool.get('lims.notebook.line')

        for c in compilations:
            nbl_alias = None
            if c.interface.notebook_line_field:
                nbl_alias = c.interface.notebook_line_field.alias
            result_fields = {}
            for column in c.interface.columns:
                if column.transfer_field:
                    result_fields[column.alias] = {
                        'type': column.type_,
                        'field_name': column.related_line_field.name,
                        }
            with Transaction().set_context(
                    lims_interface_table=c.interface.table):
                lines = Data.search([
                    ('compilation', '=', c.id)
                    ])
                for l in lines:
                    nbl_id = getattr(l, nbl_alias)
                    if nbl_id and result_fields:
                        nbl = NotebookLine.browse([nbl_id])
                        data = {}
                        for res in result_fields:
                            value = getattr(l, res)
                            data[result_fields[res]['field_name']] = value
                        if nbl and data:
                            NotebookLine.write(nbl, data)


class CompilationOrigin(ModelSQL, ModelView):
    'Compilation Origin'
    __name__ = 'lims.interface.compilation.origin'

    compilation = fields.Many2One('lims.interface.compilation',
    'Compilation', required=True, ondelete='CASCADE')
    origin_file = fields.Binary("Origin File", filename='file_name',
        file_id=file_id, store_prefix=store_prefix)
    file_name = fields.Char('Name')
    origin_file_id = fields.Char("Origin File ID", readonly=True)
    imported = fields.Boolean('Imported', readonly=True)

    @staticmethod
    def default_imported():
        return False

    @classmethod
    def validate(cls, origins):
        super(CompilationOrigin, cls).validate(origins)
        for origin in origins:
            origin.check_duplicated()

    def check_duplicated(self):
        if len(self.origin_file) == 0:
            return
        for existing in self.compilation.origins:
            if existing.id == self.id:
                continue
            if len(existing.origin_file) == len(self.origin_file):
                existing_f = io.BytesIO(existing.origin_file)
                ef_hash = hashlib.sha1()
                buf = existing_f.read(BLOCKSIZE)
                while len(buf) > 0:
                    ef_hash.update(buf)
                    buf = existing_f.read(BLOCKSIZE)
                new_f = io.BytesIO(self.origin_file)
                nf_hash = hashlib.sha1()
                buf = new_f.read(BLOCKSIZE)
                while len(buf) > 0:
                    nf_hash.update(buf)
                    buf = new_f.read(BLOCKSIZE)

                if ef_hash.hexdigest() == nf_hash.hexdigest():
                    raise UserError(gettext(
                        'lims_interface.duplicated_origin_file',
                        file_name=self.file_name))
