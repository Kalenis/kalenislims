# This file is part of lims_interface module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import interface
from . import table
from . import data


def register():
    Pool.register(
        interface.Interface,
        interface.Column,
        interface.CopyInterfaceColumnStart,
        interface.Compilation,
        interface.CompilationOrigin,
        interface.TestFormulaView,
        interface.TestFormulaViewVariable,
        interface.Variable,
        interface.VariableValue,
        table.Table,
        table.TableField,
        table.TableView,
        data.ModelAccess,
        data.Data,
        module='lims_interface', type_='model')
    Pool.register(
        interface.CopyInterfaceColumn,
        interface.TestFormula,
        module='lims_interface', type_='wizard')
