# -*- coding: utf-8 -*-


from odoo import api, fields, models, tools, _

class StockWarehouseOrderpoint(models.Model):
    """ Defines Minimum stock rules. """
    _inherit = "stock.warehouse.orderpoint"

    @api.model
    def get_min_qty(self, warehouse, product):
        """ return orderpoint for product to manufacture """

        location = warehouse.lot_stock_id
        order_point = self.env['stock.warehouse.orderpoint'].search(
            [('product_id', '=', product.id),
             ('warehouse_id', '=', warehouse.id)])

        if not order_point:
            order_point_vals = {'product_id': product.id, 'location_id': location.id, 'product_min_qty': 0.0,
                                'route_id': self.env.ref('mrp.route_warehouse0_manufacture').id, 'trigger': 'auto',
                                'qty_multiple': product.min_production_qty or 1.0,
                                'company_id': self.env.company.id or 1, 'visibility_days': 5.0}
            order_point = order_point.create(order_point_vals)

        min_qty = sum(order_point.mapped('product_min_qty')) or 0.0
        return min_qty