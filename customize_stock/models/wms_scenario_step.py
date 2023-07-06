# 2020 Joannes Landy <joannes.landy@opencrea.fr>
# Based on the work of sylvain Garancher <sylvain.garancher@syleam.fr>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging
from odoo import models, api, fields, _
from odoo.exceptions import MissingError, UserError, ValidationError
import time
import datetime

logger = logging.getLogger('wms_scanner')

#Define starting gencode for label
BARCODE_WEIGHT = '(91)'
BARCODE_PRINTER = '(98)'
BARCODE_LOCATION = '(01)'
BARCODE_PRODLOT = '(10)'



class WmsScenarioStep(models.Model):
    _inherit = 'wms.scenario.step'

    def scan_multi(self, data, scan, action_variable=""):
        """Function to return value when the scan is custom:
        lot production construction code
        5 char: product code
        6-? char: stock.lot.id or lot name
        1 char: product code end
        6-8 char: expiration date
        6 char: weight
        """
        self.ensure_one()

        # Detect the old barcode (reference used by V7) 24 or 25 or 26 length
        # 53201523101X010120000000  -24 DIGI machine frais emballé [11], la date est inversé
        # 53201523101X01012020000000 -26 espera: no id , external production [11]
        # 532010004459X010120000000 -25 old id - [:5][5:12][12][13:19][19:]
        # 01013-0066036B090320000000 -26 new_id [13]

        if len(scan) >= 24:

            # detection of date
            if scan[-10:-8] == '20':
                # specificity of ESPERA machine, the year is on 4 char
                date = scan[-14:-6]
                affinage = -15
            else:
                date = scan[-12:-6]
                affinage = -13

            # construction of the product code
            product_code = scan[:5]
            if scan[affinage] != 'X':
                product_code += scan[affinage]

            # get the weight
            weight = scan[-6:]
            if not '.' in weight:
                # By convention, if there is no dote, the decimal is three digit.
                weight = weight[:3] + '.' + weight[3:]

            try:
                weight_kg = float(weight)
                if weight_kg:
                    data['weight'] = weight_kg
            except:
                data['warning'] = _("Reading weight error:") + " {}".format(weight)

            # lot
            lot_name = scan[5:affinage]
            # by convention new lot_id start with '-'
            if (lot_name[0] == '-') and lot_name[1:].isnumeric():
                lot_id = int(lot_name[1:])
                lot_ids = self.env['stock.lot'].search([('id', '=', lot_id)])
                if len(lot_ids) == 1:
                    data['lot_id'] = lot_ids
                    data['product_id'] = lot_ids.product_id
                else:
                    data['warning'] = _("This lot is removing.")
            else:
                old_barcode = scan[:-6] + "000000"
                for barcode_field in ['barcode_ext', 'temp_old_barcode', 'temp2_old_barcode']:
                    lot_ids = self.env['stock.lot'].search([(barcode_field, '=', old_barcode)])
                    if len(lot_ids) > 1:
                        data['warning'] = _("There is more than one lot with the same name and date: {}".format(old_barcode))
                    elif lot_ids:
                        data['lot_id'] = lot_ids[0]
                        data['product_id'] = lot_ids[0].product_id
                        break

                if not data.get('lot_id'):
                    data['lot_name'] = scan[5:affinage]
                    date_year = scan[-8:-6]
                    date_day = scan[affinage+1:affinage+3]
                    date_month = scan[affinage+3:affinage+5]
                    data['lot_date'] = "20{year}-{month}-{day}".format(year=date_year, month=date_month, day=date_day)

            if not data.get('product_id'):
                # product
                product_ids = self.env['product.product'].search([('default_code', '=', product_code)])
                if len(product_ids) == 1:
                    data['product_id'] = product_ids

            if not data.get('lot_id'):
                data['lot_name'] = scan[5:affinage]
                year = '20' + scan[-8:-6]
                day = scan[affinage + 1:affinage + 3]
                month = scan[affinage + 3:affinage + 5]
                data['lot_expiration_date'] = "{}-{}-{} 12:00:00".format(year, month, day)

            if action_variable:
                data[action_variable] = data.get('lot_id') or data.get('product_id') or "?"

        return data

    @api.model
    def write_inventory(self, data):
        """ At the end of inventory process
        write the inventory line
        input: data = {
            location_origin_id: ...
            product_id:
            lot_id:
            quantity:
            }
        output: data add {'result' : True}
        """
        if data.get('location_origin_id') and data.get('product_id') and data.get('quantity'):
            inventory_vals = {
                'product_id': data['product_id'].id,
                'location_id': data['location_origin_id'].id,
                'inventory_quantity': data['quantity'],
                'user_id': self.env.user.id,
            }
            condition = [
                ('product_id', '=', data['product_id'].id),
                ('location_id', '=', data['location_origin_id'].id),
            ]

            if data['product_id'].tracking == 'lot' and data.get('lot_id'):
                inventory_vals['lot_id'] = data['lot_id'].id
                condition.append(('lot_id', '=', data['lot_id'].id))
            else:
                data['warning'] = "This product need a lot number"
                data['result'] = False
                return data

            quant_ids = self.env['stock.quant'].search(condition)
            if quant_ids:
                quant_ids[0].inventory_quantity = data['quantity']
                quant_ids[0].user_id = self.env.user
                quant_ids[0].action_apply_inventory()
            else:
                new_inventory = self.env['stock.quant'].create(inventory_vals)
                new_inventory.action_apply_inventory()
            data = self.init_data(data)
            data.update({
                'result': True,
                'message': 'The inventory is done'})
        else:
            data['result'] = False
        return data

    
    def check_product_location(self, data):

        """
        Vérifie que data contient location_origin_id, product_id,
        qu'il y a bien des stock.quant correspondant
        si le produit a un tracking par lot (la grande majorité des cas)
        vérifie si data à lot_id est qu'il y a bien des quant correspondant
        si un problème: "warning" à data avec un message
       "This product {} is not registred in this location {}"
       "This product {} need a production lot "
        """
        if data.get('location_origin_id') and data.get('product_id'):
            condition = [
                ('product_id', '=', data['product_id'].id),
                ('location_id', '=', data['location_origin_id'].id)]
        else:
            data['warning'] = "This product {} is not registred in this location {}".format(data.get('product_id'),data.get('location_origin_id'))
            data['result'] = False
            return data

        if data['product_id'].tracking == 'lot' and data.get('lot_id'):
                condition.append(('lot_id', '=', data['lot_id'].id))
        else:
                data['warning'] = "This product need a lot number"
                data['result'] = False
                return data

        quant_ids = self.env['stock.quant'].search(condition)
        if quant_ids:
            data['result'] = True
            return data
        else:
            data['warning'] = "This product need a lot number"
            data['result'] = False
            return data

    def check_product_qty(self, data):

        """
         Vérifie la quantité demandé:
        "There is only {} quantity of the lot on the location."
        """

        if data.get('location_origin_id') and data.get('product_id') and data.get('quantity')>0:
            condition = [
                ('product_id', '=', data['product_id'].id),
                ('location_id', '=', data['location_origin_id'].id),
            ]
        if data['product_id'].tracking == 'lot' and data.get('lot_id'):
                condition.append(('lot_id', '=', data['lot_id'].id))

        quant_ids = self.env['stock.quant'].search(condition)
        if quant_ids[0].available_quantity < data['quantity']:
            data['warning'] = "There is only {} quantity of the lot on the location.".format(quant_ids[0].available_quantity)
            data['result'] = False
            return data
        else:
           data['result'] = True
           return data


    @api.model
    def move_product(self, data):
        """
        Recherche un internal picking pour l'utilisateur 1 par jour et par utilisateur pour les mouvements du scanner de la journée,
        name = MV2023-06-08 {user.login) créer unle picking si pas dispo
        créer le mouvement de stock avec les variables location_origin_id, product_id, lot_id, location_dest_id, quantity
        si ok ajouter data['result'] = True
        """
        date_now = time.strftime('%Y-%m-%d')
        location_origin_id = data.get('location_origin_id').id
        location_dest_id = data.get('location_dest_id').id
        product_id = data.get('product_id').id
        uom_id = data.get('product_id').uom_id.id
        quantity = data.get('quantity')
        picking_name = "MV"+date_now+self.env.user.login
        picking_type = self.env.ref('stock.picking_type_internal').id


        picking_stock = self.env['stock.picking'].search([('name','=',picking_name)])
        if not picking_stock:
           picking_stock = self.env['stock.picking'].create({
            'name': picking_name,
            'location_id': location_origin_id,
            'location_dest_id': location_dest_id,
            'picking_type_id': picking_type,
        })
        move_stock = self.env['stock.move'].create({
            'name': 'stock_move',
            'location_id': location_origin_id,
            'location_dest_id':  location_dest_id,
            'product_id': product_id,
            'product_uom': uom_id,
            'product_uom_qty': quantity ,
            'picking_id': picking_stock.id,
        })

        if move_stock:
          data['result'] = True
          return data
        else:
          data['warning'] = "There is only {} quantity of the lot on the location.".format(quant_ids[0].inventory_quantity)
          data['result'] = False
          return data

    @api.model
    def init_data(self, data):
        """ return init data"""
        new_data = {
            'step': data['step'],
            'scenario': data['step'].scenario_id,
        }
        return new_data

