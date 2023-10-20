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

    def get_picking(self,data):
        """ get the picking to use"""
        self.ensure_one()
        picking = self.env['stock.picking']
        if data.get('picking'):
            picking = data.get('picking')
        elif data.get('picking_id'):
            if type(data['picking_id']) is str and data['picking_id'].isnumeric():
                data['picking_id'] = int(data['picking_id'])

            if type(data['picking_id']) is int:
                picking = self.env['stock.picking'].browse(data['picking_id'])
                del data['picking_id']
        return picking

    def get_next_picking_line(self, data, weight=False):
        """ Return the next preparation line to do, initialize the data with this new line"""
        self.ensure_one()
        # define the priority of the stock.move.line, by location name
        picking = self.get_picking(data)

        if picking.exists():
            data = self.init_data(data)
            data['picking'] = picking

            if picking.state in ['confirmed', 'waiting']:
                picking.action_assign()

            location_preparation_ids = self.env['stock.warehouse'].search([]).mapped('wh_pack_stock_loc_id')
            moves_line_ids = self.env['stock.move.line'].search([
                ('picking_id', '=', picking.id),
                ('location_id', 'not in', location_preparation_ids.ids),
                ('reserved_uom_qty', '>', 0.0), ('qty_done', '=', 0.0),
                ], order='priority', limit=1)

            if moves_line_ids:
                data['move_line'] = moves_line_ids[0]
        else:
            data['warning'] = data.get('warning', '') + _('No picking selected')

        return data

    def get_next_weight_line(self, data):
        """ return the next line to weight"""
        self.ensure_one()
        picking = self.get_picking(data)
        if picking.exists():
            data = self.init_data(data)
            data['picking'] = picking
            location_preparation_ids = self.env['stock.warehouse'].search([]).mapped('wh_pack_stock_loc_id')

            moves_line_ids = self.env['stock.move.line'].search([
                ('picking_id', '=', picking.id),
                ('location_id', 'in', location_preparation_ids.ids),
                ('to_weight', '=', True), ('qty_done', '>', 0.0),
            ], order='priority', limit=1)

            if moves_line_ids:
                data['weight_line'] = moves_line_ids[0]
                data['product_id'] = data['weight_line'].product_id
                data['lot_id'] = data['weight_line'].lot_id
                data['quantity'] = data['weight_line'].qty_done

        else:
            data['warning'] = data.get('warning', '') + _('No picking selected')
        return data

    def get_title(self, data):
        """ Get title at this step"""
        self.ensure_one()
        res = ""
        if data.get('picking'):
            res = data['picking'].name
        return res

    def get_input_name(self, data):
        """ Return input-name to qweb template"""
        self.ensure_one()
        if self.action_variable:
            res = self.action_variable
        else:
            res = 'scan'
        return res

    def get_input_placeholder(self, data):
        """ Return input-placeholder to qweb template"""
        self.ensure_one()
        res = 'Scan'
        move_line = data.get('move_line')
        if move_line:
            if self.action_variable == 'lot_id':
                res = _('Lot:') + f"{move_line.lot_id.ref}  {move_line.lot_id.expiration_date.strftime('%d/%m/%Y')}"
            if self.action_variable == 'quantity':
                qty_placeholder = self.get_input_description_right(data, 'quantity')
                if qty_placeholder:
                    qty_placeholder = ' (' + qty_placeholder + ')'
                res = f'{int(move_line.reserved_uom_qty)}' + qty_placeholder

        return res

    def get_input_description_left(self, data, action_variable):
        """ Return input description when the input is not focused"""
        self.ensure_one()
        res = 'Scan'
        move_line = data.get('move_line')
        if action_variable == 'product_id':
            product = data.get('product_id') or move_line and move_line.product_id
            res = product and f'{product.name}' or '????'
        if action_variable == 'location_id':
            location = data.get('location_id') or move_line and move_line.location_id
            res = location and f'{location.name}' or '????'
        if action_variable == 'lot_id':
            lot = data.get('lot_id') or move_line and move_line.lot_id
            res = lot and f'{lot.ref}' or '????'
        if action_variable == 'quantity':
            quantity = data.get('quantity') or move_line.reserved_uom_qty or '????'
            res = f'{int(quantity)}'
        return res

    def get_input_description_right(self, data, action_variable):
        """ Return input description when the input is not focused"""
        self.ensure_one()
        res = ''
        move_line = data.get('move_line')
        if action_variable == 'product_id':
            product = data.get('product_id') or move_line and move_line.product_id
            res = product and f'{product.default_code}' or '????'
        if action_variable == 'location_id':
            location = data.get('location_id') or move_line and move_line.location_id
            res = location and len(location.name) > 5 and location.name[-5:] or ''
        if action_variable == 'lot_id':
            lot = data.get('lot_id') or move_line and move_line.lot_id
            res = lot.expiration_date and f"{lot.expiration_date.strftime('%d/%m/%Y')}" or '??/??/????'
        if action_variable == 'quantity':
            if move_line.move_id.bom_line_id.bom_id.type == 'phantom':
                quantity = int(data.get('quantity') or move_line.reserved_uom_qty)
                package_qty = int(move_line.move_id.bom_line_id.product_qty)
                if package_qty:
                    package_nb = int(int(quantity) / int(package_qty))
                    res = f'{package_nb}' + _(" Pack of ") + f'{package_qty}'
                else:
                    res = ""
        return res

    def get_input_type(self, data):
        """ Return input class to qweb template"""
        self.ensure_one()
        res = "text"
        if self.action_scanner == 'scan_quantity':
            res = 'number'

        return res

    def get_input_class(self, data):
        """ Return input class to qweb template"""
        self.ensure_one()
        if data.get('warning'):
            res = "input-warning"
        else:
            res = "input-green"
        return res

    def get_user_picking(self, data):
        """ return the set of picking currently in preparation by this user"""
        self.ensure_one()
        picking_type = self.env.ref('stock.picking_type_out')

        picking_ids = self.env['stock.picking'].search([
            ('user_id', '=', self.env.user.id),
            ('picking_type_id', '=', picking_type.id),
            ('state', 'in', ['assigned', 'confirmed', 'waiting'])
        ], order='sequence')
        if picking_ids:
            picking_ids.action_assign()
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
            picking_ids.action_assign()

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

    @api.model
    def move_preparation(self, data):
        """ Move product to preparation location, unreserve quant in previews location,
        reserve in preparation location
        """
        warehouse = self.env.ref('stock.warehouse0')
        uom_weight = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
        location_dest_id = warehouse.wh_pack_stock_loc_id

        if not data.get('move_line'):
            data['Warning'] = _("No move line to move?")
            return data

        move_line = data.get('move_line')
        quantity = data.get('quantity')
        # weight =
        product_id = move_line.product_id
        lot_id = move_line.lot_id
        location_id = move_line.location_id

        # Check reserved quantity
        condition = [
            ('product_id', '=', product_id.id),
            ('location_id', '=', location_id.id),
            ('lot_id', '=', lot_id.id)
            ]
        quant_ids = self.env['stock.quant'].search(condition)

        if sum(quant_ids.mapped('quantity')) >= quantity:
            move_data = {
                'location_id': location_id,
                'product_id': product_id,
                'location_dest_id': location_dest_id,
                'lot_id': lot_id,
                'weight': data.get('weight'),
                'quantity': data.get('quantity')
                }
            result_data = self.move_product(move_data)

            if result_data.get('result'):
                if move_line.reserved_uom_qty - move_data.get('quantity') <= 0.0:
                    move_line.reserved_uom_qty = 0.0
                else:
                    move_line.reserved_uom_qty -= move_data.get('quantity')

                new_move_line = move_line.copy({
                    'location_id':  move_data.get('location_dest_id').id,
                    'weight': move_data.get('weight'),
                    'reserved_uom_qty': move_data.get('quantity'),
                    'qty_done':  move_data.get('quantity'),
                })

                # to Weight or not?
                if not new_move_line.weight:
                    if new_move_line.product_id.uos_id == uom_weight:
                        new_move_line.to_weight = True
                        new_move_line.weight = new_move_line.product_id.weight * new_move_line.qty_done
                    else:
                        new_move_line.weight = new_move_line.product_id.weight
                        new_move_line.to_weight = False
                else:
                    new_move_line.to_weight = False

                # Reserve the quants moved in preparation location
                condition = [
                    ('product_id', '=', product_id.id),
                    ('location_id', '=', location_dest_id.id),
                    ('lot_id', '=', lot_id.id or False)
                ]
                quant_ids = self.env['stock.quant'].search(condition)
                for quant in quant_ids:
                    if quant.reserved_quantity != quant.quantity:
                        quant.reserved_quantity = quant.quantity

                # Init data for next line to prepare
                data = self.init_data()
                data['picking'] = move_line.picking_id
                data['move_line'] = move_line
                data['message'] = _('The product is moving to preparation')

        if move_line.reserved_uom_qty == 0.0 and move_line.qty_done == 0.0:
            del data['move_line']
            move_line.unlink()

        return data

    @api.model
    def weight_preparation(self, data):
        """ Weight product in preparation location
        """
        warehouse = self.env.ref('stock.warehouse0')

        return data