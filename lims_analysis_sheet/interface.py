# This file is part of lims_analysis_sheet module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, Bool, Or, And
from trytond.transaction import Transaction
from trytond.modules.lims.analysis import FUNCTIONS
from .function import custom_functions
from trytond.model.modelstorage import AccessError

FUNCTIONS.update(custom_functions)


class Compilation(metaclass=PoolMeta):
    __name__ = 'lims.interface.compilation'

    analysis_sheet = fields.Many2One('lims.analysis_sheet', 'Analysis Sheet')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.date_time.states['readonly'] = Bool(Eval('analysis_sheet'))
        cls.interface.states['readonly'] = Or(Bool(Eval('analysis_sheet')),
            Eval('state') != 'draft')
        cls.revision.states['readonly'] = Or(Bool(Eval('analysis_sheet')),
            Eval('state') != 'draft')

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
                'export_file_type') == 'txt',
            'readonly': Eval('interface_state') != 'draft',
            },
        help='Mapped column in batch file')
    destination_start = fields.Integer('Field start',
        states={
            'required': Eval('_parent_interface', {}).get(
                'export_file_type') == 'txt',
            'invisible': Eval('_parent_interface', {}).get(
                'export_file_type') != 'txt',
            'readonly': Eval('interface_state') != 'draft',
            })
    destination_end = fields.Integer('Field end',
        states={
            'required': Eval('_parent_interface', {}).get(
                'export_file_type') == 'txt',
            'invisible': Eval('_parent_interface', {}).get(
                'export_file_type') != 'txt',
            'readonly': Eval('interface_state') != 'draft',
            })
    validation_column = fields.Boolean('Validation Column',
        help=('Column used to set if the result is in ranges '
        '(should return 1 or 0)'))


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
            })
    export_field_separator_other = fields.Char('Other',
        states={
            'required': And(
                Eval('export_file_type') == 'csv',
                Eval('export_field_separator') == 'other'),
            'invisible': Or(
                Eval('export_file_type') != 'csv',
                Eval('export_field_separator') != 'other'),
            })
    export_order_field = fields.Many2One('lims.interface.column',
        'Order field',
        domain=[('interface', '=', Eval('id')), ('group', '=', None)])

    @staticmethod
    def default_export_file_type():
        return 'csv'

    @staticmethod
    def default_export_field_separator():
        return 'semicolon'


class Data(metaclass=PoolMeta):
    __name__ = 'lims.interface.data'

    @classmethod
    def delete(cls, records):
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')

        if Transaction().context.get('clean_start_date', True):
            notebook_lines = []
            for x in records:
                try:
                    if x.notebook_line:
                        notebook_lines.append(x.notebook_line)
                except AccessError:
                    pass
            NotebookLine.write(notebook_lines, {'start_date': None})
        super().delete(records)
