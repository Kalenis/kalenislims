# This file is part of lims_industry module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.wizard import Wizard, StateAction
from trytond.pool import Pool, PoolMeta
from trytond.pyson import PYSONEncoder, Eval
from trytond.transaction import Transaction
from trytond.i18n import gettext

__all__ = ['ResultsReportVersionDetailSample',
    'ResultsReportVersionDetailLine', 'OpenResultsDetailPrecedent']


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
    precedent1_diagnosis = fields.Function(fields.Text(
        'Diagnosis Precedent 1'), 'get_precedent_diagnosis')
    precedent2_diagnosis = fields.Function(fields.Text(
        'Diagnosis Precedent 2'), 'get_precedent_diagnosis')
    precedent3_diagnosis = fields.Function(fields.Text(
        'Diagnosis Precedent 3'), 'get_precedent_diagnosis')

    @classmethod
    def view_attributes(cls):
        missing_diagnosis = True if 'diagnosis' not in cls._fields else False
        return [
            ('//group[@id="diagnosis"]', 'states', {
                'invisible': missing_diagnosis,
                }),
            ]

    @fields.depends('precedent1')
    def on_change_with_precedent1_diagnosis(self, name=None):
        if self.precedent1:
            result = self.get_precedent_diagnosis((self,),
                ('precedent1_diagnosis',))
            return result['precedent1_diagnosis'][self.id]
        return None

    @fields.depends('precedent2')
    def on_change_with_precedent2_diagnosis(self, name=None):
        if self.precedent2:
            result = self.get_precedent_diagnosis((self,),
                ('precedent2_diagnosis',))
            return result['precedent2_diagnosis'][self.id]
        return None

    @fields.depends('precedent3')
    def on_change_with_precedent3_diagnosis(self, name=None):
        if self.precedent3:
            result = self.get_precedent_diagnosis((self,),
                ('precedent3_diagnosis',))
            return result['precedent3_diagnosis'][self.id]
        return None

    @classmethod
    def get_precedent_diagnosis(cls, samples, names):
        result = {}
        missing_diagnosis = True if 'diagnosis' not in cls._fields else False
        if missing_diagnosis:
            for name in names:
                result[name] = {}
                for s in samples:
                    result[name][s.id] = None
        else:
            for name in names:
                result[name] = {}
                if name == 'precedent1_diagnosis':
                    for s in samples:
                        result[name][s.id] = cls._get_precedent_diagnosis(
                            s.precedent1)
                elif name == 'precedent2_diagnosis':
                    for s in samples:
                        result[name][s.id] = cls._get_precedent_diagnosis(
                            s.precedent2)
                else:  # name == 'precedent3_diagnosis':
                    for s in samples:
                        result[name][s.id] = cls._get_precedent_diagnosis(
                            s.precedent3)
        return result

    @classmethod
    def _get_precedent_diagnosis(cls, precedent):
        if not precedent:
            return None
        precedent_sample = cls.search([
            ('notebook', '=', precedent),
            ])
        if not precedent_sample:
            return None
        return precedent_sample[0].diagnosis

    @classmethod
    def _get_fields_from_sample(cls, sample):
        sample_default = super(ResultsReportVersionDetailSample,
            cls)._get_fields_from_sample(sample)
        sample_default['precedent1'] = (sample.precedent1 and
            sample.precedent1 or None)
        sample_default['precedent2'] = (sample.precedent2 and
            sample.precedent2 or None)
        sample_default['precedent3'] = (sample.precedent3 and
            sample.precedent3 or None)
        return sample_default

    @classmethod
    def create(cls, vlist):
        samples = super(ResultsReportVersionDetailSample, cls).create(vlist)
        for sample in samples:
            if not sample.precedent1:
                precedents = cls.get_default_precedents(sample)
                if not precedents:
                    continue
                for i in range(0, min(3, len(precedents))):
                    setattr(sample, 'precedent%s' % str(i + 1), precedents[i])
                sample.save()
        return samples

    @staticmethod
    def get_default_precedents(sample):
        Notebook = Pool().get('lims.notebook')
        precedents = Notebook.search([
            ('id', '!=', sample.notebook.id),
            ('component', '=', sample.component),
            ], order=[('id', 'DESC')], limit=3)
        return precedents


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


class OpenResultsDetailPrecedent(Wizard):
    'Results Report Precedent'
    __name__ = 'lims.results_report.version.detail.open_precedent'

    start = StateAction('lims.act_lims_results_report')

    def do_start(self, action):
        pool = Pool()
        ResultsReport = pool.get('lims.results_report')
        ResultsDetail = pool.get('lims.results_report.version.detail')
        ResultsSample = pool.get('lims.results_report.version.detail.sample')
        Notebook = pool.get('lims.notebook')

        active_ids = Transaction().context['active_ids']
        details = ResultsDetail.browse(active_ids)

        component_ids = []
        samples = ResultsSample.search([
            ('version_detail', 'in', active_ids),
            ])
        for s in samples:
            if s.component:
                component_ids.append(s.component.id)

        notebooks = Notebook.search([
            ('component', 'in', component_ids),
            ])
        notebook_ids = [n.id for n in notebooks]

        reports = ResultsReport.search([
            ('versions.details.samples.notebook', 'in', notebook_ids),
            ('versions.details.id', 'not in', active_ids),
            ])
        results_report_ids = [r.id for r in reports]

        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', 'in', results_report_ids),
            ])
        action['name'] = '%s (%s)' % (gettext('lims_industry.lbl_precedents'),
            ', '.join(d.rec_name for d in details))
        return action, {}
