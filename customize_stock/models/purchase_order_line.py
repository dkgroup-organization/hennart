# -*- coding: utf-8 -*-
from odoo import fields, models, api

class PurchaseOrderLineInherit(models.Model):
    _inherit = 'purchase.order.line'

    weight_picking = fields.Float(compute='_compute_weight_picking', string='Weight received', store=True, readonly=True )

    @api.depends('move_ids.weight')
    def _compute_weight_picking(self):
        for line in self:
            weight = 0.0
            for move_line in line.move_ids:
                weight += move_line.weight
            line.weight_picking = weight

    def _prepare_account_move_line(self, move=False):
        rec = super(PurchaseOrderLineInherit, self)._prepare_account_move_line(move=False)
        rec.update({'weight': self.weight_picking,'': [(6, 0, self.move_ids.mapped('lot_ids').ids)]})
        return rec

