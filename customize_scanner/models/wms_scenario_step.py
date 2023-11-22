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


    @api.model
    def get_date_scanning(self, scan):
        """ Check and return the date"""
        pass

    def scan_multi(self, data, scan, action_variable=""):
        """Function to return value when the scan is custom:
        lot production construction code
        5 char: product code
        6-? char: stock.lot.id or lot name
        1 char: product code end
        6-8 char: expiration date
        6 char: weight

        The product code is to check if there is a package.
        """
        self.ensure_one()

        # Detect the old barcode (reference used by V7) 24 or 25 or 26 length
        # 53201523101X010120000000  -24 DIGI machine frais emballé [11], la date est inversé
        # 53201523101X01012020000000 -26 espera: no id , external production [11]
        # 532010004459X010120000000 -25 old id - [:5][5:12][12][13:19][19:]
        # 01013-0066036B090320000000 -26 new_id [13]

        data_origin = data.copy()
        data = {}

        if len(scan) >= 24:
            # In this case , the barcode is composite and it is customer barcode

            # detect the product
            product = self.env['product.product']
            product_tmpl = self.env['product.product']
            affinage = -13
            if not scan[affinage].isalpha():
                affinage = -15
            if scan[affinage].isalpha():
                if scan[affinage] == "X":
                    product_code = scan[:5]
                else:
                    product_code = scan[:5] + scan[affinage]

                # Check if the product exist
                product_ids = self.env['product.product'].search([('default_code', '=', product_code)])
                if len(product_ids) == 1:
                    product_tmpl = product_ids
                    # check if it is a package
                    product = product_tmpl.base_product_tmpl_id.product_variant_id or product_tmpl
                    data['lot_code'] = product.default_code

                else:
                    data['warning'] = _("Barcode error, The product is unknown: ") + product_code
            else:
                data['warning'] = _("Barcode format error.")

            # get the weight
            if not data.get('warning'):
                weight = scan[-6:]
                if '.' not in weight:
                    # By convention, if there is no dote, the decimal is three digit.
                    weight = weight[:3] + '.' + weight[3:]
                try:
                    weight_kg = float(weight)
                    if weight_kg:
                        data['label_weight'] = weight_kg
                except:
                    data['warning'] = _("Reading weight error:") + " {}".format(weight)

            # if there is a weight this barcode is a label, use base unit count to have package quantity
            if product and not data.get('warning'):
                if data.get('label_weight') or product != product_tmpl:
                    data['label_quantity'] = product_tmpl.base_unit_count

            # Define the date
            if not data.get('warning'):
                if scan[affinage + 1:affinage + 5].isnumeric() and scan[-8:-6].isnumeric():
                    date_year = '20' + scan[-8:-6]
                    date_day = scan[affinage + 1:affinage + 3]
                    date_month = scan[affinage + 3:affinage + 5]
                    try:
                        data['lot_date'] = fields.Datetime.from_string(f"{date_year}-{date_month}-{date_day} 12:00:00")
                    except:
                        data['warning'] = _("Error on date format.")
                else:
                    data['warning'] = _("Error on date format.")

            # find the lot
            if product and not data.get('warning'):
                lot_name = scan[5:affinage]
                # by convention new lot_id (2023) start with '-'
                if (lot_name[0] == '-') and lot_name[1:].isnumeric():
                    lot_id = int(lot_name[1:])
                    lot_ids = self.env['stock.lot'].search([('id', '=', lot_id)])
                    if lot_ids:
                        if lot_ids.product_id == product:
                            data['lot_id'] = lot_ids
                        else:
                            data['warning'] = _("This lot has not the good product.")
                    else:
                        data['warning'] = _("This lot is removing.")
                else:
                    old_barcode = scan[:-6] + "000000"
                    if product != product_tmpl:
                        old_barcode = product.default_code[:5] + old_barcode[5:]

                    # old_barcode or barcode_ext is external barcode making by another system
                    for barcode_field in ['barcode_ext', 'temp_old_barcode', 'temp2_old_barcode']:
                        lot_ids = self.env['stock.lot'].search([(barcode_field, '=', old_barcode)])
                        if len(lot_ids) > 1:
                            data['warning'] = _("There is more than one lot with the same name and date: {}".format(old_barcode))
                        elif lot_ids and lot_ids.product_id == product:
                            data['lot_id'] = lot_ids[0]
                            break
                        elif lot_ids:
                            data['warning'] = _("This lot has not the good product.")
                            print(lot_ids, lot_ids.product_id , product, product_tmpl)

                    if data.get('lot_date') and not data.get('lot_id'):
                        # Maybe there is a error on date
                        lot_ids = self.env['stock.lot'].search([('name', '=', lot_name),
                                                                ('product_id', '=', product.id)])
                        if len(lot_ids) == 1 and \
                                lot_ids.expiration_date.strftime('%Y-%m-%d') != data['lot_date'].strftime('%Y-%m-%d'):
                            data['warning'] = _("The expiration date of this label is not correct: {}".format(data['lot_date'].strftime('%d-%m-%T')))

            # Get the lot name to possible creation if lot is finding
            if product and data.get('lot_date') and not data.get('lot_id'):
                # In this case the lot is to create by use lot_name, lot_product, lot_date
                data['lot_name'] = scan[5:affinage]
                data['lot_product'] = product

        if len(scan) > 4 and scan[:4] == BARCODE_WEIGHT:
            # In this case, it is a weighted device
            weight_device_ids = self.env['stock.weight.device'].search([('barcode', '=', scan)])
            if len(weight_device_ids) == 1:
                # weighting_device
                data['weighting_device'] = weight_device_ids
            else:
                data['warning'] = "No Weight device finding"

        if len(scan) > 4 and scan[:4] == BARCODE_PRINTER:
            # In this case, it is a printer
            pass

        if data.get('warning'):
            data_origin['warning'] = data.get('warning')
        else:
            data_origin.update(data)

            if self.action_scanner in ['scan_info']:
                for odj_name in ['lot_id', 'product_id', 'weight_id']:
                    if data_origin.get(odj_name):
                        data_origin['scan'] = data_origin[odj_name]
        return data_origin

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

            if data.get('lot_id'):
                inventory_vals['lot_id'] = data['lot_id'].id
                condition.append(('lot_id', '=', data['lot_id'].id))
            else:
                if data['product_id'].tracking == 'lot':
                    data['warning'] = "This product need a lot number"
                    data['result'] = False
                    return data

            quant_ids = self.env['stock.quant'].search(condition)
            if quant_ids:
                quant_ids[0].inventory_quantity = data['quantity']
                quant_ids[0].user_id = self.env.user
                quant_ids[0].inventory_quantity_set = True
                #quant_ids[0].action_apply_inventory()
            else:
                new_inventory = self.env['stock.quant'].create(inventory_vals)
                new_inventory.inventory_quantity_set = True
                #new_inventory.action_apply_inventory()
            data = self.init_data(data)
            data.update({
                'result': True,
                'message': 'The inventory is done'})
        else:
            data['result'] = False
        return data

    def check_product_location_qty(self, data):
        """
        Vérifie que data contient location_origin_id, product_id,
        qu'il y a bien des stock.quant correspondant
        si le produit a un tracking par lot (la grande majorité des cas)
        vérifie si data à lot_id est qu'il y a bien des quant correspondant
        si un problème: "warning" à data avec un message
       "This product {} is not registred in this location {}"
       "This product {} need a production lot "
        """
        if data.get('product_id') and (data.get('location_id') or data.get('location_origin_id')):
            condition = [
                ('product_id', '=', data['product_id'].id),
                ('location_id', '=', (data['location_id'] or data['location_origin_id']).id)]

            if data.get('lot_id'):
                condition.append(('lot_id', '=', data['lot_id'].id))
            elif data['product_id'].tracking == 'lot':
                data['warning'] = "This product need a lot number"
            else:
                condition.append(('lot_id', '=', False))

            quant_ids = self.env['stock.quant'].search(condition)

            if not quant_ids:
                data['warning'] = "This product is not registered on this location"
            elif data.get('quantity'):
                quantity = sum(quant_ids.mapped('available_quantity'))
                if data.get('lot_id') and quantity < data['quantity']:
                    data['warning'] = _("There is not enough quantity in this lot. The maximum is {}").format(quantity)
                elif quantity < data['quantity']:
                    data['warning'] = _("There is not enough quantity on the location. The maximum is {}").format(quantity)
        else:
            data['warning'] = _("Some information are missing to check product on location.")

        return data

    @api.model
    def move_product(self, data):
        """
        Recherche un internal picking pour l'utilisateur 1 par jour et par utilisateur pour les mouvements du scanner de la journée,
        name = MV2023-06-08 {user.login) créer unle picking si pas dispo
        créer le mouvement de stock avec les variables location_origin_id, product_id, lot_id, location_dest_id, quantity
        si ok ajouter data['result'] = True
        """

        stock_location = self.env.ref('stock.stock_location_stock')
        picking_type = self.env.ref('stock.picking_type_internal')
        location_origin_id = data.get('location_origin_id') or data.get('location_id')
        location_dest_id = data.get('location_dest_id')

        product_id = data.get('product_id')
        lot_id = data.get('lot_id')
        weight = data.get('weight') or data.get('label_weight')
        quantity = data.get('quantity', 0)

        date_now = time.strftime('MV-%Y-%m-%d-')
        session = self.env['wms.session'].get_session()
        picking_name = date_now + "{}-{}".format(session.id, self.env.user.login)

        picking_stock = self.env['stock.picking'].search([('name', '=', picking_name), ('state', 'not in', ['cancel'])])
        if not picking_stock:
            picking_stock = self.env['stock.picking'].create({
                'name': picking_name,
                'user_id': self.env.user.id,
                'location_id': stock_location.id,
                'location_dest_id': stock_location.id,
                'picking_type_id': picking_type.id,
                'immediate_transfer': True,
                'show_operations': True,
            })

        move_vals = {
            'name': "scanner: " + picking_stock.name + ': ' + product_id.default_code,
            'location_id': location_origin_id.id,
            'location_dest_id':  location_dest_id.id,
            'product_id': product_id.id,
            'product_uom': product_id.uom_id.id,
            'product_uom_qty': quantity,
            'quantity_done': quantity,
            'picking_id': picking_stock.id,
            }
        new_move = picking_stock.move_ids_without_package.create(move_vals)
        new_move._action_confirm(merge=False)

        if picking_stock.state == 'draft':
            picking_stock.action_confirm()

        if lot_id:
            new_move.move_line_ids.lot_id = lot_id

        if weight:
            new_move.move_line_ids.weight = weight
        elif product_id:
            new_move.move_line_ids.weight = product_id.weight * quantity

        new_move.picking_id._action_done()

        if new_move.state == 'done':
            data = self.init_data(data)
            data['message'] = _("The previews move is registered")
            data['result'] = True
        else:
            data['result'] = False

        return data
