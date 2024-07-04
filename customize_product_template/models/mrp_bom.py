# -*- coding: utf-8 -*-


from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

class MrpBom(models.Model):
    """ Defines bills of material for a product or a product template """
    _inherit = 'mrp.bom'

    base_unit_count = fields.Float("Unit count", compute="compute_package", store=True)
    base_product_id = fields.Many2one("product.product", string="Unit product",
                                         compute="compute_package", store=True)

    @api.constrains('type', 'bom_line_ids')
    def _check_reserved_done_quantity(self):
        for bom in self:
            if bom.type == "phantom" and len(bom.bom_line_ids) > 1 :
                raise ValidationError(_('A KIT must have only one line of product.'))

    @api.depends('type', 'bom_line_ids.product_id', 'bom_line_ids.product_qty')
    def compute_package(self):
        """ Update type value"""
        for bom in self:
            if bom.type == "phantom" and bom.bom_line_ids:
                line = bom.bom_line_ids[0]
                bom.base_unit_count = line.product_qty
                bom.base_product_id = line.product_id
            else:
                bom.base_unit_count = 1.0
                bom.base_product_id = self.env['product.product']

class MrpBomLine(models.Model):
    """ Defines bills of material for a product or a product template """
    _inherit = 'mrp.bom.line'

    product_qty = fields.Float(
        'Quantity', default=1.0,
        digits='BOM line Unit of Measure', required=True)
