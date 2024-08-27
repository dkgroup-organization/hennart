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
                invoices.update_lot()
                invoices.action_post()
                all_invoices |= invoices

        return all_invoices

    def button_print_invoice(self, report_name="account.report_invoice"):
        """ Create invoice, and print pdf """
        invoices = self.action_create_invoice()
        action_report = self.env['ir.actions.report'].search([('report_name', '=', report_name)])
        action_report.print_document(invoices.ids)




