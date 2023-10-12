# 2020 Joannes Landy <joannes.landy@opencrea.fr>
# Based on the work of sylvain Garancher <sylvain.garancher@syleam.fr>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging
from odoo import models, api, fields, _
from odoo.exceptions import MissingError, UserError, ValidationError
import time
import datetime

class WmsScenarioStep(models.Model):
    _inherit = 'wms.scenario.step'

    def get_next_picking_line(self, data):
        """ Return the next preparation line to do, initialize the data with this new line"""
        self.ensure_one()
        # define the priority of the stock.move.line, by location name
        picking = self.env['stock.picking']

        if data.get('picking'):
            picking = data.get('picking')
        elif data.get('picking_id') and data['picking_id'].isnumeric():
            picking = self.env['stock.picking'].browse(int(data['picking_id']))
        else:
            data['warning'] = data.get('warning', '') + _('No picking selected')

        if picking.exists():
            data = self.init_data(data)
            data['picking'] = picking
            print('\n---------get_next_picking_line---4------', data)

            # Todo: define the rule to apply,
            moves_line_ids = self.env['stock.move.line'].search([
                ('picking_id', '=', picking.id)
            ], order='priority', limit=1)

            data['move_line'] = moves_line_ids

        print('\n---------get_next_picking_line---------', data)
        return data

    def get_user_picking(self, data):
        """ return the set of picking currently in preparation by this user"""
        self.ensure_one()
        picking_type = self.env.ref('stock.picking_type_out')

        picking_ids = self.env['stock.picking'].search([
            ('user_id', '=', self.env.user.id),
            ('picking_type_id', '=', picking_type.id),
            ('state', 'in', ['assigned', 'confirmed', 'waiting'])
        ], order='sequence')
        data.update({'picking_ids': picking_ids})
        return data

    def add_next_picking(self, data):
        """ assign next picking to this user, return the list of picking assigned to the current user"""
        picking_type = self.env.ref('stock.picking_type_out')

        picking_ids = self.env['stock.picking'].search([
            ('user_id', '=', False),
            ('picking_type_id', '=', picking_type.id),
            ('state', 'in', ['assigned', 'confirmed', 'waiting'])
        ], order='sequence', limit=1)

        if picking_ids:
            picking_ids.user_id = self.env.user

        return self.get_user_picking(data)

    def check_move_line_scan(self, data):
        """ Check the lot and the quantity """
        self.ensure_one()

        product = data.get('product_id')
        location = data.get('location_id') or data.get('location_origin_id')
        lot = data.get('lot_id')
        move_line = data.get('move_line')
        quantity = data.get('quantity', 0.0)

        if move_line:
            location = move_line.location_id
            product = move_line.product_id

        if product and lot and product != lot.product_id:
            data['warning'] = _("This is not the product to pick.")

        elif move_line and lot and lot != move_line.lot_id:
            data['warning'] = _("This is not the lot to pick.")

        elif move_line and move_line.lot_id and not lot:
            data['warning'] = _("Scan the production lot: {}".format(move_line.lot_id.ref))

        elif product and location:
            condition = [
                ('product_id', '=', product.id),
                ('location_id', '=', location.id)]

            if lot:
                condition.append(('lot_id', '=', lot.id))
            elif product.tracking == 'lot':
                data['warning'] = _("This product need a lot number")

            if not data.get('warning'):
                quant_ids = self.env['stock.quant'].search(condition)

                if not quant_ids:
                    data['warning'] = "This product is not registered on this location"
                elif quantity:
                    max_quantity = sum(quant_ids.mapped('quantity'))
                    if quantity > max_quantity:
                        data['warning'] = _("The maximum quantity in this location is {}".format(max_quantity))
                    elif move_line and quantity > move_line.reserved_uom_qty:
                        data['warning'] = _("The maximum quantity to pick is {}".format(max_quantity))
        else:
            data['warning'] = _("Some information are missing to check product on location.")

        return data

    def move_line_to_prepa(self, data):
        """ move the quant to preparation location after user scanning """
        self.ensure_one()
        data = self.check_move_line_scan(data)
        if data.get('warning'):
            return data

        if data.get('move_line') and data.get('quantity'):
            pass
