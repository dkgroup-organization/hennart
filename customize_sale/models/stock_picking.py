# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################

from odoo import api, fields, models, _, Command


class Stock_picking(models.Model):
    _inherit = 'stock.picking'

    date_delivered = fields.Datetime("delivered date", compute='_compute_date_deliverd',
        help="Customer delivered date")

    def _compute_date_deliverd(self):
        for picking in self:
            if picking.sale_id:
                picking.date_delivered = picking.sale_id.date_delivered
            else:
                picking.date_delivered = False
