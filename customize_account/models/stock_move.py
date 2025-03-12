# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
import logging
from odoo.fields import Command
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.exceptions import UserError, ValidationError
_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    product_uos = fields.Many2one("uom.uom", compute="compute_product_uos", string="Invoicing unit")

    @api.depends('purchase_line_id', 'product_id')
    def compute_product_uos(self):
        """ Add compute uos information """
        for move in self:
            if move.purchase_line_id:
                move.product_uos = move.purchase_line_id.product_uos
            else:
                move.product_uos = move.product_id.uos_id
