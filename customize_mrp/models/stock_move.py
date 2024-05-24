# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
import logging
from datetime import datetime, timedelta
_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    def action_mrp(self):
        """ Check if all product with BOM need manufacture, recursive analyse """
        self.product_id.action_normal_mrp()
