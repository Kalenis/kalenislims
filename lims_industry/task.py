# This file is part of lims_industry module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import PoolMeta
from trytond.i18n import gettext

__all__ = ['AdministrativeTaskTemplate', 'AdministrativeTask']


class AdministrativeTaskTemplate(metaclass=PoolMeta):
    __name__ = 'lims.administrative.task.template'

    @classmethod
    def get_types(cls):
        types = super(AdministrativeTaskTemplate, cls).get_types()
        types.append(('equipment_missing_data',
            gettext('lims_industry.lbl_equipment_missing_data')))
        types.append(('component_missing_data',
            gettext('lims_industry.lbl_component_missing_data')))
        types.append(('party_incomplete_file',
            gettext('lims_industry.lbl_party_incomplete_file')))
        types.append(('sample_missing_data',
            gettext('lims_industry.lbl_sample_missing_data')))
        types.append(('sample_insufficient_volume',
            gettext('lims_industry.lbl_sample_insufficient_volume')))
        return types


class AdministrativeTask(metaclass=PoolMeta):
    __name__ = 'lims.administrative.task'

    @classmethod
    def _get_origin(cls):
        origins = super(AdministrativeTask, cls)._get_origin()
        origins.extend([
            'lims.equipment',
            'lims.component',
            'party.party',
            'lims.sample',
            ])
        return origins
