# -*- coding: utf-8 -*-
# This file is part of the lims module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from proteus import Model

__all__ = ['create_base_tables']


def create_base_tables(config=None):
    "Create Base Tables"

    # Configuration / Laboratory
    _create_base_laboratory_tables(config)


def _create_base_laboratory_tables(config=None):
    "Configuration / Laboratory"
    LaboratoryProfessional = Model.get('lims.laboratory.professional',
        config=config)
    Laboratory = Model.get('lims.laboratory', config=config)
    LabDeviceType = Model.get('lims.lab.device.type', config=config)
    LabDevice = Model.get('lims.lab.device', config=config)
    User = Model.get('res.user', config=config)
    Party = Model.get('party.party', config=config)
    Location = Model.get('stock.location', config=config)
    UomCategory = Model.get('product.uom.category', config=config)
    Uom = Model.get('product.uom', config=config)

    lims_user = User(1)
    party = Party(
        name='Laboratory Professional',
        is_lab_professional=True,
        lims_user=lims_user)
    party.save()
    professional = LaboratoryProfessional(
        party=party,
        code='LP',
        role='Responsible')
    professional.save()

    related_location, = Location.find([('code', '=', 'STO')])
    laboratory = Laboratory(
        code='SQ',
        description='Chemistry Laboratory',
        default_laboratory_professional=professional,
        default_signer=professional,
        related_location=related_location,
        section='sq')
    laboratory.save()

    lims_user.laboratories.append(laboratory)
    lims_user.save()

    device_type = LabDeviceType(
        code='PH',
        description='pH Meters')
    device_type.save()

    device = LabDevice(
        code='PH01',
        description='pH Meter 01',
        device_type=device_type)
    device.laboratories.new(laboratory=laboratory)
    device.save()

    uom_cateogory = UomCategory(
        name='Test Category',
        lims_only_available=True)
    uom_cateogory.save()

    uom = Uom(
        name='Test UoM',
        symbol='TUoM',
        category=uom_cateogory)
    uom.save()
