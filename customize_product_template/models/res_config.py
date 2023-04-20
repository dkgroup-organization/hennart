# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def button_update_packaging(self):
        """ Update all line"""
        all_line_ids = self.env['mrp.bom.linev7'].search([])
        all_line_ids.update_bom_line()