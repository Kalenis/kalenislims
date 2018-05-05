# -*- coding: utf-8 -*-
# This file is part of lims module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.model import ModelView, ModelSQL, fields, Unique
from trytond.wizard import Wizard, StateTransition, StateView, Button
from trytond.pyson import Eval
from trytond.pool import Pool
from trytond.transaction import Transaction

__all__ = ['CertificationType', 'TechnicalScope', 'TechnicalScopeVersion',
    'TechnicalScopeVersionLine', 'AnalysisFamily', 'AnalysisFamilyCertificant',
    'DuplicateAnalysisFamilyStart', 'DuplicateAnalysisFamily']


class CertificationType(ModelSQL, ModelView):
    'Certification Type'
    __name__ = 'lims.certification.type'
    _rec_name = 'description'

    code = fields.Char('Code', required=True)
    description = fields.Char('Description', required=True)
    report = fields.Boolean('Report')

    def get_rec_name(self, name):
        if self.code:
            return self.code + ' - ' + self.description
        else:
            return self.description

    @classmethod
    def search_rec_name(cls, name, clause):
        field = None
        for field in ('code', 'description'):
            records = cls.search([(field,) + tuple(clause[1:])], limit=1)
            if records:
                break
        if records:
            return [(field,) + tuple(clause[1:])]
        return [(cls._rec_name,) + tuple(clause[1:])]


class TechnicalScope(ModelSQL, ModelView):
    'Technical Scope'
    __name__ = 'lims.technical.scope'

    party = fields.Many2One('party.party', 'Party', required=True)
    certification_type = fields.Many2One('lims.certification.type',
        'Certification type')
    versions = fields.One2Many('lims.technical.scope.version',
        'technical_scope', 'Versions')

    def get_rec_name(self, name):
        if self.party:
            return self.party.rec_name

    @classmethod
    def search_rec_name(cls, name, clause):
        return [('party',) + tuple(clause[1:])]


class TechnicalScopeVersion(ModelSQL, ModelView):
    'Technical Scope Version'
    __name__ = 'lims.technical.scope.version'
    _rec_name = 'number'

    technical_scope = fields.Many2One('lims.technical.scope',
        'Technical scope', required=True)
    number = fields.Char('Number', required=True)
    date = fields.Date('Date', required=True)
    expiration_date = fields.Date('Expiration date')
    version_lines = fields.Many2Many('lims.technical.scope.version.line',
        'version', 'typification', 'Typifications')
    valid = fields.Boolean('Active')

    @classmethod
    def __setup__(cls):
        super(TechnicalScopeVersion, cls).__setup__()
        cls._error_messages.update({
            'active_version': ('Only one version can be active for each '
                'technical scope'),
            })
        cls._buttons.update({
            'open_typifications': {},
            'add_typifications': {
                'invisible': ~Eval('valid'),
                },
            'remove_typifications': {
                'invisible': ~Eval('valid'),
                },
            })

    @staticmethod
    def default_valid():
        return True

    @classmethod
    def validate(cls, versions):
        super(TechnicalScopeVersion, cls).validate(versions)
        for version in versions:
            version.check_active()

    def check_active(self):
        if self.valid:
            versions = self.search([
                    ('technical_scope', '=', self.technical_scope.id),
                    ('valid', '=', True),
                    ('id', '!=', self.id),
                    ])
            if versions:
                self.raise_user_error('active_version')

    @classmethod
    @ModelView.button_action('lims.act_open_typifications')
    def open_typifications(cls, versions):
        pass

    @classmethod
    @ModelView.button_action('lims.act_add_typifications')
    def add_typifications(cls, versions):
        pass

    @classmethod
    @ModelView.button_action('lims.act_remove_typifications')
    def remove_typifications(cls, versions):
        pass


class TechnicalScopeVersionLine(ModelSQL):
    'Technical Scope Version Line'
    __name__ = 'lims.technical.scope.version.line'

    version = fields.Many2One('lims.technical.scope.version',
        'Technical scope version', ondelete='CASCADE', select=True,
        required=True)
    typification = fields.Many2One('lims.typification', 'Typification',
        ondelete='CASCADE', select=True, required=True)


class AnalysisFamily(ModelSQL, ModelView):
    'Analysis Family'
    __name__ = 'lims.analysis.family'
    _rec_name = 'description'

    code = fields.Char('Code', required=True)
    description = fields.Char('Description', required=True)
    party = fields.Many2One('party.party', 'Certificant party')
    certificants = fields.One2Many('lims.analysis.family.certificant',
        'family', 'Product Type - Matrix')

    @classmethod
    def __setup__(cls):
        super(AnalysisFamily, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code),
                'Analysis family code must be unique'),
            ]

    def get_rec_name(self, name):
        if self.code:
            return self.code + ' - ' + self.description
        else:
            return self.description

    @classmethod
    def search_rec_name(cls, name, clause):
        field = None
        for field in ('code', 'description'):
            records = cls.search([(field,) + tuple(clause[1:])], limit=1)
            if records:
                break
        if records:
            return [(field,) + tuple(clause[1:])]
        return [(cls._rec_name,) + tuple(clause[1:])]


class AnalysisFamilyCertificant(ModelSQL, ModelView):
    'Product Type - Matrix'
    __name__ = 'lims.analysis.family.certificant'

    family = fields.Many2One('lims.analysis.family', 'Family', required=True)
    product_type = fields.Many2One('lims.product.type', 'Product type',
        required=True)
    matrix = fields.Many2One('lims.matrix', 'Matrix', required=True)

    @classmethod
    def __setup__(cls):
        super(AnalysisFamilyCertificant, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('product_matrix_uniq',
                Unique(t, t.family, t.product_type, t.matrix),
                'This record already exists'),
            ]


class DuplicateAnalysisFamilyStart(ModelView):
    'Duplicate Analysis Family'
    __name__ = 'lims.analysis.family.duplicate.start'

    family_origin = fields.Many2One('lims.analysis.family', 'Family Origin')
    code = fields.Char('Code', required=True)
    description = fields.Char('Description', required=True)
    party = fields.Many2One('party.party', 'Certificant party')


class DuplicateAnalysisFamily(Wizard):
    'Duplicate Analysis Family'
    __name__ = 'lims.analysis.family.duplicate'

    start = StateView('lims.analysis.family.duplicate.start',
        'lims.lims_duplicate_analysis_family_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Duplicate', 'duplicate', 'tryton-ok', default=True),
            ])
    duplicate = StateTransition()

    def default_start(self, fields):
        AnalysisFamily = Pool().get('lims.analysis.family')
        family_origin = AnalysisFamily(Transaction().context['active_id'])
        return {
            'family_origin': family_origin.id,
            'code': family_origin.code,
            'description': family_origin.description,
            }

    def transition_duplicate(self):
        AnalysisFamily = Pool().get('lims.analysis.family')
        AnalysisFamily.copy([self.start.family_origin], default={
            'code': self.start.code,
            'description': self.start.description,
            'party': self.start.party.id if self.start.party else None,
            })
        return 'end'
