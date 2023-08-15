from trytond.transaction import Transaction
from trytond.model import ModelView, ModelSQL, fields, Workflow
from trytond.pool import Pool
from .value_formatter import ValueFormatter
from datetime import datetime


class RecordLog(ModelSQL, ModelView):
    'Record Log'
    __name__ = 'record.log'

    name = fields.Char('Name')
    origin = fields.Reference('Operation Origin', selection='get_origin',
        readonly=True)
    user = fields.Many2One('res.user', 'User')
    field = fields.Many2One('ir.model.field', 'Field')
    old_value = fields.Char('Old Value')
    new_value = fields.Char('New Value')
    date = fields.DateTime('Date')
    is_transition = fields.Boolean('Is Transition')
    
    @classmethod
    def _get_origins(cls):
        return []

    @classmethod
    def get_origin(cls):
        Model = Pool().get('ir.model')
        models = cls._get_origins()
        models = Model.search([
            ('model', 'in', models),
            ])
        return [('', '')] + [(m.model, m.name) for m in models]

class RecordLogMixin(ValueFormatter):
    log = fields.One2Many('record.log','origin', 'Logs')

    @classmethod
    def __setup__(cls):
        super(RecordLogMixin, cls).__setup__()
        cls._track_fields = {'state'}

    def register_log(self, values):
        Log = Pool().get('record.log')
        if 'user' not in values:
            values['user'] = Transaction().user
        if 'date' not in values:
            values['date'] = datetime.now()
        if 'origin' not in values:
            values['origin'] = self
        new_log = Log.create([values])
        return new_log

    @classmethod
    def get_field(cls, fname):
        pool = Pool()
        Model = pool.get('ir.model')
        Field = pool.get('ir.model.field')
        field, = Field.search([('model.name','=', Model.get_name(cls.__name__)),('name','=',fname)])
        return field

    @classmethod
    def _register_change_log(cls, original_values):
        for record, values in original_values.items():
            for fname in values:
                vals = {**values[fname],
                        'field':cls.get_field(fname),
                        'name':"%s > %s" % (values[fname].get('old_value'), values[fname].get('new_value'))
                        }
                if fname == cls._transition_state:
                    vals['is_transition'] = True
                record.register_log(vals)


    @classmethod
    def write(cls, records, values, *args):
        original_values = {}
        to_track = [fname for fname in values.keys() if fname in cls._track_fields]
        if to_track:
            for record in records:
                original_values[record] = {}
                for tv in to_track:
                    original_values[record][tv] = {
                        'old_value':cls.format_value(tv, getattr(record, tv, None)),
                        'new_value':cls.format_value(tv, values.get(tv))
                        }
                
        super().write(records,values,*args)
        if original_values:
            cls._register_change_log(original_values)

        