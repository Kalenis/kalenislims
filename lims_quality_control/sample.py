# This file is part of lims_quality_control module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from datetime import datetime
from dateutil.relativedelta import relativedelta

from trytond.model import fields, ModelView
from trytond.wizard import Wizard, StateView, StateTransition, StateAction, \
    Button
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from trytond.pyson import PYSONEncoder, Bool, Not, Eval
from trytond.report import Report
from trytond.exceptions import UserError
from trytond.i18n import gettext


class LabWorkYear(metaclass=PoolMeta):
    __name__ = 'lims.lab.workyear'

    default_entry_quality = fields.Many2One('lims.entry',
        'Default entry quality')


class Sample(metaclass=PoolMeta):
    __name__ = 'lims.sample'

    quality = fields.Boolean('Quality')
    lot = fields.Many2One('stock.lot', 'Lot', readonly=True)
    test_state = fields.Selection([
        ('pending', 'Pending'),
        ('done', 'Done'),
        ('countersample', 'Countersample'),
        ], 'Test State', readonly=True)
    product = fields.Function(fields.Many2One('product.product',
        'Product'), 'on_change_with_product', searcher='search_product')
    quality_test = fields.Many2One('lims.quality.test', 'Test', readonly=True)
    countersample_original_sample = fields.Many2One('lims.sample',
        'Countersample Original sample', readonly=True,
        states={'invisible': Not(Bool(Eval('countersample_original_sample')))})
    countersamples = fields.One2Many('lims.sample',
        'countersample_original_sample', 'Countersamples', readonly=True)
    countersample = fields.Function(fields.Many2One('lims.sample',
        'Countersample'), 'get_countersample')

    @staticmethod
    def default_test_state():
        return 'pending'

    @fields.depends('lot')
    def on_change_with_product(self, name=None):
        if self.lot:
            return self.lot.product.id

    @classmethod
    def search_product(cls, name, clause):
        return [('lot.' + name,) + tuple(clause[1:])]

    @fields.depends('countersamples')
    def get_countersample(self, name):
        if self.countersamples:
            return self.countersamples[0].id


class TakeSampleStart(ModelView):
    'Take Sample Start'
    __name__ = 'lims.take.sample.start'

    date = fields.Date('Date', required=True)
    label = fields.Char('Label', required=True)
    attributes = fields.Dict('lims.sample.attribute', 'Attributes')

    @staticmethod
    def default_date():
        Date = Pool().get('ir.date')
        return Date.today()


class TakeSample(Wizard):
    'Take Sample'
    __name__ = 'lims.take.sample'

    start = StateView('lims.take.sample.start',
        'lims_quality_control.lims_take_sample_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Confirm', 'confirm', 'tryton-ok', default=True),
            ])
    confirm = StateTransition()

    def transition_confirm(self):
        self.create_sample()
        return 'end'

    def create_sample(self):
        pool = Pool()
        Config = pool.get('lims.configuration')
        QualityConfig = pool.get('lims.quality.configuration')
        Lot = pool.get('stock.lot')
        LabWorkYear = pool.get('lims.lab.workyear')
        Entry = pool.get('lims.entry')
        Sample = pool.get('lims.sample')
        Fraction = pool.get('lims.fraction')

        lot = Lot(Transaction().context.get('active_id'))
        if not lot.product.template.product_type:
            raise UserError(gettext('lims.msg_no_product_product_type'))
        if not lot.product.template.matrix:
            raise UserError(gettext('lims.msg_no_product_matrix'))

        config = Config(1)
        if not config.qc_fraction_type:
            raise UserError(gettext(
                'lims_quality_control.msg_no_qc_fraction_type'))
        fraction_type = config.qc_fraction_type
        if (not fraction_type.default_package_type or
                not fraction_type.default_fraction_state):
            raise UserError(gettext(
                'lims_quality_control.msg_no_qc_default_configuration'))

        quality_config = QualityConfig(1)

        workyear_id = LabWorkYear.find()
        workyear = LabWorkYear(workyear_id)
        if not workyear.default_entry_quality:
            raise UserError(gettext(
                'lims_quality_control.msg_no_entry_quality'))

        entry = Entry(workyear.default_entry_quality.id)
        if not entry.party.entry_zone and config.zone_required:
            raise UserError(gettext('lims.msg_no_party_zone',
                party=entry.party.rec_name))
        zone_id = entry.party.entry_zone and entry.party.entry_zone.id or None

        obj_description = self._get_obj_description(lot.product)

        # new sample
        new_sample, = Sample.create([{
            'quality': True,
            'lot': lot.id,
            'attributes': self.start.attributes,
            'entry': entry.id,
            'date': datetime.now(),
            'product_type': lot.product.template.product_type.id,
            'matrix': lot.product.template.matrix.id,
            'zone': zone_id,
            'label': self.start.label,
            'obj_description': obj_description,
            'packages_quantity': 1,
            'fractions': [],
            }])
        new_sample.label = '%s [%s]' % (new_sample.label, new_sample.number)
        new_sample.save()

        # new fraction
        fraction_default = {
            'sample': new_sample.id,
            'type': fraction_type.id,
            'storage_location': quality_config.sample_location.id,
            'packages_quantity': 1,
            'package_type': fraction_type.default_package_type.id,
            'fraction_state': fraction_type.default_fraction_state.id,
            'services': [],
            }
        if fraction_type.max_storage_time:
            fraction_default['storage_time'] = fraction_type.max_storage_time
        elif quality_config.sample_location.storage_time:
            fraction_default['storage_time'] = (
                quality_config.sample_location.storage_time)
        else:
            fraction_default['storage_time'] = 3
        new_fraction, = Fraction.create([fraction_default])

    def _get_obj_description(self, product):
        cursor = Transaction().connection.cursor()
        ObjectiveDescription = Pool().get('lims.objective_description')

        cursor.execute('SELECT id '
            'FROM "' + ObjectiveDescription._table + '" '
            'WHERE product_type = %s '
                'AND matrix = %s',
            (product.template.product_type.id, product.template.matrix.id))
        res = cursor.fetchone()
        return res and res[0] or None


class CountersampleCreateStart(ModelView):
    'Countersample Create Start'
    __name__ = 'lims.countersample.create.start'

    location = fields.Many2One('stock.location', 'Location', required=True)
    countersamples = fields.Many2Many(
        'lims.sample', None, None, 'Countersamples')


class CountersampleCreate(Wizard):
    'Countersample Create'
    __name__ = 'lims.countersample.create'

    start = StateTransition()
    ask = StateView('lims.countersample.create.start',
        'lims_quality_control.lims_countersample_create_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Create', 'create_', 'tryton-ok', default=True),
            ])
    create_ = StateTransition()
    open_ = StateAction('lims_quality_control.act_lims_sample_list')

    def transition_start(self):
        Sample = Pool().get('lims.sample')

        if not Transaction().context['active_ids']:
            raise UserError(gettext(
                    'lims_quality_control.msg_records_not_selected'))

        samples = Sample.browse(Transaction().context['active_ids'])
        for sample in samples:
            if sample.test_state != 'done':
                raise UserError(gettext(
                        'lims_quality_control.msg_not_test_sample'))
            if sample.countersample:
                raise UserError(gettext(
                        'lims_quality_control.msg_has_countersample'))
        return 'ask'

    def transition_create_(self):
        countersamples = self.create_countersample()
        self.ask.countersamples = [sample.id for sample in countersamples]
        return 'open_'

    def create_countersample(self):
        pool = Pool()
        Sample = pool.get('lims.sample')
        Fraction = pool.get('lims.fraction')
        Move = pool.get('stock.move')
        Date = pool.get('ir.date')

        samples = Sample.browse(Transaction().context.get('active_ids'))

        countersamples = []
        for sample in samples:

            # new countersample
            new_countersample, = Sample.create([{
                'quality': True,
                'lot': sample.lot.id,
                'attributes': sample.attributes,
                'entry': sample.entry.id,
                'date': datetime.now(),
                'product_type': sample.product_type.id,
                'matrix': sample.matrix.id,
                'zone': sample.zone and sample.zone.id or None,
                'label': sample.label,
                'obj_description': sample.obj_description,
                'packages_quantity': sample.packages_quantity,
                'countersample_original_sample': sample.id,
                'test_state': 'countersample',
                'fractions': [],
                }])

            # new fraction
            fraction_default = {
                'sample': new_countersample.id,
                'type': sample.fractions[0].type.id,
                'storage_location': self.ask.location.id,
                'packages_quantity': sample.packages_quantity,
                'package_type': sample.fractions[0].package_type.id,
                'fraction_state': sample.fractions[0].fraction_state.id,
                'storage_time': sample.fractions[0].storage_time,
                'countersample_location': self.ask.location.id,
                'countersample_date': Date.today(),
                'expiry_date': Date.today() + relativedelta(
                    months=sample.fractions[0].storage_time),
                'services': [],
                }
            new_fraction, = Fraction.create([fraction_default])

            moves = self._get_stock_moves([new_fraction])
            Move.do(moves)
            countersamples.append(new_countersample)

        return countersamples

    def do_open_(self, action):
        action['pyson_domain'] = PYSONEncoder().encode([
            ('id', 'in', [sample.id for sample in self.ask.countersamples]),
            ])
        action['views'].reverse()
        return action, {
            'res_id': [self.ask.countersamples[0].id],
            }

    def _get_stock_moves(self, fractions):
        pool = Pool()
        Config = pool.get('lims.configuration')
        User = pool.get('res.user')
        Move = pool.get('stock.move')

        config_ = Config(1)
        if config_.fraction_product:
            product = config_.fraction_product
        else:
            raise UserError(gettext('lims.msg_missing_fraction_product'))
        company = User(Transaction().user).company

        moves = []
        for fraction in fractions:
            with Transaction().set_user(0, set_context=True):
                move = Move()
            move.product = product.id
            move.fraction = fraction.id
            move.quantity = fraction.packages_quantity
            move.uom = product.default_uom
            move.from_location = \
                fraction.sample.countersample_original_sample.fractions[
                    0].storage_location.id
            move.to_location = fraction.countersample_location.id
            move.company = company
            move.planned_date = fraction.countersample_date
            move.origin = fraction
            move.state = 'draft'
            move.save()
            moves.append(move)
        return moves


class SampleLabels(Report):
    'Sample Labels'
    __name__ = 'lims.sample.labels.report'

    @classmethod
    def get_context(cls, records, data):
        report_context = super().get_context(records, data)
        labels = []
        for sample in records:
            for fraction in sample.fractions:
                for i in range(fraction.packages_quantity):
                    labels.append(fraction)
        report_context['labels'] = labels

        return report_context
