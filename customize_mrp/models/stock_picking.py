# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################

from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError
from datetime import datetime, timedelta


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def get_production_bom(self):
        """ Return BOM used in this picking, only normal type BOM, recursive search """
        def get_all_bom(boms):
            """ return all bom in this bom """
            all_bom = self.env['mrp.bom']
            for bom in boms:
                for line in bom.bom_line_ids:
                    if line.product_id.bom_ids:
                        for sub_bom in line.product_id.bom_ids:
                            all_bom |= get_all_bom(sub_bom)
            all_bom |= boms
            return all_bom

        bom_todo = self.env['mrp.bom']
        res = self.env['mrp.bom']
        # list the BOM to do
        for picking in self:
            if picking.state in ['cancel', 'done']:
                continue
            for move in picking.move_ids_without_package:
                if move.product_id.bom_ids:
                    bom_todo |= get_all_bom(move.product_id.bom_ids)

        for bom in bom_todo:
            if bom.type == 'kit' or bom.product_id.to_personnalize:
                continue
            res |= bom

        return res

    def action_mrp(self):
        """ Check if all product with BOM need manufacture, recursive analyse """
        bom_todo = self.get_production_bom()
        # In this case only one warehouse
        warehouse = self.env['stock.warehouse'].search([], limit=1)

        # list or create the order point
        order_point = self.env['stock.warehouse.orderpoint']
        for bom in bom_todo:

            product = bom.product_id
            product_min_qty = self.env['stock.warehouse.orderpoint'].get_min_qty(warehouse, product)

            # get prevision, horizon is 5 days
            date = fields.Date.today() + timedelta(days=5)
            prevision_ids = self.env['report.stock.weekprevision'].search([
                ('product_id', '=', product.id), ('warehouse_id', '=', warehouse.id), ('date', '<=', date)],
                order='date desc', limit=1)
            forecast_qty = prevision_ids.product_qty - product_min_qty

            if forecast_qty < 0.0:
                # Create OF
                self.env['mrp.production'].create_forecast_om(warehouse, product, - forecast_qty)





