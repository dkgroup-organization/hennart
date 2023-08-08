# -*- coding: utf-8 -*-
from odoo import fields, models, api

class PurchasePromotion(models.Model):
    _name = "purchase.promotion"
    _description = "Purchase Promotion"

    name = fields.Char("Comment")
    date_start = fields.Datetime('Starting Date')
    date_end = fields.Datetime('End Date')
    product_id = fields.Many2one('product.product', 'Product', required=True, domain=[("purchase_ok", "=", True)])
    supplier_id = fields.Many2one('res.partner', 'Supplier', domain=[('parent_id', '=', False)], required=True)
    discount = fields.Float('Discount')

