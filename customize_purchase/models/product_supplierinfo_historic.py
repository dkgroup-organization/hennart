# -*- coding: utf-8 -*-
from odoo import fields, models, api

class PricelistPartnerinfo(models.Model):
    _name = 'product.supplierinfo.historic'
    _description = "Historic of supplier price change"
    _order = 'min_quantity asc'

    name = fields.Char('Description', size=64)
    suppinfo_id = fields.Many2one('product.supplierinfo', 'Partner Information', required=True, ondelete='cascade')
    min_quantity = fields.Float('Quantity', required=True, help="The minimal quantity to trigger this rule, expressed in the supplier Unit of Measure if any or in the default Unit of Measure of the product otherrwise.")
    price = fields.Float('Purchase Price', required=True, digits='Purchase Product Price', help="This price will be considered as a price for the supplier Unit of Measure if any or the default Unit of Measure of the product otherwise")
    date_start = fields.Date('Start date')
    date_end = fields.Date('End date')
    unit_price = fields.Float('Unit Price', digits='Purchase Product Price')
    discount1 = fields.Float('R1 %', digits='Discount')
    discount2 = fields.Float('R2 %', digits='Discount')
