# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _
from datetime import timedelta, datetime


class ProductProduct(models.Model):
    _inherit = 'product.product'

    make_to_order = fields.Boolean('Make to order', compute="compute_make_to_order")

    @api.depends('to_personnalize')
    def compute_make_to_order(self):
        """ define the make to order specification """
        for product in self:
            product.make_to_order = product.to_personnalize

    def action_normal_mrp(self):
        """ compute the forescast quantity and create manufacture order """
        normal_bom = self.get_all_normal_bom()
        forcasting = normal_bom.product_id.get_forcasting()
        warehouse = self.env['stock.warehouse'].search([], limit=1)
        res = self.env['mrp.production']

        for product_id in list(forcasting.keys()):
            if forcasting[product_id]:
                product = self.env['product.product'].browse(product_id)
                res |= self.env['mrp.production'].create_forecast_om(warehouse, product, forcasting[product_id])

        return res

