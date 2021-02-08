# -*- coding: utf-8 -*-
# This file is part of lims_interface module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from sql import (Table, Column as SqlColumn, Literal,
    Desc, Asc, NullsFirst, NullsLast)
from sql.aggregate import Count
import formulas
import schedula
from decimal import Decimal
from itertools import chain
from collections import defaultdict

from trytond.model import ModelSQL, ModelView, fields
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from trytond.tools import cursor_dict
from trytond.pyson import PYSONEncoder, Eval
from trytond.rpc import RPC
from trytond.exceptions import UserError
from trytond.model.modelsql import convert_from
from .interface import FIELD_TYPE_TRYTON, FIELD_TYPE_CAST


class Adapter:
    def __getattr__(self, name):
        fields = self.get_fields()
        return getattr(fields, name)

    def __contains__(self, key):
        fields = self.get_fields()
        return fields.__contains__(key)

    def __iter__(self):
        fields = self.get_fields()
        return fields.__iter__()

    def __getitem__(self, name):
        fields = self.get_fields()
        return fields.__getitem__(name)

    def get_fields(self):
        # TODO: Cache
        Data = Pool().get('lims.interface.data')
        table = Data.get_table()
        if not table:
            return Data._previous_fields
        res = {}
        groups = 0
        for field in table.fields_:
            if field.type == 'char':
                obj = fields.Char(field.string)
            elif field.type == 'multiline':
                obj = fields.Text(field.string)
            elif field.type == 'integer':
                obj = fields.Integer(field.string)
            elif field.type == 'float':
                obj = fields.Float(field.string)
            elif field.type == 'boolean':
                obj = fields.Boolean(field.string)
            elif field.type == 'numeric':
                obj = fields.Numeric(field.string)
            elif field.type == 'date':
                obj = fields.Date(field.string)
            elif field.type == 'datetime':
                obj = fields.DateTime(field.string)
            elif field.type == 'timestamp':
                obj = fields.Timestamp(field.string)
            elif field.type == 'many2one':
                obj = fields.Many2One(field.related_model.model, field.string)
            elif field.type in ('binary', 'icon'):
                obj = fields.Binary(field.string)
            elif field.type == 'selection':
                selection = [tuple(v.split(':', 1))
                    for v in field.selection.splitlines() if v]
                obj = fields.Selection(selection, field.string)
            obj.name = field.name
            res[field.name] = obj
            groups = max(groups, field.group or 0)
        obj = fields.Integer('ID')
        obj.name = 'id'
        res['id'] = obj
        obj = fields.Many2One('lims.interface.compilation', 'Compilation')
        obj.name = 'compilation'
        res['compilation'] = obj
        obj = fields.Many2One('lims.notebook.line', 'Notebook Line')
        obj.name = 'notebook_line'
        obj.readonly = True
        res['notebook_line'] = obj
        for i in range(0, groups):
            obj = fields.One2Many(
                'lims.interface.grouped_data', 'data', 'Group %s' % (i + 1, ))
            obj.name = 'group_%s' % (i + 1, )
            res[obj.name] = obj
        return res


class GroupedAdapter:
    def __getattr__(self, name):
        fields = self.get_fields()
        return getattr(fields, name)

    def __contains__(self, key):
        fields = self.get_fields()
        return fields.__contains__(key)

    def __iter__(self):
        fields = self.get_fields()
        return fields.__iter__()

    def __getitem__(self, name):
        fields = self.get_fields()
        return fields.__getitem__(name)

    def get_fields(self):
        GroupedData = Pool().get('lims.interface.grouped_data')
        table = GroupedData.get_table()
        if not table:
            return GroupedData._previous_fields
        res = {}
        for field in table.grouped_fields_:
            if field.type == 'char':
                obj = fields.Char(field.string)
            elif field.type == 'multiline':
                obj = fields.Text(field.string)
            elif field.type == 'integer':
                obj = fields.Integer(field.string)
            elif field.type == 'float':
                obj = fields.Float(field.string)
            elif field.type == 'boolean':
                obj = fields.Boolean(field.string)
            elif field.type == 'numeric':
                obj = fields.Numeric(field.string)
            elif field.type == 'date':
                obj = fields.Date(field.string)
            elif field.type == 'datetime':
                obj = fields.DateTime(field.string)
            elif field.type == 'timestamp':
                obj = fields.Timestamp(field.string)
            elif field.type == 'many2one':
                obj = fields.Many2One(field.related_model.model, field.string)
            elif field.type in ('binary', 'icon'):
                obj = fields.Binary(field.string)
            elif field.type == 'selection':
                selection = [tuple(v.split(':', 1))
                    for v in field.selection.splitlines() if v]
                obj = fields.Selection(selection, field.string)
            obj.name = field.name
            res[field.name] = obj
        obj = fields.Integer('ID')
        obj.name = 'id'
        res['id'] = obj
        obj = fields.Many2One('lims.notebook.line', 'Notebook Line')
        obj.name = 'notebook_line'
        obj.readonly = True
        res['notebook_line'] = obj
        obj = fields.Many2One('lims.interface.data', 'Data')
        obj.name = 'data'
        obj.readonly = True
        res['data'] = obj
        obj = fields.Integer('Iteration')
        obj.name = 'iteration'
        obj.readonly = True
        res['iteration'] = obj
        return res


class ModelAccess(metaclass=PoolMeta):
    __name__ = 'ir.model.access'

    @classmethod
    def check_relation(cls, model_name, field_name, mode='read'):
        '''
        We must override check_relation and ensure that super() does not
        execute:

        getattr(Model, fieldname)

        because the fields do not exist in the Model. If super() used
        Model._fields[fieldname] we would not be forced to override the method.
        '''
        if model_name in ('lims.interface.data',
                'lims.interface.grouped_data'):
            return True
        return super().check_relation(model_name, field_name, mode)


class Data(ModelSQL, ModelView):
    'Lims Interface Data'
    __name__ = 'lims.interface.data'

    compilation = fields.Many2One('lims.interface.compilation', 'Compilation',
        required=True, ondelete='CASCADE')
    notebook_line = fields.Many2One('lims.notebook.line', 'Notebook Line',
        readonly=True)

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order.insert(0, ('notebook_line.notebook', 'ASC'))
        cls._order.insert(1, ('notebook_line.analysis.order', 'ASC'))
        cls._order.insert(2, ('notebook_line.analysis.code', 'ASC'))
        cls.__rpc__['fields_view_get'].cache = None
        cls.__rpc__['default_get'].cache = None

    @classmethod
    def __post_setup__(cls):
        super().__post_setup__()
        cls._previous_fields = cls._fields
        cls._fields = Adapter()

    @classmethod
    def __table__(cls):
        # TODO: Check if we can drop create(), read(), write(), delete() &
        # search()
        return cls.get_sql_table()

    def __init__(self, id=None, **kwargs):
        kwargs_copy = kwargs.copy()
        for kw in kwargs_copy:
            kwargs.pop(kw, None)
        super().__init__(id, **kwargs)
        self._values = {}
        for kw in kwargs_copy:
            self._values[kw] = kwargs_copy[kw]

    def __getattr__(self, name):
        try:
            return super().__getattr__(name)
        except AttributeError:
            pass

    def on_change_with(self, fieldnames):
        table = self.get_table()
        res = {}

        grouped_fields = defaultdict(list)
        for field in table.fields_:
            if field.group:
                grouped_fields[field.group].append(field.name)

        for field in table.fields_:
            if field.name not in fieldnames:
                continue
            ast = field.get_ast()
            inputs = []
            for input_ in field.inputs.split():
                found = False
                for group, repetition_fields in grouped_fields.items():
                    if input_ in repetition_fields:
                        group_values = getattr(self, 'group_%s' % group)
                        if not group_values:
                            continue
                        for line in group_values:
                            if line['iteration'] == int(
                                    input_.split('_')[-1:][0]):
                                inputs.append(line[
                                    '_'.join(input_.split('_')[:-1])])
                        found = True
                if not found:
                    inputs.append(getattr(self, input_))

            try:
                value = ast(*inputs)
            except schedula.utils.exc.DispatcherError as e:
                raise UserError(e.args[0] % e.args[1:])

            if isinstance(value, list):
                value = str(value)
            elif not isinstance(value, (str, int, float, Decimal, type(None))):
                value = value.tolist()
            if isinstance(value, formulas.tokens.operand.XlError):
                value = None
            elif isinstance(value, list):
                for x in chain(*value):
                    if isinstance(x, formulas.tokens.operand.XlError):
                        value = None
            res[field.name] = value
        return res

    @classmethod
    def add_on_change_with_method(cls, field):
        """
        Dynamically add 'on_change_with_<field>' methods.
        """
        fn_name = 'on_change_with_' + field.name

        def fn(self):
            table = self.get_table()
            grouped_fields = defaultdict(list)
            for table_field in table.fields_:
                if table_field.group:
                    grouped_fields[table_field.group].append(table_field.name)

            ast = field.get_ast()
            inputs = []
            for input_ in field.inputs.split():
                found = False
                for group, repetition_fields in grouped_fields.items():
                    if input_ in repetition_fields:
                        group_values = getattr(self, 'group_%s' % group)
                        if not group_values:
                            continue
                        for line in group_values:
                            if line['iteration'] == int(
                                    input_.split('_')[-1:][0]):
                                inputs.append(line[
                                    '_'.join(input_.split('_')[:-1])])
                        found = True
                if not found:
                    inputs.append(getattr(self, input_))

            try:
                value = ast(*inputs)
            except schedula.utils.exc.DispatcherError as e:
                raise UserError(e.args[0] % e.args[1:])

            if isinstance(value, list):
                value = str(value)
            elif not isinstance(value, (str, int, float, Decimal, type(None))):
                value = value.tolist()
            if isinstance(value, formulas.tokens.operand.XlError):
                value = None
            elif isinstance(value, list):
                for x in chain(*value):
                    if isinstance(x, formulas.tokens.operand.XlError):
                        value = None
            return value

        setattr(cls, fn_name, fn)

    @classmethod
    def _get_readonly_notebook_lines(cls):
        readonly_ids = []
        compilation_id = Transaction().context.get(
            'lims_interface_compilation', None)
        if not compilation_id:
            return readonly_ids
        for line in cls.search([('compilation', '=', compilation_id)]):
            if line.notebook_line and line.notebook_line.end_date:
                readonly_ids.append(line.notebook_line.id)
        return readonly_ids

    @classmethod
    def fields_get(cls, fields_names=None, level=0):
        Model = Pool().get('ir.model')
        res = super().fields_get(fields_names)

        table = cls.get_table()
        interface = cls.get_interface()

        readonly_ids = []
        readonly = Transaction().context.get('lims_interface_readonly', False)
        if not readonly:
            readonly_ids = cls._get_readonly_notebook_lines()
        encoder = PYSONEncoder()
        groups = 0

        grouped_fields = defaultdict(list)
        for field in table.fields_:
            if field.group:
                grouped_fields[field.group].append(field.name)

        for field in table.fields_:
            groups = max(groups, field.group or 0)
            if field.group:
                continue
            states = {
                'readonly': (bool(readonly or field.formula or field.readonly)
                    or Eval('notebook_line').in_(readonly_ids)),
                }
            res[field.name] = {
                'name': field.name,
                'string': field.string,
                'type': FIELD_TYPE_TRYTON[field.type],
                'help': field.help,
                'domain': field.domain,
                'states': encoder.encode(states),
                'sortable': True,
                }
            if field.type == 'many2one':
                res[field.name]['relation'] = (field.related_model.model if
                    field.related_model else None)
            if field.type == 'selection':
                selection = [tuple(v.split(':', 1))
                    for v in field.selection.splitlines() if v]
                res[field.name]['selection'] = selection
                res[field.name]['selection_change_with'] = []
                res[field.name]['sort'] = False
            if field.type == 'reference':
                selection = []
                for model in Model.search([]):
                    selection.append((model.model, model.name))
                res[field.name]['selection'] = selection
            if field.type in ['date', 'time', 'datetime', 'timestamp']:
                res[field.name]['format'] = PYSONEncoder().encode(
                    '%H:%M:%S.%f')
            if field.type in ['float', 'numeric']:
                res[field.name]['digits'] = encoder.encode((16, field.digits))
            if field.inputs:
                inputs = []
                for input_ in field.inputs.split():
                    found = False
                    for group, repetition_fields in grouped_fields.items():
                        if input_ in repetition_fields:
                            inputs.append('group_%s' % group)
                            found = True
                    if not found:
                        inputs.append(input_)
                res[field.name]['on_change_with'] = list(set(inputs))
                cls.add_on_change_with_method(field)
                func_name = '%s_%s' % ('on_change_with', field.name)
                cls.__rpc__.setdefault(func_name, RPC(instantiate=0))

        for i in range(0, groups):
            field_description = None
            for rep in interface.grouped_repetitions:
                if rep.group == i + 1:
                    field_description = rep.description

            field_name = 'group_%s' % (i + 1)
            res[field_name] = {
                'name': field_name,
                'string': field_description or field_name,
                'type': 'one2many',
                'help': '',
                'relation': 'lims.interface.grouped_data',
                'relation_field': 'data',
                }
            res[field_name]['views'] = {
                'tree': GroupedData.fields_view_get(
                    view_type='tree', group=i + 1)}
            func_name = '%s_%s' % ('on_change_with', field_name)
            cls.__rpc__.setdefault(func_name, RPC(instantiate=0))
        return res

    @classmethod
    def fields_view_get(cls, view_id=None, view_type='form'):
        if Pool().test:
            return
        table = cls.get_table()
        for view in table.views:
            if view.type == view_type:
                break
        assert(view.id)

        fields_names = [
            'compilation',
            'notebook_line',
            ]
        groups = 0
        for field in table.fields_:
            groups = max(groups, field.group or 0)
            if field.group and view.type == 'form':
                continue
            fields_names.append(field.name)
        for i in range(0, groups):
            fields_names.append('group_%s' % (i + 1))
        res = {
            'type': view.type,
            'view_id': view_id,
            'field_childs': None,
            'arch': view.arch,
            'fields': cls.fields_get(fields_names),
            'model': cls.__name__,
            }
        return res

    @classmethod
    def search(cls, domain, offset=0, limit=None, order=None, count=False,
            query=False):
        cursor = Transaction().connection.cursor()

        # Clean transaction cache
        for cache in Transaction().cache.values():
            if cls.__name__ in cache:
                del cache[cls.__name__]

        if not cls.get_table():
            return super().search(domain, offset, limit, order, count, query)

        # Get domain clauses
        sql_table = cls.get_sql_table()
        tables, expression = cls.search_domain(domain,
            tables={None: (sql_table, None)})

        # Get order by
        order_by = []
        order_types = {
            'DESC': Desc,
            'ASC': Asc,
            }
        null_ordering_types = {
            'NULLS FIRST': NullsFirst,
            'NULLS LAST': NullsLast,
            None: lambda _: _
            }
        if order is None or order is False:
            order = cls._order
        for oexpr, otype in order:
            fname, _, extra_expr = oexpr.partition('.')
            field = cls._fields[fname]
            if not otype:
                otype, null_ordering = 'ASC', None
            else:
                otype = otype.upper()
                try:
                    otype, null_ordering = otype.split(' ', 1)
                except ValueError:
                    null_ordering = None
            Order = order_types[otype]
            NullOrdering = null_ordering_types[null_ordering]
            forder = field.convert_order(oexpr, tables, cls)
            order_by.extend((NullOrdering(Order(o)) for o in forder))

        main_table, _ = tables[None]
        table = convert_from(None, tables)

        if count:
            cursor.execute(*table.select(Count(Literal('*')),
                    where=expression, limit=limit, offset=offset))
            return cursor.fetchone()[0]

        columns = [main_table.id]
        select = table.select(*columns,
            where=expression, order_by=order_by, limit=limit, offset=offset)
        if query:
            return select

        cursor.execute(*select)
        res = [x[0] for x in cursor.fetchall()]
        return cls.browse(res)

    @classmethod
    def read(cls, ids, fields_names=None):
        sql_table = cls.get_sql_table()
        table = cls.get_table()

        if not ids:
            return []

        def read_related(field_name, Target, rows, fields):
            target_ids = []
            for row in rows:
                value = row[field_name]
                if value is not None:
                    target_ids.append(value)
            return Target.read(target_ids, fields)

        def add_related(field_name, rows, targets):
            '''
            Adds 'id' and 'rec_name' of many2one/related_model fields
            Also adds 'rec_name' for the rows
            '''
            key = field_name + '.'
            for row in rows:
                value = row[field_name]
                if isinstance(value, str):
                    value = int(value.split(',', 1)[1])
                if value is not None and value >= 0:
                    row[key] = targets[value]
                    if 'rec_name' in targets[value]:
                        row['rec_name'] = targets[value]['rec_name']
                else:
                    row[key] = None
                if 'rec_name' not in row:
                    row['rec_name'] = str(row['id'])

        cursor = Transaction().connection.cursor()
        cursor.execute(*sql_table.select(where=sql_table.id.in_(ids)))
        fetchall = list(cursor_dict(cursor))

        fields_related = {
            'compilation': 'lims.interface.compilation',
            'notebook_line': 'lims.notebook.line'
            }
        for f in table.fields_:
            if f.related_model is not None:
                fields_related[f.name] = f.related_model.model

        for field in fields_related:
            Target = Pool().get(fields_related[field])
            if Target:
                targets = read_related(
                    field, Target, fetchall, ['id', 'rec_name'])
                targets = {t['id']: t for t in targets}
            else:
                targets = {}
            add_related(field, fetchall, targets)

        to_cast = {}
        for field in table.fields_:
            if fields_names and field.name not in fields_names:
                continue
            cast = FIELD_TYPE_CAST[field.type]
            if cast:
                to_cast[field.name] = cast

        if to_cast:
            for record in fetchall:
                for field, cast in to_cast.items():
                    record[field] = cast(record[field])
        return fetchall

    @classmethod
    def create(cls, vlist):
        sql_table = cls.get_sql_table()
        cursor = Transaction().connection.cursor()

        ids = []
        for record in vlist:
            fields = []
            values = []
            for key, value in record.items():
                fields.append(SqlColumn(sql_table, key))
                values.append(value)

            query = sql_table.insert(fields, values=[values],
                returning=[sql_table.id])
            cursor.execute(*query)
            ids.append(cursor.fetchone()[0])
        records = cls.browse(ids)
        cls.update_formulas(records)
        return records

    @classmethod
    def write(cls, *args):
        sql_table = cls.get_sql_table()
        cursor = Transaction().connection.cursor()

        all_records = []
        actions = iter(args)
        for records, vals in zip(actions, actions):
            all_records += records
            fields = []
            values = []
            for key, value in vals.items():
                fields.append(SqlColumn(sql_table, key))
                values.append(value)

            query = sql_table.update(fields, values,
                where=sql_table.id.in_([x.id for x in records]))
            cursor.execute(*query)
        cls.update_formulas(all_records)

    @classmethod
    def update_formulas(cls, records=None):
        Column = Pool().get('lims.interface.column')
        cursor = Transaction().connection.cursor()

        table = cls.get_table()
        sql_table = cls.get_sql_table()
        interface = cls.get_interface()

        formula_fields = []
        for field in table.fields_:
            if not field.formula:
                continue
            col = Column.search([
                ('interface', '=', interface),
                ('alias', '=', field.name),
                ])
            order = col and col[0].evaluation_order or 0
            formula_fields.append({
                'order': order,
                'field': field,
                })
        if not formula_fields:
            return

        if not records:
            records = cls.search([])
        for record in records:
            vals = {}
            fields = []
            values = []
            for field in sorted(formula_fields, key=lambda x: x['order']):
                field_name = field['field'].name
                value = record.get_formula_value(field['field'], vals)
                if value is None:
                    continue
                fields.append(SqlColumn(sql_table, field_name))
                values.append(value)
                vals[field_name] = value

            if not values:
                continue
            query = sql_table.update(fields, values,
                where=(sql_table.id == record.id))
            cursor.execute(*query)

    def get_formula_value(self, field, vals={}):
        ast = field.get_ast()
        inputs = []
        if field.inputs:
            for x in field.inputs.split():
                inputs.append(vals.get(x, getattr(self, x)))
        try:
            value = ast(*inputs)
        except schedula.utils.exc.DispatcherError as e:
            raise UserError(e.args[0] % e.args[1:])

        if isinstance(value, list):
            value = str(value)
        elif not isinstance(value, (str, int, float, Decimal, type(None))):
            value = value.tolist()
        if isinstance(value, formulas.tokens.operand.XlError):
            value = None
        elif isinstance(value, list):
            for x in chain(*value):
                if isinstance(x, formulas.tokens.operand.XlError):
                    value = None
        return value

    @classmethod
    def delete(cls, records):
        sql_table = cls.get_sql_table()
        cursor = Transaction().connection.cursor()
        ids = [x.id for x in records if x.id > 0]
        if ids:
            query = sql_table.delete(where=sql_table.id.in_(ids))
            cursor.execute(*query)

    @classmethod
    def copy(cls, records, default=None):
        records = cls.read([x.id for x in records if x.id])
        for record in records:
            del record['id']
            del record['notebook_line']
        return cls.create(records)

    @classmethod
    def get_compilation(cls):
        Compilation = Pool().get('lims.interface.compilation')
        compilation_id = Transaction().context.get(
            'lims_interface_compilation')
        if compilation_id:
            return Compilation(compilation_id)

    @classmethod
    def get_table(cls):
        pool = Pool()
        Interface = pool.get('lims.interface')
        Table = pool.get('lims.interface.table')

        if Pool().test:
            # Tryton default tests try to get data using '1' as active_id
            # We prevent the tests from failing by returning no table
            return

        table = Transaction().context.get('lims_interface_table')
        if not table:
            compilation = cls.get_compilation()
            if compilation:
                table = compilation.table
        if (not table and
                Transaction().context.get('active_model') == 'lims.interface'):
            interface_id = Transaction().context.get('active_id', None)
            if interface_id:
                interface = Interface(interface_id)
                table = interface.table and interface.table.id or None
        if table:
            return Table(table)

    @classmethod
    def get_sql_table(cls):
        table = cls.get_table()
        if table:
            return Table(table.name)
        return super().__table__()

    @classmethod
    def get_interface(cls):
        pool = Pool()
        Compilation = pool.get('lims.interface.compilation')
        Interface = pool.get('lims.interface')

        compilation_id = Transaction().context.get(
            'lims_interface_compilation')
        if compilation_id:
            return Compilation(compilation_id).interface
        interface_id = (Transaction().context.get(
            'active_model') == 'lims.interface' and
            Transaction().context.get('active_id', None) or None)
        if interface_id:
            return Interface(interface_id)
        return None


class GroupedData(ModelView):
    'Grouped Data'
    __name__ = 'lims.interface.grouped_data'

    notebook_line = fields.Many2One('lims.notebook.line', 'Notebook Line',
        readonly=True)
    data = fields.Many2One('lims.inteface.data', 'Data',
        readonly=True)
    iteration = fields.Integer('Iteration', readonly=True)

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.__rpc__['fields_view_get'].cache = None
        cls.__rpc__['default_get'].cache = None

    @classmethod
    def __post_setup__(cls):
        super().__post_setup__()
        cls._previous_fields = cls._fields
        cls._fields = GroupedAdapter()

    def __init__(self, id=None, **kwargs):
        kwargs_copy = kwargs.copy()
        for kw in kwargs_copy:
            kwargs.pop(kw, None)
        super().__init__(id, **kwargs)
        self._values = {}
        for kw in kwargs_copy:
            self._values[kw] = kwargs_copy[kw]

    def __getattr__(self, name):
        try:
            return super().__getattr__(name)
        except AttributeError:
            pass

    def on_change_with(self, fieldnames):
        table = self.get_table()
        res = {}
        for field in table.grouped_fields_:
            if field.name not in fieldnames:
                continue
            ast = field.get_ast()
            inputs = field.get_inputs().split()
            inputs = [self.data.get(x) if x in self.data.keys()
                else getattr(self, x) for x in inputs]
            try:
                value = ast(*inputs)
            except schedula.utils.exc.DispatcherError as e:
                raise UserError(e.args[0] % e.args[1:])

            if isinstance(value, list):
                value = str(value)
            elif not isinstance(value, (str, int, float, Decimal, type(None))):
                value = value.tolist()
            if isinstance(value, formulas.tokens.operand.XlError):
                value = None
            elif isinstance(value, list):
                for x in chain(*value):
                    if isinstance(x, formulas.tokens.operand.XlError):
                        value = None
            res[field.name] = value
        return res

    @classmethod
    def add_on_change_with_method(cls, field):
        """
        Dynamically add 'on_change_with_<field>' methods.
        """
        fn_name = 'on_change_with_' + field.name

        def fn(self):
            ast = field.get_ast()
            inputs = field.get_inputs().split()
            inputs = [self.data.get(x) if x in self.data.keys()
                else getattr(self, x) for x in inputs]
            try:
                value = ast(*inputs)
            except schedula.utils.exc.DispatcherError as e:
                raise UserError(e.args[0] % e.args[1:])

            if isinstance(value, list):
                value = str(value)
            elif not isinstance(value, (str, int, float, Decimal, type(None))):
                value = value.tolist()
            if isinstance(value, formulas.tokens.operand.XlError):
                value = None
            elif isinstance(value, list):
                for x in chain(*value):
                    if isinstance(x, formulas.tokens.operand.XlError):
                        value = None
            return value

        setattr(cls, fn_name, fn)

    @classmethod
    def fields_get(cls, fields_names=None, group=0, level=0):
        Model = Pool().get('ir.model')
        Data = Pool().get('lims.interface.data')
        res = super().fields_get(fields_names)

        table = cls.get_table()
        readonly = Transaction().context.get('lims_interface_readonly', False)
        encoder = PYSONEncoder()

        for field in table.grouped_fields_:
            if field.group != group:
                continue
            res[field.name] = {
                'name': field.name,
                'string': field.string,
                'type': FIELD_TYPE_TRYTON[field.type],
                'readonly': bool(readonly or field.formula or field.readonly),
                'help': field.help,
                'domain': field.domain,
                'states': '{}',
                }
            if field.type == 'many2one':
                res[field.name]['relation'] = (field.related_model.model if
                    field.related_model else None)
            if field.type == 'selection':
                selection = [tuple(v.split(':', 1))
                    for v in field.selection.splitlines() if v]
                res[field.name]['selection'] = selection
                res[field.name]['selection_change_with'] = []
                res[field.name]['sort'] = False
            if field.type == 'reference':
                selection = []
                for model in Model.search([]):
                    selection.append((model.model, model.name))
                res[field.name]['selection'] = selection
            if field.type in ['date', 'time', 'datetime', 'timestamp']:
                res[field.name]['format'] = PYSONEncoder().encode(
                    '%H:%M:%S.%f')
            if field.type in ['float', 'numeric']:
                res[field.name]['digits'] = encoder.encode((16, field.digits))
            if field.inputs:
                res[field.name]['on_change_with'] = field.inputs.split() + [
                    'data']
                cls.add_on_change_with_method(field)
                func_name = '%s_%s' % ('on_change_with', field.name)
                cls.__rpc__.setdefault(func_name, RPC(instantiate=0))

        res['data'] = {
            'name': 'data',
            'string': 'Data',
            'type': 'many2one',
            'readonly': True,
            'help': '',
            'states': '{}',
            'relation': 'lims.interface.data',
            'relation_field': 'group_%s' % group,
            'relation_fields': (Data.fields_get(level=level - 1)
                if level > 0 else []),
            }
        return res

    @classmethod
    def fields_view_get(cls, view_id=None, view_type='form', group=0):
        if Pool().test:
            return
        table = cls.get_table()
        for view in table.grouped_views:
            if view.type == view_type and view.group == group:
                break
        assert(view.id)

        fields_names = [
            'notebook_line',
            'data',
            'iteration',
            ]
        for field in table.grouped_fields_:
            if field.group != group:
                continue
            fields_names.append(field.name)
        res = {
            'type': view.type,
            'view_id': view_id,
            'field_childs': None,
            'arch': view.arch,
            'fields': cls.fields_get(fields_names, group),
            'model': cls.__name__,
            }
        return res

    @classmethod
    def get_compilation(cls):
        Compilation = Pool().get('lims.interface.compilation')
        compilation_id = Transaction().context.get(
            'lims_interface_compilation')
        if compilation_id:
            return Compilation(compilation_id)

    @classmethod
    def get_table(cls):
        pool = Pool()
        Interface = pool.get('lims.interface')
        Table = pool.get('lims.interface.table')

        if Pool().test:
            # Tryton default tests try to get data using '1' as active_id
            # We prevent the tests from failing by returning no table
            return

        table = Transaction().context.get('lims_interface_table')
        if not table:
            compilation = cls.get_compilation()
            if compilation:
                table = compilation.table
        if (not table and
                Transaction().context.get('active_model') == 'lims.interface'):
            interface_id = Transaction().context.get('active_id', None)
            if interface_id:
                interface = Interface(interface_id)
                table = interface.table and interface.table.id or None
        if table:
            return Table(table)
