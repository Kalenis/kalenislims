# -*- coding: utf-8 -*-
# This file is part of lims_interface module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import formulas
import sql

from trytond import backend
from trytond.model import ModelSQL, ModelView, fields
from trytond.transaction import Transaction
from .interface import FIELD_TYPE_SQL, FIELD_TYPE_SELECTION


class ModelEmulation:
    __doc__ = None
    _table = None
    __name__ = None


class Table(ModelSQL, ModelView):
    'Interface Table'
    __name__ = 'lims.interface.table'

    name = fields.Char('Name', required=True)
    fields_ = fields.One2Many('lims.interface.table.field', 'table',
        'Fields')
    grouped_fields_ = fields.One2Many('lims.interface.table.grouped_field',
        'table', 'Grouped Fields')
    views = fields.One2Many('lims.interface.table.view', 'table',
        'Views')
    grouped_views = fields.One2Many('lims.interface.table.grouped_view',
        'table', 'Grouped Views')

    def create_table(self):
        TableHandler = backend.TableHandler

        model = ModelEmulation()
        model.__doc__ = self.name
        model._table = self.name

        if TableHandler.table_exist(self.name):
            TableHandler.drop_table('', self.name)

        table = TableHandler(model)

        for name, field in [
                ('create_uid', fields.Integer),
                ('write_uid', fields.Integer),
                ('create_date', fields.Timestamp),
                ('write_date', fields.Timestamp),
                ('compilation', fields.Integer),
                ('annulled', fields.Boolean),
                ('notebook_line', fields.Integer),
                ]:
            sql_type = field._sql_type
            table.add_column(name, sql_type)

        for field in self.fields_:
            sql_type = FIELD_TYPE_SQL[field.type]
            table.add_column(field.name, sql_type)
        return table

    def drop_table(self):
        transaction = Transaction()
        backend.TableHandler.drop_table('', self.name, cascade=True)
        transaction.database.sequence_delete(transaction.connection,
            self.name + '_id_seq')

    @classmethod
    def delete(cls, tables):
        for table in tables:
            table.drop_table()
        super().delete(tables)


class TableField(ModelSQL, ModelView):
    'Interface Table Field'
    __name__ = 'lims.interface.table.field'

    table = fields.Many2One('lims.interface.table', 'Table',
        required=True, ondelete='CASCADE')
    name = fields.Char('Name', required=True)
    string = fields.Char('String', required=True)
    type = fields.Selection(
        [(None, ''), ('one2many', 'One2Many')] + FIELD_TYPE_SELECTION,
        'Field Type', required=False)
    help = fields.Text('Help')
    transfer_field = fields.Boolean('Is a transfer field')
    related_line_field = fields.Many2One('ir.model.field', 'Related Field')
    related_model = fields.Many2One('ir.model', 'Related Model')
    selection = fields.Text('Selection')
    domain = fields.Char('Domain Value')
    formula = fields.Char('On Change With Formula')
    inputs = fields.Char('On Change With Inputs')
    readonly = fields.Boolean('Read only')
    invisible = fields.Boolean('Invisible')
    digits = fields.Integer('Digits')
    group = fields.Integer('Group')
    related_group = fields.Integer('Related Group')
    default_width = fields.Integer('Default Width')
    colspan = fields.Integer('Colspan')
    group_name = fields.Char('Group Name')
    group_colspan = fields.Integer('Group Colspan')
    group_col = fields.Integer('Group Col')

    def get_ast(self):
        parser = formulas.Parser()
        ast = parser.ast(self.formula)[1].compile()
        return ast


class TableGroupedField(ModelSQL, ModelView):
    'Interface Table Grouped Field'
    __name__ = 'lims.interface.table.grouped_field'

    table = fields.Many2One('lims.interface.table', 'Table',
        required=True, ondelete='CASCADE')
    name = fields.Char('Name', required=True)
    string = fields.Char('String', required=True)
    type = fields.Selection([(None, '')] + FIELD_TYPE_SELECTION,
        'Field Type', required=False)
    help = fields.Text('Help')
    related_model = fields.Many2One('ir.model', 'Related Model')
    selection = fields.Text('Selection')
    domain = fields.Char('Domain Value')
    formula = fields.Char('On Change With Formula')
    inputs = fields.Function(fields.Char('On Change With Inputs'),
        'get_inputs')
    readonly = fields.Boolean('Read only')
    invisible = fields.Boolean('Invisible')
    digits = fields.Integer('Digits')
    group = fields.Integer('Group')
    default_width = fields.Integer('Default Width')

    def get_inputs(self, name=None):
        if not self.formula:
            return
        parser = formulas.Parser()
        ast = parser.ast(self.formula)[1].compile()
        return (' '.join([x for x in ast.inputs])).lower()

    def get_ast(self):
        parser = formulas.Parser()
        ast = parser.ast(self.formula)[1].compile()
        return ast


class TableView(ModelSQL, ModelView):
    'Interface Table View'
    __name__ = 'lims.interface.table.view'

    table = fields.Many2One('lims.interface.table', 'Table',
        required=True, ondelete='CASCADE')
    type = fields.Char('Type')
    arch = fields.Text('Arch')
    field_names = fields.Char('Fields')
    field_childs = fields.Char('Field Childs')


class TableGroupedView(ModelSQL, ModelView):
    'Interface Table Grouped View'
    __name__ = 'lims.interface.table.grouped_view'

    table = fields.Many2One('lims.interface.table', 'Table',
        required=True, ondelete='CASCADE')
    type = fields.Char('Type')
    arch = fields.Text('Arch')
    field_names = fields.Char('Fields')
    field_childs = fields.Char('Field Childs')
    group = fields.Integer('Group')
