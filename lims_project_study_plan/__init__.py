# This file is part of lims_project_study_plan module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from .configuration import *
from .project import *
from report import *
from wizard import *


def register():
    Pool.register(
        LimsConfiguration,
        LimsConfigurationSequence,
        LimsLabWorkYear,
        LimsLabWorkYearSequence,
        LimsProject,
        LimsEntry,
        LimsProjectReferenceElement,
        LimsProjectSolventAndReagent,
        LimsProjectSampleInCustody,
        LimsProjectDeviationAndAmendment,
        LimsProjectDeviationAndAmendmentProfessional,
        LimsProjectChangeLog,
        LimsSample,
        LimsCreateSampleStart,
        LimsProjectProfessionalPosition,
        LimsProjectLaboratoryProfessional,
        Lot,
        LimsProjectReOpenStart,
        LimsProjectGLPReport03PrintStart,
        LimsProjectGLPReport05PrintStart,
        LimsProjectGLPReport10PrintStart,
        LimsProjectGLPReport12PrintStart,
        module='lims_project_study_plan', type_='model')
    Pool.register(
        LimsCreateSample,
        LimsProjectReOpen,
        LimsProjectGLPReport03Print,
        LimsProjectGLPReport05Print,
        LimsProjectGLPReport10Print,
        LimsProjectGLPReport12Print,
        module='lims_project_study_plan', type_='wizard')
    Pool.register(
        LimsProjectGLPReport01,
        LimsProjectGLPReport02,
        LimsProjectGLPReport03,
        LimsProjectGLPReport04,
        LimsProjectGLPReport05,
        LimsProjectGLPReport06,
        LimsProjectGLPReport07,
        LimsProjectGLPReport08,
        LimsProjectGLPReport09,
        LimsProjectGLPReport10,
        LimsProjectGLPReport11,
        LimsProjectGLPReport12,
        LimsProjectGLPReport13,
        LimsProjectGLPReportStudyPlan,
        LimsProjectGLPReportFinalRP,
        LimsProjectGLPReportFinalFOR,
        LimsProjectGLPReportAnalyticalPhase,
        module='lims_project_study_plan', type_='report')
