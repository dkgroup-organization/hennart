# 2020 Joannes Landy <joannes.landy@opencrea.fr>
# Based on the work of sylvain Garancher <sylvain.garancher@syleam.fr>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging
from odoo import models, api, fields, _
from odoo.exceptions import MissingError, UserError, ValidationError
from odoo.http import request
import time
import random
import datetime


class WmsScenarioStep(models.Model):
    _inherit = 'wms.scenario.step'

    def get_picking(self, data):
        """ get the picking to use"""
        self.ensure_one()
        picking = data.get('picking') or self.env['stock.picking']
        picking_id = data.get('picking_id') or self.env['stock.picking']
        if picking_id and picking_id != picking:
            picking = picking_id
        return picking

    def get_next_picking_line(self, data):
        """ Return the next preparation line to do, initialize the data with this new line"""
        self.ensure_one()
        # define the priority of the stock.move.line, by location name
        picking = self.get_picking(data)
        move_line = data.get('move_line')
        new_data = self.init_data(data)

        if picking.exists():
            new_data['picking'] = picking

            if move_line and move_line.qty_done == 0.0 and move_line.reserved_uom_qty > 0.0:
                # this move line is to finish
                new_data['move_line'] = move_line
            else:
                location_preparation_ids = self.env['stock.warehouse'].search([]).mapped('wh_pack_stock_loc_id')
                move_line_todo = [
                    ('picking_id', '=', picking.id),
                    ('location_id', 'not in', location_preparation_ids.ids),
                    ('reserved_uom_qty', '>', 0.0), ('qty_done', '=', 0.0),
                    ]
                move_line_ids = self.env['stock.move.line'].search(move_line_todo, order='priority', limit=1)

                if move_line_ids:
                    new_data['move_line'] = move_line_ids
                else:
                    # New checking before weight and label step
                    picking.compute_preparation_state()
                    if picking.preparation_state in ['wait', 'pick']:
                        picking.action_assign()
                        move_line_ids = self.env['stock.move.line'].search(move_line_todo, order='priority', limit=1)
                        if move_line_ids:
                            new_data['move_line'] = move_line_ids
        else:
            new_data['warning'] = new_data.get('warning', '') + _('No picking selected')

        return new_data

    def get_next_weight_line(self, data):
        """ return the next line to weight"""
        self.ensure_one()
        picking = self.get_picking(data)
        printer = data.get('printer')

        if picking.exists():
            data = self.init_data(data)
            data['picking'] = picking
            if printer:
                data['printer'] = printer

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
                picking.compute_preparation_state()
        else:
            data['warning'] = data.get('warning', '') + _('No picking selected')
        return data

    def get_title(self, data):
        """ Get title at this step"""
        self.ensure_one()
        res = ""
        if data.get('picking'):
            res = data['picking'].name
            if data['picking'].partner_id:
                res += data['picking'].partner_id.name
        return res

    def get_input_name(self, data):
        """ Return input-name to qweb template"""
        self.ensure_one()
        if self.action_variable:
            res = self.action_variable
        else:
            res = 'scan'
        return res

    def get_label(self, data):
        """ Return label """
        self.ensure_one()
        res = ''
        if self.action_variable == 'maturity_product_id':
            res = _('Maturity product')
        return res

    def get_input_placeholder(self, data):
        """ Return input-placeholder to qweb template"""
        self.ensure_one()
        res = 'Scan'
        move_line = data.get('move_line') or data.get('weight_line')
        production = data.get('production_id')

        if self.action_message:
            return self.action_message

        if self.action_variable == 'lot_id':
            if move_line:
                if move_line.lot_id:
                    expiration_date = move_line.lot_id.expiration_date or move_line.lot_id.use_date
                    res = _('Lot: ') + f"{move_line.lot_id.ref}"
                    if expiration_date:
                        res += f" {expiration_date.strftime('%d/%m/%Y')}"
                else:
                    res = _('Scan lot')
            else:
                res = _('Scan lot')

        if self.action_variable == 'location_origin_id':
            res = _('Scan origin location')

        if self.action_variable == 'location_dest_id':
            res = _('Scan destination location')

        if self.action_variable == 'location_id':
            res = _('Scan location')

        if self.action_variable == 'product_id':
            res = _('Scan Product code')

        if self.action_variable == 'production_id':
            res = _('Scan production')

        if self.action_variable == 'production_lot_id':
            production_lot = production and production.lot_producing_id
            if production_lot:
                res = f"{production_lot.name or ''}"
                expiration_date = production_lot.expiration_date or production_lot.use_date
                if expiration_date:
                    res += f"            {expiration_date.strftime('%d/%m/%Y')}"
            else:
                res = _('Scan production lot')

        if self.action_variable == 'quantity':
            if move_line:
                qty_placeholder = self.get_input_description_right(data, 'quantity')
                if qty_placeholder:
                    qty_placeholder = ' (' + qty_placeholder + ')'
                res = f'{int(move_line.reserved_uom_qty)}' + qty_placeholder
            else:
                res = _('Enter Quantity')

            if data.get('max_quantity'):
                res += _('  (max: ') + f"{data['max_quantity']} " + _("Unit") + ")"

        if self.action_variable == 'production_quantity':
            if production:
                res = f'{int(production.product_qty)} ' + _('Unit')
            else:
                res = 'Produced quantity'

        if self.action_variable == 'printer':
            res = _('Scan Printer')

        if self.action_variable == 'weight':
            res = _('Enter Net weight:')
            if move_line and move_line.product_id.weight:
                res += '~ {} Kg'.format(move_line.product_id.weight * move_line.qty_done)

        if self.action_variable == 'weighting_device':
            if data.get('weight', 0.0) > 0.0:
                tare = self.get_tare(data)
                res = _("Valid:  ") + f"{data.get('weight', 0.0):.3f}" + _(" Kg or scan")
            else:
                res = _("Scan weighting device")

        if self.action_variable == 'tare':
            res = _('Enter tare by unit in Kg')

        if self.action_variable == 'expiry_date':
            res = _('Expiry date')

        if self.action_variable == 'number_of_packages':
            res = _("Nb of package: ")
            if data.get('number_of_packages'):
                res += f"{data['number_of_packages']}"
            elif data.get('picking'):
                res += f"{data['picking'].number_of_packages}"

        if self.action_variable == 'nb_container':
            res = _("Nb of container: ")
            if data.get('nb_container'):
                res += f"{data['nb_container']}"
            elif data.get('picking'):
                res += f"{data['picking'].nb_container}"

        if self.action_variable == 'nb_pallet':
            res = _("Nb of pallet: ")
            if data.get('nb_pallet'):
                res += f"{data['nb_pallet']}"
            elif data.get('picking'):
                res += f"{data['picking'].nb_pallet}"

        return res

    def get_input_description_left(self, data, action_variable):
        """ Return input description when the input is not focused"""
        self.ensure_one()
        res = 'Scan'
        move_line = data.get('move_line') or data.get('weight_line')
        production = data.get('production_id')

        if action_variable == 'product_id':
            product = data.get('product_id') or move_line and move_line.product_id
            res = product and f'{product.name}' or _('Product')
        if action_variable == 'production_product_id':
            production_product = data.get('production_product_id') or production and production.product_id
            res = production_product and f'{production_product.name}' or _('Product to produce')
        if action_variable == 'location_id':
            location = data.get('location_id') or move_line and move_line.location_id
            res = location and f'{location.name}' or _('location')
        if action_variable == 'location_origin_id':
            location = data.get('location_origin_id')
            res = location and f'{location.name}' or _('location')
        if action_variable == 'location_dest_id':
            location = data.get('location_dest_id')
            res = location and f'{location.name}' or _('location')
        if action_variable == 'lot_id':
            lot = data.get('lot_id') or move_line and move_line.lot_id
            res = lot and f'{lot.ref}' or _('Lot')
        if action_variable == 'production_lot_id':
            production_lot = data.get('production_lot_id') or production and production.lot_producing_id
            res = production_lot and f'{production_lot.ref}' or _('Production lot')

        if action_variable == 'quantity':
            quantity = data.get('quantity') or move_line and move_line.reserved_uom_qty or 0.0
            if quantity % 1 != 0.0:
                res = f"{quantity:.2f}"
            else:
                res = f'{int(quantity)}'
        if action_variable == 'production_quantity':
            if production:
                res = f'{int(production.qty_producing or production.product_qty)}  ' + _('Unit')
            else:
                res = 'Quantity'
        if action_variable == 'printer':
            printer = data.get('printer')
            res = printer and printer.name or _('scan printer')
        if action_variable == 'weight':
            if data.get('weight'):
                res = f"{data.get('weight', 0.0):.3f} Kg"
            else:
                res = f"? Kg"

        if action_variable == 'number_of_packages':
            res = _("Nb of package: ")

        if action_variable == 'nb_container':
            res = _("Nb of container: ")

        if action_variable == 'nb_pallet':
            res = _("Nb of pallet: ")

        if action_variable == 'maturity_product_id':
            res = data.get('maturity_product_id') and data['maturity_product_id'].name or _("Maturity product: ")

        if action_variable == 'expiry_date':
            res = _("Expiry Date: ")

        if action_variable == 'production_id':
            production = data.get('production_id')
            res = production and f'{production.name}' or _('Production')

        return res

    def get_input_description_right(self, data, action_variable):
        """ Return input description when the input is not focused"""
        self.ensure_one()
        res = ''
        move_line = data.get('move_line') or data.get('weight_line')
        production = data.get('production_id')

        if action_variable == 'product_id':
            product = data.get('product_id') or move_line and move_line.product_id
            res = product and f': {product.default_code}' or ''

        if action_variable == 'production_product_id':
            production_product = data.get('production_product_id') or production and production.product_id
            res = production_product and f': {production_product.default_code}' or ''

        if action_variable in ['location_id', 'location_origin_id', 'location_dest_id']:
            location = data.get('location_id') or data.get('location_origin_id') or (move_line and move_line.location_id) or False
            if location and len(location.name) > 5 and location.name[-2:].isnumeric():
                res = location.name[-5:]

        if action_variable == 'lot_id':
            lot = data.get('lot_id') or (move_line and move_line.lot_id) or False
            if lot:
                res = lot.expiration_date and f"{lot.expiration_date.strftime('%d/%m/%Y')}" or '??/??/????'

        if action_variable == 'production_lot_id':
            production_lot = data.get('lot_id') or data.get('production_lot_id') or (production and production.lot_producing_id) or False
            if production_lot:
                res = production_lot.expiration_date and f"{production_lot.expiration_date.strftime('%d/%m/%Y')}" or '??/??/????'

        if action_variable == 'quantity':
            if data.get('move_line') and move_line.move_id.bom_line_id.bom_id.type == 'phantom':
                quantity = int(data.get('quantity') or move_line.reserved_uom_qty)
                package_qty = int(move_line.move_id.bom_line_id.product_qty)
                if quantity and package_qty:
                    package_nb = int(int(quantity) / int(package_qty))
                    if package_nb:
                        res = f'{package_nb} ' + _(" Pack of ") + f'{package_qty}'
                    else:
                        res = _("Unit")

            elif data.get('product_id') and data['product_id'].base_unit_count > 1:
                res = _(" Pack of ") + f"{int(data['product_id'].base_unit_count)}"
            else:
                res = _("Unit")

        if action_variable == 'expiry_date':
            if data.get('expiry_date') and type(data['expiry_date']) in [type(datetime.date), type(datetime.datetime)]:
                expiry_date = f"{data['expiry_date'].strftime('%d/%m/%Y')}"
                res = expiry_date

        if action_variable == 'weight':
            res = _("Tare: ")
            tare = data.get('tare') or self.get_tare(data)
            res += f"{tare:.3f} Kg/Unit"

        if action_variable == 'number_of_packages':
            if data.get('number_of_packages'):
                res = f"{data['number_of_packages']}"
            elif data.get('picking'):
                res = f"{data['picking'].number_of_packages}"

        if action_variable == 'nb_container':
            if data.get('nb_container'):
                res = f"{data['nb_container']}"
            elif data.get('picking'):
                res = f"{data['picking'].nb_container}"

        if action_variable == 'nb_pallet':
            if data.get('nb_pallet'):
                res = f"{data['nb_pallet']}"
            elif data.get('picking'):
                res = f"{data['picking'].nb_pallet}"

        if action_variable == 'maturity_product_id':
            if data.get('maturity_product_id'):
                res = f"{data['maturity_product_id'].default_code}"

        return res

    def get_input_type(self, data):
        """ Return input class to qweb template"""
        self.ensure_one()
        res = "text"
        if self.action_scanner in ['scan_quantity']:
            res = 'number'
        if self.action_scanner == 'scan_weight' and self.action_variable == 'weight':
            res = 'hidden'
        if self.action_scanner in ['scan_date']:
            res = 'date'
        return res

    def get_input_step(self, data):
        """ Return step to number manual entry"""
        self.ensure_one()
        res = "1"
        if self.action_variable == 'weight':
            res = '0.001'
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
        data = self.init_data()
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

    def get_button_option(self, data):
        """ Get the configuration for add button in Qweb, on the message zone
         return a list of tuple:
         [{'text': 'the text in the button, 'href': 'the http link'},
          {},
          ...]
         """
        self.ensure_one()
        res = []
        scenario_id = data['step'].scenario_id.id
        step_id = data['step'].id
        href_base = f'./scanner?scenario={scenario_id}&step={step_id}&button='

        if data['step'].action_scanner == 'scan_weight':
            tare = self.get_tare(data)
            res = [
                {'text': _('Manual entry'),
                 'href': href_base + 'manual_weight'
                 },
                {'text': _('Change Tare: ') + f"{tare} Kg/Unit", 'href': href_base + 'manual_tare'}
            ]

        if data['step'].action_variable == 'location_origin_id':
            location_ids = self.get_default_origin_location()
            for location in location_ids:
                res.append({'text': location.name, 'href': href_base + f'location_origin_id&scan={location.id}'})

        if data['step'].action_variable == 'location_dest_id':
            location_ids = self.get_default_dest_location()
            for location in location_ids:
                res.append({'text': location.name, 'href': href_base + f'location_dest_id&scan={location.id}'})

        if data['step'].action_variable == 'production_lot_id':
            if data.get('production_id') and data['production_id'].lot_producing_id and not data['production_id'].lot_producing_id.quant_ids:
                res.append({'text': _('Modify date'), 'href': href_base + f"change_date"})

        if data['step'].action_variable == 'printer':
            if data.get('button_change_date'):
                res.append(data.get('button_change_date'))


        if not res and data.get('button_print_later') and (data.get('lot_id') or data.get('production_lot_id')
                        or (data.get('production_id') and data['production_id'].lot_producing_id)):
            lot = data.get('lot_id') or data.get('production_lot_id')
            res.append({'text': _('Print later'), 'href': href_base + f"print_later"})

        return res

    def get_tare(self, data):
        """ Return the tare of the line product"""
        self.ensure_one()
        move_line = data.get('weight_line')
        tare = 0.0
        if 'tare' in list(data.keys()):
            tare = data.get('tare')
        elif move_line:
            if move_line.pack_product_id.tare and move_line.quantity_per_pack:
                tare = move_line.pack_product_id.tare / move_line.quantity_per_pack
            else:
                tare = move_line.product_id.tare
        return tare

    def check_move_line_scan(self, data):
        """ Check the lot and the quantity """
        self.ensure_one()

        product = data.get('product_id')
        location = data.get('location_id') or data.get('location_origin_id')
        lot = data.get('lot_id')
        move_line = data.get('move_line')
        quantity = data.get('quantity') or data.get('label_quantity', 0.0)

        if move_line:
            location = move_line.location_id
            product = move_line.product_id

        if product and lot and product != lot.product_id:
            data['warning'] = _("This is not the product to pick.")

        if move_line and lot and lot != move_line.lot_id:
            data['warning'] = _("This is not the lot to pick.")

        if move_line and move_line.lot_id and not lot:
            data['warning'] = _("Scan the production lot: {}".format(move_line.lot_id.ref))

        if product and location:
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
                        data['warning'] = _("The maximum quantity to pick is {}".format(move_line.reserved_uom_qty))
        else:
            data['warning'] = _("Some information are missing to check product on location.")
        return data

    @api.model
    def move_preparation(self, data):
        """ Move product to preparation location,
        unreserve quant in previews location,
        reserve in preparation location
        """
        warehouse = self.env.ref('stock.warehouse0')
        uom_weight = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
        location_dest_id = warehouse.wh_pack_stock_loc_id

        if not data.get('move_line'):
            raise ValidationError(_("No move line to move."))

        move_line = data.get('move_line')
        quantity = data.get('quantity') or data.get('label_quantity')
        weight = data.get('weight') or data.get('label_weight')
        product_id = move_line.product_id
        lot_id = move_line.lot_id
        location_id = move_line.location_id
        priority = move_line.priority

        # Check reserved quantity on move_line
        if quantity > move_line.reserved_uom_qty:
            raise ValidationError(_("You cannot move more product than reserved"))

        # Check quantity on location
        condition = [
            ('product_id', '=', product_id.id),
            ('location_id', '=', location_id.id),
            ('lot_id', '=', lot_id.id)
            ]
        quant_ids = self.env['stock.quant'].search(condition)

        if sum(quant_ids.mapped('quantity')) < quantity:
            raise ValidationError(_("Not enough quantity in location."))

        # There is a surprise when another picking force the move a lot.
        # Odoo delete all move_line when the reservation cannot be doing anymore, in this case => bug
        # So Update product on preparation before
        new_move_data = {
            'location_id': location_dest_id.id,
            'weight': weight,
            'reserved_uom_qty': quantity,
            'qty_done': quantity,
            'priority': priority,
            }
        if move_line.reserved_uom_qty - quantity <= 0.0:
            # In this case, all quantity reserved will move, the line is finish
            move_line.write(new_move_data)
            new_move_line = move_line
        else:
            # In this case, all quantity is not moving, the line is not finish, a new line is to create
            move_line.reserved_uom_qty -= quantity
            new_move_line = move_line.copy(new_move_data)

        # to Weight or not?
        if not new_move_line.weight:
            if new_move_line.product_id.uos_id == uom_weight:
                new_move_line.to_weight = True
                new_move_line.to_label = True
            else:
                new_move_line.to_weight = False
            new_move_line.weight = new_move_line.product_id.weight * new_move_line.qty_done
        else:
            new_move_line.to_weight = False

        # Move product on preparation
        move_data = {
            'location_id': location_id,
            'product_id': product_id,
            'location_dest_id': location_dest_id,
            'lot_id': lot_id,
            'weight': weight,
            'quantity': quantity,
            'priority': priority,
            }
        result_data = self.move_product(move_data)

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
        data['message'] = _('The product is moving to preparation')

        return data

    def get_end_preparation_message(self, data):
        """ Add som indication to user at the end of the preparation"""
        message = _("End of the preparation")
        res = f"<h1>{message}</h1>"
        return res

    def check_weight(self, data):
        """ Check the weight operation"""

        params = dict(request.params) or {}
        if params.get('scan', '') and not (data.get('label_weight') or data.get('weighting_device')):
            data['warning'] = _("This is not a weight")

        product = data.get('product_id') or data.get('label_product')
        lot = data.get('lot_id') or data.get('label_lot')

        move_line = data.get('move_line') or data.get('weight_line')
        if lot and move_line.lot_id != lot:
            data['warning'] = _("This is not the good lot")
        if product and move_line.product_id != product:
            data['warning'] = _("This is not the good product")

        if data.get('weight') and not params.get('scan', ''):
            # OK
            pass

        return data

    def start_weight_preparation(self, data):
        """ After the choice of printer, do some action:
        - update the preparation_state:
        """
        self.ensure_one()
        picking = data.get('picking')
        picking.label_preparation()
        picking.compute_preparation_state()
        data.update({'print_label': True})
        return data

    def print_label_preparation(self, data):
        """ After the choice of printer, do some action:
        - print the label if no weighted is needed
        """
        self.ensure_one()
        picking = data.get('picking')
        printer = data.get('printer')
        if picking and printer:
            picking.print_label(printer=printer)
        if 'print_label' in list(data.keys()):
            del data['print_label']
        return data

    def weight_preparation(self, data):
        """ Weight product in preparation location
        """
        move_line = data.get('move_line') or data.get('weight_line')
        if data.get('lot_id') and move_line.lot_id != data.get('lot_id'):
            data['warning'] = _("This is not the good lot")
        if data.get('product_id') and move_line.product_id != data.get('product_id'):
            data['warning'] = _("This is not the good product")

        if data.get('warning'):
            # Do nothing
            pass
        elif data.get('label_weight'):
            # currently in weighting process use weight on label
            data['tare'] = 0.0
            data['weighting_device'] = -1
            data['weight'] = data.get('weight', 0.0) + data.get('label_weight')
            weight_detail = data.get('weight_detail', []).copy()
            weight_detail.append({'qty': data.get('label_qty', 1), 'weight': data['label_weight'], 'tare': 0.0})
            data['weight_detail'] = weight_detail

        elif data.get('weighting_device'):
            # currently in weighting process
            # get the weight by asking device
            weight_device = data['weighting_device'].get_weight(data=data)
            data['tare'] = self.get_tare(data)

            data['weight'] = data.get('weight', 0.0) + weight_device
            weight_detail = data.get('weight_detail', []).copy()
            weight_detail.append({'qty': 0.0, 'weight': round(weight_device, 3), 'tare': data['tare']})
            data['weight_detail'] = weight_detail

        elif data.get('weight') and data.get('weight_line'):
            # save the weight
            move_line = data.get('weight_line')
            qty_tare = move_line.qty_done
            if data.get('weight_detail'):
                # look if some product has label, in this case don't soustracte the tare
                for weighted_line in data['weight_detail']:
                    if weighted_line.get('qty') and weighted_line.get('tare', 0.0) == 0.0:
                        qty_tare -= weighted_line['qty']
                    if not data.get('tare', 0.0) and weighted_line.get('tare', 0.0) != 0.0:
                        data['tare'] = weighted_line['tare']

            move_line.weight = data.get('weight', 0.0) - qty_tare * data.get('tare', 0.0)
            move_line.to_weight = False
            move_line.to_label = True

            if move_line.to_label and data.get('printer'):
                move_line.print_label(printer=data.get('printer'))
                move_line.to_label = False
        else:
            data['warning'] = _("This is not a weight")

        # init data to new weighting operation
        new_data = self.init_data()
        for key in ['picking', 'weight_line', 'printer', 'weight', 'warning', 'tare', 'weight_detail']:
            if data.get(key):
                new_data[key] = data.get(key)
        return new_data

    def package_preparation(self, data):
        """ Update preparation package """
        self.ensure_one()
        if data.get('picking'):
            if 'number_of_packages' in list(data.keys()) and data['picking'].number_of_packages != int(data['number_of_packages']):
                data['picking'].number_of_packages = int(data['number_of_packages'])
            if 'nb_container' in list(data.keys()) and data['picking'].nb_container != int(data['nb_container']):
                data['picking'].write({'nb_container': int(data['nb_container'])})
                data['picking'].update_sscc()
            if 'nb_pallet' in list(data.keys()) and data['picking'].nb_pallet != int(data['nb_pallet']):
                data['picking'].write({'nb_pallet': int(data['nb_pallet'])})
                data['picking'].update_sscc()

    def picking_validation_print(self, data):
        """ Valid the end of the preparation, and print documents """
        self.ensure_one()

        if not data.get('warning'):
            picking = data.get('picking')
            printer = data.get('printer')

            if not picking.date_delivered or picking.state != 'done':
                picking.date_delivered = False

            if picking and printer:
                picking.print_container_label(printer=printer)

            if picking:
                # Check the state of this picking
                picking.compute_preparation_state()

                if picking.preparation_state == 'wait':
                    data['warning'] = _("This preparation is waiting after product to finish.")
                elif picking.preparation_state in ['pick', 'weight', 'label']:
                    data['warning'] = _("The preparation is not finish.")
            else:
                data['warning'] = _("No picking to check")

            # Invoice this picking
            if picking and not data.get('warning'):
                # picking validation and print document
                data.pop('end_preparation', None)
                picking.button_validate()
                data['message'] = picking.preparation_end()
                # TODO pas d'impression mais ok depuis l'interface? picking
                #picking.action_send_invoice_and_delivery()
                # BUG sur action_send_invoice_and_delivery
        return data

    def delete_data_key(self, data, key):
        """ return data with deleting key """
        if key in list(data.keys()):
            del data[key]
        return data