
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from collections import defaultdict
import datetime
import time



class StockLot(models.Model):
    _inherit = 'stock.lot'

    invoice_lot_line_ids = fields.One2many('account.move.line.lot', 'lot_id', string='Invoicing line')
    categ_id = fields.Many2one('product.category', related='product_id.categ_id', store=True, index=True)
    uos_id = fields.Many2one('uom.uom', related='product_id.uos_id', string='Unit of Sale')


    def compute_cost_price(self):
        """ return cost price and weight by lot """
        uom_weight = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()

        for lot in self:
            # Calcul du prix moyen pondéré
            total_cost = 0.0
            total_quantity = 0.0
            total_weight = 0.0

            if lot.invoice_lot_line_ids:
                for line in lot.invoice_lot_line_ids:
                    account_move_line = line.account_move_line_id
                    # Check if invoice purchase
                    if account_move_line.move_id.move_type in ['in_invoice']:
                        if account_move_line.product_uom_id == uom_weight:
                            total_quantity += account_move_line.uom_qty
                            total_weight += account_move_line.quantity
                        else:
                            total_quantity += account_move_line.quantity
                            total_weight += account_move_line.weight
                        total_cost += account_move_line.price_subtotal
            else:
                # check if there is purchase
                purchase_line_ids = self.env['purchase.order.line']
                move_line_ids = self.env['stock.move.line']. search([('lot_id', '=', lot.id), ('picking_type_code', '=', 'incoming')])
                purchase_line_ids |= move_line_ids.move_id.purchase_line_id
                for purchase_line in purchase_line_ids:
                    total_quantity += purchase_line.product_qty
                    total_weight += purchase_line.weight
                    total_cost += purchase_line.price_subtotal

            if total_weight and total_quantity:
                lot.unit_weight = total_weight / total_quantity
            if total_cost and total_quantity:
                lot.unit_price = total_cost / total_quantity
            if total_cost and total_weight:
                lot.kg_price = total_cost / total_weight




