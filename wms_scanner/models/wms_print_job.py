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
    _name = "wms.print.job"
    _description = "Scanner print job"

    name = fields.Char('Description')
    session_id = fields.Many2one('wms.session', 'Session')
    res_model = fields.Char('Model')
    res_id = fields.Integer('Record ID')
    label_id = fields.Integer('Label ID')
    label_qty = fields.Integer('Label qty')
    error = fields.Text('Error')
    context = fields.Text('context')
    state = fields.Selection(string='Status', selection=[
        ('todo', 'To do'),
        ('error', 'Error'),
        ('cancel', 'Cancelled'),
        ('done', 'Done')],
        copy=False, index=True, readonly=True,
        default='todo')

    def put_context(self):
        """ save the context of this created job """
        for job in self:
            job.context = json.dumps(self.env.context)

    def get_context(self):
        """ Get previous context """
        self.ensure_one()
        context = json.loads(self.context)
        return context

    def print_job(self, data):
        """ Print current job """
        if data.get('printer'):
            for job in self:
                # defined the api tu use
                pass

