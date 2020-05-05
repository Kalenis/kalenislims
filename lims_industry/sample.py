# This file is part of lims_industry module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateTransition, StateView, Button
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, Bool
from trytond.transaction import Transaction

__all__ = ['Entry', 'Sample', 'CreateSampleStart', 'CreateSample',
    'EditSampleStart', 'EditSample']


class Entry(metaclass=PoolMeta):
    __name__ = 'lims.entry'

    @classmethod
    def confirm(cls, entries):
        Sample = Pool().get('lims.sample')
        super(Entry, cls).confirm(entries)
        samples = [s for e in entries for s in e.samples]
        Sample._confirm_samples(samples)


class Sample(metaclass=PoolMeta):
    __name__ = 'lims.sample'

    equipment = fields.Many2One('lims.equipment', 'Equipment',
        domain=[('party', '=', Eval('party'))], depends=['party'])
    component = fields.Many2One('lims.component', 'Component',
        domain=[('equipment', '=', Eval('equipment'))], depends=['equipment'])
    comercial_product = fields.Many2One('lims.comercial.product',
        'Comercial Product')
    ind_sampling_date = fields.Date('Sampling date')
    ind_volume = fields.Float('Received volume')
    sampling_type = fields.Many2One('lims.sampling.type',
        'Sampling Type')
    ind_operational_detail = fields.Text('Operational detail')
    ind_work_environment = fields.Text('Work environment')
    ind_analysis_reason = fields.Text('Reason for analysis')
    missing_data = fields.Boolean('Missing data')
    attributes_domain = fields.Function(fields.Many2Many(
        'lims.sample.attribute', None, None, 'Attributes domain'),
        'on_change_with_attributes_domain')
    sample_photo = fields.Binary('Sample Photo',
        file_id='sample_photo_id', store_prefix='sample')
    sample_photo_id = fields.Char('Sample Photo ID', readonly=True)
    label_photo = fields.Binary('Label Photo',
        file_id='label_photo_id', store_prefix='sample')
    label_photo_id = fields.Char('Label Photo ID', readonly=True)
    oil_added = fields.Float('Liters Oil added')
    hours_equipment = fields.Integer('Hs. Equipment')
    hours_component = fields.Integer('Hs. Component')
    hours_oil = fields.Integer('Hs. Oil')
    changed_oil = fields.Boolean('Did change Oil?')

    @classmethod
    def __setup__(cls):
        super(Sample, cls).__setup__()
        cls.product_type.states['readonly'] = Bool(Eval('component'))
        if 'component' not in cls.product_type.depends:
            cls.product_type.depends.append('component')
        cls.matrix.states['readonly'] = Bool(Eval('comercial_product'))
        if 'comercial_product' not in cls.matrix.depends:
            cls.matrix.depends.append('comercial_product')
        cls.attributes.domain = [('id', 'in', Eval('attributes_domain'))]
        if 'attributes_domain' not in cls.attributes.depends:
            cls.attributes.depends.append('attributes_domain')

    @fields.depends('component')
    def on_change_component(self):
        if self.component:
            if self.component.product_type:
                self.product_type = self.component.product_type.id
            if self.component.comercial_product:
                self.comercial_product = self.component.comercial_product.id
                self.on_change_comercial_product()

    @fields.depends('comercial_product')
    def on_change_comercial_product(self):
        if self.comercial_product and self.comercial_product.matrix:
            self.matrix = self.comercial_product.matrix.id

    @fields.depends('product_type', '_parent_product_type.attribute_set')
    def on_change_with_attributes_domain(self, name=None):
        pool = Pool()
        SampleAttributeAttributeSet = pool.get(
            'lims.sample.attribute-attribute.set')
        attribute_set = None
        if self.product_type and self.product_type.attribute_set:
            attribute_set = self.product_type.attribute_set.id
        res = SampleAttributeAttributeSet.search([
            ('attribute_set', '=', attribute_set),
            ])
        return [x.attribute.id for x in res]

    @classmethod
    def _confirm_samples(cls, samples):
        TaskTemplate = Pool().get('lims.administrative.task.template')
        TaskTemplate.create_tasks('sample_missing_data',
            cls._for_task_missing_data(samples))
        TaskTemplate.create_tasks('sample_insufficient_volume',
            cls._for_task_required_volume(samples))

    @classmethod
    def _for_task_missing_data(cls, samples):
        AdministrativeTask = Pool().get('lims.administrative.task')
        res = []
        for sample in samples:
            if not sample.missing_data:
                continue
            if AdministrativeTask.search([
                    ('type', '=', 'sample_missing_data'),
                    ('origin', '=', '%s,%s' % (cls.__name__, sample.id)),
                    ('state', 'not in', ('done', 'discarded')),
                    ]):
                continue
            res.append(sample)
        return res

    @classmethod
    def _for_task_required_volume(cls, samples):
        pool = Pool()
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        AdministrativeTask = pool.get('lims.administrative.task')
        res = []
        for sample in samples:
            received_volume = sample.ind_volume or 0
            analysis_detail = EntryDetailAnalysis.search([
                ('sample', '=', sample.id)])
            for detail in analysis_detail:
                received_volume -= (detail.analysis.ind_volume or 0)
            if received_volume >= 0:
                continue
            if AdministrativeTask.search([
                    ('type', '=', 'sample_insufficient_volume'),
                    ('origin', '=', '%s,%s' % (cls.__name__, sample.id)),
                    ('state', 'not in', ('done', 'discarded')),
                    ]):
                continue
            res.append(sample)
        return res


class CreateSampleStart(metaclass=PoolMeta):
    __name__ = 'lims.create_sample.start'

    ind_required = fields.Function(fields.Boolean('Industry required'),
        'on_change_with_ind_required')
    equipment = fields.Many2One('lims.equipment', 'Equipment',
        domain=[('party', '=', Eval('party'))],
        states={'required': Bool(Eval('ind_required'))},
        depends=['party', 'ind_required'])
    component = fields.Many2One('lims.component', 'Component',
        domain=[('equipment', '=', Eval('equipment'))],
        states={'required': Bool(Eval('ind_required'))},
        depends=['equipment', 'ind_required'])
    comercial_product = fields.Many2One('lims.comercial.product',
        'Comercial Product', depends=['ind_required'],
        states={'required': Bool(Eval('ind_required'))})
    label = fields.Char('Label')
    ind_sampling_date = fields.Date('Sampling date', depends=['ind_required'],
        states={'required': Bool(Eval('ind_required'))})
    ind_volume = fields.Float('Received volume', depends=['ind_required'],
        states={'required': Bool(Eval('ind_required'))})
    sampling_type = fields.Many2One('lims.sampling.type',
        'Sampling Type', depends=['ind_required'],
        states={'required': Bool(Eval('ind_required'))})
    ind_operational_detail = fields.Text('Operational detail')
    ind_work_environment = fields.Text('Work environment')
    ind_analysis_reason = fields.Text('Reason for analysis')
    missing_data = fields.Boolean('Missing data')
    attributes_domain = fields.Function(fields.Many2Many(
        'lims.sample.attribute', None, None, 'Attributes domain'),
        'on_change_with_attributes_domain')
    sample_photo = fields.Binary('Sample Photo')
    label_photo = fields.Binary('Label Photo')
    oil_added = fields.Float('Liters Oil added')
    hours_equipment = fields.Integer('Hs. Equipment')
    hours_component = fields.Integer('Hs. Component')
    hours_oil = fields.Integer('Hs. Oil')
    changed_oil = fields.Boolean('Did change Oil?')

    @classmethod
    def __setup__(cls):
        super(CreateSampleStart, cls).__setup__()
        for field in ('component', 'comercial_product'):
            cls.analysis_domain.on_change_with.add(field)
        cls.product_type.states['readonly'] = Bool(Eval('component'))
        if 'component' not in cls.product_type.depends:
            cls.product_type.depends.append('component')
        cls.matrix.states['readonly'] = Bool(Eval('comercial_product'))
        if 'comercial_product' not in cls.matrix.depends:
            cls.matrix.depends.append('comercial_product')
        cls.attributes.domain = [('id', 'in', Eval('attributes_domain'))]
        if 'attributes_domain' not in cls.attributes.depends:
            cls.attributes.depends.append('attributes_domain')

    @fields.depends('fraction_type')
    def on_change_with_ind_required(self, name=None):
        Config = Pool().get('lims.configuration')
        if self.fraction_type:
            if self.fraction_type == Config(1).mcl_fraction_type:
                return True
        return False

    @fields.depends('component')
    def on_change_component(self):
        if self.component:
            if self.component.product_type:
                self.product_type = self.component.product_type.id
            if self.component.comercial_product:
                self.comercial_product = self.component.comercial_product.id
                self.on_change_comercial_product()

    @fields.depends('comercial_product')
    def on_change_comercial_product(self):
        if self.comercial_product and self.comercial_product.matrix:
            self.matrix = self.comercial_product.matrix.id

    @fields.depends('product_type', 'component',
        '_parent_product_type.attribute_set')
    def on_change_with_attributes_domain(self, name=None):
        pool = Pool()
        SampleAttributeAttributeSet = pool.get(
            'lims.sample.attribute-attribute.set')
        attribute_set = None
        if self.product_type and self.product_type.attribute_set:
            attribute_set = self.product_type.attribute_set.id
        res = SampleAttributeAttributeSet.search([
            ('attribute_set', '=', attribute_set),
            ])
        return [x.attribute.id for x in res]

    @fields.depends('label')
    def on_change_label(self):
        self.labels = self.label


class CreateSample(metaclass=PoolMeta):
    __name__ = 'lims.create_sample'

    start = StateView('lims.create_sample.start',
        'lims.lims_create_sample_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Create same Equipment', 'create_continue', 'tryton-ok'),
            Button('Create', 'create_', 'tryton-ok', default=True),
            ])
    create_continue = StateTransition()

    def default_start(self, fields):
        defaults = super(CreateSample, self).default_start(fields)
        for field in ('equipment', 'storage_location'):
            if (hasattr(self.start, field) and getattr(self.start, field)):
                defaults[field] = getattr(self.start, field).id
        return defaults

    def _get_samples_defaults(self, entry_id):
        samples_defaults = super(CreateSample,
            self)._get_samples_defaults(entry_id)

        equipment_id = None
        if (hasattr(self.start, 'equipment') and
                getattr(self.start, 'equipment')):
            equipment_id = getattr(self.start, 'equipment').id
        component_id = None
        if (hasattr(self.start, 'component') and
                getattr(self.start, 'component')):
            component_id = getattr(self.start, 'component').id
        comercial_product_id = None
        if (hasattr(self.start, 'comercial_product') and
                getattr(self.start, 'comercial_product')):
            comercial_product_id = getattr(self.start, 'comercial_product').id
        sampling_type_id = None
        if (hasattr(self.start, 'sampling_type') and
                getattr(self.start, 'sampling_type')):
            sampling_type_id = getattr(self.start, 'sampling_type').id
        ind_sampling_date = (hasattr(self.start,
            'ind_sampling_date') and getattr(self.start,
            'ind_sampling_date') or None)
        ind_volume = (hasattr(self.start,
            'ind_volume') and getattr(self.start,
            'ind_volume') or None)
        ind_operational_detail = (hasattr(self.start,
            'ind_operational_detail') and getattr(self.start,
            'ind_operational_detail') or None)
        ind_work_environment = (hasattr(self.start,
            'ind_work_environment') and getattr(self.start,
            'ind_work_environment') or None)
        ind_analysis_reason = (hasattr(self.start,
            'ind_analysis_reason') and getattr(self.start,
            'ind_analysis_reason') or None)
        missing_data = (hasattr(self.start, 'missing_data') and
            getattr(self.start, 'missing_data') or False)
        sample_photo = (hasattr(self.start, 'sample_photo') and
            getattr(self.start, 'sample_photo') or None)
        label_photo = (hasattr(self.start, 'label_photo') and
            getattr(self.start, 'label_photo') or None)
        oil_added = (hasattr(self.start, 'oil_added') and
            getattr(self.start, 'oil_added') or None)
        hours_equipment = (hasattr(self.start, 'hours_equipment') and
            getattr(self.start, 'hours_equipment') or None)
        hours_component = (hasattr(self.start, 'hours_component') and
            getattr(self.start, 'hours_component') or None)
        hours_oil = (hasattr(self.start, 'hours_oil') and
            getattr(self.start, 'hours_oil') or None)
        changed_oil = (hasattr(self.start, 'changed_oil') and
            getattr(self.start, 'changed_oil') or False)

        for sample_defaults in samples_defaults:
            sample_defaults['equipment'] = equipment_id
            sample_defaults['component'] = component_id
            sample_defaults['comercial_product'] = comercial_product_id
            sample_defaults['ind_sampling_date'] = ind_sampling_date
            sample_defaults['ind_volume'] = ind_volume
            sample_defaults['sampling_type'] = sampling_type_id
            sample_defaults['ind_operational_detail'] = ind_operational_detail
            sample_defaults['ind_work_environment'] = ind_work_environment
            sample_defaults['ind_analysis_reason'] = ind_analysis_reason
            sample_defaults['missing_data'] = missing_data
            sample_defaults['sample_photo'] = sample_photo
            sample_defaults['label_photo'] = label_photo
            sample_defaults['oil_added'] = oil_added
            sample_defaults['hours_equipment'] = hours_equipment
            sample_defaults['hours_component'] = hours_component
            sample_defaults['hours_oil'] = hours_oil
            sample_defaults['changed_oil'] = changed_oil

        return samples_defaults

    def transition_create_continue(self):
        self.transition_create_()
        return 'start'


class EditSampleStart(ModelView):
    'Edit Samples'
    __name__ = 'lims.sample.edit.start'

    party = fields.Many2One('party.party', 'Party')
    plant = fields.Many2One('lims.plant', 'Plant',
        domain=[('party', '=', Eval('party'))],
        depends=['party'])
    equipment = fields.Many2One('lims.equipment', 'Equipment',
        domain=[('plant', '=', Eval('plant'))],
        depends=['plant'])
    component = fields.Many2One('lims.component', 'Component',
        domain=[('equipment', '=', Eval('equipment'))],
        depends=['equipment'])


class EditSample(Wizard):
    'Edit Samples'
    __name__ = 'lims.sample.edit'

    start = StateView('lims.sample.edit.start',
        'lims_industry.edit_sample_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Confirm', 'confirm', 'tryton-ok', default=True),
            ])
    confirm = StateTransition()

    def _get_filtered_samples(self):
        Sample = Pool().get('lims.sample')
        samples = Sample.browse(Transaction().context['active_ids'])
        return [s for s in samples if s.entry.state == 'draft']

    def default_start(self, fields):
        samples = self._get_filtered_samples()
        party_id = None
        for sample in samples:
            if not party_id:
                party_id = sample.party.id
            elif party_id != sample.party.id:
                party_id = None
                break
        return {
            'party': party_id,
            }

    def transition_confirm(self):
        component_changed = bool(self.start.component)
        equipment_changed = bool(self.start.equipment)
        party_changed = bool(self.start.party)

        samples = self._get_filtered_samples()
        for sample in samples:
            if component_changed:
                sample.component = self.start.component.id
            if equipment_changed:
                sample.equipment = self.start.equipment.id
            if party_changed:
                if self.start.party.id != sample.party.id:
                    entry = self._new_entry()
                    sample.entry = entry.id
            sample.save()
        return 'end'

    def _new_entry(self):
        pool = Pool()
        Entry = pool.get('lims.entry')
        entry = Entry()
        entry.party = self.start.party.id
        entry.invoice_party = self.start.party.id
        entry.state = 'draft'
        entry.save()
        return entry
