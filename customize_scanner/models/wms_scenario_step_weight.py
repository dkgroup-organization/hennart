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

    def print_weighed_lot(self, data):
        """ Print the production lot """
        self.ensure_one()
        if data.get('printer'):
            session = self.env['wms.session'].get_session()

            if data.get('lot_id'):
                lot = data.get('lot_id')
                job_vals = {
                    'name': f'Lot: {lot.ref} ,{lot.product_id.name}',
                    'res_model': 'stock.lot',
                    'res_id': lot.id,
                    'session_id': session.id,

                }

                if data.get('weighting_device'):
                    weight_device = data['weighting_device'].get_weight(data=data)
                    if data.get('weight', 0.0) > 0.0:
                        tare = self.get_tare(data)


                job = self.env['wms.print.job'].create(job_vals)

                # Get weight
                # print label with context weight

                # job.print_label(data)
                # del the weighed device



                del data['printer']

        return data
