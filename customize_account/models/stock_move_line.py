# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import OrderedSet, groupby
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from collections import Counter, defaultdict

class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    invoice_name = fields.Char('Facture', compute='get_invoice_name')

    def get_invoice_name(self):
        """ Add information to move line """
        for move_line in self:
            invoice_name = ''
            account_lot_ids = self.env['account.move.line.lot'].search([
                ('stock_move_line_id', '=', move_line.id)
            ])
            for account_lot in account_lot_ids:
                if account_lot.account_move_line_id:
                    invoice_name += f'{account_lot.account_move_line_id.move_id.name} {account_lot.account_move_line_id.move_id.invoice_date} '
            move_line.invoice_name = invoice_name

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
                        if move.product_uos == uom_weight and not move.purchase_line_id:
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
