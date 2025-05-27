from odoo import models, fields ,api, _, SUPERUSER_ID
from odoo.exceptions import MissingError, UserError, ValidationError
import base64

class delivery_carrier_order(models.Model):

    _inherit = "delivery.carrier.order"


    def action_send_invoice_and_delivery(self):
        """Envoie la facture et le bon de livraison au client par email."""

        for order in self:
            for picking in order.picking_ids:
                invoices = self.env['account.move']
                attachment_ids = self.env['ir.attachment']

                
                partner = picking.partner_id
                if partner.parent_id and not partner.is_company:
                    partner = partner.parent_id

                if partner.invoice_auto:
                    invoices = picking.sudo().action_create_invoice()

                if partner.email_invoice:
                    for invoice in invoices:
                        # Générer les PDF pour la facture et le bon de livraison account.report_invoice
                        if not invoice.attachment_ids:
                            invoice_pdf, doc_format = self.env['ir.actions.report']._render_qweb_pdf(
                                'account.report_invoice', res_ids=invoice.ids)

                            invoice_attachment = self.env['ir.attachment'].create({
                                'name': f'{invoice.name}.pdf',
                                'type': 'binary',
                                'datas': base64.b64encode(invoice_pdf).decode('utf-8'),
                                'res_model': 'account.move',
                                'res_id': invoice.id,
                                'mimetype': 'application/pdf',
                            })
                        else:
                            invoice_attachment = invoice.attachment_ids
                        attachment_ids |= invoice_attachment

                # if partner.email_picking:
                #     # Générer les PDF pour chaque bon de livraison
                #     delivery_pdf, doc_format = self.env['ir.actions.report']._render_qweb_pdf(
                #         'stock.action_report_delivery', res_ids=picking.ids)
                #     delivery_attachment = self.env['ir.attachment'].create({
                #         'name': '%s.pdf' % picking.name,
                #         'type': 'binary',
                #         'datas': base64.b64encode(delivery_pdf).decode('utf-8'),
                #         'res_model': 'stock.picking',
                #         'res_id': picking.id,
                #         'mimetype': 'application/pdf',
                #     })
                #
                #     attachment_ids |= delivery_attachment

                if partner.email_invoice:
                    # Envoyer l'email
                    template = self.env.ref('account.email_template_edi_invoice')

                    if template:
                        email_values = {'attachment_ids': [(6, 0, attachment_ids.ids)]}
                        res = template.send_mail(invoices[0].id, email_values=email_values)