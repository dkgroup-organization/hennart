# -*- coding: utf-8 -*-


from odoo import api, fields, models
from datetime import datetime, timedelta
import unicodedata
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'mrp.production'

    # move_from_picking_ids = fields.Many2many('stock.move')

    
    
    

    