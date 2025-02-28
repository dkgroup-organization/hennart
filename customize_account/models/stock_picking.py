# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################

from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError
import base64

class StockPicking(models.Model):
    _inherit = 'stock.picking'


    def action_create_invoice(self):
        """ Create invoice from picking """
        all_invoices = self.env['account.move']

        for picking in self:
            if picking.state == 'done':
                sale = picking.group_id.sale_id
                invoices = sale.sudo().create_custom_invoice()
                invoices.picking_ids |= picking
                for invoice in invoices:
                    if invoice.state == 'draft':
                        invoice.sudo().action_post()
                all_invoices |= invoices
        return all_invoices

    def button_print_invoice(self, report_name="account.report_invoice"):
        """ Create invoice, and print pdf """
        invoices = self.action_create_invoice()
        for picking in self:
            for invoice in invoices:
                if picking in invoice.picking_ids:
                    action_report = self.env['ir.actions.report'].search([('report_name', '=', report_name)])
                    action_report.print_document([invoice.id])

    def button_print_invoice_pick(self, report_name="customize_report.report_invoice_bl_valued"):
        """ Create invoice, and print pdf """
        invoices = self.action_create_invoice()
        for picking in self:
            for invoice in invoices:
                if picking in invoice.picking_ids:
                    action_report = self.env['ir.actions.report'].search([('report_name', '=', report_name)])
                    action_report.print_document([invoice.id])

    def preparation_end(self):
        """ Use partner configuration to finish and print invoice """
        message = ''
        for picking in self:
            if picking.preparation_state == 'done':
                message = _('End of preparation: ') + picking.name

            partner = picking.partner_id
            if partner.parent_id and not partner.is_company:
                partner = partner.parent_id

            if partner.print_picking:
                picking.sudo().with_delay().button_print_picking()
                message += _('Picking is printing\n')

            if partner.print_picking2:
                picking.sudo().with_delay().button_print_invoice_pick()
                message += _('Picking with price is printing\n')

            if partner.print_invoice:
                picking.sudo().with_delay().button_print_invoice()
                message += _('Invoice is printing\n')

            if picking.delivery_type == 'chronopost':
                picking.sudo().with_delay().print_chronopost()
                message += _('Chronopost label is printing\n')

        return message

    def action_send_invoice_and_delivery(self):
        """Envoie la facture et le bon de livraison au client par email."""
        return
        for picking in self:
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
                            'name': '%s.pdf' % invoice.name,
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

    def button_validate(self):
        """ compute the account value of lot """
        res = super().button_validate()
        lot_ids = self.env['stock.lot']
        lot_ids |= self.move_line_ids.lot_id
        lot_ids.sudo().compute_cost_price()
        return res