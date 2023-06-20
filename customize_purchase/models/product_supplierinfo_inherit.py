# -*- coding: utf-8 -*-
from odoo import fields, models, api

class ProductSupplierinfoInherit(models.Model):
    _inherit = 'product.supplierinfo'
    type = fields.Selection(string="Type of supplier info",selection=[('discount','Cascade discount'),('add','Add discount')],default="discount")
    discount1 = fields.Float("Discount 1",digits='Discount')
    discount2 = fields.Float("Discount 2",digits='Discount')
    base_price = fields.Float("Base price",digits='Purchase Product Price')
    price = fields.Float(
        'Price', default=0.0, digits='Purchase Product Price',store=True,
        required=True, help="The price to purchase a product")
    packaging = fields.Many2one('product.packaging', 'Packaging',help="It specifies attributes of packaging like type, quantity of packaging,etc.")
    product_uos = fields.Many2one("uom.uom", string="Invoicing unit")
    promotion = fields.Float("Promo %", digits='Discount')
    pricelist_ids = fields.One2many("product.supplierinfo.historic", "suppinfo_id", "Supplier Pricelist",readonly=True)


    @api.onchange('type','discount1','discount2','base_price')
    def _get_price(self):
        for rec in self:
            if rec.type == 'add':
                rec.price = rec.base_price * (1 - ((rec.discount1 + rec.discount2) / 100.0))
            else:
                rec.price = rec.base_price * (1 - (rec.discount1 / 100.0)) * (1 - (rec.discount2 / 100.0))


    def write(self, vals):
        if 'price' in vals:
            self.pricelist_ids=[(0, 0, {
                'suppinfo_id':self.id,
                'min_quantity':self.min_qty,
                'price':self.price,
                'date_start':self.date_start,
                'date_end':self.date_end,
                'unit_price':self.base_price,
                'discount1':self.discount1,
                'discount2': self.discount2,
            })]
        res = super(ProductSupplierinfoInherit, self).write(vals)
        return res




