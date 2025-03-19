# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime, timedelta
from odoo.fields import Command
from collections import defaultdict
from odoo.exceptions import UserError, ValidationError
import time


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'


    @api.depends('product_id', 'order_id.partner_id', 'order_id.commitment_date')
    def compute_cadence(self):
        """ get the sale frequency of the product"""
        nb_week = 13

        for line in self:
            date_start = line.order_id.commitment_date or datetime.today()
            date_start = date_start - timedelta(days=date_start.weekday())  # monday
            if line.order_id.partner_shipping_id.parent_id:
                partner_shipping_id = line.order_id.partner_shipping_id.parent_id
            else:
                partner_shipping_id = line.order_id.partner_shipping_id

            condition = [
                '&', '|', ('move_id.partner_id', 'child_of', line.order_id.partner_id.id),
                ('move_id.partner_shipping_id', 'child_of', partner_shipping_id.id),
                '&', ('product_id', '=', line.product_id.id),
                '&', ('move_id.state', '=', 'posted'),
                '&', ('uom_qty', '>=', 1.0),
                '&', ('move_id.move_type', '=', 'out_invoice'),
                ]
            qty_by_week = {}
            # Loop through the past 13 weeks
            if line.product_id:
                for week in range(0, nb_week):
                    date_to = date_start - timedelta(weeks=week)
                    date_from = date_start - timedelta(weeks=week + 1)
                    # Get the quantity sold for the product for the current week
                    invoice_lines = self.env['account.move.line'].search(condition + [
                        '&', ('move_id.invoice_date', '<', date_to),
                        ('move_id.invoice_date', '>=', date_from)
                        ])
                    qty = sum(invoice_lines.mapped('uom_qty'))
                    if qty >= 1.0:
                        qty_by_week['{}'.format(week)] = qty

            # If there is data for the product, create a table to display the quantity sold by week
            cadence_table = '<table style="border-collapse: collapse; width: 100%; table-layout: fixed;"><tr>'
            style_td = "border-left: 1px solid grey; width:7.6%; padding-left: 5px; padding-right: 5px;"
            style_text = " font-weight: bold; text-align: center;"
            for week in range(1, 14):
                qty = qty_by_week.get('{}'.format(week), '')
                if qty and qty != '':
                    qty_str = str(int(qty))
                    cadence_table += '<td style="{}">{}</td>'.format(style_td + style_text, qty_str)
                else:
                    cadence_table += '<td style="{}"></td>'.format(style_td)
            cadence_table += '</tr></table>'
            line.cadence = cadence_table
