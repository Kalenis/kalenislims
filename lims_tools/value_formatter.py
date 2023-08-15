from trytond.transaction import Transaction
from trytond.pool import Pool

class ValueFormatter(object):

    @classmethod
    def _format_date(cls, field, value):
        '''Localize date to company timezone'''
        pool = Pool()
        transaction = Transaction()
        company_id = transaction.context.get('company')
        Company = pool.get('company.company')
        Lang = pool.get('ir.lang')
        lang, = Lang.search([('code', '=', transaction.language or 'en')])
        company = None
        if company_id:
            company = Company(company_id)
            value = company.convert_timezone_datetime(value)
            return lang.strftime(value)
        return value

    @classmethod
    def format_date(cls, field, value):
        return cls._format_date(field, value)
    
    @classmethod
    def format_datetime(cls, field, value):
        return cls._format_date(field, value)

    @classmethod
    def format_selection(cls, field, value):
        language = Transaction().language
        definition = field.definition(cls, language)
        for option in definition.get('selection'):
            if option[0] == value:
                value = option[1]
                break
        return value
    
    @classmethod
    def format_many2one(cls, field, value):
        Target = Pool().get(field.model_name)
        instance = None
        if isinstance(value, int):
            instance = Target(value)
        else:
            instance = value
        return getattr(instance, 'rec_name', '')
    
    @classmethod
    def format_value(cls, fname, value):        
        field = cls._fields.get(fname)
        ftype = field._type
        getter = getattr(cls, "format_%s" % ftype, None)
        if getter:
            value = getter(field, value)
        return value

    @classmethod
    def format_values(cls, record=None, fnames=[], values={}):
        if record and not values:
            if not fnames:
                return {}
            for fname in fnames:
                values[fname] = getattr(record, fname, None)

        for fname, value in values.items():
            values[fname] = cls.format_value(fname, value)
        return values
            
    


