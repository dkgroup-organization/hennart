# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def button_update_account(self):
        "Update All account code"
        account_ids = self.env['account.account'].search([])
        
        for account in account_ids:
            if len(account.code) == 6 and account.code[:2] != 99:
                print(account.code)
                reconcile = account.reconcile
                code = account.code + '00000'
                account.write({'reconcile': reconcile, 'code': code})


