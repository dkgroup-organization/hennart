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

    product_id = fields.Many2one('product.product', related='product_tmpl_id.product_variant_id', store=True, index=True)
    packaging = fields.Many2one('product.packaging',
                                'Packaging',help="It specifies attributes of packaging like type, quantity of packaging,etc.")
    product_uos = fields.Many2one("uom.uom", string="Invoicing unit")
    pricelist_ids = fields.One2many("product.supplierinfo.historic", "suppinfo_id", "Supplier Pricelist",readonly=True)

    package_domain = fields.Binary(string="Package domain", compute="_compute_package_domain")
    no_purchase = fields.Boolean('Stop Purchase', help="""Select this option if you want stopping to purchase 
    this product from this supplier""")

    @api.depends('company_id.multi_vat_foreign_country_ids', 'company_id.account_fiscal_country_id')
    def _compute_tag_ids_domain(self):
        for rep_line in self:
            allowed_country_ids = (False, rep_line.company_id.account_fiscal_country_id.id, *rep_line.company_id.multi_vat_foreign_country_ids.ids,)
            rep_line.tag_ids_domain = [('applicability', '=', 'taxes'), ('country_id', 'in', allowed_country_ids)]

    @api.depends('product_tmpl_id')
    def _compute_package_domain(self):
        """ return domain to use on package"""
        for package in self:
            product_ids = self.env['product.product']
            if package.product_tmpl_id:
                product_ids |= package.product_tmpl_id.product_variant_ids
            package.package_domain = [('product_id', 'in', product_ids.ids)]

    @api.onchange('type','discount1','discount2','base_price')
    def _get_price(self):
        for rec in self:
            if rec.type == 'add':
                rec.price = rec.base_price * (1 - ((rec.discount1 + rec.discount2) / 100.0))
            else:
                rec.price = rec.base_price * (1 - (rec.discount1 / 100.0)) * (1 - (rec.discount2 / 100.0))

    def add_priceinfo(self):
        self.pricelist_ids = [(0, 0, {
            'suppinfo_id': self.id,
            'min_quantity': self.min_qty,
            'price': self.price,
            'date_start': self.date_start,
            'date_end': self.date_end,
            'unit_price': self.base_price,
            'discount1': self.discount1,
            'discount2': self.discount2,
        })]
