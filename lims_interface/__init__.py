# This file is part of lims_interface module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import interface
from . import table
from . import data
from . import notebook
from . import sample


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
        table.TableGroupedField,
        table.TableView,
        table.TableGroupedView,
        data.ModelAccess,
        data.Data,
        data.GroupedData,
        notebook.NotebookLine,
        module='lims_interface', type_='model')
    Pool.register(
        interface.OpenCompilationData,
        interface.CopyInterfaceColumn,
        interface.TestFormula,
        sample.OpenReferralCompilation,
        module='lims_interface', type_='wizard')
