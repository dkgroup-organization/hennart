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
        for sale in self:
            invoices = sale._create_invoices()
            invoices.update_discount_stock()

        if self.env.context.get('open_invoices'):
            return self.action_view_invoice()
