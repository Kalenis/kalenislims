# This file is part of lims_industry module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import PoolMeta

__all__ = ['TrendChart', 'OpenTrendChart']


class TrendChart(metaclass=PoolMeta):
    __name__ = 'lims.trend.chart'

    @classmethod
    def __setup__(cls):
        super(TrendChart, cls).__setup__()
        filter = ('component', 'Same Component')
        if filter not in cls.filter.selection:
            cls.filter.selection.append(filter)
        x_axis = ('hours_component', 'Hs. Component')
        if x_axis not in cls.x_axis.selection:
            cls.x_axis.selection.append(x_axis)


class OpenTrendChart(metaclass=PoolMeta):
    __name__ = 'lims.trend.chart.open'

    def _get_clause(self):
        chart = self.start.chart
        notebook = self.start.notebook
        clause = super(OpenTrendChart, self)._get_clause()

        if chart.filter == 'component':
            clause.append(('component', '=', notebook.component))

        if chart.x_axis == 'hours_component':
            clause.append(('hours_component', '<=', notebook.hours_component))
        return clause

    def _get_order(self):
        chart = self.start.chart
        if chart.x_axis == 'hours_component':
            return [('hours_component', 'DESC')]
        return super(OpenTrendChart, self)._get_order()

    def _get_x_axis(self, notebook):
        chart = self.start.chart
        if chart.x_axis == 'hours_component':
            return notebook.hours_component
        return super(OpenTrendChart, self)._get_x_axis(notebook)
