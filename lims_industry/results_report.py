# This file is part of lims_industry module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.i18n import gettext

__all__ = ['ResultsReportVersionDetailSample',
    'ResultsReportVersionDetailLine']


class ResultsReportVersionDetailSample(metaclass=PoolMeta):
    __name__ = 'lims.results_report.version.detail.sample'

    plant = fields.Function(fields.Many2One('lims.plant', 'Plant'),
        'get_notebook_field')
    equipment = fields.Function(fields.Many2One('lims.equipment', 'Equipment'),
        'get_notebook_field')
    component = fields.Function(fields.Many2One('lims.component', 'Component'),
        'get_notebook_field')
    precedent1 = fields.Many2One('lims.notebook', 'Precedent 1',
        domain=[('component', '=', Eval('component'))],
        depends=['component'])
    precedent2 = fields.Many2One('lims.notebook', 'Precedent 2',
        domain=[('component', '=', Eval('component'))],
        depends=['component'])
    precedent3 = fields.Many2One('lims.notebook', 'Precedent 3',
        domain=[('component', '=', Eval('component'))],
        depends=['component'])

    @classmethod
    def _get_sample_copy(cls, sample):
        sample_default = super(ResultsReportVersionDetailSample,
            cls)._get_sample_copy(sample)
        sample_default['precedent1'] = (sample.precedent1 and
            sample.precedent1 or None)
        sample_default['precedent2'] = (sample.precedent2 and
            sample.precedent2 or None)
        sample_default['precedent3'] = (sample.precedent3 and
            sample.precedent3 or None)
        return sample_default


class ResultsReportVersionDetailLine(metaclass=PoolMeta):
    __name__ = 'lims.results_report.version.detail.line'

    precedent1_result = fields.Function(fields.Char('Precedent 1'),
        'get_precedent_result')
    precedent2_result = fields.Function(fields.Char('Precedent 2'),
        'get_precedent_result')
    precedent3_result = fields.Function(fields.Char('Precedent 3'),
        'get_precedent_result')

    @classmethod
    def get_precedent_result(cls, details, names):
        result = {}
        for name in names:
            result[name] = {}
            if name == 'precedent1_result':
                for d in details:
                    result[name][d.id] = cls._get_precedent_result(
                        d.detail_sample.precedent1, d)
            elif name == 'precedent2_result':
                for d in details:
                    result[name][d.id] = cls._get_precedent_result(
                        d.detail_sample.precedent2, d)
            else:  # name == 'precedent3_result':
                for d in details:
                    result[name][d.id] = cls._get_precedent_result(
                        d.detail_sample.precedent3, d)
        return result

    @classmethod
    def _get_precedent_result(cls, precedent, line):
        NotebookLine = Pool().get('lims.notebook.line')
        if not precedent:
            return None
        precedent_line = NotebookLine.search([
            ('notebook', '=', precedent),
            ('analysis', '=', line.notebook_line.analysis),
            ('accepted', '=', True),
            ])
        if not precedent_line:
            return None
        return cls._get_result(precedent_line[0])
