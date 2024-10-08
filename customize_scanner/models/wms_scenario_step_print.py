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

    def check_job(self, data):
        """ return print job to do """
        data = self.init_data(data)
        session = self.env['wms.session'].get_session()
        job_ids = self.env['wms.print.job'].search([('state', '=', 'todo'), ('session_id', '=', session.id)])
        for job in job_ids:
            if job.res_model == 'stock.lot':
                lot = self.env['stock.lot'].browse(job.res_id)
                data['lot_id'] = lot
                break
        data['button_print_later'] = True
        data['job'] = job_ids
        return data

    def save_job(self, data):
        """ Save lot to print has a job """
        lot = data.get('lot_id') or data.get('production_lot_id')
        if data.get('production_id') and data['production_id'].lot_producing_id:
            lot = data['production_id'].lot_producing_id

        if lot:
            session = self.env['wms.session'].get_session()
            job_ids = self.env['wms.print.job'].search([
                ('res_model', '=', 'stock.lot'), ('res_id', '=', lot.id),
                ('session_id', '=', session.id), ('state', '=', 'todo')])
            if job_ids:
                job_ids[0].label_qty += 1
            else:
                job_vals = {
                    'name': f'Lot: {lot.ref} ,{lot.product_id.name}',
                    'res_model': 'stock.lot',
                    'res_id': lot.id,
                    'label_qty': 1,
                    'session_id': session.id,
                }
                job_ids = self.env['wms.print.job'].create(job_vals)

            data['job'] = job_ids
            data['message'] = _('Print label later: ') + str(int(job_ids[0].label_qty))
        return data

    def print_lot(self, data):
        """ Print the production lot """

        self.ensure_one()
        if data.get('printer'):
            session = self.env['wms.session'].get_session()
            job_ids = self.env['wms.print.job'].search([('state', '=', 'todo'), ('session_id', '=', session.id)])

            for job in job_ids:
                job.print_label(data)

            if data.get('job'):
                del data['job']

        return data

    def print_current_lot(self, data):
        """ At the end print production lot """

        if data.get('button', '') == 'print_later':
            if not data.get('job'):
                data = self.save_job(data)
            data = self.init_data(data)
            data.update({'button_print_later': True})
        else:
            data = self.save_job(data)
            data = self.print_lot(data)
            if data.get('printer'):
                del data['printer']
        return data

    def print_later(self, data):
        """ Create pool printing with lot in data """
        self.ensure_one()
        data = self.save_job(data)
        return data

    def info_message_print(self, data):
        """ Check print before message """
        print('-----------------data-------------------------', data)
        if data.get('button', '') == 'print_later':
            self.save_job(data)
            data = self.init_data(data)

        if data.get('lot_id'):
            data['button_print_later'] = True

        return data
