# -*- coding: utf-8 -*-


from odoo import api, fields, models, tools, _


class ProductProduct(models.Model):
    _inherit = 'product.product'

    base_product_id = fields.Many2one("product.product", string="base product",
                                        compute="compute_base_product", store=True)
    base_unit_count = fields.Float('Unit Count', compute="compute_base_product", store=True)
    base_unit_price = fields.Float("Price", compute="compute_base_product", store=True)
    base_unit_name = fields.Char('Name', compute="compute_base_product", store=True)
    lst_price = fields.Float("Product price", compute="compute_base_product", store=True)


    @api.depends('product_tmpl_id')
    def compute_base_product(self):
        """ NO variant """
        for product in self:
            product.base_product_id = product.product_tmpl_id.base_product_tmpl_id.product_variant_id
            product.base_unit_count = product.product_tmpl_id.base_unit_count
            product.base_unit_price = product.product_tmpl_id.base_unit_price
            product.lst_price = product.product_tmpl_id.list_price
            product.base_unit_name = product.product_tmpl_id.base_unit_name
