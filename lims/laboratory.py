# -*- coding: utf-8 -*-
# This file is part of lims module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.model import ModelView, ModelSQL, fields, Unique
from trytond.pool import Pool
from trytond.transaction import Transaction

__all__ = ['LaboratoryProfessional', 'Laboratory', 'LaboratoryCVCorrection',
    'LabMethod', 'LabDeviceType', 'LabDevice', 'LabDeviceLaboratory',
    'LabDeviceTypeLabMethod', ]


class Laboratory(ModelSQL, ModelView):
    'Laboratory'
    __name__ = 'lims.laboratory'
    _rec_name = 'description'

    code = fields.Char('Code', required=True)
    description = fields.Char('Description', required=True)
    default_laboratory_professional = fields.Many2One(
        'lims.laboratory.professional', 'Default professional')
    default_signer = fields.Many2One('lims.laboratory.professional',
        'Default signer', required=True)
    related_location = fields.Many2One('stock.location', 'Related location',
        required=True, domain=[('type', '=', 'storage')])
    cv_corrections = fields.One2Many('lims.laboratory.cv_correction',
        'laboratory', 'CV Corrections',
        help="Corrections for Coefficients of Variation (Control Charts)")
    section = fields.Selection([
        ('amb', 'Ambient'),
        ('for', 'Formulated'),
        ('mi', 'Microbiology'),
        ('rp', 'Agrochemical Residues'),
        ('sq', 'Chemistry'),
        ], 'Section', sort=False)
    headquarters = fields.Char('Headquarters', translate=True)

    @classmethod
    def __setup__(cls):
        super(Laboratory, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code),
                'Laboratory code must be unique'),
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


class LaboratoryCVCorrection(ModelSQL, ModelView):
    'CV Correction'
    __name__ = 'lims.laboratory.cv_correction'

    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        required=True, ondelete='CASCADE', select=True)
    fraction_type = fields.Many2One('lims.fraction.type', 'Fraction type',
        required=True)
    min_cv = fields.Float('Minimum CV (%)')
    max_cv = fields.Float('Maximum CV (%)')
    min_cv_corr_fact = fields.Float('Correction factor for Minimum CV',
        help="Correction factor for CV between Min and Max")
    max_cv_corr_fact = fields.Float('Correction factor for Maximum CV',
        help="Correction factor for CV greater than Max")


class LaboratoryProfessional(ModelSQL, ModelView):
    'Laboratory Professional'
    __name__ = 'lims.laboratory.professional'

    party = fields.Many2One('party.party', 'Party', required=True,
        domain=[('is_lab_professional', '=', True)])
    code = fields.Char('Code')
    role = fields.Char('Signature role', translate=True)
    signature = fields.Binary('Signature')
    methods = fields.One2Many('lims.lab.professional.method', 'professional',
        'Methods')

    @classmethod
    def __setup__(cls):
        super(LaboratoryProfessional, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code),
                'Professional code must be unique'),
            ('party_uniq', Unique(t, t.party),
                'The party is already associated to a professional'),
            ]

    def get_rec_name(self, name):
        if self.party:
            return self.party.name

    @classmethod
    def search_rec_name(cls, name, clause):
        return [('party',) + tuple(clause[1:])]

    @classmethod
    def get_lab_professional(cls):
        cursor = Transaction().connection.cursor()
        login_user_id = Transaction().user
        cursor.execute('SELECT id '
            'FROM party_party '
            'WHERE is_lab_professional = true '
                'AND lims_user = %s '
            'LIMIT 1', (login_user_id,))
        party_id = cursor.fetchone()
        if not party_id:
            return None
        cursor.execute('SELECT id '
            'FROM "' + cls._table + '" '
            'WHERE party = %s '
            'LIMIT 1', (party_id[0],))
        lab_professional_id = cursor.fetchone()
        if (lab_professional_id):
            return lab_professional_id[0]
        return None


class LabMethod(ModelSQL, ModelView):
    'Laboratory Method'
    __name__ = 'lims.lab.method'

    code = fields.Char('Code', required=True)
    name = fields.Char('Name', required=True, translate=True)
    reference = fields.Char('Reference')
    determination = fields.Char('Determination', required=True)
    requalification_months = fields.Integer('Requalification months',
        required=True)
    supervised_requalification = fields.Boolean('Supervised requalification')
    deprecated_since = fields.Date('Deprecated since')
    pnt = fields.Char('PNT')
    results_estimated_waiting = fields.Integer(
        'Estimated number of days for results')

    @classmethod
    def __setup__(cls):
        super(LabMethod, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code),
                'Method code must be unique'),
            ]

    def get_rec_name(self, name):
        if self.code:
            return self.code + ' - ' + self.name
        else:
            return self.name

    @classmethod
    def search_rec_name(cls, name, clause):
        field = None
        for field in ('code', 'name'):
            records = cls.search([(field,) + tuple(clause[1:])], limit=1)
            if records:
                break
        if records:
            return [(field,) + tuple(clause[1:])]
        return [(cls._rec_name,) + tuple(clause[1:])]

    @classmethod
    def write(cls, *args):
        super(LabMethod, cls).write(*args)
        actions = iter(args)
        for methods, vals in zip(actions, actions):
            if 'results_estimated_waiting' in vals:
                cls.update_laboratory_notebook(methods)

    @classmethod
    def update_laboratory_notebook(cls, methods):
        NotebookLine = Pool().get('lims.notebook.line')

        for method in methods:
            notebook_lines = NotebookLine.search([
                ('method', '=', method.id),
                ('accepted', '=', False),
                ])
            if notebook_lines:
                NotebookLine.write(notebook_lines, {
                    'results_estimated_waiting': (
                        method.results_estimated_waiting),
                    })


class LabDevice(ModelSQL, ModelView):
    'Laboratory Device'
    __name__ = 'lims.lab.device'
    _rec_name = 'description'

    code = fields.Char('Code', required=True)
    description = fields.Char('Description', required=True)
    device_type = fields.Many2One('lims.lab.device.type', 'Device type',
        required=True)
    laboratories = fields.One2Many('lims.lab.device.laboratory', 'device',
        'Laboratories', required=True)
    serial_number = fields.Char('Serial number')

    @classmethod
    def __setup__(cls):
        super(LabDevice, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code),
                'Device code must be unique'),
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


class LabDeviceType(ModelSQL, ModelView):
    'Laboratory Device Type'
    __name__ = 'lims.lab.device.type'
    _rec_name = 'description'

    code = fields.Char('Code', required=True)
    description = fields.Char('Description', required=True)
    methods = fields.Many2Many('lims.lab.device.type-lab.method',
        'device_type', 'method', 'Methods')

    @classmethod
    def __setup__(cls):
        super(LabDeviceType, cls).__setup__()
        t = cls.__table__()
        cls._sql_constraints += [
            ('code_uniq', Unique(t, t.code),
                'Device type code must be unique'),
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


class LabDeviceTypeLabMethod(ModelSQL):
    'Laboratory Device Type - Laboratory Method'
    __name__ = 'lims.lab.device.type-lab.method'

    device_type = fields.Many2One('lims.lab.device.type', 'Device type',
        ondelete='CASCADE', select=True, required=True)
    method = fields.Many2One('lims.lab.method', 'Method',
        ondelete='CASCADE', select=True, required=True)


class LabDeviceLaboratory(ModelSQL, ModelView):
    'Laboratory Device Laboratory'
    __name__ = 'lims.lab.device.laboratory'

    device = fields.Many2One('lims.lab.device', 'Device', required=True,
        ondelete='CASCADE', select=True)
    laboratory = fields.Many2One('lims.laboratory', 'Laboratory',
        required=True)
    physically_here = fields.Boolean('Physically here')

    @classmethod
    def __setup__(cls):
        super(LabDeviceLaboratory, cls).__setup__()
        cls._error_messages.update({
            'physically_elsewhere': ('This Device is physically in another'
            ' Laboratory'),
            })

    @staticmethod
    def default_physically_here():
        return True

    @classmethod
    def validate(cls, laboratories):
        super(LabDeviceLaboratory, cls).validate(laboratories)
        for l in laboratories:
            l.check_location()

    def check_location(self):
        if self.physically_here:
            laboratories = self.search([
                ('device', '=', self.device.id),
                ('physically_here', '=', True),
                ('id', '!=', self.id),
                ])
            if laboratories:
                self.raise_user_error('physically_elsewhere')
