# This file is part of lims_analysis_sheet_stock module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.model import ModelView, ModelSQL, fields, Unique
from trytond.wizard import Wizard, StateTransition, StateView, Button
from trytond.pyson import Eval, Id
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.i18n import gettext


class TemplateAnalysisSheet(metaclass=PoolMeta):
    __name__ = 'lims.template.analysis_sheet'

    materials = fields.One2Many('lims.template.analysis_sheet.material',
        'template', 'Materials')


class TemplateAnalysisSheetMaterial(ModelSQL, ModelView):
    'Template Material'
    __name__ = 'lims.template.analysis_sheet.material'

    template = fields.Many2One('lims.template.analysis_sheet', 'Template',
        required=True, ondelete='CASCADE', select=True)
    product = fields.Many2One('product.product', 'Product',
        required=True, domain=[
            ('type', '!=', 'service'),
        ])
    uom_category = fields.Function(fields.Many2One(
        'product.uom.category', 'Uom Category'), 'on_change_with_uom_category')
    uom = fields.Many2One('product.uom', 'Uom', required=True,
        domain=[
            ('category', '=', Eval('uom_category')),
        ], depends=['uom_category'])
    unit_digits = fields.Function(fields.Integer('Unit Digits'),
        'on_change_with_unit_digits')
    quantity = fields.Float('Quantity', required=True,
        domain=['OR',
            ('quantity', '>=', 0),
            ('quantity', '=', None),
            ],
        digits=(16, Eval('unit_digits', 2)),
        depends=['unit_digits'])
    quantity_by_sample = fields.Boolean('Quantity by Sample')
    interface = fields.Function(fields.Many2One(
        'lims.interface', 'Device Interface'), 'get_interface')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        t = cls.__table__()
        cls._sql_constraints = [
            ('product_template_uniq', Unique(t, t.product, t.template),
                'lims_analysis_sheet_stock.msg_product_template_unique'),
            ]

    @fields.depends('product', 'uom')
    def on_change_product(self):
        if self.product:
            category = self.product.default_uom.category
            if not self.uom or self.uom.category != category:
                self.uom = self.product.default_uom
                self.unit_digits = self.product.default_uom.digits
        else:
            self.uom = None

    @fields.depends('product')
    def on_change_with_uom_category(self, name=None):
        if self.product:
            return self.product.default_uom.category.id

    @fields.depends('uom')
    def on_change_with_unit_digits(self, name=None):
        if self.uom:
            return self.uom.digits
        return 2

    def get_rec_name(self, name):
        return self.product.rec_name

    @classmethod
    def search_rec_name(cls, name, clause):
        return [('product.rec_name',) + tuple(clause[1:])]

    def compute_quantity(self, factor):
        return self.uom.ceil(self.quantity * factor)

    def get_interface(self, name):
        return self.template.interface.id


class AnalysisSheet(metaclass=PoolMeta):
    __name__ = 'lims.analysis_sheet'

    moves = fields.One2Many('stock.move', 'origin', 'Moves', readonly=True)

    @classmethod
    @ModelView.button
    def validate_(cls, sheets):
        super().validate_(sheets)
        cls.check_materials(sheets)

    @classmethod
    def check_materials(cls, sheets):
        for s in sheets:
            if s.template.materials and not s.moves:
                raise UserError(gettext(
                    'lims_analysis_sheet_stock.msg_sheet_not_materials'))


class AddMaterialStart(ModelView):
    'Add Material'
    __name__ = 'lims.analysis_sheet.add_material.start'

    materials = fields.One2Many(
        'lims.analysis_sheet.add_material_detail.start',
        'material', 'Materials')


class AddMaterialDetailStart(ModelView):
    'Add Material'
    __name__ = 'lims.analysis_sheet.add_material_detail.start'

    material = fields.Many2One('lims.analysis_sheet.add_material.start',
        'Material')
    product = fields.Many2One('product.product', 'Product',
        required=True, domain=[
            ('type', '!=', 'service'),
        ])
    lot = fields.Many2One('stock.lot', 'Lot',
        domain=[
            ('product', '=', Eval('product')),
            ],
        depends=['product'])
    from_location = fields.Many2One('stock.location', 'From Location',
        domain=[('type', '=', 'storage')])
    uom = fields.Many2One('product.uom', 'Uom', required=True,
        domain=[
            ('category', '=', Eval('uom_category')),
        ], depends=['uom_category'])
    unit_digits = fields.Function(fields.Integer('Unit Digits'),
        'on_change_with_unit_digits')
    quantity = fields.Float('Quantity', required=True,
        domain=['OR',
            ('quantity', '>=', 0),
            ('quantity', '=', None),
            ],
        digits=(16, Eval('unit_digits', 2)),
        depends=['unit_digits'])

    @fields.depends('product', 'uom')
    def on_change_product(self):
        if self.product:
            category = self.product.default_uom.category
            if not self.uom or self.uom.category != category:
                self.uom = self.product.default_uom
                self.unit_digits = self.product.default_uom.digits
        else:
            self.uom = None

    @fields.depends('product')
    def on_change_with_uom_category(self, name=None):
        if self.product:
            return self.product.default_uom.category.id

    @fields.depends('uom')
    def on_change_with_unit_digits(self, name=None):
        if self.uom:
            return self.uom.digits
        return 2


class AddMaterialAssignFailed(ModelView):
    'Add Material Assign Failed'
    __name__ = 'lims.analysis_sheet.add_material.assign.failed'

    inventory_moves = fields.Many2Many('stock.move', None, None,
        'Inventory Moves', readonly=True)

    @staticmethod
    def default_inventory_moves():
        AnalysisSheet = Pool().get('lims.analysis_sheet')

        sheet = None
        line_id = Transaction().context.get('active_id', None)
        sheet_id = Transaction().context.get('lims_analysis_sheet', None)
        if line_id and sheet_id:
            sheet = AnalysisSheet(sheet_id)
        if not sheet:
            return []
        return [x.id for x in sheet.moves if x.state == 'draft']


class AddMaterial(Wizard):
    'Add Material'
    __name__ = 'lims.analysis_sheet.add_material'

    start_state = 'check'
    check = StateTransition()
    start = StateView('lims.analysis_sheet.add_material.start',
        'lims_analysis_sheet_stock.add_material_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Save', 'save', 'tryton-save', default=True),
            ])
    save = StateTransition()
    failed = StateView('lims.analysis_sheet.add_material.assign.failed',
        'lims_analysis_sheet_stock.add_material_assign_failed_view_form', [
            Button('Force Assign', 'force', 'tryton-forward',
                states={
                    'invisible': ~Id('stock',
                        'group_stock_force_assignment').in_(
                        Eval('context', {}).get('groups', [])),
                    }),
            Button('OK', 'delete_moves', 'tryton-ok', True),
            ])
    force = StateTransition()
    delete_moves = StateTransition()

    def _get_analysis_sheet_id(self):
        return Transaction().context.get('lims_analysis_sheet', None)

    def transition_check(self):
        AnalysisSheet = Pool().get('lims.analysis_sheet')

        line_id = Transaction().context.get('active_id', None)
        sheet_id = self._get_analysis_sheet_id()
        if line_id and sheet_id:
            sheet = AnalysisSheet(sheet_id)
            if sheet.state == 'active':
                return 'start'

        return 'end'

    def default_start(self, fields):
        pool = Pool()
        AnalysisSheet = pool.get('lims.analysis_sheet')

        sheet_id = self._get_analysis_sheet_id()
        sheet = AnalysisSheet(sheet_id)

        moves = []
        for material in sheet.template.materials:
            move = {
                'product': material.product.id,
                'uom': material.uom.id,
                'quantity': material.quantity,
                }

            moves.append(move)

        defaults = {
            'materials': moves,
            }
        return defaults

    def _move(self, origin, from_location, to_location, product, uom, quantity,
            lot):
        Move = Pool().get('stock.move')
        move = Move(
            origin=origin,
            product=product,
            lot=lot,
            uom=uom,
            quantity=quantity,
            from_location=from_location,
            to_location=to_location,
            state='draft',
            )
        return move

    def get_moves(self):
        pool = Pool()
        AnalysisSheet = pool.get('lims.analysis_sheet')
        Move = pool.get('stock.move')
        Config = Pool().get('lims.configuration')

        config = Config(1)
        sheet_id = self._get_analysis_sheet_id()
        sheet = AnalysisSheet(sheet_id)

        moves = []
        for material in self.start.materials:
            move = self._move(sheet, material.from_location,
                config.materials_consumption_location, material.product,
                material.uom, material.quantity, material.lot)
            moves.append(move)

        Move.save(moves)
        return moves

    def transition_save(self):
        pool = Pool()
        Move = pool.get('stock.move')

        moves = self.get_moves()

        if not Move.assign_try(moves):
            return 'failed'
        Move.do(moves)

        return 'end'

    def transition_force(self):
        pool = Pool()
        AnalysisSheet = pool.get('lims.analysis_sheet')
        Move = pool.get('stock.move')

        sheet = None
        line_id = Transaction().context.get('active_id', None)
        sheet_id = Transaction().context.get('lims_analysis_sheet', None)
        if line_id and sheet_id:
            sheet = AnalysisSheet(sheet_id)
        Move.do([m for m in sheet.moves])

        return 'end'

    def transition_delete_moves(self):
        pool = Pool()
        AnalysisSheet = pool.get('lims.analysis_sheet')
        Move = pool.get('stock.move')

        sheet = None
        line_id = Transaction().context.get('active_id', None)
        sheet_id = Transaction().context.get('lims_analysis_sheet', None)
        if line_id and sheet_id:
            sheet = AnalysisSheet(sheet_id)

        Move.delete([m for m in sheet.moves])

        return 'end'
