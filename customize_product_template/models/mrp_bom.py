# -*- coding: utf-8 -*-


from odoo import api, fields, models, tools, _


class MrpBom(models.Model):
    """ Defines bills of material for a product or a product template """
    _inherit = 'mrp.bom'

    package_quantity = fields.Float("Package quantity", compute="compute_package", store=True)
    package_product_id = fields.Many2one("product.product", string="Package product", compute="compute_package", store=True)

    @api.depends('bom_line_ids.product_id', 'bom_line_ids.product_qty')
    def compute_package(self):
        """ Update type value"""
        for bom in self:
            if bom.type == "phantom" and bom.bom_line_ids:
                line = bom.bom_line_ids[0]
                bom.package_quantity = line.product_qty
                bom.package_product_id = line.product_id
            else:
                bom.package_quantity = 0.0
                bom.package_product_id = self.env['product.product']


class MrpBomLine(models.Model):
    """ Defines bills of material for a product or a product template """
    _inherit = 'mrp.bom.line'

    product_qty = fields.Float(
        'Quantity', default=1.0,
        digits='BOM line Unit of Measure', required=True)