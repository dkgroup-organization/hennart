# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################

from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    shipping_weight = fields.Float('Shipping Weight', compute='_compute_shipping_weight', store=True, readonly=False)

    @api.depends('weight')
    def _compute_shipping_weight(self):
        coef_shipping_weight = float(self.env["ir.config_parameter"].sudo().get_param("customize_account.coef_shipping_weight", '1.1'))

        for rec in self:
            rec.shipping_weight = rec.weight * coef_shipping_weight


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

    def print_chronopost(self):
        """ print label """
        for picking in self:
            if picking.carrier_id.delivery_type == 'chronopost':
                attachment_ids = self.env['ir.attachment'].search([
                    ('res_model', '=', 'stock.picking'), ('res_id', '=', picking.id), ('name', 'ilike', '%Chronopost%')])
                if not attachment_ids:
                    if picking.sscc_line_ids:
                        res = picking.carrier_id.chronopost_send_shipping(self)
                        carrier_tracking_ref = ''
                        for item in res:
                            if item:
                                carrier_tracking_ref += ','
                            carrier_tracking_ref += item.get('tracking_number')
                else:
                    # Print label
                    if picking.carrier_id.cpst_printer_id:
                        printer = picking.carrier_id.cpst_printer_id
                        doc_format = picking.carrier_id.cpst_label_format
                        for attachment in attachment_ids:
                            printer.print_document(
                                report=picking.carrier_id,
                                content=attachment.datas,
                                doc_format=doc_format,
                                action='server', tray='Main')

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