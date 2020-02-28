# This file is part of lims_device_maintenance module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

try:
    from \
        trytond.modules.lims_device_maintenance.tests.test_device_maintenance \
        import suite
except ImportError:
    from .test_device_maintenance import suite

__all__ = ['suite']
