# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    workshop_coefficient = fields.Float(
        string="Workshop Coefficient",
        default=1.12,
        config_parameter='product.template.workshop_coefficient',
        help="Coefficient used to calculate the workshop cost price"
    )

    def button_update_packaging(self):
        """ Update all line"""
        all_line_ids = self.env['mrp.bom.linev7'].search([])
        all_line_ids.update_bom_line()

    def button_update_product(self):
        """ Update all product"""
        all_ids = self.env['product.template'].search([])
        all_ids.bom_ids.compute_package()
        all_ids.compute_package()

