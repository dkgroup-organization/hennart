# -*- coding: utf-8 -*-
from odoo import fields, models, api, Command
import logging
_logger = logging.getLogger(__name__)

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    date_planned = fields.Datetime(
        string='Warehouse date', index=True, copy=False, required=True,
        default=lambda self: fields.Datetime.now(),
        compute=False,
        help="Delivery date promised by vendor. This date is used to determine expected arrival of products.")

    def _compute_date_planned(self):
        """ Not used"""
        pass

    def button_confirm(self):
        """ Confirm purchase"""
        for order in self:
            if order.state not in ['draft', 'sent']:
                continue

            for line in self.order_line:
                if not line.product_qty:
                    line.unlink()
            #order.order_line._validate_analytic_distribution()
            #order._add_supplier_to_product()
            # Deal with double validation process
            if order._approval_allowed():
                order.button_approve()
            else:
                order.write({'state': 'to approve'})
            if order.partner_id not in order.message_partner_ids:
                pass
                #order.message_subscribe([order.partner_id.id])
        return True

    def _update_date_planned(self, updated_date):
        """ Update date """
        move_to_update = self.move_ids.filtered(lambda m: m.state not in ['done', 'cancel'])
        if move_to_update:
            self._update_move_date_deadline(updated_date)

    @api.onchange('partner_id')
    def onchange_partner_id_seller(self):

        self.order_line.unlink()

        if self.partner_id:
            line_vals = []
            seller_ids = self.env['product.supplierinfo'].search([
                ('partner_id', '=', self.partner_id.id),
                ('no_purchase', '!=', True)])
            if seller_ids:
                product_ids_seller = seller_ids.mapped('product_tmpl_id').mapped('product_variant_ids')
                product_ids = product_ids_seller
                for product in product_ids:
                    seller = product._select_seller(
                        partner_id=self.partner_id, quantity=1)
                    if seller:
                        line_vals.append(Command.create({
                            'product_id': product.id,
                            'product_uom': product.uom_id.id,
                            'product_uom_qty': 0.0,
                            'product_packaging_id': seller.packaging,
                        }))
                self.update({'order_line': line_vals})

                for line in self.order_line:
                    line._product_id_change()
                    line._compute_price_unit_and_date_planned_and_name()
                    line.calculate_discount_percentage()

    @api.onchange('date_planned')
    def onchange_date_planned(self):
        """ recompute price , check promo"""
        if self.date_planned:
            for line in self.order_line:
                line.date_planned = self.date_planned
                line._compute_price_unit_and_date_planned_and_name()
                line.calculate_discount_percentage()

