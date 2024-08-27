# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################

from datetime import date, timedelta, datetime
from odoo import api, fields, models, Command, _
from odoo.exceptions import UserError, ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def create_custom_invoice(self):
        """ custom create invoice"""
        res = self.env['account.move']
        for sale in self:
            if sale.invoice_status == "to invoice":
                invoices = sale._create_invoices()
            else:
                invoices = sale.invoice_ids
            res |= invoices

            for sale_line in sale.order_line:
                for invoice_line in sale_line.invoice_lines:
                    for stock_move in sale_line.move_ids:
                        for stock_move_line in stock_move.move_line_ids:
                            if invoice_line.account_move_line_lot_ids and not invoice_line.account_move_line_lot_ids[0].stock_move_line_id:
                                invoice_line.account_move_line_lot_ids[0].stock_move_line_id = stock_move_line
                                invoice_line.account_move_line_lot_ids[0].lot_id = stock_move_line.lot_id
                                invoice_line.account_move_line_lot_ids[0].uom_qty = stock_move_line.qty_done
                                invoice_line.account_move_line_lot_ids[0].weight = stock_move_line.weight
                            else:
                                line_lot_vals = {
                                    'account_move_line_id': invoice_line.id,
                                    'stock_move_line_id': stock_move_line.id,
                                    'lot_id': stock_move_line.lot_id,
                                    'uom_qty': stock_move_line.qty_done,
                                    'weight': stock_move_line.weight,
                                }
                                invoice_line.account_move_line_lot_ids.create(line_lot_vals)

        for invoice in res:
            if invoice.state == 'draft':
                for line in invoice.line_ids:
                    line._compute_totals()
                    line._compute_all_tax()

                invoice._compute_tax_totals()
                invoice._compute_amount()


                try:
                    invoice.action_post()
                except:
                    pass
        if self.env.context.get('open_invoices'):
            return self.action_view_invoice()
        else:
            return res
