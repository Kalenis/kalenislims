# -*- coding: utf-8 -*-
# This file is part of lims_interface module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.


def concat(*args):
    return ''.join([a if isinstance(a, str) else '' for a in args])


custom_functions = {}
custom_functions['CONCAT'] = concat
