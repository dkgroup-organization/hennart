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
    res_id = fields.Integer('record ID')
    error = fields.Text('Error')
    state = fields.Selection(string='Status', selection=[
        ('todo', 'To do'),
        ('cancel', 'Cancelled'),
        ('done', 'Done')],
        copy=False, index=True, readonly=True,
        default='todo')
