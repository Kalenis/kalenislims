# -*- coding: utf-8 -*-
# This file is part of the lims module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import datetime
from decimal import Decimal
from dateutil.relativedelta import relativedelta

from proteus import Model

from trytond.modules.company.tests.tools import get_company

__all__ = ['set_lims_configuration', 'create_workyear', 'create_base_tables']


def set_lims_configuration(company=None, config=None):
    "Set Lims Configuration"
    if not company:
        company = get_company()

    # Create fraction product
    ProductUom = Model.get('product.uom', config=config)
    unit, = ProductUom.find([('name', '=', 'Unit')])
    ProductTemplate = Model.get('product.template', config=config)
    Product = Model.get('product.product', config=config)
    fraction_product = Product()
    fraction_template = ProductTemplate()
    fraction_template.name = 'Fraction'
    fraction_template.default_uom = unit
    fraction_template.type = 'goods'
    fraction_template.list_price = Decimal('1')
    fraction_template.cost_price = Decimal('1')
    fraction_template.save()
    fraction_product.template = fraction_template
    fraction_product.save()

    # Create analysis product category
    ProductCategory = Model.get('product.category', config=config)
    analysis_product_category = ProductCategory()
    analysis_product_category.name = 'Analysis Services'
    analysis_product_category.save()

    # Create default notebook view
    default_notebook_view = _create_default_notebook_view(config)

    # Create required sequences
    Sequence = Model.get('ir.sequence', config=config)
    planification_sequence = Sequence()
    planification_sequence.name = 'Planification Sequence'
    planification_sequence.code = 'lims.planification'
    planification_sequence.company = company
    planification_sequence.save()

    # Set Lims configuration
    LimsConfiguration = Model.get('lims.configuration', config=config)
    lims_config, = LimsConfiguration.find()
    lims_config.fraction_product = fraction_product
    lims_config.analysis_product_category = analysis_product_category
    lims_config.default_notebook_view = default_notebook_view
    lims_config.planification_sequence = planification_sequence
    lims_config.save()


def _create_default_notebook_view(config=None):
    "Create default notebook view"
    NotebookView = Model.get('lims.notebook.view', config=config)
    NotebookViewColumn = Model.get('lims.notebook.view.column', config=config)
    Field = Model.get('ir.model.field', config=config)

    default_notebook_view = NotebookView()
    default_notebook_view.name = 'Default View'
    sequence = 1
    for field_name in ('analysis', ):
        column = NotebookViewColumn()
        default_notebook_view.columns.append(column)
        field, = Field.find([
            ('model.model', '=', 'lims.notebook.line'),
            ('name', '=', field_name),
            ])
        column.field = field
        column.sequence = sequence
        sequence += 1
    default_notebook_view.save()
    return default_notebook_view


def create_workyear(company=None, today=None, config=None):
    "Create Work Year"
    if not company:
        company = get_company()
    if not today:
        today = datetime.date.today()

    # Create sequences
    Sequence = Model.get('ir.sequence', config=config)
    entry_sequence = Sequence()
    entry_sequence.name = 'Entry Sequence'
    entry_sequence.code = 'lims.entry'
    entry_sequence.company = company
    entry_sequence.save()
    sample_sequence = Sequence()
    sample_sequence.name = 'Sample Sequence'
    sample_sequence.code = 'lims.sample'
    sample_sequence.company = company
    sample_sequence.save()
    service_sequence = Sequence()
    service_sequence.name = 'Service Sequence'
    service_sequence.code = 'lims.service'
    service_sequence.company = company
    service_sequence.save()
    results_report_sequence = Sequence()
    results_report_sequence.name = 'Results Report Sequence'
    results_report_sequence.code = 'lims.results_report'
    results_report_sequence.company = company
    results_report_sequence.save()

    # Create Work Year
    LabWorkYear = Model.get('lims.lab.workyear', config=config)
    workyear = LabWorkYear()
    workyear.code = str(today.year)
    workyear.start_date = today + relativedelta(month=1, day=1)
    workyear.end_date = today + relativedelta(month=12, day=31)
    workyear.entry_sequence = entry_sequence
    workyear.sample_sequence = sample_sequence
    workyear.service_sequence = service_sequence
    workyear.results_report_sequence = results_report_sequence
    workyear.save()

    # Set default entry control
    default_entry_control = _create_default_entry_control(company, today,
        config)
    workyear.default_entry_control = default_entry_control
    workyear.save()


def _create_default_entry_control(company=None, today=None, config=None):
    "Create default entry control"
    Entry = Model.get('lims.entry', config=config)
    InvoiceContact = Model.get('lims.entry.invoice_contacts', config=config)
    ReportContact = Model.get('lims.entry.report_contacts', config=config)
    AcknowledgmentContact = Model.get('lims.entry.acknowledgment_contacts',
        config=config)

    default_entry_control = Entry()
    default_entry_control.date = datetime.datetime.combine(today,
        datetime.time.min)
    default_entry_control.party = company.party
    default_entry_control.invoice_party = company.party

    # Set party contacts
    contact = _create_company_contacts(company, config)
    invoice_contact = InvoiceContact()
    default_entry_control.invoice_contacts.append(invoice_contact)
    invoice_contact.contact = contact
    report_contact = ReportContact()
    default_entry_control.report_contacts.append(report_contact)
    report_contact.contact = contact
    acknowledgment_contact = AcknowledgmentContact()
    default_entry_control.acknowledgment_contacts.append(
        acknowledgment_contact)
    acknowledgment_contact.contact = contact

    default_entry_control.no_acknowledgment_of_receipt = True
    default_entry_control.state = 'draft'
    default_entry_control.save()

    # Confirm entry
    default_entry_control.click('confirm')
    return default_entry_control


def _create_company_contacts(company=None, config=None):
    "Create contacts for company party"
    if not company:
        company = get_company()

    Address = Model.get('party.address', config=config)
    address, = Address.find([('party', '=', company.party.id)])
    address.invoice_contact = True
    address.report_contact = True
    address.acknowledgment_contact = True
    address.email = 'name@domain.com'
    address.save()
    return address


def create_base_tables(config=None):
    "Create Base Tables"

    # Configuration / Certification

    # Configuration / Entry
    _create_base_entry_tables(config)

    # Configuration / Laboratory
    _create_base_laboratory_tables(config)

    # Configuration / Base Tables
    _create_base_tables(config)


def _create_base_entry_tables(config=None):
    "Configuration / Entry"
    PackagingType = Model.get('lims.packaging.type', config=config)
    PackagingIntegrity = Model.get('lims.packaging.integrity', config=config)
    Zone = Model.get('lims.zone', config=config)
    EntrySuspensionReason = Model.get('lims.entry.suspension.reason',
        config=config)

    packaging_type = PackagingType(
        code='01',
        description='Package')
    packaging_type.save()

    packaging_integrity = PackagingIntegrity(
        code='OK',
        description='Ok')
    packaging_integrity.save()

    zone = Zone(
        code='N',
        description='North')
    zone.save()

    suspension_reason = EntrySuspensionReason(
        code='01',
        description='Administration pending',
        by_default=True)
    suspension_reason.save()


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


def _create_base_tables(config=None):
    "Configuration / Base Tables"
    ProductType = Model.get('lims.product.type', config=config)
    Matrix = Model.get('lims.matrix', config=config)
    LabMethod = Model.get('lims.lab.method', config=config)
    Analysis = Model.get('lims.analysis', config=config)
    Typification = Model.get('lims.typification', config=config)
    Laboratory = Model.get('lims.laboratory', config=config)
    LabDevice = Model.get('lims.lab.device', config=config)
    FractionType = Model.get('lims.fraction.type', config=config)

    product_type = ProductType(
        code='WINE',
        description='Wine')
    product_type.save()

    matrix = Matrix(
        code='GRAPE',
        description='Grape')
    matrix.save()

    method = LabMethod(
        code='002',
        name='SQ 002 : By potentiometry',
        determination='DETERMINATION OF pH MEASUREMENT BY POTENTIOMETRY',
        requalification_months=12,
        results_estimated_waiting=10)
    method.save()

    laboratory, = Laboratory.find([('code', '=', 'SQ')])
    device, = LabDevice.find([('code', '=', 'PH01')])
    analysis = Analysis(
        code='0002',
        description='pH (at 20°C)',
        type='analysis',
        behavior='normal')
    analysis.laboratories.new(laboratory=laboratory)
    analysis.methods.append(method)
    analysis.devices.new(laboratory=laboratory, device=device)
    analysis.save()
    analysis.click('activate')

    typification = Typification(
        product_type=product_type,
        matrix=matrix,
        analysis=analysis,
        method=method)
    typification.save()

    fraction_type = FractionType(
        code='MCL',
        description='Customer')
    fraction_type.save()
