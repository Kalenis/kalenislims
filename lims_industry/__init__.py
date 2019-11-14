# This file is part of lims_industry module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import industry
from . import analysis
from . import sample
from . import party
from . import planification
from . import configuration
from . import task


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
        analysis.AliquotType,
        analysis.AliquotTypeProductType,
        analysis.Analysis,
        sample.Entry,
        sample.Sample,
        sample.CreateSampleStart,
        sample.EditSampleStart,
        sample.Fraction,
        sample.Aliquot,
        party.Party,
        party.Address,
        planification.Rack,
        planification.RackPosition,
        configuration.Configuration,
        configuration.ConfigurationSequence,
        configuration.LabWorkYear,
        configuration.LabWorkYearSequence,
        task.AdministrativeTaskTemplate,
        task.AdministrativeTask,
        module='lims_industry', type_='model')
    Pool.register(
        sample.CreateSample,
        sample.EditSample,
        module='lims_industry', type_='wizard')
