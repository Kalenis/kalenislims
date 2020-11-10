# This file is part of lims_industry module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import configuration
from . import industry
from . import analysis
from . import sample
from . import notebook
from . import results_report
from . import party
from . import task
from . import control_tendency


def register():
    Pool.register(
        industry.Plant,
        industry.EquipmentType,
        industry.Brand,
        industry.ComponentType,
        industry.EquipmentTemplate,
        industry.EquipmentTemplateComponentType,
        industry.Equipment,
        industry.Component,
        industry.ComercialProductBrand,
        industry.ComercialProduct,
        analysis.SampleAttributeSet,
        analysis.SampleAttribute,
        analysis.SampleAttributeAttributeSet,
        analysis.SamplingType,
        analysis.ProductType,
        analysis.Analysis,
        sample.Entry,
        sample.Sample,
        sample.Fraction,
        sample.FractionType,
        sample.CreateSampleStart,
        sample.EditSampleStart,
        notebook.Notebook,
        results_report.ResultsReportVersionDetailSample,
        results_report.ResultsReportVersionDetailLine,
        party.Party,
        party.Address,
        task.AdministrativeTaskTemplate,
        task.AdministrativeTask,
        control_tendency.TrendChart,
        module='lims_industry', type_='model')
    Pool.register(
        configuration.Configuration,
        module='lims_industry', type_='model',
        depends=['lims_email'])
    Pool.register(
        sample.CreateSample,
        sample.EditSample,
        results_report.OpenResultsDetailPrecedent,
        control_tendency.OpenTrendChart,
        module='lims_industry', type_='wizard')
    Pool.register(
        results_report.SendResultsReport,
        module='lims_industry', type_='wizard',
        depends=['lims_email'])
