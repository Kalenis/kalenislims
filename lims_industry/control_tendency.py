# This file is part of lims_industry module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import PoolMeta


class TrendChart(metaclass=PoolMeta):
    __name__ = 'lims.trend.chart'

    @classmethod
    def __setup__(cls):
        super().__setup__()
        for sample_filter in [
                ('equipment', 'Same Equipment'),
                ('component', 'Same Component'),
                ]:
            if sample_filter not in cls.filter.selection:
                cls.filter.selection.append(sample_filter)
        for x_axis in [
                ('ind_equipment', 'Hs/Km Equipment'),
                ('ind_component', 'Hs/Km Component'),
                ('ind_oil', 'Hs/Km Oil'),
                ]:
            if x_axis not in cls.x_axis.selection:
                cls.x_axis.selection.append(x_axis)


class OpenTrendChart(metaclass=PoolMeta):
    __name__ = 'lims.trend.chart.open'

    def _get_clause(self):
        chart = self.start.chart
        notebook = self.start.notebook
        clause = super()._get_clause()

        if chart.filter == 'equipment':
            clause.append(('equipment', '=', notebook.equipment))
        elif chart.filter == 'component':
            clause.append(('component', '=', notebook.component))

        if chart.x_axis == 'ind_equipment':
            clause.append(('ind_equipment', '<=', notebook.ind_equipment))
        elif chart.x_axis == 'ind_component':
            clause.append(('ind_component', '<=', notebook.ind_component))
        elif chart.x_axis == 'ind_oil':
            clause.append(('fraction.sample.ind_oil', '<=',
                notebook.fraction.sample.ind_oil))
        return clause

    def _get_order(self):
        chart = self.start.chart
        if chart.x_axis == 'ind_equipment':
            return [('ind_equipment', 'DESC')]
        elif chart.x_axis == 'ind_component':
            return [('ind_component', 'DESC')]
        elif chart.x_axis == 'ind_oil':
            return [('fraction.sample.ind_oil', 'DESC')]
        return super()._get_order()

    def _get_x_axis(self, notebook):
        chart = self.start.chart
        if chart.x_axis == 'ind_equipment':
            return notebook.ind_equipment
        elif chart.x_axis == 'ind_component':
            return notebook.ind_component
        elif chart.x_axis == 'ind_oil':
            return notebook.fraction.sample.ind_oil
        return super()._get_x_axis(notebook)
