# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import json
from odoo.http import request
import datetime
import logging
logger = logging.getLogger('wms_scanner')


class WmsPrintJob(models.Model):
    _inherit = "wms.print.job"

    def print_label(self, data=None):
        """ print the job """
        printer = data.get('printer')
        print('\n---------print_label---------------------', data)
        if not printer:
            return data

        for job in self:
            # Get label
            label_id = self.env['printing.label.zpl2'].search([('model_id.model', '=', job.res_model)])
            record_id = self.env[job.res_model].search([('id', '=', job.res_id)])
            print('\n---------print_label---------------------', label_id, record_id)
            if label_id and record_id:
                label_id.print_label(printer, record_id)
                job.state = 'done'
