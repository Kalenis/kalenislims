# -*- coding: utf-8 -*-
# This file is part of lims_project_implementation module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.report import Report
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Eval, Equal, Bool, Not


class Project(metaclass=PoolMeta):
    __name__ = 'lims.project'

    mpi_date = fields.Date('Request date',
        states={'required': Bool(Equal(Eval('type'), 'implementation'))},
        depends=['type'])
    mpi_services = fields.Function(fields.Text('Requested analysis'),
        'get_mpi_services')
    mpi_product_types = fields.Function(fields.Text('Product types'),
        'get_mpi_product_types')
    mpi_matrixs = fields.Function(fields.Text('Matrixs'), 'get_mpi_matrixs')
    mpi_methods = fields.Function(fields.Text('Methods'), 'get_mpi_methods')
    mpi_laboratory_date = fields.Date(
        'Date of delivery of report and procedure to the laboratory',)

    @classmethod
    def __setup__(cls):
        super().__setup__()
        project_type = ('implementation', 'Implementation')
        if project_type not in cls.type.selection:
            cls.type.selection.append(project_type)

    @classmethod
    def view_attributes(cls):
        return super().view_attributes() + [
            ('//group[@id="implementation"]', 'states', {
                'invisible': Not(Bool(Equal(Eval('type'), 'implementation'))),
                }),
            ]

    def get_mpi_product_types(self, name):
        pool = Pool()
        Sample = pool.get('lims.sample')
        samples = Sample.search([
            ('entry.project', '=', self.id),
            ], order=[('number', 'ASC')])
        product_types = list(set(s.product_type.description for s in samples))
        return '\n'.join(product_types)

    def get_mpi_matrixs(self, name):
        pool = Pool()
        Sample = pool.get('lims.sample')
        samples = Sample.search([
            ('entry.project', '=', self.id),
            ], order=[('number', 'ASC')])
        matrixs = list(set(s.matrix.description for s in samples))
        return '\n'.join(matrixs)

    def get_mpi_services(self, name):
        pool = Pool()
        Service = pool.get('lims.service')
        services = Service.search([
            ('fraction.sample.entry.project', '=', self.id),
            ], order=[('number', 'ASC')])
        return '\n'.join(s.analysis.description for s in services)

    def get_mpi_methods(self, name):
        pool = Pool()
        Service = pool.get('lims.service')
        services = Service.search([
            ('fraction.sample.entry.project', '=', self.id),
            ], order=[('number', 'ASC')])
        return '\n'.join(s.method.name for s in services if s.method)


class ProjectSolventAndReagent(metaclass=PoolMeta):
    __name__ = 'lims.project.solvent_reagent'

    purchase_date = fields.Date('Purchase date')


class Entry(metaclass=PoolMeta):
    __name__ = 'lims.entry'

    @classmethod
    def __setup__(cls):
        super().__setup__()
        project_type = ('implementation', 'Implementation')
        if project_type not in cls.project_type.selection:
            cls.project_type.selection.append(project_type)


class Fraction(metaclass=PoolMeta):
    __name__ = 'lims.fraction'

    @fields.depends('type')
    def on_change_with_special_type(self, name=None):
        Config = Pool().get('lims.configuration')
        config = Config(1)
        if self.type and self.type == config.mpi_fraction_type:
            return 'mpi'
        return super().on_change_with_special_type(name)

    @classmethod
    def _get_special_type(cls, types):
        Config = Pool().get('lims.configuration')
        config = Config(1)
        res_type = super()._get_special_type(types)
        for type_ in types:
            if type_ == 'mpi':
                res_type.append(config.mpi_fraction_type)
        return res_type


class ImplementationsReport(Report):
    'Implementation Projects'
    __name__ = 'lims.project.implementation_report'

    @classmethod
    def get_context(cls, records, data):
        records = [r for r in records if r.type == 'implementation']
        report_context = super().get_context(records, data)
        report_context['company'] = report_context['user'].company
        report_context['records'] = records
        return report_context
