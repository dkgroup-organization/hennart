

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
        store=True,
        digits='Product Unit of Measure',
        help="Invoiced quantity in kg or unit.",
        compute="compute_quantity"
    )
    weight = fields.Float(
        string="Weight",
        digits='Stock Weight',
        required=False,
    )
    state = fields.Selection([
        ('manual', 'Manual'),
        ('draft', 'draft'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')], default='manual',
        store=True, compute='_compute_state',
        copy=True)

    @api.depends('stock_move_line_id.state')
    def _compute_state(self):
        """ define state """
        for line in self:
            if line.stock_move_line_id:
                if line.stock_move_line_id.state in ['cancel', 'done']:
                    line.state = line.stock_move_line_id.state
                else:
                    line.state = 'draft'
            else:
                line.state = 'manual'

    @api.depends('product_uom_id', 'weight', 'uom_qty')
    def compute_quantity(self):
        """ get quantity by UDV"""
        uom_weight = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
        for line in self:
            if line.product_uom_id == uom_weight:
                line.quantity = line.weight
            else:
                line.quantity = line.uom_qty

    @api.onchange('stock_move_line_id')
    def onchange_stock_move_line_id(self):
        """ get qty and weight """
        if self.stock_move_line_id:
            self.uom_qty = self.stock_move_line_id.qty_done
            self.weight = self.stock_move_line_id.weight
            self.lot_id = self.stock_move_line_id.lot_id
