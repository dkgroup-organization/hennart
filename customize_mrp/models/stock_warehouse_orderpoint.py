# -*- coding: utf-8 -*-


from odoo import api, fields, models, tools, _
from odoo.tools.float_utils import float_round, float_is_zero


class StockWarehouseOrderpoint(models.Model):
    """ Defines Minimum stock rules. """
    _inherit = "stock.warehouse.orderpoint"

    @api.model
    def create_bom_orderpoint(self):
        """ Create all default orderpoint for product to manufacture """
        route_mo = self.env.ref('mrp.route_warehouse0_manufacture')
        bom_product_ids = self.env['mrp.bom'].search([('type', '=', 'normal')]).mapped('product_id')
        orderpoint_product_ids = self.env['stock.warehouse.orderpoint'].search([]).mapped('product_id')

        for product in bom_product_ids - orderpoint_product_ids:
            # Create order point
            vals_orderpoint = {
                'trigger': 'auto',
            }

        #set_A.difference(set_B)


