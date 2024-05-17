# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################

from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_mrp(self):
        """ Check if all product with BOM need manufacture, recursive analyse """
        bom_todo = self.env['mrp.bom']

        def get_all_bom(boms):
            """ return all bom in this bom """
            all_bom = self.env['stock.bom']
            for bom in boms:
                for line in bom.bom_line_ids:
                    if line.product_id.bom_ids:
                        for sub_bom in line.product_id.bom_ids:
                            all_bom |= get_all_bom(sub_bom)
            all_bom |= boms
            return all_bom

        # list the BOM to do
        for picking in self:
            if picking.state in ['cancel', 'done']:
                continue
            for move in picking.move_ids_without_package:
                if move.product_id.bom_ids:
                    bom_todo |= get_all_bom(move.product_id.bom_ids)

        # list or create the order point
        order_point = self.env['stock.warehouse.orderpoint']
        for bom in bom_todo:
            if bom.type == 'kit':
                continue
            product = bom.product_id
            location = self.search['stock.warehouse']([], limit=1).lot_stock_id
            order_point = self.env['stock.warehouse.orderpoint'].search(
                [('product_id', '=', product.id),
                 ('location_id', '=', location.id)], limit=1)

            if not order_point:
                order_point_vals = {'product_id': product.id, 'location_id': location.id, 'product_min_qty': 0.0,
                                    'route_id': self.ref('mrp.route_warehouse0_manufacture'), 'trigger': 'auto',
                                    'bom_id': bom.id, 'qty_multiple': product.min_production_qty or 1.0,
                                    'company_id': self.env.company.id or 1, 'visibility_days': 5.0}
                order_point = order_point.create(order_point_vals)

