# This file is part of lims_diagnosis module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import PoolMeta


class NotebookRule(metaclass=PoolMeta):
    __name__ = 'lims.rule'

    @classmethod
    def _target_fields(cls):
        field_list = super()._target_fields()
        field_list.append('diagnosis_warning')
        return field_list
