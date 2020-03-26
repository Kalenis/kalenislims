# This file is part of lims_analysis_sheet module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import sql
from datetime import datetime

from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, Bool, Or, And
from trytond.transaction import Transaction
from trytond.modules.lims_interface.data import Adapter
from trytond.modules.lims_interface.interface import FUNCTIONS
from .function import custom_functions

__all__ = ['Compilation', 'Column', 'Interface', 'Table', 'Data']


FUNCTIONS.update(custom_functions)


class Compilation(metaclass=PoolMeta):
    __name__ = 'lims.interface.compilation'

    analysis_sheet = fields.Many2One('lims.analysis_sheet', 'Analysis Sheet')

    @classmethod
    def __setup__(cls):
        super(Compilation, cls).__setup__()
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

        cls._buttons['draft']['invisible'] = Or(Eval('state') != 'active',
            Bool(Eval('analysis_sheet')))
        cls._buttons['activate']['invisible'] = Or(Eval('state') != 'draft',
            Bool(Eval('analysis_sheet')))
        cls._buttons['validate_']['invisible'] = Or(Eval('state') != 'active',
            Bool(Eval('analysis_sheet')))
        cls._buttons['confirm']['invisible'] = Or(Eval('state') != 'validated',
            Bool(Eval('analysis_sheet')))
        #cls._buttons['view_data']['invisible'] = Or(Eval('state') == 'draft',
            #Bool(Eval('analysis_sheet')))
        #cls._buttons['collect']['invisible'] = Or(Eval('state') != 'active',
            #Bool(Eval('analysis_sheet')))

    @classmethod
    def confirm(cls, compilations):
        pool = Pool()
        Data = pool.get('lims.interface.data')
        NotebookLine = pool.get('lims.notebook.line')

        super(Compilation, cls).confirm(compilations)

        lines_to_write = []
        for c in compilations:
            with Transaction().set_context(
                    lims_interface_table=c.table.id):
                lines = Data.search([('compilation', '=', c.id)])
                for line in lines:
                    if line.annulled and line.notebook_line:
                        lines_to_write.append(line.notebook_line)
        if lines_to_write:
            NotebookLine.write(lines_to_write, {
                'result_modifier': 'na',
                'annulled': True,
                'annulment_date': datetime.now(),
                'report': False,
                })


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

    @staticmethod
    def default_export_file_type():
        return 'csv'

    @staticmethod
    def default_export_field_separator():
        return 'semicolon'

    def _get_fields_tree_view(self):
        fields = super(Interface, self)._get_fields_tree_view()
        fields.append('<field name="annulled"/>')
        return fields

    def _get_fields_form_view(self):
        fields = super(Interface, self)._get_fields_form_view()
        fields.append('<label name="annulled"/>')
        fields.append('<field name="annulled"/>')
        return fields


class Table(metaclass=PoolMeta):
    __name__ = 'lims.interface.table'

    def create_table(self):
        table = super(Table, self).create_table()
        table.add_column('annulled', fields.Boolean._sql_type)
        return table


class NewAdapter(Adapter):

    def get_fields(self):
        Data = Pool().get('lims.interface.data')
        res = super(NewAdapter, self).get_fields()
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
        super(Data, cls).__post_setup__()
        cls._fields = NewAdapter()

    @classmethod
    def create(cls, vlist):
        vlist = [x.copy() for x in vlist]
        count = {}
        for values in vlist:
            if 'sequence' in values:
                continue
            if not values['compilation'] in count:
                count[values['compilation']] = 0
            count[values['compilation']] += 1
            values['sequence'] = (
                cls.get_last_sequence(values['compilation']) +
                count[values['compilation']])
        return super(Data, cls).create(vlist)

    @classmethod
    def get_last_sequence(cls, compilation_id):
        last = cls.search([('compilation', '=', compilation_id)],
            order=[('sequence', 'DESC')], limit=1)
        sequence = last and last[0].sequence or 0
        return sequence

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
        return super(Data, cls).fields_get(fields_names)
