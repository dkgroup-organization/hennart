# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################

from datetime import date, timedelta, datetime
from odoo import api, fields, models, Command, _
from odoo.exceptions import UserError, ValidationError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def action_create_invoice(self):
        """ Update invoice with picking weight
        """
        res = super().action_create_invoice()
        domain = res.get('domain')
        if res.get('type', '?') == 'ir.actions.act_window_close':
            return
        elif res.get('res_id'):
            domain = [('id', '=', int(res.get('res_id')))]

        if domain:
            invoices = self.env['account.move'].search(domain)
            invoices.update_discount_stock()
        return res
