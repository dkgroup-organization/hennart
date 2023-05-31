# 2020 Joannes Landy <joannes.landy@opencrea.fr>
# Based on the work of sylvain Garancher <sylvain.garancher@syleam.fr>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging
from odoo import models, api, fields, _
from odoo.exceptions import MissingError, UserError, ValidationError

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
        # 53201523101X010120000000  -24 DIGI machine frais emballé [11]
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
            if lot_name[5] == '-' and lot_name[1:].isnumeric():
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
                    if lot_ids:
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
