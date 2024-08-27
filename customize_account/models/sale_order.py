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

        for invoice in res:
            if invoice.state == 'draft':
                invoice.action_post()

        if self.env.context.get('open_invoices'):
            return self.action_view_invoice()
        else:
            return res
