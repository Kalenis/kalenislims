# -*- coding: utf-8 -*-
# This file is part of lims_instrument_custom_set module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import io
import csv

from trytond.transaction import Transaction


def getControllerName():
    if Transaction().language in ('es', 'es_419'):
        return 'Planilla personalizada - CSV'
    else:
        return 'Custom Set - CSV'


def parse(self, infile):
    filedata = io.StringIO(infile)
    reader = csv.reader(filedata)
    for line in reader:
        print((str(', '.join(line), 'utf-8')))
