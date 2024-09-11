# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################

from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'


    def action_create_invoice(self):
        """ Create invoice from picking """
        all_invoices = self.env['account.move']

        for picking in self:
            if picking.state == 'done':
                sale = picking.group_id.sale_id
                invoices = sale.create_custom_invoice()
                invoices.picking_ids |= picking
                all_invoices |= invoices

        return all_invoices

    def button_print_invoice(self, report_name="account.report_invoice"):
        """ Create invoice, and print pdf """
        invoices = self.action_create_invoice()
        invoice_ids = []
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
            else:
                continue

            partner = picking.partner_id
            if partner.parent_id and not partner.is_company:
                partner = partner.parent_id

            if partner.print_invoice:
                picking.button_print_invoice()
                message += 'Invoice is printing'

        return message


