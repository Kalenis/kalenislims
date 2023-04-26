from trytond.model import ModelSQL, ModelView, fields, sequence_ordered
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from trytond.exceptions import UserError
import formulas
import re
import ast

def _encode_args(args):
    encoded_args = []
    def encodeArg(data, arg):
        if type(data) is dict:
            value = data[arg]
        else:
            value = arg
        if type(value) is dict:
            for v in value:
                value[v] = encodeArg(value, v)
        elif type(value) in (list, tuple):
            val = [encodeArg(value, v) for v in value]
            value = val
        elif issubclass(type(value), ModelSQL):
            # HIGHLIGHT THE MODEL TO DECODE EASILY
            v = tuple(str(value).split(','))
            value = {'_is_instance':True, 'value':v}
            # value = ['_is_instance'] + str(value).split(',')
                
        return value
    for value in args:
        value = encodeArg(args, value)
        encoded_args.append(value)
    return str(encoded_args)

def hydrate_record_instance(value):
    model = value[0]
    id = value[1]
    try:
        int(id)
    except TypeError:
        return None
    return Pool().get(model)(id)

def _decode_args(payload):
    if not payload:
        return None
    decoded = ast.literal_eval(payload)
    new_decoded = []
    def decodeArg(data, arg):
        if type(data) is dict:
            value = data[arg]
        else:
            value = arg
        if type(value) is dict and '_is_instance' in value:
            value = hydrate_record_instance(value.get('value'))
        if type(value) is dict:
            for v in value:
                value[v] = decodeArg(value, v)
        elif type(value) in [list, tuple]:
            val = [decodeArg(value, v) for v in value]
            value = val
        return value        
    for d in decoded:
        new_decoded.append(decodeArg(decoded, d))
    return tuple(new_decoded)

FUNCTIONS = formulas.get_functions()
FUNCTIONS['FLOAT'] = lambda x: float(x)

def str_includes(list_str, value):
    value_list = list_str.split(';')
    return value in value_list

FUNCTIONS['STR_INCLUDES'] = str_includes

def is_number(value):
    res = False
    try:
        float(value)
        res = True
    except:
        pass
    return res

FUNCTIONS['IS_NUMBER'] = is_number

def run_method(object, method_name, *args):
    if not object:
        return None
    try:
        return getattr(object, method_name)(*args)
    except AttributeError:
        raise UserError('Formula Failed')

FUNCTIONS['RUN'] = run_method

def get_method(object, method_name, *args):
    try:        
        res = [
            object, 
            method_name, 
            args
        ]

        res = _encode_args(res)

        return str(['RUN_LATER', res])
        
    except AttributeError:
        raise UserError('Formula Failed')

FUNCTIONS['RUN_LATER'] = get_method


class FormulaCategory(ModelSQL, ModelView):
    'Category Formula'
    __name__ = 'formula.template.category'

    name = fields.Char('Name')
    code = fields.Char('Code')


class FormulaTemplate(ModelSQL, ModelView):
    'Formula Template'
    __name__ = 'formula.template'

    name = fields.Char('Name')
    key = fields.Char('Key')
    expression = fields.Char('Expression')
    category = fields.Many2One('formula.template.category', 'Category')
    expression_icon = fields.Function(fields.Char('Expression Icon'),
        'on_change_with_expression_icon')

    def formula_error(self):
        if not self.expression:
            return
        if not self.expression.startswith('='):
            return
        parser = formulas.Parser()
        try:
            builder = parser.ast(self.expression)[1]
            # Find missing methods:
            # https://github.com/vinci1it2000/formulas/issues/19#issuecomment-429793111
            missing_methods = [k for k, v in builder.dsp.function_nodes.items()
                if v['function'] is formulas.functions.not_implemented]
            if missing_methods:
                # When there are two occurrences of the same missing method,
                # the function name returned looks like this:
                #
                # Sample formula: A(x) + A(y)
                # missing_methods: ['A', 'A<0>']
                #
                # So in the line below we remove the '<0>' suffix
                missing_methods = {x.split('<')[0] for x in missing_methods}
                if len(missing_methods) == 1:
                    msg = 'Unknown method: '
                else:
                    msg = 'Unknown methods: '
                msg += (', '.join(missing_methods))
                return ('error', msg)

            ast = builder.compile()
            missing = (set([x.lower() for x in ast.inputs]) -
                self.previous_formulas())
            if not missing:
                return
            return ('warning', 'Referenced alias "%s" not found. Ensure it is '
                'declared before this formula.' % ', '.join(missing))
        except formulas.errors.FormulaError as error:
            msg = error.msg.replace('\n', ' ')
            if error.args[1:]:
                msg = msg % error.args[1:]
            return ('error', msg)

    def previous_formulas(self):
        res = []
        # for formula in self.interface.columns:
        #     if formula == self:
        #         break
        #     res.append(formula.alias)
        return set(res)


    @fields.depends('expression')
    def on_change_with_expression_icon(self, name=None):
        if not self.expression:
            return ''
        if not self.expression.startswith('='):
            return ''
        error = self.formula_error()
        if not error:
            return 'lims-green'
        if error[0] == 'warning':
            return 'lims-yellow'
        return 'lims-red'


class FormulaMixin():

    def get_formula(self, formula_key):        
        try:
            formula, = Pool().get('formula.template').search([('key','=',formula_key)])
        except ValueError:
            raise UserError("Missing Formula", "The formula with key %s does not exist" % formula_key)
        return formula
    
    def get_extended_inputs(self, values):
        return {}
    
    def _extract_function_args(self, expression):
        # pattern = r'^(.*)\((.*)\)$'
        # pattern = r'^(.*)\[(.*)\]$'
        pattern = r'^(.*)\{(.*)\}$'

        match = re.match(pattern, expression)
        function_name = match.group(1)
        args = match.group(2).split(',')
        return (function_name, args)

    def get_object_value(self, obj, v):
        '''Parse expressions of type obj.attr'''
        if not obj:
            return None
        value = obj

        def _call_value(method, args):
            if not args:
                args = []
            method(*args)

        splitted = v.split('.')
        args = []
        if len(splitted) > 1:
            value = obj
            for dot in splitted[1:]:
                if value:
                    if '(' in dot:
                        dot, args = self._extract_function_args(dot)
                    if type(value) is tuple or type(value) is list:
                        value = [getattr(v, dot or '') for v in value]
                    else:
                        value = getattr(value, dot or '')
                        if callable(value):
                            value = _call_value(value, args)
        # if callable(value):
        #     function_name, args = self._extract_function_args(splitted[len(splitted)-1])
        #     _call_value(value, args)
        return value


    def get_input_value(self, name, values):
        def _get_from_values():
            if type(values) is dict:
                return values.get(name, None)
            return getattr(values, name, None)
        value = None
        if '.' in name:
            fname = name.split('.')[0]
            value = self.get_object_value(self.get_input_value(fname, values), name)
        # Preserve support to call straight attribute name without "self"
        if hasattr(self, name):
            value = getattr(self, name, None)
        if not value:
            value = _get_from_values()
        if not value:
            extended_inputs = self.get_extended_inputs(values)
            if name in extended_inputs:
                value = extended_inputs.get(name)
        if callable(value):
            value = value()
        return value
    
    def _check_callable(self, result):
        try:
            result = result.tolist()
        except AttributeError:
            return None
        if type(result) is str and 'RUN_LATER' in result:
            result = ast.literal_eval(result)
            if type(result) is list and result[0] == 'RUN_LATER':
                decoded = _decode_args(result[1])
                object = decoded[0]
                method_name = decoded[1]
                args = decoded[2]
                getattr(object, method_name)(*args)
                return True
        return None
    
    def compile(self, formula):
        try:
            func = formulas.Parser().ast(formula.expression)[1].compile()
        except formulas.errors.FormulaError:
            return "Invalid Formula"

        return func

    def solve_formula(self, formula_key, values):
        formula = self.get_formula(formula_key)
        if not formula:
            return ""
        func = self.compile(formula)
        inputs = (' '.join([x for x in func.inputs])).lower().split()
        formula_values = [self.get_input_value(input, values) for input in inputs]
        res = func(*formula_values)
        method_run = self._check_callable(res)
        if method_run is not None:
            return method_run
        
        return res
