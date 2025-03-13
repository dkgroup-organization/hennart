# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    coef_workshop_cost = fields.Float(
        string="Coefficient Workshop Cost",
        config_parameter='customize_account.coef_workshop_cost'
    )
