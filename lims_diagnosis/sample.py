# This file is part of lims_diagnosis module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta

__all__ = ['Sample', 'CreateSampleStart', 'CreateSample']


class Sample(metaclass=PoolMeta):
    __name__ = 'lims.sample'

    diagnostician = fields.Many2One('lims.diagnostician', 'Diagnostician')

    @classmethod
    def create(cls, vlist):
        samples = super().create(vlist)
        for sample in samples:
            if not sample.diagnostician:
                sample.diagnostician = cls.get_default_diagnostician(sample)
                sample.save()
        return samples

    @staticmethod
    def get_default_diagnostician(sample):
        # 1st check party
        if sample.party.diagnostician:
            return sample.party.diagnostician.id
        # 2nd check plant
        if hasattr(sample, 'plant') and getattr(sample, 'plant'):
            if sample.plant.diagnostician:
                return sample.plant.diagnostician.id
        # 3rd check services
        for fraction in sample.fractions:
            for service in fraction.services:
                if service.analysis.diagnostician:
                    return service.analysis.diagnostician.id
        # 4th check product type
        if sample.product_type.diagnostician:
            return sample.product_type.diagnostician.id
        return None


class CreateSampleStart(metaclass=PoolMeta):
    __name__ = 'lims.create_sample.start'

    diagnostician = fields.Many2One('lims.diagnostician', 'Diagnostician')


class CreateSample(metaclass=PoolMeta):
    __name__ = 'lims.create_sample'

    def _get_samples_defaults(self, entry_id):
        samples_defaults = super()._get_samples_defaults(entry_id)

        diagnostician_id = None
        if (hasattr(self.start, 'diagnostician') and
                getattr(self.start, 'diagnostician')):
            diagnostician_id = getattr(self.start, 'diagnostician').id

        if diagnostician_id:
            for sample in samples_defaults:
                sample['diagnostician'] = diagnostician_id
        return samples_defaults
