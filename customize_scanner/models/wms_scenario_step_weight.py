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

    def print_lot(self, data):
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
                job = self.env['wms.print.job'].create(job_vals)

            job_ids = self.env['wms.print.job'].search([('state', '=', 'todo')])
            if job_ids:
                for job in job_ids:
                    job.print_label(data)
            del data['printer']

        return data
