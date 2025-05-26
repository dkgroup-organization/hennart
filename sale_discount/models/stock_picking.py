# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################

from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    sale_id = fields.Many2one('sale.order', string='Sale Order', compute='_compute_sale_id', store=True, readonly=False)
    sale_total_weight = fields.Float(string='Sale Total Weight', compute='_compute_sale_total_weight', store=True)

    @api.depends('origin')
    def _compute_sale_id(self):
        for picking in self:
            if picking.picking_type_code == 'outgoing' and picking.origin:
                order = self.env['sale.order'].search([('name', '=', picking.origin)], limit=1)
                picking.sale_id = order if order else False
            else:
                picking.sale_id = False

    @api.depends('sale_id.total_weight')
    def _compute_sale_total_weight(self):
        for picking in self:
            picking.sale_total_weight = picking.sale_id.total_weight if picking.sale_id else 0.0
