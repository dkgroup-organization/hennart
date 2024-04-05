# -*- coding: utf-8 -*-


from odoo import api, fields, models, tools, _
from odoo.tools.float_utils import float_round, float_is_zero
from datetime import timedelta, datetime


class ProductProduct(models.Model):
    _inherit = 'product.product'

    production_forcasting = fields.Float('Production forcasting', compute="compute_production_forcasting")

    def compute_production_forcasting(self):
        """ Compute the quantity forcast to produce """
        horizon_past = 5
        horizon_futur_outgoing = 2
        horizon_futur_incoming = 1

        for product in self:
            if product.bom_ids and product.bom_ids[0].type == 'normal' and not product.to_personnalize:

                incoming_moves = self.env['stock.move'].search([
                        ('product_id', '=', product.id),
                        ('state', 'not in', ['draft', 'done', 'cancel']),
                        ('location_id.usage', 'not in', ['internal', 'view']),
                        ('location_dest_id.usage', 'in', ['internal', 'view']),
                        ('date', '>=', fields.Datetime.now() - timedelta(days=horizon_past)),
                        ('date', '<', fields.Datetime.now() + timedelta(days=horizon_futur_incoming))
                    ])
                incoming_qty = sum(incoming_moves.mapped('product_uom_qty'))
                outgoing_moves = self.env['stock.move'].search([
                        ('product_id', '=', product.id),
                        ('state', 'not in', ['draft', 'done', 'cancel']),
                        ('location_dest_id.usage', 'not in', ['internal', 'view']),
                        ('location_id.usage', 'in', ['internal', 'view']),
                        ('date', '>=', fields.Datetime.now() - timedelta(days=horizon_past)),
                        ('date', '<', fields.Datetime.now() + timedelta(days=horizon_futur_outgoing))
                    ])
                outgoing_qty = sum(outgoing_moves.mapped('product_uom_qty'))
                production_forcasting = outgoing_qty - product.qty_available - incoming_qty

                print(outgoing_moves, outgoing_qty, incoming_moves, incoming_qty)
                if production_forcasting <= 0.0:
                    production_forcasting = 0.0
                elif product.min_production_qty > 0.0:
                    nb_batch = production_forcasting / product.min_production_qty
                    if nb_batch > float(int(nb_batch)):
                        nb_batch = float(int(nb_batch)) + 1.0
                    else:
                        nb_batch = float(int(nb_batch))
                    production_forcasting = nb_batch * product.min_production_qty

                product.production_forcasting = production_forcasting
            else:
                product.production_forcasting = 0.0

    def action_mrp(self):
        """ Create production if product.production_forcasting is needed """
        res = self.env['mrp.production']
        for product in self:
            product_qty = product.production_forcasting

            if product_qty > 0.0:
                bom = product.bom_ids[0]
                lot = self.env['stock.lot'].create_production_lot(product)
                mo_vals = {
                    'product_id': product.id,
                    'origin': 'stock',
                    'product_qty': product_qty,
                    'bom_id': bom.id,
                    'lot_producing_id': lot.id,
                }
                new_mo = self.env['mrp.production'].create(mo_vals)
                new_mo.action_confirm()
                res |= new_mo
        return res
