# This file is part of lims_interface module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import laboratory
from . import interface
from . import function
from . import table
from . import data
from . import notebook
from . import sample


def register():
    Pool.register(
        laboratory.Laboratory,
        interface.Interface,
        interface.Column,
        interface.GroupedRepetition,
        interface.View,
        interface.ViewColumn,
        interface.CopyInterfaceColumnStart,
        interface.ImportInterfaceColumnStart,
        interface.ImportInterfaceColumnMap,
        interface.ImportInterfaceColumnMapCell,
        interface.ShowInterfaceViewAsk,
        interface.ShowInterfaceViewStart,
        interface.Compilation,
        interface.CompilationOrigin,
        interface.TestFormulaView,
        interface.TestFormulaViewVariable,
        interface.Variable,
        interface.VariableValue,
        interface.Constant,
        function.Function,
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
        interface.ImportInterfaceColumn,
        interface.ShowInterfaceView,
        interface.TestFormula,
        sample.OpenReferralCompilation,
        module='lims_interface', type_='wizard')
