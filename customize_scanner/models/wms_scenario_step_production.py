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

    def get_production_ids(self, data):
        """ Get the current production todo """
        self.ensure_one()
        production_ids = self.env['mrp.production']
        option = dict(request.params).get('option', '')
        button = dict(request.params).get('button', '')
        production_condition = [('state', 'not in', ['draft', 'cancel', 'done'])]
        all_production_ids = self.env['mrp.production'].search(production_condition, order='date_planned_start')
        new_data = self.init_data()

        if button == "update_production" and data.get('partner_ids'):
            option = 'production_partner'
        if button == "update_production" and data.get('categ_ids'):
            option = 'production_categ'

        if button == 'new_production':
            production_vals = {'user_id': self.env.user.id}
            new_data['button'] = 'new_production'

        elif option == 'production_categ':
            categ_ids = self.env['product.category']
            for production in all_production_ids:
                if not production.partner_id:
                    categ_ids |= production.product_id.categ_id
            new_data.update({'categ_ids': categ_ids})

        elif option == 'production_partner':
            partner_ids = self.env['res.partner']
            for production in all_production_ids:
                if production.partner_id:
                    partner_ids |= production.partner_id
            new_data.update({'partner_ids': partner_ids})

        elif data.get('partner_id'):
            if type(data.get('partner_id')) == str:
                data['partner_id'] = self.env['res.partner'].search([('id', '=', int(data.get('partner_id')))])
            production_condition += [('partner_id', '=', data['partner_id'].id)]
            production_ids = self.env['mrp.production'].search(production_condition)

        elif data.get('categ_id'):
            if type(data.get('categ_id')) == str:
                data['categ_id'] = self.env['product.category'].search([('id', '=', int(data.get('categ_id')))])
            production_condition += [('product_id.categ_id', '=', data['categ_id'].id)]
            production_ids = self.env['mrp.production'].search(production_condition)

        if type(data.get('production_id')) == str:
            new_data = self.check_production_id(data)

        if production_ids:
            new_data.update({'production_ids': production_ids})

        return new_data

    def change_production_date(self, data):
        """ Change the date of production lot """
        self.ensure_one()
        if data.get('production_id'):
            if data['production_id'].lot_producing_id:
                production_lot = data['production_id'].lot_producing_id
                if data.get('expiry_date'):
                    production_lot.expiration_date = data['expiry_date']
                    del data['expiry_date']
                else:
                    data['warning'] = _("Enter a valid date.")
            else:
                data['warning'] = _("Create a lot before change the date.")
        else:
            data['warning'] = _("This production is no longer available")
        return data

    def check_production_id(self, data):
        """ Check or create new production if there is no current available """
        self.ensure_one()
        production = self.env['mrp.production']

        if data.get('production_id'):
            # This production is to check
            if type(data.get('production_id')) == str:
                # initialise production data. When the production_id is str, it is a menu choice
                data['production_id'] = self.env['mrp.production'].browse(int(data.get('production_id')))
                production = data.get('production_id')
                if production:
                    data = self.init_data()
                    data['production_id'] = production

            if type(data.get('production_id')) == type(self.env['mrp.production']):
                production = data['production_id']
                data['production_product_id'] = data['production_id'].product_id
            else:
                data['warning'] = _("This production is no longer available")
                return data

            # Check the lot
            if data.get('lot_id') and type(data['lot_id']) == type(self.env['stock.lot']):
                lot = data.get('lot_id')
                if production and lot:
                    if lot.product_id != production.product_id:
                        data['warning'] = _("It is not the good product")
                        return data
                    elif production.sale_id and production.lot_producing_id != lot:
                        # When the production is for a customer, the lot is already created
                        data['warning'] = _("It is not the good lot number")
                        return data
                    else:
                        data['production_product_id'] = data['production_id'].product_id

        elif data.get('lot_id') and type(data['lot_id']) == type(self.env['stock.lot']):
            # No production selected, find one or create one if needed
            lot = data['lot_id']
            production_ids = self.env['mrp.production'].search([
                ('lot_producing_id', '=', lot.id), ('state', '!=', 'cancel')])

            if len(production_ids) == 1:
                # a production exist with this lot
                data = self.init_data()
                data['production_id'] = production_ids
                data['production_product_id'] = production_ids.product_id
                data['production_lot_id'] = production_ids.lot_producing_id

            elif not production_ids and len(lot.quant_ids) == 0:
                # no production but a new lot exist
                if lot.product_id.bom_ids and lot.product_id.bom_ids[0].type == "normal":

                        mo_vals = {
                            'product_id': lot.product_id.id,
                            'product_qty': 1,
                            'origin': 'scanner',
                            'bom_id': lot.product_id.bom_ids[0].id,
                            'lot_producing_id': lot.id,
                        }
                        new_mo = self.env['mrp.production'].create(mo_vals)
                        new_mo._compute_move_raw_ids()
                        new_mo.move_raw_ids.put_quantity_done()
                        new_mo.action_confirm()
                        data = self.init_data()
                        data['production_id'] = new_mo
                        data['production_product_id'] = new_mo.product_id
                        data['production_lot_id'] = new_mo.lot_producing_id
                else:
                    data['warning'] = _("This product is not configured to create production")
            else:
                data['warning'] = _("This lot is already used, you cannot create a new production with it")

        elif data.get('label_lot') and data.get('label_date') and data.get('label_product'):
            # In this case, Create a new lot and a new production
            if data['label_product'].bom_ids and data['label_product'].bom_ids[0].type == "normal":
                # Create the new lot
                lot_vals = {
                    'name': data['label_lot'],
                    'product_id': data['label_product'].id,
                    'expiration_date': data['label_date'],
                }
                lot = self.env['stock.lot'].create(lot_vals)

                # Create OF with origin location and product
                mo_vals = {
                    'product_id': data['label_product'].id,
                    'product_qty': 1,
                    'origin': 'scanner',
                    'user_id': self.env.user.id,
                    'bom_id': data['label_product'].bom_ids[0].id,
                    'lot_producing_id': lot.id,
                }
                new_mo = self.env['mrp.production'].create(mo_vals)
                new_mo._compute_move_raw_ids()
                new_mo.move_raw_ids.put_quantity_done()
                new_mo.action_confirm()
                data = self.init_data()
                data['production_id'] = new_mo
                data['production_product_id'] = new_mo.product_id
                data['production_lot_id'] = new_mo.lot_producing_id

            else:
                data['warning'] = _("This product have no production configuration")

        return data

    def put_production_quantity(self, data):
        """ Register the quantity produced """
        self.ensure_one()

        if data.get('production_id') and data['production_id'].state in ['cancel', 'done']:
            data['warning'] = _('This production order is already finished')

        elif data.get('production_id') and data.get('production_quantity', 0.0) > 0.0:
            production = data['production_id']
            production.user_id = self.env.user
            production.change_quantity_needed(data['production_quantity'])
            production.change_quantity_producing()

        elif data.get('production_quantity', 0.0) <= 0.0:
            data['warning'] = _('Put positive quantity on production')
        else:
            data['warning'] = _('This production order is not to do')

        return data

    def get_production_move_line(self, data):
        """ Return production move line with tracking lot """
        self.ensure_one()
        new_data = self.init_data()

        if data.get('production_id') and data['production_id'].state not in ['cancel', 'done']:
            production = data['production_id']
            new_data['production_id'] = production
            new_data['production_product_id'] = production.product_id

            for move in production.move_raw_ids:
                if not move.move_line_ids:
                    move.put_quantity_done()

            for move_line in production.move_raw_ids.move_line_ids:
                if move_line.state in ['cancel', 'done']:
                    continue
                elif move_line.product_id.tracking != 'none' and not move_line.lot_id:
                    new_data['move_line'] = move_line
                    new_data['product_id'] = new_data['move_line'].product_id
                    new_data['quantity'] = new_data['move_line'].qty_done
                    break
        else:
            data['warning'] = _('This production order is not to do')

        data = new_data
        return data

    def check_production_move_line(self, data):
        """ Check if move_line is complete """
        self.ensure_one()
        if data.get('move_line') and data.get('lot_id'):
            if data['move_line'].product_id != data['lot_id'].product_id:
                data['warning'] = _('This not the good product')
            else:
                source_location = data['move_line'].production_id.location_src_id
                location_origin_ids = self.env['stock.location'].search([('id', 'child_of', source_location.id)])
                quant_ids = self.env['stock.quant'].search([
                    ('lot_id', '=', data['lot_id'].id), ('location_id', '=', location_origin_ids.ids)])

                if (not quant_ids) or sum(quant_ids.mapped('quantity')) < data['move_line'].qty_done:
                    data['warning'] = _('There is not enough quantity on production, move the component on production '
                                        'zone before')
                else:
                    data['move_line'].lot_id = data['lot_id']
                    data['move_line'].qty_done = data['move_line'].reserved_uom_qty

        elif data.get('move_line'):
            data['warning'] = _('This lot is unknown')
        else:
            data['warning'] = _('No component product to check')
        return data

    def confirm_production(self, data):
        """ Confirm the production """
        self.ensure_one()
        if data.get('production_id') and data['production_id'].state not in ['cancel', 'done']:
            production = data['production_id']
            if production.state == 'to_close':
                production.button_mark_done()
        return data

    def get_list_option(self, data):
        """ Return list of option of select input """
        self.ensure_one()
        res = []
        product = data.get('product_id')
        if product and self.action_variable == 'maturity_product_id':
            res.append((f'{product.id}', f'[{product.default_code}] {product.name}'))
            if product.gestion_affinage:
                list_maturity_product = product.get_maturity_product()
                for maturity_product in list_maturity_product[product.id]:
                    product_name = f'[{maturity_product.default_code}] {maturity_product.name}'
                    res.append((f'{maturity_product.id}', product_name))
        return res

    def change_lot(self, data):
        """ Change lot date, or change maturity_product """
        self.ensure_one()
        product = data.get('product_id')
        maturity_product = data.get('maturity_product_id')
        lot = data.get('lot_id')
        expiry_date = data.get('expiry_date')
        location_origin = data.get('location_origin_id')
        quantity = data.get('quantity')

        if not (product and lot and expiry_date and location_origin and quantity):
            data['warning'] = _('Not enough information to change lot characteristics')
            return data

        if product and not maturity_product:
            maturity_product = product

        # Create the new lot
        lot_vals = {
            'name': lot.name,
            'product_id': maturity_product.id,
            'expiration_date': expiry_date,
        }
        maturity_lot = self.env['stock.lot'].create(lot_vals)

        # Create OF with origin location and product
        mo_vals = {
            'product_id': maturity_product.id,
            'product_qty': quantity,
            'origin': 'scanner',
            'bom_id': False,
            'lot_producing_id': maturity_lot.id,
            'location_src_id': location_origin.id,
            'location_dest_id': location_origin.id,
        }
        new_mo = self.env['mrp.production'].create(mo_vals)

        # Create stock.move with composant
        move_vals = {
            'product_id': product.id,
            'location_id': location_origin.id,
            'location_dest_id': new_mo.production_location_id.id,
            'product_uom_qty': quantity,
            'product_uom': product.uom_id.id,
            'raw_material_production_id': new_mo.id,
            'picking_type_id': new_mo.picking_type_id.id,
            'manual_consumption': True,
        }
        new_move = self.env['stock.move'].create(move_vals)
        new_mo.action_confirm()

        # Update move.line with lot and quantity done
        new_move.quantity_done = quantity
        new_move.put_quantity_done()
        new_move.move_line_ids.update({'lot_id': lot.id})

        # confirm production
        new_mo.qty_producing = quantity
        new_mo.with_context(skip_expired=True).button_mark_done()

        # Return MO to data
        data['mo_id'] = new_mo

        return data

    def print_production_label(self, data):
        """ At the end print production lot """
        self.ensure_one()
        session = self.env['wms.session'].get_session()
        production = data.get('production_id')
        if production and production.lot_producing_id:
            job_vals = {
                'name': f'Lot: {production.lot_producing_id.ref} ,{production.lot_producing_id.product_id.name}',
                'res_model': 'stock.lot',
                'res_id': production.lot_producing_id.id,
                'session_id': session.id,
            }
            job_id = self.env['wms.print.job'].create(job_vals)

            if data.get('printer'):
                job_id.print_label(data)
                # Del the printer after each print
                del data['printer']
        return data
