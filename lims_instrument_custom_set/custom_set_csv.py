# -*- coding: utf-8 -*-
# This file is part of lims_instrument_custom_set module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import StringIO
import csv

from trytond.transaction import Transaction


def getControllerName():
    if Transaction().language in ('es', 'es_419'):
        return u'Planilla personalizada - CSV'
    else:
        return u'Custom Set - CSV'


def parse(self, infile):
    filedata = StringIO.StringIO(infile)
    reader = csv.reader(filedata)
    for line in reader:
        print(unicode(', '.join(line), 'utf-8'))
