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

    def weighted_tare(self, data):
        """ Get tare with this lot """
        self.ensure_one()
        if data.get('lot_id'):
            lot = data['lot_id']
            if lot.product_id.tare:
                data['tare'] = lot.product_id.tare
        return data

    def print_weighted_lot(self, data):
        """ Print the production lot """
        self.ensure_one()
        new_data = self.init_data()

        for key in ['lot_id', 'printer', 'button', 'tare']:
            if data.get(key):
                new_data[key] = data[key]

        if data.get('printer'):
            session = self.env['wms.session'].get_session()

            if data.get('lot_id'):
                lot = data.get('lot_id')
                if data.get('weighting_device'):
                    weight_id = data['weighting_device'].get_weight_id(data=data)

                    if weight_id:
                        weight_id.tare = self.get_tare(data)
                        weight = weight_id.weight - weight_id.tare

                        job_vals = {
                            'name': f'Lot: {lot.ref} , {weight} kg, {lot.product_id.name}',
                            'res_model': 'stock.weight.value',
                            'res_id': weight_id.id,
                            'session_id': session.id,
                            }
                        new_job = self.env['wms.print.job'].create(job_vals)
                        new_job.print_label(data=data)

                    else:
                        new_data['warning'] = _('No weight measured')
        return new_data

