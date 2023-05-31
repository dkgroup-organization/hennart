# -*- coding: utf-8 -*-


from odoo import api, fields, models, tools, _


class MrpBomLinev7(models.Model):
    """ import bills of material from a previews project in v7, only migration use
     product_product_bom: product_parent_id | product_child_id | product_qty
     product_packaging: ul | product_id | weight | sequence | ul_qty | qty | width | length | rows | height | weight_ul
                        |  product_parent_id
    """
    _name = 'mrp.bom.linev7'
    _description = "importation bom configuration"

    product_parent_id = fields.Many2one('product.product', string="Product parent")
    product_id = fields.Many2one('product.product', string="Product line")
    product_qty = fields.Float("Quantity", digits='BOM line Unit of Measure')

    ul = fields.Integer("Type of Package")
    weight = fields.Float("weight", digits='Stock Weight')
    sequence = fields.Integer("sequence", default=0)
    ul_qty = fields.Integer("Package by layer")
    width = fields.Float("width")
    length = fields.Float("length")
    rows = fields.Integer("Number of Layers")
    height = fields.Float("height")
    weight_ul = fields.Float("Empty Package Weight", digits='Stock Weight')

    bom_line_id = fields.Many2one("mrp.bom.line", string="BOM line")
    state = fields.Selection([('cancel', 'cancel'), ('draft', 'draft'), ('phantom', 'kit'), ('normal', 'normal')],
                             string="state", default="draft")

    def update_bom_line(self):
        """ Check and create BOM line"""
        for line in self:
            if line.state == "cancel":
                continue
            elif line.state == "draft":
                if line.sequence:
                    line.state = "phantom"
                else:
                    line.state = "normal"

            if not line.bom_line_id:
                bom_ids = self.env['mrp.bom'].search([('product_id', '=', line.product_parent_id.id)])
                if not bom_ids:
                    bom_vals = {
                        'product_id': line.product_parent_id.id,
                        'code': line.product_parent_id.default_code,
                        'product_tmpl_id': line.product_parent_id.product_tmpl_id.id,
                        'type': line.state,
                    }
                    bom = bom_ids.create(bom_vals)
                else:
                    bom = bom_ids[0]

                bom_line_ids = self.env['mrp.bom.line'].search(
                    [('bom_id', '=', bom.id),
                     '|',
                     ('product_id', '=', line.product_id.id),
                     ('product_tmpl_id', '=', line.product_id.product_tmpl_id.id)])
                if not bom_line_ids:
                    bom_line_vals = {
                        'bom_id': bom.id,
                        'product_id': line.product_id.id,
                        'product_uom_id': line.product_id.uom_id.id,
                        'product_qty': line.product_qty
                    }
                    bom_line = bom_line_ids.create(bom_line_vals)
                    line.bom_line_id = bom_line
                else:
                    line.bom_line_id = bom_line_ids[0]

            elif line.product_qty == line.bom_line_id.product_qty and line.product_id == line.bom_line_id.product_id:
                continue
            else:
                line.bom_line_id.product_qty = line.product_qty
                line.bom_line_id.product_id = line.product_id

