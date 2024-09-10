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

    def action_mrp(self):
        """ Check if all product with BOM need manufacture """
        for picking in self:
            production_qty = {}
            production_exist = {}

            for production in picking.group_id.mrp_production_ids:
                if production.state in ['cancel']:
                    continue
                elif production.product_id in list(production_exist.keys()):
                    production_exist[production.product_id] |= production
                else:
                    production_exist[production.product_id] = production

            for move in picking.move_ids_without_package:
                # sum of product_qty  if there is a need
                if move.product_id.bom_ids and move.product_id.bom_ids[0].type == 'normal':
                    if move.product_id in list(production_qty.keys()):
                        production_qty[move.product_id] += move.product_uom_qty
                    else:
                        production_qty[move.product_id] = move.product_uom_qty

            for move in picking.move_ids_without_package:
                if move.product_id not in list(production_qty.keys()):
                    # No production todo
                    continue

                if move.product_id.make_to_order:
                    if not production_exist.get(move.product_id):
                        lot = self.env['stock.lot'].create_production_lot(move.product_id)
                        production_vals = {
                            'product_id': move.product_id.id,
                            'origin': picking.origin,
                            'product_qty': production_qty[move.product_id],
                            'bom_id': move.product_id.bom_ids[0].id,
                            'lot_producing_id': lot.id,
                            'procurement_group_id': picking.group_id.id,
                            'date_planned_start': picking.scheduled_date or fields.Datetime.now()
                        }
                        new_mo = self.env['mrp.production'].create(production_vals)
                        new_mo.action_confirm()
                        new_mo.move_raw_ids.put_quantity_done()
                        production_exist[move.product_id] = new_mo
                        picking.group_id.mrp_production_ids |= new_mo

                    if production_exist[move.product_id]:
                        if not move.move_line_ids:
                            move.put_quantity_done()
                        for move_line in move.move_line_ids:
                            move_line.lot_id = production_exist[move.product_id][0].lot_producing_id
                            move_line.location_id = production_exist[move.product_id][0].location_dest_id
                            move_line.reserved_uom_qty = move.product_uom_qty
                else:
                    if not production_exist.get(move.product_id):
                        stock_mo = move.product_id.action_normal_mrp()
                        production_exist[move.product_id] = stock_mo
