# This file is part of lims_analysis_sheet module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pyson import Eval, Id
from trytond.pool import Pool, PoolMeta


class Configuration(metaclass=PoolMeta):
    __name__ = 'lims.configuration'

    analysis_sheet_sequence = fields.MultiValue(fields.Many2One(
        'ir.sequence', 'Analysis Sheet Sequence', required=True,
        domain=[
            ('sequence_type', '=',
                Id('lims_analysis_sheet', 'seq_type_analysis_sheet')),
            ('company', 'in',
                [Eval('context', {}).get('company', -1), None]),
            ]))
    planification_update_draft_sheet = fields.Boolean(
        'Update draft sheets when planning analyzes')
    analysis_sheet_annul_notebook_lines = fields.Boolean(
        'Annul lines in the Notebook when annulling Analysis Sheets')

    @staticmethod
    def default_planification_update_draft_sheet():
        return False

    @staticmethod
    def default_analysis_sheet_annul_notebook_lines():
        return False

    @classmethod
    def default_analysis_sheet_sequence(cls, **pattern):
        return cls.multivalue_model(
            'analysis_sheet_sequence').default_analysis_sheet_sequence()

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field == 'analysis_sheet_sequence':
            return pool.get('lims.configuration.sequence')
        return super().multivalue_model(field)


class ConfigurationSequence(metaclass=PoolMeta):
    __name__ = 'lims.configuration.sequence'

    analysis_sheet_sequence = fields.Many2One('ir.sequence',
        'Analysis Sheet Sequence', domain=[
            ('sequence_type', '=',
                Id('lims_analysis_sheet', 'seq_type_analysis_sheet')),
            ('company', 'in', [Eval('company', -1), None]),
            ])

    @classmethod
    def default_analysis_sheet_sequence(cls):
        pool = Pool()
        ModelData = pool.get('ir.model.data')
        try:
            return ModelData.get_id('lims.analysis_sheet',
                'seq_analysis_sheet')
        except KeyError:
            return None
