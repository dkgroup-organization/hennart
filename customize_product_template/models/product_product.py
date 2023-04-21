# -*- coding: utf-8 -*-


from odoo import api, fields, models, tools, _


class ProductProduct(models.Model):
    _inherit = 'product.product'

    base_product_id = fields.Many2one("product.product", string="Unit product",
                                        compute="compute_base_product", store=True)
    base_unit_count = fields.Float('Unit Count', related='product_tmpl_id.base_unit_count', store=True,
        help="Number of unit in the package.")
    base_unit_price = fields.Float("Price Per Unit",  related='product_tmpl_id.base_unit_price',
        help="Price of unit in the package.")
    base_unit_name = fields.Char(compute='_compute_base_unit_name', related='product_tmpl_id.base_unit_name',
                                 help='Displays the custom unit for the products if defined or the selected unit of measure otherwise.')

    @api.depends('base_product_tmpl_id')
    def compute_base_product(self):
        for product in self:
            if not product.id:
                product.base_product_id = False
            elif product.bom_ids:
                bom = product.bom_ids[0]
                product.base_product_id = bom.base_product_id
            else:
                product.base_product_id = False

    def _get_base_unit_price(self, price):
        self.ensure_one()
        return self.base_unit_price