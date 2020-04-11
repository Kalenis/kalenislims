# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
try:
    from trytond.modules.lims_quality_control.tests.test_lims_quality_control \
        import suite
except ImportError:
    from .test_lims_quality_control import suite

__all__ = ['suite']
