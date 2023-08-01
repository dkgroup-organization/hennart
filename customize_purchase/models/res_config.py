# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def button_update_purchase_packaging(self):
        """ Update all line"""

        # no unit
        package_ids = self.env['product.packaging'].search([('qty', '<=', 1)])
        package_ids.unlink()

        package_ok = self.env['product.packaging']
        all_purchase_price = self.env['product.supplierinfo'].search([
            '&', ('packaging', '!=', False), ('packaging.sales', '=', True)
            ])

        for purchase_price in all_purchase_price:
            purchase_price.packaging.sales = False
            purchase_price.packaging.purchase = True

        package_ids = self.env['product.packaging'].search([('sales', '=', True)])
        package_ids.unlink()

