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
            if not partner_id:
                partner_id = self.env.company.partner_id
            production.sale_id = sale_id
            production.partner_id = partner_id

    def action_generate_serial(self):
        """ generate serial """
        self.ensure_one()
        if self.product_id:
            self.lot_producing_id = self.env['stock.lot'].create_production_lot(product=self.product_id)
        if self.product_id.tracking == 'serial':
            self._set_qty_producing()

    def button_mark_done(self):
        """ Change the quantity reserved when the produced qty is no same """
        for production in self:
            if production.state in ['cancel', 'done']:
                continue
            if production.product_qty > 0.0 and production.product_qty != production.qty_producing:
                factor = production.qty_producing / production.product_qty
                production.product_qty = production.qty_producing
                production.move_finished_ids.product_uom_qty = production.qty_producing
                production._update_raw_moves(factor)
                production._onchange_producing()
                production._compute_move_raw_ids()

        return super().button_mark_done()

    @api.onchange('qty_producing')
    def onchange_qty_producing(self):
        """ automaticaly update qty_producing """
        if self.state not in ['cancel', 'done']:
            if self.product_qty > 0.0 and self.product_qty != self.qty_producing:
                factor = self.qty_producing / self.product_qty
                self.product_qty = self.qty_producing
                self.move_finished_ids.product_uom_qty = self.qty_producing
                self._update_raw_moves(factor)
