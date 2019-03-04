# -*- coding: utf-8 -*-
# This file is part of lims_project_study_plan module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from datetime import datetime
from trytond.model import ModelSQL, ModelView, fields, Unique
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Eval, Equal, Bool, Not, And, Or
from trytond.transaction import Transaction
from trytond.wizard import Wizard, StateTransition, StateView, StateAction, \
    Button
from trytond.report import Report

__all__ = ['Project', 'Entry', 'ProjectReferenceElement',
    'ProjectSolventAndReagent', 'ProjectSampleInCustody',
    'ProjectDeviationAndAmendment', 'ProjectDeviationAndAmendmentProfessional',
    'ProjectChangeLog', 'Sample', 'CreateSampleStart', 'CreateSample',
    'ProjectProfessionalPosition', 'ProjectLaboratoryProfessional', 'Lot',
    'ProjectReOpenStart', 'ProjectReOpen', 'ProjectGLPReport01',
    'ProjectGLPReport02', 'ProjectGLPReport03PrintStart',
    'ProjectGLPReport03Print', 'ProjectGLPReport03', 'ProjectGLPReport04',
    'ProjectGLPReport05PrintStart', 'ProjectGLPReport05Print',
    'ProjectGLPReport05', 'ProjectGLPReport06', 'ProjectGLPReport07',
    'ProjectGLPReport08', 'ProjectGLPReport09', 'ProjectGLPReport10PrintStart',
    'ProjectGLPReport10Print', 'ProjectGLPReport10', 'ProjectGLPReport11',
    'ProjectGLPReport12PrintStart', 'ProjectGLPReport12Print',
    'ProjectGLPReport12', 'ProjectGLPReportStudyPlan',
    'ProjectGLPReportFinalRP', 'ProjectGLPReportFinalFOR',
    'ProjectGLPReportAnalyticalPhase', 'ProjectGLPReport13']

STATES = {
    'readonly': Bool(Equal(Eval('stp_state'), 'finalized')),
    }
DEPENDS = ['stp_state']
PROJECT_TYPE = ('study_plan', 'Study plan')


class Project(metaclass=PoolMeta):
    __name__ = 'lims.project'

    stp_number = fields.Char('SP Id', readonly=True)
    stp_title = fields.Function(fields.Char('Title'),
        'on_change_with_stp_title')
    stp_description = fields.Text('Description',
        states={
            'required': Bool(Equal(Eval('type'), 'study_plan')),
            'readonly': Bool(Equal(Eval('stp_state'), 'finalized')),
            },
        depends=['type', 'stp_state'])
    stp_phase = fields.Selection([
        ('', ''),
        ('study_plan', 'Study plan'),
        ('analytical_phase', 'Analytical phase plan'),
        ], 'Study plan phase', sort=False, states=STATES, depends=DEPENDS)
    stp_target = fields.Text('Target', states=STATES, depends=DEPENDS)
    stp_sponsor = fields.Function(fields.Many2One('party.party', 'Sponsor'),
        'on_change_with_stp_sponsor')
    stp_matrix_client_description = fields.Char('Matrix client description',
        states=STATES, depends=DEPENDS)
    stp_product_brand = fields.Char('Product brand', states=STATES,
        depends=DEPENDS)
    stp_date = fields.Date('Ingress date',
        states={
            'required': Bool(Equal(Eval('type'), 'study_plan')),
            'readonly': Bool(Equal(Eval('stp_state'), 'finalized')),
            },
        depends=['type', 'stp_state'])
    stp_proposal_start_date = fields.Char('Proposal start date', states=STATES,
        depends=DEPENDS)
    stp_proposal_end_date = fields.Char('Proposal end date', states=STATES,
        depends=DEPENDS)
    stp_effective_start_date = fields.Date('Effective start date',
        states=STATES, depends=DEPENDS)
    stp_laboratory_professionals = fields.One2Many(
        'lims.project.stp_professional', 'project', 'Laboratory professionals',
        states=STATES, depends=DEPENDS)
    stp_study_director = fields.Function(fields.Many2One(
        'lims.laboratory.professional', 'Study director'),
        'on_change_with_stp_study_director')
    stp_facility_director = fields.Function(fields.Many2One(
        'lims.laboratory.professional', 'Facility director'),
        'on_change_with_stp_facility_director')
    stp_quality_unit = fields.Function(fields.Many2One(
        'lims.laboratory.professional', 'Quality unit'),
        'on_change_with_stp_quality_unit')
    stp_suspension_date = fields.Date('Discard date', states=STATES,
        depends=DEPENDS)
    stp_suspension_reason = fields.Char('Discard reason',
        states={
            'invisible': Not(Bool(Eval('stp_suspension_date'))),
            'readonly': Bool(Equal(Eval('stp_state'), 'finalized')),
            },
        depends=['stp_suspension_date', 'stp_state'])
    stp_pattern_availability = fields.Boolean('Pattern availability',
        states=STATES, depends=DEPENDS)
    stp_implementation_validation = fields.Selection([
        ('', ''),
        ('implementation_validation', 'Implementation and validation'),
        ('validation_only', 'Validation only'),
        ], 'Implementation - Validation', sort=False, states=STATES,
        depends=DEPENDS)
    stp_rector_scheme_comments = fields.Text('Rector scheme comments',
        states=STATES, depends=DEPENDS)
    stp_glp = fields.Boolean('Good laboratory practices', states=STATES,
        depends=DEPENDS)
    stp_reference_elements = fields.One2Many('lims.project.reference_element',
        'project', 'Reference/Test elements in GLP', states=STATES,
        depends=DEPENDS)
    stp_solvents_and_reagents = fields.One2Many('lims.project.solvent_reagent',
        'project', 'Solvents and Reagents', states=STATES, depends=DEPENDS)
    stp_samples_in_custody = fields.One2Many('lims.project.sample_in_custody',
        'project', 'Samples in custody', states=STATES, depends=DEPENDS)
    stp_deviation_and_amendment = fields.One2Many(
        'lims.project.deviation_amendment', 'project',
        'Deviations and Amendments', context={
            'dev_amnd_prof_domain': Eval('dev_amnd_prof_domain'),
            },
        states=STATES, depends=['dev_amnd_prof_domain', 'stp_state'])
    dev_amnd_prof_domain = fields.Function(fields.Many2Many(
        'lims.laboratory.professional', None, None, 'Professional domain'),
        'on_change_with_dev_amnd_prof_domain')
    stp_state = fields.Selection([
        ('', ''),
        ('canceled', 'Canceled'),
        ('finalized', 'Finalized'),
        ('initiated', 'Initiated'),
        ('pending', 'Pending'),
        ('requested', 'Requested'),
        ], 'State', sort=False, states=STATES, depends=DEPENDS)
    stp_state_string = stp_state.translated('stp_state')
    stp_test_system = fields.Text('Test system', states=STATES,
        depends=DEPENDS)
    stp_test_method = fields.Text('Test method', states=STATES,
        depends=DEPENDS)
    stp_records = fields.Char('Records', states=STATES, depends=DEPENDS)
    stp_start_date = fields.Function(fields.Date('Start date'),
        'on_change_with_stp_start_date')
    stp_end_date = fields.Function(fields.Date('End date'),
        'on_change_with_stp_end_date')
    stp_samples = fields.Function(fields.Many2Many('lims.sample',
        None, None, 'Samples'), 'get_stp_samples')
    stp_notebook_lines = fields.Function(fields.Many2Many('lims.notebook.line',
        None, None, 'Tests performed'), 'get_stp_notebook_lines')
    min_qty_sample = fields.Integer('Minimum quantity of sample',
        states=STATES, depends=DEPENDS)
    unit = fields.Many2One('product.uom', 'Unit',
        domain=[('category.lims_only_available', '=', True)], states=STATES,
        depends=DEPENDS)
    min_qty_sample_compliance = fields.Selection([
        ('', ''),
        ('conforming', 'Conforming'),
        ('non_conforming', 'Non Conforming'),
        ('not_apply', 'Not apply'),
        ], 'Compliance with Minimum quantity of sample', sort=False,
        states=STATES, depends=DEPENDS)
    min_qty_sample_compliance_string = min_qty_sample_compliance.translated(
        'min_qty_sample_compliance')
    stp_changelog = fields.One2Many('lims.project.stp_changelog', 'project',
        'Changelog', states=STATES, depends=DEPENDS)

    @staticmethod
    def default_stp_pattern_availability():
        return False

    @staticmethod
    def default_stp_glp():
        return False

    @staticmethod
    def default_unit():
        uoms = Pool().get('product.uom').search([('symbol', '=', 'g')])
        return uoms[0].id if uoms else None

    @classmethod
    def __setup__(cls):
        super(Project, cls).__setup__()
        project_type = PROJECT_TYPE
        if project_type not in cls.type.selection:
            cls.type.selection.append(project_type)
        cls.code.states['readonly'] = Or(And(Eval('type') == 'study_plan',
            Eval('stp_phase') == 'study_plan'), Eval('type') == 'tas')
        for field in ('type', 'stp_phase'):
            if field not in cls.code.depends:
                cls.code.depends.append(field)
        cls.external_quality_control.states['readonly'] = Bool(Equal(
            Eval('type'), 'study_plan'))
        if 'type' not in cls.external_quality_control.depends:
            cls.external_quality_control.depends.append('type')
        cls.description.states['readonly'] = Bool(Equal(Eval('stp_state'),
            'finalized'))
        if 'stp_state' not in cls.description.depends:
            cls.description.depends.append('stp_state')
        cls.type.states['readonly'] = Bool(Equal(Eval('stp_state'),
            'finalized'))
        if 'stp_state' not in cls.type.depends:
            cls.type.depends.append('stp_state')
        cls.start_date.states['readonly'] = Bool(Equal(Eval('stp_state'),
            'finalized'))
        if 'stp_state' not in cls.start_date.depends:
            cls.start_date.depends.append('stp_state')
        cls.end_date.states['readonly'] = Bool(Equal(Eval('stp_state'),
            'finalized'))
        if 'stp_state' not in cls.end_date.depends:
            cls.end_date.depends.append('stp_state')
        cls.client.states['readonly'] = Bool(Equal(Eval('stp_state'),
            'finalized'))
        if 'stp_state' not in cls.client.depends:
            cls.client.depends.append('stp_state')
        cls.storage_time.states['readonly'] = Bool(Equal(Eval('stp_state'),
            'finalized'))
        if 'stp_state' not in cls.storage_time.depends:
            cls.storage_time.depends.append('stp_state')
        cls.comments.states['readonly'] = Bool(Equal(Eval('stp_state'),
            'finalized'))
        if 'stp_state' not in cls.comments.depends:
            cls.comments.depends.append('stp_state')
        cls._buttons.update({
            'get_stp_test_system': {
                'invisible': (Eval('stp_state') == 'finalized'),
                },
            'get_stp_test_method': {
                'invisible': (Eval('stp_state') == 'finalized'),
                },
            're_open': {
                'invisible': (Eval('stp_state') != 'finalized'),
                },
            })
        cls._error_messages.update({
            'no_project_study_plan_sequence': ('There is no sequence for '
                'Study plan Projects for the work year "%s".'),
            'not_glp': ('Please, select a "Study plan" Project to print this '
                'report'),
            'not_analytical_phase': ('Please, select a "Analytical Phase '
                'Project" to print this report'),
            'not_study_plan': ('Please, select a "Study Plan Phase '
                'Project" to print this report'),
            })

    @classmethod
    def view_attributes(cls):
        return super(Project, cls).view_attributes() + [
            ('//group[@id="study_plan"]', 'states', {
                    'invisible': Not(Bool(Equal(Eval('type'), 'study_plan'))),
                    })]

    @classmethod
    def create(cls, vlist):
        pool = Pool()
        LabWorkYear = pool.get('lims.lab.workyear')
        Sequence = pool.get('ir.sequence.strict')

        workyear_id = LabWorkYear.find()
        workyear = LabWorkYear(workyear_id)
        sequence = workyear.get_sequence('project_study_plan')
        if not sequence:
            cls.raise_user_error('no_project_study_plan_sequence',
                (workyear.rec_name,))

        vlist = [x.copy() for x in vlist]
        for values in vlist:
            if values['type'] == 'study_plan':
                values['stp_number'] = Sequence.get_id(sequence.id)
                if values['stp_phase'] == 'study_plan':
                    values['code'] = values['stp_number']
        return super(Project, cls).create(vlist)

    @fields.depends('description')
    def on_change_with_stp_title(self, name=None):
        if self.description:
            return self.description
        return None

    @fields.depends('client')
    def on_change_with_stp_sponsor(self, name=None):
        if self.client:
            return self.client.id
        return None

    @fields.depends('type')
    def on_change_type(self, name=None):
        if self.type == 'study_plan':
            self.external_quality_control = False

    @ModelView.button_change('stp_test_system')
    def get_stp_test_system(self, name=None):
        NotebookLine = Pool().get('lims.notebook.line')

        stp_test_system = None
        notebook_lines = NotebookLine.search([
            ('notebook.fraction.sample.entry.project', '=', self.id),
            ('device', '!=', None),
            ], order=[('device', 'ASC')])
        if notebook_lines:
            devices = {}
            for line in notebook_lines:
                if line.device.id not in devices:
                    devices[line.device.id] = line.device.rec_name
            if devices:
                stp_test_system = '\n'.join([d for d in list(devices.values())])
        self.stp_test_system = stp_test_system

    @ModelView.button_change('stp_test_method')
    def get_stp_test_method(self, name=None):
        NotebookLine = Pool().get('lims.notebook.line')

        stp_test_method = None
        notebook_lines = NotebookLine.search([
            ('notebook.fraction.sample.entry.project', '=', self.id),
            ('method', '!=', None),
            ], order=[('method', 'ASC')])
        if notebook_lines:
            methods = {}
            for line in notebook_lines:
                if line.method.id not in methods:
                    methods[line.method.id] = line.method.rec_name
            if methods:
                stp_test_method = '\n'.join([m for m in list(methods.values())])
        self.stp_test_method = stp_test_method

    @classmethod
    @ModelView.button_action('lims_project_study_plan.wiz_re_open_project')
    def re_open(cls, projects):
        cls.write(projects, {'stp_state': ''})

    @fields.depends('start_date')
    def on_change_with_stp_start_date(self, name=None):
        if self.start_date:
            return self.start_date
        return None

    @fields.depends('end_date')
    def on_change_with_stp_end_date(self, name=None):
        if self.end_date:
            return self.end_date
        return None

    @fields.depends('stp_laboratory_professionals')
    def on_change_with_stp_study_director(self, name=None):
        if self.stp_laboratory_professionals:
            for pp in self.stp_laboratory_professionals:
                if pp.role_study_director:
                    return pp.professional.id
        return None

    @fields.depends('stp_laboratory_professionals')
    def on_change_with_stp_facility_director(self, name=None):
        if self.stp_laboratory_professionals:
            for pp in self.stp_laboratory_professionals:
                if pp.role_facility_director:
                    return pp.professional.id
        return None

    @fields.depends('stp_laboratory_professionals')
    def on_change_with_stp_quality_unit(self, name=None):
        if self.stp_laboratory_professionals:
            for pp in self.stp_laboratory_professionals:
                if pp.role_quality_unit:
                    return pp.professional.id
        return None

    @fields.depends('stp_laboratory_professionals')
    def on_change_with_dev_amnd_prof_domain(self, name=None):
        professionals = []
        if self.stp_laboratory_professionals:
            professionals = [pp.professional.id for pp in
                self.stp_laboratory_professionals if pp.professional]
        return professionals

    def get_stp_samples(self, name=None):
        Sample = Pool().get('lims.sample')
        samples = Sample.search([
            ('entry.project', '=', self.id),
            ], order=[('number', 'ASC')])
        if samples:
            return [s.id for s in samples]
        return []

    def get_stp_notebook_lines(self, name=None):
        NotebookLine = Pool().get('lims.notebook.line')
        notebook_lines = NotebookLine.search([
            ('notebook.fraction.sample.entry.project', '=', self.id),
            ], order=[('notebook', 'ASC')])
        if notebook_lines:
            return [nl.id for nl in notebook_lines]
        return []


class Entry(metaclass=PoolMeta):
    __name__ = 'lims.entry'

    @classmethod
    def __setup__(cls):
        super(Entry, cls).__setup__()
        project_type = PROJECT_TYPE
        if project_type not in cls.project_type.selection:
            cls.project_type.selection.append(project_type)


class ProjectLaboratoryProfessional(ModelSQL, ModelView):
    'Project Professional'
    __name__ = 'lims.project.stp_professional'

    project = fields.Many2One('lims.project', 'Study plan project',
        ondelete='CASCADE', select=True, required=True)
    professional = fields.Many2One('lims.laboratory.professional',
        'Laboratory professional', required=True)
    position = fields.Many2One('lims.project.stp_professional.position',
        'Position')
    role_study_director = fields.Boolean('Study director')
    role_facility_director = fields.Boolean('Facility director')
    role_quality_unit = fields.Boolean('Quality unit')
    role_other = fields.Boolean('Other')
    approval_date = fields.Date('Approval date')

    @classmethod
    def __setup__(cls):
        super(ProjectLaboratoryProfessional, cls).__setup__()
        cls._error_messages.update({
            'existing_role_study_director': ('There is already a '
                'Study director for this project'),
            'existing_role_facility_director': ('There is already a '
                'Facility director for this project'),
            'existing_role_quality_unit': ('There is already a '
                'Quality unit for this project'),
            })

    @classmethod
    def validate(cls, professionals):
        super(ProjectLaboratoryProfessional, cls).validate(professionals)
        for p in professionals:
            p.check_roles()

    def check_roles(self):
        for field in ('role_study_director', 'role_facility_director',
                'role_quality_unit'):
            if getattr(self, field):
                existing_roles = self.search([
                    ('project', '=', self.project.id),
                    (field, '=', True),
                    ('id', '!=', self.id),
                    ])
                if existing_roles:
                    self.raise_user_error('existing_' + field)

    @fields.depends('role_study_director', 'role_facility_director',
        'role_quality_unit', 'role_other')
    def on_change_role_study_director(self, name=None):
        if self.role_study_director:
            self.role_facility_director = False
            self.role_quality_unit = False
            self.role_other = False

    @fields.depends('role_facility_director', 'role_study_director',
        'role_quality_unit', 'role_other')
    def on_change_role_facility_director(self, name=None):
        if self.role_facility_director:
            self.role_study_director = False
            self.role_quality_unit = False
            self.role_other = False

    @fields.depends('role_quality_unit', 'role_study_director',
        'role_facility_director', 'role_other')
    def on_change_role_quality_unit(self, name=None):
        if self.role_quality_unit:
            self.role_study_director = False
            self.role_facility_director = False
            self.role_other = False

    @fields.depends('role_other', 'role_study_director',
        'role_facility_director', 'role_quality_unit')
    def on_change_role_other(self, name=None):
        if self.role_other:
            self.role_study_director = False
            self.role_facility_director = False
            self.role_quality_unit = False


class ProjectProfessionalPosition(ModelSQL, ModelView):
    'Professional Position'
    __name__ = 'lims.project.stp_professional.position'
    _rec_name = 'description'

    code = fields.Char('Code', required=True)
    description = fields.Char('Description', required=True)

    @classmethod
    def __setup__(cls):
        super(ProjectProfessionalPosition, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code), 'Position code must be unique'),
            ]

    def get_rec_name(self, name):
        if self.code:
            return self.code + ' - ' + self.description
        else:
            return self.description

    @classmethod
    def search_rec_name(cls, name, clause):
        field = None
        for field in ('code', 'description'):
            records = cls.search([(field,) + tuple(clause[1:])], limit=1)
            if records:
                break
        if records:
            return [(field,) + tuple(clause[1:])]
        return [(cls._rec_name,) + tuple(clause[1:])]


class ProjectReferenceElement(ModelSQL, ModelView):
    'Reference/Test Element in GLP'
    __name__ = 'lims.project.reference_element'

    project = fields.Many2One('lims.project', 'Project',
        ondelete='CASCADE', select=True, required=True)
    type = fields.Selection([
        ('test', 'Test element'),
        ('reference', 'Reference element'),
        ], 'Type', sort=False)
    input_product = fields.Many2One('product.product', 'Input')
    common_name = fields.Function(fields.Char('Common name'),
        'on_change_with_common_name')
    chemical_name = fields.Function(fields.Char('Chemical name'),
        'on_change_with_chemical_name')
    cas_number = fields.Function(fields.Char('CAS number'),
        'on_change_with_cas_number')
    lot = fields.Many2One('stock.lot', 'Lot',
        domain=[('product', '=', Eval('input_product'))],
        depends=['input_product'])
    purity_degree = fields.Function(fields.Many2One('lims.purity.degree',
        'Purity Degree'), 'on_change_with_purity_degree')
    stability = fields.Function(fields.Char('Stability'),
        'on_change_with_stability')
    homogeneity = fields.Function(fields.Char('Homogeneity'),
        'on_change_with_homogeneity')
    expiration_date = fields.Function(fields.Date('Expiration date'),
        'on_change_with_expiration_date')
    reception_date = fields.Function(fields.Date('Reception date'),
        'on_change_with_reception_date')
    formula = fields.Function(fields.Char('Formula'), 'on_change_with_formula')
    molecular_weight = fields.Function(fields.Char('Molecular weight'),
        'on_change_with_molecular_weight')
    location = fields.Many2One('stock.location', 'Location',
        domain=[('type', '=', 'storage')])

    @fields.depends('input_product')
    def on_change_with_common_name(self, name=None):
        if self.input_product:
            return self.input_product.common_name

    @fields.depends('input_product')
    def on_change_with_chemical_name(self, name=None):
        if self.input_product:
            return self.input_product.chemical_name

    @fields.depends('input_product')
    def on_change_with_cas_number(self, name=None):
        if self.input_product:
            return self.input_product.cas_number

    @fields.depends('lot')
    def on_change_with_purity_degree(self, name=None):
        if self.lot and self.lot.purity_degree:
            return self.lot.purity_degree.id

    @fields.depends('lot')
    def on_change_with_stability(self, name=None):
        if self.lot:
            return self.lot.stability

    @fields.depends('lot')
    def on_change_with_homogeneity(self, name=None):
        if self.lot:
            return self.lot.homogeneity

    @fields.depends('lot')
    def on_change_with_expiration_date(self, name=None):
        if self.lot:
            return self.lot.expiration_date

    @fields.depends('lot')
    def on_change_with_reception_date(self, name=None):
        if self.lot:
            return self.lot.reception_date

    @fields.depends('lot')
    def on_change_with_formula(self, name=None):
        if self.lot:
            return self.lot.formula

    @fields.depends('lot')
    def on_change_with_molecular_weight(self, name=None):
        if self.lot:
            return self.lot.molecular_weight


class ProjectSolventAndReagent(ModelSQL, ModelView):
    'Solvent and Reagent'
    __name__ = 'lims.project.solvent_reagent'

    project = fields.Many2One('lims.project', 'Project',
        ondelete='CASCADE', select=True, required=True)
    product = fields.Many2One('product.product', 'Solvent/Reagent',
        domain=[('account_category', 'in', Eval('solvent_reagent_domain'))],
        depends=['solvent_reagent_domain'])
    solvent_reagent_domain = fields.Function(fields.Many2Many(
        'product.category', None, None, 'Solvent/Reagent domain'),
        'get_solvent_reagent_domain')
    lot = fields.Many2One('stock.lot', 'Lot',
        domain=[('product', '=', Eval('product'))],
        depends=['product'])

    @staticmethod
    def default_solvent_reagent_domain():
        Config = Pool().get('lims.configuration')
        config = Config(1)
        return config.get_solvents() + config.get_reagents()

    def get_solvent_reagent_domain(self, name=None):
        return self.default_solvent_reagent_domain()


class ProjectSampleInCustody(ModelSQL, ModelView):
    'Sample in Custody'
    __name__ = 'lims.project.sample_in_custody'

    project = fields.Many2One('lims.project', 'Project',
        ondelete='CASCADE', select=True, required=True)
    sample = fields.Char('Sample', readonly=True)
    entry_date = fields.Date('Entry date')
    packages_quantity = fields.Integer('Packages quantity')
    package_type = fields.Many2One('lims.packaging.type', 'Package type')
    carrier = fields.Many2One('carrier', 'Carrier')
    location = fields.Many2One('stock.location', 'Location',
        domain=[('type', '=', 'storage')])
    entry_responsible = fields.Many2One('res.user', 'Entry responsible')
    file_operator_responsible = fields.Many2One('res.user',
        'File operator responsible')
    comments = fields.Text('Comments')
    temperature = fields.Selection([
        (None, ''),
        ('frozen', 'Frozen'),
        ('refrigerated', 'Refrigerated'),
        ('ambient', 'Ambient'),
        ('others', 'Others (specify)'),
        ], 'Temperature condition of the samples', sort=False)
    temperature_other = fields.Char('Temperature', states={
            'invisible': Not(Bool(Equal(Eval('temperature'), 'others'))),
            }, depends=['temperature'])
    temperature_string = temperature.translated('temperature')
    processing_state = fields.Selection([
        (None, ''),
        ('row', 'Row'),
        ('prepared', 'Prepared/Homogenized'),
        ('processed', 'Processed'),
        ('others', 'Others (specify)'),
        ], 'State of samples processing', sort=False)
    processing_state_other = fields.Char('State', states={
            'invisible': Not(Bool(Equal(Eval('processing_state'), 'others'))),
            }, depends=['processing_state'])
    processing_state_string = processing_state.translated('processing_state')

    @classmethod
    def create(cls, vlist):
        pool = Pool()
        Config = pool.get('lims.configuration')
        Sequence = pool.get('ir.sequence')

        vlist = [x.copy() for x in vlist]
        config = Config(1)
        for values in vlist:
            values['sample'] = Sequence.get_id(
                config.sample_in_custody_sequence.id)
        return super(ProjectSampleInCustody, cls).create(vlist)


class ProjectDeviationAndAmendment(ModelSQL, ModelView):
    'Deviation and Amendment'
    __name__ = 'lims.project.deviation_amendment'

    project = fields.Many2One('lims.project', 'Project',
        ondelete='CASCADE', select=True, required=True)
    type = fields.Selection([
        ('deviation', 'Deviation'),
        ('amendment', 'Amendment'),
        ], 'Type', sort=False, required=True)
    type_string = type.translated('type')
    document_type = fields.Selection([
        ('study_plan', 'Study Plan'),
        ('final_report', 'Final Report'),
        ], 'Document Type', sort=False, required=True)
    document_type_string = document_type.translated('document_type')
    number = fields.Char('Number', readonly=True)
    date = fields.Date('Date')
    description = fields.Char('Description')
    reason = fields.Char('Reason')
    anomaly_number = fields.Char('Anomaly number')
    sponsor_communication = fields.Char('Sponsor communication')
    professionals = fields.One2Many(
        'lims.project.deviation_amendment.professional',
        'deviation_amendment', 'Staff involved', context={
            'dev_amnd_prof_domain': Eval('context', {}).get(
                'dev_amnd_prof_domain', []),
            })

    @classmethod
    def __setup__(cls):
        super(ProjectDeviationAndAmendment, cls).__setup__()
        cls._order.insert(0, ('type', 'ASC'))
        cls._order.insert(1, ('document_type', 'ASC'))
        cls._order.insert(2, ('number', 'ASC'))

    @classmethod
    def create(cls, vlist):
        vlist = [x.copy() for x in vlist]
        count = {}
        for values in vlist:
            key = (values['project'], values['type'], values['document_type'])
            if key not in count:
                count[key] = 0
            count[key] += 1
            values['number'] = cls.get_next_number(key, count[key])
        return super(ProjectDeviationAndAmendment, cls).create(vlist)

    @classmethod
    def get_next_number(cls, key, count):
        number = cls.search_count([
            ('project', '=', key[0]),
            ('type', '=', key[1]),
            ('document_type', '=', key[2]),
            ])
        number += count
        return str(number)


class ProjectDeviationAndAmendmentProfessional(ModelSQL, ModelView):
    'Deviation/Amendment Professional'
    __name__ = 'lims.project.deviation_amendment.professional'
    _table = 'lims_project_deviation_amendment_pro'

    deviation_amendment = fields.Many2One('lims.project.deviation_amendment',
        'Deviation/Amendment', ondelete='CASCADE', select=True, required=True)
    professional = fields.Many2One('lims.laboratory.professional',
        'Laboratory professional', required=True, domain=['OR',
            ('id', '=', Eval('professional')),
            ('id', 'in', Eval('context', {}).get('dev_amnd_prof_domain', [])),
            ])
    date = fields.Date('Date')


class ProjectChangeLog(ModelSQL):
    'Project Changelog'
    __name__ = 'lims.project.stp_changelog'

    project = fields.Many2One('lims.project', 'Study plan project',
        ondelete='CASCADE', select=True, required=True)
    reason = fields.Text('Reason')
    date = fields.DateTime('Date')
    date2 = fields.Function(fields.Date('Date'), 'get_date',
        searcher='search_date')
    user = fields.Many2One('res.user', 'User')

    def get_date(self, name):
        pool = Pool()
        Company = pool.get('company.company')

        date = self.date
        company_id = Transaction().context.get('company')
        if company_id:
            date = Company(company_id).convert_timezone_datetime(date)
        return date.date()

    @classmethod
    def search_date(cls, name, clause):
        pool = Pool()
        Company = pool.get('company.company')
        cursor = Transaction().connection.cursor()

        timezone = None
        company_id = Transaction().context.get('company')
        if company_id:
            timezone = Company(company_id).timezone
        timezone_datetime = 'date::timestamp AT TIME ZONE \'UTC\''
        if timezone:
            timezone_datetime += ' AT TIME ZONE \'' + timezone + '\''

        operator_ = clause[1:2][0]
        cursor.execute('SELECT id '
                'FROM "' + cls._table + '" '
                'WHERE (' + timezone_datetime + ')::date ' +
                operator_ + ' %s::date', clause[2:3])
        return [('id', 'in', [x[0] for x in cursor.fetchall()])]


class Sample(metaclass=PoolMeta):
    __name__ = 'lims.sample'

    application_date = fields.Date('Application date', states={
            'invisible': Not(Bool(Equal(Eval('project_type'), 'study_plan'))),
            }, depends=['project_type'])
    sampling_date = fields.Date('Sampling date', states={
            'invisible': Not(Bool(Equal(Eval('project_type'), 'study_plan'))),
            }, depends=['project_type'])
    reception_date = fields.Date('Reception date', states={
            'invisible': Not(Bool(Equal(Eval('project_type'), 'study_plan'))),
            }, depends=['project_type'])
    treatment = fields.Char('Treatment', states={
            'invisible': Not(Bool(Equal(Eval('project_type'), 'study_plan'))),
            }, depends=['project_type'])
    dosis = fields.Char('Dosis', states={
            'invisible': Not(Bool(Equal(Eval('project_type'), 'study_plan'))),
            }, depends=['project_type'])
    after_application_days = fields.Char('After application days', states={
            'invisible': Not(Bool(Equal(Eval('project_type'), 'study_plan'))),
            }, depends=['project_type'])
    glp_repetitions = fields.Char('GLP repetitions', states={
            'invisible': Not(Bool(Equal(Eval('project_type'), 'study_plan'))),
            }, depends=['project_type'])
    sample_weight = fields.Integer('Sample weight')
    balance = fields.Many2One('lims.lab.device', 'Balance')
    cultivation_zone = fields.Char('Cultivation zone', states={
            'invisible': Not(Bool(Equal(Eval('project_type'), 'study_plan'))),
            }, depends=['project_type'])

    @classmethod
    def view_attributes(cls):
        return super(Sample, cls).view_attributes() + [
            ('//page[@id="study_plan"]', 'states', {
                    'invisible': Not(Bool(Equal(
                        Eval('project_type'), 'study_plan'))),
                    })]


class CreateSampleStart(metaclass=PoolMeta):
    __name__ = 'lims.create_sample.start'

    application_date = fields.Date('Application date', states={
            'invisible': Not(Bool(Equal(Eval('project_type'), 'study_plan'))),
            }, depends=['project_type'])
    sampling_date = fields.Date('Sampling date', states={
            'invisible': Not(Bool(Equal(Eval('project_type'), 'study_plan'))),
            }, depends=['project_type'])
    reception_date = fields.Date('Reception date', states={
            'invisible': Not(Bool(Equal(Eval('project_type'), 'study_plan'))),
            }, depends=['project_type'])
    treatment = fields.Char('Treatment', states={
            'invisible': Not(Bool(Equal(Eval('project_type'), 'study_plan'))),
            }, depends=['project_type'])
    dosis = fields.Char('Dosis', states={
            'invisible': Not(Bool(Equal(Eval('project_type'), 'study_plan'))),
            }, depends=['project_type'])
    after_application_days = fields.Char('After application days', states={
            'invisible': Not(Bool(Equal(Eval('project_type'), 'study_plan'))),
            }, depends=['project_type'])
    glp_repetitions = fields.Char('GLP repetitions', states={
            'invisible': Not(Bool(Equal(Eval('project_type'), 'study_plan'))),
            }, depends=['project_type'])
    sample_weight = fields.Integer('Sample weight')
    balance = fields.Many2One('lims.lab.device', 'Balance')
    cultivation_zone = fields.Char('Cultivation zone', states={
            'invisible': Not(Bool(Equal(Eval('project_type'), 'study_plan'))),
            }, depends=['project_type'])

    @classmethod
    def view_attributes(cls):
        return super(CreateSampleStart, cls).view_attributes() + [
            ('//page[@id="study_plan"]', 'states', {
                    'invisible': Not(Bool(Equal(
                        Eval('project_type'), 'study_plan'))),
                    })]


class CreateSample(metaclass=PoolMeta):
    __name__ = 'lims.create_sample'

    def _get_samples_defaults(self, entry_id):
        samples_defaults = super(CreateSample,
            self)._get_samples_defaults(entry_id)

        application_date = (hasattr(self.start, 'application_date') and
            getattr(self.start, 'application_date') or None)
        sampling_date = (hasattr(self.start, 'sampling_date') and
            getattr(self.start, 'sampling_date') or None)
        reception_date = (hasattr(self.start, 'reception_date') and
            getattr(self.start, 'reception_date') or None)
        treatment = (hasattr(self.start, 'treatment') and
            getattr(self.start, 'treatment') or None)
        dosis = (hasattr(self.start, 'dosis') and
            getattr(self.start, 'dosis') or None)
        after_application_days = (hasattr(self.start,
            'after_application_days') and getattr(self.start,
            'after_application_days') or None)
        glp_repetitions = (hasattr(self.start, 'glp_repetitions') and
            getattr(self.start, 'glp_repetitions') or None)
        sample_weight = (hasattr(self.start, 'sample_weight') and
            getattr(self.start, 'sample_weight') or None)
        balance_id = None
        if (hasattr(self.start, 'balance')
                and getattr(self.start, 'balance')):
            balance_id = getattr(self.start, 'balance').id
        cultivation_zone = (hasattr(self.start, 'cultivation_zone') and
            getattr(self.start, 'cultivation_zone') or None)

        for sample_defaults in samples_defaults:
            sample_defaults['application_date'] = application_date
            sample_defaults['sampling_date'] = sampling_date
            sample_defaults['reception_date'] = reception_date
            sample_defaults['treatment'] = treatment
            sample_defaults['dosis'] = dosis
            sample_defaults['after_application_days'] = after_application_days
            sample_defaults['glp_repetitions'] = glp_repetitions
            sample_defaults['sample_weight'] = sample_weight
            sample_defaults['balance'] = balance_id
            sample_defaults['cultivation_zone'] = cultivation_zone

        return samples_defaults


class Lot(metaclass=PoolMeta):
    __name__ = 'stock.lot'

    formula = fields.Char('Formula', depends=['special_category'],
        states={
            'invisible': Not(Bool(Equal(Eval('special_category'),
                'input_prod'))),
            })
    molecular_weight = fields.Char('Molecular weight',
        depends=['special_category'], states={
            'invisible': Not(Bool(Equal(Eval('special_category'),
                'input_prod'))),
            })


class ProjectReOpenStart(ModelView):
    'Open Project'
    __name__ = 'lims.project.re_open.start'

    reason = fields.Text('Reason', required=True)


class ProjectReOpen(Wizard):
    'Open Project'
    __name__ = 'lims.project.re_open'

    start = StateView('lims.project.re_open.start',
        'lims_project_study_plan.lims_project_re_open_start_view_form', [
            Button('Open', 're_open', 'tryton-ok', default=True),
            ])
    re_open = StateTransition()

    def transition_re_open(self):
        ProjectChangeLog = Pool().get('lims.project.stp_changelog')
        ProjectChangeLog.create([{
            'project': Transaction().context['active_id'],
            'reason': self.start.reason,
            'date': datetime.now(),
            'user': Transaction().user,
            }])
        return 'end'


class ProjectGLPReport01(Report):
    'GLP-005- Annex 3 Temporary input and output of samples to the file'
    __name__ = 'lims.project.glp_report.01'

    @classmethod
    def execute(cls, ids, data):
        Project = Pool().get('lims.project')
        if len(ids) > 1:
            Project.raise_user_error('not_glp')

        project = Project(ids[0])
        if project.type != 'study_plan':
            Project.raise_user_error('not_glp')

        return super(ProjectGLPReport01, cls).execute(ids, data)

    @classmethod
    def get_context(cls, records, data):
        ProjectSampleInCustody = Pool().get(
            'lims.project.sample_in_custody')

        report_context = super(ProjectGLPReport01, cls).get_context(
            records, data)

        report_context['company'] = report_context['user'].company
        report_context['stp_number'] = records[0].stp_number
        report_context['stp_sponsor'] = (records[0].stp_sponsor.code if
            records[0].stp_sponsor else '')
        report_context['stp_matrix'] = records[0].stp_matrix_client_description
        report_context['stp_product_brand'] = records[0].stp_product_brand
        report_context['code'] = records[0].code

        samples = ProjectSampleInCustody.search([
            ('project', '=', records[0].id),
            ('location', '!=', None),
            ])

        objects = {}
        for sample in samples:
            if sample.location.id not in objects:
                objects[sample.location.id] = {
                    'location': sample.location.rec_name,
                    'samples': [],
                    }
            objects[sample.location.id]['samples'].append({
                'entry_date': sample.entry_date,
                'processing_state': sample.processing_state_string,
                'temperature': sample.temperature_string,
                'packages': '%s %s' % (sample.packages_quantity or '',
                    sample.package_type.description if sample.package_type
                    else ''),
                'comments': str(sample.comments or ''),
                'entry_responsible': (sample.entry_responsible.rec_name
                    if sample.entry_responsible else ''),
                'file_operator_responsible': (
                    sample.file_operator_responsible.rec_name
                    if sample.file_operator_responsible else ''),
                })
        report_context['objects'] = objects

        return report_context


class ProjectGLPReport02(Report):
    'GLP-005- Annex 4 Definitive input and output of samples to analyze'
    __name__ = 'lims.project.glp_report.02'

    @classmethod
    def execute(cls, ids, data):
        Project = Pool().get('lims.project')
        if len(ids) > 1:
            Project.raise_user_error('not_glp')

        project = Project(ids[0])
        if project.type != 'study_plan':
            Project.raise_user_error('not_glp')

        return super(ProjectGLPReport02, cls).execute(ids, data)

    @classmethod
    def get_context(cls, records, data):
        Fraction = Pool().get('lims.fraction')

        report_context = super(ProjectGLPReport02, cls).get_context(
            records, data)

        report_context['company'] = report_context['user'].company
        report_context['stp_number'] = records[0].stp_number
        report_context['min_qty_sample_compliance'] = \
            records[0].min_qty_sample_compliance_string
        report_context['min_qty_sample'] = records[0].min_qty_sample
        report_context['stp_sponsor'] = (records[0].stp_sponsor.code if
            records[0].stp_sponsor else '')
        report_context['stp_matrix'] = records[0].stp_matrix_client_description
        report_context['stp_product_brand'] = records[0].stp_product_brand
        report_context['project_comments'] = records[0].comments
        report_context['code'] = records[0].code
        report_context['balance_name'] = ''

        fractions = Fraction.search([
            ('sample.entry.project', '=', records[0].id),
            ], order=[('number', 'ASC')])

        objects = {}
        for fraction in fractions:
            report_context['balance_name'] = (
                fractions[0].sample.balance.rec_name if
                fractions[0].sample.balance else '')
            if fraction.storage_location.id not in objects:
                objects[fraction.storage_location.id] = {
                    'location': fraction.storage_location.rec_name,
                    'samples': [],
                    }

            objects[fraction.storage_location.id]['samples'].append({
                'number': fraction.get_formated_number('pt-m-sy-sn-fn'),
                'packages': '%s %s' % (fraction.packages_quantity or '',
                    fraction.package_type.description if fraction.package_type
                    else ''),
                'entry_date': fraction.sample.date2,
                'label': fraction.sample.label,
                'sample_weight': fraction.sample.sample_weight,
                'comments': str(fraction.comments or '')
                })

        report_context['objects'] = objects
        return report_context


class ProjectGLPReport03PrintStart(ModelView):
    'GLP-005- Annex 5 Storage of samples'
    __name__ = 'lims.project.glp_report.03.print.start'

    project = fields.Many2One('lims.project', 'Project', readonly=True)
    report_date_from = fields.Date('Report date from', required=True)
    report_date_to = fields.Date('to', required=True)


class ProjectGLPReport03Print(Wizard):
    'GLP-005- Annex 5 Storage of samples'
    __name__ = 'lims.project.glp_report.03.print'

    start = StateView('lims.project.glp_report.03.print.start',
        'lims_project_study_plan.report_glp_03_print_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print', 'print_', 'tryton-print', default=True),
            ])
    print_ = StateAction('lims_project_study_plan.report_glp_03')

    def default_start(self, fields):
        return {
            'project': Transaction().context['active_id'],
            }

    def do_print_(self, action):
        data = {
            'id': self.start.project.id,
            'report_date_from': self.start.report_date_from,
            'report_date_to': self.start.report_date_to,
            }
        return action, data


class ProjectGLPReport03(Report):
    'GLP-005- Annex 5 Storage of samples'
    __name__ = 'lims.project.glp_report.03'

    @classmethod
    def execute(cls, ids, data):
        Project = Pool().get('lims.project')

        project = Project(data['id'])
        if project.type != 'study_plan':
            Project.raise_user_error('not_glp')

        return super(ProjectGLPReport03, cls).execute(ids, data)

    @classmethod
    def get_context(cls, records, data):
        pool = Pool()
        Project = pool.get('lims.project')
        Fraction = pool.get('lims.fraction')

        report_context = super(ProjectGLPReport03, cls).get_context(
            records, data)

        project = Project(data['id'])

        report_context['company'] = report_context['user'].company
        report_context['stp_number'] = project.stp_number
        report_context['report_date_from'] = data['report_date_from']
        report_context['report_date_to'] = data['report_date_to']
        report_context['stp_code'] = project.code
        fractions = Fraction.search([
            ('sample.entry.project', '=', project.id),
            ('countersample_date', '>=',
                data['report_date_from']),
            ('countersample_date', '<=',
                data['report_date_to']),
            ], order=[('number', 'ASC')])

        objects = []
        for fraction in fractions:

            objects.append({
                'number': fraction.get_formated_number('pt-m-sy-sn-fn'),
                'type': fraction.type.code,
                'packages': '%s %s' % (fraction.packages_quantity or '',
                    fraction.package_type.description if fraction.package_type
                    else ''),
                'storage_location': fraction.storage_location.code,
                'entry_date': fraction.sample.date2,
                'countersample_location': (fraction.countersample_location.code
                    if fraction.countersample_location else ''),
                'countersample_date': fraction.countersample_date or '',
                'comments': str(fraction.comments or ''),
                })
        report_context['objects'] = objects

        return report_context


class ProjectGLPReport04(Report):
    'GLP-005- Annex 6 Movements of countersamples'
    __name__ = 'lims.project.glp_report.04'

    @classmethod
    def execute(cls, ids, data):
        Project = Pool().get('lims.project')
        if len(ids) > 1:
            Project.raise_user_error('not_glp')

        project = Project(ids[0])
        if project.type != 'study_plan':
            Project.raise_user_error('not_glp')

        return super(ProjectGLPReport04, cls).execute(ids, data)

    @classmethod
    def get_context(cls, records, data):
        pool = Pool()
        Fraction = pool.get('lims.fraction')
        Move = pool.get('stock.move')

        report_context = super(ProjectGLPReport04, cls).get_context(
            records, data)

        report_context['company'] = report_context['user'].company
        report_context['stp_number'] = records[0].stp_number
        report_context['stp_sponsor'] = (records[0].stp_sponsor.code if
            records[0].stp_sponsor else '')
        report_context['stp_matrix'] = records[0].stp_matrix_client_description
        report_context['stp_product_brand'] = records[0].stp_product_brand
        report_context['code'] = records[0].code
        fractions = Fraction.search([
            ('sample.entry.project', '=', records[0].id),
            ], order=[('number', 'ASC')])

        objects = {}
        for fraction in fractions:
            clause = [
                ('fraction', '=', fraction.id),
                ('effective_date', '>=', fraction.countersample_date),
                ('create_uid', '!=', 0),
                ]
            if fraction.discharge_date:
                clause.append(
                    ('effective_date', '<=', fraction.discharge_date))
            fraction_moves = Move.search(clause, order=[
                ('effective_date', 'ASC'), ('id', 'ASC')])
            if not fraction_moves:
                continue

            current_location = fraction.current_location
            if current_location.id not in objects:
                objects[current_location.id] = {
                    'location': current_location.rec_name,
                    'samples': [],
                    }
            for move in fraction_moves:
                objects[current_location.id]['samples'].append({
                    'number': fraction.get_formated_number('pt-m-sy-sn-fn'),
                    'from_location': move.from_location.rec_name,
                    'to_location': move.to_location.rec_name,
                    'date': move.effective_date,
                    'shipment': move.shipment.number,
                    'responsible': move.create_uid.name,
                    })
        report_context['objects'] = objects

        return report_context


class ProjectGLPReport05PrintStart(ModelView):
    'GLP-005- Annex 7 Discharge of samples'
    __name__ = 'lims.project.glp_report.05.print.start'

    project = fields.Many2One('lims.project', 'Project', readonly=True)
    expiry_date_from = fields.Date('Expiry date from', required=True)
    expiry_date_to = fields.Date('to', required=True)


class ProjectGLPReport05Print(Wizard):
    'GLP-005- Annex 7 Discharge of samples'
    __name__ = 'lims.project.glp_report.05.print'

    start = StateView('lims.project.glp_report.05.print.start',
        'lims_project_study_plan.report_glp_05_print_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print', 'print_', 'tryton-print', default=True),
            ])
    print_ = StateAction('lims_project_study_plan.report_glp_05')

    def default_start(self, fields):
        return {
            'project': Transaction().context['active_id'],
            }

    def do_print_(self, action):
        data = {
            'id': self.start.project.id,
            'expiry_date_from': self.start.expiry_date_from,
            'expiry_date_to': self.start.expiry_date_to,
            }
        return action, data


class ProjectGLPReport05(Report):
    'GLP-005- Annex 7 Discharge of samples'
    __name__ = 'lims.project.glp_report.05'

    @classmethod
    def execute(cls, ids, data):
        Project = Pool().get('lims.project')

        project = Project(data['id'])
        if project.type != 'study_plan':
            Project.raise_user_error('not_glp')

        return super(ProjectGLPReport05, cls).execute(ids, data)

    @classmethod
    def get_context(cls, records, data):
        pool = Pool()
        Project = pool.get('lims.project')
        Fraction = pool.get('lims.fraction')

        report_context = super(ProjectGLPReport05, cls).get_context(
            records, data)

        project = Project(data['id'])

        report_context['company'] = report_context['user'].company
        report_context['stp_number'] = project.stp_number
        report_context['expiry_date_from'] = data['expiry_date_from']
        report_context['expiry_date_to'] = data['expiry_date_to']
        report_context['code'] = project.code
        fractions = Fraction.search([
            ('sample.entry.project', '=', project.id),
            ('expiry_date', '>=', data['expiry_date_from']),
            ('expiry_date', '<=', data['expiry_date_to']),
            ], order=[('number', 'ASC')])

        objects = []
        for fraction in fractions:
            objects.append({
                'number': fraction.get_formated_number('pt-m-sy-sn-fn'),
                'type': fraction.type.code,
                'packages': '%s %s' % (fraction.packages_quantity or '',
                    fraction.package_type.description if fraction.package_type
                    else ''),
                'storage_location': fraction.storage_location.code,
                'entry_date': fraction.sample.date2,
                'countersample_location': (fraction.countersample_location.code
                    if fraction.countersample_location else ''),
                'countersample_date': fraction.countersample_date or '',
                'discharge_date': fraction.discharge_date or '',
                'comments': str(fraction.comments or ''),
                })
        report_context['objects'] = objects

        return report_context


class ProjectGLPReport06(Report):
    'GLP-001- Annex 3 Deviations and amendments of Study plan'
    __name__ = 'lims.project.glp_report.06'

    @classmethod
    def execute(cls, ids, data):
        Project = Pool().get('lims.project')
        if len(ids) > 1:
            Project.raise_user_error('not_glp')

        project = Project(ids[0])
        if project.type != 'study_plan':
            Project.raise_user_error('not_glp')

        return super(ProjectGLPReport06, cls).execute(ids, data)

    @classmethod
    def get_context(cls, records, data):
        pool = Pool()
        ProjectDevAndAmndmnt = pool.get(
            'lims.project.deviation_amendment')
        ProjectDevAndAmndmntProfessional = pool.get(
            'lims.project.deviation_amendment.professional')

        report_context = super(ProjectGLPReport06, cls).get_context(
            records, data)

        report_context['company'] = report_context['user'].company
        report_context['stp_number'] = records[0].stp_number
        report_context['stp_title'] = records[0].stp_title
        report_context['code'] = records[0].code

        devs_amnds = ProjectDevAndAmndmnt.search([
            ('project', '=', records[0].id),
            ], order=[('date', 'ASC')])

        objects = []
        for dev_amnd in devs_amnds:
            professionals = ProjectDevAndAmndmntProfessional.search([
                ('deviation_amendment', '=', dev_amnd.id),
                ])
            objects.append({
                'type_number': '%s %s' % (dev_amnd.type_string,
                    dev_amnd.number),
                'document_type': dev_amnd.document_type_string,
                'reason': str(dev_amnd.reason or ''),
                'description': str(dev_amnd.description or ''),
                'professionals': [{
                    'name': p.professional.rec_name,
                    'date': p.date or '',
                    } for p in professionals],
                })
        report_context['objects'] = objects

        return report_context


class ProjectGLPReport07(Report):
    'Table 1- Study plan'
    __name__ = 'lims.project.glp_report.07'

    @classmethod
    def execute(cls, ids, data):
        Project = Pool().get('lims.project')
        if len(ids) > 1:
            Project.raise_user_error('not_glp')

        project = Project(ids[0])
        if project.type != 'study_plan':
            Project.raise_user_error('not_glp')

        return super(ProjectGLPReport07, cls).execute(ids, data)

    @classmethod
    def get_context(cls, records, data):
        pool = Pool()
        Entry = pool.get('lims.entry')
        Fraction = pool.get('lims.fraction')

        report_context = super(ProjectGLPReport07, cls).get_context(
            records, data)

        report_context['company'] = report_context['user'].company
        report_context['stp_number'] = records[0].stp_number
        report_context['stp_matrix'] = records[0].stp_matrix_client_description
        report_context['code'] = records[0].code
        entries = Entry.search([
            ('project', '=', records[0].id),
            ], order=[('number', 'ASC')])
        report_context['entries'] = ', '.join(e.number for e in entries)

        fractions = Fraction.search([
            ('sample.entry.project', '=', records[0].id),
            ], order=[('number', 'ASC')])

        objects = []
        for fraction in fractions:
            objects.append({
                'number': fraction.get_formated_number('sy-sn-fn'),
                'packages': '%s %s' % (fraction.packages_quantity or '',
                    fraction.package_type.description if fraction.package_type
                    else ''),
                'reception_date': fraction.sample.reception_date,
                'application_date': fraction.sample.application_date,
                'sampling_date': fraction.sample.sampling_date,
                'treatment': fraction.sample.treatment,
                'dosis': fraction.sample.dosis,
                'glp_repetitions': fraction.sample.glp_repetitions,
                'zone': (fraction.sample.cultivation_zone if
                    fraction.sample.cultivation_zone else ''),
                'after_application_days': (
                    fraction.sample.after_application_days),
                'variety': (fraction.sample.variety.description if
                    fraction.sample.variety else ''),
                'label': fraction.sample.label,
                'storage_location': fraction.storage_location.code,
                })
        report_context['objects'] = objects

        return report_context


class ProjectGLPReport08(Report):
    'Table 2- Test elements for Final report (RP)'
    __name__ = 'lims.project.glp_report.08'

    @classmethod
    def execute(cls, ids, data):
        Project = Pool().get('lims.project')
        if len(ids) > 1:
            Project.raise_user_error('not_glp')

        project = Project(ids[0])
        if project.type != 'study_plan':
            Project.raise_user_error('not_glp')

        return super(ProjectGLPReport08, cls).execute(ids, data)

    @classmethod
    def get_context(cls, records, data):
        pool = Pool()
        Entry = pool.get('lims.entry')
        Fraction = pool.get('lims.fraction')

        report_context = super(ProjectGLPReport08, cls).get_context(
            records, data)

        report_context['company'] = report_context['user'].company
        report_context['stp_number'] = records[0].stp_number
        report_context['code'] = records[0].code

        entries = Entry.search([
            ('project', '=', records[0].id),
            ], order=[('number', 'ASC')])
        report_context['entries'] = ', '.join(e.number for e in entries)

        fractions = Fraction.search([
            ('sample.entry.project', '=', records[0].id),
            ], order=[('number', 'ASC')])

        objects = []
        for fraction in fractions:
            objects.append({
                'number': fraction.get_formated_number('sy-sn-fn'),
                'reception_date': fraction.sample.reception_date,
                'application_date': fraction.sample.application_date,
                'sampling_date': fraction.sample.sampling_date,
                'treatment': fraction.sample.treatment,
                'dosis': fraction.sample.dosis,
                'glp_repetitions': fraction.sample.glp_repetitions,
                'zone': (fraction.sample.cultivation_zone if
                    fraction.sample.cultivation_zone else ''),
                'after_application_days': (
                    fraction.sample.after_application_days),
                'variety': (fraction.sample.variety.description if
                    fraction.sample.variety else ''),
                'label': fraction.sample.label,
                'sample_weight': fraction.sample.sample_weight,
                })
        report_context['objects'] = objects

        return report_context


class ProjectGLPReport09(Report):
    'Table 3- Result of Final report'
    __name__ = 'lims.project.glp_report.09'

    @classmethod
    def execute(cls, ids, data):
        Project = Pool().get('lims.project')
        if len(ids) > 1:
            Project.raise_user_error('not_glp')

        project = Project(ids[0])
        if project.type != 'study_plan':
            Project.raise_user_error('not_glp')

        return super(ProjectGLPReport09, cls).execute(ids, data)

    @classmethod
    def get_context(cls, records, data):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Fraction = pool.get('lims.fraction')
        Service = pool.get('lims.service')
        NotebookLine = pool.get('lims.notebook.line')
        ResultsReport = pool.get('lims.results_report')
        Analysis = pool.get('lims.analysis')

        report_context = super(ProjectGLPReport09, cls).get_context(
            records, data)

        report_context['company'] = report_context['user'].company
        report_context['stp_number'] = records[0].stp_number
        report_context['code'] = records[0].code

        fractions = Fraction.search([
            ('sample.entry.project', '=', records[0].id),
            ], order=[('number', 'ASC')])

        objects = {}
        for fraction in fractions:

            cursor.execute('SELECT DISTINCT(nl.results_report) , '
                'nl.result_modifier, nl.result, a.description '
                'FROM "' + NotebookLine._table + '" nl '
                    'INNER JOIN "' + Service._table + '" s '
                    'ON nl.service = s.id '
                'INNER JOIN "' + Analysis._table + '" a '
                'ON a.id = nl.analysis '
                'WHERE s.fraction = %s '
                    'AND nl.results_report IS NOT NULL '
                'ORDER BY nl.results_report ASC ',
                (fraction.id,))
            res = cursor.fetchall()
            if not res:
                continue

            key = (fraction.sample.variety.id if fraction.sample.variety
                else None)
            if key not in objects:
                objects[key] = {
                    'matrix': records[0].stp_matrix_client_description,
                    'variety': (fraction.sample.variety.description if
                        fraction.sample.variety else ''),
                    'reports': {},
                    }
            for report_id in res:
                if report_id[0] not in objects[key]['reports']:
                    report = ResultsReport(report_id[0])
                    objects[key]['reports'][report_id[0]] = {
                        'report_id': report.id,
                        'number': report.number,
                        'zone': (fraction.sample.cultivation_zone if
                        fraction.sample.cultivation_zone else ''),
                        'fractions': [],
                        }

                re = None
                analysis = None
                if report_id[1] == 'eq':
                        re = report_id[2]
                else:
                    if report_id[1] == 'low':
                        re = '< ' + report_id[2]
                    else:
                        if report_id[1] == 'nd':
                            re = report_id[1]
                analysis = report_id[3]

                objects[key]['reports'][report_id[0]]['fractions'].append({
                    'number': fraction.get_formated_number('sy-sn-fn'),
                    'treatment': fraction.sample.treatment,
                    'dosis': fraction.sample.dosis,
                    'glp_repetitions': fraction.sample.glp_repetitions,
                    'after_application_days': (
                        fraction.sample.after_application_days),
                    'sample_weight': fraction.sample.sample_weight,
                    'label': fraction.sample.label,
                    'analysis': analysis if analysis else '',
                    'result': re if re else '',
                    })

        report_context['objects'] = objects

        return report_context


class ProjectGLPReport10PrintStart(ModelView):
    'Rector scheme'
    __name__ = 'lims.project.glp_report.10.print.start'

    date_from = fields.Date('Ingress date from', required=True)
    date_to = fields.Date('to', required=True)
    stp_state = fields.Selection([
        ('canceled', 'Canceled'),
        ('finalized', 'Finalized'),
        ('initiated', 'Initiated'),
        ('unfinished', 'Unfinished'),
        ('pending', 'Pending'),
        ('no_status', 'No status'),
        ('requested', 'Requested'),
        ('all', 'All'),
        ], 'State', sort=False, required=True)

    @staticmethod
    def default_stp_state():
        return 'all'


class ProjectGLPReport10Print(Wizard):
    'Rector scheme'
    __name__ = 'lims.project.glp_report.10.print'

    start = StateView('lims.project.glp_report.10.print.start',
        'lims_project_study_plan.report_glp_10_print_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print', 'print_', 'tryton-print', default=True),
            ])
    print_ = StateAction('lims_project_study_plan.report_glp_10')

    def do_print_(self, action):
        data = {
            'date_from': self.start.date_from,
            'date_to': self.start.date_to,
            'stp_state': self.start.stp_state,
            }
        return action, data


class ProjectGLPReport10(Report):
    'Rector scheme'
    __name__ = 'lims.project.glp_report.10'

    @classmethod
    def get_context(cls, records, data):
        pool = Pool()
        Project = pool.get('lims.project')

        report_context = super(ProjectGLPReport10, cls).get_context(
            records, data)

        report_context['company'] = report_context['user'].company
        report_context['date_from'] = data['date_from']
        report_context['date_to'] = data['date_to']
        clause = [
            ('type', '=', 'study_plan'),
            ('stp_date', '>=', data['date_from']),
            ('stp_date', '<=', data['date_to']),
            ]

        if data['stp_state'] in ('canceled', 'finalized', 'initiated',
                'pending', 'requested'):
            clause.append(('stp_state', '=', data['stp_state']))
        elif data['stp_state'] == 'unfinished':
            clause.append([
                ('stp_state', '!=', 'finalized'),
                ('stp_state', '!=', None),
                ('stp_state', '!=', 'canceled')])
        elif data['stp_state'] == 'no_status':
            clause.append(('stp_state', '=', None))

        projects = Project.search(clause)

        objects = []
        for project in projects:
            objects.append({
                'stp_number': project.stp_number,
                'stp_code': project.code,
                'stp_glp': project.stp_glp,
                'stp_sponsor': (project.stp_sponsor.code
                    if project.stp_sponsor else ''),
                'stp_study_director': (project.stp_study_director.rec_name
                    if project.stp_study_director else ''),
                'stp_start_date': project.stp_start_date,
                'stp_end_date': project.stp_end_date,
                'stp_state': project.stp_state_string,
                'stp_proposal_start_date': project.stp_proposal_start_date,
                'stp_proposal_end_date': project.stp_proposal_end_date,
                'stp_product_brand': project.stp_product_brand,
                'stp_implementation_validation': (True if
                    project.stp_implementation_validation ==
                    'implementation_validation' else False),
                'stp_pattern_availability': project.stp_pattern_availability,
                'stp_matrix': project.stp_matrix_client_description,
                'stp_description': project.stp_description,
                'samples': [{
                    'entry_date': s.entry_date,
                    'packages': '%s %s' % (s.packages_quantity or '',
                        s.package_type.description if s.package_type
                        else ''),
                    'comments': str(s.comments or ''),
                    } for s in project.stp_samples_in_custody],
                })
        report_context['objects'] = objects

        return report_context


class ProjectGLPReport11(Report):
    'Reference/Test elements (FOR)'
    __name__ = 'lims.project.glp_report.11'

    @classmethod
    def execute(cls, ids, data):
        Project = Pool().get('lims.project')
        if len(ids) > 1:
            Project.raise_user_error('not_glp')

        project = Project(ids[0])
        if project.type != 'study_plan':
            Project.raise_user_error('not_glp')

        return super(ProjectGLPReport11, cls).execute(ids, data)

    @classmethod
    def get_context(cls, records, data):
        ProjectReferenceElement = Pool().get(
            'lims.project.reference_element')

        report_context = super(ProjectGLPReport11, cls).get_context(
            records, data)

        report_context['company'] = report_context['user'].company
        report_context['stp_number'] = records[0].stp_number
        report_context['code'] = records[0].code
        report_context['test_objects'] = []
        report_context['reference_objects'] = []

        elements = ProjectReferenceElement.search([
            ('project', '=', records[0].id),
            ])

        for element in elements:
            record = {
                'chemical_name': element.chemical_name or '',
                'common_name': element.common_name or '',
                'cas_number': element.cas_number or '',
                'catalog': element.input_product.catalog or '',
                'lot': element.lot.rec_name if element.lot else '',
                'purity_degree': (element.purity_degree.rec_name
                    if element.purity_degree else ''),
                'stability': element.stability or '',
                'homogeneity': element.homogeneity or '',
                'expiration_date': element.expiration_date,
                'reception_date': element.reception_date,
                'formula': element.formula or '',
                'molecular_weight': element.molecular_weight or '',
                'location': (element.location.rec_name if element.location
                    else ''),
                }
            if element.type == 'test':
                report_context['test_objects'].append(record)
            elif element.type == 'reference':
                report_context['reference_objects'].append(record)

        return report_context


class ProjectGLPReport12PrintStart(ModelView):
    'Changelog'
    __name__ = 'lims.project.glp_report.12.print.start'

    date_from = fields.Date('Date from', required=True)
    date_to = fields.Date('to', required=True)


class ProjectGLPReport12Print(Wizard):
    'Changelog'
    __name__ = 'lims.project.glp_report.12.print'

    start = StateView('lims.project.glp_report.12.print.start',
        'lims_project_study_plan.report_glp_12_print_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print', 'print_', 'tryton-print', default=True),
            ])
    print_ = StateAction('lims_project_study_plan.report_glp_12')

    def do_print_(self, action):
        data = {
            'date_from': self.start.date_from,
            'date_to': self.start.date_to,
            }
        return action, data


class ProjectGLPReport12(Report):
    'Changelog'
    __name__ = 'lims.project.glp_report.12'

    @classmethod
    def get_context(cls, records, data):
        pool = Pool()
        ProjectChangeLog = pool.get('lims.project.stp_changelog')

        report_context = super(ProjectGLPReport12, cls).get_context(
            records, data)

        report_context['company'] = report_context['user'].company
        report_context['date_from'] = data['date_from']
        report_context['date_to'] = data['date_to']

        changelogs = ProjectChangeLog.search([
            ('date2', '>=', data['date_from']),
            ('date2', '<=', data['date_to']),
            ], order=[
            ('project', 'ASC'), ('date', 'ASC'),
            ])

        objects = []
        for change in changelogs:
            project = change.project
            objects.append({
                'change_reason': change.reason,
                'change_date': change.date,
                'change_user': change.user.rec_name,
                'stp_number': project.stp_number,
                'stp_code': project.code,
                'stp_title': project.stp_title,
                'stp_sponsor': (project.stp_sponsor.code
                    if project.stp_sponsor else ''),
                'stp_glp': project.stp_glp,
                'stp_matrix': project.stp_matrix_client_description,
                'stp_product_brand': project.stp_product_brand,
                'stp_start_date': project.stp_start_date,
                'stp_end_date': project.stp_end_date,
                'stp_state': project.stp_state_string,
                'stp_proposal_start_date': project.stp_proposal_start_date,
                'stp_proposal_end_date': project.stp_proposal_end_date,
                'stp_rector_scheme_comments': str(
                    project.stp_rector_scheme_comments or ''),
                'stp_implementation_validation': (True if
                    project.stp_implementation_validation ==
                    'implementation_validation' else False),
                'stp_pattern_availability': (
                    project.stp_pattern_availability),
                'stp_target': str(project.stp_target or ''),
                'stp_description': project.stp_description,
                'stp_test_method': str(project.stp_test_method or ''),
                'stp_study_director': (project.stp_study_director.rec_name
                    if project.stp_study_director else ''),
                'stp_facility_director': (
                    project.stp_facility_director.rec_name
                    if project.stp_facility_director else ''),
                'stp_quality_unit': (project.stp_quality_unit.rec_name
                    if project.stp_quality_unit else ''),
                'stp_records': project.stp_records,
                'stp_laboratory_professionals': [{
                    'professional': p.professional.rec_name,
                    'position': p.position.description if p.position else '',
                    } for p in project.stp_laboratory_professionals],
                })

        report_context['objects'] = objects

        return report_context


class ProjectGLPReportStudyPlan(Report):
    'BPL Study plan'
    __name__ = 'lims.project.glp_report.study_plan'

    @classmethod
    def execute(cls, ids, data):
        Project = Pool().get('lims.project')
        if len(ids) > 1:
            Project.raise_user_error('not_glp')

        project = Project(ids[0])
        if project.type != 'study_plan':
            Project.raise_user_error('not_glp')

        return super(ProjectGLPReportStudyPlan, cls).execute(ids, data)

    @classmethod
    def get_context(cls, records, data):
        report_context = super(ProjectGLPReportStudyPlan, cls).get_context(
            records, data)

        project = records[0]

        report_context['company'] = report_context['user'].company
        c = report_context['user'].company.rec_name.split('-')
        company = c[0]
        report_context['company_name'] = company
        report_context['stp_number'] = project.stp_number
        report_context['code'] = project.code
        report_context['stp_title'] = project.stp_title
        report_context['stp_target'] = str(project.stp_target or '')
        report_context['stp_description'] = project.stp_description
        report_context['stp_sponsor'] = project.stp_sponsor
        report_context['stp_date'] = project.stp_date
        report_context['stp_reception_date_list'] = ', '.join(
            cls.get_reception_date(project.id))
        report_context['stp_start_date'] = project.stp_start_date
        report_context['stp_proposal_start_date'] = (
            project.stp_proposal_start_date)
        report_context['stp_proposal_end_date'] = project.stp_proposal_end_date
        report_context['stp_test_method'] = str(project.stp_test_method
            or '')
        report_context['stp_test_system'] = str(project.stp_test_system
            or '')
        report_context['stp_study_director'] = None
        report_context['stp_study_director_date'] = None
        report_context['stp_quality_unit'] = None
        report_context['stp_quality_unit_date'] = None
        report_context['stp_facility_director'] = None
        report_context['stp_facility_director_date'] = None
        report_context['stp_professionals'] = []
        report_context['stp_entry_list'] = ', '.join([
            e.number for e in cls.get_entry_list(project.id)])
        for pp in project.stp_laboratory_professionals:
            report_context['stp_professionals'].append(pp.professional.party)
            if pp.role_study_director:
                report_context['stp_study_director'] = pp.professional.party
                report_context['stp_study_director_date'] = pp.approval_date
            elif pp.role_quality_unit:
                report_context['stp_quality_unit'] = pp.professional.party
                report_context['stp_quality_unit_date'] = pp.approval_date
            elif pp.role_facility_director:
                report_context['stp_facility_director'] = pp.professional.party
                report_context['stp_facility_director_date'] = pp.approval_date

        return report_context

    @staticmethod
    def get_reception_date(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        ProjectSampleInCustody = pool.get('lims.project.sample_in_custody')

        cursor.execute('SELECT DISTINCT(psc.entry_date ) '
            'FROM "' + ProjectSampleInCustody._table + '" psc '
            'WHERE psc.project = %s ',
            (project_id,))
        return [x[0].strftime("%d/%m/%Y") for x in cursor.fetchall()]

    @staticmethod
    def get_entry_list(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Entry = pool.get('lims.entry')

        cursor.execute('SELECT DISTINCT(e.id) '
            'FROM "' + Entry._table + '" e '
            'WHERE e.project = %s ',
            (project_id,))
        return Entry.search([
            ('id', 'in', cursor.fetchall()),
            ])


class ProjectGLPReportFinalRP(Report):
    'BPL Final Report (RP)'
    __name__ = 'lims.project.glp_report.final_rp'

    @classmethod
    def execute(cls, ids, data):
        Project = Pool().get('lims.project')
        if len(ids) > 1:
            Project.raise_user_error('not_glp')

        project = Project(ids[0])
        if project.type != 'study_plan':
            Project.raise_user_error('not_glp')
        else:
            if project.stp_phase != 'study_plan':
                Project.raise_user_error('not_study_plan')
        return super(ProjectGLPReportFinalRP, cls).execute(ids, data)

    @classmethod
    def get_context(cls, records, data):
        report_context = super(ProjectGLPReportFinalRP, cls).get_context(
            records, data)

        project = records[0]

        report_context['company'] = report_context['user'].company
        c = report_context['user'].company.rec_name.split('-')
        company = c[0]
        report_context['company_name'] = company
        report_context['stp_title'] = project.stp_title
        report_context['stp_end_date'] = project.stp_end_date
        report_context['stp_number'] = project.stp_number
        report_context['code'] = project.code
        report_context['stp_sponsor'] = project.stp_sponsor
        report_context['stp_samples'] = ', '.join(
            cls.get_fraction(project.id))
        report_context['stp_reference_elements'] = [e for e in
            project.stp_reference_elements if e.type == 'reference']
        report_context['stp_reference_elements_list'] = ', '.join([
            e.common_name or ''
            for e in report_context['stp_reference_elements']])
        report_context['stp_matrix'] = project.stp_matrix_client_description
        report_context['stp_study_director'] = (
            project.stp_study_director.party if project.stp_study_director
            else None)
        report_context['stp_target'] = str(project.stp_target or '')
        report_context['stp_description'] = project.stp_description
        report_context['stp_test_elements'] = [e for e in
            project.stp_reference_elements if e.type == 'test']
        report_context['stp_professionals'] = [pp.professional.party
            for pp in project.stp_laboratory_professionals]
        report_context['stp_all_professionals'] = (
            cls.get_laboratory_professionals(project.id))
        report_context['stp_start_date'] = project.stp_start_date
        report_context['stp_experimental_start_date'] = (
            cls.get_experimental_start_date(project.id))
        report_context['stp_experimental_end_date'] = (
            cls.get_experimental_end_date(project.id))
        report_context['stp_lims_sample_input'] = (
            cls.get_lims_sample_input(project.id))
        report_context['stp_test_method'] = str(project.stp_test_method
            or '')
        report_context['stp_solvents_and_reagents'] = (
            project.stp_solvents_and_reagents)
        report_context['stp_results_reports_list'] = ', '.join([
            r.number for r in cls.get_results_reports(project.id)])
        report_context['stp_deviation_and_amendment'] = (
            project.stp_deviation_and_amendment)
        report_context['stp_reception_date_list'] = ', '.join(
            cls.get_reception_date(project.id))

        return report_context

    @staticmethod
    def get_experimental_start_date(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Planification = pool.get('lims.planification')
        NotebookLine = pool.get('lims.notebook.line')
        Service = pool.get('lims.service')
        Fraction = pool.get('lims.fraction')
        Sample = pool.get('lims.sample')
        Entry = pool.get('lims.entry')

        cursor.execute('SELECT MIN(p.start_date) '
            'FROM "' + Planification._table + '" p '
                'INNER JOIN "' + NotebookLine._table + '" nl '
                'ON nl.planification = p.id '
                'INNER JOIN "' + Service._table + '" srv '
                'ON nl.service = srv.id '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON srv.fraction = f.id '
                'INNER JOIN "' + Sample._table + '" s '
                'ON f.sample = s.id '
                'INNER JOIN "' + Entry._table + '" e '
                'ON s.entry = e.id '
            'WHERE e.project = %s '
                'AND nl.results_report IS NOT NULL',
            (project_id,))
        return cursor.fetchone()[0]

    @staticmethod
    def get_experimental_end_date(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        Service = pool.get('lims.service')
        Fraction = pool.get('lims.fraction')
        Sample = pool.get('lims.sample')
        Entry = pool.get('lims.entry')

        cursor.execute('SELECT MAX(nl.end_date) '
            'FROM "' + NotebookLine._table + '" nl '
                'INNER JOIN "' + Service._table + '" srv '
                'ON nl.service = srv.id '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON srv.fraction = f.id '
                'INNER JOIN "' + Sample._table + '" s '
                'ON f.sample = s.id '
                'INNER JOIN "' + Entry._table + '" e '
                'ON s.entry = e.id '
            'WHERE e.project = %s '
                'AND nl.results_report IS NOT NULL',
            (project_id,))
        return cursor.fetchone()[0]

    @staticmethod
    def get_results_reports(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        Service = pool.get('lims.service')
        Fraction = pool.get('lims.fraction')
        Sample = pool.get('lims.sample')
        Entry = pool.get('lims.entry')
        ResultsReport = pool.get('lims.results_report')

        cursor.execute('SELECT DISTINCT(nl.results_report) '
            'FROM "' + NotebookLine._table + '" nl '
                'INNER JOIN "' + Service._table + '" srv '
                'ON nl.service = srv.id '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON srv.fraction = f.id '
                'INNER JOIN "' + Sample._table + '" s '
                'ON f.sample = s.id '
                'INNER JOIN "' + Entry._table + '" e '
                'ON s.entry = e.id '
            'WHERE e.project = %s '
                'AND nl.results_report IS NOT NULL',
            (project_id,))
        return ResultsReport.search([
            ('id', 'in', cursor.fetchall()),
            ])

    @staticmethod
    def get_reception_date(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        ProjectSampleInCustody = pool.get('lims.project.sample_in_custody')

        cursor.execute('SELECT DISTINCT(psc.entry_date ) '
            'FROM "' + ProjectSampleInCustody._table + '" psc '
            'WHERE psc.project = %s ',
            (project_id,))
        return [x[0].strftime("%d/%m/%Y") for x in cursor.fetchall()]

    @staticmethod
    def get_lims_sample_input(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Planification = pool.get('lims.planification')
        NotebookLine = pool.get('lims.notebook.line')
        Service = pool.get('lims.service')
        Fraction = pool.get('lims.fraction')
        Sample = pool.get('lims.sample')
        Entry = pool.get('lims.entry')

        cursor.execute('SELECT MIN(srv.confirmation_date) '
            'FROM "' + Planification._table + '" p '
                'INNER JOIN "' + NotebookLine._table + '" nl '
                'ON nl.planification = p.id '
                'INNER JOIN "' + Service._table + '" srv '
                'ON nl.service = srv.id '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON srv.fraction = f.id '
                'INNER JOIN "' + Sample._table + '" s '
                'ON f.sample = s.id '
                'INNER JOIN "' + Entry._table + '" e '
                'ON s.entry = e.id '
            'WHERE e.project = %s '
                'AND nl.end_date IS NOT NULL',
            (project_id,))
        return cursor.fetchone()[0]

    @classmethod
    def get_laboratory_professionals(cls, project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LaboratoryProfessionals = pool.get('lims.project.stp_professional')
        Position = pool.get('lims.project.stp_professional.position')
        LaboratoryProfessional = pool.get('lims.laboratory.professional')
        Party = pool.get('party.party')

        cursor.execute('SELECT  p.description, pa.name '
            'FROM "' + LaboratoryProfessionals._table + '" lp '
                'INNER JOIN "' + Position._table + '" p '
                'ON lp.position = p.id '
                'INNER JOIN "' + LaboratoryProfessional._table + '" pr '
                'ON lp.professional = pr.id '
                'INNER JOIN "' + Party._table + '" pa '
                'ON pr.party = pa.id '
            'WHERE lp.project = %s ',
            (project_id,))
        professional_lines = {}
        professional_lines = cursor.fetchall()
        res = []
        if professional_lines:
            for line in professional_lines:
                line_p = ['%s: %s' % (line[0], line[1])]
                res.extend(line_p)
        return res

    @staticmethod
    def get_fraction(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Fraction = pool.get('lims.fraction')
        Sample = pool.get('lims.sample')
        Entry = pool.get('lims.entry')

        cursor.execute('SELECT f.number '
            'FROM "' + Entry._table + '" e '
                'INNER JOIN "' + Sample._table + '" s '
                'ON e.id = s.entry '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON s.id = f.sample '
            'WHERE e.project = %s ',
            (project_id,))
        return [x[0] for x in cursor.fetchall()]


class ProjectGLPReportFinalFOR(Report):
    'BPL Final Report (FOR)'
    __name__ = 'lims.project.glp_report.final_for'

    @classmethod
    def execute(cls, ids, data):
        Project = Pool().get('lims.project')
        if len(ids) > 1:
            Project.raise_user_error('not_glp')

        project = Project(ids[0])
        if project.type != 'study_plan':
            Project.raise_user_error('not_glp')
        else:
            if project.stp_phase != 'study_plan':
                Project.raise_user_error('not_study_plan')
        return super(ProjectGLPReportFinalFOR, cls).execute(ids, data)

    @classmethod
    def get_context(cls, records, data):
        report_context = super(ProjectGLPReportFinalFOR, cls).get_context(
            records, data)

        project = records[0]

        report_context['company'] = report_context['user'].company
        c = report_context['user'].company.rec_name.split('-')
        company = c[0]
        report_context['company_name'] = company
        report_context['stp_title'] = project.stp_title
        report_context['stp_end_date'] = project.stp_end_date
        report_context['stp_number'] = project.stp_number
        report_context['stp_sponsor'] = project.stp_sponsor
        report_context['stp_samples'] = ''
        report_context['code'] = project.code
        product_type_matrix = {}
        for s in project.stp_samples:
            if report_context['stp_samples']:
                report_context['stp_samples'] += ', '
            report_context['stp_samples'] += s.number
            key = (s.product_type.id, s.matrix.id)
            if key not in product_type_matrix:
                product_type_matrix[key] = '%s-%s' % (
                    s.product_type.code, s.matrix.code)
        report_context['product_type_matrix_list'] = ', '.join(
            list(product_type_matrix.values()))
        report_context['stp_test_elements'] = [e for e in
            project.stp_reference_elements if e.type == 'test']
        report_context['stp_test_elements_list'] = ', '.join([
            e.common_name or ''
            for e in report_context['stp_test_elements']])
        report_context['stp_analysis_list'] = cls.get_analysis_list(project.id)
        report_context['stp_study_director'] = (
            project.stp_study_director.party if project.stp_study_director
            else None)
        report_context['stp_target'] = str(project.stp_target or '')
        report_context['stp_description'] = project.stp_description
        report_context['stp_professionals'] = [pp.professional.party
            for pp in project.stp_laboratory_professionals]
        report_context['stp_start_date'] = project.stp_start_date
        report_context['stp_experimental_start_date'] = (
            cls.get_experimental_start_date(project.id))
        report_context['stp_experimental_end_date'] = (
            cls.get_experimental_end_date(project.id))
        report_context['stp_lims_sample_input'] = (
            cls.get_lims_sample_input(project.id))
        report_context['stp_all_professionals'] = (
            cls.get_laboratory_professionals(project.id))
        report_context['stp_test_method'] = str(project.stp_test_method
            or '')
        report_context['stp_reference_elements'] = [e for e in
            project.stp_reference_elements if e.type == 'reference']
        report_context['stp_solvents_and_reagents'] = (
            project.stp_solvents_and_reagents)
        report_context['stp_results_reports_list'] = ', '.join([
            r.number for r in cls.get_results_reports(project.id)])
        report_context['stp_deviation_and_amendment'] = (
            project.stp_deviation_and_amendment)
        report_context['stp_reception_date_list'] = ', '.join(
            cls.get_reception_date(project.id))

        return report_context

    @staticmethod
    def get_analysis_list(project_id):
        EntryDetailAnalysis = Pool().get('lims.entry.detail.analysis')

        analysis = {}
        details = EntryDetailAnalysis.search([
            ('entry.project', '=', project_id),
            ])
        for detail in details:
            if detail.analysis.id not in analysis:
                analysis[detail.analysis.id] = detail.analysis.description
        return ', '.join(list(analysis.values()))

    @staticmethod
    def get_experimental_start_date(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Planification = pool.get('lims.planification')
        NotebookLine = pool.get('lims.notebook.line')
        Service = pool.get('lims.service')
        Fraction = pool.get('lims.fraction')
        Sample = pool.get('lims.sample')
        Entry = pool.get('lims.entry')

        cursor.execute('SELECT MIN(p.start_date) '
            'FROM "' + Planification._table + '" p '
                'INNER JOIN "' + NotebookLine._table + '" nl '
                'ON nl.planification = p.id '
                'INNER JOIN "' + Service._table + '" srv '
                'ON nl.service = srv.id '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON srv.fraction = f.id '
                'INNER JOIN "' + Sample._table + '" s '
                'ON f.sample = s.id '
                'INNER JOIN "' + Entry._table + '" e '
                'ON s.entry = e.id '
            'WHERE e.project = %s '
                'AND nl.results_report IS NOT NULL',
            (project_id,))
        return cursor.fetchone()[0]

    @staticmethod
    def get_experimental_end_date(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        Service = pool.get('lims.service')
        Fraction = pool.get('lims.fraction')
        Sample = pool.get('lims.sample')
        Entry = pool.get('lims.entry')

        cursor.execute('SELECT MAX(nl.end_date) '
            'FROM "' + NotebookLine._table + '" nl '
                'INNER JOIN "' + Service._table + '" srv '
                'ON nl.service = srv.id '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON srv.fraction = f.id '
                'INNER JOIN "' + Sample._table + '" s '
                'ON f.sample = s.id '
                'INNER JOIN "' + Entry._table + '" e '
                'ON s.entry = e.id '
            'WHERE e.project = %s '
                'AND nl.results_report IS NOT NULL',
            (project_id,))
        return cursor.fetchone()[0]

    @staticmethod
    def get_results_reports(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        Service = pool.get('lims.service')
        Fraction = pool.get('lims.fraction')
        Sample = pool.get('lims.sample')
        Entry = pool.get('lims.entry')
        ResultsReport = pool.get('lims.results_report')

        cursor.execute('SELECT DISTINCT(nl.results_report) '
            'FROM "' + NotebookLine._table + '" nl '
                'INNER JOIN "' + Service._table + '" srv '
                'ON nl.service = srv.id '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON srv.fraction = f.id '
                'INNER JOIN "' + Sample._table + '" s '
                'ON f.sample = s.id '
                'INNER JOIN "' + Entry._table + '" e '
                'ON s.entry = e.id '
            'WHERE e.project = %s '
                'AND nl.results_report IS NOT NULL',
            (project_id,))
        return ResultsReport.search([
            ('id', 'in', cursor.fetchall()),
            ])

    @staticmethod
    def get_lims_sample_input(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Planification = pool.get('lims.planification')
        NotebookLine = pool.get('lims.notebook.line')
        Service = pool.get('lims.service')
        Fraction = pool.get('lims.fraction')
        Sample = pool.get('lims.sample')
        Entry = pool.get('lims.entry')

        cursor.execute('SELECT MIN(srv.confirmation_date) '
            'FROM "' + Planification._table + '" p '
                'INNER JOIN "' + NotebookLine._table + '" nl '
                'ON nl.planification = p.id '
                'INNER JOIN "' + Service._table + '" srv '
                'ON nl.service = srv.id '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON srv.fraction = f.id '
                'INNER JOIN "' + Sample._table + '" s '
                'ON f.sample = s.id '
                'INNER JOIN "' + Entry._table + '" e '
                'ON s.entry = e.id '
            'WHERE e.project = %s '
                'AND nl.end_date IS NOT NULL',
            (project_id,))
        return cursor.fetchone()[0]

    @staticmethod
    def get_reception_date(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        ProjectSampleInCustody = pool.get('lims.project.sample_in_custody')

        cursor.execute('SELECT DISTINCT(psc.entry_date ) '
            'FROM "' + ProjectSampleInCustody._table + '" psc '
            'WHERE psc.project = %s ',
            (project_id,))
        return [x[0].strftime("%d/%m/%Y") for x in cursor.fetchall()]

    @classmethod
    def get_laboratory_professionals(cls, project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LaboratoryProfessionals = pool.get('lims.project.stp_professional')
        Position = pool.get('lims.project.stp_professional.position')
        LaboratoryProfessional = pool.get('lims.laboratory.professional')
        Party = pool.get('party.party')

        cursor.execute('SELECT  p.description, pa.name '
            'FROM "' + LaboratoryProfessionals._table + '" lp '
                'INNER JOIN "' + Position._table + '" p '
                'ON lp.position = p.id '
                'INNER JOIN "' + LaboratoryProfessional._table + '" pr '
                'ON lp.professional = pr.id '
                'INNER JOIN "' + Party._table + '" pa '
                'ON pr.party = pa.id '
            'WHERE lp.project = %s ',
            (project_id,))
        professional_lines = {}
        professional_lines = cursor.fetchall()
        res = []
        if professional_lines:
            for line in professional_lines:
                line_p = ['%s: %s' % (line[0], line[1])]
                res.extend(line_p)
        return res


class ProjectGLPReportAnalyticalPhase(Report):
    'BPL Analytical Phase Report '
    __name__ = 'lims.project.glp_report.analytical_phase'

    @classmethod
    def execute(cls, ids, data):
        Project = Pool().get('lims.project')
        if len(ids) > 1:
            Project.raise_user_error('not_glp')

        project = Project(ids[0])
        if project.type != 'study_plan':
            Project.raise_user_error('not_glp')
        else:
            if project.stp_phase != 'analytical_phase':
                Project.raise_user_error('not_analytical_phase')
        return super(ProjectGLPReportAnalyticalPhase,
            cls).execute(ids, data)

    @classmethod
    def get_context(cls, records, data):
        report_context = super(ProjectGLPReportAnalyticalPhase,
            cls).get_context(records, data)

        project = records[0]

        report_context['company'] = report_context['user'].company
        c = report_context['user'].company.rec_name.split('-')
        company = c[0]
        report_context['company_name'] = company
        report_context['stp_title'] = project.stp_title
        report_context['stp_end_date'] = project.stp_end_date
        report_context['stp_number'] = project.stp_number
        report_context['code'] = project.code
        report_context['stp_sponsor'] = project.stp_sponsor
        report_context['stp_samples'] = ', '.join(
            cls.get_fraction(project.id))
        report_context['stp_reference_elements'] = [e for e in
            project.stp_reference_elements if e.type == 'reference']
        report_context['stp_reference_elements_list'] = ', '.join([
            e.common_name or ''
            for e in report_context['stp_reference_elements']])
        report_context['stp_matrix'] = project.stp_matrix_client_description
        report_context['stp_study_director'] = (
            project.stp_study_director.party if project.stp_study_director
            else None)
        report_context['stp_target'] = str(project.stp_target or '')
        report_context['stp_description'] = project.stp_description
        report_context['stp_test_elements'] = [e for e in
            project.stp_reference_elements if e.type == 'test']
        report_context['stp_professionals'] = [pp.professional.party
            for pp in project.stp_laboratory_professionals]
        report_context['stp_start_date'] = project.stp_start_date
        report_context['stp_experimental_start_date'] = (
            cls.get_experimental_start_date(project.id))
        report_context['stp_experimental_end_date'] = (
            cls.get_experimental_end_date(project.id))
        report_context['stp_lims_sample_input'] = (
            cls.get_lims_sample_input(project.id))
        report_context['stp_all_professionals'] = (
            cls.get_laboratory_professionals(project.id))
        report_context['stp_test_method'] = str(project.stp_test_method
            or '')
        report_context['stp_solvents_and_reagents'] = (
            project.stp_solvents_and_reagents)
        report_context['stp_results_reports_list'] = ', '.join([
            r.number for r in cls.get_results_reports(project.id)])
        report_context['stp_deviation_and_amendment'] = (
            project.stp_deviation_and_amendment)
        report_context['stp_reception_date_list'] = ', '.join(
            cls.get_reception_date(project.id))

        return report_context

    @staticmethod
    def get_experimental_start_date(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Planification = pool.get('lims.planification')
        NotebookLine = pool.get('lims.notebook.line')
        Service = pool.get('lims.service')
        Fraction = pool.get('lims.fraction')
        Sample = pool.get('lims.sample')
        Entry = pool.get('lims.entry')

        cursor.execute('SELECT MIN(p.start_date) '
            'FROM "' + Planification._table + '" p '
                'INNER JOIN "' + NotebookLine._table + '" nl '
                'ON nl.planification = p.id '
                'INNER JOIN "' + Service._table + '" srv '
                'ON nl.service = srv.id '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON srv.fraction = f.id '
                'INNER JOIN "' + Sample._table + '" s '
                'ON f.sample = s.id '
                'INNER JOIN "' + Entry._table + '" e '
                'ON s.entry = e.id '
            'WHERE e.project = %s '
                'AND nl.results_report IS NOT NULL',
            (project_id,))
        return cursor.fetchone()[0]

    @staticmethod
    def get_experimental_end_date(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        Service = pool.get('lims.service')
        Fraction = pool.get('lims.fraction')
        Sample = pool.get('lims.sample')
        Entry = pool.get('lims.entry')

        cursor.execute('SELECT MAX(nl.end_date) '
            'FROM "' + NotebookLine._table + '" nl '
                'INNER JOIN "' + Service._table + '" srv '
                'ON nl.service = srv.id '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON srv.fraction = f.id '
                'INNER JOIN "' + Sample._table + '" s '
                'ON f.sample = s.id '
                'INNER JOIN "' + Entry._table + '" e '
                'ON s.entry = e.id '
            'WHERE e.project = %s '
                'AND nl.results_report IS NOT NULL',
            (project_id,))
        return cursor.fetchone()[0]

    @staticmethod
    def get_results_reports(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        NotebookLine = pool.get('lims.notebook.line')
        Service = pool.get('lims.service')
        Fraction = pool.get('lims.fraction')
        Sample = pool.get('lims.sample')
        Entry = pool.get('lims.entry')
        ResultsReport = pool.get('lims.results_report')

        cursor.execute('SELECT DISTINCT(nl.results_report) '
            'FROM "' + NotebookLine._table + '" nl '
                'INNER JOIN "' + Service._table + '" srv '
                'ON nl.service = srv.id '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON srv.fraction = f.id '
                'INNER JOIN "' + Sample._table + '" s '
                'ON f.sample = s.id '
                'INNER JOIN "' + Entry._table + '" e '
                'ON s.entry = e.id '
            'WHERE e.project = %s '
                'AND nl.results_report IS NOT NULL',
            (project_id,))
        return ResultsReport.search([
            ('id', 'in', cursor.fetchall()),
            ])

    @staticmethod
    def get_lims_sample_input(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Planification = pool.get('lims.planification')
        NotebookLine = pool.get('lims.notebook.line')
        Service = pool.get('lims.service')
        Fraction = pool.get('lims.fraction')
        Sample = pool.get('lims.sample')
        Entry = pool.get('lims.entry')

        cursor.execute('SELECT MIN(srv.confirmation_date) '
            'FROM "' + Planification._table + '" p '
                'INNER JOIN "' + NotebookLine._table + '" nl '
                'ON nl.planification = p.id '
                'INNER JOIN "' + Service._table + '" srv '
                'ON nl.service = srv.id '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON srv.fraction = f.id '
                'INNER JOIN "' + Sample._table + '" s '
                'ON f.sample = s.id '
                'INNER JOIN "' + Entry._table + '" e '
                'ON s.entry = e.id '
            'WHERE e.project = %s '
                'AND nl.end_date IS NOT NULL',
            (project_id,))
        return cursor.fetchone()[0]

    @staticmethod
    def get_reception_date(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        ProjectSampleInCustody = pool.get('lims.project.sample_in_custody')

        cursor.execute('SELECT DISTINCT(psc.entry_date ) '
            'FROM "' + ProjectSampleInCustody._table + '" psc '
            'WHERE psc.project = %s ',
            (project_id,))
        return [x[0].strftime("%d/%m/%Y") for x in cursor.fetchall()]

    @classmethod
    def get_laboratory_professionals(cls, project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        LaboratoryProfessionals = pool.get('lims.project.stp_professional')
        Position = pool.get('lims.project.stp_professional.position')
        LaboratoryProfessional = pool.get('lims.laboratory.professional')
        Party = pool.get('party.party')

        cursor.execute('SELECT  p.description, pa.name '
            'FROM "' + LaboratoryProfessionals._table + '" lp '
                'INNER JOIN "' + Position._table + '" p '
                'ON lp.position = p.id '
                'INNER JOIN "' + LaboratoryProfessional._table + '" pr '
                'ON lp.professional = pr.id '
                'INNER JOIN "' + Party._table + '" pa '
                'ON pr.party = pa.id '
            'WHERE lp.project = %s ',
            (project_id,))
        professional_lines = {}
        professional_lines = cursor.fetchall()
        res = []
        if professional_lines:
            for line in professional_lines:
                line_p = ['%s: %s' % (line[0], line[1])]
                res.extend(line_p)
        return res

    @staticmethod
    def get_fraction(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        Fraction = pool.get('lims.fraction')
        Sample = pool.get('lims.sample')
        Entry = pool.get('lims.entry')

        cursor.execute('SELECT f.number '
            'FROM "' + Entry._table + '" e '
                'INNER JOIN "' + Sample._table + '" s '
                'ON e.id = s.entry '
                'INNER JOIN "' + Fraction._table + '" f '
                'ON s.id = f.sample '
            'WHERE e.project = %s ',
            (project_id,))
        return [x[0] for x in cursor.fetchall()]


class ProjectGLPReport13(Report):
    'GLP 13. GLP-007- Annex 3 Sample preparation registration GLP'
    __name__ = 'lims.project.glp_report.13'

    @classmethod
    def execute(cls, ids, data):
        Project = Pool().get('lims.project')
        if len(ids) > 1:
            Project.raise_user_error('not_glp')

        project = Project(ids[0])
        if project.type != 'study_plan':
            Project.raise_user_error('not_glp')

        return super(ProjectGLPReport13, cls).execute(ids, data)

    @classmethod
    def get_context(cls, records, data):
        pool = Pool()
        Fraction = pool.get('lims.fraction')

        report_context = super(ProjectGLPReport13, cls).get_context(
            records, data)

        report_context['company'] = report_context['user'].company
        report_context['stp_matrix'] = records[0].stp_matrix_client_description
        report_context['code'] = records[0].code
        report_context['stp_reference_objects_list'] = ', '.join([
            r.common_name for r in
            cls.get_reference_objects_list(records[0].id)])
        report_context['stp_test_method'] = records[0].stp_test_method

        fractions = Fraction.search([
            ('sample.entry.project', '=', records[0].id),
            ], order=[('number', 'ASC')])

        objects = []
        for fraction in fractions:
            objects.append({
                'number': fraction.get_formated_number('sy-sn-fn'),
                'label': fraction.sample.label,
                'fraction_type': fraction.type.code,
                })
        report_context['objects'] = objects
        return report_context

    @staticmethod
    def get_reference_objects_list(project_id):
        cursor = Transaction().connection.cursor()
        pool = Pool()
        ReferenceElement = pool.get('lims.project.reference_element')
        Entry = pool.get('lims.entry')

        cursor.execute('SELECT DISTINCT(el.id) '
            'FROM "' + ReferenceElement._table + '" el '
                'INNER JOIN "' + Entry._table + '" e '
                'ON el.project = e.project '
            'WHERE e.project = %s ',
            (project_id,))
        return ReferenceElement.search([
            ('id', 'in', cursor.fetchall()),
            ])
