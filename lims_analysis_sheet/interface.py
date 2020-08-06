# This file is part of lims_analysis_sheet module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import sql

from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, Bool, Or, And
from trytond.transaction import Transaction
from trytond.modules.lims_interface.data import Adapter
from trytond.modules.lims_interface.interface import FUNCTIONS
from .function import custom_functions

FUNCTIONS.update(custom_functions)


class Compilation(metaclass=PoolMeta):
    __name__ = 'lims.interface.compilation'

    analysis_sheet = fields.Many2One('lims.analysis_sheet', 'Analysis Sheet')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.date_time.states['readonly'] = Bool(Eval('analysis_sheet'))
        if 'analysis_sheet' not in cls.date_time.depends:
            cls.date_time.depends.append('analysis_sheet')
        cls.interface.states['readonly'] = Bool(Eval('analysis_sheet'))
        if 'analysis_sheet' not in cls.interface.depends:
            cls.interface.depends.append('analysis_sheet')
        cls.revision.states['readonly'] = Or(Bool(Eval('analysis_sheet')),
            Eval('state') != 'draft')
        if 'analysis_sheet' not in cls.revision.depends:
            cls.revision.depends.append('analysis_sheet')

        cls._buttons['view_data']['invisible'] = Or(
            Eval('state') == 'draft',
            Bool(Eval('analysis_sheet')))
        cls._buttons['view_data']['depends'].append('analysis_sheet')
        cls._buttons['draft']['invisible'] = Or(
            Eval('state') != 'active',
            Bool(Eval('analysis_sheet')))
        cls._buttons['draft']['depends'].append('analysis_sheet')
        cls._buttons['activate']['invisible'] = Or(
            ~Eval('state').in_(['draft', 'validated']),
            Bool(Eval('analysis_sheet')))
        cls._buttons['activate']['depends'].append('analysis_sheet')
        cls._buttons['collect']['invisible'] = Or(
            Eval('state') != 'active',
            Bool(Eval('analysis_sheet')))
        cls._buttons['collect']['depends'].append('analysis_sheet')
        cls._buttons['validate_']['invisible'] = Or(
            Eval('state') != 'active',
            Bool(Eval('analysis_sheet')))
        cls._buttons['validate_']['depends'].append('analysis_sheet')
        cls._buttons['confirm']['invisible'] = Or(
            Eval('state') != 'validated',
            Bool(Eval('analysis_sheet')))
        cls._buttons['confirm']['depends'].append('analysis_sheet')

    def collect_csv(self, create_new_lines=True):
        new_lines = create_new_lines
        if self.analysis_sheet:
            new_lines = False
        super().collect_csv(create_new_lines=new_lines)

    def collect_excel(self, create_new_lines=True):
        new_lines = create_new_lines
        if self.analysis_sheet:
            new_lines = False
        super().collect_excel(create_new_lines=new_lines)


class Column(metaclass=PoolMeta):
    __name__ = 'lims.interface.column'

    destination_column = fields.Integer('Column',
        states={
            'invisible': Eval('_parent_interface', {}).get(
                'export_template_type') == 'txt',
            },
        help='Mapped column in batch file')
    destination_start = fields.Integer('Field start',
        states={
            'required': Eval('_parent_interface', {}).get(
                'export_template_type') == 'txt',
            'invisible': Eval('_parent_interface', {}).get(
                'export_template_type') != 'txt',
            })
    destination_end = fields.Integer('Field end',
        states={
            'required': Eval('_parent_interface', {}).get(
                'export_template_type') == 'txt',
            'invisible': Eval('_parent_interface', {}).get(
                'export_template_type') != 'txt',
            })


class Interface(metaclass=PoolMeta):
    __name__ = 'lims.interface'

    export_file_type = fields.Selection([
        (None, ''),
        ('excel', 'Excel'),
        ('csv', 'Comma Separated Values'),
        ('txt', 'Text File'),
        ], 'File Type', sort=False)
    export_field_separator = fields.Selection([
        ('comma', 'Comma (,)'),
        ('colon', 'Colon (:)'),
        ('semicolon', 'Semicolon (;)'),
        ('tab', 'Tab'),
        ('space', 'Space'),
        ('other', 'Other'),
        ], 'Field separator', sort=False,
        states={
            'required': Eval('export_file_type') == 'csv',
            'invisible': Eval('export_file_type') != 'csv',
            },
        depends=['export_file_type'])
    export_field_separator_other = fields.Char('Other',
        states={
            'required': And(
                Eval('export_file_type') == 'csv',
                Eval('export_field_separator') == 'other'),
            'invisible': Or(
                Eval('export_file_type') != 'csv',
                Eval('export_field_separator') != 'other'),
            },
        depends=['export_file_type', 'export_field_separator'])
    export_order_field = fields.Many2One('lims.interface.column',
        'Order field', depends=['id'],
        domain=[('interface', '=', Eval('id')), ('grouped', '=', False)])

    @staticmethod
    def default_export_file_type():
        return 'csv'

    @staticmethod
    def default_export_field_separator():
        return 'semicolon'

    def _get_fields_tree_view(self):
        fields = super()._get_fields_tree_view()
        fields.append('<field name="annulled"/>')
        return fields

    def _get_fields_form_view(self):
        fields = super()._get_fields_form_view()
        fields.append('<label name="annulled"/>')
        fields.append('<field name="annulled"/>')
        return fields


class Table(metaclass=PoolMeta):
    __name__ = 'lims.interface.table'

    def create_table(self):
        table = super().create_table()
        table.add_column('annulled', fields.Boolean._sql_type)
        return table


class NewAdapter(Adapter):

    def get_fields(self):
        Data = Pool().get('lims.interface.data')
        res = super().get_fields()
        table = Data.get_table()
        if not table:
            return res
        obj = fields.Boolean('Annulled')
        obj.name = 'annulled'
        res['annulled'] = obj
        return res


class Data(metaclass=PoolMeta):
    __name__ = 'lims.interface.data'

    annulled = fields.Boolean('Annulled')

    @classmethod
    def __post_setup__(cls):
        super().__post_setup__()
        cls._fields = NewAdapter()

    def set_field(self, value, field):
        cursor = Transaction().connection.cursor()
        try:
            table = self.get_sql_table()
            query = table.update([sql.Column(table, field)], [value],
                where=(table.id == self.id))
            cursor.execute(*query)
        except Exception:
            pass

    @classmethod
    def fields_get(cls, fields_names=None):
        if not fields_names:
            fields_names = []
        fields_names.append('annulled')
        res = super().fields_get(fields_names)
        readonly = Transaction().context.get('lims_interface_readonly', False)
        res['annulled']['readonly'] = bool(readonly)
        return res

    @classmethod
    def delete(cls, records):
        NotebookLine = Pool().get('lims.notebook.line')
        notebook_lines = [x.notebook_line for x in records
            if x.notebook_line]
        NotebookLine.write(notebook_lines, {'start_date': None})
        super().delete(records)
