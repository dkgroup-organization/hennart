# -*- coding: utf-8 -*-


from odoo import api, fields, models, tools, _


class ProductCategory(models.Model):
    _inherit = "product.category"

    tracking = fields.Selection([
        ('serial', 'By Unique Serial Number'),
        ('lot', 'By Lots'),
        ('none', 'No Tracking')],
        string="Tracking", required=True, default='lot',
        help="Ensure the traceability of a storable product in your warehouse.")

    detailed_type = fields.Selection([
        ('product', 'Product'),
        ('consu', 'Consumable'),
        ('service', 'Service')],
        string="type", default='product')

    type = fields.Selection([
        ('product', 'Product'),
        ('consu', 'Consumable'),
        ('service', 'Service')],
        string="type", default='product')

    use_expiration_date = fields.Boolean("Use expiration date", default=True)

    @api.onchange('tracking', 'detailed_type', 'use_expiration_date')
    def onchange_detailed_type(self):
        """ change the configuration"""
        all_ids = self.env['product.template'].search([('categ_id', 'in', self.ids)])
        all_ids.update_categ_value()

