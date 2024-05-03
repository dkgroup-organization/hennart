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

            data['message'] = _('The lot is printed')
        return data
