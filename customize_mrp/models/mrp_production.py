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

    @api.depends('company_id', 'date_planned_start', 'is_planned', 'product_id')
    def _compute_date_planned_finished(self):
        for production in self:
            if production.is_planned:
                continue
            date_planned_start = production.date_planned_start or fields.Datetimes.now()
            production.date_planned_finished = date_planned_start + timedelta(hours=1)

    def _get_consumption_issues(self):
        """ No consumption issue, the operator can change the value  """
        issues = []
        return issues

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
        if self.product_id.tracking != 'none':
            self._set_qty_producing()

    def button_test(self):
        """ Used to test function"""
        self._compute_move_raw_ids()

    def change_quantity_needed(self, product_qty):
        """ change the quantity to produce """
        self.ensure_one()
        self.do_unreserve()

        if self.product_qty > 0.0 and self.product_qty != product_qty:
            factor = product_qty / self.product_qty
            self._update_raw_moves(factor)
            self.product_qty = product_qty
            self.move_finished_ids.product_uom_qty = product_qty
    
        self.move_raw_ids.move_line_ids.lot_id = False
        self.move_raw_ids.move_line_ids.qty_done = 0.0
        self.qty_producing = 0.0
        self._compute_move_raw_ids()

    def change_quantity_producing(self, product_qty=None):
        """ Update qty producing to quantity to do """
        self.ensure_one()
        self.qty_producing = product_qty or self.product_qty
        self._onchange_producing()
        self._compute_move_raw_ids()
        for move in self.move_raw_ids:
            move.quantity_done = move.product_uom_qty
            move.put_quantity_done()

    @api.model
    def create_forecast_om(self, warehouse, product, forecast_qty):
        """ Create OF to produce forecast quantity to replenish the stock """
        def get_modulo_qty(product, quantity):
            if product.min_production_qty:
                modulo_qty = int(quantity) / int(product.min_production_qty)
                if modulo_qty * int(product.min_production_qty) < int(quantity):
                    modulo_qty += 1
                return float(modulo_qty * int(product.min_production_qty))
            else:
                return quantity

        res = self.env['mrp.production']
        # Check if there is already a OF waiting (not started)
        mo_ids = self.search([('product_id', '=', product.id),
                              ('lot_producing_id', '=', False),
                              ('state', 'in', ['confirmed'])])

        if mo_ids:
            # Check if the warehouse is ok: (only one warehouse)
            # Check the quantity
            production = mo_ids[0]
            total_qty = get_modulo_qty(product, production.product_qty + forecast_qty)
            production.change_quantity_needed(total_qty)
            res |= production
        else:
            mo_vals = {
                'product_id': product.id,
                'product_qty': get_modulo_qty(product, forecast_qty),
                'origin': 'Stock',
                'user_id': False,
                'bom_id': product.bom_ids[0].id,
            }
            new_mo = self.env['mrp.production'].create(mo_vals)
            new_mo._compute_move_raw_ids()
            new_mo.move_raw_ids.put_quantity_done()
            new_mo.action_confirm()
            res |= new_mo

        return res
            




