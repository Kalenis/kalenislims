# -*- coding: utf-8 -*-
# This file is part of lims_project_water module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval, Equal, Bool, Not

__all__ = ['LimsProject', 'LimsEntry', 'LimsSample', 'LimsCreateSampleStart',
    'LimsCreateSample']

STATES = {
    'required': Bool(Equal(Eval('type'), 'water')),
}
DEPENDS = ['type']
PROJECT_TYPE = ('water', 'Water sampling')


class LimsProject:
    __name__ = 'lims.project'
    __metaclass__ = PoolMeta

    wtr_comments = fields.Text('Climatic conditions of the sampling')

    @classmethod
    def __setup__(cls):
        super(LimsProject, cls).__setup__()
        project_type = PROJECT_TYPE
        if project_type not in cls.type.selection:
            cls.type.selection.append(project_type)
        cls._error_messages.update({
            'not_water': ('Please, select a "Water sampling" Project to print '
                'this report'),
            })

    @classmethod
    def view_attributes(cls):
        return super(LimsProject, cls).view_attributes() + [
            ('//group[@id="water"]', 'states', {
                    'invisible': Not(Bool(Equal(Eval('type'), 'water'))),
                    })]


class LimsEntry:
    __name__ = 'lims.entry'
    __metaclass__ = PoolMeta

    @classmethod
    def __setup__(cls):
        super(LimsEntry, cls).__setup__()
        project_type = PROJECT_TYPE
        if project_type not in cls.project_type.selection:
            cls.project_type.selection.append(project_type)


class LimsSample:
    __name__ = 'lims.sample'
    __metaclass__ = PoolMeta

    sampling_point = fields.Char('Sampling point', states={
            'invisible': Not(Bool(Equal(Eval('project_type'), 'water'))),
            }, depends=['project_type'])
    gps_coordinates = fields.Char('GPS coordinates', states={
            'invisible': Not(Bool(Equal(Eval('project_type'), 'water'))),
            }, depends=['project_type'])
    sampling_datetime = fields.DateTime('Sampling date and time', states={
            'invisible': Not(Bool(Equal(Eval('project_type'), 'water'))),
            }, depends=['project_type'])
    sampling_responsible = fields.Many2One('party.party',
        'Sampling responsible', states={
            'invisible': Not(Bool(Equal(Eval('project_type'), 'water'))),
            }, depends=['project_type'])

    @classmethod
    def view_attributes(cls):
        return super(LimsSample, cls).view_attributes() + [
            ('//page[@id="water_sampling"]', 'states', {
                    'invisible': Not(Bool(
                        Equal(Eval('project_type'), 'water'))),
                    })]


class LimsCreateSampleStart:
    __name__ = 'lims.create_sample.start'
    __metaclass__ = PoolMeta

    sampling_point = fields.Char('Sampling point', states={
            'invisible': Not(Bool(Equal(Eval('project_type'), 'water'))),
            }, depends=['project_type'])
    gps_coordinates = fields.Char('GPS coordinates', states={
            'invisible': Not(Bool(Equal(Eval('project_type'), 'water'))),
            }, depends=['project_type'])
    sampling_datetime = fields.DateTime('Sampling date and time', states={
            'invisible': Not(Bool(Equal(Eval('project_type'), 'water'))),
            }, depends=['project_type'])
    sampling_responsible = fields.Many2One('party.party',
        'Sampling responsible', states={
            'invisible': Not(Bool(Equal(Eval('project_type'), 'water'))),
            }, depends=['project_type'])

    @classmethod
    def view_attributes(cls):
        return super(LimsCreateSampleStart, cls).view_attributes() + [
            ('//page[@id="water_sampling"]', 'states', {
                    'invisible': Not(Bool(
                        Equal(Eval('project_type'), 'water'))),
                    })]


class LimsCreateSample:
    __name__ = 'lims.create_sample'
    __metaclass__ = PoolMeta

    def _get_samples_defaults(self, entry_id):
        samples_defaults = super(LimsCreateSample,
            self)._get_samples_defaults(entry_id)

        sampling_point = (hasattr(self.start, 'sampling_point') and
            getattr(self.start, 'sampling_point') or None)
        gps_coordinates = (hasattr(self.start, 'gps_coordinates') and
            getattr(self.start, 'gps_coordinates') or None)
        sampling_responsible_id = None
        if (hasattr(self.start, 'sampling_responsible')
                and getattr(self.start, 'sampling_responsible')):
            sampling_responsible_id = getattr(self.start,
                'sampling_responsible').id

        for sample_defaults in samples_defaults:
            sample_defaults['sampling_point'] = sampling_point
            sample_defaults['gps_coordinates'] = gps_coordinates
            sample_defaults['sampling_responsible'] = sampling_responsible_id

        return samples_defaults
