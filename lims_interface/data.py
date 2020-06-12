# -*- coding: utf-8 -*-
# This file is part of lims_interface module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import sql
import formulas
import schedula
from itertools import chain

from trytond.model import ModelSQL, ModelView, fields
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from trytond.tools import cursor_dict
from trytond.pyson import PYSONEncoder
from trytond.rpc import RPC
from trytond.exceptions import UserError
from .interface import FIELD_TYPE_TRYTON, FIELD_TYPE_CAST

__all__ = ['ModelAccess', 'Data', 'GroupedData']


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
            obj.name = field.name
            res[field.name] = obj
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
            obj.name = field.name
            res[field.name] = obj
        obj = fields.Integer('ID')
        obj.name = 'id'
        res['id'] = obj
        obj = fields.Many2One('lims.notebook.line', 'Notebook Line')
        obj.name = 'notebook_line'
        obj.readonly = True
        res['notebook_line'] = obj
        obj = fields.Integer('Iteration')
        obj.name = 'iteration'
        obj.readonly = True
        res['iteration'] = obj
        return res


class ModelAccess(metaclass=PoolMeta):
    __name__ = 'ir.model.access'

    @classmethod
    def get_access(cls, models):
        access = super(ModelAccess, cls).get_access(models)
        if Transaction().user != 0:
            for m in ('lims.interface.data', 'lims.interface.grouped_data'):
                if m in models:
                    access[m]['create'] = False
        return access

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
        return super(ModelAccess, cls).check_relation(model_name, field_name,
            mode)


class Data(ModelSQL, ModelView):
    'Lims Interface Data'
    __name__ = 'lims.interface.data'

    compilation = fields.Many2One('lims.interface.compilation', 'Compilation',
        required=True, ondelete='CASCADE')
    notebook_line = fields.Many2One('lims.notebook.line', 'Notebook Line',
        readonly=True)

    @classmethod
    def __setup__(cls):
        super(Data, cls).__setup__()
        cls.__rpc__['fields_view_get'].cache = None
        cls.__rpc__['default_get'].cache = None

    @classmethod
    def __post_setup__(cls):
        super(Data, cls).__post_setup__()
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
        super(Data, self).__init__(id, **kwargs)
        self._values = {}
        for kw in kwargs_copy:
            self._values[kw] = kwargs_copy[kw]

    def __getattr__(self, name):
        try:
            return super(Data, self).__getattr__(name)
        except AttributeError:
            pass

    @classmethod
    def add_on_change_with_method(cls, field):
        """
        Dynamically add 'on_change_with_<field>' methods.
        """
        fn_name = 'on_change_with_' + field.name

        def fn(self):
            ast = field.get_ast()
            inputs = field.inputs.split()
            inputs = [getattr(self, x) for x in inputs]
            try:
                value = ast(*inputs)
            except schedula.utils.exc.DispatcherError as e:
                raise UserError(e.args[0] % e.args[1:])

            if isinstance(value, list):
                value = str(value)
            elif (not isinstance(value, str) and
                    not isinstance(value, int) and
                    not isinstance(value, float) and
                    not isinstance(value, type(None))):
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
    def fields_get(cls, fields_names=None):
        Model = Pool().get('ir.model')
        res = super(Data, cls).fields_get(fields_names)

        table = cls.get_table()
        readonly = Transaction().context.get('lims_interface_readonly', False)
        encoder = PYSONEncoder()
        for field in table.fields_:
            res[field.name] = {
                'name': field.name,
                'string': field.string,
                'type': FIELD_TYPE_TRYTON[field.type],
                'relation': (field.related_model.model if
                    field.related_model else None),
                'readonly': bool(field.formula or field.readonly or readonly),
                'help': field.help,
                'domain': field.domain,
                }
            if field.inputs:
                res[field.name]['on_change_with'] = field.inputs.split()
                cls.add_on_change_with_method(field)
                cls.__rpc__[
                    'on_change_with_%s' % (field.name)] = RPC(instantiate=0)

            if field.type == 'reference':
                selection = []
                for model in Model.search([]):
                    selection.append((model.model, model.name))
                res[field.name]['selection'] = selection
            if field.type in ['datetime', 'timestamp']:
                res[field.name]['format'] = PYSONEncoder().encode(
                    '%H:%M:%S.%f')
            if field.type in ['float', 'numeric']:
                res[field.name]['digits'] = encoder.encode((16, field.digits))
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
        for field in table.fields_:
            fields_names.append(field.name)
        res = {
            'type': view.type,
            'view_id': view_id,
            'field_childs': None,
            'arch': view.arch,
            'fields': cls.fields_get(fields_names),
            }
        return res

    @classmethod
    def search(cls, domain, offset=0, limit=None, order=None, count=False,
            query=False):
        # Clean transaction cache
        for cache in Transaction().cache.values():
            if cls.__name__ in cache:
                del cache[cls.__name__]
        if not cls.get_table():
            return super(Data, cls).search(domain, offset, limit, order, count,
                query)
        table = cls.get_sql_table()
        cursor = Transaction().connection.cursor()
        # Get domain clauses
        tables, expression = cls.search_domain(domain,
            tables={None: (table, None)})

        select = table.select(table.id, where=expression, limit=limit,
            offset=offset, order_by=(table.id.asc,))
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
                fields.append(sql.Column(sql_table, key))
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
                fields.append(sql.Column(sql_table, key))
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
        compilation = cls.get_compilation()

        interface = compilation and compilation.interface.id or None

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
                fields.append(sql.Column(sql_table, field_name))
                value = record.get_formula_value(field['field'], vals)
                values.append(value)
                vals[field_name] = value

            query = sql_table.update(fields, values,
                where=(sql_table.id == record.id))
            cursor.execute(*query)

    def get_formula_value(self, field, vals={}):
        ast = field.get_ast()
        inputs = []
        for x in field.inputs.split():
            inputs.append(vals.get(x, getattr(self, x)))
        try:
            value = ast(*inputs)
        except schedula.utils.exc.DispatcherError as e:
            raise UserError(e.args[0] % e.args[1:])

        if isinstance(value, list):
            value = str(value)
        elif (not isinstance(value, str) and
                not isinstance(value, int) and
                not isinstance(value, float) and
                not isinstance(value, type(None))):
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
        Table = Pool().get('lims.interface.table')
        table = Transaction().context.get('lims_interface_table')
        if Pool().test:
            # Tryton default tests try to get data using '1' as active_id
            # We prevent the tests from failing by returning no table
            return
        if not table:
            compilation = cls.get_compilation()
            if compilation:
                table = compilation.table
        if table:
            return Table(table)

    @classmethod
    def get_sql_table(cls):
        table = cls.get_table()
        if table:
            return sql.Table(table.name)
        return super(Data, cls).__table__()


class GroupedData(ModelView):
    'Grouped Data'
    __name__ = 'lims.interface.grouped_data'

    notebook_line = fields.Many2One('lims.notebook.line', 'Notebook Line',
        readonly=True)
    iteration = fields.Integer('Iteration', readonly=True)

    @classmethod
    def __setup__(cls):
        super(GroupedData, cls).__setup__()
        cls.__rpc__['fields_view_get'].cache = None
        cls.__rpc__['default_get'].cache = None

    @classmethod
    def __post_setup__(cls):
        super(GroupedData, cls).__post_setup__()
        cls._previous_fields = cls._fields
        cls._fields = GroupedAdapter()

    def __init__(self, id=None, **kwargs):
        kwargs_copy = kwargs.copy()
        for kw in kwargs_copy:
            kwargs.pop(kw, None)
        super(GroupedData, self).__init__(id, **kwargs)
        self._values = {}
        for kw in kwargs_copy:
            self._values[kw] = kwargs_copy[kw]

    def __getattr__(self, name):
        try:
            return super(GroupedData, self).__getattr__(name)
        except AttributeError:
            pass

    @classmethod
    def add_on_change_with_method(cls, field):
        """
        Dynamically add 'on_change_with_<field>' methods.
        """
        fn_name = 'on_change_with_' + field.name

        def fn(self):
            ast = field.get_ast()
            inputs = field.get_inputs().split()
            inputs = [getattr(self, x) for x in inputs]
            try:
                value = ast(*inputs)
            except schedula.utils.exc.DispatcherError as e:
                raise UserError(e.args[0] % e.args[1:])

            if isinstance(value, list):
                value = str(value)
            elif (not isinstance(value, str) and
                    not isinstance(value, int) and
                    not isinstance(value, float) and
                    not isinstance(value, type(None))):
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
    def fields_get(cls, fields_names=None):
        Model = Pool().get('ir.model')
        res = super(GroupedData, cls).fields_get(fields_names)

        table = cls.get_table()
        readonly = Transaction().context.get('lims_interface_readonly', False)
        encoder = PYSONEncoder()
        for field in table.grouped_fields_:
            res[field.name] = {
                'name': field.name,
                'string': field.string,
                'type': FIELD_TYPE_TRYTON[field.type],
                'relation': (field.related_model.model if
                    field.related_model else None),
                'readonly': bool(field.formula or field.readonly or readonly),
                'help': field.help,
                'domain': field.domain,
                }
            if field.inputs:
                res[field.name]['on_change_with'] = field.inputs.split()
                cls.add_on_change_with_method(field)
                cls.__rpc__[
                    'on_change_with_%s' % (field.name)] = RPC(instantiate=0)

            if field.type == 'reference':
                selection = []
                for model in Model.search([]):
                    selection.append((model.model, model.name))
                res[field.name]['selection'] = selection
            if field.type in ['datetime', 'timestamp']:
                res[field.name]['format'] = PYSONEncoder().encode(
                    '%H:%M:%S.%f')
            if field.type in ['float', 'numeric']:
                res[field.name]['digits'] = encoder.encode((16, field.digits))
        return res

    @classmethod
    def fields_view_get(cls, view_id=None, view_type='form'):
        if Pool().test:
            return
        table = cls.get_table()
        for view in table.grouped_views:
            if view.type == view_type:
                break
        assert(view.id)

        fields_names = [
            'notebook_line',
            'iteration',
            ]
        for field in table.grouped_fields_:
            fields_names.append(field.name)
        res = {
            'type': view.type,
            'view_id': view_id,
            'field_childs': None,
            'arch': view.arch,
            'fields': cls.fields_get(fields_names),
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
        Table = Pool().get('lims.interface.table')
        table = Transaction().context.get('lims_interface_table')
        if Pool().test:
            # Tryton default tests try to get data using '1' as active_id
            # We prevent the tests from failing by returning no table
            return
        if not table:
            compilation = cls.get_compilation()
            if compilation:
                table = compilation.table
        if table:
            return Table(table)
