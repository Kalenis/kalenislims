=============
LIMS Scenario
=============

Imports::
    >>> import datetime
    >>> from proteus import Model, Wizard
    >>> from trytond.tests.tools import activate_modules
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company
    >>> from trytond.modules.lims.tests.tools import \
    ...     set_lims_configuration, create_workyear, create_base_tables
    >>> today = datetime.date.today()

Install lims_tests::

    >>> config = activate_modules('lims')

Create company::

    >>> _ = create_company()
    >>> company = get_company()

Set Lims configuration::

    >>> set_lims_configuration(company)
    >>> create_workyear(company, today)

Create base tables::

    >>> create_base_tables()

Create customer::

    >>> Party = Model.get('party.party')
    >>> customer = Party(name='Customer')
    >>> address = customer.addresses.new()
    >>> address.invoice_contact = True
    >>> address.invoice_contact_default = True
    >>> address.report_contact = True
    >>> address.report_contact_default = True
    >>> address.acknowledgment_contact = True
    >>> address.acknowledgment_contact_default = True
    >>> address.email = 'name@domain.com'
    >>> customer.save()

Create Entry::

    >>> Entry = Model.get('lims.entry')
    >>> entry = Entry()
    >>> entry.party = customer
    >>> entry.save()

Create Samples::

    >>> product_type, = Model.get('lims.product.type').find([
    ...     ('code', '=', 'WINE')])
    >>> matrix, = Model.get('lims.matrix').find([
    ...     ('code', '=', 'GRAPE')])
    >>> fraction_state, = Model.get('lims.packaging.integrity').find([
    ...     ('code', '=', 'OK')])
    >>> package_type, = Model.get('lims.packaging.type').find([
    ...     ('code', '=', '01')])
    >>> zone, = Model.get('lims.zone').find([
    ...     ('code', '=', 'N')])
    >>> fraction_type, = Model.get('lims.fraction.type').find([
    ...     ('code', '=', 'MCL')])
    >>> storage_location, = Model.get('stock.location').find([
    ...     ('code', '=', 'STO')])
    >>> with config.set_context(
    ...         date_from=today, date_to=today, calculate=True):
    ...     analysis, = Model.get('lims.analysis').find([
    ...         ('code', '=', '0002')])
    >>> laboratory, = Model.get('lims.laboratory').find([
    ...     ('code', '=', 'SQ')])
    >>> method, = Model.get('lims.lab.method').find([
    ...     ('code', '=', '002')])
    >>> device, = Model.get('lims.lab.device').find([
    ...     ('code', '=', 'PH01')])

    >>> create_sample = Wizard('lims.create_sample', [entry])

    >>> create_sample.form.sample_client_description = 'Wine'
    >>> create_sample.form.product_type = product_type
    >>> create_sample.form.matrix = matrix
    >>> create_sample.form.zone = zone
    >>> create_sample.form.fraction_type = fraction_type
    >>> create_sample.form.storage_location = storage_location
    >>> create_sample.form.labels = 'LBL-001\nLBL-002\nLBL-003'

    >>> package = create_sample.form.packages.new(
    ...     quantity=1,
    ...     type=package_type,
    ...     state=fraction_state)

    >>> service = create_sample.form.services.new()
    >>> service.analysis = analysis
    >>> service.laboratory = laboratory
    >>> service.method = method
    >>> service.device = device

    >>> create_sample.execute('create_')

Confirm Entry::

    >>> entry.reload()
    >>> entry.click('confirm')

Plan the analysis::

    >>> Professional = Model.get('lims.laboratory.professional')
    >>> professional, = Professional.find([('code', '=', 'LP')])

    >>> Planification = Model.get('lims.planification')
    >>> planification = Planification()
    >>> planification.laboratory = laboratory
    >>> planification.start_date = today
    >>> planification.date_from = today
    >>> planification.date_to = today
    >>> planification.analysis.append(analysis)
    >>> _ = planification.technicians.new(laboratory_professional=professional)
    >>> planification.save()

    >>> planification.reload()
    >>> search_fractions = Wizard('lims.planification.search_fractions',
    ...     [planification])

    >>> details = Model.get(
    ...     'lims.planification.search_fractions.detail').find()
    >>> for d in details:
    ...     search_fractions.form.details.append(d)
    >>> search_fractions.execute('add')

    >>> planification.reload()
    >>> planification.click('preplan')
    >>> for f in planification.details:
    ...     for s in f.details:
    ...         s.staff_responsible.append(Professional(professional.id))
    >>> planification.save()

    >>> planification.reload()
    >>> technicians_qualification = Wizard(
    ...     'lims.planification.technicians_qualification', [planification])
    >>> _ = planification.click('confirm')

