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

    type = fields.Selection([
        ('product', 'Product'),
        ('consu', 'Consumable'),
        ('service', 'Service')],
        string="type", compute="update_type", default='product', store=True)

    detailed_type = fields.Selection([
        ('product', 'Product'),
        ('consu', 'Consumable'),
        ('service', 'Service')],
        string="type", default="product")

    use_expiration_date = fields.Boolean("Use expiration date", default=True)

    @api.depends('detailed_type')
    def update_type(self):
        """ Update type value"""
        for categ in self:
            categ.type = categ.detailed_type

    @api.onchange('detailed_type')
    def onchange_detailed_type(self):
        """ change the configuration"""
        if self.detailed_type in ['service', 'consu']:
            self.tracking = 'none'
            self.use_expiration_date = False

    @api.onchange('tracking')
    def onchange_detailed_type(self):
        """ change the configuration"""
        if self.tracking == 'none':
            self.use_expiration_date = False
        else:
            self.tracking = 'lot'
            self.use_expiration_date = True
