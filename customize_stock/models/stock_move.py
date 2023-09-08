# -*- coding: utf-8 -*-
from odoo import fields, models, api
import logging
import datetime

_logger = logging.getLogger(__name__)

class StockMove(models.Model):
    _inherit = "stock.move"

    default_code = fields.Char('Code', related="product_id.default_code")
    product_packaging_qty = fields.Float('Packaging Quantity')
    weight_manual = fields.Float("Weight manual")
    weight = fields.Float(compute='get_move_weight', digits='Stock Weight', store=True, compute_sudo=True)

    prodlot_inv = fields.Char(string='Supplier N° lot')
    picking_type_use_create_lots = fields.Boolean(related='picking_type_id.use_create_lots', readonly=True)

    lot_description = fields.Html("Lot description", compute="get_lot_description")
    lot_expiration_date = fields.Datetime(
        string='Expiration Date', compute='_compute_expiration_date', store=True,
        help='This is the date on which the goods with this Serial Number may'
             ' become dangerous and must not be consumed.')

    def get_lot_description(self):
        """ Get lot description"""
        for move in self:
            move.lot_description = ""

    def write(self, vals):
        res = super().write(vals)
        if 'prodlot_inv' in vals or 'lot_expiration_date' in vals:
            if not self.move_line_ids:
                self.move_line_ids = [(0, 0, {
                    'lot_name': self.prodlot_inv,
                    'expiration_date': self.lot_expiration_date
                    })]
            elif (self.move_line_ids and len(self.move_line_ids) == 1):
                for move in self.move_line_ids:
                    move.lot_name = self.prodlot_inv
                    move.expiration_date = self.lot_expiration_date
        return res

    @api.depends('state', 'product_id', 'product_uom_qty', 'product_uom', 'weight_manual', 'move_line_ids.weight')
    def get_move_weight(self):
        for move in self:
            if move.state == 'cancel':
                move.weight = 0.0
                move.weight_manual = 0.0
                continue

            weight = 0.0
            if move.weight_manual > 0.00:
                weight = move.weight_manual
            elif move.move_line_ids and move.move_line_ids.filtered(lambda lines: lines.weight > 0.00):
                # TODO: Check if state cancel exist on stock.move.line
                weight = sum(move.move_line_ids.filtered(lambda lines: lines.weight > 0.00).mapped('weight'))
            elif move.product_id.weight > 0.0:
                if move.state == "done":
                    move.weight_manual = weight = (move.quantity_done * move.product_id.weight)
                else:
                    weight = (move.product_qty * move.product_id.weight)
            move.weight = weight

