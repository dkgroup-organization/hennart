# -*- coding: utf-8 -*-


from odoo import api, fields, models, tools, _


class ProductProduct(models.Model):
    _inherit = 'product.product'

    package_quantity = fields.Float("Package quantity", compute="compute_package")
    package_product_id = fields.Many2one("product.product", string="Package product", compute="compute_package")

    def compute_package(self):
        """ Update type value"""
        for product in self:
            if product.bom_ids:
                bom = product.bom_ids[0]
                product.package_quantity = bom.package_quantity
                product.package_product_id = bom.package_product_id
            else:
                product.package_quantity = 1.0
                product.package_product_id = product