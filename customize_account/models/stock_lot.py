
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from collections import defaultdict
import datetime
import time



class StockLot(models.Model):
    _inherit = 'stock.lot'

    invoice_lot_line_ids = fields.One2many('account.move.line.lot', 'lot_id', string='Invoicing line')

    unit_weight = fields.Float('Weight', compute='_compute_value', store=True)
    unit_price = fields.Monetary('Unit price', compute='_compute_value', store=True,
                                 groups='stock.group_stock_manager')


    def compute_cost_price(self):
        """ return cost price and weight by lot """
        uom_weight = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()

        for lot in self:
            # Calcul du prix moyen pondéré
            total_cost = 0.0
            total_quantity = 0.0
            total_weight = 0.0

            for line in lot.invoice_lot_line_ids:
                if line.product_uom_id == uom_weight:
                    total_quantity += line.uom_qty
                    total_weight += line.quantity
                else:
                    total_quantity += line.quantity
                    total_weight += line.weight

                if line.account_move_line_id.uom_qty:
                    total_cost += line.account_move_line_id.price_subtotal * line.uom_qty / line.account_move_line_id.uom_qty

            if total_quantity:
                lot.unit_weight = total_weight / total_quantity
                lot.unit_price = total_cost / total_quantity
            else:
                lot.unit_weight = lot.product_id.weight

                if lot.product_id.uos_id == uom_weight:
                    lot.unit_price = lot.product_id.average_cost_price * lot.product_id.weight
                else:
                    lot.unit_price = lot.product_id.average_cost_price
