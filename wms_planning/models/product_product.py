# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _
from datetime import timedelta, datetime


class ProductProduct(models.Model):
    _inherit = 'product.product'

    make_to_order = fields.Boolean('Make to order')

    def get_all_bom(self):
        """ Get all bom of product with recursive search """
        all_bom = self.env['mrp.bom']
        for product in self:
            if product.bom_ids:
                bom = product.bom_ids[0]
                all_bom |= bom
                all_bom |= bom.bom_line_ids.product_id.get_all_bom()
        return all_bom

    def get_all_normal_bom(self):
        """ Get all bom of product with recursive search """
        all_bom = self.get_all_bom()
        res = self.env['mrp.bom']
        for bom in self:
            if bom.type == 'normal' and not bom.product_id.make_to_order:
                res |= bom
        return all_bom

    def get_all_make_to_order_bom(self):
        """ Get all bom of product with recursive search """
        all_bom = self.get_all_bom()
        res = self.env['mrp.bom']
        for bom in self:
            if bom.product_id.make_to_order:
                res |= bom
        return all_bom

    def get_forcasting(self):
        """ Compute the quantity forcast,
        return:
         {product_id: forecast_quantity, ...}
        """
        horizon_past = 5
        horizon_futur = 5
        all_warehouse = self.env['stock.warehouse'].search([])
        res = {}

        for product in self:
            res[product.id] = product.qty_available

            moves = self.env['stock.move'].search([
                    ('product_id', '=', product.id),
                    ('wh_filter', '=', True),
                    ('warehouse_id', 'in', all_warehouse.ids),
                    ('date', '>=', fields.Datetime.now() - timedelta(days=horizon_past)),
                    ('date', '<', fields.Datetime.now() + timedelta(days=horizon_futur))
                ])

            for warehouse in all_warehouse:
                for move in moves:
                    if move.location_dest_id.warehouse_id == warehouse:
                        res[product.id] += move.product_uom_qty
                    if move.location_id.warehouse_id == warehouse:
                        res[product.id] -= move.product_uom_qty

        for product_id in list(res.keys()):
            if res[product_id] < 0.0:
                res[product_id] = - res[product_id]
            else:
                res[product_id] = 0.0

        return res
