# -*- coding: utf-8 -*-
# This file is part of lims_instrument_custom_set module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import PoolMeta
from . import custom_set_csv
from . import custom_set_xls


class ResultsImport(metaclass=PoolMeta):
    __name__ = 'lims.resultsimport'

    @classmethod
    def __setup__(cls):
        super().__setup__()
        controllers = [
            ('custom_set_csv', 'Custom Set - CSV'),
            ('custom_set_xls', 'Custom Set - XLS'),
            ]
        for controller in controllers:
            if controller not in cls.name.selection:
                cls.name.selection.append(controller)

    def loadController(self):
        if self.name == 'custom_set_csv':
            self.controller = custom_set_csv
        elif self.name == 'custom_set_xls':
            self.controller = custom_set_xls
        else:
            return super().loadController()

    def getAnalysisCode(self, row):
        return self.controller.getAnalysisCode(self, row)

    def getDataHeader(self, worksheet, curr_row):
        return self.controller.getDataHeader(self, worksheet, curr_row)

    def getFormula(self, row):
        return self.controller.getFormula(self, row)
