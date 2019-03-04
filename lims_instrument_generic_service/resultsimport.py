# -*- coding: utf-8 -*-
# This file is part of lims_instrument_generic_service module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import PoolMeta
from . import generic_service_xls

__all__ = ['ResultsImport']


class ResultsImport(metaclass=PoolMeta):
    __name__ = 'lims.resultsimport'

    @classmethod
    def __setup__(cls):
        super(ResultsImport, cls).__setup__()
        controllers = [
            ('generic_service_xls', 'Generic Service Form - XLS'),
            ]
        for controller in controllers:
            if controller not in cls.name.selection:
                cls.name.selection.append(controller)

    def loadController(self):
        if self.name == 'generic_service_xls':
            self.controller = generic_service_xls
        else:
            return super(ResultsImport, self).loadController()
