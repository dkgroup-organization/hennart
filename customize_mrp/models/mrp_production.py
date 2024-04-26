# -*- coding: utf-8 -*-


from odoo import api, fields, models
from datetime import datetime, timedelta
import unicodedata
import logging

_logger = logging.getLogger(__name__)


class MRPProduction(models.Model):
    _inherit = 'mrp.production'

    sale_id = fields.Many2one('sale.order', string="Sale order", compute='_compute_sale_order', store=True)
    partner_id = fields.Many2one('res.partner', string="Partner", compute='_compute_sale_order', store=True)

    @api.depends('procurement_group_id')
    def _compute_sale_order(self):
        """ sale order """
        for production in self:
            sale_id = False
            partner_id = False
            if production.procurement_group_id.sale_id:
                sale_id = production.procurement_group_id.sale_id
                partner_id = production.procurement_group_id.sale_id.partner_id
            production.sale_id = sale_id
            production.partner_id = partner_id

    def action_generate_serial(self):
        """ generate serial """
        self.ensure_one()
        if self.product_id:
            self.lot_producing_id = self.env['stock.lot'].create_production_lot(product=self.product_id)
        if self.product_id.tracking == 'serial':
            self._set_qty_producing()


