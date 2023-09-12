# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tools import float_is_zero


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'


    #=== BUSINESS METHODS ===#

    def _create_invoices(self, sale_orders):
        self.ensure_one()
        if self.advance_payment_method == 'delivered':
            return sale_orders._create_invoices(final=self.deduct_down_payments)
        else:
            self.sale_order_ids.ensure_one()
            self = self.with_company(self.company_id)
            order = self.sale_order_ids

            # Create deposit product if necessary
            if not self.product_id:
                self.product_id = self.env['product.product'].create(
                    self._prepare_down_payment_product_values()
                )
                self.env['ir.config_parameter'].sudo().set_param(
                    'sale.default_deposit_product_id', self.product_id.id)

            # Create down payment section if necessary
            if not any(line.display_type and line.is_downpayment for line in order.order_line):
                self.env['sale.order.line'].create(
                    self._prepare_down_payment_section_values(order)
                )

            down_payment_so_line = self.env['sale.order.line'].create(
                self._prepare_so_line_values(order)
            )

            invoice = self.env['account.move'].sudo().create(
                self._prepare_invoice_values(order, down_payment_so_line)
            )

            invoice.invoice_line_ids.update_stock_move()

            invoice = invoice.with_user(self.env.uid)  # Unsudo the invoice after creation

            """ invoice.message_post_with_view(
                'mail.message_origin_link',
                values={'self': invoice, 'origin': order},
                subtype_id=self.env.ref('mail.mt_note').id)
            """

            return invoice
