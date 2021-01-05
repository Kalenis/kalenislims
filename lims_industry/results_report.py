# This file is part of lims_industry module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.wizard import Wizard, StateAction
from trytond.pool import Pool, PoolMeta
from trytond.pyson import PYSONEncoder, Eval
from trytond.transaction import Transaction
from trytond.i18n import gettext


class ResultsReportVersionDetailSample(metaclass=PoolMeta):
    __name__ = 'lims.results_report.version.detail.sample'

    plant = fields.Function(fields.Many2One('lims.plant', 'Plant'),
        'get_notebook_field')
    equipment = fields.Function(fields.Many2One('lims.equipment', 'Equipment'),
        'get_notebook_field')
    equipment_template = fields.Function(fields.Many2One(
        'lims.equipment.template', 'Equipment Template'), 'get_notebook_field')
    equipment_model = fields.Function(fields.Char('Equipment Model'),
        'get_notebook_field')
    equipment_serial_number = fields.Function(fields.Char(
        'Equipment Serial Number'), 'get_notebook_field')
    equipment_name = fields.Function(fields.Char(
        'Equipment Name'), 'get_notebook_field')
    component = fields.Function(fields.Many2One('lims.component', 'Component'),
        'get_notebook_field')
    comercial_product = fields.Function(fields.Many2One(
        'lims.comercial.product', 'Comercial Product'), 'get_notebook_field')
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
    precedent1_diagnosis_states = fields.Function(fields.Dict(
        'lims.diagnosis.state', 'Diagnosis States Precedent 1'),
        'get_precedent_diagnosis')
    precedent2_diagnosis_states = fields.Function(fields.Dict(
        'lims.diagnosis.state', 'Diagnosis States Precedent 2'),
        'get_precedent_diagnosis')
    precedent3_diagnosis_states = fields.Function(fields.Dict(
        'lims.diagnosis.state', 'Diagnosis States Precedent 3'),
        'get_precedent_diagnosis')

    @classmethod
    def view_attributes(cls):
        missing_diagnosis = True if 'diagnosis' not in cls._fields else False
        return super().view_attributes() + [
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
                if 'precedent1' in name:
                    for s in samples:
                        result[name][s.id] = cls._get_precedent_diagnosis(
                            s.precedent1, name)
                elif 'precedent2' in name:
                    for s in samples:
                        result[name][s.id] = cls._get_precedent_diagnosis(
                            s.precedent2, name)
                else:  # name == 'precedent3_diagnosis':
                    for s in samples:
                        result[name][s.id] = cls._get_precedent_diagnosis(
                            s.precedent3, name)
        return result

    @classmethod
    def _get_precedent_diagnosis(cls, precedent, name):
        if not precedent:
            return None
        precedent_sample = cls.search([
            ('notebook', '=', precedent),
            ])
        if not precedent_sample:
            return None
        return (precedent_sample[0].diagnosis_states if 'states' in name
            else precedent_sample[0].diagnosis)

    @classmethod
    def _get_fields_from_sample(cls, sample):
        sample_default = super()._get_fields_from_sample(sample)
        sample_default['precedent1'] = (sample.precedent1 and
            sample.precedent1 or None)
        sample_default['precedent2'] = (sample.precedent2 and
            sample.precedent2 or None)
        sample_default['precedent3'] = (sample.precedent3 and
            sample.precedent3 or None)
        return sample_default

    @classmethod
    def create(cls, vlist):
        samples = super().create(vlist)
        for sample in samples:
            if not sample.precedent1:
                precedents = cls.get_default_precedents(sample)
                if not precedents:
                    continue
                for i in range(0, min(3, len(precedents))):
                    setattr(sample, 'precedent%s' % str(i + 1), precedents[i])
                sample.save()
                cls.update_precedent_lines(sample)
        return samples

    @classmethod
    def write(cls, *args):
        super().write(*args)
        update_precedent_lines = False
        if not update_precedent_lines:
            return
        actions = iter(args)
        for samples, vals in zip(actions, actions):
            change_precedents = False
            for field in ['precedent1', 'precedent2', 'precedent3']:
                if field in vals:
                    change_precedents = True
            if change_precedents:
                for sample in samples:
                    cls.update_precedent_lines(sample)

    @staticmethod
    def get_default_precedents(sample):
        pool = Pool()
        Notebook = pool.get('lims.notebook')
        precedents = Notebook.search([
            ('id', '!=', sample.notebook.id),
            ('component', '=', sample.component),
            ('invoice_party', '=', sample.notebook.invoice_party),
            ], order=[('id', 'DESC')], limit=3)
        return precedents

    @classmethod
    def update_precedent_lines(cls, sample):
        pool = Pool()
        ResultsLine = pool.get('lims.results_report.version.detail.line')
        NotebookLine = pool.get('lims.notebook.line')

        precedent_lines = ResultsLine.search([
            ('detail_sample', '=', sample.id),
            ('notebook_line', '=', None),
            ])
        if precedent_lines:
            ResultsLine.delete(precedent_lines)

        result_lines = ResultsLine.search([
            ('detail_sample', '=', sample.id),
            ])
        analysis = [rl.notebook_line.analysis.id for rl in result_lines]

        lines_to_create = []
        for precedent in [sample.precedent1, sample.precedent2,
                sample.precedent3]:
            if not precedent:
                continue
            precedent_lines = NotebookLine.search([
                ('notebook', '=', precedent),
                ('analysis', 'not in', analysis),
                ('accepted', '=', True),
                ])
            for line in precedent_lines:
                lines_to_create.append({
                    'detail_sample': sample.id,
                    'precedent_analysis': line.analysis.id,
                    })
                analysis.append(line.analysis.id)

        if lines_to_create:
            ResultsLine.create(lines_to_create)


class ResultsReportVersionDetailLine(metaclass=PoolMeta):
    __name__ = 'lims.results_report.version.detail.line'

    precedent_analysis = fields.Many2One('lims.analysis', 'Analysis')
    precedent1_result = fields.Function(fields.Char('Precedent 1'),
        'get_precedent_result')
    precedent2_result = fields.Function(fields.Char('Precedent 2'),
        'get_precedent_result')
    precedent3_result = fields.Function(fields.Char('Precedent 3'),
        'get_precedent_result')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.analysis.getter = 'get_analysis'

    @classmethod
    def get_analysis(cls, details, name):
        result = {}
        for d in details:
            if d.precedent_analysis:
                result[d.id] = d.precedent_analysis.id
            elif d.notebook_line:
                field = getattr(d.notebook_line, name, None)
                result[d.id] = field.id if field else None
            else:
                result[d.id] = None
        return result

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
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        if not precedent:
            return None
        precedent_line = NotebookLine.search([
            ('notebook', '=', precedent),
            ('analysis', '=', line.analysis),
            ('accepted', '=', True),
            ])
        if not precedent_line:
            return None
        return precedent_line[0].get_formated_result()


class OpenResultsDetailPrecedent(Wizard):
    'Results Report Precedent'
    __name__ = 'lims.results_report.version.detail.open_precedent'

    start = StateAction('lims.act_lims_results_report_list')

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


class SendResultsReport(metaclass=PoolMeta):
    __name__ = 'lims_email.send_results_report'

    def get_grouped_reports(self, report_ids):
        pool = Pool()
        Config = pool.get('lims.configuration')
        ResultsReport = pool.get('lims.results_report')
        ResultsSample = pool.get('lims.results_report.version.detail.sample')

        config = Config(1)

        if config.mail_ack_report_grouping == 'plant':
            res = {}
            results_reports = ResultsReport.browse(report_ids)
            for report in results_reports:
                plant_id = None
                samples = ResultsSample.search([
                    ('version_detail.report_version.results_report.id',
                        '=', report.id),
                    ])
                if samples:
                    sample = samples[0].notebook.fraction.sample
                    if sample.plant:
                        plant_id = sample.plant.id
                if not plant_id:
                    plant_id = report.id

                key = (plant_id, report.cie_fraction_type)
                if key not in res:
                    res[key] = {
                        'cie_fraction_type': report.cie_fraction_type,
                        'reports': [],
                        }
                res[key]['reports'].append(report)
            return res

        if config.mail_ack_report_grouping == 'equipment':
            res = {}
            results_reports = ResultsReport.browse(report_ids)
            for report in results_reports:
                equipment_id = None
                samples = ResultsSample.search([
                    ('version_detail.report_version.results_report.id',
                        '=', report.id),
                    ])
                if samples:
                    sample = samples[0].notebook.fraction.sample
                    if sample.equipment:
                        equipment_id = sample.equipment.id
                if not equipment_id:
                    equipment_id = report.id

                key = (equipment_id, report.cie_fraction_type)
                if key not in res:
                    res[key] = {
                        'cie_fraction_type': report.cie_fraction_type,
                        'reports': [],
                        }
                res[key]['reports'].append(report)
            return res

        return super().get_grouped_reports(report_ids)


class OpenResultsDetailAttachment(metaclass=PoolMeta):
    __name__ = 'lims.results_report.version.detail.open_attachment'

    def get_resource(self, details):
        res = super().get_resource(details)
        for detail in details:
            for s in detail.samples:
                if s.notebook.fraction.sample.equipment:
                    res.append(self._get_resource(
                        s.notebook.fraction.sample.equipment))
                if s.notebook.fraction.sample.component:
                    res.append(self._get_resource(
                        s.notebook.fraction.sample.component))
        return res
