# -*- coding: utf-8 -*-


from odoo import api, fields, models
from datetime import datetime, timedelta
import unicodedata
import logging

_logger = logging.getLogger(__name__)


class MRPProduction(models.Model):
    _inherit = 'mrp.production'

    # move_from_picking_ids = fields.Many2many('stock.move')

    
    move_from_picking_ids = fields.One2many(
        string='Moves from Pickings',
        comodel_name='stock.move',
        inverse_name='mrp_id',
    )
    
    

    