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
        option = dict(request.params).get('option', '')
        production_condition = [('state', 'not in', ['draft', 'cancel', 'done'])]
        all_production_ids = self.env['mrp.production'].search(production_condition, order='date_planned_start')

        if option == 'production_categ':
            categ_ids = self.env['product.category']
            for production in all_production_ids:
                categ_ids |= production.product_id.categ_id
            data.update({'categ_ids': categ_ids})

        elif option == 'production_partner':
            partner_ids = self.env['res.partner']
            for production in all_production_ids:
                if production.partner_id:
                    partner_ids |= production.partner_id
            data.update({'partner_ids': partner_ids})

        elif all_production_ids:
            if data.get('partner_id'):
                if data.get('partner_id'):
                    if type(data.get('partner_id')) == str:
                        data['partner_id'] = self.env['res.partner'].search([('id', '=', int(data.get('partner_id')))])
                production_condition += [('partner_id', '=', data['partner_id'].id)]
                production_ids = self.env['mrp.production'].search(production_condition)
            elif data.get('categ_id'):
                if type(data.get('categ_id')) == str:
                    data['categ_id'] = self.env['product.category'].search([('id', '=', int(data.get('categ_id')))])
                production_condition += [('product_id.categ_id', '=', data['categ_id'].id)]
                production_ids = self.env['mrp.production'].search(production_condition)
            else:
                production_ids = all_production_ids
            data.update({'production_ids': production_ids})
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
        mo = data.get('mo_id')
        if mo and mo.lot_producing_id:
            job_vals = {
                'name': f'Lot: {mo.lot_producing_id.ref} ,{mo.lot_producing_id.product_id.name}',
                'res_model': 'stock.lot',
                'res_id': mo.lot_producing_id.id,
                'session_id': session.id,
            }
            job_id = self.env['wms.print.job'].create(job_vals)

            if data.get('printer'):
                job_id.print_label(data)

            data['message'] = _('The lot is changed')
        return data
