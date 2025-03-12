# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    def check_line(self):
        """ check if all line has production lot information
            Add the purchase case (some time the purchase invoicing unit is not the sale invoicing unit
        """
        uom_weight = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
        message = ""

        for move in self:
            if move.picking_id.picking_type_code == 'incoming':
                for move_line in move.move_line_ids:

                    if move_line.state == "cancel":
                        continue
                    if not move_line.qty_done:
                        continue
                    move_line.to_weight = False

                    if move_line.weight == 0.0:
                        if move.product_uos == uom_weight:
                            message += _(f"\nThis line need a weight: {move.name}")
                        else:
                            move_line.weight = move_line.qty_done * move_line.product_id.weight

        if message:
            raise ValidationError(message)
        else:
            super().check_line()

    def get_to_weight(self):
        """ Check if the to_weight field has to be changed return dictionary
            Add the purchase case (some time the purchase invoicing unit is not the sale invoicing unit
        """
        uom_weight = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
        res = super().get_to_weight()
        if self.move_id.product_uos == uom_weight:
            res['to_weight'] = True
        return res
    