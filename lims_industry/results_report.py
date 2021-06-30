# This file is part of lims_industry module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.wizard import Wizard, StateAction
from trytond.pool import Pool, PoolMeta
from trytond.pyson import PYSONEncoder, Eval, If
from trytond.transaction import Transaction
from trytond.i18n import gettext


class ResultsReport(metaclass=PoolMeta):
    __name__ = 'lims.results_report'

    plants_list = fields.Function(fields.Char('Plants'),
        'get_plants_list', searcher='search_plants_list')
    equipments_list = fields.Function(fields.Char('Equipments'),
        'get_equipments_list', searcher='search_equipments_list')
    components_list = fields.Function(fields.Char('Components'),
        'get_components_list', searcher='search_components_list')

    @classmethod
    def get_plants_list(cls, reports, name):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Plant = pool.get('lims.plant')
        Equipment = pool.get('lims.equipment')
        Sample = pool.get('lims.sample')
        Fraction = pool.get('lims.fraction')
        Notebook = pool.get('lims.notebook')
        ResultsSample = pool.get('lims.results_report.version.detail.sample')
        ResultsDetail = pool.get('lims.results_report.version.detail')
        ResultsVersion = pool.get('lims.results_report.version')

        result = {}
        for r in reports:
            result[r.id] = ''
            cursor.execute('SELECT DISTINCT(p.name) '
                'FROM "' + Plant._table + '" p '
                    'INNER JOIN "' + Equipment._table + '" e '
                    'ON p.id = e.plant '
                    'INNER JOIN "' + Sample._table + '" s '
                    'ON e.id = s.equipment '
                    'INNER JOIN "' + Fraction._table + '" f '
                    'ON s.id = f.sample '
                    'INNER JOIN "' + Notebook._table + '" n '
                    'ON f.id = n.fraction '
                    'INNER JOIN "' + ResultsSample._table + '" rs '
                    'ON n.id = rs.notebook '
                    'INNER JOIN "' + ResultsDetail._table + '" rd '
                    'ON rs.version_detail = rd.id '
                    'INNER JOIN "' + ResultsVersion._table + '" rv '
                    'ON rd.report_version = rv.id '
                'WHERE rv.results_report = %s '
                'ORDER BY p.name', (r.id,))
            samples = [x[0] for x in cursor.fetchall()]
            if samples:
                result[r.id] = ', '.join(samples)
        return result

    @classmethod
    def search_plants_list(cls, name, clause):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Plant = pool.get('lims.plant')
        Equipment = pool.get('lims.equipment')
        Sample = pool.get('lims.sample')
        Fraction = pool.get('lims.fraction')
        Notebook = pool.get('lims.notebook')
        ResultsSample = pool.get('lims.results_report.version.detail.sample')
        ResultsDetail = pool.get('lims.results_report.version.detail')
        ResultsVersion = pool.get('lims.results_report.version')

        value = clause[2]
        cursor.execute('SELECT rv.results_report '
            'FROM "' + Plant._table + '" p '
                'INNER JOIN "' + Equipment._table + '" e '
                'ON p.id = e.plant '
                'INNER JOIN "' + Sample._table + '" s '
                'ON e.id = s.equipment '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON s.id = f.sample '
                'INNER JOIN "' + Notebook._table + '" n '
                'ON f.id = n.fraction '
                'INNER JOIN "' + ResultsSample._table + '" rs '
                'ON n.id = rs.notebook '
                'INNER JOIN "' + ResultsDetail._table + '" rd '
                'ON rs.version_detail = rd.id '
                'INNER JOIN "' + ResultsVersion._table + '" rv '
                'ON rd.report_version = rv.id '
            'WHERE p.name ILIKE %s',
            (value,))
        details_ids = [x[0] for x in cursor.fetchall()]
        if not details_ids:
            return [('id', '=', -1)]
        return [('id', 'in', details_ids)]

    @classmethod
    def get_equipments_list(cls, reports, name):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Equipment = pool.get('lims.equipment')
        Sample = pool.get('lims.sample')
        Fraction = pool.get('lims.fraction')
        Notebook = pool.get('lims.notebook')
        ResultsSample = pool.get('lims.results_report.version.detail.sample')
        ResultsDetail = pool.get('lims.results_report.version.detail')
        ResultsVersion = pool.get('lims.results_report.version')

        result = {}
        for r in reports:
            result[r.id] = ''
            cursor.execute('SELECT DISTINCT(e.name) '
                'FROM "' + Equipment._table + '" e '
                    'INNER JOIN "' + Sample._table + '" s '
                    'ON e.id = s.equipment '
                    'INNER JOIN "' + Fraction._table + '" f '
                    'ON s.id = f.sample '
                    'INNER JOIN "' + Notebook._table + '" n '
                    'ON f.id = n.fraction '
                    'INNER JOIN "' + ResultsSample._table + '" rs '
                    'ON n.id = rs.notebook '
                    'INNER JOIN "' + ResultsDetail._table + '" rd '
                    'ON rs.version_detail = rd.id '
                    'INNER JOIN "' + ResultsVersion._table + '" rv '
                    'ON rd.report_version = rv.id '
                'WHERE rv.results_report = %s '
                'ORDER BY e.name', (r.id,))
            samples = [x[0] for x in cursor.fetchall()]
            if samples:
                result[r.id] = ', '.join(samples)
        return result

    @classmethod
    def search_equipments_list(cls, name, clause):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Equipment = pool.get('lims.equipment')
        Sample = pool.get('lims.sample')
        Fraction = pool.get('lims.fraction')
        Notebook = pool.get('lims.notebook')
        ResultsSample = pool.get('lims.results_report.version.detail.sample')
        ResultsDetail = pool.get('lims.results_report.version.detail')
        ResultsVersion = pool.get('lims.results_report.version')

        value = clause[2]
        cursor.execute('SELECT rv.results_report '
            'FROM "' + Equipment._table + '" e '
                'INNER JOIN "' + Sample._table + '" s '
                'ON e.id = s.equipment '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON s.id = f.sample '
                'INNER JOIN "' + Notebook._table + '" n '
                'ON f.id = n.fraction '
                'INNER JOIN "' + ResultsSample._table + '" rs '
                'ON n.id = rs.notebook '
                'INNER JOIN "' + ResultsDetail._table + '" rd '
                'ON rs.version_detail = rd.id '
                'INNER JOIN "' + ResultsVersion._table + '" rv '
                'ON rd.report_version = rv.id '
            'WHERE e.name ILIKE %s',
            (value,))
        details_ids = [x[0] for x in cursor.fetchall()]
        if not details_ids:
            return [('id', '=', -1)]
        return [('id', 'in', details_ids)]

    @classmethod
    def get_components_list(cls, reports, name):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        ComponentType = pool.get('lims.component.type')
        Component = pool.get('lims.component')
        Sample = pool.get('lims.sample')
        Fraction = pool.get('lims.fraction')
        Notebook = pool.get('lims.notebook')
        ResultsSample = pool.get('lims.results_report.version.detail.sample')
        ResultsDetail = pool.get('lims.results_report.version.detail')
        ResultsVersion = pool.get('lims.results_report.version')

        result = {}
        for r in reports:
            result[r.id] = ''
            cursor.execute('SELECT DISTINCT(ct.name) '
                'FROM "' + ComponentType._table + '" ct '
                    'INNER JOIN "' + Component._table + '" c '
                    'ON ct.id = c.type '
                    'INNER JOIN "' + Sample._table + '" s '
                    'ON c.id = s.component '
                    'INNER JOIN "' + Fraction._table + '" f '
                    'ON s.id = f.sample '
                    'INNER JOIN "' + Notebook._table + '" n '
                    'ON f.id = n.fraction '
                    'INNER JOIN "' + ResultsSample._table + '" rs '
                    'ON n.id = rs.notebook '
                    'INNER JOIN "' + ResultsDetail._table + '" rd '
                    'ON rs.version_detail = rd.id '
                    'INNER JOIN "' + ResultsVersion._table + '" rv '
                    'ON rd.report_version = rv.id '
                'WHERE rv.results_report = %s '
                'ORDER BY ct.name', (r.id,))
            samples = [x[0] for x in cursor.fetchall()]
            if samples:
                result[r.id] = ', '.join(samples)
        return result

    @classmethod
    def search_components_list(cls, name, clause):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        ComponentType = pool.get('lims.component.type')
        Component = pool.get('lims.component')
        Sample = pool.get('lims.sample')
        Fraction = pool.get('lims.fraction')
        Notebook = pool.get('lims.notebook')
        ResultsSample = pool.get('lims.results_report.version.detail.sample')
        ResultsDetail = pool.get('lims.results_report.version.detail')
        ResultsVersion = pool.get('lims.results_report.version')

        value = clause[2]
        cursor.execute('SELECT rv.results_report '
            'FROM "' + ComponentType._table + '" ct '
                'INNER JOIN "' + Component._table + '" c '
                'ON ct.id = c.type '
                'INNER JOIN "' + Sample._table + '" s '
                'ON c.id = s.component '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON s.id = f.sample '
                'INNER JOIN "' + Notebook._table + '" n '
                'ON f.id = n.fraction '
                'INNER JOIN "' + ResultsSample._table + '" rs '
                'ON n.id = rs.notebook '
                'INNER JOIN "' + ResultsDetail._table + '" rd '
                'ON rs.version_detail = rd.id '
                'INNER JOIN "' + ResultsVersion._table + '" rv '
                'ON rd.report_version = rv.id '
            'WHERE ct.name ILIKE %s',
            (value,))
        details_ids = [x[0] for x in cursor.fetchall()]
        if not details_ids:
            return [('id', '=', -1)]
        return [('id', 'in', details_ids)]


class ResultsReport2(metaclass=PoolMeta):
    __name__ = 'lims.results_report'

    def _get_name_substitutions(self):
        pool = Pool()
        ResultsSample = pool.get('lims.results_report.version.detail.sample')

        res = super()._get_name_substitutions()

        samples = ResultsSample.search([
            ('version_detail.report_version.results_report',
                '=', self.id),
            ], order=[('id', 'ASC')], limit=1)
        sample = samples and samples[0] or None

        substitutions = {
            'party_fantasy_name': sample and sample.party.fantasy_name or '',
            'equipment_name': (sample and sample.equipment and
                sample.equipment.name or ''),
            'equipment_serial_number': (sample and sample.equipment and
                sample.equipment.serial_number or ''),
            'equipment_type': (sample and sample.equipment and
                sample.equipment.type.name or ''),
            'plant_name': sample and sample.plant and sample.plant.name or '',
            'component_customer_description': (sample and sample.component and
                sample.component.customer_description or ''),
            'component_type': (sample and sample.component and
                sample.component.type.name or ''),
            'ind_equipment': (sample and
                sample.notebook.fraction.sample.ind_equipment and
                (str(sample.notebook.fraction.sample.ind_equipment) +
                sample.notebook.fraction.sample.ind_equipment_uom) or '')
            }
        for key, value in list(substitutions.items()):
            substitutions[key.upper()] = value.upper()
        res.update(substitutions)
        return res


class ResultsReportVersionDetail(metaclass=PoolMeta):
    __name__ = 'lims.results_report.version.detail'

    plants_list = fields.Function(fields.Char('Plants'),
        'get_plants_list', searcher='search_plants_list')
    equipments_list = fields.Function(fields.Char('Equipments'),
        'get_equipments_list', searcher='search_equipments_list')
    components_list = fields.Function(fields.Char('Components'),
        'get_components_list', searcher='search_components_list')

    @classmethod
    def get_plants_list(cls, details, name):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Plant = pool.get('lims.plant')
        Equipment = pool.get('lims.equipment')
        Sample = pool.get('lims.sample')
        Fraction = pool.get('lims.fraction')
        Notebook = pool.get('lims.notebook')
        ResultsSample = pool.get('lims.results_report.version.detail.sample')

        result = {}
        for d in details:
            result[d.id] = ''
            cursor.execute('SELECT DISTINCT(p.name) '
                'FROM "' + Plant._table + '" p '
                    'INNER JOIN "' + Equipment._table + '" e '
                    'ON p.id = e.plant '
                    'INNER JOIN "' + Sample._table + '" s '
                    'ON e.id = s.equipment '
                    'INNER JOIN "' + Fraction._table + '" f '
                    'ON s.id = f.sample '
                    'INNER JOIN "' + Notebook._table + '" n '
                    'ON f.id = n.fraction '
                    'INNER JOIN "' + ResultsSample._table + '" rs '
                    'ON n.id = rs.notebook '
                'WHERE rs.version_detail = %s '
                'ORDER BY p.name', (d.id,))
            samples = [x[0] for x in cursor.fetchall()]
            if samples:
                result[d.id] = ', '.join(samples)
        return result

    @classmethod
    def search_plants_list(cls, name, clause):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Plant = pool.get('lims.plant')
        Equipment = pool.get('lims.equipment')
        Sample = pool.get('lims.sample')
        Fraction = pool.get('lims.fraction')
        Notebook = pool.get('lims.notebook')
        ResultsSample = pool.get('lims.results_report.version.detail.sample')

        value = clause[2]
        cursor.execute('SELECT rs.version_detail '
            'FROM "' + Plant._table + '" p '
                'INNER JOIN "' + Equipment._table + '" e '
                'ON p.id = e.plant '
                'INNER JOIN "' + Sample._table + '" s '
                'ON e.id = s.equipment '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON s.id = f.sample '
                'INNER JOIN "' + Notebook._table + '" n '
                'ON f.id = n.fraction '
                'INNER JOIN "' + ResultsSample._table + '" rs '
                'ON n.id = rs.notebook '
            'WHERE p.name ILIKE %s',
            (value,))
        details_ids = [x[0] for x in cursor.fetchall()]
        if not details_ids:
            return [('id', '=', -1)]
        return [('id', 'in', details_ids)]

    @classmethod
    def get_equipments_list(cls, details, name):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Equipment = pool.get('lims.equipment')
        Sample = pool.get('lims.sample')
        Fraction = pool.get('lims.fraction')
        Notebook = pool.get('lims.notebook')
        ResultsSample = pool.get('lims.results_report.version.detail.sample')

        result = {}
        for d in details:
            result[d.id] = ''
            cursor.execute('SELECT DISTINCT(e.name) '
                'FROM "' + Equipment._table + '" e '
                    'INNER JOIN "' + Sample._table + '" s '
                    'ON e.id = s.equipment '
                    'INNER JOIN "' + Fraction._table + '" f '
                    'ON s.id = f.sample '
                    'INNER JOIN "' + Notebook._table + '" n '
                    'ON f.id = n.fraction '
                    'INNER JOIN "' + ResultsSample._table + '" rs '
                    'ON n.id = rs.notebook '
                'WHERE rs.version_detail = %s '
                'ORDER BY e.name', (d.id,))
            samples = [x[0] for x in cursor.fetchall()]
            if samples:
                result[d.id] = ', '.join(samples)
        return result

    @classmethod
    def search_equipments_list(cls, name, clause):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Equipment = pool.get('lims.equipment')
        Sample = pool.get('lims.sample')
        Fraction = pool.get('lims.fraction')
        Notebook = pool.get('lims.notebook')
        ResultsSample = pool.get('lims.results_report.version.detail.sample')

        value = clause[2]
        cursor.execute('SELECT rs.version_detail '
            'FROM "' + Equipment._table + '" e '
                'INNER JOIN "' + Sample._table + '" s '
                'ON e.id = s.equipment '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON s.id = f.sample '
                'INNER JOIN "' + Notebook._table + '" n '
                'ON f.id = n.fraction '
                'INNER JOIN "' + ResultsSample._table + '" rs '
                'ON n.id = rs.notebook '
            'WHERE e.name ILIKE %s',
            (value,))
        details_ids = [x[0] for x in cursor.fetchall()]
        if not details_ids:
            return [('id', '=', -1)]
        return [('id', 'in', details_ids)]

    @classmethod
    def get_components_list(cls, details, name):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        ComponentType = pool.get('lims.component.type')
        Component = pool.get('lims.component')
        Sample = pool.get('lims.sample')
        Fraction = pool.get('lims.fraction')
        Notebook = pool.get('lims.notebook')
        ResultsSample = pool.get('lims.results_report.version.detail.sample')

        result = {}
        for d in details:
            result[d.id] = ''
            cursor.execute('SELECT DISTINCT(ct.name) '
                'FROM "' + ComponentType._table + '" ct '
                    'INNER JOIN "' + Component._table + '" c '
                    'ON ct.id = c.type '
                    'INNER JOIN "' + Sample._table + '" s '
                    'ON c.id = s.component '
                    'INNER JOIN "' + Fraction._table + '" f '
                    'ON s.id = f.sample '
                    'INNER JOIN "' + Notebook._table + '" n '
                    'ON f.id = n.fraction '
                    'INNER JOIN "' + ResultsSample._table + '" rs '
                    'ON n.id = rs.notebook '
                'WHERE rs.version_detail = %s '
                'ORDER BY ct.name', (d.id,))
            samples = [x[0] for x in cursor.fetchall()]
            if samples:
                result[d.id] = ', '.join(samples)
        return result

    @classmethod
    def search_components_list(cls, name, clause):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        ComponentType = pool.get('lims.component.type')
        Component = pool.get('lims.component')
        Sample = pool.get('lims.sample')
        Fraction = pool.get('lims.fraction')
        Notebook = pool.get('lims.notebook')
        ResultsSample = pool.get('lims.results_report.version.detail.sample')

        value = clause[2]
        cursor.execute('SELECT rs.version_detail '
            'FROM "' + ComponentType._table + '" ct '
                'INNER JOIN "' + Component._table + '" c '
                'ON ct.id = c.type '
                'INNER JOIN "' + Sample._table + '" s '
                'ON c.id = s.component '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON s.id = f.sample '
                'INNER JOIN "' + Notebook._table + '" n '
                'ON f.id = n.fraction '
                'INNER JOIN "' + ResultsSample._table + '" rs '
                'ON n.id = rs.notebook '
            'WHERE ct.name ILIKE %s',
            (value,))
        details_ids = [x[0] for x in cursor.fetchall()]
        if not details_ids:
            return [('id', '=', -1)]
        return [('id', 'in', details_ids)]


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
        domain=[If(~Eval('free_precedents'),
            ('component', '=', Eval('component')), ())],
        depends=['free_precedents', 'component'])
    precedent2 = fields.Many2One('lims.notebook', 'Precedent 2',
        domain=[If(~Eval('free_precedents'),
            ('component', '=', Eval('component')), ())],
        depends=['free_precedents', 'component'])
    precedent3 = fields.Many2One('lims.notebook', 'Precedent 3',
        domain=[If(~Eval('free_precedents'),
            ('component', '=', Eval('component')), ())],
        depends=['free_precedents', 'component'])
    precedent4 = fields.Many2One('lims.notebook', 'Precedent 4',
        domain=[('component', '=', Eval('component'))],
        depends=['component'])
    precedent5 = fields.Many2One('lims.notebook', 'Precedent 5',
        domain=[('component', '=', Eval('component'))],
        depends=['component'])
    precedent6 = fields.Many2One('lims.notebook', 'Precedent 6',
        domain=[('component', '=', Eval('component'))],
        depends=['component'])
    precedent7 = fields.Many2One('lims.notebook', 'Precedent 7',
        domain=[('component', '=', Eval('component'))],
        depends=['component'])
    precedent8 = fields.Many2One('lims.notebook', 'Precedent 8',
        domain=[('component', '=', Eval('component'))],
        depends=['component'])
    free_precedents = fields.Boolean('Free precedents')
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

    @staticmethod
    def default_free_precedents():
        return False

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
    def _get_fields_from_sample(cls, sample, only_accepted=True):
        sample_default = super()._get_fields_from_sample(sample,
            only_accepted)
        sample_default['precedent1'] = (sample.precedent1 and
            sample.precedent1 or None)
        sample_default['precedent2'] = (sample.precedent2 and
            sample.precedent2 or None)
        sample_default['precedent3'] = (sample.precedent3 and
            sample.precedent3 or None)
        sample_default['precedent4'] = (sample.precedent4 and
            sample.precedent4 or None)
        sample_default['precedent5'] = (sample.precedent5 and
            sample.precedent5 or None)
        sample_default['precedent6'] = (sample.precedent6 and
            sample.precedent6 or None)
        sample_default['precedent7'] = (sample.precedent7 and
            sample.precedent7 or None)
        sample_default['precedent8'] = (sample.precedent8 and
            sample.precedent8 or None)
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
            for field in ['precedent1', 'precedent2', 'precedent3',
                    'precedent4', 'precedent5', 'precedent6', 'precedent7',
                    'precedent8']:
                if field in vals:
                    change_precedents = True
            if change_precedents:
                for sample in samples:
                    cls.update_precedent_lines(sample)

    @staticmethod
    def get_default_precedents(sample):
        pool = Pool()
        Notebook = pool.get('lims.notebook')
        if not sample.component:
            return []
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
    precedent4_result = fields.Function(fields.Char('Precedent 4'),
        'get_precedent_result')
    precedent5_result = fields.Function(fields.Char('Precedent 5'),
        'get_precedent_result')
    precedent6_result = fields.Function(fields.Char('Precedent 6'),
        'get_precedent_result')
    precedent7_result = fields.Function(fields.Char('Precedent 7'),
        'get_precedent_result')
    precedent8_result = fields.Function(fields.Char('Precedent 8'),
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
            elif name == 'precedent3_result':
                for d in details:
                    result[name][d.id] = cls._get_precedent_result(
                        d.detail_sample.precedent3, d)
            elif name == 'precedent4_result':
                for d in details:
                    result[name][d.id] = cls._get_precedent_result(
                        d.detail_sample.precedent4, d)
            elif name == 'precedent5_result':
                for d in details:
                    result[name][d.id] = cls._get_precedent_result(
                        d.detail_sample.precedent5, d)
            elif name == 'precedent6_result':
                for d in details:
                    result[name][d.id] = cls._get_precedent_result(
                        d.detail_sample.precedent6, d)
            elif name == 'precedent7_result':
                for d in details:
                    result[name][d.id] = cls._get_precedent_result(
                        d.detail_sample.precedent7, d)
            else:  # name == 'precedent8_result':
                for d in details:
                    result[name][d.id] = cls._get_precedent_result(
                        d.detail_sample.precedent8, d)
        return result

    @classmethod
    def _get_precedent_result(cls, precedent, line):
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        if not precedent:
            return ''
        precedent_line = NotebookLine.search([
            ('notebook', '=', precedent),
            ('analysis', '=', line.analysis),
            ('method', '=', line.method),
            ('accepted', '=', True),
            ])
        if not precedent_line:
            return ''
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


class ReportNameFormat(metaclass=PoolMeta):
    __name__ = 'lims.result_report.format'

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.format_.help += (
            "\n- ${party_fantasy_name}"
            "\n- ${equipment_name}"
            "\n- ${equipment_serial_number}"
            "\n- ${equipment_type}"
            "\n- ${plant_name}"
            "\n- ${component_customer_description}"
            "\n- ${component_type}"
            "\n- ${ind_equipment}")
