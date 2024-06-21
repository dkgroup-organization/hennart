# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import json
from odoo.http import request
import datetime
import json
import logging
logger = logging.getLogger('wms_scanner')


class WmsPrintJob(models.Model):
    _inherit = "wms.print.job"

    def print_label(self, data=None):
        """ print the job """
        printer = data.get('printer')
        if not printer:
            return data

        for job in self:
            # Get label
            if job.label_id:
                label = self.env['printing.label.zpl2'].browse(job.label_id)
            else:
                label = self.env['printing.label.zpl2'].search([('model_id.model', '=', job.res_model)])

            if label:
                record_id = self.env[job.res_model].search([('id', '=', job.res_id)])
                if record_id:
                    if job.context:
                        job_context = job.get_context()
                        if job_context.get('weight'):
                            label.with_context(weight=job_context.get('weight')).print_label(printer, record_id)
                    else:
                        label.print_label(printer, record_id)
                    job.state = 'done'
                else:
                    job.state = 'error'
            else:
                job.state = 'error'
