

from odoo import _, api, fields, models
from odoo.tools import float_compare, float_is_zero
from collections import defaultdict

import logging
_logger = logging.getLogger(__name__)


class AccountMoveLineLot(models.Model):
    """ detailled lot on account.move.line
    """
    _name = "account.move.line.lot"
    _description = "Detailed lot"

    account_move_line_id = fields.Many2one('account.move.line', string='Account move line')

    product_id = fields.Many2one('product.product', string="product", related="account_move_line_id.product_id")
    stock_move_line_id = fields.Many2one('stock.move.line', string='stock move line')
    lot_id = fields.Many2one('stock.lot', string='Production lot')

    uom_qty = fields.Float(string="Qty")
    product_uom_id = fields.Many2one('uom.uom', string="Udv", related="account_move_line_id.product_uom_id")
    quantity = fields.Float(
        string='Quantity',
        digits='Product Unit of Measure',
        help="Invoiced quantity in kg or unit."
    )
    weight = fields.Float(
        string="Weight",
        digits='Stock Weight',
        required=True,
    )

    def update_lot_qty(self):
        """ get qty and lot"""
        pass