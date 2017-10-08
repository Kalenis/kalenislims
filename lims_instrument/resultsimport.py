# -*- coding: utf-8 -*-
# This file is part of lims_instrument module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import traceback

from trytond.model import ModelView, ModelSQL, fields, Unique
from trytond.pool import PoolMeta
from trytond.pyson import Eval, Bool, If

__all__ = ['LimsNotebookLine', 'LimsResultsImport']


class LimsNotebookLine:
    __name__ = 'lims.notebook.line'
    __metaclass__ = PoolMeta

    imported_result = fields.Char('Result')
    imported_literal_result = fields.Char('Literal result')
    imported_end_date = fields.Date('End date')
    imported_professionals = fields.Char('Professionals')
    imported_chromatogram = fields.Char('Chromatogram')
    imported_device = fields.Many2One('lims.lab.device', 'Device')
    imported_dilution_factor = fields.Float('Dilution factor')
    imported_rm_correction_formula = fields.Char('RM Correction Formula')

    @classmethod
    def view_attributes(cls):
        return [('/tree', 'colors',
                If(Bool(Eval('report_date')), 'red', 'black'))]


class LimsResultsImport(ModelSQL, ModelView):
    'Results Import'
    __name__ = 'lims.resultsimport'
    _rec_name = 'description'

    name = fields.Selection([], 'Name', required=True, sort=False,
        depends=['description'])
    description = fields.Char('Description', required=True)
    controller = None
    _infile = None
    header = []
    rawresults = {}
    mimetype = None
    numline = 0

    @classmethod
    def __setup__(cls):
        super(LimsResultsImport, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('name_uniq', Unique(t, t.name),
                'The results importer name must be unique'),
            ]
        cls._error_messages.update({
            'not_module': 'No module for importer type "%s"',
            'not_implemented': ('The function "%s" is not implemented for'
                ' this importer'),
            })

    @fields.depends('name')
    def on_change_with_description(self, name=None):
        description = None
        if self.name:
            self.loadController()
        if self.controller:
            try:
                description = self.controller.getControllerName()
            except AttributeError:
                self.raise_user_error('not_implemented',
                    ('getControllerName',))
        return description

    def loadController(self):
        self.raise_user_error('not_module', (self.name,))

    def getInputFile(self):
        return self._infile

    def setInputFile(self, infile):
        self._infile = infile

    def parse(self, infile):
        if not self.controller:
            self.loadController()
        try:
            return self.controller.parse(self, infile)
        except AttributeError:
            traceback.print_exc()
            self.raise_user_error('not_implemented', ('parse',))

    def exportResults(self):
        '''
        This function defines whether the importer
        export results to a file at the end of the process.
        Default is False
        '''
        if not self.controller:
            self.loadController()
        try:
            return self.controller.exportResults(self)
        except AttributeError:
            return False
