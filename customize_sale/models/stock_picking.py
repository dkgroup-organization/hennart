# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################

from odoo import api, fields, models, _, Command


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def compute_date_delivered(self):
        """ Define date delivered"""

        for picking in self:
            if picking.state in ['done', 'cancel']:
                continue
            if picking.sale_id:
                picking.date_delivered = picking.sale_id.date_delivered
            else:
                picking.date_delivered = fields.Datetime.now()
