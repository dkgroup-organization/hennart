# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    note = fields.Char('Notes', translate=True, help="Legal mentions that have to be printed on the invoices.")