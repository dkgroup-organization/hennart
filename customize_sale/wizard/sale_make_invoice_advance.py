# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tools import float_is_zero


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    advance_payment_method = fields.Selection(
        selection=[
            ('delivered', "Regular invoice"),
            ('percentage', "Down payment (percentage)"),
            ('fixed', "Down payment (fixed amount)"),
        ],
        string="Create Invoice",
        default='delivered',
        invisible=True,
        required=True,
        help="A standard invoice is issued with all the order lines ready for invoicing,"
            "according to their invoicing policy (based on ordered or delivered quantity).")

    #=== ACTION METHODS ===#

    def create_invoices2(self):
        self._create_invoices2(self.sale_order_ids)

        if self.env.context.get('open_invoices'):
            return self.sale_order_ids.action_view_invoice()

        return {'type': 'ir.actions.act_window_close'}

    #=== BUSINESS METHODS ===#

    def _create_invoices2(self, sale_orders):
        self.ensure_one()
        invoices = sale_orders._create_invoices(final=self.deduct_down_payments)
        print('-----------invoices-------------', invoices)
        invoices.update_discount_stock()
