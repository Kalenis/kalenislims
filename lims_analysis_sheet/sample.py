# This file is part of lims_analysis_sheet module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.i18n import gettext


class Entry(metaclass=PoolMeta):
    __name__ = 'lims.entry'

    @classmethod
    def confirm(cls, entries):
        cls.check_analysis_sheet_templates(entries)
        super().confirm(entries)

    @classmethod
    def check_analysis_sheet_templates(cls, entries):
        '''Report, before confirming, every analysis that would end up
        without an analysis sheet or with a sheet that has no columns'''
        pool = Pool()
        Fraction = pool.get('lims.fraction')
        EntryDetailAnalysis = pool.get('lims.entry.detail.analysis')
        Template = pool.get('lims.template.analysis_sheet')

        missing, not_ready = set(), set()
        for entry in entries:
            # Same fractions Entry._confirm() is about to confirm
            fractions = Fraction.search([
                ('entry', '=', entry.id),
                ('confirmed', '=', False),
                ])
            if not fractions:
                continue
            details = EntryDetailAnalysis.search([
                ('service.fraction', 'in', [f.id for f in fractions]),
                ('plannable', '=', True),
                ('state', '!=', 'annulled'),
                ])
            for detail in details:
                sample = detail.service.fraction.sample
                template_id = Template.get_template(detail.analysis.id,
                    detail.method and detail.method.id or None,
                    sample.product_type and sample.product_type.id or None,
                    sample.matrix and sample.matrix.id or None)
                if template_id:
                    template = Template(template_id)
                    if not template.interface_ready():
                        not_ready.add((template.rec_name,
                            template.interface.rec_name))
                elif detail.analysis_sheet_required():
                    missing.add((
                        detail.analysis.rec_name,
                        detail.method and detail.method.rec_name or '-',
                        sample.product_type and sample.product_type.rec_name
                        or '-',
                        sample.matrix and sample.matrix.rec_name or '-',
                        ))

        errors = []
        if not_ready:
            errors.append(gettext(
                'lims_analysis_sheet.msg_entry_interfaces_not_ready',
                templates='\n'.join('%s (%s)' % t for t in sorted(not_ready))))
        if missing:
            errors.append(gettext(
                'lims_analysis_sheet.msg_missing_analysis_sheet_template',
                lines='\n'.join(' / '.join(m) for m in sorted(missing))))
        if errors:
            raise UserError('\n\n'.join(errors))


class EntryDetailAnalysis(metaclass=PoolMeta):
    __name__ = 'lims.entry.detail.analysis'

    def analysis_sheet_required(self):
        'Whether this analysis must be worked on an analysis sheet'
        if self.analysis.no_analysis_sheet:
            return False
        return bool(self.laboratory
            and self.laboratory.analysis_sheet_required)


class EditFractionService(metaclass=PoolMeta):
    __name__ = 'lims.fraction.edit_service'

    def transition_confirm(self):
        result = super().transition_confirm()
        pool = Pool()
        Fraction = pool.get('lims.fraction')
        AnalysisSheet = pool.get('lims.analysis_sheet')
        for fraction in Fraction.browse(
                Transaction().context['active_ids']):
            AnalysisSheet.sync_fraction_after_service_change(fraction)
        return result


class EditSampleService(metaclass=PoolMeta):
    __name__ = 'lims.sample.edit_service'

    def transition_confirm(self):
        result = super().transition_confirm()
        pool = Pool()
        Sample = pool.get('lims.sample')
        AnalysisSheet = pool.get('lims.analysis_sheet')
        for sample in Sample.browse(
                Transaction().context['active_ids']):
            for fraction in sample.fractions:
                AnalysisSheet.sync_fraction_after_service_change(fraction)
        return result
