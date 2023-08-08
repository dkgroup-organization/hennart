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

        # no sale package
        for purchase_price in all_purchase_price:
            purchase_price.packaging.sales = False
            purchase_price.packaging.purchase = True

        package_ids = self.env['product.packaging'].search([('sales', '=', True)])
        package_ids.unlink()

        # check if the package has a  product
        all_purchase_price = self.env['product.supplierinfo'].search([('product_id', '=', False)])
        for purchase_price in all_purchase_price:
            purchase_price.product_id = purchase_price.product_tmpl_id.product_variant_id
            if purchase_price.packaging:
                purchase_price.packaging.product_id = purchase_price.product_id


        # Check if the product has a bom
        bom_product_ids = self.env['mrp.bom'].search([]).mapped('product_id')
        bom_purchase_price = self.env['product.supplierinfo'].search([('product_id', 'in', bom_product_ids.ids)])
        bom_purchase_price.unlink()

        # Check if the product has the purchase_ok = True
        product_tmpl_ids = self.env['product.supplierinfo'].search([('product_tmpl_id.purchase_ok', '=', False)]).mapped('product_tmpl_id')
        product_tmpl_ids.purchase_ok = True


