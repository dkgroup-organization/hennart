from base64 import b64decode
from io import BytesIO
from logging import getLogger

from PIL import Image

from odoo import api, models

try:
    from PyPDF2 import PdfFileWriter, PdfFileReader
    from PyPDF2.utils import PdfReadError
except ImportError:
    pass

logger = getLogger(__name__)
logger.setLevel('DEBUG')

class Report(models.Model):
    _inherit = "ir.actions.report"

    def render_qweb_pdf(self, res_ids=None, data=None):
        if not self.env.context.get("res_ids"):
            return super(Report, self.with_context(res_ids=res_ids)).render_qweb_pdf(
                res_ids=res_ids, data=data
            )
        return super(Report, self).render_qweb_pdf(res_ids=res_ids, data=data)

    @api.model
    def _run_wkhtmltopdf(
        self,
        bodies,
        report_ref=False,
        header=None,
        footer=None,
        landscape=False,
        specific_paperformat_args=None,
        set_viewport_size=False,
    ):
        logger.debug("Running wkhtmltopdf with report_ref: %s", report_ref)
        result = super(Report, self)._run_wkhtmltopdf(
            bodies,
            report_ref=report_ref,
            header=header,
            footer=footer,
            landscape=landscape,
            specific_paperformat_args=specific_paperformat_args,
            set_viewport_size=set_viewport_size,
        )
        docids = self.env.context.get("res_ids", False)
        report_sudo = self._get_report(report_ref)
        watermark = None
        logger.debug("Document IDs: %s", docids)

        if self.env.company.cgv_binary:
            watermark = b64decode(self.env.company.cgv_binary)

        if not watermark:
            return result

        report = self._get_report(report_ref)
        report_name = report.report_name if report else self.name
        logger.debug("PDF generation completed, checking report name: %s", report_name)
        expected_reports = [
            'Factures avec Attachements',
            'Factures avec CGV',
            'report_merge_cgv.report_invoice_with_cgv'
        ]

        if report_name not in expected_reports:
            logger.debug("Report name does not match, returning generated PDF")
            return result

        if watermark:
            logger.debug("Found CGV attachment for company")
            return self.merge_pdf_with_watermark(result, watermark)
        
        logger.debug("No watermark found or not applicable, returning original PDF")
        return result

    def merge_pdf_with_watermark(self, pdf_content, watermark):
        pdf = PdfFileWriter()
        source_pdf = PdfFileReader(BytesIO(pdf_content))
        watermark_pdf = PdfFileReader(BytesIO(watermark))


        for page in source_pdf.pages:
            pdf.addPage(page)


        try:
            for page in watermark_pdf.pages:
                pdf.addPage(page)
            logger.debug("Watermark PDF added successfully")
        except PdfReadError:
            logger.debug("Failed to read watermark PDF")
            return pdf_content

        output = BytesIO()
        pdf.write(output)
        return output.getvalue()