# This file is part of lims_project_study_plan module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import configuration
from . import project


def register():
    Pool.register(
        configuration.Configuration,
        configuration.ConfigurationSequence,
        configuration.LabWorkYear,
        configuration.LabWorkYearSequence,
        project.Project,
        project.Entry,
        project.ProjectReferenceElement,
        project.ProjectSolventAndReagent,
        project.ProjectSampleInCustody,
        project.ProjectDeviationAndAmendment,
        project.ProjectDeviationAndAmendmentProfessional,
        project.ProjectChangeLog,
        project.Sample,
        project.CreateSampleStart,
        project.ProjectProfessionalPosition,
        project.ProjectLaboratoryProfessional,
        project.Lot,
        project.ProjectReOpenStart,
        project.ProjectGLPReport03PrintStart,
        project.ProjectGLPReport05PrintStart,
        project.ProjectGLPReport10PrintStart,
        project.ProjectGLPReport12PrintStart,
        module='lims_project_study_plan', type_='model')
    Pool.register(
        project.CreateSample,
        project.ProjectReOpen,
        project.ProjectGLPReport03Print,
        project.ProjectGLPReport05Print,
        project.ProjectGLPReport10Print,
        project.ProjectGLPReport12Print,
        module='lims_project_study_plan', type_='wizard')
    Pool.register(
        project.ProjectGLPReport01,
        project.ProjectGLPReport02,
        project.ProjectGLPReport03,
        project.ProjectGLPReport04,
        project.ProjectGLPReport05,
        project.ProjectGLPReport06,
        project.ProjectGLPReport07,
        project.ProjectGLPReport08,
        project.ProjectGLPReport09,
        project.ProjectGLPReport10,
        project.ProjectGLPReport11,
        project.ProjectGLPReport12,
        project.ProjectGLPReport13,
        project.ProjectGLPReportStudyPlan,
        project.ProjectGLPReportFinalRP,
        project.ProjectGLPReportFinalFOR,
        project.ProjectGLPReportAnalyticalPhase,
        module='lims_project_study_plan', type_='report')
