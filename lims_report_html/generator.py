# This file is part of lims_report_html module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from weasyprint import HTML, CSS


class PdfGenerator:

    def __init__(self, main_html, header_html=None, footer_html=None,
            base_url=None, side_margin=2, extra_vertical_margin=30,
            stylesheets=None, page_orientation='portrait'):
        self.main_html = main_html
        self.header_html = header_html
        self.footer_html = footer_html
        self.base_url = base_url
        self.side_margin = side_margin
        self.extra_vertical_margin = extra_vertical_margin
        self.stylesheets = stylesheets or []
        self.page_orientation = page_orientation

    @staticmethod
    def get_element(boxes, element):
        for box in boxes:
            if box.element_tag == element:
                return box
            return PdfGenerator.get_element(box.all_children(), element)

    def render_html(self):
        if self.header_html:
            header_body, header_height = self._compute_overlay_element(
                'header')
        else:
            header_body, header_height = None, 0

        if self.footer_html:
            footer_body, footer_height = self._compute_overlay_element(
                'footer')
        else:
            footer_body, footer_height = None, 0

        margins = '{header_size}px {side_margin} {footer_size}px {side_margin}'.format(
            header_size=header_height + self.extra_vertical_margin,
            footer_size=footer_height + self.extra_vertical_margin,
            side_margin='{}cm'.format(self.side_margin),
            )
        content_print_layout = ('@page {size: A4 %s; margin: %s;}' %
            (self.page_orientation,
            margins)
            )
        stylesheets = [CSS(string=content_print_layout)]
        for sheet in self.stylesheets:
            stylesheets.append(CSS(string=sheet or ''))

        html = HTML(
            string=self.main_html,
            base_url=self.base_url,
            )
        main_doc = html.render(stylesheets=stylesheets)

        if self.header_html or self.footer_html:
            self._apply_overlay_on_main(main_doc, header_body, footer_body)

        return main_doc

    def _compute_overlay_element(self, element: str):
        overlay_layout = (
            '@page {size: A4 %s; margin: 0;}' % self.page_orientation +
            '\nheader {position: fixed; width: 100%; top: 0;}' +
            '\nfooter {position: fixed; width: 100%; bottom: 0;}')
        stylesheets = [CSS(string=overlay_layout)]
        for sheet in self.stylesheets:
            stylesheets.append(CSS(string=sheet or ''))

        html = HTML(
            string=getattr(self, '{}_html'.format(element)),
            base_url=self.base_url,
            )
        element_doc = html.render(stylesheets=stylesheets)
        element_page = element_doc.pages[0]
        element_body = PdfGenerator.get_element(
            element_page._page_box.all_children(), 'body')
        element_body = element_body.copy_with_children(
            element_body.all_children())
        element_html = PdfGenerator.get_element(
            element_page._page_box.all_children(), element)

        if element == 'header':
            element_height = element_html.height
        if element == 'footer':
            element_height = element_page.height - element_html.position_y

        return element_body, element_height

    def _apply_overlay_on_main(self, main_doc,
            header_body=None, footer_body=None):
        for page in main_doc.pages:
            page_body = PdfGenerator.get_element(
                page._page_box.all_children(), 'body')
            if header_body:
                page_body.children += header_body.all_children()
            if footer_body:
                page_body.children += footer_body.all_children()
