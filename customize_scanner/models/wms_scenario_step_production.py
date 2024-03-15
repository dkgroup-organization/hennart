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
        self.env['stock.move'].create(move_vals)
        new_mo.action_confirm()

        return data


        # Tester reservé ? marquer à faire ? valider la prod., valider avec forçage de lot expiré



