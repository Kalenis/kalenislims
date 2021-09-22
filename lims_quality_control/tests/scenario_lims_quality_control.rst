=============================
LIMS Quality Control Scenario
=============================

Imports::
    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from operator import attrgetter
    >>> from proteus import config, Model, Wizard
    >>> from trytond.tests.tools import activate_modules
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company
    >>> from trytond.modules.lims.tests.tools import \
    ...     set_lims_configuration, create_workyear
    >>> from trytond.modules.lims_quality_control.tests.tools import \
    ...     create_base_tables
    >>> today = datetime.date.today()

Install quality_test module::

    >>> config = activate_modules('lims_quality_control')

Create company::

    >>> _ = create_company()
    >>> company = get_company()

Set Lims configuration::

    >>> set_lims_configuration(company)
    >>> create_workyear(company, today)

Create base tables::

    >>> create_base_tables()

Create Quality Configuration::

    >>> Sequence = Model.get('ir.sequence')
    >>> Configuration = Model.get('lims.quality.configuration')
    >>> quality_sequence, = Sequence.find(
    ...     [('sequence_type.name', '=', "Quality Control")], limit=1)
    >>> sample_location, = Model.get('stock.location').find([
    ...     ('code', '=', 'STO')])
    >>> configuration = Configuration(1)
    >>> configuration.quality_sequence = quality_sequence
    >>> configuration.sample_location = sample_location
    >>> configuration.save()
    >>> LabWorkYear = Model.get('lims.lab.workyear')
    >>> workyear = LabWorkYear(1)
    >>> workyear.default_entry_quality = workyear.default_entry_control
    >>> workyear.save()

Add zone to default entry for samples party::

    >>> Zone = Model.get('lims.zone')
    >>> zone = Zone(
    ...     code='N',
    ...     description='North')
    >>> zone.save()
    >>> party = workyear.default_entry_quality.party
    >>> party.entry_zone = zone
    >>> party.save()

Create Product Type::

    >>> ProductType = Model.get('lims.product.type')
    >>> product_type = ProductType(
    ...     code='WINE',
    ...     description='Wine')
    >>> product_type.save()

Create Matrix::

    >>> Matrix = Model.get('lims.matrix')
    >>> matrix = Matrix(
    ...     code='GRAPE',
    ...     description='Grape')
    >>> matrix.save()

Create Method::

    >>> LabMethod = Model.get('lims.lab.method')
    >>> method = LabMethod(
    ...     code='001',
    ...     name='SQ 001 : By liquid chromatography',
    ...     determination='SQ 008 : By high performance liquid chromatography (HPLC) with refractive index detector (RID).',
    ...     requalification_months=12,
    ...     results_estimated_waiting=10)
    >>> method.save()

Add qualification for the professional::

    >>> Professional = Model.get('lims.laboratory.professional')
    >>> professional, = Professional.find([('code', '=', 'LP')])
    >>> LabProfessionalMethod = Model.get('lims.lab.professional.method')
    >>> professional_method = LabProfessionalMethod(
    ...     professional=professional,
    ...     method=method,
    ...     state='qualified',
    ...     type='preparation')
    >>> _ = professional_method.requalification_history.new(
    ...     type='qualification',
    ...     date=today,
    ...     last_execution_date=today)
    >>> professional_method.save()

Create analysis product category::

    >>> ProductCategory = Model.get('product.category')
    >>> analysis_product_category = ProductCategory(
    ...     name='Test analysis')
    >>> analysis_product_category.save()
    >>> LimsConfiguration = Model.get('lims.configuration')
    >>> lims_config, = LimsConfiguration.find()
    >>> lims_config.analysis_product_category = analysis_product_category
    >>> lims_config.save()

Create Analyses::

    >>> laboratory, = Model.get('lims.laboratory').find([('code', '=', 'SQ')])
    >>> device, = Model.get('lims.lab.device').find([('code', '=', 'PH01')])
    >>> unit, = Model.get('product.uom').find([('name', '=', 'Test UoM')])

    >>> Analysis = Model.get('lims.analysis')
    >>> analysis = Analysis(
    ...     code='0001',
    ...     description='Glucose',
    ...     type='analysis',
    ...     behavior='normal',
    ...     quality_type='quantitative')
    >>> _ = analysis.laboratories.new(laboratory=laboratory)
    >>> analysis.methods.append(LabMethod(method.id))
    >>> _ = analysis.devices.new(laboratory=laboratory, device=device)
    >>> analysis.save()
    >>> analysis.click('activate')

    >>> Typification = Model.get('lims.typification')
    >>> typification_1 = Typification(
    ...     product_type=product_type,
    ...     matrix=matrix,
    ...     analysis=analysis,
    ...     method=method,
    ...     quality=True,
    ...     quality_min=0.0,
    ...     quality_max=5.0,
    ...     start_uom=unit)
    >>> typification_1.save()

    >>> analysis = Analysis(
    ...     code='0002',
    ...     description='Fructose',
    ...     type='analysis',
    ...     behavior='normal',
    ...     quality_type='quantitative')
    >>> _ = analysis.laboratories.new(laboratory=laboratory)
    >>> analysis.methods.append(LabMethod(method.id))
    >>> _ = analysis.devices.new(laboratory=laboratory, device=device)
    >>> analysis.save()
    >>> analysis.click('activate')

    >>> typification_2 = Typification(
    ...     product_type=product_type,
    ...     matrix=matrix,
    ...     analysis=analysis,
    ...     method=method,
    ...     quality=True,
    ...     quality_min=1.0,
    ...     quality_max=10.0,
    ...     start_uom=unit)
    >>> typification_2.save()

    >>> analysis = Analysis(
    ...     code='0003',
    ...     description='Colour',
    ...     type='analysis',
    ...     behavior='normal',
    ...     quality_type='qualitative')
    >>> _ = analysis.laboratories.new(laboratory=laboratory)
    >>> analysis.methods.append(LabMethod(method.id))
    >>> _ = analysis.devices.new(laboratory=laboratory, device=device)
    >>> _ = analysis.quality_possible_values.new(name='Valid')
    >>> _ = analysis.quality_possible_values.new(name='Not valid')
    >>> analysis.save()
    >>> analysis.click('activate')

    >>> QualitativeValue = Model.get('lims.quality.qualitative.value')
    >>> qualitative_value, = QualitativeValue.find([
    ...     ('name', '=', 'Valid'),
    ...     ('analysis', '=', analysis),
    ...     ])

    >>> typification_3 = Typification(
    ...     product_type=product_type,
    ...     matrix=matrix,
    ...     analysis=analysis,
    ...     method=method,
    ...     quality=True,
    ...     valid_value=qualitative_value)
    >>> typification_3.save()

    >>> analysis = Analysis(
    ...     code='0004',
    ...     description='Smell',
    ...     type='analysis',
    ...     behavior='normal',
    ...     quality_type='qualitative')
    >>> _ = analysis.laboratories.new(laboratory=laboratory)
    >>> analysis.methods.append(LabMethod(method.id))
    >>> _ = analysis.devices.new(laboratory=laboratory, device=device)
    >>> _ = analysis.quality_possible_values.new(name='Valid')
    >>> _ = analysis.quality_possible_values.new(name='Not valid')
    >>> analysis.save()
    >>> analysis.click('activate')

    >>> qualitative_value, = QualitativeValue.find([
    ...     ('name', '=', 'Valid'),
    ...     ('analysis', '=', analysis),
    ...     ])

    >>> typification_4 = Typification(
    ...     product_type=product_type,
    ...     matrix=matrix,
    ...     analysis=analysis,
    ...     method=method,
    ...     quality=True,
    ...     valid_value=qualitative_value)
    >>> typification_4.save()

Create Interface::

    >>> Interface = Model.get('lims.interface')
    >>> interface = Interface(
    ...     name='Interface',
    ...     kind='template',
    ...     template_type='excel',
    ...     first_row=1)
    >>> _ = interface.columns.new(
    ...     name='Column',
    ...     alias='column',
    ...     type_='char')
    >>> interface.save()
    >>> interface.click('activate')

Create Template Analysis Sheet::

    >>> TemplateAnalysisSheet = Model.get('lims.template.analysis_sheet')
    >>> template_analysis_sheet = TemplateAnalysisSheet(
    ...     interface=interface,
    ...     name='Template Analysis Sheet')
    >>> _ = template_analysis_sheet.analysis.new(
    ...     analysis=typification_1.analysis)
    >>> _ = template_analysis_sheet.analysis.new(
    ...     analysis=typification_2.analysis)
    >>> _ = template_analysis_sheet.analysis.new(
    ...     analysis=typification_3.analysis)
    >>> _ = template_analysis_sheet.analysis.new(
    ...     analysis=typification_4.analysis)
    >>> template_analysis_sheet.save()

Create Quality Fraction Type::

    >>> PackagingType = Model.get('lims.packaging.type')
    >>> packaging_type = PackagingType(
    ...     code='01',
    ...     description='Package')
    >>> packaging_type.save()
    >>> PackagingIntegrity = Model.get('lims.packaging.integrity')
    >>> packaging_integrity = PackagingIntegrity(
    ...     code='OK',
    ...     description='Ok')
    >>> packaging_integrity.save()
    >>> fraction_type = Model.get('lims.fraction.type')(
    ...     code='QC',
    ...     description='Quality control',
    ...     default_package_type=packaging_type,
    ...     default_fraction_state=packaging_integrity)
    >>> fraction_type.save()
    >>> LimsConfiguration = Model.get('lims.configuration')
    >>> lims_config, = LimsConfiguration.find()
    >>> lims_config.qc_fraction_type = fraction_type
    >>> lims_config.save()

Create product to test::

    >>> ProductUom = Model.get('product.uom')
    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> ProductTemplate = Model.get('product.template')
    >>> test_product = ProductTemplate()
    >>> test_product.name = 'Kalenis Wine'
    >>> test_product.default_uom = unit
    >>> test_product.type = 'goods'
    >>> test_product.product_type = product_type
    >>> test_product.matrix = matrix
    >>> test_product.save()

Create Template, Kalenis Wine::

    >>> Template = Model.get('lims.quality.template')
    >>> template = Template()
    >>> template.name = 'Kalenis Wine'
    >>> template.product, = test_product.products
    >>> template.end_date = today
    >>> template.comments = 'Comments'
    >>> template.save()

    >>> typification_1.quality_template = template
    >>> typification_1.save()
    >>> typification_2.quality_template = template
    >>> typification_2.save()
    >>> typification_3.quality_template = template
    >>> typification_3.save()
    >>> typification_4.quality_template = template
    >>> typification_4.save()

    >>> template.click('active')

Create Lot::

    >>> Lot = Model.get('stock.lot')
    >>> lot = Lot(
    ...     number='0001',
    ...     product=test_product.products[0])
    >>> lot.save()

Take a sample::

    >>> take_sample = Wizard('lims.take.sample', [lot])
    >>> take_sample.form.label = 'LBL-001'
    >>> take_sample.execute('confirm')
    >>> take_sample.execute('end')
    >>> take_sample.state
    'end'

Create quality test::

    >>> Sample = Model.get('lims.sample')
    >>> sample, = Sample.find([('lot', '=', lot)])
    >>> create_test = Wizard('lims.create.quality.test', [sample])
    >>> create_test.form.product, = test_product.products
    >>> create_test.execute('confirm')
    >>> test, = create_test.actions[0]
    >>> test.click('confirm')
    >>> test.state
    'confirmed'
    >>> len(test.lines)
    4

Create Planification::

    >>> Planification = Model.get('lims.planification')
    >>> planification = Planification()
    >>> planification.laboratory = laboratory
    >>> planification.start_date = today
    >>> planification.date_from = today
    >>> planification.date_to = today
    >>> planification.analysis.append(typification_1.analysis)
    >>> planification.analysis.append(typification_2.analysis)
    >>> planification.analysis.append(typification_3.analysis)
    >>> planification.analysis.append(typification_4.analysis)
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
    >>> planification.state
    'preplanned'
    >>> len(planification.analysis)
    4

    >>> for f in planification.details:
    ...     for s in f.details:
    ...         s.staff_responsible.append(Professional(professional.id))
    >>> planification.save()
    >>> planification.reload()
    >>> technicians_qualification = Wizard(
    ...     'lims.planification.technicians_qualification', [planification])
    >>> _ = planification.click('confirm')
    >>> planification.state
    'confirmed'

Add results and check success in lines::

    >>> quantitavive_results = {
    ...     typification_1: '6.0',
    ...     typification_2: '3.0',
    ...     }
    >>> qualitative_results = {
    ...     typification_3: 'Not valid',
    ...     typification_4: 'Valid',
    ...     }
    >>> for line in test.lines:
    ...     if line.typification in [typification_1, typification_2]:
    ...         line.result = quantitavive_results[line.typification]
    ...     if line.typification in [typification_3, typification_4]:
    ...         qualitative_value, = QualitativeValue.find([
    ...             ('name', '=', qualitative_results[line.typification]),
    ...             ('analysis', '=', line.analysis),
    ...             ])
    ...         line.qualitative_value = qualitative_value
    ...     line.end_date = today
    ...     line.accepted = True
    ...     line.save()
    ...     line.success
    True
    False
    True
    False

Create results report::

    >>> generate_results_report = Wizard('lims.generate_results_report')
    >>> generate_results_report.form.date_from = today
    >>> generate_results_report.form.date_to = today
    >>> generate_results_report.form.laboratory = laboratory
    >>> generate_results_report.form.generation_type = 'aut'
    >>> generate_results_report.execute('search')
    >>> generate_results_report.execute('generate')
    >>> results_report_version, = generate_results_report.actions[0]
    >>> results_report_version.click('revise')
    >>> results_report_version.state
    'revised'
    >>> results_report_version.click('release')
    >>> results_report_version.state
    'released'

Validate "failed" Test::

    >>> test.reload()
    >>> test.click('manager_validate')
    >>> test.state
    'failed'

Take a second sample::

    >>> take_sample = Wizard('lims.take.sample', [lot])
    >>> take_sample.form.label = 'LBL-002'
    >>> take_sample.execute('confirm')
    >>> take_sample.execute('end')
    >>> take_sample.state
    'end'

Create a second quality test::

    >>> Sample = Model.get('lims.sample')
    >>> sample, = Sample.find([
    ...     ('lot', '=', lot),
    ...     ('label', 'like', 'LBL-002%'),
    ...     ])
    >>> create_test = Wizard('lims.create.quality.test', [sample])
    >>> create_test.form.product, = test_product.products
    >>> create_test.execute('confirm')
    >>> test, = create_test.actions[0]
    >>> test.click('confirm')
    >>> test.state
    'confirmed'
    >>> len(test.lines)
    4

Create second Planification::

    >>> planification = Planification()
    >>> planification.laboratory = laboratory
    >>> planification.start_date = today
    >>> planification.date_from = today
    >>> planification.date_to = today
    >>> planification.analysis.append(Analysis(typification_1.analysis.id))
    >>> planification.analysis.append(Analysis(typification_2.analysis.id))
    >>> planification.analysis.append(Analysis(typification_3.analysis.id))
    >>> planification.analysis.append(Analysis(typification_4.analysis.id))
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
    >>> planification.state
    'preplanned'
    >>> len(planification.analysis)
    4

    >>> for f in planification.details:
    ...     for s in f.details:
    ...         s.staff_responsible.append(Professional(professional.id))
    >>> planification.save()
    >>> planification.reload()
    >>> technicians_qualification = Wizard(
    ...     'lims.planification.technicians_qualification', [planification])
    >>> _ = planification.click('confirm')
    >>> planification.state
    'confirmed'

Add results and check success in lines::

    >>> quantitavive_results = {
    ...     typification_1: '5.0',
    ...     typification_2: '3.0',
    ...     }
    >>> qualitative_results = {
    ...     typification_3: 'Valid',
    ...     typification_4: 'Valid',
    ...     }
    >>> for line in test.lines:
    ...     if line.typification in [typification_1, typification_2]:
    ...         line.result = quantitavive_results[line.typification]
    ...     if line.typification in [typification_3, typification_4]:
    ...         qualitative_value, = QualitativeValue.find([
    ...             ('name', '=', qualitative_results[line.typification]),
    ...             ('analysis', '=', line.analysis),
    ...             ])
    ...         line.qualitative_value = qualitative_value
    ...     line.end_date = today
    ...     line.accepted = True
    ...     line.save()
    ...     line.success
    True
    True
    True
    True

Create second results report::

    >>> generate_results_report = Wizard('lims.generate_results_report')
    >>> generate_results_report.form.date_from = today
    >>> generate_results_report.form.date_to = today
    >>> generate_results_report.form.laboratory = laboratory
    >>> generate_results_report.form.generation_type = 'aut'
    >>> generate_results_report.execute('search')
    >>> generate_results_report.execute('generate')
    >>> results_report_version, = generate_results_report.actions[0]
    >>> results_report_version.click('revise')
    >>> results_report_version.state
    'revised'
    >>> results_report_version.click('release')
    >>> results_report_version.state
    'released'

Validate "success" Test::

    >>> test.reload()
    >>> test.click('manager_validate')
    >>> test.state
    'successful'
