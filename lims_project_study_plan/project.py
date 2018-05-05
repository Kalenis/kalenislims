# -*- coding: utf-8 -*-
# This file is part of lims_project_study_plan module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelSQL, ModelView, fields, Unique
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Eval, Equal, Bool, Not, And, Or
from trytond.transaction import Transaction

__all__ = ['LimsProject', 'LimsEntry', 'LimsProjectReferenceElement',
    'LimsProjectSolventAndReagent', 'LimsProjectSampleInCustody',
    'LimsProjectDeviationAndAmendment',
    'LimsProjectDeviationAndAmendmentProfessional', 'LimsProjectChangeLog',
    'LimsSample', 'LimsCreateSampleStart', 'LimsCreateSample',
    'LimsProjectProfessionalPosition', 'LimsProjectLaboratoryProfessional',
    'Lot']

STATES = {
    'readonly': Bool(Equal(Eval('stp_state'), 'finalized')),
    }
DEPENDS = ['stp_state']
PROJECT_TYPE = ('study_plan', 'Study plan')


class LimsProject:
    __name__ = 'lims.project'
    __metaclass__ = PoolMeta

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
        super(LimsProject, cls).__setup__()
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
        return super(LimsProject, cls).view_attributes() + [
            ('//group[@id="study_plan"]', 'states', {
                    'invisible': Not(Bool(Equal(Eval('type'), 'study_plan'))),
                    })]

    @classmethod
    def create(cls, vlist):
        pool = Pool()
        LimsLabWorkYear = pool.get('lims.lab.workyear')
        Sequence = pool.get('ir.sequence.strict')

        workyear_id = LimsLabWorkYear.find()
        workyear = LimsLabWorkYear(workyear_id)
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
        return super(LimsProject, cls).create(vlist)

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
        LimsNotebookLine = Pool().get('lims.notebook.line')

        stp_test_system = None
        notebook_lines = LimsNotebookLine.search([
            ('notebook.fraction.sample.entry.project', '=', self.id),
            ('device', '!=', None),
            ], order=[('device', 'ASC')])
        if notebook_lines:
            devices = {}
            for line in notebook_lines:
                if line.device.id not in devices:
                    devices[line.device.id] = line.device.rec_name
            if devices:
                stp_test_system = '\n'.join([d for d in devices.values()])
        self.stp_test_system = stp_test_system

    @ModelView.button_change('stp_test_method')
    def get_stp_test_method(self, name=None):
        LimsNotebookLine = Pool().get('lims.notebook.line')

        stp_test_method = None
        notebook_lines = LimsNotebookLine.search([
            ('notebook.fraction.sample.entry.project', '=', self.id),
            ('method', '!=', None),
            ], order=[('method', 'ASC')])
        if notebook_lines:
            methods = {}
            for line in notebook_lines:
                if line.method.id not in methods:
                    methods[line.method.id] = line.method.rec_name
            if methods:
                stp_test_method = '\n'.join([m for m in methods.values()])
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
        LimsSample = Pool().get('lims.sample')
        samples = LimsSample.search([
            ('entry.project', '=', self.id),
            ], order=[('number', 'ASC')])
        if samples:
            return [s.id for s in samples]
        return []

    def get_stp_notebook_lines(self, name=None):
        LimsNotebookLine = Pool().get('lims.notebook.line')
        notebook_lines = LimsNotebookLine.search([
            ('notebook.fraction.sample.entry.project', '=', self.id),
            ], order=[('notebook', 'ASC')])
        if notebook_lines:
            return [nl.id for nl in notebook_lines]
        return []


class LimsEntry:
    __name__ = 'lims.entry'
    __metaclass__ = PoolMeta

    @classmethod
    def __setup__(cls):
        super(LimsEntry, cls).__setup__()
        project_type = PROJECT_TYPE
        if project_type not in cls.project_type.selection:
            cls.project_type.selection.append(project_type)


class LimsProjectLaboratoryProfessional(ModelSQL, ModelView):
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
        super(LimsProjectLaboratoryProfessional, cls).__setup__()
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
        super(LimsProjectLaboratoryProfessional, cls).validate(professionals)
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


class LimsProjectProfessionalPosition(ModelSQL, ModelView):
    'Professional Position'
    __name__ = 'lims.project.stp_professional.position'
    _rec_name = 'description'

    code = fields.Char('Code', required=True)
    description = fields.Char('Description', required=True)

    @classmethod
    def __setup__(cls):
        super(LimsProjectProfessionalPosition, cls).__setup__()
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


class LimsProjectReferenceElement(ModelSQL, ModelView):
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


class LimsProjectSolventAndReagent(ModelSQL, ModelView):
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


class LimsProjectSampleInCustody(ModelSQL, ModelView):
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
        return super(LimsProjectSampleInCustody, cls).create(vlist)


class LimsProjectDeviationAndAmendment(ModelSQL, ModelView):
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
        super(LimsProjectDeviationAndAmendment, cls).__setup__()
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
        return super(LimsProjectDeviationAndAmendment, cls).create(vlist)

    @classmethod
    def get_next_number(cls, key, count):
        number = cls.search_count([
            ('project', '=', key[0]),
            ('type', '=', key[1]),
            ('document_type', '=', key[2]),
            ])
        number += count
        return str(number)


class LimsProjectDeviationAndAmendmentProfessional(ModelSQL, ModelView):
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


class LimsProjectChangeLog(ModelSQL):
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
                'WHERE (' + timezone_datetime + ')::date '
                + operator_ + ' %s::date', clause[2:3])
        return [('id', 'in', [x[0] for x in cursor.fetchall()])]


class LimsSample:
    __name__ = 'lims.sample'
    __metaclass__ = PoolMeta

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
        return super(LimsSample, cls).view_attributes() + [
            ('//page[@id="study_plan"]', 'states', {
                    'invisible': Not(Bool(Equal(
                        Eval('project_type'), 'study_plan'))),
                    })]


class LimsCreateSampleStart:
    __name__ = 'lims.create_sample.start'
    __metaclass__ = PoolMeta

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
        return super(LimsCreateSampleStart, cls).view_attributes() + [
            ('//page[@id="study_plan"]', 'states', {
                    'invisible': Not(Bool(Equal(
                        Eval('project_type'), 'study_plan'))),
                    })]


class LimsCreateSample:
    __name__ = 'lims.create_sample'
    __metaclass__ = PoolMeta

    def _get_samples_defaults(self, entry_id):
        samples_defaults = super(LimsCreateSample,
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


class Lot:
    __name__ = 'stock.lot'
    __metaclass__ = PoolMeta

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
