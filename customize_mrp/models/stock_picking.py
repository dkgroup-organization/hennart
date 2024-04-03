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
        for picking in self:
            for move in picking.move_ids_without_package:
                product = move.product_id
                min_production_qty = product.min_production_qty
                quantity_to_produce = move.product_uom_qty

                if move.product_id.bom_ids != False:
                    if move.product_uom_qty != move.forecast_availability and move.product_uom_qty > 0:
                        if move.mrp_id == False:

                            in_process_productions = self.env['mrp.production'].search([
                            ('product_id', '=', product.id),
                            ('state', '=', 'draft'),
                            ])
                            
                            if quantity_to_produce <= min_production_qty:
                                quantity_to_produce = min_production_qty

                            elif quantity_to_produce % min_production_qty != 0:
                                quantity_to_produce = (min_production_qty * ((quantity_to_produce // min_production_qty) + 1)) - move.forecast_availability

                        # if move_line.state == 'assigned' and move_line.product_uom_qty > 0:

                            if in_process_productions:
                                quantity = in_process_productions.product_qty + quantity_to_produce
                                in_process_productions.write({
                                    'product_qty': quantity,
                                    'move_from_picking_ids': [(4, move.id)],  
                                    })
                                
                            else:
                                production_order = self.env['mrp.production'].create({
                                    'product_id': move.product_id.id,
                                    'product_qty': quantity_to_produce,
                                    'move_from_picking_ids': [(4, move.id)],  

                                })

                            # production_order.action_confirm()  # Confirmer le MO
                            # production_order.button_plan()  # Planifier le MO
                            # production_order.action_produce()  # Démarrer la production du MO
