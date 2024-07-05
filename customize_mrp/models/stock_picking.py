# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################

from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError
from datetime import datetime, timedelta


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_mrp(self):
        """ Check if all product with BOM need manufacture, recursive analyse """
        self.move_ids_without_package.action_mrp()
