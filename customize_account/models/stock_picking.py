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
                        invoice.sudo().with_context(update_discount_stock=True).action_post()
                all_invoices |= invoices
        return all_invoices

    def preparation_end(self):
        """ Use partner configuration to finish and print invoice """
        message = ''
        for picking in self:
            if picking.preparation_state == 'done':
                message = _('End of preparation: ') + picking.name
        return message

    def button_validate(self):
        """ compute the account value of lot """
        change_product_uom_qty = {}
        for picking in self:
            if picking.picking_type_id.code == 'incoming':
                for move in picking.move_ids_without_package:
                    if move.product_uom_qty < move.quantity_done:
                        change_product_uom_qty[move] = move.product_uom_qty
                        move.product_uom_qty = move.quantity_done

        res = super().button_validate()

        for move in list(change_product_uom_qty.keys()):
            move.product_uom_qty = change_product_uom_qty.get(move, move.product_uom_qty)

        lot_ids = self.env['stock.lot']
        lot_ids |= self.move_line_ids.lot_id
        lot_ids.sudo().compute_cost_price()
        lot_ids.sudo().get_partner_supplier()
        return res

