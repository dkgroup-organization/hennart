
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    weight = fields.Float(compute='wms_move_weight', digits='Stock Weight', store=True, compute_sudo=True)
    weight_manual = fields.Float(digits='Manual Weight')

    @api.depends('product_id', 'qty_done', 'weight_manual')
    def wms_move_weight(self):
        """ Define the weight by:
                - default product weight
                - manual entry
                - weighed device
        """
        for move in self:
            weight = 0.0
            if move.weight_manual:
                weight = move.weight_manual
            elif move.product_id.weight:
                weight = move.product_id.weight * move.qty_done
            else:
                weight = 0.0
            move.weight = weight
