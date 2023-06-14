# -*- coding: utf-8 -*-
from odoo import fields, models, api, Command
import logging
_logger = logging.getLogger(__name__)

class PurchaseOrderInherit(models.Model):
    _inherit = 'purchase.order'

    @api.onchange('partner_id')
    def onchange_partner_id_seller(self):
        self.order_line = False
        if self.partner_id:
            line_vals = []
            seller_ids = self.env['product.supplierinfo'].search([('partner_id', '=', self.partner_id.id)])
            if seller_ids:
                product_ids_seller = seller_ids.mapped('product_tmpl_id').mapped('product_variant_ids')
                product_ids = product_ids_seller
                for product in product_ids:
                    seller = product._select_seller(
                        partner_id=self.partner_id, quantity=1)
                    if (seller):
                        line_vals.append(Command.create({
                            'product_id': product.id,
                            'product_uom_qty': 0.0,
                            'product_packaging_id': seller.packaging,
                        }))
                self.update({'order_line': line_vals})
                if line_vals:
                    for line in self.order_line:
                        line._product_id_change()
                        line._compute_price_unit_and_date_planned_and_name()
                        line.calculate_discount_percentage()

    @api.onchange("date_order")
    def update_discount_ligne(self):
        for line in self.order_line:
            line.calculate_discount_percentage()