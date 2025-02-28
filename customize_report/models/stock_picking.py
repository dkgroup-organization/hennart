# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################

from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'


    def button_print_picking(self, report_name="customize_report.report_delivery_hennart"):
        """ Create invoice, and print pdf """
        for picking in self:
            action_report = self.env['ir.actions.report'].sudo().search([('report_name', '=', report_name)])
            action_report.sudo().print_document([picking.id])

    def button_print_invoice(self, report_name="account.report_invoice"):
        """ Create invoice, and print pdf """
        invoices = self.action_create_invoice()
        for picking in self:
            for invoice in invoices:
                if picking in invoice.picking_ids:
                    action_report = self.env['ir.actions.report'].sudo().search([('report_name', '=', report_name)])
                    action_report.sudo().print_document([invoice.id])

    def button_print_invoice_pick(self, report_name="customize_report.report_invoice_bl_valued"):
        """ Create invoice, and print pdf """
        invoices = self.action_create_invoice()
        for picking in self:
            for invoice in invoices:
                if picking in invoice.picking_ids:
                    action_report = self.env['ir.actions.report'].sudo().search([('report_name', '=', report_name)])
                    action_report.sudo().print_document([invoice.id])