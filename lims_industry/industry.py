# This file is part of lims_industry module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelSQL, ModelView, DeactivableMixin, fields, \
    Unique, Index
from trytond.pool import Pool
from trytond.pyson import Eval, If
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.i18n import gettext
from trytond import backend


class Plant(ModelSQL, ModelView):
    'Plant'
    __name__ = 'lims.plant'

    party = fields.Many2One('party.party', 'Party', required=True,
        ondelete='CASCADE')
    name = fields.Char('Name', required=True)
    street = fields.Char('Street', required=True)
    postal_code = fields.Char('Postal Code', required=True)
    city = fields.Char('City', required=True)
    subdivision = fields.Many2One('country.subdivision',
        'Subdivision', required=True, domain=[
            ('country', '=', Eval('country', -1)),
            ('parent', '=', None),
            ])
    country = fields.Many2One('country.country', 'Country',
        required=True)
    equipments = fields.One2Many('lims.equipment', 'plant',
        'Equipments')
    contacts = fields.One2Many('party.address', 'plant',
        'Contacts', domain=[('party', '=', Eval('party'))])
    invoice_party = fields.Many2One('party.party', 'Invoice Party')
    latitude = fields.Numeric('Latitude', digits=(3, 14))
    longitude = fields.Numeric('Longitude', digits=(4, 14))

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order.insert(0, ('party', 'ASC'))
        cls._order.insert(1, ('name', 'ASC'))
        t = cls.__table__()
        cls._sql_constraints = [
            ('name_unique', Unique(t, t.party, t.name),
                'lims_industry.msg_plant_name_unique'),
            ]

    @classmethod
    def __register__(cls, module_name):
        table = cls.__table_handler__(module_name)
        table.column_rename('zip', 'postal_code')
        super().__register__(module_name)

    @staticmethod
    def default_country():
        Company = Pool().get('company.company')
        company_id = Transaction().context.get('company')
        if company_id:
            address = Company(company_id).party.address_get()
            if address and address.country:
                return address.country.id

    def get_rec_name(self, name):
        res = '%s [%s]' % (self.name, self.party.name)
        return res

    @classmethod
    def copy(cls, records, default=None):
        if default is None:
            default = {}
        current_default = default.copy()
        current_default['equipments'] = None

        new_records = []
        for record in records:
            current_default['name'] = '%s (copy)' % record.name
            new_record, = super().copy([record], default=current_default)
            new_records.append(new_record)
        return new_records


class EquipmentType(ModelSQL, ModelView):
    'Equipment Type'
    __name__ = 'lims.equipment.type'

    name = fields.Char('Name', required=True)

    @classmethod
    def __setup__(cls):
        super().__setup__()
        t = cls.__table__()
        cls._sql_constraints = [
            ('name_unique', Unique(t, t.name),
                'lims_industry.msg_equipment_type_name_unique'),
            ]

    @classmethod
    def copy(cls, records, default=None):
        if default is None:
            default = {}
        current_default = default.copy()

        new_records = []
        for record in records:
            current_default['name'] = '%s (copy)' % record.name
            new_record, = super().copy([record], default=current_default)
            new_records.append(new_record)
        return new_records


class Brand(ModelSQL, ModelView):
    'Brand'
    __name__ = 'lims.brand'

    name = fields.Char('Name', required=True)

    @classmethod
    def __setup__(cls):
        super().__setup__()
        t = cls.__table__()
        cls._sql_constraints = [
            ('name_unique', Unique(t, t.name),
                'lims_industry.msg_brand_name_unique'),
            ]

    @classmethod
    def copy(cls, records, default=None):
        if default is None:
            default = {}
        current_default = default.copy()

        new_records = []
        for record in records:
            current_default['name'] = '%s (copy)' % record.name
            new_record, = super().copy([record], default=current_default)
            new_records.append(new_record)
        return new_records


class ComponentKind(ModelSQL, ModelView):
    'Component Kind'
    __name__ = 'lims.component.kind'

    name = fields.Char('Name', required=True)
    product_type = fields.Many2One('lims.product.type', 'Product type',
        required=True)

    @classmethod
    def __setup__(cls):
        super().__setup__()
        t = cls.__table__()
        cls._sql_constraints = [
            ('name_unique', Unique(t, t.name),
                'lims_industry.msg_component_kind_name_unique'),
            ]

    @classmethod
    def copy(cls, records, default=None):
        if default is None:
            default = {}
        current_default = default.copy()

        new_records = []
        for record in records:
            current_default['name'] = '%s (copy)' % record.name
            new_record, = super().copy([record], default=current_default)
            new_records.append(new_record)
        return new_records


class ComponentLocation(ModelSQL, ModelView):
    'Component Location'
    __name__ = 'lims.component.location'

    name = fields.Char('Name', required=True)


class ComponentType(ModelSQL, ModelView):
    'Component Type'
    __name__ = 'lims.component.type'

    name = fields.Char('Name', required=True)
    product_type = fields.Many2One('lims.product.type', 'Product type',
        required=True)
    kind = fields.Many2One('lims.component.kind', 'Kind')
    location = fields.Many2One('lims.component.location', 'Location')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        t = cls.__table__()
        cls._sql_constraints = [
            ('name_unique', Unique(t, t.name),
                'lims_industry.msg_component_type_name_unique'),
            ]

    @classmethod
    def copy(cls, records, default=None):
        if default is None:
            default = {}
        current_default = default.copy()

        new_records = []
        for record in records:
            current_default['name'] = '%s (copy)' % record.name
            new_record, = super().copy([record], default=current_default)
            new_records.append(new_record)
        return new_records


class EquipmentTemplate(ModelSQL, ModelView):
    'Equipment Template'
    __name__ = 'lims.equipment.template'

    type = fields.Many2One('lims.equipment.type', 'Type', required=True)
    brand = fields.Many2One('lims.brand', 'Brand', required=True)
    model = fields.Char('Model')
    power = fields.Char('Power')
    component_kinds = fields.One2Many(
        'lims.equipment.template-component.kind',
        'template', 'Component kinds')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order.insert(0, ('type', 'ASC'))
        cls._order.insert(1, ('brand', 'ASC'))
        cls._order.insert(2, ('model', 'ASC'))
        t = cls.__table__()
        cls._sql_constraints = [
            ('type_brand_model_unique', Unique(t, t.type, t.brand, t.model),
                'lims_industry.msg_equipment_template_unique'),
            ]

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

    @classmethod
    def copy(cls, records, default=None):
        if default is None:
            default = {}
        current_default = default.copy()

        new_records = []
        for record in records:
            current_default['model'] = '%s (copy)' % record.model
            new_record, = super().copy([record], default=current_default)
            new_records.append(new_record)
        return new_records


class EquipmentTemplateComponentKind(ModelSQL, ModelView):
    'Equipment Template - Component Kind'
    __name__ = 'lims.equipment.template-component.kind'
    _table = 'lims_equipment_template_component_kind'

    template = fields.Many2One('lims.equipment.template', 'Template',
        required=True, ondelete='CASCADE')
    kind = fields.Many2One('lims.component.kind', 'Kind',
        required=True, ondelete='CASCADE')
    location = fields.Many2One('lims.component.location', 'Location')

    @classmethod
    def __register__(cls, module_name):
        cursor = Transaction().connection.cursor()
        TableHandler = backend.TableHandler
        sql_table = cls.__table__()
        super().__register__(module_name)
        old_table_name = 'lims_equipment_template_component_type'
        if TableHandler.table_exist(old_table_name):
            cursor.execute('SELECT etct.template, ct.kind, ct.location '
                'FROM lims_equipment_template_component_type etct '
                'INNER JOIN lims_component_type ct '
                    'ON ct.id = etct.type '
                'WHERE ct.kind IS NOT NULL')
            res = cursor.fetchall()
            if res:
                cursor.execute(*sql_table.insert(
                    columns=[sql_table.template, sql_table.kind,
                        sql_table.location],
                    values=[[x[0], x[1], x[2]] for x in res]))
            TableHandler.drop_table('', old_table_name)


class Equipment(DeactivableMixin, ModelSQL, ModelView):
    'Equipment'
    __name__ = 'lims.equipment'

    template = fields.Many2One('lims.equipment.template', 'Template',
        required=True)
    name = fields.Char('Name', required=True)
    type = fields.Function(fields.Many2One('lims.equipment.type', 'Type'),
        'get_type', searcher='search_type')
    brand = fields.Function(fields.Many2One('lims.brand', 'Brand'),
        'get_brand', searcher='search_brand')
    model = fields.Char('Model', required=True)
    power = fields.Char('Power')
    voltage = fields.Char('Primary Voltage')
    voltage_secondary = fields.Char('Secondary Voltage')
    voltage_tertiary = fields.Char('Tertiary Voltage')
    amperage = fields.Char('Secondary Amperage')
    serial_number = fields.Char('Serial number')
    internal_id = fields.Char('Internal ID Code')
    latitude = fields.Numeric('Latitude', digits=(3, 14))
    longitude = fields.Numeric('Longitude', digits=(4, 14))
    plant = fields.Many2One('lims.plant', 'Plant', required=True,
        domain=[If(Eval('context', {}).contains('party'),
            ('party', '=', Eval('context', {}).get('party', -1)),
            ())])
    components = fields.One2Many('lims.component', 'equipment',
        'Components')
    year_manufacturing = fields.Integer('Year of manufacturing')
    year_service_start = fields.Integer('Year of service start')
    internal_location = fields.Char('Internal location')
    contacts = fields.One2Many('party.address', 'equipment',
        'Contacts', domain=[('party', '=', Eval('party'))],
        context={'plant': Eval('plant')}, depends={'plant'})
    party = fields.Function(fields.Many2One('party.party', 'Party'),
        'get_party', searcher='search_party')
    missing_data = fields.Boolean('Missing data')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order.insert(0, ('template', 'ASC'))
        cls._order.insert(1, ('name', 'ASC'))
        t = cls.__table__()
        cls._sql_constraints = [
            ('name_unique', Unique(t, t.plant, t.name),
                'lims_industry.msg_equipment_name_unique'),
            ]
        #cls._sql_indexes.update({
            #Index(t, (t.plant, Index.Equality())),
            #})

    @classmethod
    def create(cls, vlist):
        TaskTemplate = Pool().get('lims.administrative.task.template')
        equipments = super().create(vlist)
        TaskTemplate.create_tasks('equipment_missing_data',
            cls._for_task_missing_data(equipments))
        return equipments

    @classmethod
    def _for_task_missing_data(cls, equipments):
        AdministrativeTask = Pool().get('lims.administrative.task')
        res = []
        for equipment in equipments:
            if not equipment.missing_data:
                continue
            if AdministrativeTask.search([
                    ('type', '=', 'equipment_missing_data'),
                    ('origin', '=', '%s,%s' % (cls.__name__, equipment.id)),
                    ('state', 'not in', ('done', 'discarded')),
                    ]):
                continue
            res.append(equipment)
        return res

    def get_rec_name(self, name):
        res = '%s [%s]' % (self.name, self.plant.name)
        return res

    @classmethod
    def search_rec_name(cls, name, clause):
        return ['OR',
            ('name',) + tuple(clause[1:]),
            ('serial_number',) + tuple(clause[1:]),
            ('brand.name',) + tuple(clause[1:]),
            ('plant.name',) + tuple(clause[1:]),
            ('components.customer_description',) + tuple(clause[1:]),
            ]

    @fields.depends('plant', '_parent_plant.party')
    def on_change_with_party(self, name=None):
        return self.get_party([self], name)[self.id]

    @classmethod
    def get_party(cls, equipments, name):
        result = {}
        for e in equipments:
            result[e.id] = e.plant and e.plant.party or None
        return result

    @classmethod
    def search_party(cls, name, clause):
        return [('plant.party',) + tuple(clause[1:])]

    @fields.depends('template', '_parent_template.type')
    def on_change_with_type(self, name=None):
        return self.get_type([self], name)[self.id]

    @classmethod
    def get_type(cls, equipments, name):
        result = {}
        for e in equipments:
            result[e.id] = e.template and e.template.type or None
        return result

    @classmethod
    def search_type(cls, name, clause):
        return [('template.type',) + tuple(clause[1:])]

    @fields.depends('template', '_parent_template.brand')
    def on_change_with_brand(self, name=None):
        return self.get_brand([self], name)[self.id]

    @classmethod
    def get_brand(cls, equipments, name):
        result = {}
        for e in equipments:
            result[e.id] = e.template and e.template.brand or None
        return result

    @classmethod
    def search_brand(cls, name, clause):
        return [('template.brand',) + tuple(clause[1:])]

    @fields.depends('template', 'components')
    def on_change_template(self):
        pool = Pool()
        Component = pool.get('lims.component')

        if not self.template:
            return
        current_components_ids = [(component.kind.id,
            component.location and component.location.id or None)
            for component in self.components]
        components = list(self.components)
        for record in self.template.component_kinds:
            kind_id = record.kind.id
            location_id = record.location and record.location.id or None
            if (kind_id, location_id) in current_components_ids:
                continue
            value = Component(**Component.default_get(
                list(Component._fields.keys()), with_rec_name=False))
            value.kind = kind_id
            value.location = location_id
            components.append(value)
        self.model = self.template.model
        self.power = self.template.power
        self.components = components

    @classmethod
    def copy(cls, records, default=None):
        if default is None:
            default = {}
        current_default = default.copy()

        new_records = []
        for record in records:
            current_default['name'] = '%s (copy)' % record.name
            new_record, = super().copy([record], default=current_default)
            new_records.append(new_record)
        return new_records


class Component(ModelSQL, ModelView):
    'Component'
    __name__ = 'lims.component'

    equipment = fields.Many2One('lims.equipment', 'Equipment',
        required=True, ondelete='CASCADE')
    kind = fields.Many2One('lims.component.kind', 'Kind', required=True)
    location = fields.Many2One('lims.component.location', 'Location')
    product_type = fields.Function(fields.Many2One('lims.product.type',
        'Product type'), 'get_product_type')
    comercial_product = fields.Many2One('lims.comercial.product',
        'Comercial product')
    capacity = fields.Char('Capacity (lts)')
    serial_number = fields.Char('Serial number')
    model = fields.Char('Model')
    power = fields.Char('Power')
    brand = fields.Many2One('lims.brand', 'Brand')
    internal_id = fields.Char('Internal ID Code')
    customer_description = fields.Char('Customer description')
    year_manufacturing = fields.Integer('Year of manufacturing')
    plant = fields.Function(fields.Many2One('lims.plant', 'Plant'),
        'get_plant', searcher='search_plant')
    party = fields.Function(fields.Many2One('party.party', 'Party'),
        'get_party', searcher='search_party')
    missing_data = fields.Boolean('Missing data')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order.insert(0, ('equipment', 'ASC'))
        cls._order.insert(1, ('kind', 'ASC'))
        t = cls.__table__()
        cls._sql_constraints = [
            ('kind_location_description_unique', Unique(t, t.equipment,
                    t.kind, t.location, t.customer_description),
                'lims_industry.msg_component_unique'),
            ]

    @classmethod
    def __register__(cls, module_name):
        table_h = cls.__table_handler__(module_name)
        type_exist = table_h.column_exist('type')
        super().__register__(module_name)
        if type_exist:
            cursor = Transaction().connection.cursor()
            ComponentType = Pool().get('lims.component.type')
            cursor.execute('UPDATE "' + cls._table + '" c '
                'SET kind = ct.kind, location = ct.location '
                'FROM "' + ComponentType._table + '" ct '
                'WHERE ct.id = c.type')
            table_h.drop_constraint('type_unique')
            table_h.drop_constraint('type_description_unique')
            table_h.drop_column('type')

    @classmethod
    def create(cls, vlist):
        TaskTemplate = Pool().get('lims.administrative.task.template')
        components = super().create(vlist)
        TaskTemplate.create_tasks('component_missing_data',
            cls._for_task_missing_data(components))
        return components

    @classmethod
    def _for_task_missing_data(cls, components):
        AdministrativeTask = Pool().get('lims.administrative.task')
        res = []
        for component in components:
            if not component.missing_data:
                continue
            if AdministrativeTask.search([
                    ('type', '=', 'component_missing_data'),
                    ('origin', '=', '%s,%s' % (cls.__name__, component.id)),
                    ('state', 'not in', ('done', 'discarded')),
                    ]):
                continue
            res.append(component)
        return res

    @classmethod
    def delete(cls, components):
        cls.check_delete(components)
        super().delete(components)

    @classmethod
    def check_delete(cls, components):
        Sample = Pool().get('lims.sample')
        for component in components:
            samples = Sample.search_count([
                ('component', '=', component.id),
                ])
            if samples != 0:
                raise UserError(gettext('lims_industry.msg_delete_component',
                    component=component.get_rec_name(None)))

    @classmethod
    def copy(cls, records, default=None):
        if default is None:
            default = {}
        current_default = default.copy()

        new_records = []
        for record in records:
            current_default['customer_description'] = '%s (copy)' % (
                record.customer_description)
            new_record, = super().copy([record], default=current_default)
            new_records.append(new_record)
        return new_records

    def get_rec_name(self, name):
        res = self.kind.rec_name
        if self.location:
            res += ' ' + self.location.name
        if self.brand:
            res += ' - ' + self.brand.rec_name
        if self.model:
            res += ' - ' + self.model
        if self.customer_description:
            res += ' [' + self.customer_description + ']'
        return res

    @classmethod
    def search_rec_name(cls, name, clause):
        return ['OR',
            ('kind.name',) + tuple(clause[1:]),
            ('location.name',) + tuple(clause[1:]),
            ('brand.name',) + tuple(clause[1:]),
            ('model',) + tuple(clause[1:]),
            ('customer_description',) + tuple(clause[1:]),
            ]

    @classmethod
    def get_plant(cls, component, name):
        result = {}
        for c in component:
            result[c.id] = c.equipment and c.equipment.plant.id or None
        return result

    @classmethod
    def search_plant(cls, name, clause):
        return [('equipment.plant',) + tuple(clause[1:])]

    @classmethod
    def get_party(cls, component, name):
        result = {}
        for c in component:
            result[c.id] = c.equipment and c.equipment.plant.party.id or None
        return result

    @classmethod
    def search_party(cls, name, clause):
        return [('equipment.plant.party',) + tuple(clause[1:])]

    @fields.depends('kind', '_parent_kind.product_type')
    def on_change_with_product_type(self, name=None):
        return self.get_product_type([self], name)[self.id]

    @classmethod
    def get_product_type(cls, components, name):
        result = {}
        for c in components:
            result[c.id] = c.kind and c.kind.product_type or None
        return result


class ComercialProductBrand(ModelSQL, ModelView):
    'Comercial Product Brand'
    __name__ = 'lims.comercial.product.brand'

    name = fields.Char('Name', required=True)


class ComercialProduct(ModelSQL, ModelView):
    'Comercial Product'
    __name__ = 'lims.comercial.product'

    name = fields.Char('Name', required=True)
    brand = fields.Many2One('lims.comercial.product.brand', 'Brand',
        required=True)
    matrix = fields.Many2One('lims.matrix', 'Base/Matrix', required=True)
    dangerous = fields.Boolean('Dangerous')

    @staticmethod
    def default_dangerous():
        return False

    def get_rec_name(self, name):
        res = '%s %s' % (self.brand.name, self.name)
        return res

    @classmethod
    def search_rec_name(cls, name, clause):
        return ['OR',
            ('name',) + tuple(clause[1:]),
            ('brand.name',) + tuple(clause[1:]),
            ]
