# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)

class AccountMoveLineInherit(models.Model):
    _inherit = 'account.move.line'
    discount1 = fields.Float("R1 %")
    discount2 = fields.Float("R2 %")
    base_price = fields.Float("Base price")
    product_uos = fields.Many2one("uom.uom",string="Invoicing unit")
    weight = fields.Float('Weight')
    product_packaging_id = fields.Many2one('product.packaging', string='Packaging', domain="[('product_id', '=', product_id)]", check_company=True )
    product_packaging_qty = fields.Float('Packaging Quantity')
