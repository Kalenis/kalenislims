# -*- coding: utf-8 -*-
# This file is part of lims module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import Model
from trytond.exceptions import UserError
from trytond.i18n import gettext


class FormulaParser(Model):
    'Formula Parser'
    __slots__ = ('_string', '_index', '_vars')

    def __init__(self, string, vars={}, id=None, **kwargs):
        self._string = string
        self._index = 0
        self._vars = {
            'pi': 3.141592653589793,
            'e': 2.718281828459045,
            }
        for var in list(vars.keys()):
            if self._vars.get(var) is not None:
                raise UserError(gettext(
                    'lims.msg_variable_redefine', variable=var))
            self._vars[var] = vars[var]
        super().__init__(id, **kwargs)

    def getValue(self):
        value = self.parseExpression()
        self.skipWhitespace()
        if self.hasNext():
            raise UserError(gettext('lims.msg_unexpected_character',
                character=self.peek(), index=str(self._index)))
        return value

    def peek(self):
        return self._string[self._index:self._index + 1]

    def hasNext(self):
        return self._index < len(self._string)

    def skipWhitespace(self):
        while self.hasNext():
            if self.peek() in ' \t\n\r':
                self._index += 1
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
                self._index += 1
                values.append(self.parseMultiplication())
            elif char == '-':
                self._index += 1
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
                self._index += 1
                values.append(self.parsePower())
            elif char == '/':
                # div_index = self._index
                self._index += 1
                denominator = self.parsePower()
                if denominator == 0:
                    # raise UserError(gettext(
                    #     'lims.msg_division_zero', index=str(div_index)))
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
                self._index += 1
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
            self._index += 1
            value = self.parseExpression()
            self.skipWhitespace()
            if self.peek() != ')':
                raise UserError(gettext(
                    'lims.msg_closing_parenthesis', index=str(self._index)))
            self._index += 1
            return value
        else:
            return self.parseNegative()

    def parseNegative(self):
        self.skipWhitespace()
        char = self.peek()
        if char == '-':
            self._index += 1
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
                self._index += 1
            else:
                break

        value = self._vars.get(var, None)
        if value is None:
            raise UserError(gettext(
                'lims.msg_unrecognized_variable', variable=var))
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
                    raise UserError(gettext(
                        'lims.msg_extra_period', index=str(self._index)))
                decimal_found = True
                strValue += '.'
            elif char in '0123456789':
                strValue += char
            else:
                break
            self._index += 1

        if len(strValue) == 0:
            if char == '':
                raise UserError(gettext('lims.msg_unexpected_end'))
            else:
                raise UserError(gettext('lims.msg_number_expected',
                    index=str(self._index), character=char))

        return float(strValue)
