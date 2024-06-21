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

    def print_weighted_lot(self, data):
        """ Print the production lot """
        self.ensure_one()
        new_data = self.init_data()
        if data.get('lot_id') and data.get('printer'):
            new_data['lot_id'] = data['lot_id']
            new_data['printer'] = data['printer']

        if data.get('printer'):
            session = self.env['wms.session'].get_session()

            if data.get('lot_id'):
                lot = data.get('lot_id')

                if data.get('weighting_device'):
                    weight_device = data['weighting_device'].get_weight(data=data)

                    if weight_device > 0.0:
                        tare = self.get_tare(data)
                        weight = weight_device - tare

                        job_vals = {
                            'name': f'Lot: {lot.ref} ,{lot.product_id.name}',
                            'res_model': 'stock.lot',
                            'res_id': lot.id,
                            'session_id': session.id,
                            }
                        new_job = self.env['wms.print.job'].create(job_vals)
                        new_job.put_context(job_context={'weight': weight})
                        new_job.print_label(data=data)

                    else:
                        new_data['warning'] = _('The weight must be positive')
        return new_data
