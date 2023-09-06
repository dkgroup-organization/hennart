# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################

from odoo import api, fields, models, _, Command


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    #date_delivered = fields.Datetime("delivered date", compute='compute_date_delivered', help="Customer delivered date")
    picking_type_code = fields.Selection(string='Code', related="picking_type_id.code")

    def compute_date_delivered(self):
        """ Custom delivery, Always delivery at one time with no backorder"""
        for picking in self:
            if picking.state in ['done', 'cancel']:
                continue
            if not picking.date_delivered:
                picking.date_delivered = fields.Datetime.now()
