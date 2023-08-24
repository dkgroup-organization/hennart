# -*- coding: utf-8 -*-
from odoo import fields, models, api

class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    default_code = fields.Char('Code', related="product_id.default_code")
    weight_manual = fields.Float("Weight manual")
    weight = fields.Float("Weight", compute='get_move_line_weight', digits='Stock Weight', store=True, compute_sudo=True)
    picking_type_code = fields.Selection('Type', related="picking_type_id.code", store=True, index=True)

    @api.depends('weight_manual', 'qty_done', 'reserved_uom_qty')
    def get_move_line_weight(self):
        for move_line in self:
            weight = 0.0
            if move_line.weight_manual > 0.0:
                weight = move_line.weight_manual
            elif move_line.product_id.weight > 0.0:
                weight = (move_line.qty_done or move_line.reserved_uom_qty) * move_line.product_id.weight

            move_line.weight = weight
