# -*- coding: utf-8 -*-
# This file is part of lims_instrument_generic_form module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import PoolMeta
import generic_form_xls

__all__ = ['LimsResultsImport']


class LimsResultsImport:
    __name__ = 'lims.resultsimport'
    __metaclass__ = PoolMeta

    @classmethod
    def __setup__(cls):
        super(LimsResultsImport, cls).__setup__()
        controllers = [
            ('generic_form_xls', 'Generic Form - XLS'),
            ]
        for controller in controllers:
            if controller not in cls.name.selection:
                cls.name.selection.append(controller)

    def loadController(self):
        if self.name == 'generic_form_xls':
            self.controller = generic_form_xls
        else:
            return super(LimsResultsImport, self).loadController()
