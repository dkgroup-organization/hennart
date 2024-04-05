# -*- coding: utf-8 -*-


from odoo import api, fields, models
from datetime import datetime, timedelta
import unicodedata
import logging

_logger = logging.getLogger(__name__)


class MRPProduction(models.Model):
    _inherit = 'mrp.production'

    sale_id = fields.Many2one('sale.order', string="Sale order", compute='_compute_sale_order', store=True)

    @api.depends('procurement_group_id')
    def _compute_sale_order(self):
        for production in self:
            production.sale_id = production.procurement_group_id.sale_id
