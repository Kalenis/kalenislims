# -*- coding: utf-8 -*-
# This file is part of lims module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import Model

__all__ = ['FormulaParser']


class FormulaParser(Model):
    'Formula Parser'

    @classmethod
    def __setup__(cls):
        super(FormulaParser, cls).__setup__()
        cls._error_messages.update({
            'variable_redefine': 'Cannot redefine the value of "%s"',
            'unexpected_character': ('Unexpected character found: "%s"'
                ' at index %s'),
            'division_zero': 'Division by 0 (occured at index %s)',
            'closing_parenthesis': ('No closing parenthesis found at'
                ' character %s'),
            'unrecognized_variable': 'Unrecognized variable: "%s"',
            'extra_period': ('Found an extra period in a number at'
                ' character %s'),
            'unexpected_end': 'Unexpected end found',
            'number_expected': ('Expecting to find a number at character'
                ' %s but instead there is a "%s"'),
            })

    def __init__(self, string, vars={}, id=None, **kwargs):
        self.string = string
        self.index = 0
        self.vars = {
            'pi': 3.141592653589793,
            'e': 2.718281828459045,
            }
        for var in list(vars.keys()):
            if self.vars.get(var) is not None:
                self.raise_user_error('variable_redefine', (var,))
            self.vars[var] = vars[var]
        super(FormulaParser, self).__init__(id, **kwargs)

    def getValue(self):
        value = self.parseExpression()
        self.skipWhitespace()
        if self.hasNext():
            self.raise_user_error('unexpected_character',
                (self.peek(), str(self.index)))
        return value

    def peek(self):
        return self.string[self.index:self.index + 1]

    def hasNext(self):
        return self.index < len(self.string)

    def skipWhitespace(self):
        while self.hasNext():
            if self.peek() in ' \t\n\r':
                self.index += 1
            else:
                return

    def parseExpression(self):
        return self.parseAddition()

    def parseAddition(self):
        values = [self.parseMultiplication()]
        while True:
            self.skipWhitespace()
            char = self.peek()
            if char == '+':
                self.index += 1
                values.append(self.parseMultiplication())
            elif char == '-':
                self.index += 1
                values.append(-1 * self.parseMultiplication())
            else:
                break
        return sum(values)

    def parseMultiplication(self):
        values = [self.parsePower()]
        while True:
            self.skipWhitespace()
            char = self.peek()
            if char == '*':
                self.index += 1
                values.append(self.parsePower())
            elif char == '/':
                #div_index = self.index
                self.index += 1
                denominator = self.parsePower()
                if denominator == 0:
                    #self.raise_user_error('division_zero', (str(div_index),))
                    return 0.0
                values.append(1.0 / denominator)
            else:
                break
        value = 1.0
        for factor in values:
            value *= factor
        return value

    def parsePower(self):
        values = [self.parseParenthesis()]
        while True:
            self.skipWhitespace()
            char = self.peek()
            if char == '^':
                self.index += 1
                values.append(self.parseParenthesis())
            else:
                break
        value = values[0]
        for exponent in values[1:]:
            value **= exponent
        return value

    def parseParenthesis(self):
        self.skipWhitespace()
        char = self.peek()
        if char == '(':
            self.index += 1
            value = self.parseExpression()
            self.skipWhitespace()
            if self.peek() != ')':
                self.raise_user_error('closing_parenthesis',
                    (str(self.index),))
            self.index += 1
            return value
        else:
            return self.parseNegative()

    def parseNegative(self):
        self.skipWhitespace()
        char = self.peek()
        if char == '-':
            self.index += 1
            return -1 * self.parseParenthesis()
        else:
            return self.parseValue()

    def parseValue(self):
        self.skipWhitespace()
        char = self.peek()
        if char in '0123456789.':
            return self.parseNumber()
        else:
            return self.parseVariable()

    def parseVariable(self):
        self.skipWhitespace()
        var = ''
        while self.hasNext():
            char = self.peek()
            if char.lower() in '_abcdefghijklmnopqrstuvwxyz0123456789':
                var += char
                self.index += 1
            else:
                break

        value = self.vars.get(var, None)
        if value is None:
            self.raise_user_error('unrecognized_variable', (var,))
        if value == '':
            return float(0)
        try:
            value = float(value)
        except (ValueError):
            return float(0)
        return value

    def parseNumber(self):
        self.skipWhitespace()
        strValue = ''
        decimal_found = False
        char = ''

        while self.hasNext():
            char = self.peek()
            if char == '.':
                if decimal_found:
                    self.raise_user_error('extra_period', (str(self.index),))
                decimal_found = True
                strValue += '.'
            elif char in '0123456789':
                strValue += char
            else:
                break
            self.index += 1

        if len(strValue) == 0:
            if char == '':
                self.raise_user_error('unexpected_end')
            else:
                self.raise_user_error('number_expected',
                    (str(self.index), char))

        return float(strValue)
