# This file is part of lims_industry module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelSQL, ModelView, fields, Unique
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Not, Bool, Equal, Eval
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.i18n import gettext

__all__ = ['Rack', 'RackPosition']


class Rack(metaclass=PoolMeta):
    __name__ = 'lims.planification'

    type = fields.Selection([
        ('normal', 'Normal'),
        ('rack', 'Rack'),
        ], 'Type', required=True, sort=False)
    rack_number = fields.Char('Rack number', readonly=True)
    aliquot_type = fields.Many2One('lims.aliquot.type', 'Rack type',
        states={'required': Eval('type') == 'rack'},
        domain=[('kind', '=', 'rack')],
        depends=['type'])
    rack_state = fields.Selection([
        (None, ''),
        ('open', 'Open'),
        ('closed', 'Closed'),
        ], 'Rack state', sort=False,
        states={'required': Eval('type') == 'rack'},
        depends=['type'])
    rack_user = fields.Many2One('res.user', 'Rack user',
        states={'required': Eval('type') == 'rack'},
        depends=['type'])
    positions = fields.One2Many('lims.planification.position',
        'planification', 'Positions',
        states={'readonly': Not(Bool(Equal(Eval('state'), 'draft')))},
        depends=['state'])

    @classmethod
    def __setup__(cls):
        super(Rack, cls).__setup__()
        cls.details.context.update({'planification_type': Eval('type')})

    @staticmethod
    def default_type():
        return 'normal'

    @staticmethod
    def default_rack_user():
        return int(Transaction().user)

    @classmethod
    def create(cls, vlist):
        pool = Pool()
        Config = pool.get('lims.configuration')
        Sequence = pool.get('ir.sequence')
        AliquotType = pool.get('lims.aliquot.type')

        vlist = [x.copy() for x in vlist]
        config = Config(1)
        for values in vlist:
            if values['type'] != 'rack':
                continue
            number = '%s' % values['date'].strftime("%Y%m%d")
            number += '-%s' % AliquotType(values['aliquot_type']).code
            number += '-%s' % Sequence.get_id(config.rack_sequence.id)
            values['rack_number'] = number
        return super(Rack, cls).create(vlist)

    @classmethod
    def plan_aliquot(cls, aliquot, analysis):
        pool = Pool()
        PlanificationPosition = pool.get('lims.planification.position')
        PlanificationDetail = pool.get('lims.planification.detail')
        Date = pool.get('ir.date')

        if aliquot.type.kind != 'rack':
            return

        laboratory = Transaction().context.get('laboratory', None)
        if not laboratory:
            raise UserError(gettext('lims_industry.msg_user_no_laboratory'))

        # Rack
        create_new_rack = True
        position = 1
        open_racks = cls.search([
            ('type', '=', 'rack'),
            ('laboratory', '=', laboratory),
            ('rack_user', '=', int(Transaction().user)),
            ('aliquot_type', '=', aliquot.type),
            ('rack_state', '=', 'open'),
            ])
        for open_rack in open_racks:
            if len(open_rack.positions) >= 20:
                open_rack.rack_state = 'closed'
                open_rack.save()
                continue
            rack = open_rack
            position += len(rack.positions)
            create_new_rack = False
            break

        if create_new_rack:
            today = Date.today()
            rack = cls(
                laboratory=laboratory,
                date=today,
                date_from=today,
                date_to=today,
                state='draft',
                type='rack',
                aliquot_type=aliquot.type.id,
                rack_state='open',
                rack_user=int(Transaction().user),
                )
            rack.save()

        # Rack position
        rack_position = PlanificationPosition(
            planification=rack.id,
            position=position,
            aliquot=aliquot.id,
            )
        rack_position.save()
        if position == 20:
            rack.rack_state = 'closed'
            rack.save()

        # Fraction to plan
        rack_services = []
        for analysis_id in analysis:
            if not PlanificationDetail.search([
                    ('planification', '=', rack.id),
                    ('fraction', '=', aliquot.fraction.id),
                    ('service_analysis', '=', analysis_id),
                    ]):
                rack_service = PlanificationDetail(
                    planification=rack.id,
                    fraction=aliquot.fraction.id,
                    service_analysis=analysis_id,
                    )
                rack_services.append(rack_service)
        PlanificationDetail.save(rack_services)


class RackPosition(ModelSQL, ModelView):
    'Rack Position'
    __name__ = 'lims.planification.position'

    planification = fields.Many2One('lims.planification', 'Planification',
        ondelete='CASCADE', select=True, required=True)
    position = fields.Integer('Position', required=True,
        domain=[('position', '>=', 1), ('position', '<=', 20)])
    aliquot = fields.Many2One('lims.aliquot', 'Aliquot', required=True)

    @classmethod
    def __setup__(cls):
        super(RackPosition, cls).__setup__()
        cls._order.insert(0, ('position', 'ASC'))
        t = cls.__table__()
        cls._sql_constraints += [
            ('position_uniq', Unique(t, t.planification, t.position),
                'lims_industry.msg_planification_position_unique'),
            ]
