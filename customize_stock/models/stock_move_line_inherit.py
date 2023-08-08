# -*- coding: utf-8 -*-
from odoo import fields, models, api

class StockMoveLineInherit(models.Model):
    _inherit = "stock.move.line"

    weight_manual = fields.Float("Weight manual")
    weight = fields.Float(compute='_cal_move_line_weight', digits='Stock Weight', store=True, compute_sudo=True)

    @api.depends('weight_manual')
    def _cal_move_line_weight(self):
        for move_line in self:
            weight = 0.0
            if (move_line.weight_manual > 0.00):
                weight = move_line.weight_manual
            elif (move_line.product_id.weight > 0.0):
                weight = (move_line.reserved_uom_qty * move_line.product_id.weight)
            move_line.weight = weight
