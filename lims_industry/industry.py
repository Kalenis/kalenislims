# This file is part of lims_industry module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelSQL, ModelView, fields
from trytond.pool import Pool
from trytond.pyson import Eval
from trytond.transaction import Transaction

__all__ = ['Plant', 'EquipmentType', 'Brand', 'ComponentType',
    'EquipmentTemplate', 'EquipmentTemplateComponentType', 'Equipment',
    'Component']


class Plant(ModelSQL, ModelView):
    'Plant'
    __name__ = 'lims.plant'

    party = fields.Many2One('party.party', 'Party', required=True,
        ondelete='CASCADE', select=True,
        states={'readonly': Eval('id', 0) > 0}, depends=['id'])
    name = fields.Char('Name', required=True)
    street = fields.Char('Street', required=True)
    zip = fields.Char('Zip', required=True)
    city = fields.Char('City', required=True)
    subdivision = fields.Many2One('country.subdivision',
        'Subdivision', required=True, domain=[
            ('country', '=', Eval('country', -1)),
            ('parent', '=', None),
            ],
        depends=['country'])
    country = fields.Many2One('country.country', 'Country',
        required=True)
    equipments = fields.One2Many('lims.equipment', 'plant',
        'Equipments')
    contacts = fields.One2Many('party.address', 'plant',
        'Contacts', domain=[('party', '=', Eval('party'))],
        depends=['party'])
    invoice_party = fields.Many2One('party.party', 'Invoice Party')
    latitude = fields.Numeric('Latitude', digits=(3, 14))
    longitude = fields.Numeric('Longitude', digits=(4, 14))

    @classmethod
    def __setup__(cls):
        super(Plant, cls).__setup__()
        cls._order.insert(0, ('party', 'ASC'))
        cls._order.insert(1, ('name', 'ASC'))

    @staticmethod
    def default_country():
        Company = Pool().get('company.company')
        company_id = Transaction().context.get('company')
        if company_id:
            address = Company(company_id).party.address_get()
            if address and address.country:
                return address.country.id


class EquipmentType(ModelSQL, ModelView):
    'Equipment Type'
    __name__ = 'lims.equipment.type'

    name = fields.Char('Name', required=True)


class Brand(ModelSQL, ModelView):
    'Brand'
    __name__ = 'lims.brand'

    name = fields.Char('Name', required=True)


class ComponentType(ModelSQL, ModelView):
    'Component Type'
    __name__ = 'lims.component.type'

    name = fields.Char('Name', required=True)


class EquipmentTemplate(ModelSQL, ModelView):
    'Equipment Template'
    __name__ = 'lims.equipment.template'

    type = fields.Many2One('lims.equipment.type', 'Type', required=True)
    brand = fields.Many2One('lims.brand', 'Brand', required=True)
    model = fields.Char('Model')
    power = fields.Char('Power')
    component_types = fields.Many2Many(
        'lims.equipment.template-component.type',
        'template', 'type', 'Component types')

    @classmethod
    def __setup__(cls):
        super(EquipmentTemplate, cls).__setup__()
        cls._order.insert(0, ('type', 'ASC'))
        cls._order.insert(1, ('brand', 'ASC'))
        cls._order.insert(2, ('model', 'ASC'))

    def get_rec_name(self, name):
        res = '%s - %s' % (self.type.rec_name, self.brand.rec_name)
        if self.model:
            res += ' - ' + self.model
        return res

    @classmethod
    def search_rec_name(cls, name, clause):
        return ['OR',
            ('type.name',) + tuple(clause[1:]),
            ('brand.name',) + tuple(clause[1:]),
            ('model',) + tuple(clause[1:]),
            ]


class EquipmentTemplateComponentType(ModelSQL):
    'Equipment Template - Component Type'
    __name__ = 'lims.equipment.template-component.type'
    _table = 'lims_equipment_template_component_type'

    template = fields.Many2One('lims.equipment.template', 'Template',
        required=True, ondelete='CASCADE', select=True)
    type = fields.Many2One('lims.component.type', 'Type',
        required=True, ondelete='CASCADE', select=True)


class Equipment(ModelSQL, ModelView):
    'Equipment'
    __name__ = 'lims.equipment'

    template = fields.Many2One('lims.equipment.template', 'Template',
        required=True)
    name = fields.Char('Name', required=True)
    model = fields.Char('Model', required=True)
    serial_number = fields.Char('Serial number')
    internal_id = fields.Char('Internal ID Code')
    latitude = fields.Numeric('Latitude', digits=(3, 14))
    longitude = fields.Numeric('Longitude', digits=(4, 14))
    plant = fields.Many2One('lims.plant', 'Plant',
        required=True, select=True)
    components = fields.One2Many('lims.component', 'equipment',
        'Components')
    year_manufacturing = fields.Integer('Year of manufacturing')
    internal_location = fields.Char('Internal location')
    contacts = fields.One2Many('party.address', 'equipment',
        'Contacts', domain=[('party', '=', Eval('party'))],
        context={'plant': Eval('plant')},
        depends=['party', 'plant'])
    party = fields.Function(fields.Many2One('party.party', 'Party'),
        'get_party', searcher='search_party')
    missing_data = fields.Boolean('Missing data')

    @classmethod
    def __setup__(cls):
        super(Equipment, cls).__setup__()
        cls._order.insert(0, ('template', 'ASC'))
        cls._order.insert(1, ('name', 'ASC'))

    def get_party(self, name):
        if self.plant:
            return self.plant.party.id

    @classmethod
    def search_party(cls, name, clause):
        return [('plant.party',) + tuple(clause[1:])]

    @fields.depends('template')
    def on_change_template(self):
        pool = Pool()
        Component = pool.get('lims.component')

        model = None
        components = []
        if self.template:
            model = self.template.model
            for type in self.template.component_types:
                value = Component(**Component.default_get(
                    list(Component._fields.keys())))
                value.type = type.id
                components.append(value)
        self.model = model
        self.components = components


class Component(ModelSQL, ModelView):
    'Component'
    __name__ = 'lims.component'

    equipment = fields.Many2One('lims.equipment', 'Equipment',
        required=True, ondelete='CASCADE', select=True,)
    type = fields.Many2One('lims.component.type', 'Type',
        required=True)
    capacity = fields.Char('Capacity (lts)')
    serial_number = fields.Char('Serial number')
    model = fields.Char('Model')
    power = fields.Char('Power')
    brand = fields.Many2One('lims.brand', 'Brand')
    internal_id = fields.Char('Internal ID Code')
    customer_description = fields.Char('Customer description')
    year_manufacturing = fields.Integer('Year of manufacturing')
    party = fields.Function(fields.Many2One('party.party', 'Party'),
        'get_party', searcher='search_party')

    @classmethod
    def __setup__(cls):
        super(Component, cls).__setup__()
        cls._order.insert(0, ('equipment', 'ASC'))
        cls._order.insert(1, ('type', 'ASC'))

    def get_rec_name(self, name):
        res = self.type.rec_name
        if self.brand:
            res += ' - ' + self.brand.rec_name
        if self.model:
            res += ' - ' + self.model
        return res

    def get_party(self, name):
        if self.equipment:
            return self.equipment.plant.party.id

    @classmethod
    def search_party(cls, name, clause):
        return [('equipment.plant.party',) + tuple(clause[1:])]
