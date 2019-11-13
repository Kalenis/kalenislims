# This file is part of lims_industry module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelSQL, ModelView, fields
from trytond.wizard import Wizard, StateTransition, StateView, Button
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, Bool
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.i18n import gettext

__all__ = ['Entry', 'Sample', 'CreateSampleStart', 'CreateSample',
    'EditSampleStart', 'EditSample', 'Fraction', 'Aliquot']


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
        required=True, domain=[('party', '=', Eval('party'))],
        depends=['party'])
    component = fields.Many2One('lims.component', 'Component',
        required=True, domain=[('equipment', '=', Eval('equipment'))],
        depends=['equipment'])
    comercial_product = fields.Many2One('lims.comercial.product',
        'Comercial Product', required=True)
    ind_sampling_date = fields.Date('Sampling date', required=True)
    ind_volume = fields.Float('Received volume', required=True)
    sampling_type = fields.Many2One('lims.sampling.type',
        'Sampling Type', required=True)
    ind_operational_detail = fields.Text('Operational detail')
    ind_work_environment = fields.Text('Work environment')
    ind_analysis_reason = fields.Text('Reason for analysis')
    missing_data = fields.Boolean('Missing data')
    attributes = fields.Dict('lims.sample.attribute', 'Attributes',
        domain=[('id', 'in', Eval('attributes_domain'))],
        depends=['attributes_domain'])
    attributes_domain = fields.Function(fields.Many2Many(
        'lims.sample.attribute', None, None, 'Attributes domain'),
        'on_change_with_attributes_domain')
    sample_photo = fields.Binary('Sample Photo',
        file_id='sample_photo_id', store_prefix='sample')
    sample_photo_id = fields.Char('Sample Photo ID', readonly=True)
    label_photo = fields.Binary('Label Photo',
        file_id='label_photo_id', store_prefix='sample')
    label_photo_id = fields.Char('Label Photo ID', readonly=True)

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

    @fields.depends('product_type')
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

    equipment = fields.Many2One('lims.equipment', 'Equipment',
        required=True, domain=[('party', '=', Eval('party'))],
        depends=['party'])
    component = fields.Many2One('lims.component', 'Component',
        required=True, domain=[('equipment', '=', Eval('equipment'))],
        depends=['equipment'])
    comercial_product = fields.Many2One('lims.comercial.product',
        'Comercial Product', required=True)
    label = fields.Char('Label')
    ind_sampling_date = fields.Date('Sampling date', required=True)
    ind_volume = fields.Float('Received volume', required=True)
    sampling_type = fields.Many2One('lims.sampling.type',
        'Sampling Type', required=True)
    ind_operational_detail = fields.Text('Operational detail')
    ind_work_environment = fields.Text('Work environment')
    ind_analysis_reason = fields.Text('Reason for analysis')
    missing_data = fields.Boolean('Missing data')
    attributes = fields.Dict('lims.sample.attribute', 'Attributes',
        domain=[('id', 'in', Eval('attributes_domain'))],
        depends=['attributes_domain'])
    attributes_domain = fields.Function(fields.Many2Many(
        'lims.sample.attribute', None, None, 'Attributes domain'),
        'on_change_with_attributes_domain')
    sample_photo = fields.Binary('Sample Photo')
    label_photo = fields.Binary('Label Photo')

    @classmethod
    def __setup__(cls):
        super(CreateSampleStart, cls).__setup__()
        for field in ('component', 'comercial_product'):
            cls.analysis_domain.on_change_with.add(field)

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

    @fields.depends('product_type', 'component')
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
        attributes = (hasattr(self.start, 'attributes') and
            getattr(self.start, 'attributes') or None)
        sample_photo = (hasattr(self.start, 'sample_photo') and
            getattr(self.start, 'sample_photo') or None)
        label_photo = (hasattr(self.start, 'label_photo') and
            getattr(self.start, 'label_photo') or None)

        for sample_defaults in samples_defaults:
            sample_defaults['equipment'] = self.start.equipment.id
            sample_defaults['component'] = self.start.component.id
            sample_defaults['comercial_product'] = (
                self.start.comercial_product.id)
            sample_defaults['ind_sampling_date'] = self.start.ind_sampling_date
            sample_defaults['ind_volume'] = self.start.ind_volume
            sample_defaults['sampling_type'] = self.start.sampling_type.id
            sample_defaults['ind_operational_detail'] = ind_operational_detail
            sample_defaults['ind_work_environment'] = ind_work_environment
            sample_defaults['ind_analysis_reason'] = ind_analysis_reason
            sample_defaults['missing_data'] = missing_data
            sample_defaults['attributes'] = attributes
            sample_defaults['sample_photo'] = sample_photo
            sample_defaults['label_photo'] = label_photo

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


class Fraction(metaclass=PoolMeta):
    __name__ = 'lims.fraction'

    @classmethod
    def confirm(cls, fractions):
        super(Fraction, cls).confirm(fractions)
        for fraction in fractions:
            fraction.create_aliquots()
            fraction.plan_aliquots()

    def create_aliquots(self):
        pool = Pool()
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        Aliquot = pool.get('lims.aliquot')

        aliquot_types = []
        analysis_detail = EntryDetailAnalysis.search([
            ('fraction', '=', self.id)])
        for detail in analysis_detail:
            if detail.analysis.aliquot_type:
                aliquot_types.append(detail.analysis.aliquot_type.id)

        aliquots = []
        for type in list(set(aliquot_types)):
            aliquot = Aliquot()
            aliquot.fraction = self.id
            aliquot.type = type
            aliquots.append(aliquot)
        if aliquots:
            Aliquot.save(aliquots)

    def plan_aliquots(self):
        pool = Pool()
        Service = pool.get('lims.service')
        Aliquot = pool.get('lims.aliquot')
        Planification = pool.get('lims.planification')

        analysis_ids = []
        services = Service.search([('fraction', '=', self.id)])
        for service in services:
            analysis_ids.append(service.analysis.id)
        analysis = list(set(analysis_ids))

        aliquots = Aliquot.search([('fraction', '=', self.id)])
        for aliquot in aliquots:
            Planification.plan_aliquot(aliquot, analysis)


class Aliquot(ModelSQL, ModelView):
    'Aliquot'
    __name__ = 'lims.aliquot'
    _rec_name = 'number'

    number = fields.Char('Number', select=True, readonly=True)
    fraction = fields.Many2One('lims.fraction', 'Fraction', required=True,
        ondelete='CASCADE', select=True, depends=['number'],
        states={'readonly': Bool(Eval('number'))})
    type = fields.Many2One('lims.aliquot.type', 'Type', required=True)
    kind = fields.Function(fields.Selection([
        ('int', 'Internal'),
        ('ext', 'External'),
        ('rack', 'Rack'),
        ], 'Kind'), 'get_type_field')
    shipment_date = fields.Date('Shipment date',
        states={'invisible': Eval('kind') != 'ext'},
        depends=['kind'])
    laboratory = fields.Function(fields.Many2One('party.party',
        'Destination Laboratory',
        states={'invisible': Eval('kind') != 'ext'},
        depends=['kind']), 'get_type_field')
    preparation = fields.Function(fields.Boolean('Preparation',
        states={'invisible': Eval('kind') != 'int'},
        depends=['kind']), 'get_type_field')

    @classmethod
    def __setup__(cls):
        super(Aliquot, cls).__setup__()
        cls._order.insert(0, ('number', 'DESC'))

    @fields.depends('type')
    def on_change_with_kind(self, name=None):
        if self.type:
            result = self.get_type_field((self,), ('kind',))
            return result['kind'][self.id]
        return None

    @fields.depends('type')
    def on_change_with_laboratory(self, name=None):
        if self.type:
            result = self.get_type_field((self,), ('laboratory',))
            return result['laboratory'][self.id]
        return None

    @fields.depends('type')
    def on_change_with_preparation(self, name=None):
        if self.type:
            result = self.get_type_field((self,), ('preparation',))
            return result['preparation'][self.id]
        return None

    @classmethod
    def get_type_field(cls, aliquots, names):
        result = {}
        for name in names:
            result[name] = {}
            if name == 'laboratory':
                for a in aliquots:
                    field = getattr(a.type, name, None)
                    result[name][a.id] = field.id if field else None
            else:
                for a in aliquots:
                    result[name][a.id] = getattr(a.type, name, None)
        return result

    @classmethod
    def create(cls, vlist):
        pool = Pool()
        LabWorkYear = pool.get('lims.lab.workyear')
        Sequence = pool.get('ir.sequence')
        TaskTemplate = Pool().get('lims.administrative.task.template')

        workyear_id = LabWorkYear.find()
        workyear = LabWorkYear(workyear_id)
        sequence = workyear.get_sequence('aliquot')
        if not sequence:
            raise UserError(gettext('lims_industry.msg_aliquot_no_sequence',
                work_year=workyear.rec_name))

        vlist = [x.copy() for x in vlist]
        for values in vlist:
            values['number'] = Sequence.get_id(sequence.id)

        aliquots = super(Aliquot, cls).create(vlist)
        TaskTemplate.create_tasks('aliquot_preparation',
            cls._for_task_preparation(aliquots))
        return aliquots

    @classmethod
    def _for_task_preparation(cls, aliquots):
        AdministrativeTask = Pool().get('lims.administrative.task')
        res = []
        for aliquot in aliquots:
            if not aliquot.preparation:
                continue
            if AdministrativeTask.search([
                    ('type', '=', 'aliquot_preparation'),
                    ('origin', '=', '%s,%s' % (cls.__name__, aliquot.id)),
                    ('state', 'not in', ('done', 'discarded')),
                    ]):
                continue
            res.append(aliquot)
        return res
