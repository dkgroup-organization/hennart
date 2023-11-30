# -*- coding: utf-8 -*-


from odoo import api, fields, models, tools, _


class ProductCategory(models.Model):
    _inherit = "product.category"

    tracking = fields.Selection([
        ('serial', 'By Unique Serial Number'),
        ('lot', 'By Lots'),
        ('none', 'No Tracking')],
        string="Tracking", required=True, default='lot', precompute=False,
        help="Ensure the traceability of a storable product in your warehouse.")

    detailed_type = fields.Selection([
        ('product', 'Product'),
        ('consu', 'Consumable'),
        ('service', 'Service')],
        string="type", default='product')

    type = fields.Selection(related="detailed_type", string="type")

    use_expiration_date = fields.Boolean("Use expiration date", default=True)

    @api.onchange('tracking', 'detailed_type', 'use_expiration_date')
    def onchange_detailed_type(self):
        """ change the configuration"""
        # Force update on product template
        query_list = [
            "update product_template pt set tracking = pc.tracking from  product_category pc where pt.categ_id = pc.id and pt.tracking != pc.tracking",
            "update product_template pt set type = pc.type from  product_category pc where pt.categ_id = pc.id and pt.type != pc.type",
            "update product_template pt set detailed_type = pc.detailed_type from  product_category pc where pt.categ_id = pc.id and pt.detailed_type != pc.detailed_type",
            "update product_template pt set use_expiration_date = pc.use_expiration_date from  product_category pc where pt.categ_id = pc.id and pt.use_expiration_date != pc.use_expiration_date",
            ]
        for query in query_list:
            self.env.cr.execute(query)

        self.env['product.template'].invalidate_model()
        self.env['product.product'].invalidate_model()
        self.env['product.category'].invalidate_model()

        all_ids = self.env['product.template'].search([('categ_id', 'in', self.ids)])
        all_ids.update_categ_value()





